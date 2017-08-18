import asyncio
import uuid

from .base import ZKBase


class TestTreeCache(ZKBase):
    async def setUp(self):
        await super().setUp()
        for attrname in ['basenode', 'node1', 'node2', 'subnode1', 'subnode2', 'subnode3']:
            setattr(self, attrname, uuid.uuid4().hex)
        for attrname in ['data1', 'data2', 'data3']:
            setattr(self, attrname, uuid.uuid4().hex.encode())
        
        self.basepath = '/{}'.format(self.basenode)
        self.path1 = '{}/{}'.format(self.basepath, self.node1)
        self.path2 = '{}/{}'.format(self.basepath, self.node2)
        self.subpath1 = '{}/{}'.format(self.path2, self.subnode1)
        self.subpath2 = '{}/{}'.format(self.path2, self.subnode2)
        self.subpath3 = '{}/{}'.format(self.subpath1, self.subnode3)

        await self.c.create(self.basepath)
        await self.c.create(self.path1, self.data1)
        await self.c.create(self.path2)
        await self.c.create(self.subpath1, self.data2)
        await self.c.create(self.subpath2)
        await self.c.create(self.subpath3, self.data3)

    async def tearDown(self):
        await self.c.deleteall(self.basepath)
        await super().tearDown()

    async def test_cache(self):
        cache = self.c.recipes.TreeCache(self.basenode)
        cache.set_client(self.c)
        await cache.start()

        expected = {
            self.node1: self.data1,
            self.node2: {
                self.subnode1: {
                    self.subnode3: self.data3
                },
                self.subnode2: None
            }
        }

        self.assertDictEqual(cache.as_dict(), expected)
        # we can't see this one in the dict:
        assert getattr(getattr(cache.root, self.node2), self.subnode1).value == self.data2

        newnode = uuid.uuid4().hex
        newdata = [uuid.uuid4().hex.encode() for i in range(3)]

        await self.c.create('{}/{}'.format(self.basepath, newnode), newdata[0]) # add node
        await self.c.set_data(self.path1, newdata[1]) # change data
        await self.c.set_data(self.subpath2, newdata[2]) # set data
        await self.c.delete(self.subpath3) # delete node

        await asyncio.sleep(0.1)

        expected[newnode] = newdata[0]
        expected[self.node1] = newdata[1]
        expected[self.node2][self.subnode2] = newdata[2]
        expected[self.node2][self.subnode1] = self.data2 # this one is now exposed

        self.assertDictEqual(cache.as_dict(), expected)

        await cache.stop()
