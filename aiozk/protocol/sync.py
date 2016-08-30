from .request import Request
from .response import Response
from .primitives import UString


class SyncRequest(Request):
    """
    """
    opcode = 9

    parts = (
        ("path", UString),
    )


class SyncResponse(Response):
    """
    """
    opcode = 9

    parts = (
        ("path", UString),
    )
