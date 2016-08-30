import time

from tornado import gen

from zoonado import exc, WatchEvent

from .recipe import Recipe


class Barrier(Recipe):

    def __init__(self, path):
        super(Barrier, self).__init__()
        self.path = path

    @gen.coroutine
    def create(self):
        yield self.ensure_path()

    @gen.coroutine
    def lift(self):
        try:
            self.client.delete(self.path)
        except exc.NoNode:
            pass

    @gen.coroutine
    def wait(self, timeout=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        barrier_lifted = self.client.wait_for_event(
            WatchEvent.DELETED, self.path
        )

        if time_limit:
            barrier_lifted = gen.with_timeout(barrier_lifted, time_limit)

        exists = yield self.client.exists(path=self.path, watch=True)
        if not exists:
            return

        try:
            yield barrier_lifted
        except gen.TimeoutError:
            raise exc.TimeoutError
