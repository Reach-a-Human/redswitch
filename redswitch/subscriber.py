import asyncio
import collections
import logging
import time

import aredis
import ujson
from switchy.utils import APIError

from .event import CallResponse
from .utils import parse_redis_url

log = logging.getLogger('redswitch.subscriber')


Job = collections.namedtuple('Job', ['dial_id', 'call_id', 'barge_id'])


class Subscriber:
    def __init__(self, url):
        host, port, password = parse_redis_url(url)
        self.redis = aredis.StrictRedisCluster(host=host, port=port,
                                               password=password)
        self.pubsub = self.redis.pubsub()

        self.esl = None

        self.jobs = dict()
        self.new_subscriptions = set()

    def set_esl(self, esl):
        self.esl = esl

    def subscribe(self, dial_id, call_id):
        self.jobs[dial_id] = Job(dial_id=dial_id, call_id=call_id, barge_id=0)
        self.jobs[call_id] = Job(dial_id=dial_id, call_id=call_id, barge_id=0)

        # This method is always called within an ESL thread. Due to jankiness
        # of the switchy and aredis libraries, the former can not communicate
        # with the latter.

        # We add this dial_id to a set which the `self.subscribe` loop
        # constantly polls and deals with in the asyncio thread. That loop is
        # responsible for _actually_ subscribing the the `dial_id` channel;
        # once it does, our while loop breaks.
        self.new_subscriptions.add(dial_id)
        while dial_id in self.new_subscriptions:
            time.sleep(0.05)

    async def do_subscribe(self):
        while True:
            await asyncio.sleep(0.01)

            try:
                channel = self.new_subscriptions.pop()
            except KeyError:
                # no new subscriptions
                continue

            await self.pubsub.subscribe(channel)

    async def poll(self):
        if not self.esl:
            raise Exception('redis instance has no ESL connection')

        while True:
            await asyncio.sleep(0.01)

            try:
                job = await self.pubsub.get_message()
            except RuntimeError:
                # no subscriptions yet
                await asyncio.sleep(1)
                continue

            if not job or job.get('type') in ('subscribe', 'unsubscribe'):
                continue

            channel_id = job.get('channel').decode()
            job = ujson.loads(job['data'])
            kind = job.get('type')
            if kind in ('ack', 'answer-event', 'bridge-event',
                        'channel-create-event', 'hangup-event', 'call-start', 'success', 'failure'):
                continue

            try:
                await self.redis.publish(channel_id, CallResponse.get(kind))
                getattr(self, kind.replace('-', '_'))(channel_id, job)
            except AttributeError as e:
                log.warning('subscriber for %s got event %s', channel_id, kind)
                log.exception(e)

    def barge(self, dial_id, job):
        call_id = self.jobs[dial_id].call_id
        caller_id = job['caller_id']
        phone_number = job['phone_number']

        log.info('sending barge from %s on %s', phone_number, dial_id)
        self.esl.barge(dial_id, call_id, caller_id, job)

    def bot_call(self, core_id, job):
        phone_number = job['phone_number']

        log.info('sending call (leg 2) to %s on %s', phone_number, core_id)

        self.esl.call(job)

    def bridge(self, core_id, job):
        try:
            call_id1 = self.jobs[job['dial_id1']].call_id
            call_id2 = self.jobs[job['dial_id2']].call_id
        except KeyError as error:
            log.error('bridge failure', exc_info=error)
            self.esl.bridge_error(error)
            return

        log.info('bridging calls %s and %s on %s', call_id1, call_id2, core_id)
        self.esl.bridge(call_id1, call_id2)

    def hangup(self, dial_id, _job):
        log.info('sending hangup for %s', dial_id)
        call_id = self.jobs[dial_id].call_id

        try:
            self.esl.hangup(call_id)
        except APIError:
            log.info('%s is already hungup', dial_id)

    def stop_playback(self, dial_id, _job):
        log.info('stopping playback for %s', dial_id)
        call_id = self.jobs[dial_id].call_id
        self.esl.stop_playback(call_id)

    def mute(self, dial_id, _job):
        barge_id = self.jobs[dial_id].barge_id

        log.info('sending mute for %s on %s', barge_id, dial_id)
        self.esl.mute(barge_id)

    def threeway(self, dial_id, _job):
        barge_id = self.jobs[dial_id].barge_id
        log.info('starting threeway for %s on %s', barge_id, dial_id)
        self.esl.threeway(barge_id)

    def unthreeway(self, dial_id, _job):
        barge_id = self.jobs[dial_id].barge_id
        log.info('recived un threeway')
        self.esl.unthreeway(barge_id)

    def play(self, dial_id, job):
        try:
            call_id = self.jobs[dial_id].call_id
        except KeyError as error:
            self.esl.play_error(error)
            return

        try:
            media_path = job['path']
        except KeyError as error:
            self.esl.play_error(error, kind=1)
            return

        log.info('playing %s on %s', media_path, dial_id)
        self.esl.play(call_id, media_path)

    def play_now(self, dial_id, job):
        try:
            call_id = self.jobs[dial_id].call_id
        except KeyError as error:
            self.esl.play_error(error)
            return

        try:
            media_path = job['path']
        except KeyError as error:
            self.esl.play_error(error, kind=1)
            return

        log.info('playing %s on %s', media_path, dial_id)
        self.esl.play(call_id, media_path)

    def whisper(self, dial_id, _job):
        barge_id = self.jobs[dial_id].barge_id

        log.info('sending whisper for %s on %s', barge_id, dial_id)
        self.esl.whisper(barge_id)

    def start_background(self, dial_id, job):
        try:
            call_id = self.jobs[dial_id].call_id
        except KeyError as error:
            self.esl.play_error(error)
            return

        try:
            path = job['path']
        except KeyError as error:
            self.esl.play_error(error, kind=1)
            return

        self.esl.start_background(call_id, path)

    def stop_background(self, dial_id, job):
        call_id = self.jobs[dial_id].call_id
        path = job['path']
        self.esl.stop_background(call_id, path)
