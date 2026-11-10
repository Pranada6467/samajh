"""Experiment E1: the teach-back call against a yes/no confirmation call on the same scenarios.

Reported by stratum and never pooled, because the mix of strata is the set author's choice
(`data/scenarios/README.md`, "The yes/no call and what E1 can claim"):

  * coached: the customer was told to say yes to everything. The yes/no call confirms by assumption.
  * acquiescent: says yes to a bank caller without weighing the question. Also by assumption.
  * never_asked: a truthful customer holds a wrong belief that the five closed questions do not
    ask about, so the yes/no call confirms. This measures the closed script's coverage.
  * asked: a truthful customer whose wrong belief a closed question does ask about.
  * informed: the customer's beliefs match the record. Shown apart: it is the cost side.

"Caught" means the call did not end as a pass: the yes/no call ended not confirmed, or the
teach-back verdict is not `clear` (a flag, or unclear and sent to a person). The yes/no arm is
the set's scripted outcome, read perfectly, with no LLM. The teach-back arm is the real pipeline.
"""

from collections.abc import Iterable
from dataclasses import dataclass

STRATA = ("coached", "acquiescent", "never_asked", "asked", "informed")


def stratum(informed: bool, disposition: str, confirmed: bool) -> str:
    if informed:
        return "informed"
    if disposition in ("coached", "acquiescent"):
        return disposition
    return "never_asked" if confirmed else "asked"


@dataclass(frozen=True)
class E1Row:
    """Both arms on one scenario."""

    base: str  # the base case the four language versions share
    stratum: str
    gold_clear: bool
    yes_no_caught: bool
    teach_back_caught: bool  # pipeline verdict is not clear (an extractor error is not clear)
    target_flagged: bool  # the pipeline flagged the rule the scenario was written for
    ceiling_caught: bool  # the rule engine on the set's gold extraction is not clear


def _count(rows: list[E1Row], field: str) -> str:
    """Calls caught, and base cases caught in every language they have."""
    if not rows:
        return "n/a (n=0)"
    hits = sum(getattr(r, field) for r in rows)
    bases = sorted({r.base for r in rows})
    whole = sum(all(getattr(r, field) for r in rows if r.base == base) for base in bases)
    return f"{hits}/{len(rows)} calls ({whole}/{len(bases)} base cases in every language)"


def table(rows: Iterable[E1Row]) -> str:
    rows = list(rows)
    header = [
        "stratum", "gold", "calls (base cases)", "yes/no call caught", "teach-back caught",
        "teach-back flagged the target rule", "teach-back caught, gold extraction",
    ]  # fmt: skip
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for name in STRATA:
        for gold_clear in (False, True):
            group = [r for r in rows if r.stratum == name and r.gold_clear is gold_clear]
            if not group:
                continue
            cells = [
                name,
                "clear" if gold_clear else "flag or unclear",
                f"{len(group)} ({len({r.base for r in group})})",
                _count(group, "yes_no_caught"),
                _count(group, "teach_back_caught"),
                _count(group, "target_flagged"),
                _count(group, "ceiling_caught"),
            ]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
