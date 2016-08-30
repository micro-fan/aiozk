import time

from tornado import gen, ioloop, concurrent

from .sequential import SequentialRecipe


class LeaderElection(SequentialRecipe):

    def __init__(self, base_path):
        super(LeaderElection, self).__init__(base_path)
        self.has_leadership = False

        self.leadership_future = concurrent.Future()

    @gen.coroutine
    def join(self):
        yield self.create_unique_znode("candidate")
        yield self.check_position()

    @gen.coroutine
    def check_position(self, _=None):
        owned_positions, candidates = yield self.analyze_siblings()
        if "candidate" not in owned_positions:
            return

        position = owned_positions["candidate"]

        self.has_leadership = bool(position == 0)

        if self.has_leadership:
            self.leadership_future.set_result(None)
            return

        moved_up = self.wait_on_sibling(candidates[position - 1])

        ioloop.IOLoop.current().add_future(moved_up, self.check_position)

    @gen.coroutine
    def wait_for_leadership(self, timeout=None):
        if self.has_leadership:
            return

        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        if time_limit:
            yield gen.with_timeout(self.leadership_future, time_limit)
        else:
            yield self.leadership_future

    @gen.coroutine
    def resign(self):
        yield self.delete_unique_znode("candidate")
