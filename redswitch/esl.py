import logging
import os
import uuid

import rediscluster
import switchy
from switchy.utils import APIError

from .event import CallEvent
from .event import DTMF
from .subscriber import Job
from .utils import parse_redis_url


PUBSUB_REDIS_TIMEOUT = int(os.environ.get('PUBSUB_REDIS_TIMEOUT', '10'))

log = logging.getLogger('redswitch.esl')


class ESL:
    def __init__(self, redis_url, subscriber):
        host, port, password = parse_redis_url(redis_url)
        self.redis = rediscluster.StrictRedisCluster(
            host=host, port=port, password=password,
            socket_timeout=PUBSUB_REDIS_TIMEOUT)
        self.subscriber = subscriber

        self.calls = set()
        #TODO make env_var
        self.gateway = 'flowroute'
        self.client = None

    def _our_call(self, event):
        return event.getHeader('variable_dial_id') in self.calls

    def barge(self, dial_id, call_id, caller_id, data):
        uid = str(uuid.uuid4())
        # TODO: mutable subscriber jobs
        job = self.subscriber.jobs[dial_id]
        self.subscriber.jobs[dial_id] = Job(dial_id=job.dial_id,
                                            call_id=job.call_id, barge_id=uid)

        chan_vars = {
            'dial_id': dial_id,
            'origination_callee_id_number': str(caller_id),
            'origination_uuid': uid,
        }
        gateway = self.gateway

        handle_sip2sip = self.handle_sip2sip(data, chan_vars)
        if handle_sip2sip is None:
            return

        if handle_sip2sip:
            # TODO: make envvar
            gateway = None

        self.client.originate(
            uuid_func=lambda: uid,
            dest_url=data['phone_number'],
            gateway=gateway,
            app_name='eavesdrop',
            app_arg_str=call_id,
            **chan_vars)

        log.info('esl barging %s from %s', dial_id, data['phone_number'])

    def handle_sip2sip(self, data, chan_vars):
        # TODO: revisit this for robustness
        if '@' in data['phone_number']:
            log.info('sip call to %s', data['phone_number'])
            if data.get('auth', False):
                if {'sip_auth_username,'  'sip_auth_password'} - data.keys():
                    event = CallEvent.failure('unknown',
                                              'Missing username/password')
                    self.redis.publish(data['dial_id'], event)
                    log.warning('Call failed for %s', data['dial_id'])
                    return None

                chan_vars['sip_auth_username'] = data['sip_auth_username']
                chan_vars['sip_auth_password'] = data['sip_auth_password']
                return True

        return False

    def bridge(self, uuid1, uuid2, delay=0):
        raise NotImplementedError

    def call(self, data):
        raise NotImplementedError

    def hangup(self, call_id, delay=0):
        raise NotImplementedError

    def mute(self, barge_id, delay=0):
        raise NotImplementedError

    def play(self, call_id, path):
        raise NotImplementedError

    def stop_playback(self, call_id):
        raise NotImplementedError

    def whisper(self, barge_id, delay=0):
        raise NotImplementedError


