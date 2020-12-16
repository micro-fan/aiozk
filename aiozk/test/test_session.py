import asyncio
from unittest import mock

import aiozk.session
from aiozk.states import States

import pytest

from aiozk import exc, protocol


@pytest.fixture
def session(event_loop):
    fake_retry_policy = mock.MagicMock(wraps=aiozk.session.RetryPolicy.forever())
    session = aiozk.session.Session(
        'zookeeper.test',
        timeout=10,
        retry_policy=fake_retry_policy,
        allow_read_only=True,
        read_timeout=30,
        loop=mock.MagicMock(wraps=event_loop),
    )
    session.state.transition_to(aiozk.session.States.CONNECTED)
    session.conn = mock.MagicMock()
    session.conn.send = mock.AsyncMock()
    session.conn.close = mock.AsyncMock()
    session.ensure_safe_state = mock.AsyncMock()
    session.set_heartbeat = mock.Mock()
    return session


@pytest.fixture
def retry_policy():
    with mock.patch('aiozk.session.RetryPolicy') as rpcls:
        rp = rpcls.exponential_backoff.return_value

        async def sleep_zero():
            await asyncio.sleep(0)
        enforce = mock.AsyncMock(side_effect=sleep_zero)
        rp.enforce = enforce
        yield rp


def prepare_repair_loop_callback_done_future(session):
    """Creates future that Awaits for session.repair_loop_task to be completed and returns value of session.closing"""
    future = session.loop.create_future()
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


@pytest.mark.asyncio
async def test_duplicated_heartbeat_task(servers, event_loop):
    session = aiozk.session.Session(servers, 3, None, False, None, event_loop)
    await session.start()
    session.set_heartbeat()

    # Simulate that response is delayed
    session.conn.read_loop_task.cancel()
    # Ensure that the first heartbeat task is running and waiting for a
    # response of ping request.
    await asyncio.sleep(session.timeout / aiozk.session.HEARTBEAT_FREQUENCY +
                        0.1)
    # While the first heartbeat task is waiting for a response,
    # .set_heartbeat() can be called by session.send().
    session.set_heartbeat()
    # Ensure that the second heartbeat task is running and waiting for a
    # response of ping request.
    await asyncio.sleep(session.timeout / aiozk.session.HEARTBEAT_FREQUENCY +
                        0.1)
    session.conn.start_read_loop()
    # If the second call of .set_heartbeat() created a duplicated heartbeat
    # task and the state of session turns into SUSPENDED. The right behavior is
    # that the second call of .set_heartbeat does not create a duplicated
    # heartbeat task.
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                session.state.wait_for(States.SUSPENDED),
                timeout=session.timeout -
                session.timeout / aiozk.session.HEARTBEAT_FREQUENCY * 2)
    finally:
        await session.state.wait_for(States.CONNECTED)
        await session.close()


@pytest.mark.asyncio
async def test_session_close_heartbeat_cancellation(servers, event_loop):
    session = aiozk.session.Session(servers, 3, None, False, None, event_loop)
    await session.start()
    heartbeat_task = mock.AsyncMock()
    done = mock.MagicMock()
    done.return_value = False
    heartbeat_task.done = done

    cancel_called = False

    def cancel():
        nonlocal cancel_called
        cancel_called = True

    heartbeat_task.cancel = cancel
    session.heartbeat_task = heartbeat_task
    await session.close()

    assert cancel_called
    assert session.heartbeat_task is None


@pytest.mark.asyncio
async def test_send_timeout(servers, event_loop, path):
    session = aiozk.session.Session(servers, 3, None, False, None, event_loop)
    await session.start()
    await session.state.wait_for(States.CONNECTED)
    # Simulate that response is delayed
    session.conn.read_loop_task.cancel()

    await asyncio.sleep(0.1)

    nonode_path = path
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(session.send(
            protocol.ExistsRequest(path=nonode_path, watch=False)),
                               timeout=0.1)

    await asyncio.sleep(0.1)
    session.conn.start_read_loop()
    try:
        with pytest.raises(exc.NoNode):
            await asyncio.wait_for(session.send(
                protocol.ExistsRequest(path=nonode_path, watch=False)),
                                   timeout=session.timeout + 1)
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_find_server(session, retry_policy):
    session.make_connection = mock.AsyncMock()
    conn = mock.MagicMock()
    conn.close = mock.AsyncMock()
    conn.start_read_only = True
    session.make_connection.return_value = conn

    task = session.loop.create_task(session.find_server(allow_read_only=False))

    async def _wait_for():
        while retry_policy.enforce.await_count < 4:
            await asyncio.sleep(0)

    await asyncio.wait_for(_wait_for(), 1)
    assert not task.done(), 'find_server should not finish '
    task.cancel()

    conn.start_read_only = False
    await session.find_server(allow_read_only=False)
