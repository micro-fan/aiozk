from .request import Request
from .response import Response
from .stat import Stat
from .primitives import Bool, UString, Vector


class GetChildrenRequest(Request):
    """
    """
    opcode = 8

    parts = (
        ("path", UString),
        ("watch", Bool),
    )


class GetChildrenResponse(Response):
    """
    """
    opcode = 8

    parts = (
        ("children", Vector.of(UString)),
    )


class GetChildren2Request(Request):
    """
    """
    opcode = 12

    parts = (
        ("path", UString),
        ("watch", Bool),
    )


class GetChildren2Response(Response):
    """
    """
    opcode = 12

    parts = (
        ("children", Vector.of(UString)),
        ("stat", Stat),
    )
