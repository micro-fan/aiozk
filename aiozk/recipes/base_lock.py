import asyncio
import logging
import time

from aiozk import exc, states

from .sequential import SequentialRecipe

log = logging.getLogger(__name__)


class BaseLock(SequentialRecipe):
    async def wait_in_line(self, znode_label, timeout=None, blocked_by=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        await self.create_unique_znode(znode_label)

        while True:
            if time_limit and time.time() >= time_limit:
                await self.delete_unique_znode(znode_label)
                raise exc.TimeoutError

            owned_positions, contenders = await self.analyze_siblings()
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

            try:
                await self.wait_on_sibling(blockers[-1], timeout)
            except exc.TimeoutError:
                await self.delete_unique_znode(znode_label)

        return self.make_contextmanager(znode_label)

    def make_contextmanager(self, znode_label):
        state = {"acquired": True}

        def still_acquired():
            return state["acquired"]

        state_fut = self.client.session.state.wait_for(states.States.LOST)

        async def handle_session_loss():
            await state_fut
            if not state["acquired"]:
                return

            log.warning(
                "Session expired at some point, lock %s no longer acquired.",
                self)
            state["acquired"] = False

        fut = asyncio.ensure_future(handle_session_loss(),
                                    loop=self.client.loop)

        async def on_exit():
            state["acquired"] = False
            if not fut.done():
                if not state_fut.done():
                    self.client.session.state.remove_waiting(
                        state_fut, states.States.LOST)
                fut.cancel()

            await self.delete_unique_znode(znode_label)

        class Lock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                await on_exit()

        return Lock()


class LockLostError(exc.ZKError):
    pass
