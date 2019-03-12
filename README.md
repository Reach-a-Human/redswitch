# Redswitch
Redswitch is a freeswitch ESL agent that recives jobs via Redis to control
Freeswitch.

## Configuration

Redswitch can be configured with the following environment variables:

Name | Description | Default Value
---- | ----------- | -------------
ESL_PASSWORD | Password for ESL connection. | ClueCon
ESL_PORT | Port of ESL server. | 8021
ESL_URL | URL of ESL server. | 127.0.0.1
PUBSUB_REDIS_TIMEOUT | Timeout when connecting to Redis. Integer. | 10
PUBSUB_REDIS_URL | URL to Redis cluster. | redis://127.0.0.1:6379

## Redswitch Jobs
A Redswitch Job is where initial calls begin a job that can be handled by any
instance of Redswitch. Each job directive is associated with a set of expected
responses.

### ASP Call
An asp call is pushed to `talkiq-asp.calls`. Because freeswitch hangs up a
channel when a call fails, the reasons for a failed call are denoted in the
[Hangup-Cause](https://wiki.freeswitch.org/wiki/Hangup_Causes).

    {
        "type": "asp-call",
        "call_provider": "talk_call_provider",
        "callee_number": "1415697098",
        "caller_id_lega": "15105625882",
        "caller_id_legb": "14157697098",
        "caller_number": "15105625882",
        "dial_id": "talkiq_dial_id",
        "org_id":  "talkiq_org_id",
        "user_id": "talkiq_user_id",
    }

### Call Control messages
Call control messages are used to control active Redswitch job. Any time a
redswitch job is answered, the responsible instance of Redswitch becomes a
subscriber to a channel named after the `dial_id` and it awaits call control
messages for the `dial_id` in question.

- Dial IDs are implicit !!! they are are the channel your working on!

#### Hangup

    {
        "type": "hangup"
    }

#### Barge
Barging creates a new call which allows the barger to listen in on the
specified `dial_id`.

    {
        "type": "barge",
        "phone_number": "15105625882",
        "caller_id": "777-777-7777",
    }

#### Whisper
Whisper allows a barger to start talking to the call initiator.

    {
        "type": "whisper",
    }

#### Mute (un-whisper)
Mute causes the barger to return to muted.

    {
        "type": "mute",
    }

#### Threeway
threeway allows the barger to talk both to the caller and to the callee

    {
        "type": "threeway",
    }

#### unthreeway
unthreeway allows the barger to talk both to the caller and to the callee

    {
        "type": "unthreeway",
    }


### Call Events
Call events are events that happen on calls that may not have initiating call
control events.

- side 0: phone of the caller
- side 1: phone of the callee

Dial_ids are still implicit.

#### call-start
call-start is is published when freeswitch initiates the call

    {
        "type": "call-start",
        "dial_id": <dial_id>
    }

#### Hangup

    {
        "type": "hangup-event",
        "side": "call-side",
        "cause": "see https://wiki.freeswitch.org/wiki/Hangup_Causes",
    }

#### Answer

    {
        "type": "answer-event",
        "side": "call-side",
    }

<<<<<<< HEAD
### Whisper
Whisper allows a barger to start talking to the call initiator.

    {
        "type": "whisper",
    }

#### Mute (un-whisper)
Mute causes the barger to return to muted.

    {
        "type": "mute",
    }

#### Threeway
threeway allows the barger to talk both to the caller and to the callee

    {
        "type": "threeway",
    }

#### unthreeway
unthreeway allows the barger to talk both to the caller and to the callee

    {
        "type": "unthreeway",
    }


#### failure
failure  gets published to the dial_id when a call will not even be attempted by freeswitch

    {
        "type": "failure",
        "cause: "the cause of the failure"
    }


### Ack
All call control messages respond to acknowledgements as follows

    {
        "type": "ack",
        "event": "callcontrol_message"
    }

## Active Calls
Redswitch keeps track of all active calls in redis, each active call is
represented as a list with the fallowing format.

    redswitch.<dial_id>.<org_id>.<user_id>

each value of the list represents a call side in the following format

    <state>.<side>

 - Currently the only state is 'ACTIVE'
 - When a side is hung up, the list item is removed
 - Active calls expire after 24hrs

## Event history
Redsiwitch tracks the event history hisetory of active calls on a per user baises the list is formated as fallows

    redswitch_history.<org_id>.<user_id>
 - List Values are identical to redswitch events
 - Event history is deleted at the start of every new call
 - Event historys expire after 4 hrs

## Local Dev
Redswitch requires an accessible Redis cluster and a Freeswitch instance.

The `talkiq/redis` library can be used for the former:

    cd /path/to/talkiq/redis
    docker-compose up -d

You can connect a local `redswitch` to the above network and a test Freeswitch
instance with

    docker build -t redswitch .
    docker run --rm --name redswitch --net redis_default -it \
        -e PUBSUB_REDIS_URL=redis://node0:6379 \
        -e ESL_URL=174.36.124.235 \
        -e ESL_PASSWORD=ClueCon \
        -v ${PWD}/redswitch:/src \
        -v ${PWD}/tester:/opt/sensu/service/vader-tester \
        redswitch

You can verify your connections to Redis and Freeswitch with

    docker exec redswitch /opt/sensu/service/vader-tester/esl.py
    docker exec redswitch /opt/sensu/service/vader-tester/redis.py

You can run `lpop.py` against it to send test commands with

    docker exec redswitch /src/lpop.py --help
