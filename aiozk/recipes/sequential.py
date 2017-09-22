import asyncio
import logging
import re
import uuid

from aiozk import exc, WatchEvent

from .recipe import Recipe


log = logging.getLogger(__name__)

sequential_re = re.compile(r'.*[0-9]{10}$')


class SequentialRecipe(Recipe):

    def __init__(self, base_path):
        super(SequentialRecipe, self).__init__(base_path)
        self.guid = uuid.uuid4().hex

        self.owned_paths = {}

    def sequence_number(self, sibling):
        return int(sibling[-10:])

    def determine_znode_label(self, sibling):
        return sibling.rsplit("-", 2)[0]

    def sibling_path(self, path):
        return "/".join([self.base_path, path])

    async def create_unique_znode(self, znode_label, data=None):
        path = self.sibling_path(znode_label + "-" + self.guid + "-")

        try:
            created_path = await self.client.create(
                path, data=data, ephemeral=True, sequential=True
            )
        except exc.NoNode:
            await self.ensure_path()
            created_path = await self.client.create(
                path, data=data, ephemeral=True, sequential=True
            )

        self.owned_paths[znode_label] = created_path

    async def delete_unique_znode(self, znode_label):
        try:
            await self.client.delete(self.owned_paths[znode_label])
        except exc.NoNode:
            pass

    async def analyze_siblings(self):
        siblings = await self.client.get_children(self.base_path)
        siblings = [name for name in siblings if sequential_re.match(name)]

        siblings.sort(key=self.sequence_number)

        owned_positions = {}

        for index, path in enumerate(siblings):
            if self.guid in path:
                owned_positions[self.determine_znode_label(path)] = index
        return (owned_positions, siblings)

    async def wait_on_sibling(self, sibling, time_limit=None):
        log.debug("Waiting on sibling %s", sibling)

        path = self.sibling_path(sibling)

        unblocked = self.client.wait_for_events([WatchEvent.DELETED], path)

        exists = await self.client.exists(path=path, watch=True)
        if not exists:
            unblocked.set_result(None)

        try:
            if time_limit:
                await asyncio.wait_for(unblocked, time_limit, loop=self.client.loop)
            else:
                await unblocked
        except asyncio.TimeoutError:
            raise exc.TimeoutError
