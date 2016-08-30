from tornado import gen
from zoonado import WatchEvent

from .base_watcher import BaseWatcher


class DataWatcher(BaseWatcher):

    watched_event = WatchEvent.DATA_CHANGED

    @gen.coroutine
    def fetch(self, path):
        data = yield self.client.get_data(path=path, watch=True)
        raise gen.Return(data)
