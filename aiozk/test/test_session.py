import unittest
from unittest import mock

import asynctest
from aiozk import session


class TestSession(asynctest.TestCase):

    def setUp(self):
        self.fake_retry_policy = mock.MagicMock()
        self.fake_loop = mock.MagicMock()
        self.session = session.Session('zookeeper.test', 10, self.fake_retry_policy, True, 30, loop=self.fake_loop)

    async def test_start_session_twice(self):
        with mock.patch.object(self.session, 'ensure_safe_state', asynctest.CoroutineMock()) as ensure_safe_state:
            await self.session.start()
            await self.session.start()

            self.fake_loop.call_soon.assert_called_once()
            self.fake_loop.create_task.assert_called_once()
            ensure_safe_state.assert_called_once()
