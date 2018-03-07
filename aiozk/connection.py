import asyncio
import collections
import logging
import re
import struct
import sys
from time import time

# from tornado import ioloop, iostream, gen, concurrent, tcpclient

from aiozk import protocol, iterables, exc

DEFAULT_READ_TIMEOUT = 3

version_regex = re.compile(rb'Zookeeper version: (\d+)\.(\d+)\.(\d+)-.*')

# all requests and responses are prefixed with a 32-bit int denoting size
size_struct = struct.Struct("!i")
# replies are prefixed with an xid, zxid and error code
reply_header_struct = struct.Struct("!iqi")

log = logging.getLogger(__name__)
payload_log = logging.getLogger(__name__ + ".payload")
if payload_log.level == logging.NOTSET:
    payload_log.setLevel(logging.INFO)


class Connection:

    def __init__(self, host, port, watch_handler, read_timeout, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.host = host
        self.port = int(port)

        self.reader = None
        self.writer = None
        self.closing = False

        self.version_info = None
        self.start_read_only = None

        self.watch_handler = watch_handler

        self.opcode_xref = {}
        self.host_ip = None

        self.pending = {}
        self.pending_specials = collections.defaultdict(list)

        self.watches = collections.defaultdict(list)

        self.read_timeout = read_timeout or DEFAULT_READ_TIMEOUT
        self.read_loop_task = None

    async def connect(self):
        log.debug("Initial connection to server %s:%d", self.host, self.port)
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port,
                                                                 loop=self.loop)

        self.host_ip = self.writer.transport.get_extra_info('peername')[0]

        log.debug("Sending 'srvr' command to %s:%d", self.host, self.port)
        self.writer.write(b"srvr")

        answer = await self.reader.read()

        version_line = answer.split(b"\n")[0]
        match = version_regex.match(version_line)
        if match is None:
            raise ConnectionError
        self.version_info = tuple(map(int, match.groups()))
        self.start_read_only = bool(b"READ_ONLY" in answer)

        log.debug("Version info: %s", self.version_info)
        log.debug("Read-only mode: %s", self.start_read_only)

        log.debug("Actual connection to server %s:%d", self.host, self.port)
        self.writer.close()
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port,
                                                                 loop=self.loop)

    async def send_connect(self, request):
        # meant to be used before the read_loop starts
        payload_log.debug("[SEND] (initial) %s", request)

        payload = request.serialize()
        payload = size_struct.pack(len(payload)) + payload

        self.writer.write(payload)

        try:
            _, zxid, response = await self.read_response(initial_connect=True)
        except Exception:
            log.exception("Error reading connect response.")
            return

        payload_log.debug("[RECV] (initial) %s", response)
        return zxid, response

    def start_read_loop(self):
        self.read_loop_task = self.loop.create_task(self.read_loop())
        # ioloop.IOLoop.current().add_callback(self.read_loop)

    def send(self, request, xid=None):
        f = self.loop.create_future()

        if self.closing:
            f.set_exception(exc.ConnectError(self.host, self.port))
            return f

        if request.special_xid:
            xid = request.special_xid

        payload_log.debug("[SEND] (xid: %s) %s", xid, request)

        payload = request.serialize(xid)
        payload = size_struct.pack(len(payload)) + payload

        self.opcode_xref[xid] = request.opcode

        if xid in protocol.SPECIAL_XIDS:
            self.pending_specials[xid].append(f)
        else:
            self.pending[xid] = f

        def handle_write(write_future):
            try:
                write_future.result()
            except Exception as e:
                log.exception('Handle future error')
                self.abort()

        try:
            self.writer.write(payload)
            # handle_write(f)
        except Exception as e:
            log.exception('Exception during write')
            self.abort()

        return f

    async def read_loop(self):
        """
        Infinite loop that reads messages off of the socket while not closed.

        When a message is received its corresponding pending Future is set
        to have the message as its result.

        This is never used directly and is fired as a separate callback on the
        I/O loop via the `connect()` method.
        """
        while not self.closing:
            try:
                xid, zxid, response = await self.read_response()
            except (ConnectionAbortedError, asyncio.CancelledError):
                return
            except Exception as e:
                log.exception("Error reading response.")
                self.abort()
                return

            payload_log.debug("[RECV] (xid: %s) %s", xid, response)

            if xid == protocol.WATCH_XID:
                self.watch_handler(response)
                continue
            elif xid in protocol.SPECIAL_XIDS:
                f = self.pending_specials[xid].pop()
            else:
                f = self.pending.pop(xid)

            if isinstance(response, Exception):
                f.set_exception(response)
            elif not f.cancelled():
                f.set_result((zxid, response))

    async def _read(self, size=-1):
        remaining_size = size
        end_time = time() + self.read_timeout
        payload = []
        while remaining_size and (time() < end_time):
            remaining_time = end_time - time()
            done, pending = await asyncio.wait([self.reader.read(remaining_size)],
                                               timeout=remaining_time,
                                               loop=self.loop)
            if done:
                chunk = done.pop().result()
                payload.append(chunk)
                remaining_size -= len(chunk)
            if pending:
                pending.pop().cancel()
        if remaining_size:
            raise exc.UnfinishedRead
        return b''.join(payload)

    async def read_response(self, initial_connect=False):
        raw_size = await self.reader.read(size_struct.size)
        if raw_size == b'':
            raise ConnectionAbortedError
        size = size_struct.unpack(raw_size)[0]

        # connect and close op replies don't contain a reply header
        if initial_connect or self.pending_specials[protocol.CLOSE_XID]:
            raw_payload = await self._read(size)
            response = protocol.ConnectResponse.deserialize(raw_payload)
            return (None, None, response)

        raw_header = await self._read(reply_header_struct.size)
        xid, zxid, error_code = reply_header_struct.unpack_from(raw_header)

        if error_code:
            return (xid, zxid, exc.get_response_error(error_code))

        size -= reply_header_struct.size

        raw_payload = await self._read(size)

        if xid == protocol.WATCH_XID:
            response = protocol.WatchEvent.deserialize(raw_payload)
        else:
            opcode = self.opcode_xref.pop(xid)
            response = protocol.response_xref[opcode].deserialize(raw_payload)

        return (xid, zxid, response)

    def abort(self, exception=exc.ConnectError):
        """
        Aborts a connection and puts all pending futures into an error state.

        If ``sys.exc_info()`` is set (i.e. this is being called in an exception
        handler) then pending futures will have that exc info set.  Otherwise
        the given ``exception`` parameter is used (defaults to
        ``ConnectError``).
        """
        log.warning("Aborting connection to %s:%s", self.host, self.port)

        def abort_pending(f):
            exc_info = sys.exc_info()
            # TODO
            log.debug('Abort pending: {}'.format(f))
            if False and any(exc_info):
                f.set_exc_info(exc_info)
            else:
                f.set_exception(exception(self.host, self.port))

        for pending in self.drain_all_pending():
            if pending.done() or pending.cancelled():
                continue
            abort_pending(pending)

    def drain_all_pending(self):
        for special_xid in protocol.SPECIAL_XIDS:
            for f in iterables.drain(self.pending_specials[special_xid]):
                yield f
        for _, f in iterables.drain(self.pending):
            yield f

    async def close(self, timeout):
        if self.closing:
            return
        self.closing = True
        if self.read_loop_task:
            self.read_loop_task.cancel()
            await self.read_loop_task
        if self.pending or (self.pending_specials and self.pending_specials != {None: []}):
            log.warning('Pendings: {}; specials:  {}'.format(self.pending, self.pending_specials))

        try:
            # await list(pending_with_timeouts)
            self.abort(exception=exc.TimeoutError)
            # wlist = list(self.drain_all_pending())
            # log.warning('Wait for list: {} {}'.format(wlist, self.pending))
            # if len(wlist) > 0:
            #     await asyncio.wait(wlist, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning('ABORT Timeout')
            await self.abort(exception=exc.TimeoutError)
        except Exception as e:
            log.exception('in close: {}'.format(e))
            raise e
        finally:
            log.debug('Closing writer')
            self.writer.close()
            log.debug('Writer closed')
