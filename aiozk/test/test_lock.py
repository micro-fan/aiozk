import asyncio
import asynctest
import logging
import pytest
import time
import types

from aiozk.exc import TimeoutError
from aiozk.states import States

log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_creation_failure_deadlock(zk, path):
    lock = zk.recipes.Lock(path)
    await lock.ensure_path()

    async def change_state():
        await asyncio.sleep(1)
        zk.session.state.transition_to(States.SUSPENDED)

    zk.session.conn.read_loop_task.cancel()
    zk.session.conn.read_loop_task = None
    # wait for that read loop task is cancelled
    await asyncio.sleep(1)

    asyncio.create_task(change_state())
    lock_acquired = False
    with pytest.raises(TimeoutError):
        # lock is created at zookeeper but response can not be returned because
        # read loop task was cancelled.
        async with await lock.acquire(timeout=2):
            lock_acquired = True

    assert not lock_acquired
    assert not lock.owned_paths

    lock2 = zk.recipes.Lock(path)
    try:
        async with await lock2.acquire(timeout=2):
            lock_acquired = True

        assert lock_acquired
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_acquisition_failure_deadlock(zk, path):
    lock = zk.recipes.Lock(path)
    await lock.ensure_path()

    async with await lock.acquire(timeout=0.5):
        lock2 = zk.recipes.Lock(path)
        await lock2.ensure_path()

        lock2.analyze_siblings_orig = lock2.analyze_siblings
        # analyze_siblings() is called by .wait_in_line()
        async def analyze_siblings_fail(self):
            await self.analyze_siblings_orig()
            raise TimeoutError('fail', 1234)

        lock2.analyze_siblings = types.MethodType(analyze_siblings_fail, lock2)

        lock_acquired = False
        with pytest.raises(TimeoutError):
            async with await lock2.acquire(timeout=0.5):
                lock_acquired = True

        assert not lock_acquired

    try:
        lock3 = zk.recipes.Lock(path)
        await lock.ensure_path()
        lock_acquired2 = False
        async with await lock3.acquire(timeout=0.5):
            lock_acquired2 = True

        assert lock_acquired2
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_timeout_accuracy(zk, path):
    lock = zk.recipes.Lock(path)

    async with await lock.acquire():
        lock2 = zk.recipes.Lock(path)
        analyze_siblings = lock2.analyze_siblings
        lock2.analyze_siblings = asynctest.CoroutineMock()

        async def slow_analyze():
            await asyncio.sleep(0.5)
            return await analyze_siblings()

        lock2.analyze_siblings.side_effect = slow_analyze

        acquired = False
        start = time.perf_counter()
        with pytest.raises(TimeoutError):
            async with await lock2.acquire(timeout=0.5):
                acquired = True

        elapsed = time.perf_counter() - start

    await zk.deleteall(path)

    assert not acquired
    assert elapsed < 1
