"""The right-party check as a lender setting (P8): a fixed menu, the honest description, the case-file record.

The call itself is in `samajh.dialogue.machine` (`start(..., identity=...)`, `identity_record(state)`).
"""

from samajh.identity.policy import (
    CHECK_LINES,
    MENU,
    CheckKind,
    IdentityPolicy,
    IdentityRecord,
    describe,
    expected_answer,
    identity_sentence,
    parse_policy,
)

__all__ = [
    "CHECK_LINES",
    "MENU",
    "CheckKind",
    "IdentityPolicy",
    "IdentityRecord",
    "describe",
    "expected_answer",
    "identity_sentence",
    "parse_policy",
]
