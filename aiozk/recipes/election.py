import asyncio

from .sequential import SequentialRecipe


class LeaderElection(SequentialRecipe):

    def __init__(self, base_path):
        super().__init__(base_path)
        self.has_leadership = False

        self.leadership_future = self.client.loop.create_future()

    async def join(self):
        await self.create_unique_znode("candidate")
        await self.check_position()

    async def check_position(self, _=None):
        owned_positions, candidates = await self.analyze_siblings()
        if "candidate" not in owned_positions:
            return

        position = owned_positions["candidate"]

        self.has_leadership = bool(position == 0)

        if self.has_leadership:
            self.leadership_future.set_result(None)
            return

        await self.wait_on_sibling(candidates[position - 1])
        asyncio.ensure_future(self.check_position(), loop=self.client.loop)

    async def wait_for_leadership(self, timeout=None):
        if self.has_leadership:
            return

        if timeout:
            await asyncio.wait_for(self.leadership_future, timeout)
        else:
            await self.leadership_future

    async def resign(self):
        await self.delete_unique_znode("candidate")
