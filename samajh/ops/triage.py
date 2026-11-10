"""The triage seam: the only place in this package that reads a tier or builds a summary line.

The tier of a call and of each flag comes from the core (`CaseResult.tier`, `Flag.tier`; contract
in references/pilots/P3a-contract.md section 1). This module decides nothing about it.

INTERIM: the summary lines. The contract's `samajh.rules.summarise` (section 6) has not landed, so
the lines are built here: a call's flags are merged by (rule, product), and a line carries the most
serious tier among its flags, the highest severity at that tier, and every distinct quote. When
`summarise` lands, `triage` maps its `IssueLine`s onto `SummaryLine` and `_line` goes away.
"""

from samajh.ops.model import SummaryLine, Tier, Triage
from samajh.types import CaseResult, Evidence, Flag, Severity

_TIER_RANK = {Tier.refer: 0, Tier.incomplete: 1, Tier.understanding_gap: 2}
_SEVERITY_RANK = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}


def _rank(flag: Flag) -> tuple[int, int]:
    return _TIER_RANK[Tier(flag.tier.value)], _SEVERITY_RANK[flag.severity]


def _line(flags: list[Flag]) -> SummaryLine:
    top = min(flags, key=_rank)
    quotes = [Evidence(quote=f.quote, turn_id=f.turn_id) for f in flags if f.quote and f.turn_id is not None]
    quotes += [evidence for f in flags for evidence in f.also]
    return SummaryLine(
        rule_id=top.rule_id,
        clause=top.clause,
        product_id=top.product_id,
        severity=top.severity,
        tier=Tier(top.tier.value),
        expected=top.expected,
        heard=top.heard,
        quotes=tuple(dict.fromkeys(quotes)),
    )


def triage(result: CaseResult) -> Triage:
    """The tier of one call and its summary lines: refer lines first, then by severity."""
    merged: dict[tuple, list[Flag]] = {}
    for flag in result.all_flags():
        merged.setdefault((flag.rule_id, flag.product_id), []).append(flag)
    lines = sorted(
        (_line(flags) for flags in merged.values()),
        key=lambda line: (_TIER_RANK[line.tier], _SEVERITY_RANK[line.severity]),
    )
    refer = [line for line in lines if line.tier is Tier.refer]
    return Triage(
        tier=Tier(result.tier.value), severity=refer[0].severity if refer else None, lines=tuple(lines)
    )
