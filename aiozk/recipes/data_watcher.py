from aiozk import WatchEvent

from .base_watcher import BaseWatcher


class DataWatcher(BaseWatcher):

    watched_events = [WatchEvent.DATA_CHANGED, WatchEvent.DELETED]

    async def fetch(self, path):
        data = await self.client.get_data(path=path, watch=True)
        return data
