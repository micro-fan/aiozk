from .part import Part
from .primitives import Long, Int


class Stat(Part):
    """
    """
    parts = (
        ("created_zxid", Long),
        ("last_modified_zxid", Long),
        ("created", Long),
        ("modified", Long),
        ("version", Int),
        ("child_version", Int),
        ("acl_version", Int),
        ("ephemeral_owner", Long),
        ("data_length", Int),
        ("num_children", Int),
        ("last_modified_children", Long),
    )


class StatPersisted(Part):
    """
    """
    parts = (
        ("created_zxid", Long),
        ("last_modified_zxid", Long),
        ("created", Long),
        ("modified", Long),
        ("version", Int),
        ("child_version", Int),
        ("acl_version", Int),
        ("ephemeral_owner", Long),
        ("last_modified_children", Long),
    )
