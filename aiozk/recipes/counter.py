import logging
import asyncio

from aiozk import exc

from .data_watcher import DataWatcher
from .recipe import Recipe


log = logging.getLogger(__name__)


class Counter(Recipe):

    sub_recipes = {
        "watcher": DataWatcher
    }

    def __init__(self, base_path, use_float=False):
        super(Counter, self).__init__(base_path)

        self.value = None

        if use_float:
            self.numeric_type = float
        else:
            self.numeric_type = int

        self.value_sync = self.client.loop.create_future()

    async def start(self):
        self.watcher.add_callback(self.base_path, self.data_callback)
        await asyncio.sleep(0.01, loop=self.client.loop)

        await self.ensure_path()

        raw_value = await self.client.get_data(self.base_path)
        self.value = self.numeric_type(raw_value or 0)

    def data_callback(self, new_value):
        self.value = self.numeric_type(new_value)
        if not self.value_sync.done():
            self.value_sync.set_result(None)
            self.value_sync = self.client.loop.create_future()

    async def set_value(self, value, force=True):
        data = str(value)
        await self.client.set_data(self.base_path, data, force=force)
        log.debug("Set value to '%s': successful", data)
        await self.value_sync

    async def apply_operation(self, operation):
        success = False
        while not success:
            data = str(operation(self.value))
            try:
                await self.client.set_data(self.base_path, data, force=False)
                log.debug("Operation '%s': successful", operation.__name__)
                await self.value_sync
                success = True
            except exc.BadVersion:
                log.debug(
                    "Operation '%s': version mismatch, retrying",
                    operation.__name__
                )
                await self.value_sync

    async def incr(self):

        def increment(value):
            return value + 1

        await self.apply_operation(increment)

    async def decr(self):

        def decrement(value):
            return value - 1

        await self.apply_operation(decrement)

    def stop(self):
        self.watcher.remove_callback(self.base_path, self.data_callback)
