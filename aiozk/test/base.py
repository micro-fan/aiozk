from aiozk import ZKClient
from .aio_test import AIOTestCase


class ZKBase(AIOTestCase):
    async def setUp(self):
        self.c = ZKClient('localhost', chroot='/test_aiozk')
        await self.c.start()

    async def tearDown(self):
        await self.c.delete('/')
        await self.c.close()
