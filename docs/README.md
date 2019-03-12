# Redswitch Autobot Protocol
The following describes how to make calls using freeswitch. For non-ASP calling,
refer to the main readme for ASP.

## Redswitch Jobs

## loadtest job

### loadtest call
This is the start of a more generalized call handling protocol, but it is
currently intended for dialpad load testing.

    {
        "type": "load-test",
        "phone_number": "locadtest endpoint",
        "dial_id": "number of call created",
        "org_id":  "talkiq_org_id",
        "dialpad_crm": "dialpad_crm",
        "leg": "leg number of call"
    }

### bot-call
- Working with Redswitch starts by pushing a Redswitch job onto the
"talkiq-bot.calls" list in redis.
- This will initiate an outbound call.
- When the call is initiated, Redswitch will publish a channel_create event to
a pub/sub channel named after the dial_id.
- The channel_create event will contain a "core_uuid"; this core_uuid is the
location where the human is dialed in.
- All bot calls must be made on the same freeswitch instance using bot-call
callControl message
- bots and humans will not be required to be on the same instance of freeswitch
in future versions.
- unlike asp calls, when a hangup occurs on a leg of a bot call, the other leg
will return to a parked state and must hung up explicitly

    {
        "type": "bot-call",
        "callee_number": "the number of the human you're calling",
        "dial_id": "talkiq_dial_id",
        "org_id":  "talkiq_org_id",
        "user_id": "talkiq_user_id"
    }

#### sip2sip calling
sip2sip calling is mostly the same as a regular calls. simply replace the
callee_number with a sip uri. If authentication is required, additional fields
must be added to the initial request. eg:

    {
        "type": "bot-call",
        "caller_id": caller_id,
        "dial_id": dial_id,
        "org_id": "00Dj0000001noV5EAI",
        "phone_number": callee,
        "user_id": "005j000000C8FKUAA3",
        "auth": "true",
        "sip_auth_username": "test",
        "sip_auth_password": "test-password"
    }

### Call events
- Call events are published to redis channels named after the dial_id used to
create the call.
- To receive call events, simply subscribe to the channel named after the
dial_id you used to initiate the call.
- The developer should subscribe to the dial_id in question before creating a
Redswitch job or a callControl msg to receive events.

#### channel-create

    {
        "type": "channel-create-event",
        "core_uuid": "uuid4 that identifies the asterisk server where the user or bot is",
    }

#### Answer

    {
        "type": "answer-event",
        "side": "call-side",
    }

#### Hangup

    {
       "type": "hangup-event",
       "side": "call-side",
    }

#### call-start
call-start is is published when freeswitch initiates the call

    {
        "type": "call-start",
        "dial_id": <dial_id>
    }

#### Success
Success is published for certain call control events like bridge if success can
be determined by Redswitch.

    {
        "type": "success",
        "event": <the event that suceeded >
    }


### CallControl messages
Call control messages are used to control active calls or create new calls.

Any time a Redswitch call is answered, the responsible instance of Redswitch
becomes a subscriber to a channel named after the dial_id and it awaits call
control messages for the dial_id in question.

Call Events get published as soon as a call is initiated but Redswitch will
only take commands after an "answer-event".

- Dial IDs are implicit !!! they are the channel you're working on!

#### Hangup
Hangups must be published to the dial_id channel you wish to hangup.

    {
       "type": "hangup"
    }

##### bridge
Bridge is used to bridge two dial_ids(calls) together. It should be published to
the core_uuid channel.

    {
        "type": "bridge",
        "dial_id_1": "dial_id",
        "dial_id_2": "dial_id",
    }

#### Barge
Barging creates a new call which allows the barger to listen in on the
specified `dial_id`.

    {
        "type": "barge",
        "phone_number": "15105625882",
        "caller_id": "777-777-7777",
    }


##### Ack
All call control messages respond to acknowledgements as follows.

    {
       "type": "ack",
       "event": "callcontrol_message"
    }

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
`threeway` allows the barger to talk both to the caller and to the callee.

    {
        "type": "threeway",
    }

#### unthreeway
`unthreeway` stops the barger from talking to both the caller and the callee.

    {
        "type": "unthreeway",
    }

####  playbackground music on dial_id
This music is mixed with the ongoing conversation. The loudness of this music is
determined by the wav file. This is untested on remotely hosted audio files.

    {
        "type": "start-background",
        "path": media_path,
    }

#### stop background
The media to be stopped must be specified (this is a requirement of freeswitch)

    {
        "type": "stop-background",
        "path": media_path,
    }
