import asyncio
import logging
import pytest

from aiozk import exc

log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_barrier(zk, path):
    is_lifted = False
    is_worker_started = zk.loop.create_future()

    async def start_worker():
        barrier = zk.recipes.Barrier(path)
        is_worker_started.set_result('ok')
        await barrier.wait()
        assert is_lifted is True

    barrier = zk.recipes.Barrier(path)
    await barrier.create()

    worker = asyncio.ensure_future(start_worker(), loop=zk.loop)
    is_ok = await is_worker_started
    assert is_ok == 'ok'

    is_lifted = True
    await barrier.lift()
    await worker


@pytest.mark.asyncio
async def test_double_barrier(zk, path):
    num_workers = 0
    workers = []

    async def start_worker(min_workers):
        barrier = zk.recipes.DoubleBarrier(path, min_workers)
        await barrier.enter()
        for i in range(5):
            assert num_workers >= min_workers
        await barrier.leave()

    target = 8
    for _ in range(target):
        num_workers += 1
        workers.append(zk.loop.create_task(start_worker(target)))
    await asyncio.wait(workers)
    await zk.delete(path)


@pytest.mark.asyncio
async def test_many_waiters(zk, path):
    """Test for many waiters"""

    WORKER_NUM = 1000
    worker_cnt = 0
    pass_barrier = 0
    cond = asyncio.Condition()

    async def start_worker():
        barrier = zk.recipes.Barrier(path)
        nonlocal worker_cnt
        worker_cnt += 1
        async with cond:
            cond.notify()

        await barrier.wait()

        nonlocal pass_barrier
        pass_barrier += 1
        worker_cnt -= 1
        async with cond:
            cond.notify()

    barrier = zk.recipes.Barrier(path)
    await barrier.create()

    for _ in range(WORKER_NUM):
        asyncio.create_task(start_worker())

    async with cond:
        await cond.wait_for(lambda: worker_cnt == WORKER_NUM)

    await asyncio.sleep(1)
    # Make sure that all workers are blocked at .wait() coroutines. And no one
    # passed beyond the barrier until now.
    assert pass_barrier == 0
    await barrier.lift()

    async def drain():
        async with cond:
            await cond.wait_for(lambda: worker_cnt == 0)

    await asyncio.wait_for(drain(), timeout=5)

    assert pass_barrier == WORKER_NUM


@pytest.mark.asyncio
async def test_wait_before_create(zk, path):
    """await barrier.wait() should finish immediately if the barrier does not
    exist. Because it is semantically right: No barrier, no blocking.
    """
    wait_finished = False

    async def start_worker():
        barrier = zk.recipes.Barrier(path)
        await barrier.wait()
        nonlocal wait_finished
        wait_finished = True

    task = asyncio.create_task(start_worker())

    try:
        await asyncio.wait_for(task, timeout=2)
    except asyncio.TimeoutError:
        pass

    assert wait_finished


@pytest.mark.asyncio
async def test_double_barrier_timeout(zk, path):
    entered = False
    MIN_WORKERS = 10
    barrier = zk.recipes.DoubleBarrier(path, MIN_WORKERS)
    with pytest.raises(exc.TimeoutError):
        await barrier.enter(timeout=0.5)
        entered = True

    assert not entered

    await zk.deleteall(path)


@pytest.mark.asyncio
async def test_double_barrier_enter_leakage(zk, path):
    enter_count = 0
    MIN_WORKERS = 32

    async def start_worker():
        nonlocal enter_count
        barrier = zk.recipes.DoubleBarrier(path, MIN_WORKERS)
        await barrier.enter(timeout=0.5)
        enter_count += 1

    with pytest.raises(exc.TimeoutError):
        await start_worker()

    assert enter_count == 0

    try:
        results = await asyncio.gather(
            *[start_worker() for _ in range(MIN_WORKERS - 1)],
            return_exceptions=True)

        assert all([isinstance(x, exc.TimeoutError) for x in results])
        assert enter_count == 0
        assert len(await zk.get_children(path)) == 0
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_double_barrier_leave_timeout(zk, path):
    MIN_WORKERS = 11

    async def start_first_worker():
        barrier = zk.recipes.DoubleBarrier(path, MIN_WORKERS)
        await barrier.enter()
        # Some of workers won't leave in timeout so timeout exception should be
        # occured
        await barrier.leave(timeout=0.5)

    count = 0

    async def start_worker():
        barrier = zk.recipes.DoubleBarrier(path, MIN_WORKERS)
        await barrier.enter()
        nonlocal count
        count += 1
        await asyncio.sleep(1 - count * 0.1)
        await barrier.leave()

    tasks = []
    first_task = asyncio.create_task(start_first_worker())
    for _ in range(MIN_WORKERS - 1):
        tasks.append(asyncio.create_task(start_worker()))
        # Ensure the order of creation of sequential znodes
        await asyncio.sleep(0.1)

    try:
        with pytest.raises(exc.TimeoutError):
            await first_task
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await zk.deleteall(path)
