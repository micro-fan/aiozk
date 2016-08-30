import collections
import logging

from tornado import ioloop, gen

from zoonado import exc

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
            ioloop.IOLoop.current().add_callback(self.watch_loop, path)

    def remove_callback(self, path, callback):
        self.callbacks[path].discard(callback)

    @gen.coroutine
    def fetch(self, path):
        raise NotImplementedError

    @gen.coroutine
    def watch_loop(self, path):
        while self.callbacks[path]:
            wait = self.client.wait_for_event(self.watched_event, path)

            log.debug("Fetching data for %s", path)
            try:
                result = yield self.fetch(path)
            except exc.NoNode:
                return

            yield wait

            for callback in self.callbacks[path]:
                ioloop.IOLoop.current().add_callback(callback, result)
