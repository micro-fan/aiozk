import asyncio
from unittest import mock

import aiozk

import pytest


def coroutine_mock(return_value=None):
    stub = mock.Mock(return_value=return_value)
    return asyncio.coroutine(stub)


@pytest.fixture
def session():
    fake_retry_policy = mock.MagicMock()
    fake_loop = mock.MagicMock()
    return aiozk.session.Session('zookeeper.test', 10, fake_retry_policy, True, 30, loop=fake_loop)


@pytest.mark.asyncio
async def test_start_session_twice(session):
    with mock.patch.object(session, 'ensure_safe_state', coroutine_mock()) as ensure_safe_state:
        await session.start()
        await session.start()

        session.loop.call_soon.assert_called_once()
        session.loop.create_task.assert_called_once()
        ensure_safe_state.assert_called_once()


@pytest.mark.asyncio
async def test_close_not_started(session):
    await session.close()
    assert not session.closing
