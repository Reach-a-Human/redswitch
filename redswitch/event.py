import ujson


class CallEvent:
    @staticmethod
    def answer(side):
        return ujson.dumps({
            'type': 'answer-event',
            'side': side,
        })

    @staticmethod
    def call_start(dial_id):
        return ujson.dumps({
            'type': 'call-start',
            'dial_id': dial_id,
        })

    @staticmethod
    def bridge(core, chan1, chan2):
        return ujson.dumps({
            'type': 'bridge-event',
            'chan_uuid1': chan1,
            'chan_uuid2': chan2,
            'core_uuid': core,
        })

    @staticmethod
    def channel_create(core):
        return ujson.dumps({
            'type': 'channel-create-event',
            'core_uuid': core,
        })

    @staticmethod
    def hangup(side, cause):
        return ujson.dumps({
            'type': 'hangup-event',
            'side': side,
            'cause': cause,
        })

    @staticmethod
    def success(event):
        return ujson.dumps({
            'type': 'success',
            'event': event
        })

    @staticmethod
    def failure(event_kind, event):
        return ujson.dumps({
            'type': event_kind,
            'cause': event
        })


class CallResponse:
    @staticmethod
    def get(event):
        return ujson.dumps({
            'type': 'ack',
            'event': event,
        })


class DTMF:
    MUTE = '1'
    WHISPER = '2'
    THREEWAY = '3'
    UNTHREEWAY = '0'
