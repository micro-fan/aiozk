import asyncio
import pytest
from aiozk import states
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


def inspect_waiting_loss_handlers(zk, tag):
    waitings = zk.session.state.waitings(
        states.States.LOST)[states.States.LOST]
    tasks = [task for task in asyncio.Task.all_tasks() if not task.done()]

    print(f'({tag}) waitings={waitings}, len={len(waitings)}')
    print(f'({tag}) tasks={tasks} len={len(tasks)}')

    return waitings, tasks


@pytest.mark.asyncio
async def test_remove_session_loss_handler_after_lock_released(zk, path):
    waitings_orig, tasks_orig = inspect_waiting_loss_handlers(zk, 'original')
    lock = zk.recipes.SharedLock(path)
    async with await lock.acquire_write():
        waitings_locking, tasks_locking = inspect_waiting_loss_handlers(
            zk, 'locking')

    waitings_released, tasks_released = inspect_waiting_loss_handlers(
        zk, 'released')

    assert len(waitings_locking) > len(waitings_released)
    assert len(waitings_orig) == len(waitings_released)
    assert len(tasks_locking) > len(tasks_released)
    assert len(tasks_orig) == len(tasks_released)

    await zk.delete(path)
