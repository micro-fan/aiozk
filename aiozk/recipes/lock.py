from aiozk import exc, Deadline

from .base_lock import BaseLock


class Lock(BaseLock):

    async def acquire(self, timeout=None):
        deadline = Deadline(timeout)
        result = None
        while not result:
            try:
                result = await self.wait_in_line("lock", deadline.timeout)
            except exc.SessionLost:
                continue
        return result
