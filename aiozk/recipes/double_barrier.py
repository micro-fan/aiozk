import logging
import time

from tornado import gen

from zoonado import exc, WatchEvent

from .sequential import SequentialRecipe

log = logging.getLogger(__name__)


class DoubleBarrier(SequentialRecipe):

    def __init__(self, base_path, min_participants):
        super(DoubleBarrier, self).__init__(base_path)
        self.min_participants = min_participants

    @property
    def sentinel_path(self):
        return self.sibling_path("sentinel")

    @gen.coroutine
    def enter(self, timeout=None):
        log.debug("Entering double barrier %s", self.base_path)
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        barrier_lifted = self.client.wait_for_event(
            WatchEvent.CREATED, self.sentinel_path
        )
        if time_limit:
            barrier_lifted = gen.with_timeout(barrier_lifted, time_limit)

        exists = yield self.client.exists(path=self.sentinel_path, watch=True)

        yield self.create_unique_znode("worker")

        _, participants = yield self.analyze_siblings()

        if exists:
            return

        elif len(participants) >= self.min_participants:
            yield self.create_znode(self.sentinel_path)
            return

        try:
            yield barrier_lifted
        except gen.TimeoutError:
            raise exc.TimeoutError

    @gen.coroutine
    def leave(self, timeout=None):
        log.debug("Leaving double barrier %s", self.base_path)
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        owned_positions, participants = yield self.analyze_siblings()
        while len(participants) > 1:
            if owned_positions["worker"] == 0:
                yield self.wait_on_sibling(participants[-1], time_limit)
            else:
                yield self.delete_unique_znode("worker")
                yield self.wait_on_sibling(participants[0], time_limit)

            owned_positions, participants = yield self.analyze_siblings()

        if len(participants) == 1 and "worker" in owned_positions:
            yield self.delete_unique_znode("worker")
            try:
                yield self.client.delete(self.sentinel_path)
            except exc.NoNode:
                pass
