from tornado import gen

from zoonado import exc

from .base_lock import BaseLock


class SharedLock(BaseLock):

    @gen.coroutine
    def acquire_read(self, timeout=None):
        result = None
        while not result:
            try:
                result = yield self.wait_in_line(
                    "read", timeout, blocked_by=("write")
                )
            except exc.SessionLost:
                continue

        raise gen.Return(result)

    @gen.coroutine
    def acquire_write(self, timeout=None):
        result = None
        while not result:
            try:
                result = yield self.wait_in_line("write", timeout)
            except exc.SessionLost:
                continue

        raise gen.Return(result)
