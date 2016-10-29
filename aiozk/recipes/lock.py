from aiozk import exc

from .base_lock import BaseLock


class Lock(BaseLock):

    async def acquire(self, timeout=None):
        result = None
        while not result:
            try:
                result = await self.wait_in_line("lock", timeout)
            except exc.SessionLost:
                continue
        return result
