"""Triage numbers for one run: where each kind of customer ended up. Pure: no network, no LLM.

Groups, by what the scenario set says about the customer (never by what the pipeline returned):

  * problem: the customer is misled, unaware or says they did not agree. A MISS is a call that
    ends `clear` or `understanding_gap`: nobody would look at it. `refer` and `incomplete` are
    not misses.
  * informed_clear: the customer is informed and the set's gold is clear (a compliant record).
    A REFERRAL here is a false referral: reviewer time spent on a customer with no problem.
  * informed_flagged: the customer is informed and the gold still flags the call, for a fault on
    the lender's record or a rule's boundary cost. A referral here may be the right outcome.
  * gold_not_clear, gold_clear: a set with no customer labels (the development set).

Units: calls, and base cases. The four language versions of a base case share their gold, so the
independent unit is the base case. A base case counts as hit when any of its calls in the slice
is a hit. Rates are per 100 with the count beside them; intervals are Wilson 95% on base cases
when the set has them, else on calls.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from samajh.evalkit.score import wilson
from samajh.types import Tier

GROUPS = ("problem", "informed_clear", "informed_flagged", "gold_not_clear", "gold_clear")
# Hindi and Hinglish are the product languages; Tamil and Kannada are experimental and shown apart.
SLICES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hi + hi-en", ("hi", "hi-en")),
    ("hi", ("hi",)),
    ("hi-en", ("hi-en",)),
    ("ta (experimental)", ("ta",)),
    ("kn (experimental)", ("kn",)),
)
MISS = frozenset({Tier.clear, Tier.understanding_gap})


def group(customer_state: str | None, gold_clear: bool) -> str:
    if customer_state is None:
        return "gold_clear" if gold_clear else "gold_not_clear"
    if customer_state != "informed":
        return "problem"
    return "informed_clear" if gold_clear else "informed_flagged"


@dataclass(frozen=True)
class TriageRow:
    """One call. `tier` is None when the pipeline gave no result; `ceiling` is the rule engine on
    the set's own extraction, so a miss there is not the extractor's."""

    id: str
    base: str | None
    language: str
    group: str
    tier: Tier | None
    ceiling: Tier | None = None


def _per_100(hits: int, n: int) -> str:
    if not n:
        return "n/a (n=0)"
    low, high = wilson(hits, n)
    return f"{100 * hits / n:.0f} per 100 ({hits}/{n}; 95% {100 * low:.0f} to {100 * high:.0f})"


def _hits(rows: list[TriageRow], hit: frozenset[Tier], field: str) -> tuple[str, str]:
    """(calls, base cases) with a hit, each as a rate per 100."""
    hits = [r for r in rows if getattr(r, field) in hit]
    calls = _per_100(len(hits), len(rows))
    bases = {r.base for r in rows if r.base}
    if not bases:
        return calls, "n/a (no base cases)"
    return calls, _per_100(len({r.base for r in hits if r.base}), len(bases))


def _tiers(rows: list[TriageRow]) -> str:
    counts = Counter(r.tier.value if r.tier else "no result" for r in rows)
    return ", ".join(f"{name} {counts[name]}" for name in (*(t.value for t in Tier), "no result") if counts[name])


def table(rows: Iterable[TriageRow]) -> str:
    rows = list(rows)
    header = [
        "group", "languages", "calls (base cases)", "tiers", "misses, calls", "misses, base cases",
        "referrals, calls", "referrals, base cases", "misses on the set's own extraction, calls",
    ]  # fmt: skip
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for name in GROUPS:
        for label, languages in SLICES:
            own = [r for r in rows if r.group == name and r.language in languages]
            if not own:
                continue
            miss_calls, miss_bases = _hits(own, MISS, "tier")
            refer_calls, refer_bases = _hits(own, frozenset({Tier.refer}), "tier")
            ceiling = [r for r in own if r.ceiling is not None]
            cells = [
                name,
                label,
                f"{len(own)} ({len({r.base for r in own if r.base})})",
                _tiers(own),
                miss_calls,
                miss_bases,
                refer_calls,
                refer_bases,
                _hits(ceiling, MISS, "ceiling")[0],
            ]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def misses(rows: Iterable[TriageRow]) -> list[TriageRow]:
    """Calls with a customer problem that nobody would look at."""
    return [r for r in rows if r.group == "problem" and r.tier in MISS]


def false_referrals(rows: Iterable[TriageRow]) -> list[TriageRow]:
    """Informed customers on a compliant record sent to a reviewer."""
    return [r for r in rows if r.group == "informed_clear" and r.tier is Tier.refer]