class ESLAsp(ESL):
    def __init__(self, redis_url, subscriber, host, port, password):
        super(ESLAsp, self).__init__(redis_url, subscriber)
        l = switchy.EventListener(host=host, port=port, auth=password,
                                  autorecon=True)

        l._handlers['CHANNEL_ANSWER'] = self.channel_answer
        l._handlers['CHANNEL_HANGUP'] = self.channel_hangup
        l._handlers['CHANNEL_ORIGINATE'] = self.channel_originate
        l.connect()
        l.start()

        self.client = switchy.Client(host, port, password, listener=l)
        self.client.connect()
        log.debug('connected to esl (for asp) at %s:%s', host, port)

    def channel_answer(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_ANSWER for %s', event.getHeader('Unique-ID'))

        call_id = event.getHeader('variable_call_uuid')
        dial_id = event.getHeader('variable_dial_id')
        org_id = event.getHeader('variable_sip_h_Accuvit-Organization-ID')
        user_id = event.getHeader('variable_sip_h_Accuvit-User-ID')
        side = event.getHeader('variable_call-side')
        if not side:
            return False, None

        call_key = 'redswitch.{}.{}.{}'.format(org_id, user_id, dial_id)
        state_value = '{}.{}'.format('ACTIVE', side)

        self.subscriber.subscribe(dial_id, call_id)
        self.redis.publish(dial_id, CallEvent.answer(side))
        self.redis.lpush(call_key, state_value)
        self.redis.expire(call_key, 86400)
        self.log_history(CallEvent.answer(side), org_id, user_id)

        return False, None

    def channel_hangup(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_HANGUP for %s', event.getHeader('Unique-ID'))

        dial_id = event.getHeader('variable_dial_id')
        org_id = event.getHeader('variable_sip_h_Accuvit-Organization-ID')
        user_id = event.getHeader('variable_sip_h_Accuvit-User-ID')
        side = event.getHeader('variable_call-side')
        hangup_cause = event.getHeader('Hangup-Cause')

        if not side:
            log.info('not our call to handle (missing call-side)')
            return False, None

        call_key = 'redswitch.{}.{}.{}'.format(org_id, user_id, dial_id)
        state_value = '{}.{}'.format('ACTIVE', side)

        self.redis.publish(dial_id, CallEvent.hangup(side, hangup_cause))
        self.redis.lrem(call_key, 0, state_value)
        self.log_history(CallEvent.hangup(side, hangup_cause), org_id, user_id)

        return False, None

    def channel_originate(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_ORIGINATE for %s', event.getHeader('Unique-ID'))
        return False, None



    def call(self, data):
        log.info('esl calling %s from %s on %s (using asp)',
                 data['callee_number'], data['caller_number'], data['dial_id'])

        if not data['callee_number'] or not data['caller_number']:
            log.error('Invalid callee_number: %s or caller_number: %s',
                      data['callee_number'], data['caller_number'])
            return

        uid = str(uuid.uuid4())
        self.calls.add(data['dial_id'])

        chan_vars = {
            'call-side': '0',
            'dial_id': data['dial_id'],
            'instant_ringback': 'true',
            'ignore_early_media': 'true',
            'origination_caller_id_number': data['caller_id_lega'],
            'origination_callee_id_number': data['caller_id_legb'],
            'origination_uuid': uid,
            'sip_h_Accuvit-Dial-ID': data['dial_id'],
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': data['org_id'],
            'sip_h_Accuvit-User-ID': data['user_id'],
            'sip_h_X-TalkIQ-Callprovider': data['call_provider'],
        }
        app_arg_str = ''.join((
            '[call-side=1]',
            '[dial_id={}]'.format(data['dial_id']),
            '[sip_h_Accuvit-Dial-Side=1]',
            'sofia/gateway/flowroute/{}'.format(data['callee_number']),
        ))

        self.client.originate(
            uuid_func=lambda: uid,
            dest_url=data['caller_number'],
            gateway='flowroute',
            app_name='bridge',
            app_arg_str=app_arg_str,
            **chan_vars)

        # TODO: fix all of this
        event = CallEvent.call_start(data['dial_id'])
        self.delete_history(data['org_id'], data['user_id'])
        self.redis.publish(data['dial_id'], event)
        self.log_history(event, data['org_id'], data['user_id'])

    def hangup(self, call_id, delay=0):
        log.info('esl hanging up %s (using asp)', call_id)
        self.client.api('sched_hangup +{} {} NORMAL_CLEARING'.format(delay,
                                                                     call_id))

    def mute(self, barge_id, delay=0):
        log.info('esl muting barge %s (using asp)', barge_id)
        self.client.api('sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.MUTE))

    def threeway(self, barge_id, delay=0):
        log.info('esl staring threeway calling theeway for %s', barge_id)
        self.client.api('sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.THREEWAY))

    def unthreeway(self, barge_id, delay=0):
        log.info('esl ending threeway calling for %s', barge_id)
        self.client.api('sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.UNTHREEWAY))

    def play(self, call_id, path):
        log.info('esl playing %s on %s (using asp)', path, call_id)
        self.client.api('sched_broadcast +0 {} {} both'.format(call_id, path))

    def whisper(self, barge_id, delay=0):
        log.info('esl whispering barge %s (using asp)', barge_id)
        self.client.api('sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.WHISPER))

    def log_history(self, event, org_id, user_id, expiry=14400):
        key = 'redswitch_history.{}.{}'.format(org_id, user_id)
        self.redis.lpush(key, event)
        self.redis.expire(key, expiry)

    def delete_history(self, org_id, user_id):
        self.redis.delete('redswitch_history.{}.{}'.format(org_id, user_id))


class ESLLoad(ESL):
    def __init__(self, redis_url, subscriber, host, port, password):
        super(ESLLoad, self).__init__(redis_url, subscriber)
        l = switchy.EventListener(host=host, port=port, auth=password,
                                  autorecon=True)

        l._handlers['CHANNEL_ANSWER'] = self.channel_answer
        #l._handlers['CHANNEL_CREATE'] = self.channel_create
        l._handlers['CHANNEL_HANGUP'] = self.channel_hangup

        l.connect()
        l.start()

        self.client = switchy.Client(host, port, password, listener=l)
        self.client.connect()
        log.debug('connected to esl (load-test) at %s:%s', host, port)

        self.core = None


    def call(self, data):
        log.info('esl calling %s from %s call-leg', data['phone_number'],
                 data['dial_id'])

        uid = str(uuid.uuid4())
        self.calls.add(str(data['dial_id']))

        chan_vars = {
            'call-side': data['leg'],
            'dial_id': data['dial_id'],
            'ignore_early_media': 'False',
            'origination_caller_id_number': data['leg'],
            'origination_uuid': uid,
            'sip_h_X-Dialpad-CRM': data['dialpad_crm'],
            'sip_h_X-Dialpad-OrganizationId': data['org_id'],
            'sip_h_X-Dialpad-CallLeg': data['leg'],
            'sip_h_X-Dialpad-CallLegTag': data['leg'],
            'sip_h_X-Dialpad-ParentCallId': data['parent_callid'],
            'sip_h_X-Dialpad-CalleeName': data['callee_name'],
            'sip_h_X-Dialpad-TargetKey': data['target_key'],
            'sip_h_X-Dialpad-Topic': data['topic'],
        }

        self.client.originate(
            uuid_func=lambda: uid,
            dest_url=data['phone_number'],
            gateway=data['gateway'],
            app_name='park',
            **chan_vars)

    def channel_answer(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('CHANNEL_ANSWER %s', str(event.getHeader('variable_dial_id')))

        call_id = event.getHeader('variable_call_uuid')
        dial_id = event.getHeader('variable_dial_id')
        side = event.getHeader('variable_sip_h_X-Dialpad-CallLeg')

        self.redis.publish(dial_id, CallEvent.answer(side))
        self.subscriber.subscribe(dial_id, call_id)
        return False, None

    def channel_hangup(self, event):
        if not self._our_call(event):
            return False, None

        dial_id = event.getHeader('variable_dial_id')
        side = event.getHeader('variable_sip_h_X-Dialpad-CallLeg')
        hangup_cause = event.getHeader('Hangup-Cause')
        self.redis.publish(dial_id, CallEvent.hangup(side, hangup_cause))
        return False, None

    def hangup(self, call_id, delay=0):
        log.info('esl hanging up %s (using loadtest)', call_id)
        self.client.api('sched_hangup +{} {} NORMAL_CLEARING'.format(delay,
                                                                     call_id))

    def play(self, call_id, path):
        log.info('esl playing %s on %s (using loadtest)', path, call_id)
        self.client.api('sched_broadcast +0 {} {} both'.format(call_id, path))


class ESLBot(ESL):
    def __init__(self, redis_url, subscriber, host, port, password):
        super(ESLBot, self).__init__(redis_url, subscriber)
        l = switchy.EventListener(host=host, port=port, auth=password,
                                  autorecon=True)

        l._handlers['CHANNEL_ANSWER'] = self.channel_answer
        l._handlers['CHANNEL_BRIDGE'] = self.channel_bridge
        l._handlers['CHANNEL_CREATE'] = self.channel_create
        l._handlers['CHANNEL_HANGUP'] = self.channel_hangup

        l.connect()
        l.start()

        self.client = switchy.Client(host, port, password, listener=l)
        self.client.connect()
        log.debug('connected to esl (for bot) at %s:%s', host, port)
        self.core = None

    def call(self, data):
        log.info('esl calling %s from %s (using bot)', data['phone_number'],
                 data['dial_id'])

        uid = str(uuid.uuid4())
        self.calls.add(uid)

        chan_vars = {
            'call-side': '0',
            'dial_id': data['dial_id'],
            'ignore_early_media': 'False',
            'origination_caller_id_number': data['caller_id'],
            'origination_uuid': uid,
            'sip_h_Accuvit-Dial-ID': data['dial_id'],
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': data['org_id'],
            'sip_h_Accuvit-User-ID': data['user_id'],
            'sip_h_X-TalkIQ-Callprovider': 'auto-bot',
        }

        self.client.originate(
            uuid_func=lambda: uid,
            dest_url=data['phone_number'],
            gateway='opensips',
            app_name='park',
            **chan_vars)


    def channel_answer(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_ANSWER for %s', event.getHeader('Unique-ID'))
        dial_id = event.getHeader('variable_dial_id')
        side = event.getHeader('variable_sip_h_Accuvit-Dial-Side')

        self.redis.publish(dial_id, CallEvent.answer(side))
        return False, None

    def channel_bridge(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_BRIDGE for %s', event.getHeader('Unique-ID'))

        core = event.getHeader('Core-UUID')
        call_id1 = event.getHeader('Unique-ID')
        call_id2 = event.getHeader('Other-Leg-Unique-ID')

        dial_id1 = self.subscriber.jobs[call_id1].dial_id
        dial_id2 = self.subscriber.jobs[call_id2].dial_id
        self.redis.publish(core, CallEvent.bridge(core, dial_id1, dial_id2))
        return False, None

    def channel_create(self, event):
        if not self._our_call(event):
            log.info(event.getHeader('variable_dial_id'))
            return False, None

        log.debug('got CHANNEL_CREATE for %s', event.getHeader('variable_dial_id'))
        dial_id = event.getHeader('variable_dial_id')
        call_id = event.getHeader('variable_call_uuid')
        core = event.getHeader('Core-UUID')

        if core != self.core:
            log.info('creating channel with core_id %s ', core)
            self.subscriber.subscribe(core, dial_id)
            self.core = core

        self.subscriber.subscribe(dial_id, call_id)
        log.info('subscribed to %s', dial_id)

        self.redis.publish(dial_id, CallEvent.channel_create(self.core))
        self.redis.publish(self.core, CallEvent.channel_create(self.core))

        return False, None

    def channel_hangup(self, event):
        if not self._our_call(event):
            return False, None

        log.debug('got CHANNEL_HANGUP for %s', event.getHeader('Unique-ID'))

        dial_id = event.getHeader('variable_dial_id')
        side = event.getHeader('variable_sip_h_Accuvit-Dial-Side')
        hangup_cause = event.getHeader('Hangup-Cause')

        log.info(hangup_cause)
        self.redis.publish(dial_id, CallEvent.hangup(side, hangup_cause))

        return False, None

    def bridge(self, uuid1, uuid2, delay=0):
        log.info('esl bridging %s and %s (using bot)', uuid1, uuid2)
        job = self.client.bgapi('uuid_bridge {} {}'.format(uuid1, uuid2))

        if 'Invalid' in job.result:
            log.info('bridge failure: %s', job.result)
            event = CallEvent.failure('bridge-event',
                                      'bad job result {}'.format(job.result))
        else:
            event = CallEvent.success('bridge-event')

        self.redis.publish(self.core, event)

    def bridge_error(self, error):
        log.info('not attempting bridge cause %s', error)
        event = CallEvent.failure('bridge-event',
                                  'no such dial_id {}'.format(error))
        self.redis.publish(self.core, event)

    def call(self, data):
        log.info('esl calling %s from %s (using bot)', data['phone_number'],
                 data['dial_id'])

        if not data['phone_number']:
            log.error('phone_number is required')
            if data['dial_id'] is not None:
                event = CallEvent.failure('call',
                                          'missing required field in call job')
                self.redis.publish(data['dial_id'], event)
                return

            log.warning('dial_id was None no call will be made and no error '
                        'will be published to redis')
            return

        uid = str(uuid.uuid4())
        self.calls.add(data['dial_id'])

        chan_vars = {
            'call-side': '0',
            'dial_id': data['dial_id'],
            'ignore_early_media': 'False',
            'park_after_bridge': 'True',
            'origination_caller_id_number': data['caller_id'],
            'origination_uuid': uid,
            'sip_h_Accuvit-Dial-ID': data['dial_id'],
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': data['org_id'],
            'sip_h_Accuvit-User-ID': data['user_id'],
            'sip_h_X-TalkIQ-Callprovider': 'auto-bot',
        }
        gateway = self.gateway
        # TODO: revisit this for robustness

        if '@' in data['phone_number']:
            log.info('sip call to %s', data['phone_number'])
            gateway = None

            if data.get('auth', False):
                if {'sip_auth_username,'  'sip_auth_password'} - data.keys():
                    log.warning('Call failed for %s', data['dial_id'])

                    event = CallEvent.failure('call',
                                              'Missing username/password')
                    self.redis.publish(data['dial_id'], event)
                    return

                chan_vars['sip_auth_username'] = data['sip_auth_username']
                chan_vars['sip_auth_password'] = data['sip_auth_password']

        self.client.originate(
            uuid_func=lambda: uid,
            dest_url=data['phone_number'],
            gateway=gateway,
            app_name='park',
            **chan_vars)

    def hangup(self, call_id, delay=0):
        log.info('esl hanging up %s (using bot)', call_id)
        self.client.api('sched_hangup +{} {} NORMAL_CLEARING'.format(delay,
                                                                     call_id))

    def start_background(self, call_id, path):
        log.info('playing bakground music to %d', call_id)
        self.client.api('uuid_displace {} start {} 0 mux'.format(call_id, path))

    def stop_background(self, call_id, path):
        log.info('stopping background music to %d', call_id)
        self.client.api('uuid_displace {} stop {}'.format(call_id, path))

    def play(self, call_id, path):
        log.info('esl playing %s to %s', path, call_id)
        job = self.client.bgapi('uuid_broadcast {} {} both'.format(call_id,
                                                                   path))

        if 'Invalid' in job.result:
            log.info('playback failure: %s', job.result)
            event = CallEvent.failure('play-event',
                                      'bad job result {}'.format(job.result))
        else:
            event = CallEvent.success('play-event')

        self.redis.publish(self.core, event)

    def play_error(self, error, kind=0):
        if kind == 0:
            log.error('playback failure: %r %s', kind, error)
            event = CallEvent.failure('play',
                                      'no such dial_id {}'.format(error))
            self.redis.publish(self.core, event)
            return

        if kind == 1:
            log.error('playback failure: %r %s', kind, error)
            event = CallEvent.failure('play', 'no such path {}'.format(error))
            self.redis.publish(self.core, event)
            return

        log.error('unknown failure: %r %s', kind, error)

    def stop_playback(self, call_id):
        log.info('stopping audio playback on %s', call_id)

        try:
            self.client.api('uuid_break {} all'.format(call_id))
        except APIError:
            # freeswitch does not respond to uuid_break
            # suppresses switchy exception
            pass

    def play_now(self, call_id, path):
        log.info('stopping audio playback on %s and playing %s', call_id, path)

        try:
            self.client.api('uuid_break {} all'.format(call_id))
        except APIError:
            pass

        self.client.api('uuid_broadcast {} {} both'.format(call_id, path))
