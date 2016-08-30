import logging
import time

from tornado import gen, ioloop
from zoonado import exc

from .sequential import SequentialRecipe


log = logging.getLogger(__name__)


class Lease(SequentialRecipe):

    def __init__(self, base_path, limit=1):
        super(Lease, self).__init__(base_path)
        self.limit = limit

    @gen.coroutine
    def obtain(self, duration):
        lessees = yield self.client.get_children(self.base_path)

        if len(lessees) >= self.limit:
            raise gen.Return(False)

        time_limit = time.time() + duration.total_seconds()

        try:
            yield self.create_unique_znode("lease", data=str(time_limit))
        except exc.NodeExists:
            log.warn("Lease for %s already obtained.", self.base_path)

        ioloop.IOLoop.current().call_at(time_limit, self.release)

        raise gen.Return(True)

    @gen.coroutine
    def release(self):
        yield self.delete_unique_znode("lease")
