from .request import Request
from .response import Response
from .stat import Stat
from .primitives import UString, Bool


class ExistsRequest(Request):
    """
    """
    opcode = 3

    parts = (
        ("path", UString),
        ("watch", Bool),
    )


class ExistsResponse(Response):
    """
    """
    opcode = 3

    parts = (
        ("stat", Stat),
    )
