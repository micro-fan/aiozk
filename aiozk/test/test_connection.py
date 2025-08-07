import asyncio
from unittest import mock

import pytest

import aiozk.connection


@pytest.fixture
def connection():
    connection = aiozk.connection.Connection(
        host='zookeeper.test',
        port=2181,
        watch_handler=mock.MagicMock(),
        read_timeout=30,
    )

    connection.writer = mock.MagicMock()
    return connection


@pytest.mark.asyncio
async def test_close_connection_in_state_closing_do_not_performs_abort(connection):
    connection.abort = mock.AsyncMock()
    connection.closing = True

    await connection.close(0.1)

    connection.abort.assert_not_awaited()


@pytest.mark.asyncio
async def test_close_cancels_read_loop_task(connection):
    loop = asyncio.get_running_loop()
    connection.read_loop_task = loop.create_future()
    connection.read_loop_task.done = mock.MagicMock(return_value=False)
    connection.read_loop_task.cancel = mock.MagicMock(wraps=connection.read_loop_task.cancel)
    await connection.close(0.1)
    connection.read_loop_task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_connection_abort(connection):
    connection.pending_count = mock.MagicMock(return_value=1)
    connection.abort = mock.MagicMock()
    await connection.close(0.1)
    connection.abort.assert_called_once()
