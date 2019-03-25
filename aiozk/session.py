import asyncio
import collections
import logging
import random
import re

from aiozk import protocol, exc
from .connection import Connection
from .retry import RetryPolicy
from .states import States, SessionStateMachine

# from tornado import gen, ioloop


DEFAULT_ZOOKEEPER_PORT = 2181

MAX_FIND_WAIT = 60  # in seconds

HEARTBEAT_FREQUENCY = 3  # heartbeats per timeout interval


log = logging.getLogger(__name__)


class Session(object):

    def __init__(self, servers, timeout, retry_policy, allow_read_only, read_timeout, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.hosts = []
        for server in servers.split(","):
            ipv6_match = re.match(r'\[(.*)\]:(\d+)$', server)
            if ipv6_match is not None:
                host, port = ipv6_match.groups()
            elif ":" in server:
                host, port = server.rsplit(":", 1)
            else:
                host = server
                port = DEFAULT_ZOOKEEPER_PORT

            self.hosts.append((host, port))

        self.conn = None
        self.state = SessionStateMachine()

        self.retry_policy = retry_policy or RetryPolicy.forever()
        self.allow_read_only = allow_read_only

        self.xid = 0
        self.last_zxid = None

        self.session_id = None
        self.timeout = timeout
        self.password = b'\x00'
        self.read_timeout = read_timeout

        self.repair_loop_task = None

        self.heartbeat_handle = None

        self.watch_callbacks = collections.defaultdict(set)

        self.started = False
        self.closing = False

    async def ensure_safe_state(self, writing=False):
        safe_states = [States.CONNECTED]
        if self.allow_read_only and not writing:
            safe_states.append(States.READ_ONLY)

        if self.state in safe_states:
            return

        await self.state.wait_for(*safe_states, loop=self.loop)

    async def start(self):
        if self.started:
            await self.ensure_safe_state()
            return
        log.debug('Start session...')
        self.loop.call_soon(self.set_heartbeat)
        self.repair_loop_task = self.loop.create_task(self.repair_loop())
        self.repair_loop_task.add_done_callback(self._on_repair_loop_done)
        self.started = True
        await self.ensure_safe_state()

    def _on_repair_loop_done(self, repair_loop_task):
        repair_loop_exception = repair_loop_task.exception()
        if repair_loop_exception:
            log.error('Repair loop task failed with exception: {error}'.format(error=repair_loop_exception))

    async def find_server(self, allow_read_only):
        conn = None

        retry_policy = RetryPolicy.exponential_backoff(maximum=MAX_FIND_WAIT)

        while not conn:
            await retry_policy.enforce(loop=self.loop)

            servers = random.sample(self.hosts, len(self.hosts))
            for host, port in servers:
                log.info("Connecting to %s:%s", host, port)
                conn = await self.make_connection(host, port)
                if not conn or (conn.start_read_only and not allow_read_only):
                    continue
                log.info("Connected to %s:%s", host, port)
                break

            if not conn:
                log.warning("No servers available, will keep trying.")

        old_conn = self.conn
        self.conn = conn

        if old_conn:
            log.debug('Close old connection')
            self.loop.create_task(old_conn.close(self.timeout))

        if conn.start_read_only:
            self.loop.create_task(self.find_server(allow_read_only=False))

    async def make_connection(self, host, port):
        conn = Connection(host, port, watch_handler=self.event_dispatch, read_timeout=self.read_timeout, loop=self.loop)
        try:
            await conn.connect()
        except Exception:
            log.exception("Couldn't connect to %s:%s", host, port)
            return
        return conn

    async def establish_session(self):
        log.info("Establishing session. {!r}".format(self.session_id))
        connection_response = await self.conn.send_connect(
            protocol.ConnectRequest(
                protocol_version=0,
                last_seen_zxid=self.last_zxid or 0,
                timeout=int((self.timeout or 0) * 1000),
                session_id=self.session_id or 0,
                password=self.password,
                read_only=self.allow_read_only,
            )
        )
        if connection_response is None:
            # handle issue with inconsistent zxid on reconnection
            if self.state.current_state != States.LOST:
                self.state.transition_to(States.LOST)
            self.last_zxid = None
            raise exc.SessionLost()

        zxid, response = connection_response
        self.last_zxid = zxid

        if response.session_id == 0:  # invalid session, probably expired
            log.debug('Session lost')
            if self.state.current_state != States.LOST:
                self.state.transition_to(States.LOST)
            raise exc.SessionLost()

        log.info("Got session id %s", hex(response.session_id))
        log.info("Negotiated timeout: %s seconds", response.timeout / 1000)

        self.session_id = response.session_id
        self.password = response.password
        self.timeout = response.timeout / 1000

        self.last_zxid = zxid

    async def repair_loop(self):
        while not self.closing:
            log.debug('Await for repairable state')
            await self.state.wait_for(States.SUSPENDED, States.LOST, loop=self.loop)
            log.debug('Repair state reached')
            if self.closing:
                break

            await self.find_server(allow_read_only=self.allow_read_only)

            try:
                await asyncio.wait_for(self.establish_session(), self.timeout, loop=self.loop)
            except (exc.SessionLost, asyncio.TimeoutError) as e:
                log.info('Session closed: {}'.format(e))
                self.conn.abort(exc.SessionLost)
                await self.conn.close(self.timeout)  # TODO: make real timeout
                self.session_id = None
                self.password = b'\x00'
                continue

            if self.conn.start_read_only:
                self.state.transition_to(States.READ_ONLY)
            else:
                self.state.transition_to(States.CONNECTED)

            self.conn.start_read_loop()
            await self.set_existing_watches()

    async def send(self, request):
        response = None
        while not response:
            await self.retry_policy.enforce(request, loop=self.loop)
            await self.ensure_safe_state(writing=request.writes_data)

            try:
                self.xid += 1
                zxid, response = await self.conn.send(request, xid=self.xid)
                self.last_zxid = zxid
                self.set_heartbeat()
                self.retry_policy.clear(request)
            except (exc.NodeExists, exc.NoNode, exc.NotEmpty, exc.BadVersion):
                self.retry_policy.clear(request)
                raise
            except asyncio.CancelledError:
                self.retry_policy.clear(request)
                raise
            except exc.ConnectError:
                self.state.transition_to(States.SUSPENDED)
            except Exception as e:
                log.exception('Send exception: {}'.format(e))
                self.retry_policy.clear(request)
                raise e
        return response

    def set_heartbeat(self):
        timeout = self.timeout / HEARTBEAT_FREQUENCY
        if self.heartbeat_handle:
            self.heartbeat_handle.cancel()
        self.heartbeat_handle = self.loop.call_later(timeout, self.create_heartbeat)

    def create_heartbeat(self):
        self.loop.create_task(self.heartbeat())

    async def heartbeat(self):
        if self.closing:
            return

        await self.ensure_safe_state()

        try:
            timeout = self.timeout - self.timeout/HEARTBEAT_FREQUENCY
            zxid, _ = await asyncio.wait_for(self.conn.send(protocol.PingRequest()), timeout, loop=self.loop)
            self.last_zxid = zxid
        except (exc.ConnectError, asyncio.TimeoutError):
            self.state.transition_to(States.SUSPENDED)
        except Exception as e:
            log.exception('in heartbeat: {}'.format(e))
            raise e
        finally:
            self.set_heartbeat()

    def add_watch_callback(self, event_type, path, callback):
        self.watch_callbacks[(event_type, path)].add(callback)

    def remove_watch_callback(self, event_type, path, callback):
        self.watch_callbacks[(event_type, path)].discard(callback)

    def event_dispatch(self, event):
        log.debug("Got watch event: %s", event)

        if event.type:
            key = (event.type, event.path)
            for callback in self.watch_callbacks[key]:
                self.loop.call_soon(callback, event.path)
                # ioloop.IOLoop.current().add_callback(callback, event.path)
            return

        if event.state == protocol.WatchEvent.DISCONNECTED:
            log.error("Got 'disconnected' watch event.")
            self.state.transition_to(States.LOST)
        elif event.state == protocol.WatchEvent.SESSION_EXPIRED:
            log.error("Got 'session expired' watch event.")
            self.state.transition_to(States.LOST)
        elif event.state == protocol.WatchEvent.AUTH_FAILED:
            log.error("Got 'auth failed' watch event.")
            self.state.transition_to(States.LOST)
        elif event.state == protocol.WatchEvent.CONNECTED_READ_ONLY:
            log.warning("Got 'connected read only' watch event.")
            self.state.transition_to(States.READ_ONLY)
        elif event.state == protocol.WatchEvent.SASL_AUTHENTICATED:
            log.info("Authentication successful.")
        elif event.state == protocol.WatchEvent.CONNECTED:
            log.info("Got 'connected' watch event.")
            self.state.transition_to(States.CONNECTED)

    async def set_existing_watches(self):
        if not self.watch_callbacks:
            return

        request = protocol.SetWatchesRequest(
            relative_zxid=self.last_zxid or 0,
            data_watches=[],
            exist_watches=[],
            child_watches=[],
        )

        for event_type, path in self.watch_callbacks.keys():
            if event_type == protocol.WatchEvent.CREATED:
                request.exist_watches.append(path)
            if event_type == protocol.WatchEvent.DATA_CHANGED:
                request.data_watches.append(path)
            elif event_type == protocol.WatchEvent.CHILDREN_CHANGED:
                request.child_watches.append(path)

        await self.send(request)

    async def close(self):
        if not self.started:
            log.debug('Do nothing because session is not started')
            return
        if self.closing:
            return
        self.closing = True
        if self.repair_loop_task:
            self.repair_loop_task.cancel()
            await asyncio.wait_for(self.send(protocol.CloseRequest()), self.timeout,
                                   loop=self.loop)
        if self.state.current_state != States.LOST:
            self.state.transition_to(States.LOST)
        if self.conn:
            await self.conn.close(self.timeout)
        self.closing = False
        self.started = False
