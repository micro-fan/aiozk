import asyncio
import logging
import uuid
import pytest

from aiozk import WatchEvent


logging.getLogger('asyncio').setLevel(logging.DEBUG)


@pytest.fixture
async def full_zk(zk, path):
    child_1 = f'{path}/{uuid.uuid4().hex}'
    child_2 = f'{path}/{uuid.uuid4().hex}'
    await zk.create(path)
    await zk.create(child_1)
    await zk.create(child_2)
    yield zk
    await zk.delete(child_2)
    await zk.delete(child_1)
    await zk.delete(path)


@pytest.mark.asyncio
async def test_children(full_zk, path):
    resp = await full_zk.get_children(path)
    assert len(resp) == 2


@pytest.mark.asyncio
async def test_cancel_crash(zk, path):
    async def wait_loop():
        while 1:
            await zk.wait_for_events([WatchEvent.DATA_CHANGED], path)

    f = asyncio.ensure_future(wait_loop())
    f.cancel()
