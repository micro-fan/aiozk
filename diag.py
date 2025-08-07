#!/usr/bin/env python3
import asyncio
import logging.config
import os
import socket
import sys


LOG_ROOT = '.'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stderr,
            'formatter': 'standard',
        },
        'default': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_ROOT, 'default.log'),
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

logging.config.dictConfig(LOGGING)

from aiozk import ZKClient  # noqa


def printe(msg):
    print(msg, file=sys.stderr)
    sys.stderr.flush()


async def main():
    # await asyncio.sleep(10)
    logging.debug('Start')
    zk = ZKClient('zk', session_timeout=3)
    await zk.start()
    while 1:
        try:
            await zk.exists('/zookeeper')
            c = zk.session.conn
            ip = c.host_ip
            logging.debug('DIAG Curr conn: %s', [socket.gethostbyaddr(ip)[0]])
        except Exception as e:
            logging.error('DIAG Exc: %s', e)
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
