import asyncio
import collections
import inspect
import logging

from aiozk import exc

from .recipe import Recipe


log = logging.getLogger(__name__)


def maybe_future(fut, loop):
    if inspect.isawaitable(fut):
        asyncio.ensure_future(fut, loop=loop)


class BaseWatcher(Recipe):

    watched_events = []

    def __init__(self, *args, **kwargs):
        super(BaseWatcher, self).__init__(*args, **kwargs)
        self.callbacks = collections.defaultdict(set)
        self.loops = {}

    def add_callback(self, path, callback):
        self.callbacks[path].add(callback)

        if path not in self.loops:
            self.loops[path] = asyncio.ensure_future(self.watch_loop(path), loop=self.client.loop)

    def remove_callback(self, path, callback):
        self.callbacks[path].discard(callback)

        if not self.callbacks[path]:
            self.loops.pop(path).cancel()

    async def fetch(self, path):
        raise NotImplementedError

    async def watch_loop(self, path):
        while self.callbacks[path]:
            log.debug("Fetching data for %s", path)
            try:
                result = await self.fetch(path)
            except exc.NoNode:
                for callback in self.callbacks[path]:
                    maybe_future(callback(exc.NoNode), loop=self.client.loop)
                return
            for callback in self.callbacks[path]:
                maybe_future(callback(result), loop=self.client.loop)
            try:
                await self.client.wait_for_events(self.watched_events, path)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print('EXC is: {!r}'.format(e))
                raise
