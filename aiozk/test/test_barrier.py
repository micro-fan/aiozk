import asyncio

from .base import ZKBase


NAME = '/test_barrier'


class TestBarrier(ZKBase):
    async def worker(self):
        barrier = self.c.recipes.Barrier(NAME)
        self.waiting.set_result('ok')
        await barrier.wait()
        self.assertEqual(self.lifted, True)

    async def test_barrier(self):
        self.waiting = asyncio.Future()
        self.lifted = False
        barrier = self.c.recipes.Barrier(NAME)
        await barrier.create()
        worker = asyncio.ensure_future(self.worker())

        r = await self.waiting
        self.assertEqual(r, 'ok')

        self.lifted = True
        await barrier.lift()
        await worker


class TestDoubleBarrier(ZKBase):
    async def worker(self, num, min_workers):
        barrier = self.c.recipes.DoubleBarrier(NAME, min_workers)
        await barrier.enter()
        for i in range(5):
            self.assertGreaterEqual(self.num_workers, min_workers)
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
