import asyncio
import time

from aiozk import exc, WatchEvent

from .recipe import Recipe


class Barrier(Recipe):

    def __init__(self, path):
        super(Barrier, self).__init__()
        self.path = path

    async def create(self):
        await self.ensure_path()
        await self.create_znode(self.path)

    async def lift(self):
        try:
            await self.client.delete(self.path)
        except exc.NoNode:
            pass

    async def wait(self, timeout=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        barrier_lifted = self.client.wait_for_events(
            [WatchEvent.DELETED], self.path
        )

        exists = await self.client.exists(path=self.path, watch=True)
        if not exists:
            return

        try:
            if time_limit:
                await asyncio.wait_for(barrier_lifted, time_limit, loop=self.client.loop)
            else:
                await barrier_lifted
        except asyncio.TimeoutError:
            raise exc.TimeoutError
