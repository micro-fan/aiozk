from .request import Request
from .response import Response
from .part import Part
from .stat import Stat
from .primitives import UString, Int, Vector


class ID(Part):
    """
    """
    parts = (
        ("scheme", UString),
        ("id", UString),
    )


class ACL(Part):
    """
    """
    READ_PERM = 1 << 0
    WRITE_PERM = 1 << 1
    CREATE_PERM = 1 << 2
    DELETE_PERM = 1 << 3
    ADMIN_PERM = 1 << 4

    parts = (
        ("perms", Int),
        ("id", ID),
    )

    @classmethod
    def make(
            cls, scheme, id,
            read=False, write=False, create=False, delete=False, admin=False
    ):
        instance = cls(id=ID(scheme=scheme, id=id))
        instance.set_perms(read, write, create, delete, admin)

        return instance

    def set_perms(self, read, write, create, delete, admin):
        perms = 0
        if read:
            perms |= self.READ_PERM
        if write:
            perms |= self.WRITE_PERM
        if create:
            perms |= self.CREATE_PERM
        if delete:
            perms |= self.DELETE_PERM
        if admin:
            perms |= self.ADMIN_PERM

        self.perms = perms


WORLD_READABLE = ACL.make(
    scheme="world", id="anyone",
    read=True, write=False, create=False, delete=False, admin=False
)

AUTHED_UNRESTRICTED = ACL.make(
    scheme="auth", id="",
    read=True, write=True, create=True, delete=True, admin=True
)

UNRESTRICTED_ACCESS = ACL.make(
    scheme="world", id="anyone",
    read=True, write=True, create=True, delete=True, admin=True
)


class GetACLRequest(Request):
    """
    """
    opcode = 6

    parts = (
        ("path", UString),
    )


class GetACLResponse(Response):
    """
    """
    opcode = 6

    parts = (
        ("acl", Vector.of(ACL)),
        ("stat", Stat),
    )


class SetACLRequest(Request):
    """
    """
    opcode = 7

    parts = (
        ("path", UString),
        ("acl", Vector.of(ACL)),
        ("version", Int),
    )


class SetACLResponse(Response):
    """
    """
    opcode = 7

    parts = (
        ("stat", Stat),
    )
