import logging

import pytest


def test_asp_initalized(asp_esl):
    assert asp_esl.client.connect.call_count == 1


def test_bot_initialized(bot_esl):
    assert bot_esl.client.connect.call_count == 1


@pytest.mark.parametrize(
    'call_provider, org_id, user_id, dial_id, caller, callee',
    [
        ('switchy', 'org', 'user', '0', '1234', '5678'),
        ('dave', 'org1', 'user1', '42', '9999', '8888'),
    ])
def test_asp_call(mocker, asp_esl, call_provider, org_id, user_id, dial_id,
                  caller, callee):
    asp_esl.call({
        'type': 'asp-call',
        'call_provider': call_provider,
        'callee_number': callee,
        'caller_number': caller,
        'caller_id_lega': callee,
        'caller_id_legb': caller,
        'dial_id': dial_id,
        'org_id': org_id,
        'user_id': user_id,
    })

    asp_esl.client.originate.assert_called_with(
        app_arg_str=('[call-side=1][dial_id={}][sip_h_Accuvit-Dial-Side=1]'
                     'sofia/gateway/flowroute/{}'.format(dial_id, callee)),
        app_name='bridge',
        dest_url=caller,
        dial_id=dial_id,
        gateway='flowroute',
        ignore_early_media='true',
        instant_ringback='true',
        origination_callee_id_number=caller,
        origination_caller_id_number=callee,
        origination_uuid=mocker.ANY,
        uuid_func=mocker.ANY,
        **{
            'call-side': '0',
            'sip_h_Accuvit-Dial-ID': dial_id,
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': org_id,
            'sip_h_Accuvit-User-ID': user_id,
            'sip_h_X-TalkIQ-Callprovider': call_provider,
        })


@pytest.mark.parametrize('org_id, user_id, dial_id, callee, caller_id', [
    ('org1', 'user1', '42', '1111', 'ass'),
    ('org1', 'user1', '42', '1111', 'ass'),
])
def test_bot_call(mocker, org_id, bot_esl, user_id, dial_id, callee,
                  caller_id):
    bot_esl.call({
        'type': 'bot-call',
        'caller_id': caller_id,
        'dial_id': dial_id,
        'org_id': org_id,
        'phone_number': callee,
        'user_id': user_id,
    })

    bot_esl.client.originate.assert_called_with(
        uuid_func=mocker.ANY,
        app_name='park',
        dest_url=callee,
        dial_id=dial_id,
        gateway='flowroute',
        origination_uuid=mocker.ANY,
        **{
            'call-side': '0',
            'ignore_early_media': 'False',
            'park_after_bridge': 'True',
            'origination_caller_id_number': caller_id,
            'sip_h_Accuvit-Dial-ID': dial_id,
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': org_id,
            'sip_h_Accuvit-User-ID': user_id,
            'sip_h_X-TalkIQ-Callprovider': 'auto-bot',
        })


# calls should not be attempted with known bad data, thus we test for an
# originate count of 0 and error logging
# TODO: make this test check that errors are published to redis
@pytest.mark.parametrize('org_id, user_id, dial_id, callee, caller_id', [
    ('org1', 'user1', None, None, None),
    ('org1', 'user1', None, None, 'ass'),
])
def test_bot_call_bad_data(caplog, bot_esl, org_id, user_id, dial_id, callee,
                           caller_id):
    bot_esl.call({
        'type': 'bot-call',
        'caller_id': caller_id,
        'dial_id': dial_id,
        'org_id': org_id,
        'phone_number': callee,
        'user_id': user_id,
    })

    assert bot_esl.client.originate.call_count == 0
    assert 'phone_number' in caplog.text


# tests that sip to sip calling results in a gateway of None
@pytest.mark.parametrize('org_id, user_id, dial_id, callee, caller_id', [
    ('org1', 'user1', '1337', '1@asdfasdfasd', 'asdfasdf'),
    ('org1', 'user1', '1332', 'pub@e', 'ass'),
])
def test_bot_sip2sip(mocker, bot_esl, org_id, user_id, dial_id, callee,
                     caller_id):
    bot_esl.call({
        'type': 'bot-call',
        'caller_id': caller_id,
        'dial_id': dial_id,
        'org_id': org_id,
        'phone_number': callee,
        'user_id': user_id,
    })

    bot_esl.client.originate.assert_called_with(
        uuid_func=mocker.ANY,
        app_name='park',
        dest_url=callee,
        dial_id=dial_id,
        gateway=None,
        origination_uuid=mocker.ANY,
        **{
            'call-side': '0',
            'ignore_early_media': 'False',
            'park_after_bridge': 'True',
            'origination_caller_id_number': caller_id,
            'sip_h_Accuvit-Dial-ID': dial_id,
            'sip_h_Accuvit-Dial-Side': '0',
            'sip_h_Accuvit-Organization-ID': org_id,
            'sip_h_Accuvit-User-ID': user_id,
            'sip_h_X-TalkIQ-Callprovider': 'auto-bot',
        })


@pytest.mark.parametrize(
    'call_provider, org_id, user_id, dial_id, caller, callee',
    [
        ('dave', 'org1', 'user1', '42', None, None),
        ('dave', 'org1', 'user1', '42', '1111', None),
    ])
def test_asp_call_bad_data(caplog, asp_esl, call_provider, org_id, user_id,
                           dial_id, caller, callee):
    caplog.set_level(logging.ERROR)

    asp_esl.call({
        'type': 'asp-call',
        'call_provider': call_provider,
        'callee_number': callee,
        'caller_number': caller,
        'caller_id_lega': callee,
        'caller_id_legb': caller,
        'dial_id': dial_id,
        'org_id': org_id,
        'user_id': user_id,
    })

    assert asp_esl.client.originate.call_count == 0
    assert 'Invalid' in caplog.text
