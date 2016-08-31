import asyncio
import logging
import time

from aiozk import exc

from .sequential import SequentialRecipe


log = logging.getLogger(__name__)


class Lease(SequentialRecipe):

    def __init__(self, base_path, limit=1):
        super(Lease, self).__init__(base_path)
        self.limit = limit

    async def obtain(self, duration):
        lessees = await self.client.get_children(self.base_path)

        if len(lessees) >= self.limit:
            return False

        time_limit = time.time() + duration.total_seconds()

        try:
            await self.create_unique_znode("lease", data=str(time_limit))
        except exc.NodeExists:
            log.warn("Lease for %s already obtained.", self.base_path)

        asyncio.call_later(time_limit, asyncio.ensure_future, self.release())
        return True

    async def release(self):
        await self.delete_unique_znode("lease")
