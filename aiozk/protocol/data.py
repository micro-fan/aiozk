from .request import Request
from .response import Response
from .stat import Stat
from .primitives import Bool, UString, Buffer, Int


class GetDataRequest(Request):
    """
    """
    opcode = 4

    parts = (
        ("path", UString),
        ("watch", Bool),
    )


class GetDataResponse(Response):
    """
    """
    opcode = 4

    parts = (
        ("data", Buffer),
        ("stat", Stat)
    )


class SetDataRequest(Request):
    """
    """
    opcode = 5

    writes_data = True

    parts = (
        ("path", UString),
        ("data", Buffer),
        ("version", Int),
    )


class SetDataResponse(Response):
    """
    """
    opcode = 5

    parts = (
        ("stat", Stat),
    )
