## Redswitch smoke tests
This is probably an abuse of the term "smoke test".

The following describes the manual tests used to verify that redswitch is
working.

The tests are performed using `lpop.py`. `lpop.py` is only used for running
smoke tests and is by no means the only way to do it.

`lpop.py` requires `PUBSUB_REDIS_URL` is set.

### ASP
#### Make call
The following will create a call with a dial_id of "1337" the caller_id will be
displayed to both sides of the call.

    ./lpop.py asp-call <callside1> <callside2>

#### Hangup
The following will hangup a call with the specified dial_id if it is in
progress.

    ./lpop.py hangup <dial_id>

#### Play
The following will play a wav file to both sides of the call:

    ./lpop.py play <dial_id> <file_path>

#### Barge
The following will make a 3rd call which can hear the call of the specified
dial_id.

    ./lpop.py barge <dial_id> <phone_number_of_barger>

#### Whisper
Once a call has been barged, whispering will allow the barger to speak to the
caller specified in the original call.

    ./lpop.py whisper <dial_id>

### Auto-Bot
Because Autobot features are more granular the tests were combined to speed up testing.

Barge and whisper are not currently implemented for autobot calls. **Hangups are
the same as asp calls**

#### Make 2 calls then bridge
The following will cause one call to be made and parked then a second call will
be made and parked 6 seconds later. Then the calls will be bridged 8 seconds
after the creation of the first call.

    ./lpop.py test-bot <core_id> <caller> <callee>

#### Play sound file on parked call
A call will be made to test_phone_number_1 and 15 seconds later,
`welcome-to-freeswitch` will be played on the parked call.

    ./lpop.py test-play <callee>
