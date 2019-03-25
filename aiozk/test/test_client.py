import asyncio
import logging
import uuid
import pytest

from aiozk import WatchEvent
from .conftest import get_client


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


@pytest.mark.asyncio
async def test_closed_close():
    zk = get_client()
    await asyncio.wait_for(zk.session.close(), 2)



@pytest.mark.asyncio
async def test_inconsistent_zxid():
    async def coro():
        zk = get_client()
        await zk.start()
        # simulate failed connection
        await zk.session.close()
        zk.session.last_zxid = 1231231241312312
        await zk.session.start()
        await zk.session.close()
    try:
        await asyncio.wait_for(coro(), timeout=10)
    except asyncio.TimeoutError as exc:
        pytest.fail("Failed with timeout on session reconnection attemt")


@pytest.mark.asyncio
async def test_session_reconnect():
    async def coro():
        zk = get_client()
        await zk.start()
        await zk.session.close()
        await zk.session.start()
        await zk.session.close()
    try:
        await asyncio.wait_for(coro(), timeout=10)
    except asyncio.TimeoutError as exc:
        pytest.fail("Failed with timeout on session reconnection attemt")


@pytest.mark.asyncio
async def test_raw_get(full_zk, path):
    # type: (aiozk.ZKClient, str) -> None
    """Test that get returns data + stat"""
    data, stat = await full_zk.get(path)
    assert data is None
    assert stat.version == 0

@pytest.mark.asyncio
async def test_raw_set(full_zk, path):
    # type: (aiozk.ZKClent, str) -> None
    """Test that raw set returns Stat"""
    stat = await full_zk.set(path, 'asdf', -1)
    assert stat.data_length == 4
    assert stat.version == 1