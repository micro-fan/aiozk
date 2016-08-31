from aiozk import exc

from .base_lock import BaseLock


class SharedLock(BaseLock):

    async def acquire_read(self, timeout=None):
        result = None
        while not result:
            try:
                result = await self.wait_in_line(
                    "read", timeout, blocked_by=("write")
                )
            except exc.SessionLost:
                continue
        return result

    async def acquire_write(self, timeout=None):
        result = None
        while not result:
            try:
                result = await self.wait_in_line("write", timeout)
            except exc.SessionLost:
                continue
        return result
