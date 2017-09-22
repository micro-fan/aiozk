import asyncio
import os
import uuid

from aiozk import ZKClient, exc  # noqa
from aiozk.states import States
import pytest


HOST = os.environ.get('ZK_HOST', 'zk')


@pytest.fixture
def event_loop(event_loop):
    event_loop.set_debug(True)
    yield event_loop


def get_client():
    return ZKClient(HOST, chroot='/test_aiozk')


async def get_tree(client, curr='/'):
    out = [curr, ]
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
    yield f'/{uuid.uuid4().hex}'


@pytest.fixture
async def zk():
    c = get_client()
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
async def zk2(zk):
    c = get_client()
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
    yield _force_reconnect
