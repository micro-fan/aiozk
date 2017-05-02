import asyncio
import uuid

from .base import ZKBase
from ..exc import NoNode


class TestDataWatch(ZKBase):
    async def setUp(self):
        await super().setUp()
        self.path = '/{}'.format(uuid.uuid4().hex)
        await self.c.create(self.path)

    async def tearDown(self):
        await self.c.delete(self.path)
        await super().tearDown()

    async def test_watch(self):
        data = []
        ready = asyncio.Event()
        test_data = b'test' * 1000

        async def data_callback(d):
            data.append(d)
            ready.set()

        watcher = self.c.recipes.DataWatcher()
        watcher.set_client(self.c)
        watcher.add_callback(self.path, data_callback)
        assert data == []
        await self.c.set_data(self.path, test_data)
        await asyncio.wait([ready.wait()], timeout=0.1)
        assert ready.is_set()
        assert data == [test_data]

    async def test_watch_no_node(self):
        watcher = self.c.recipes.DataWatcher()
        watcher.set_client(self.c)
        await self.assertRaises(NoNode, watcher.add_callback, self.path + uuid.uuid4().hex, lambda d: True)


class TestChildrenWatch(ZKBase):
    async def setUp(self):
        await super().setUp()
        self.path = '/{}'.format(uuid.uuid4().hex)
        self.child_1 = '{}/{}'.format(self.path, uuid.uuid4().hex)
        self.child_2 = '{}/{}'.format(self.path, uuid.uuid4().hex)
        await self.c.create(self.path)

    async def tearDown(self):
        try:
            await self.c.delete(self.child_1)
            await self.c.delete(self.child_2)
        except NoNode:
            pass
        await self.c.delete(self.path)
        await super().tearDown()

    async def test_watch(self):
        children = set()
        ready = asyncio.Event()

        async def children_callback(c):
            for child in c:
                children.add(child)
                ready.set()

        watcher = self.c.recipes.ChildrenWatcher()
        watcher.set_client(self.c)
        watcher.add_callback(self.path, children_callback)
        assert children == set()
        await self.c.create(self.child_1)
        await asyncio.wait([ready.wait()], timeout=0.1)
        assert children == {self.child_1.split('/')[-1]}
        ready.clear()
        await self.c.create(self.child_2)
        await asyncio.wait([ready.wait()], timeout=0.1)
        assert ready.is_set()
        assert children == {child.split('/')[-1] for child in (self.child_1, self.child_2)}

    async def test_watch_no_node(self):
        watcher = self.c.recipes.ChildrenWatcher()
        watcher.set_client(self.c)
        await self.assertRaises(NoNode, watcher.add_callback, self.path + uuid.uuid4().hex, lambda d: True)
