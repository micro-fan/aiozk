import asyncio
from unittest import mock

import aiozk.session

import pytest
import asynctest

from aiozk import exc


@pytest.fixture
def session(event_loop):
    fake_retry_policy = asynctest.MagicMock(wraps=aiozk.session.RetryPolicy.forever())
    session = aiozk.session.Session(
        'zookeeper.test',
        timeout=10,
        retry_policy=fake_retry_policy,
        allow_read_only=True,
        read_timeout=30,
        loop=asynctest.MagicMock(wraps=event_loop),
    )
    session.state.transition_to(aiozk.session.States.CONNECTED)
    session.conn = asynctest.MagicMock()
    session.conn.send = asynctest.CoroutineMock()
    session.conn.close = asynctest.CoroutineMock()
    session.ensure_safe_state = asynctest.CoroutineMock()
    session.set_heartbeat = mock.Mock()
    return session


def prepare_repair_loop_callback_done_future(session):
    """Creates future that Awaits for session.repair_loop_task to be completed and returns value of session.closing"""
    future = asyncio.Future()
    repair_loop_task = session.repair_loop_task

    def set_result(_):
        future.set_result(session.closing)

    repair_loop_task.add_done_callback(set_result)
    return future


@pytest.mark.asyncio
async def test_start_session_twice(session):
    await session.start()
    session.ensure_safe_state.assert_called_once_with()
    session.ensure_safe_state.reset_mock()
    await session.start()
    session.ensure_safe_state.assert_called_once_with()

    session.loop.call_soon.assert_called_once()
    session.loop.create_task.assert_called_once()
    session.repair_loop_task.cancel()


@pytest.mark.asyncio
async def test_close_not_started(session):
    await session.close()
    assert not session.closing


@pytest.mark.asyncio
async def test_close_produces_no_error_log(session):
    session.conn.send.return_value = (mock.MagicMock(), mock.MagicMock())
    await session.start()

    repair_loop_callback_done = prepare_repair_loop_callback_done_future(session)
    with mock.patch.object(aiozk.session.log, 'error') as err_log_mock:

        assert not session.closing
        await session.close()

        session_closing = await repair_loop_callback_done

        assert session_closing
        assert not session.closing
        err_log_mock.assert_not_called()


@pytest.mark.asyncio
async def test_repair_loop_task_cancellation_produces_error_log(session):
    await session.start()

    repair_loop_callback_done = prepare_repair_loop_callback_done_future(session)
    with mock.patch.object(aiozk.session.log, 'error') as err_log_mock:
        session.repair_loop_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await session.repair_loop_task

        session_closing = await repair_loop_callback_done
        assert not session_closing
        err_log_mock.assert_called_once_with('Repair loop task cancelled when session is not in "closing" state')


@pytest.mark.asyncio
async def test_send_no_node(session):
    req = mock.MagicMock()
    session.conn.send.side_effect = exc.NoNode
    with pytest.raises(exc.NoNode):
        await session.send(req)

    session.retry_policy.clear.assert_called_once_with(req)
    session.conn.send.assert_called_once()
    session.set_heartbeat.assert_not_called()


@pytest.mark.asyncio
async def test_send_bad_version(session):
    req = mock.MagicMock()
    session.conn.send.side_effect = exc.BadVersion
    with pytest.raises(exc.BadVersion):
        await session.send(req)
    session.conn.send.assert_called_once()


@pytest.mark.asyncio
async def test_send_canceled(session):
    req = mock.MagicMock()
    session.conn.send.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await session.send(req)

    session.retry_policy.clear.assert_called_once_with(req)
    session.conn.send.assert_called_once()
    session.set_heartbeat.assert_not_called()


@pytest.mark.asyncio
async def test_send_connection_error(session):
    zxid = 1
    session.conn.send.side_effect = [exc.ConnectError('zookeeper.test', '2181'), (zxid, mock.MagicMock())]
    req = mock.MagicMock()
    await session.send(req)

    session.retry_policy.clear.assert_called_once_with(req)
    assert session.conn.send.call_count == 2
    session.set_heartbeat.assert_called_once_with()


@pytest.mark.asyncio
async def test_send_unknown_error(session):
    req = mock.MagicMock()
    session.conn.send.side_effect = RuntimeError
    with pytest.raises(RuntimeError):
        await session.send(req)

    session.retry_policy.clear.assert_called_once_with(req)
    session.conn.send.assert_called_once()
    session.set_heartbeat.assert_not_called()


@pytest.mark.asyncio
async def test_send_good_case(session):
    zxid = 1
    req = mock.MagicMock()
    resp = mock.MagicMock()
    session.conn.send.return_value = (zxid, resp)
    await session.send(req)

    session.retry_policy.clear.assert_called_once_with(req)
    session.conn.send.assert_called_once()
    session.set_heartbeat.assert_called_once_with()


@pytest.mark.asyncio
async def test_cxid_rollover(zk, path):
    zk.session.xid = 0x7fffffff - 10

    try:
        await zk.create(path)
        for _ in range(20):
            await zk.set_data(path, '')
    finally:
        await zk.deleteall(path)

    assert zk.session.xid < 0x7fffffff
    assert zk.session.xid > 0
