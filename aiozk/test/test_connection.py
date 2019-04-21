import asyncio

import asynctest
import pytest

import aiozk.connection


@pytest.fixture
def connection(event_loop):
    connection = aiozk.connection.Connection(
        host='zookeeper.test',
        port=2181,
        watch_handler=asynctest.MagicMock(),
        read_timeout=30,
        loop=asynctest.MagicMock(wraps=event_loop))

    connection.writer = asynctest.MagicMock()
    return connection


@pytest.mark.asyncio
async def test_close_connection_in_state_closing_do_not_performs_abort(connection):
    connection.abort = asynctest.CoroutineMock()
    connection.closing = True

    await connection.close(asynctest.ANY)

    connection.abort.assert_not_awaited()


@pytest.mark.asyncio
async def test_close_cancels_read_loop_task(connection):
    connection.start_read_loop()
    connection.read_response = asynctest.CoroutineMock(return_value=(0, asynctest.ANY, asynctest.ANY))

    task_cancelled_future = asyncio.Future()

    def set_result(task):
        task_cancelled_future.set_result(task.cancelled())

    connection.read_loop_task.add_done_callback(set_result)

    await connection.close(asynctest.ANY)
    assert await task_cancelled_future
