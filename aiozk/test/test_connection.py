from unittest import mock

import pytest

import aiozk.connection


@pytest.fixture
def connection(event_loop):
    connection = aiozk.connection.Connection(
        host='zookeeper.test',
        port=2181,
        watch_handler=mock.MagicMock(),
        read_timeout=30,
        loop=mock.MagicMock(wraps=event_loop))

    connection.writer = mock.MagicMock()
    return connection


@pytest.mark.asyncio
async def test_close_connection_in_state_closing_do_not_performs_abort(connection):
    connection.abort = mock.AsyncMock()
    connection.closing = True

    await connection.close(mock.ANY)

    connection.abort.assert_not_awaited()


@pytest.mark.asyncio
async def test_close_cancels_read_loop_task(connection):
    connection.start_read_loop()
    connection.read_response = mock.AsyncMock(return_value=(0, mock.ANY, mock.ANY))

    task_cancelled_future = connection.loop.create_future()

    def set_result(task):
        task_cancelled_future.set_result(task.cancelled())

    connection.read_loop_task.add_done_callback(set_result)

    await connection.close(mock.ANY)
    assert await task_cancelled_future
