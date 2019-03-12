from redswitch.event import CallEvent
from redswitch.event import DTMF
from redswitch.subscriber import Job


def test_asp_answer(mocker, asp_esl, answer_event):
    asp_esl.calls.add(answer_event.getHeader('variable_dial_id'))

    asp_esl.channel_answer(answer_event)

    call_id = answer_event.getHeader('variable_call_uuid')
    dial_id = answer_event.getHeader('variable_dial_id')
    side = answer_event.getHeader('variable_call-side')
    org_id = answer_event.getHeader('variable_sip_h_Accuvit-Organization-ID')
    user_id = answer_event.getHeader('variable_sip_h_Accuvit-User-ID')

    call_key = 'redswitch.{}.{}.{}'.format(org_id, user_id, dial_id)
    state_value = '{}.{}'.format('ACTIVE', side)

    asp_esl.subscriber.subscribe.assert_called_with(dial_id, call_id)
    asp_esl.redis.publish.assert_called_with(dial_id, CallEvent.answer(side))
    asp_esl.redis.lpush.assert_has_calls([mocker.call(call_key, state_value)])
    asp_esl.redis.redis.expire(call_key, 86400)


def test_bot_answer(bot_esl, answer_event):
    bot_esl.calls.add(answer_event.getHeader('variable_dial_id'))

    bot_esl.channel_answer(answer_event)
    dial_id = answer_event.getHeader('variable_dial_id')
    side = answer_event.getHeader('variable_sip_h_Accuvit-Dial-Side')

    bot_esl.redis.publish.assert_called_with(dial_id, CallEvent.answer(side))


def test_bot_bridge(bot_esl, bridge_event):
    bot_esl.calls.add(bridge_event.getHeader('variable_dial_id'))
    bot_esl.channel_bridge(bridge_event)
    core = bridge_event.getHeader('Core-UUID')
    call_id1 = bridge_event.getHeader('Unique-ID')
    call_id2 = bridge_event.getHeader('Other-Leg-Unique-ID')

    bot_esl.subscriber.jobs = {
        'call_id1': Job(dial_id='1337', call_id=call_id1, barge_id=0),
        'call_id2': Job(dial_id='1336', call_id=call_id2, barge_id=0),
    }

    event = CallEvent.bridge(core, bot_esl.subscriber[call_id1],
                             bot_esl.subscriber[call_id2])
    bot_esl.redis.publish.assert_called_with(core, event)


def test_bot_channel_hangup(bot_esl, hangup_event):
    bot_esl.calls.add(hangup_event.getHeader('variable_dial_id'))
    bot_esl.channel_hangup(hangup_event)

    dial_id = hangup_event.getHeader('variable_dial_id')
    side = hangup_event.getHeader('variable_sip_h_Accuvit-Dial-Side')
    hangup_cause = hangup_event.getHeader('Hangup-Cause')

    event = CallEvent.hangup(side, hangup_cause)
    bot_esl.redis.publish.assert_called_with(dial_id, event)


def test_bot_cmd_hangup(bot_esl):
    call_id = '1337'
    delay = 0

    bot_esl.hangup(call_id, delay=delay)

    bot_esl.client.api.assert_called_with(
        'sched_hangup +{} {} NORMAL_CLEARING'.format(delay, call_id))


def test_bot_cmd_startbackground(bot_esl):
    call_id = '1337'
    path = 'path2media'

    bot_esl.start_background(call_id, path)

    bot_esl.client.api.assert_called_with(
        'uuid_displace {} start {} 0 mux'.format(call_id, path))


def test_bot_cmd_stop_background(bot_esl):
    call_id = '1337'
    path = 'path2media'

    bot_esl.stop_background(call_id, path)

    bot_esl.client.api.assert_called_with(
        'uuid_displace {} stop {}'.format(call_id, path))


def test_bot_cmd_play_now(bot_esl):
    call_id = '1337'
    path = 'path2media'

    bot_esl.play_now(call_id, path)

    bot_esl.client.api.assert_called_with(
        'uuid_broadcast {} {} both'.format(call_id, path))


def test_asp_hangup(asp_esl, hangup_event):
    asp_esl.calls.add(hangup_event.getHeader('variable_dial_id'))
    asp_esl.channel_hangup(hangup_event)

    dial_id = hangup_event.getHeader('variable_dial_id')
    org_id = hangup_event.getHeader('variable_sip_h_Accuvit-Organization-ID')
    user_id = hangup_event.getHeader('variable_sip_h_Accuvit-User-ID')
    side = hangup_event.getHeader('variable_call-side')
    hangup_cause = hangup_event.getHeader('Hangup-Cause')

    call_key = 'redswitch.{}.{}.{}'.format(org_id, user_id, dial_id)
    state_value = '{}.{}'.format('ACTIVE', side)

    event = CallEvent.hangup(side, hangup_cause)
    asp_esl.redis.publish.assert_called_with(dial_id, event)
    asp_esl.redis.lrem(call_key, 0, state_value)


def test_cmd_hangup_asp(asp_esl):
    call_id = '1337'
    delay = 0

    asp_esl.hangup(call_id, delay=delay)

    asp_esl.client.api.assert_called_with(
        'sched_hangup +{} {} NORMAL_CLEARING'.format(delay, call_id))


def test_cmd_mute_asp(asp_esl):
    barge_id = '1337'
    delay = 0

    asp_esl.mute(barge_id, delay=delay)

    asp_esl.client.api.assert_called_with(
        'sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.MUTE))


def test_cmd_threeway_asp(asp_esl):
    barge_id = '1337'
    delay = 0

    asp_esl.threeway(barge_id, delay=delay)

    asp_esl.client.api.assert_called_with(
        'sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.THREEWAY))


def test_cmd_unthreeway_asp(asp_esl):
    barge_id = '1337'
    delay = 0

    asp_esl.unthreeway(barge_id, delay=delay)

    asp_esl.client.api.assert_called_with(
        'sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.UNTHREEWAY))


def test_cmd_play_asp(asp_esl):
    call_id = '1337'
    path = 'pathtosound'

    asp_esl.play(call_id, path)

    asp_esl.client.api.assert_called_with(
        'sched_broadcast +0 {} {} both'.format(call_id, path))


def test_cmd_whisper_asp(asp_esl):
    barge_id = '1337'
    delay = 0

    asp_esl.whisper(barge_id, delay)

    asp_esl.client.api.assert_called_with(
        'sched_api +{} none uuid_recv_dtmf {} {}'.format(
            delay, barge_id, DTMF.WHISPER))
