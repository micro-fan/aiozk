import asyncio
import logging

from aiozk import exc, protocol

from .features import Features
from .recipes.proxy import RecipeProxy
from .session import Session
from .transaction import Transaction

# from tornado import gen, concurrent


log = logging.getLogger(__name__)


class ZKClient(object):
    def __init__(
        self,
        servers,
        chroot=None,
        session_timeout=10,
        default_acl=None,
        retry_policy=None,
        allow_read_only=False,
        read_timeout=None,
        loop=None,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.chroot = None
        if chroot:
            self.chroot = self.normalize_path(chroot)
            log.info("Using chroot '%s'", self.chroot)

        self.session = Session(
            servers, session_timeout, retry_policy, allow_read_only, read_timeout, loop
        )

        self.default_acl = default_acl or [protocol.UNRESTRICTED_ACCESS]

        self.stat_cache = {}

        self.recipes = RecipeProxy(self)

    def normalize_path(self, path):
        if self.chroot:
            path = "/".join([self.chroot, path])

        normalized = "/".join([name for name in path.split("/") if name])

        return "/" + normalized

    def denormalize_path(self, path):
        if self.chroot and path.startswith(self.chroot):
            path = path[len(self.chroot) :]

        return path

    async def start(self):
        await self.session.start()

        if self.chroot:
            await self.ensure_path("/")

    @property
    def features(self):
        if self.session.conn:
            return Features(self.session.conn.version_info)
        else:
            return Features((0, 0, 0))

    async def send(self, request):
        response = await self.session.send(request)

        if getattr(request, "path", None) and getattr(response, "stat", None):
            self.stat_cache[self.denormalize_path(request.path)] = response.stat

        return response

    async def close(self):
        await self.session.close()

    def wait_for_events(self, event_types, path):
        path = self.normalize_path(path)

        f = self.loop.create_future()

        def set_future(_):
            if not f.done():
                f.set_result(None)
            for event_type in event_types:
                self.session.remove_watch_callback(event_type, path, set_future)

        for event_type in event_types:
            self.session.add_watch_callback(event_type, path, set_future)

        return f

    async def exists(self, path, watch=False):
        path = self.normalize_path(path)

        try:
            await self.send(protocol.ExistsRequest(path=path, watch=watch))
        except exc.NoNode:
            return False
        return True

    async def create(
        self,
        path,
        data=None,
        acl=None,
        ephemeral=False,
        sequential=False,
        container=False,
    ):
        if container and not self.features.containers:
            raise ValueError("Cannot create container, feature unavailable.")

        path = self.normalize_path(path)
        acl = acl or self.default_acl

        if self.features.create_with_stat:
            request_class = protocol.Create2Request
        else:
            request_class = protocol.CreateRequest

        request = request_class(path=path, data=data, acl=acl)
        request.set_flags(ephemeral, sequential, container)

        response = await self.send(request)

        return self.denormalize_path(response.path)

    async def ensure_path(self, path, acl=None):
        path = self.normalize_path(path)

        acl = acl or self.default_acl

        paths_to_make = []
        for segment in path[1:].split("/"):
            if not paths_to_make:
                paths_to_make.append("/" + segment)
                continue

            paths_to_make.append("/".join([paths_to_make[-1], segment]))

        while paths_to_make:
            path = paths_to_make[0]

            if self.features.create_with_stat:
                request = protocol.Create2Request(path=path, acl=acl)
            else:
                request = protocol.CreateRequest(path=path, acl=acl)
            request.set_flags(
                ephemeral=False, sequential=False, container=self.features.containers
            )

            try:
                await self.send(request)
            except exc.NodeExists:
                pass

            paths_to_make.pop(0)

    async def delete(self, path, force=False):
        path = self.normalize_path(path)

        if not force and path in self.stat_cache:
            version = self.stat_cache[path].version
        else:
            version = -1

        await self.send(protocol.DeleteRequest(path=path, version=version))

    async def deleteall(self, path):
        childs = await self.get_children(path)
        for child in childs:
            await self.deleteall("/".join([path, child]))
        await self.delete(path, force=True)

    async def get(self, path, watch=False):
        # type: (str, bool) -> Tuple[str, protocol.stat.Stat]
        path = self.normalize_path(path)
        response = await self.send(protocol.GetDataRequest(path=path, watch=watch))
        return (response.data, response.stat)

    async def get_data(self, path, watch=False):
        response = await self.get(path, watch=watch)
        return response[0]

    async def set(self, path, data, version):
        # type: (str, str, int) -> protocol.SetDataResponse
        path = self.normalize_path(path)
        response = await self.send(
            protocol.SetDataRequest(path=path, data=data, version=version)
        )
        return response.stat

    async def set_data(self, path, data, force=False):
        path = self.normalize_path(path)

        if not force and path in self.stat_cache:
            version = self.stat_cache[path].version
        else:
            version = -1

        await self.send(protocol.SetDataRequest(path=path, data=data, version=version))

    async def get_children(self, path, watch=False):
        path = self.normalize_path(path)

        response = await self.send(protocol.GetChildren2Request(path=path, watch=watch))
        return response.children

    async def get_acl(self, path):
        path = self.normalize_path(path)

        response = await self.send(protocol.GetACLRequest(path=path))
        return response.acl

    async def set_acl(self, path, acl, force=False):
        path = self.normalize_path(path)

        if not force and path in self.stat_cache:
            version = self.stat_cache[path].version
        else:
            version = -1

        await self.send(protocol.SetACLRequest(path=path, acl=acl, version=version))

    def begin_transaction(self):
        return Transaction(self)
