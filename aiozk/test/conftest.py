import asyncio
import os
import uuid

import pytest

from aiozk import ZKClient, exc
from aiozk.states import States


HOST = os.environ.get('ZK_HOST', 'zk')
PORT = os.environ.get('ZK_PORT', '2181')


@pytest.fixture
def servers():
    return f'{HOST}:{PORT}'


def get_client(servers):
    return ZKClient(servers, chroot='/test_aiozk')


async def get_tree(client, curr='/'):
    out = [
        curr,
    ]
    children = await client.get_children(curr)
    for c in children:
        # eliminate double slash: //root = '/'.join('/', 'root')
        if curr == '/':
            curr = ''
        out.extend(await get_tree(client, '/'.join([curr, c])))
    return out


async def dump_tree(client, base='/'):
    out = list(await get_tree(client, base))
    print(f'Tree dump: {out}')
    return out


@pytest.fixture
def path():
    return f'/{uuid.uuid4().hex}'


@pytest.fixture
async def zk(servers):
    c = get_client(servers)
    await c.start()
    if len(await c.get_children('/')):
        await c.deleteall('')
        await c.create('')
    yield c
    try:
        await c.delete('/')
    except exc.NotEmpty:
        await dump_tree(c)
        await c.deleteall('')
        raise
    await c.close()


@pytest.fixture
async def zk2(servers):
    c = get_client(servers)
    await c.start()
    yield c
    await c.close()


@pytest.fixture
def zk_disruptor(zk):
    """
    Force zk reconnect
    """

    async def _force_reconnect():
        conn = zk.session.conn
        await asyncio.sleep(0.2)
        await zk.session.ensure_safe_state()
        await conn.close(1)
        lost = [States.SUSPENDED, States.LOST]
        await zk.session.state.wait_for(*lost)
        await zk.session.ensure_safe_state()

    return _force_reconnect
