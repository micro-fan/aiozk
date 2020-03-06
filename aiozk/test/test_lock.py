import asyncio
import logging
import pytest
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
