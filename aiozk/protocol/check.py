from .request import Request
from .response import Response
from .primitives import Int, UString


class CheckVersionRequest(Request):
    """
    """
    opcode = 13

    parts = (
        ("path", UString),
        ("version", Int),
    )


class CheckVersionResponse(Response):
    """
    """
    opcode = 13

    parts = ()
