import asyncio
import pytest
from aiozk import states
from aiozk.exc import TimeoutError


@pytest.mark.asyncio
async def test_shared_lock(zk, path):

    shared = zk.recipes.SharedLock(path)
    got_lock = False
    async with shared.writer_lock:
        got_lock = True

    assert got_lock

    got_released = False
    async with shared.writer_lock:
        got_released = True

    assert got_released
    await zk.delete(path)


@pytest.mark.asyncio
async def test_shared_lock_timeout(zk, path):
    got_lock = False
    async with zk.recipes.SharedLock(path).writer_lock:
        got_lock = True

        with pytest.raises(TimeoutError):
            shrlock2 = zk.recipes.SharedLock(path)
            await shrlock2.writer_lock.acquire(timeout=1)

    assert got_lock

    got_released = False
    async with zk.recipes.SharedLock(path).writer_lock:
        got_released = True

    assert got_released

    await zk.deleteall(path)


@pytest.mark.asyncio
async def test_multiple_reader_allowed(zk, path):
    WORKERS = 8
    counter = 0
    cond = asyncio.Condition()

    async def start_worker():
        nonlocal counter
        async with zk.recipes.SharedLock(path).reader_lock:
            counter += 1
            async with cond:
                cond.notify()

    async with zk.recipes.SharedLock(path).reader_lock:
        try:
            for _ in range(WORKERS):
                asyncio.create_task(start_worker())
            async with cond:
                await asyncio.wait_for(
                    cond.wait_for(lambda: counter == WORKERS), timeout=2)
        finally:
            await zk.deleteall(path)

    assert counter == WORKERS


@pytest.mark.asyncio
async def test_reader_after_writer(zk, path):
    counter = 0

    async def start_reader_lock():
        nonlocal counter
        async with zk.recipes.SharedLock(path).reader_lock:
            counter += 1
            await asyncio.sleep(2)

    async def start_writer_lock():
        nonlocal counter
        async with zk.recipes.SharedLock(path).writer_lock:
            counter += 1
            await asyncio.sleep(2)

    tasks = []

    tasks.append(asyncio.create_task(start_reader_lock()))
    tasks.append(asyncio.create_task(start_reader_lock()))
    await asyncio.sleep(0.5)
    assert counter == 2
    # it should wait for 2 readers release
    tasks.append(asyncio.create_task(start_writer_lock()))
    await asyncio.sleep(0.5)
    assert counter == 2
    # it should wait for prior writer release
    tasks.append(asyncio.create_task(start_reader_lock()))
    tasks.append(asyncio.create_task(start_reader_lock()))
    await asyncio.sleep(0.5)
    assert counter == 2
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    await zk.deleteall(path)


@pytest.mark.asyncio
async def test_locked(zk, path):
    lock = zk.recipes.SharedLock(path)

    async with lock.reader_lock:
        assert lock.reader_lock.locked()
        assert not lock.writer_lock.locked()

    assert not lock.reader_lock.locked()
    assert not lock.writer_lock.locked()

    async with lock.writer_lock:
        assert lock.writer_lock.locked()
        assert not lock.reader_lock.locked()

    assert not lock.reader_lock.locked()
    assert not lock.writer_lock.locked()

    await zk.delete(path)


@pytest.mark.asyncio
async def test_same_instance_acquire_simultaneously(zk, path):
    """simultaneous .acquire calls of the same instance are not permitted"""
    lock = zk.recipes.SharedLock(path)
    WORKERS = 8
    run_counter = 0
    acquired_counter = 0
    cond = asyncio.Condition()

    async def start_inadequate_task():
        nonlocal run_counter
        nonlocal acquired_counter
        run_counter += 1
        try:
            async with lock.reader_lock:
                acquired_counter += 1
        except Exception:
            pass
        finally:
            async with cond:
                cond.notify()

    async with lock.reader_lock:
        for _ in range(WORKERS):
            asyncio.create_task(start_inadequate_task())

    async with cond:
        await cond.wait_for(lambda: run_counter == WORKERS)

    assert acquired_counter == 0

    await zk.delete(path)


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
    tasks = [task for task in asyncio.all_tasks() if not task.done()]

    print(f'({tag}) waitings={waitings}, len={len(waitings)}')
    print(f'({tag}) tasks={tasks} len={len(tasks)}')

    return waitings, tasks


@pytest.mark.asyncio
async def test_remove_session_loss_handler_after_lock_released(zk, path):
    waitings_orig, tasks_orig = inspect_waiting_loss_handlers(zk, 'original')
    lock = zk.recipes.SharedLock(path)
    async with lock.writer_lock:
        waitings_locking, tasks_locking = inspect_waiting_loss_handlers(
            zk, 'locking')
    # give a shot for tasks related to lock to be cancelled
    await asyncio.sleep(0)
    waitings_released, tasks_released = inspect_waiting_loss_handlers(
        zk, 'released')

    await zk.delete(path)

    assert len(waitings_locking) >= len(waitings_released)
    assert len(waitings_orig) == len(waitings_released)
    assert len(tasks_locking) > len(tasks_released)
    assert len(tasks_orig) == len(tasks_released)
