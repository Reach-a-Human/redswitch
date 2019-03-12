#!/usr/bin/env python3
"""lpop.py

Usage:
    lpop.py asp-call <caller>
    lpop.py bot-call <dial_id> <phone_number> <caller_id>
    lpop.py load-test <dial_id>
    lpop.py bot-call-leg-2 <core_id> <dial_id> <phone_number> <caller_id>
    lpop.py barge <dial_id> <phone_number> <caller_id>
    lpop.py bridge <core_id> <dial_id1> <dial_id2>
    lpop.py hangup <dial_id>
    lpop.py mute <dial_id>
    lpop.py threeway <dial_id>
    lpop.py unthreeway <dial_id>
    lpop.py play <dial_id> <media_path>
    lpop.py play-now <dial_id> <media_path>
    lpop.py whisper <dial_id>
    lpop.py test-bot <core_id> <caller> <callee>
    lpop.py test-bot-broken <core_id> <caller> <callee>
    lpop.py test-play <callee> <caller_id>
    lpop.py stop-playback <dial_id>
    lpop.py start-background <dial_id> <media_path>
    lpop.py stop-background <dial_id> <media_path>

"""
import asyncio
import os

import aredis
import docopt
import ujson

from .utils import parse_redis_url


REDIS_URL = os.environ.get('PUBSUB_REDIS_URL', 'redis://127.0.0.1:6379')


def asp_call(callee, caller):
    return ujson.dumps({
        'type': 'asp-call',
        'call_provider': 'shifty',
        'callee_number': callee,
        'caller_number': caller,
        'caller_id_lega': callee,
        'caller_id_legb': caller,
        'dial_id': '1337',
        'org_id': '00Dj0000001noV5EAI',
        'user_id': '005j000000C8FKUAA3',
    })


def barge(phone_number, caller_id):
    return ujson.dumps({
        'type': 'barge',
        'caller_id': caller_id,
        'phone_number': phone_number,
    })


def bot_call(dial_id, callee, caller_id):
    return ujson.dumps({
        'type': 'bot-call',
        'caller_id': caller_id,
        'dial_id': dial_id,
        'org_id': '00Dj0000001noV5EAI',
        'phone_number': callee,
        'user_id': '005j000000C8FKUAA3',
    })


def load_call(dial_id):
    return ujson.dumps({
        'type': 'load-test',
        'caller_id': '111111111',
        'dial_id': dial_id,
        'org_id': '00Dj0000001noV5EAI',
        'phone_number': dial_id,
        'dialpad_crm': 'dialpad-crm-insert',
        'leg': '1', #remember your going to automate the chainging of the leg number
        'parent_callid': 'parent-call-id-insert', # your going to need to automate this
        'callee_name': dial_id,
        'target_key': 'target-key',
        'topic': 'loadtesting',
        'gateway': 'dialpad-loadtest',
    })

def bot_call_sip_auth(dial_id, callee, caller_id):
    return ujson.dumps({
        'type': 'bot-call',
        'caller_id': caller_id,
        'dial_id': dial_id,
        'org_id': '00Dj0000001noV5EAI',
        'phone_number': callee,
        'user_id': '005j000000C8FKUAA3',
        'auth': 'true',
        'sip_auth_username': 'test',
        'sip_auth_password': 'test-password'
    })



def bridge(dial_id1, dial_id2):
    return ujson.dumps({
        'type': 'bridge',
        'dial_id1': dial_id1,
        'dial_id2': dial_id2,
    })


def stop_playback():
    return ujson.dumps({
        'type': 'stop-playback',
    })


def hangup():
    return ujson.dumps({'type': 'hangup'})


def mute():
    return ujson.dumps({'type': 'mute'})


def threeway():
    return ujson.dumps({'type': 'threeway'})


def un_threeway():
    return ujson.dumps({'type': 'unthreeway'})


def play(media_path):
    return ujson.dumps({
        'type': 'play',
        'path': media_path,
    })


def play_now(media_path):
    return ujson.dumps({
        'type': 'play-now',
        'path': media_path,
    })


def start_background(media_path):
    return ujson.dumps({
        'type': 'start-background',
        'path': media_path,
    })


