import asyncio
import uuid

import pytest

from .. import WatchEvent
from ..exc import NoNode


@pytest.fixture
async def data_watcher(zk, path):
    await zk.create(path)
    watcher = zk.recipes.DataWatcher()
    watcher.set_client(zk)
    yield watcher
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
    data_watcher.remove_callback(path, data_callback)


@pytest.mark.asyncio
async def test_data_watch_delete(zk, path, data_watcher):
    data = []
    ready = asyncio.Event()
    test_data = b'test'

    async def data_callback(d):
        data.append(d)
        ready.set()

    await zk.set_data(path, test_data)

    data_watcher.add_callback(path, data_callback)
    await asyncio.sleep(0.2)
    assert data == [test_data]
    ready.clear()
    await zk.delete(path)

    await asyncio.wait_for(ready.wait(), timeout=1)
    assert ready.is_set()
    assert data == [test_data, NoNode]
    data_watcher.remove_callback(path, data_callback)

    await zk.create(path)


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
    child_watcher.remove_callback(path, children_callback)


@pytest.mark.asyncio
async def test_child_watch_no_node(child_watcher, path):
    random_path = path + uuid.uuid4().hex
    is_finished = asyncio.Future()

    async def stub_callback(d):
        assert d == NoNode
        is_finished.set_result(True)

    child_watcher.add_callback(random_path, stub_callback)
    await asyncio.wait_for(is_finished, 0.1)


@pytest.mark.asyncio
async def test_reconnect_watcher(data_watcher, path, zk_disruptor, zk, zk2):
    test_data = uuid.uuid4().hex.encode()
    ready = asyncio.Future()

    async def data_callback(d):
        print(f'Data callback get: {d}')
        if d == NoNode:
            return
        if d and not ready.done():
            print(f'Set result: {d} {ready}')
            ready.set_result(d)

    data_watcher.add_callback(path, data_callback)
    await zk_disruptor()
    await zk2.set_data(path, test_data)
    resp = await zk2.get_data(path)
    assert resp == test_data

    data = await asyncio.wait_for(ready, 1)
    assert data == test_data

    data_watcher.remove_callback(path, data_callback)


@pytest.mark.asyncio
async def test_watcher_fires_after_nonode(zk, data_watcher, child1):
    """
    Test that waiting for a nonexistent node is allowed if
    CREATED is in the watched events
    """
    messages = asyncio.Queue()
    data_watcher.watched_events.append(WatchEvent.CREATED)

    async def callback(d):
        print('Callback sees', d)
        await messages.put(d)

    # should trigger fetch right away, getting NoNode
    data_watcher.add_callback(child1, callback)

    no_node = await asyncio.wait_for(messages.get(), 1)
    assert no_node == NoNode

    # should trigger watch, which triggers fetch, which gets 'some data'
    await zk.create(child1, 'some data')
    some_data = await asyncio.wait_for(messages.get(), 1)
    assert some_data == b'some data'

    data_watcher.remove_callback(child1, callback)
    await zk.delete(child1)

@pytest.mark.asyncio
async def test_watcher_without_parents(zk, path, child1):
    """
    Make sure behavior is sane if ancestor node does not exist
    """
    final = f"{child1}/{uuid.uuid4().hex}"
    watcher = zk.recipes.DataWatcher(wait_for_create=True)
    messages = asyncio.Queue()

    async def callback(d):
        print('callback sees', d)
        await messages.put(d)

    watcher.add_callback(final, callback)

    # full path doesn't exist
    no_node = await asyncio.wait_for(messages.get(), 1)
    assert no_node == NoNode

    # create parent, no message should arrive
    await zk.create(path)
    await zk.create(child1)
    assert messages.empty() == True

    # create final node, should get 'howdy'
    await zk.create(final, b'howdy')
    howdy = await asyncio.wait_for(messages.get(), 1)
    assert howdy == b'howdy'

    watcher.remove_callback(final, callback)
    await zk.delete(final)
    await zk.delete(child1)
    await zk.delete(path)
