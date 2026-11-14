"""Which half of a two-part consent answer is missing (iteration 4, W4). Pure; shared by the rules and the live call.

`method_only` is the rules' own predicate (`checks._method_only`), under a public name; `what_only` is its mirror."""

from __future__ import annotations

from typing import Literal

from samajh.types import Answer, ConsentMethod, GapReason, Stated, Unclear


def method_only(given: Answer[bool], method: Answer[ConsentMethod]) -> bool:
    """The consent reply gave a way of agreeing and named nothing agreed to (`checks._method_only`)."""
    from samajh.rules.checks import _method_only

    return _method_only(given, method)


def what_only(given: Answer[bool], method: Answer[ConsentMethod]) -> bool:
    """The mirror: the reply named something agreed to and gave no way of agreeing, in the same turn."""
    return (
        isinstance(given, Stated)
        and isinstance(method, Unclear)
        and method.reason is GapReason.no_usable_answer
        and (method.evidence is None or method.evidence.turn_id == given.evidence.turn_id)
        and all(e.turn_id != given.evidence.turn_id for e in given.also)
    )


def missing_half(given: Answer[bool], method: Answer[ConsentMethod]) -> Literal["what", "how"] | None:
    """"what" when only the way of agreeing was given, "how" when only what was agreed to, else None."""
    if method_only(given, method):
        return "what"
    if what_only(given, method):
        return "how"
    return None
