# from tornado import gen

from aiozk import protocol


class Transaction(object):

    def __init__(self, client):
        self.client = client
        self.request = protocol.TransactionRequest()

    def check_version(self, path, version):
        path = self.client.normalize_path(path)

        self.request.add(
            protocol.CheckVersionRequest(path=path, version=version)
        )

    def create(
            self, path, data=None, acl=None,
            ephemeral=False, sequential=False, container=False
    ):
        if container and not self.client.features.containers:
            raise ValueError("Cannot create container, feature unavailable.")

        path = self.client.normalize_path(path)
        acl = acl or self.client.default_acl

        if self.client.features.create_with_stat:
            request_class = protocol.Create2Request
        else:
            request_class = protocol.CreateRequest

        request = request_class(path=path, data=data, acl=acl)
        request.set_flags(ephemeral, sequential, container)

        self.request.add(request)

    def set_data(self, path, data, version=-1):
        path = self.client.normalize_path(path)

        self.request.add(
            protocol.SetDataRequest(path=path, data=data, version=version)
        )

    def delete(self, path, version=-1):
        path = self.client.normalize_path(path)

        self.request.add(
            protocol.DeleteRequest(path=path, version=version)
        )

    async def commit(self):
        if not self.request.requests:
            raise ValueError("No operations to commit.")

        response = await self.client.send(self.request)
        pairs = zip(self.request.requests, response.responses)

        result = Result()
        for request, reply in pairs:
            if isinstance(reply, protocol.CheckVersionResponse):
                result.checked.add(self.client.denormalize_path(request.path))
            elif isinstance(reply, protocol.CreateResponse):
                result.created.add(self.client.denormalize_path(request.path))
            elif isinstance(reply, protocol.SetDataResponse):
                result.updated.add(self.client.denormalize_path(request.path))
            elif isinstance(reply, protocol.DeleteResponse):
                result.deleted.add(self.client.denormalize_path(request.path))

        return result


class Result(object):

    def __init__(self):
        self.checked = set()
        self.created = set()
        self.updated = set()
        self.deleted = set()

    def __bool__(self):
        return sum([
            len(self.checked),
            len(self.created),
            len(self.updated),
            len(self.deleted),
        ]) > 0

    def __nonzero__(self):
        return self.__bool__()
