import asyncio
import logging
import time

from aiozk import exc, WatchEvent

from .sequential import SequentialRecipe

log = logging.getLogger(__name__)


class DoubleBarrier(SequentialRecipe):

    def __init__(self, base_path, min_participants):
        super(DoubleBarrier, self).__init__(base_path)
        self.min_participants = min_participants

    @property
    def sentinel_path(self):
        return self.sibling_path("sentinel")

    async def enter(self, timeout=None):
        log.debug("Entering double barrier %s", self.base_path)
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        barrier_lifted = self.client.wait_for_events(
            [WatchEvent.CREATED], self.sentinel_path
        )

        exists = await self.client.exists(path=self.sentinel_path, watch=True)

        await self.create_unique_znode("worker")

        _, participants = await self.analyze_siblings()

        if exists:
            return

        elif len(participants) >= self.min_participants:
            await self.create_znode(self.sentinel_path)
            return

        try:
            if time_limit:
                await asyncio.wait_for(barrier_lifted, time_limit, loop=self.client.loop)
            else:
                await barrier_lifted
        except asyncio.TimeoutError:
            raise exc.TimeoutError

    async def leave(self, timeout=None):
        log.debug("Leaving double barrier %s", self.base_path)
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        owned_positions, participants = await self.analyze_siblings()
        while len(participants) > 1:
            if owned_positions["worker"] == 0:
                await self.wait_on_sibling(participants[-1], time_limit)
            else:
                await self.delete_unique_znode("worker")
                await self.wait_on_sibling(participants[0], time_limit)

            owned_positions, participants = await self.analyze_siblings()

        if len(participants) == 1 and "worker" in owned_positions:
            await self.delete_unique_znode("worker")
            try:
                await self.client.delete(self.sentinel_path)
            except exc.NoNode:
                pass
