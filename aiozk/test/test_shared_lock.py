import asyncio
import pytest
from aiozk.exc import TimeoutError


@pytest.mark.asyncio
async def test_shared_lock(zk, path):

    shared = zk.recipes.SharedLock(path)
    got_lock = False
    async with await shared.acquire_write():
        got_lock = True

    assert got_lock

    got_released = False
    async with await shared.acquire_write():
        got_released = True

    assert got_released
    await zk.delete(path)


@pytest.mark.asyncio
async def test_shared_lock_timeout(zk, path):
    got_lock = False
    async with await zk.recipes.SharedLock(path).acquire_write():
        got_lock = True

        with pytest.raises(TimeoutError):
            await zk.recipes.SharedLock(path).acquire_write(timeout=1)

    assert got_lock

    got_released = False
    async with await zk.recipes.SharedLock(path).acquire_write():
        got_released = True

    assert got_released

    await zk.deleteall(path)
