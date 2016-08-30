import contextlib
import logging
import time

from tornado import gen, ioloop

from zoonado import exc, states

from .sequential import SequentialRecipe


log = logging.getLogger(__name__)


class BaseLock(SequentialRecipe):

    @gen.coroutine
    def wait_in_line(self, znode_label, timeout=None, blocked_by=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        yield self.create_unique_znode(znode_label)

        while True:
            if time_limit and time.time() >= time_limit:
                raise exc.TimeoutError

            owned_positions, contenders = yield self.analyze_siblings()
            if znode_label not in owned_positions:
                raise exc.SessionLost

            blockers = contenders[:owned_positions[znode_label]]
            if blocked_by:
                blockers = [
                    contender for contender in blockers
                    if self.determine_znode_label(contender) in blocked_by
                ]

            if not blockers:
                break

            yield self.wait_on_sibling(blockers[-1], time_limit)

        raise gen.Return(self.make_contextmanager(znode_label))

    def make_contextmanager(self, znode_label):
        state = {"acquired": True}

        def still_acquired():
            return state["acquired"]

        @gen.coroutine
        def handle_session_loss():
            yield self.client.session.state.wait_for(states.States.LOST)
            if not state["acquired"]:
                return

            log.warn(
                "Session expired at some point, lock %s no longer acquired.",
                self
            )
            state["acquired"] = False

        ioloop.IOLoop.current().add_callback(handle_session_loss)

        @gen.coroutine
        def on_exit():
            state["acquired"] = False
            yield self.delete_unique_znode(znode_label)

        @contextlib.contextmanager
        def context_manager():
            try:
                yield still_acquired
            finally:
                ioloop.IOLoop.current().add_callback(on_exit)

        return context_manager()


class LockLostError(exc.ZKError):
    pass