def stop_background(media_path):
    return ujson.dumps({
        'type': 'stop-background',
        'path': media_path,
    })


def whisper():
    return ujson.dumps({'type': 'whisper'})


async def main():
    # pylint: disable=too-many-branches,too-many-statements
    args = docopt.docopt(__doc__)

    host, port, password = parse_redis_url(REDIS_URL)
    r = aredis.StrictRedisCluster(host=host, port=port, password=password)

    if args['asp-call']:
        job = asp_call('16057819836', args['<caller>'])
        await r.rpush('talkiq-asp.calls', job)

    if args['load-test']:
        job = load_call(args['<dial_id>'])
        await r.rpush('talkiq-load.calls', job)

    if args['bot-call']:
        job = bot_call(args['<dial_id>'], args['<phone_number>'],
                       args['<caller_id>'])
        await r.rpush('talkiq-bot.calls', job)

    if args['bot-call-leg-2']:
        job = bot_call(args['<dial_id>'], args['<phone_number>'],
                       args['<caller_id>'])
        await r.publish(args['<core_id>'], job)

    if args['barge']:
        job = barge(args['<phone_number>'], args['<caller_id>'])
        await r.publish(args['<dial_id>'], job)

    if args['bridge']:
        job = bridge(args['<dial_id1>'], args['<dial_id2>'])
        await r.publish(args['<core_id>'], job)

    if args['hangup']:
        job = hangup()
        await r.publish(args['<dial_id>'], job)

    if args['stop-playback']:
        job = stop_playback()
        await r.publish(args['<dial_id>'], job)

    if args['mute']:
        job = mute()
        await r.publish(args['<dial_id>'], job)

    if args['threeway']:
        job = threeway()
        await r.publish(args['<dial_id>'], job)

    if args['unthreeway']:
        job = un_threeway()
        await r.publish(args['<dial_id>'], job)

    if args['play']:
        job = play(args['<media_path>'])
        await r.publish(args['<dial_id>'], job)

    if args['play-now']:
        job = play_now(args['<media_path>'])
        await r.publish(args['<dial_id>'], job)

    if args['whisper']:
        job = whisper()
        await r.publish(args['<dial_id>'], job)

    if args['test-bot']:
        dial_id1 = '1337'
        dial_id2 = '1332'

        print('calling {}'.format(args['<caller>']))
        job = bot_call(dial_id1, args['<caller>'], args['<callee>'])
        await r.rpush('talkiq-bot.calls', job)

        await asyncio.sleep(6)

        print('calling {}'.format(args['<callee>']))
        job = bot_call(dial_id2, args['<callee>'], args['<caller>'])
        await r.rpush('talkiq-bot.calls', job)

        await asyncio.sleep(8)

        print('bridging')
        job = bridge(dial_id1, dial_id2)
        await r.publish(args['<core_id>'], job)


    if args['test-bot-broken']:
        dial_id1 = '1337'
        dial_id2 = '1332'

        print('calling {}'.format(args['<caller>']))
        job = bot_call(dial_id1, args['<caller>'], args['<callee>'])
        await r.rpush('talkiq-bot.calls', job)

        await asyncio.sleep(6)

        print('calling {}'.format(args['<callee>']))
        job = bot_call(dial_id2, args['<callee>'], args['<caller>'])
        await r.rpush('talkiq-bot.calls', job)

        await asyncio.sleep(8)

        print('bridging')
        job = bridge(dial_id1, '1992')
        await r.publish(args['<core_id>'], job)

    if args['test-play']:
        dial_id = '1337'

        print('calling {}'.format(args['<callee>']))
        job = bot_call(dial_id, args['<callee>'], args['<caller_id>'])
        await r.rpush('talkiq-bot.calls', job)

        await asyncio.sleep(15)

        print('playing')
        job = play('ivr/ivr-welcome_to_freeswitch.wav')
        await r.publish(dial_id, job)

    print('done')

    if args['start-background']:
        job = start_background('ivr/ivr-welcome_to_freeswitch.wav')
        await r.publish(args['<dial_id>'], job)

        print('done')

    if args['stop-background']:
        job = stop_background('ivr/ivr-welcome_to_freeswitch.wav')
        await r.publish(args['<dial_id>'], job)

        print('done')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
