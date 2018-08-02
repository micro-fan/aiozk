import asyncio
from unittest import mock

import aiozk

import pytest


@pytest.fixture
def session():
    fake_retry_policy = mock.MagicMock()
    fake_loop = mock.MagicMock()
    return aiozk.session.Session('zookeeper.test', 10, fake_retry_policy, True, 30, loop=fake_loop)


@pytest.mark.asyncio
async def test_start_session_twice(session):
    ensure_safe_state = mock.Mock()
    with mock.patch.object(session, 'ensure_safe_state', asyncio.coroutine(ensure_safe_state)):
        await session.start()
        ensure_safe_state.assert_called_once_with()
        ensure_safe_state.reset_mock()
        await session.start()
        ensure_safe_state.assert_called_once_with()

        session.loop.call_soon.assert_called_once()
        session.loop.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_close_not_started(session):
    await session.close()
    assert not session.closing
