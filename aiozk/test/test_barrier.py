import asyncio

from .base import ZKBase


class TestBarrier(ZKBase):
    async def worker(self):
        barrier = self.c.recipes.Barrier('/test_barrier')
        await barrier.wait()
        while True:
            self.assertEqual(self.lifted, True)
            await asyncio.sleep(0.3)

    async def test_barrier(self):
        self.lifted = False
        barrier = self.c.recipes.Barrier('/test_barrier')
        await barrier.create()
        asyncio.ensure_future(self.worker())
        await asyncio.sleep(0.5)
        await barrier.lift()
        self.lifted = True
        await asyncio.sleep(1)
