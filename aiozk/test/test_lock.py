from unittest import mock
import asyncio
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
        await lock.acquire(timeout=2)
        try:
            lock_acquired = True
        finally:
            await lock.release()

    assert not lock_acquired
    assert not lock.owned_paths

    lock2 = zk.recipes.Lock(path)
    try:
        await lock2.acquire(timeout=2)
        try:
            lock_acquired = True
        finally:
            await lock2.release()
    finally:
        await zk.deleteall(path)
    assert lock_acquired


@pytest.mark.asyncio
async def test_acquisition_failure_deadlock(zk, path):
    async with zk.recipes.Lock(path):
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
            await lock2.acquire(timeout=0.5)
            try:
                lock_acquired = True
            finally:
                await lock2.release()

        assert not lock_acquired

    try:
        lock_acquired2 = False
        lock3 = zk.recipes.Lock(path)
        await lock3.acquire(timeout=1)
        try:
            lock_acquired2 = True
        finally:
            await lock3.release()

        assert lock_acquired2
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_timeout_accuracy(zk, path):
    try:
        async with zk.recipes.Lock(path):
            lock2 = zk.recipes.Lock(path)
            analyze_siblings = lock2.analyze_siblings
            lock2.analyze_siblings = mock.AsyncMock()

            async def slow_analyze():
                await asyncio.sleep(0.5)
                return await analyze_siblings()

            lock2.analyze_siblings.side_effect = slow_analyze

            acquired = False
            start = time.perf_counter()
            with pytest.raises(TimeoutError):
                await lock2.acquire(timeout=0.5)
                try:
                    acquired = True
                finally:
                    await lock2.release()

            elapsed = time.perf_counter() - start
    finally:
        await zk.deleteall(path)
    assert not acquired
    assert elapsed < 1


@pytest.mark.asyncio
async def test_acquire_lock(zk, path):
    lock = zk.recipes.Lock(path)
    acquired = False
    try:
        await lock.acquire(timeout=2)
        try:
            acquired = True
            assert acquired
        finally:
            await lock.release()
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_async_context_manager(zk, path):
    acquired = False
    try:
        async with zk.recipes.Lock(path):
            acquired = True
            await asyncio.sleep(1)

        assert acquired
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_async_context_manager_deadlock(zk, path):
    acquired = False
    acquired2 = False
    try:
        async with zk.recipes.Lock(path):
            acquired = True

            lock = zk.recipes.Lock(path)
            with pytest.raises(TimeoutError):
                await lock.acquire(timeout=1)
                try:
                    acquired2 = True
                finally:
                    await lock.release()
    finally:
        await zk.deleteall(path)

    assert acquired
    assert not acquired2


@pytest.mark.asyncio
async def test_async_context_manager_reentrance(zk, path):
    """reentrance is not permitted"""
    lock = zk.recipes.Lock(path)
    acquired = False
    acquired2 = False
    try:
        async with lock:
            acquired = True
            with pytest.raises(RuntimeError):
                await lock.acquire()
                acquired2 = True

        assert acquired
        assert not acquired2
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_async_context_manager_reuse(zk, path):
    lock = zk.recipes.Lock(path)
    acquired = False
    acquired2 = False
    try:
        async with lock:
            acquired = True
            assert lock.locked()
        assert not lock.locked()
        async with lock:
            acquired2 = True
            assert lock.locked()
        assert not lock.locked()
        assert acquired
        assert acquired2
    finally:
        await zk.deleteall(path)


@pytest.mark.asyncio
async def test_async_context_manager_contention(zk, path):
    CONTENDERS = 8
    done = 0
    cond = asyncio.Condition()

    async def create_contender():
        async with zk.recipes.Lock(path):
            async with cond:
                await asyncio.sleep(0.1)
                nonlocal done
                done += 1
                cond.notify()

    for _ in range(CONTENDERS):
        asyncio.create_task(create_contender())

    try:
        async with cond:
            await asyncio.wait_for(cond.wait_for(lambda: done == CONTENDERS),
                                   timeout=2)

        assert CONTENDERS == done
    finally:
        await zk.deleteall(path)
