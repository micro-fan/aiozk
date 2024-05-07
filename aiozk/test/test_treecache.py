import asyncio
import uuid

import pytest


class Tree:
    def __init__(self, zk, path):
        self.zk = zk
        self.path = path

    async def init(self):
        self.data = {}
        await self.zk.create(self.path)
        for name in ['node1', 'node2']:
            await self.zk.create(f'{self.path}/{name}')
            self.data[name] = {}
            for subname in ['subnode1', 'subnode2']:
                s = uuid.uuid4().hex.encode()
                await self.zk.create(f'{self.path}/{name}/{subname}', s)
                self.data[name][subname] = s

    async def modify(self):
        s = uuid.uuid4().hex
        new_node = f'{self.path}/{s}'
        await self.zk.create(new_node, s)
        self.data[s] = s.encode()

        sn1 = f'{self.path}/node1/subnode1'
        self.data['node1']['subnode1'] = s.encode()
        await self.zk.set_data(sn1, s)

        await self.zk.delete(f'{self.path}/node1/subnode2')
        del self.data['node1']['subnode2']
        await asyncio.sleep(0.1)


@pytest.fixture
async def tree(zk, path):
    out = Tree(zk, path)
    await out.init()
    yield out
    await zk.deleteall(path)


@pytest.fixture
async def tree_cache(zk, path):
    cache = zk.recipes.TreeCache(path)
    cache.set_client(zk)
    await cache.start()
    yield cache
    await cache.stop()


@pytest.mark.asyncio
async def test_tree_cache(zk, tree, tree_cache, path):
    assert tree_cache.as_dict() == tree.data

    td = b'test_data'
    await zk.set_data(f'{path}/node1', td)
    await asyncio.sleep(0.1)
    assert getattr(tree_cache.root, 'node1').value == td

    await tree.modify()
    assert tree_cache.as_dict() == tree.data


@pytest.mark.asyncio
async def test_stop_cachecrash(zk, path):
    cache = zk.recipes.TreeCache(path)
    cache.set_client(zk)
    await cache.start()
    await cache.stop()
    await zk.delete(path)


@pytest.mark.asyncio
async def test_cachecrash_after_delete(zk, path):
    cache = zk.recipes.TreeCache(path)
    cache.set_client(zk)
    await cache.start()
    await zk.delete(path)
    await cache.stop()
