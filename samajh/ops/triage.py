"""The triage seam: the only place in this package that reads a tier or builds a case summary.

The tier comes from the core (`CaseResult.tier`) and the summary lines from
`samajh.rules.summarise` (contract: references/pilots/P3a-contract.md sections 1 and 6). This
module decides nothing about either. It adds one thing the queue needs and the core does not
give: the highest severity among the call's `refer` flags, which orders the reviewer queue.
The referral basis and the first line are the core's (`CaseSummary`), copied through.
"""

from samajh.ops.model import Triage
from samajh.rules import summarise
from samajh.types import CaseResult, LoanRecord, Severity, Tier

_SEVERITY_RANK = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}


def triage(record: LoanRecord, result: CaseResult) -> Triage:
    """The tier of one call, its deduplicated summary and, when referred, its highest severity."""
    refer = [flag.severity for flag in result.all_flags() if flag.tier is Tier.refer]
    summary = summarise(record, result)
    return Triage(
        tier=result.tier,
        severity=min(refer, key=_SEVERITY_RANK.__getitem__) if refer else None,
        lines=summary.lines,
        referral_basis=summary.referral_basis,
        first_line=summary.first_line,
    )
