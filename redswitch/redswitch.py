#!/usr/bin/env python3
import asyncio
import logging
import os

from .call_watcher import CallWatcherAsp, CallWatcherBot, CallWatcherLoad
from .esl import ESLAsp, ESLBot, ESLLoad  # pylint: disable=no-name-in-module
from .subscriber import Subscriber

ESL_PASSWORD = os.environ.get('ESL_PASSWORD', 'ClueCon')
ESL_PORT = os.environ.get('ESL_PORT', 8021)
ESL_URL = os.environ.get('ESL_URL', '127.0.0.1')
REDIS_URL = os.environ.get('PUBSUB_REDIS_URL', 'redis://127.0.0.1:6379')
RED_MODE = os.environ.get('RED_MODE', 'default')

def main():
    if RED_MODE == 'default':
        asp_pubsub = Subscriber(REDIS_URL)
        asp_esl = ESLAsp(REDIS_URL, asp_pubsub, ESL_URL, ESL_PORT, ESL_PASSWORD)
        asp_pubsub.set_esl(asp_esl)
        asp_watcher = CallWatcherAsp(REDIS_URL, asp_esl)

        bot_pubsub = Subscriber(REDIS_URL)
        bot_esl = ESLBot(REDIS_URL, bot_pubsub, ESL_URL, ESL_PORT, ESL_PASSWORD)
        bot_pubsub.set_esl(bot_esl)
        bot_watcher = CallWatcherBot(REDIS_URL, bot_esl)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(
            asyncio.ensure_future(asp_watcher.poll()),
            asyncio.ensure_future(asp_pubsub.poll()),
            asyncio.ensure_future(asp_pubsub.do_subscribe()),
            asyncio.ensure_future(bot_watcher.poll()),
            asyncio.ensure_future(bot_pubsub.poll()),
            asyncio.ensure_future(bot_pubsub.do_subscribe()),
        ))

    elif RED_MODE == 'load-test':
        loadtest_pubsub = Subscriber(REDIS_URL)
        loadtest_esl = ESLLoad(REDIS_URL, loadtest_pubsub, ESL_URL, ESL_PORT, ESL_PASSWORD)
        loadtest_pubsub.set_esl(loadtest_esl)
        loadtest_watcher = CallWatcherLoad(REDIS_URL, loadtest_esl)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(
            asyncio.ensure_future(loadtest_watcher.poll()),
            asyncio.ensure_future(loadtest_pubsub.poll()),
            asyncio.ensure_future(loadtest_pubsub.do_subscribe()),
        ))


if __name__ == '__main__':
    logging.getLogger().handlers = []

    log = logging.getLogger('redswitch')
    log.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    FORMAT = ('[%(asctime)s %(filename)-15s:%(lineno)-4s] '
              '%(name)-24s %(levelname)s\t%(message)s')
    ch.setFormatter(logging.Formatter(fmt=FORMAT))
    log.addHandler(ch)

    try:
        main()
    except KeyboardInterrupt:
        pass
