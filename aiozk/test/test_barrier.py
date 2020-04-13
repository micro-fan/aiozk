import asyncio

import pytest


@pytest.mark.asyncio
async def test_barrier(zk, path):
    is_lifted = False
    is_worker_started = asyncio.Future()

    async def start_worker():
        barrier = zk.recipes.Barrier(path)
        is_worker_started.set_result('ok')
        await barrier.wait()
        assert is_lifted == True

    barrier = zk.recipes.Barrier(path)
    await barrier.create()

    worker = asyncio.ensure_future(start_worker())
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
        workers.append(asyncio.ensure_future(start_worker(target)))
    await asyncio.wait(workers)
    await zk.delete(path)


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
