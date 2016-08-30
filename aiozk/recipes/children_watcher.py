from tornado import gen
from zoonado import WatchEvent

from .base_watcher import BaseWatcher


class ChildrenWatcher(BaseWatcher):

    watched_event = WatchEvent.CHILDREN_CHANGED

    @gen.coroutine
    def fetch(self, path):
        children = yield self.client.get_children(path=path, watch=True)
        raise gen.Return(children)
