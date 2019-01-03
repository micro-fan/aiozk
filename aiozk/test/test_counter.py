import asyncio
import logging

import pytest

from ..recipes.counter import Counter  # noqa


async def _simple_helper(zk, path, val):
    counter = zk.recipes.Counter(path, default=val)
    await counter.start()
    _type = type(val)
    assert counter.value == val
    assert type(counter.value) == _type
    for _i in range(4):
        await counter.incr()
    await zk.delete(path)
    counter.stop()
    assert counter.value == 4


@pytest.mark.asyncio
async def test_counter_simple_int(zk, path):
    await _simple_helper(zk, path, 0)


@pytest.mark.asyncio
async def test_counter_simple_float(zk, path):
    await _simple_helper(zk, path, 0.0)


@pytest.mark.asyncio
async def test_counter_multiple(zk, path):
    async def worker():
        c = zk.recipes.Counter(path)
        await c.start()
        await c.incr()

    workers = []
    for _i in range(5):
        workers.append(worker())

    done, _pending = await asyncio.wait(workers)
    assert len(done) == 5  # sanity check
    data, stat = await zk.get(path)
    await zk.delete(path)
    assert int(data) == 5
    assert stat.version == 5


@pytest.mark.asyncio
async def test_counter_single_reused(zk, path):
    counter = zk.recipes.Counter(path)
    await counter.start()

    async def worker():
        await counter.incr()

    workers = []
    for _i in range(5):
        workers.append(worker())

    done, _pending = await asyncio.wait(workers)
    assert len(done) == 5
    val = await counter.get_value()
    await zk.delete(path)
    assert val == 5
