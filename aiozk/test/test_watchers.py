import asyncio
import uuid

import pytest

from ..exc import NoNode


@pytest.fixture
async def data_watcher(zk, path):
    await zk.create(path)
    watcher = zk.recipes.DataWatcher()
    watcher.set_client(zk)
    yield watcher
    watcher.cancel()
    await zk.delete(path)


@pytest.mark.asyncio
async def test_data_watch(zk, path, data_watcher):
    data = []
    ready = asyncio.Event()
    test_data = b'test' * 1000

    async def data_callback(d):
        data.append(d)
        ready.set()

    data_watcher.add_callback(path, data_callback)
    assert data == []
    await zk.set_data(path, test_data)
    await asyncio.wait_for(ready.wait(), timeout=0.1)
    assert ready.is_set()
    assert data == [test_data]
    asyncio.Future()


@pytest.mark.asyncio
async def test_data_watch_no_node(zk, path, data_watcher):
    random_path = path + uuid.uuid4().hex
    is_finished = asyncio.Future()

    async def stub_callback(d):
        assert d == NoNode
        is_finished.set_result(True)

    data_watcher.add_callback(random_path, stub_callback)
    await asyncio.wait_for(is_finished, 0.1)


@pytest.fixture
def child1(path):
    yield f'{path}/{uuid.uuid4().hex}'


@pytest.fixture
def child2(path):
    yield f'{path}/{uuid.uuid4().hex}'


@pytest.fixture
async def child_watcher(zk, path, child1, child2):
    await zk.create(path)
    watcher = zk.recipes.ChildrenWatcher()
    watcher.set_client(zk)
    yield watcher

    watcher.cancel()

    try:
        await zk.delete(child1)
        await zk.delete(child2)
    except NoNode:
        pass
    await zk.delete(path)


@pytest.mark.asyncio
async def test_child_watch(child_watcher, path, zk, child1, child2):
    children = set()
    ready = asyncio.Event()

    async def children_callback(c):
        for child in c:
            children.add(child)
            ready.set()

    child_watcher.add_callback(path, children_callback)
    assert children == set()
    await zk.create(child1)
    await asyncio.wait([ready.wait()], timeout=0.1)
    assert children == {child1.split('/')[-1]}
    ready.clear()
    await zk.create(child2)
    await asyncio.wait([ready.wait()], timeout=0.1)
    assert ready.is_set()
    assert children == {child.split('/')[-1] for child in (child1, child2)}


@pytest.mark.asyncio
async def test_child_watch_no_node(child_watcher, path):
    random_path = path + uuid.uuid4().hex
    is_finished = asyncio.Future()

    async def stub_callback(d):
        assert d == NoNode
        is_finished.set_result(True)

    child_watcher.add_callback(random_path, stub_callback)
    await asyncio.wait_for(is_finished, 0.1)
