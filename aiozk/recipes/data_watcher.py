from aiozk import WatchEvent

from .base_watcher import BaseWatcher


class DataWatcher(BaseWatcher):

    watched_event = WatchEvent.DATA_CHANGED

    async def fetch(self, path):
        data = await self.client.get_data(path=path, watch=True)
        return data
