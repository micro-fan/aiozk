from .base import ZKBase


class ClientTest(ZKBase):

    async def test_childs(self):
        await self.c.create('/test')
        await self.c.create('/test/subtest')
        await self.c.create('/test/subtest2')
        c = await self.c.get_children('/test')
        assert len(c) == 2, c
        self.assertSetEqual({'subtest', 'subtest2'}, set(c))
        await self.c.delete('/test/subtest2')
        await self.c.delete('/test/subtest')
        await self.c.delete('/test')
