import os

from aiozk import ZKClient, exc
from .aio_test import AIOTestCase

HOST = os.environ.get('ZK_HOST', 'zk')


class ZKBase(AIOTestCase):
    async def client(self):
        c = ZKClient(HOST, chroot='/test_aiozk')
        await c.start()
        self.clients.append(c)
        return c

    async def setUp(self):
        self.clients = []
        self.c = ZKClient(HOST, chroot='/test_aiozk')
        await self.c.start()
        if len(await self.c.get_children('/')) > 0:
            await self.c.deleteall('')
            await self.c.create('')

    async def tearDown(self):
        for c in self.clients:
            await c.close()
        try:
            await self.c.delete('/')
        except exc.NotEmpty:
            await self.dump_tree()
            await self.c.deleteall('')
        await self.c.close()

    async def dump_tree(self, base='/'):
        out = list(await self.get_tree(base))
        print('Tree dump: {}'.format(out))
        return out

    async def get_tree(self, curr='/'):
        out = [curr, ]
        children = await self.c.get_children(curr)
        for c in children:
            # eliminate double slash: //root = '/'.join('/', 'root')
            if curr == '/':
                curr = ''
            out.extend(await self.get_tree('/'.join([curr, c])))
        return out
