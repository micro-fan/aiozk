import asyncio
import uuid

from .base import ZKBase


class TestBarrier(ZKBase):
    async def worker(self):
        barrier = self.c.recipes.Barrier(self.path)
        self.waiting.set_result('ok')
        await barrier.wait()
        self.assertEqual(self.lifted, True)

    async def test_barrier(self):
        self.path = '/{}'.format(uuid.uuid4().hex)
        self.waiting = asyncio.Future()
        self.lifted = False
        barrier = self.c.recipes.Barrier(self.path)
        await barrier.create()
        worker = asyncio.ensure_future(self.worker())

        r = await self.waiting
        self.assertEqual(r, 'ok')

        self.lifted = True
        await barrier.lift()
        await worker


class TestDoubleBarrier(ZKBase):
    async def worker(self, min_workers):
        barrier = self.c.recipes.DoubleBarrier(self.path, min_workers)
        await barrier.enter()
        for i in range(5):
            self.assertGreaterEqual(self.num_workers, min_workers)
        await barrier.leave()

    async def test_barrier(self):
        self.path = '/{}'.format(uuid.uuid4().hex)
        self.lifted = False
        self.num_workers = 0
        workers = []
        target = 8
        for _ in range(target):
            self.num_workers += 1
            workers.append(asyncio.ensure_future(self.worker(target)))
        await asyncio.wait(workers)

    async def tearDown(self):
        await self.c.delete(self.path)
        await super().tearDown()
