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



@pytest.mark.asyncio
async def test_delete_unique_znode_on_timeout(zk, path):
    lock = zk.recipes.SharedLock(path)
    try:
        # timeout -1 here to force a timeout error
        await lock.wait_in_line('write', timeout=-1)
    except TimeoutError:
        pass

    _, contenders = await lock.analyze_siblings()

    # when we have a timeout error the contender must be deleted.
    assert not contenders

    await zk.delete(path)
