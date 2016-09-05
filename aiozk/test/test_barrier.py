import asyncio

from .base import ZKBase


NAME = '/test_barrier'


class TestBarrier(ZKBase):
    async def worker(self):
        barrier = self.c.recipes.Barrier(NAME)
        await barrier.wait()
        while True:
            self.assertEqual(self.lifted, True)
            await asyncio.sleep(0.3)

    async def test_barrier(self):
        self.lifted = False
        barrier = self.c.recipes.Barrier(NAME)
        await barrier.create()
        asyncio.ensure_future(self.worker())
        await asyncio.sleep(0.05)
        await barrier.lift()
        self.lifted = True
        await asyncio.sleep(0.1)


class TestDoubleBarrier(ZKBase):
    async def worker(self, num, min_workers):
        c = await self.client()
        barrier = c.recipes.DoubleBarrier(NAME, min_workers)

        await asyncio.sleep(0.01*num)
        await barrier.enter()
        for i in range(5):
            self.assertGreaterEqual(self.num_workers, min_workers)
            await asyncio.sleep(0.01*num)
        await barrier.leave()

    async def test_barrier(self):
        self.lifted = False
        self.num_workers = 0
        workers = []
        target = 8
        for x in range(target):
            self.num_workers += 1
            workers.append(asyncio.ensure_future(self.worker(x, target)))
        await asyncio.wait(workers)

    async def tearDown(self):
        await self.c.delete(NAME)
        await super().tearDown()
