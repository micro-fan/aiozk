import uuid

from .base import ZKBase


class TestClient(ZKBase):
    async def setUp(self):
        await super().setUp()
        self.path = '/{}'.format(uuid.uuid4().hex)
        self.child_1 = '{}/{}'.format(self.path, uuid.uuid4().hex)
        self.child_2 = '{}/{}'.format(self.path, uuid.uuid4().hex)
        await self.c.create(self.path)
        await self.c.create(self.child_1)
        await self.c.create(self.child_2)

    async def tearDown(self):
        await self.c.delete(self.child_1)
        await self.c.delete(self.child_2)
        await self.c.delete(self.path)
        await super().tearDown()

    async def test_children(self):
        c = await self.c.get_children(self.path)
        assert len(c) == 2, c
