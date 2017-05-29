import asyncio
import collections
import logging

from aiozk import exc

from .recipe import Recipe


log = logging.getLogger(__name__)


class BaseWatcher(Recipe):

    watched_event = None

    def __init__(self, *args, **kwargs):
        super(BaseWatcher, self).__init__(*args, **kwargs)
        self.callbacks = collections.defaultdict(set)

    def add_callback(self, path, callback):
        self.callbacks[path].add(callback)

        if len(self.callbacks[path]) == 1:
            asyncio.ensure_future(self.watch_loop(path), loop=self.client.loop)

    def remove_callback(self, path, callback):
        self.callbacks[path].discard(callback)

    async def fetch(self, path):
        raise NotImplementedError

    async def watch_loop(self, path):
        while self.callbacks[path]:
            log.debug("Fetching data for %s", path)
            try:
                result = await self.fetch(path)
            except exc.NoNode:
                return
            for callback in self.callbacks[path]:
                asyncio.ensure_future(callback(result), loop=self.client.loop)
            await self.client.wait_for_event(self.watched_event, path)
