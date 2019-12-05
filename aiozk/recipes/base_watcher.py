import asyncio
import collections
import inspect
import logging

from aiozk import WatchEvent, exc

from .recipe import Recipe

log = logging.getLogger(__name__)


def maybe_future(fut, loop):
    if inspect.isawaitable(fut):
        asyncio.ensure_future(fut, loop=loop)


class BaseWatcher(Recipe):

    watched_events = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callbacks = collections.defaultdict(set)
        self.loops = {}

    def add_callback(self, path, callback):
        self.callbacks[path].add(callback)

        if path not in self.loops:
            self.add_watch_loop(path)

    def remove_callback(self, path, callback):
        self.callbacks[path].discard(callback)

        if not self.callbacks[path]:
            self.callbacks.pop(path)
            self.discard_watch_loop(path)

    def add_watch_loop(self, path):
        log.debug('Add new watch loop for %s', path)
        stop_event = asyncio.Event(loop=self.client.loop)
        fut = asyncio.ensure_future(self.watch_loop(path, stop_event), loop=self.client.loop)
        self.loops[path] = (fut, stop_event)

    def discard_watch_loop(self, path):
        log.debug('Discard watch loop of %s', path)
        try:
            fut, stop_event = self.loops.pop(path)
        except KeyError:
            pass
        else:
            stop_event.set()

    async def fetch(self, path):
        raise NotImplementedError

    async def watch_loop(self, path, stop_event):
        async def run_callbacks():
            log.debug('Fetching data for %s', path)
            try:
                result = await self.fetch(path)
            except exc.NoNode:
                result = exc.NoNode
            except exc.ZKError as e:
                log.exception('Exception in watch loop: {}'.format(e))
                log.info('Waiting for safe state...')
                await self.client.session.ensure_safe_state()
                return
            except Exception as e:
                log.exception('Not handled in watch loop: %s', e)
                self.discard_watch_loop(path)
                return

            for callback in self.callbacks[path].copy():
                log.debug('run user callback %s', callback)
                try:
                    maybe_future(callback(result), loop=self.client.loop)
                except Exception as e:
                    log.warning('user watch callback %s raised an unknown exception: %s', callback, e)

            if WatchEvent.CREATED not in self.watched_events and result == exc.NoNode:
                self.discard_watch_loop(path)
                return

        def watch_callback(*args):
            asyncio.ensure_future(run_callbacks(), loop=self.client.loop)

        normalized_path = self.client.normalize_path(path)
        for event_type in self.watched_events:
            self.client.session.add_watch_callback(event_type, normalized_path, watch_callback)
        try:
            watch_callback()
            await stop_event.wait()
        finally:
            for event_type in self.watched_events:
                self.client.session.remove_watch_callback(event_type, normalized_path, watch_callback)
