import asyncio
import logging

import aredis
import ujson

from .utils import parse_redis_url


log = logging.getLogger('redswitch.call_watcher')


class CallWatcher:
    def __init__(self, redis_url, esl):
        host, port, password = parse_redis_url(redis_url)
        self.connection = aredis.StrictRedisCluster(host=host, port=port,
                                                    password=password)
        self.esl = esl

        self.rjob = None
        self.rlist = None

    async def poll(self):
        while True:
            await asyncio.sleep(0.01)

            job = await self.connection.lpop(self.rlist)
            if not job:
                continue

            job = ujson.loads(job)
            kind = job.get('type')
            if kind == self.rjob:
                # All switchy methods are called in a dedicated thread, thus
                # this function call is pretty much non-blocking.
                self.esl.call(job)
                continue

            log.warning('got bad job %s on list %s', kind, self.rlist)


class CallWatcherAsp(CallWatcher):
    def __init__(self, *args, **kwargs):
        super(CallWatcherAsp, self).__init__(*args, **kwargs)

        self.rjob = 'asp-call'
        self.rlist = 'talkiq-asp.calls'


class CallWatcherBot(CallWatcher):
    def __init__(self, *args, **kwargs):
        super(CallWatcherBot, self).__init__(*args, **kwargs)

        self.rjob = 'bot-call'
        self.rlist = 'talkiq-bot.calls'

class CallWatcherLoad(CallWatcher):
    def __init__(self, *args, **kwargs):
        super(CallWatcherLoad, self).__init__(*args, **kwargs)

        self.rjob = 'load-test'
        self.rlist = 'talkiq-load.calls'
