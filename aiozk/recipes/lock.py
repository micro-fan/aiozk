from tornado import gen

from zoonado import exc

from .base_lock import BaseLock


class Lock(BaseLock):

    @gen.coroutine
    def acquire(self, timeout=None):
        result = None
        while not result:
            try:
                result = yield self.wait_in_line("lock", timeout)
            except exc.SessionLost:
                continue

        raise gen.Return(result)
