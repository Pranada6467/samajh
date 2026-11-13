"""The right-party check as a lender setting (P8). Fixed menu, no free text.

`IdentityPolicy` is the setting. No field holds text, so no deployment can make the bot ask a question the
code does not already contain. The menu (`CheckKind`) has one member, the year of birth; a PIN-code check
and a second item are not built (decided, ledger I4). The expected answer comes from the loan record and
from nothing else (`expected_answer`); `IdentityRecord`, which goes into the case file, has no field that
can hold it or the words of a reply.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, field_validator

from samajh.types import LoanRecord


class CheckKind(StrEnum):
    """The questions a lender may add after the name. One member, on purpose."""

    year_of_birth = "year_of_birth"


class IdentityPolicy(BaseModel):
    """What the call does to decide it is speaking with the borrower. The default is no second check."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    second_check: CheckKind | None = None
    attempts: Literal[1, 2] = 1  # answers the second check judges; ignored with no second check
    prior_notice: StrictBool = True  # a written message before the call; mocked in the browser demo
    call_back_line: StrictBool = True  # the spoken "hang up and call the number on your papers" line


# The option names a lender (or the demo picker) may write for `second_check`.
_NONE = "none"
MENU: tuple[str, ...] = (_NONE, *(kind.value for kind in CheckKind))


def parse_policy(mapping: Mapping[str, object]) -> IdentityPolicy:
    """Read a setting (a `settings.toml` table, a session request). Raises ValueError on anything outside
    the menu: an unknown key, an unknown kind, free text, a string where a number or a flag belongs."""
    if not isinstance(mapping, Mapping):
        raise ValueError("the identity setting must be a table of fields")  # noqa: TRY004 - one error type for callers
    unknown = set(mapping) - set(IdentityPolicy.model_fields)
    if unknown:
        raise ValueError(f"unknown identity setting(s): {sorted(map(str, unknown))}")
    fields = dict(mapping)
    if "second_check" in fields:
        choice = fields["second_check"]
        if choice is None or choice == _NONE:
            fields["second_check"] = None
        elif isinstance(choice, str) and choice in MENU:
            fields["second_check"] = CheckKind(choice)
        else:
            raise ValueError(f"second_check must be one of {list(MENU)}")
    attempts = fields.get("attempts", 1)
    if isinstance(attempts, bool) or not isinstance(attempts, int):
        raise ValueError("attempts must be the number 1 or 2")  # noqa: TRY004 - one error type for callers
    try:
        return IdentityPolicy.model_validate(fields)
    except ValidationError as error:
        raise ValueError(f"invalid identity setting: {error.errors()[0]['msg']}") from error


_ATTEMPT_WORDS = {1: "one attempt", 2: "two attempts"}
_DISCLAIMER = "This is a right-party check, not identity verification."


def describe(policy: IdentityPolicy) -> str:
    """The honest description shown on the demo page and written into the case file."""
    if policy.second_check is None:
        check = (
            "No second check. A person who affirms twice that they are the borrower (yes to the name "
            "question, then yes to 'are you <first name> yourself?') is treated as the borrower; after an "
            "unclear first reply, one yes to that direct question is enough."
        )
    else:
        check = (
            f"The call asks for the year of birth after the name ({_ATTEMPT_WORDS[policy.attempts]}). A family "
            "member or anyone holding the borrower's details can answer it."
        )
    notice = (
        "A written notice is sent before the call (mocked in the demo: nothing is sent)."
        if policy.prior_notice
        else "No written notice before the call."
    )
    line = (
        "The call says the customer can hang up and call the customer-care number on their papers."
        if policy.call_back_line
        else "The call does not offer the hang-up-and-call-back line."
    )
    return f"{check} {_DISCLAIMER} {notice} {line}"


# The bot lines each setting can speak for the right-party check (keys of `samajh.dialogue.prompts.LINES`;
# a test checks each exists in every language and passes the bot-line lint). The who-check after a sign of
# another speaker belongs to both.
_COMMON_LINES = ("right_party.ask", "right_party.reask", "purpose.before_confirm", "disclosure.never_ask",
                 "verify.short", "right_party.who_check", "end.third_party")  # fmt: skip
CHECK_LINES: dict[CheckKind | None, tuple[str, ...]] = {
    None: _COMMON_LINES,
    CheckKind.year_of_birth: (*_COMMON_LINES, "second_check.ask", "second_check.reask", "end.check_failed"),
}


def expected_answer(kind: CheckKind, record: LoanRecord) -> int:
    """The answer the check compares with: read from the loan record and nothing else."""
    match kind:
        case CheckKind.year_of_birth:
            return record.borrower.dob.year


class IdentityRecord(BaseModel):
    """What the case file keeps of the right-party check. No field can hold the expected answer or a reply."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy: IdentityPolicy
    check_used: CheckKind | None  # the second check asked, or None when the policy has none
    attempts_allowed: int = Field(ge=0, le=2)  # 0 with no second check
    attempts_used: int = Field(ge=0, le=2)  # answers the second check judged
    # True: the check passed. False: the call ended at the check without passing. None: the call ended (or
    # stands) before the check was decided.
    passed: bool | None
    prior_notice_shown: bool
    prior_notice_mocked: Literal[True] = True  # the demo shows the notice; no message is ever sent
    sentence: str  # built from fixed templates (`identity_sentence`); never holds a digit

    @field_validator("sentence")
    @classmethod
    def _no_digit(cls, value: str) -> str:
        if any(ch.isdigit() for ch in value):
            raise ValueError("the identity sentence must hold no digit")
        return value


_COUNT = {0: "no", 1: "one", 2: "two"}


def identity_sentence(
    policy: IdentityPolicy, *, attempts_used: int, passed: bool | None, later_wrong_party: bool = False
) -> str:
    """One sentence for the case file, from fixed templates only. `later_wrong_party`: the check passed and the
    call later ended as a wrong party (a who-check or a takeover after the pass)."""
    if policy.second_check is None:
        result = {
            True: "the speaker affirmed being the borrower and was treated as the borrower",
            False: "the speaker was not accepted as the borrower, so the call ended before the loan was named",
            None: "the call ended before the right-party question was decided",
        }[passed]
        head = "No second check was set"
    else:
        of = f"{_COUNT[attempts_used]} of {_COUNT[policy.attempts]} attempt{'s' if policy.attempts > 1 else ''} used"
        if passed is False and attempts_used == 0:
            failed = "the speaker was not accepted at the name question, before any year of birth was judged"
        else:
            failed = f"the year of birth did not pass, with {of}"
        result = {
            True: f"the year of birth matched the loan record, with {of}",
            False: failed,
            None: "the call ended before the year of birth was judged",
        }[passed]
        head = "The year of birth was the second check"
    notice = (
        "a prior notice was shown (mocked, not sent)" if policy.prior_notice else "no prior notice was set"
    )
    if later_wrong_party and passed is True:
        result += (
            ", but later in the call signs that someone else had the phone ended it as a wrong party, and the"
            " speaker is not treated as the borrower"
        )
    return f"{head}; {result}; {notice}. {_DISCLAIMER}"
