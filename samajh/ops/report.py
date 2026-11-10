"""The half-yearly report: counts over one batch, each with its n and a Wilson 95% interval.

Every count comes from the store's own files (book, draws, attempts, calls, dispositions) through
`load_batch`, never from the simulation's hidden truth. The definitions are in the docstrings
below so that a reader can recount them from the raw files.
"""

import statistics
from collections.abc import Callable, Sequence
from datetime import date, datetime

from samajh.ops import wording
from samajh.ops.batch import Batch, Sampled, load_batch
from samajh.ops.model import WINDOW_DAYS, AttemptOutcome, Decision, FinalStatus
from samajh.ops.store import OpsStore
from samajh.ops.views import (
    Breakdown,
    BreakdownRow,
    DispositionRow,
    Funnel,
    FunnelRow,
    PolicyItem,
    Proportion,
    ReportView,
    RuleFinding,
    TierRow,
    Timing,
    batch_view,
    draw_views,
    proportion,
)
from samajh.rules import CLAUSES
from samajh.types import RuleId, Tier

MIN_GROUP = 5  # a branch or channel is named as "highest" only with at least this many completed calls


def _day(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


def _flagged(s: Sampled) -> set[RuleId]:
    return {flag.rule_id for flag in s.call.result.all_flags()}


def funnel(batch: Batch) -> Funnel:
    """Sampled: every drawn loan of every draw. Each stage is a share of sampled.

    attempted: at least one attempt. reached: any attempt whose outcome is not no_answer.
    right party confirmed: any attempt with `right_party_confirmed`. completed: the last attempt
    completed. Exits: one row per final status other than completed (the status comes from the
    last attempt: none is not_attempted, no_answer is unreachable, otherwise the same name).
    Completed plus the exits equals sampled.
    """
    sampled = batch.sampled
    n = len(sampled)
    stages = {
        "attempted": sum(bool(s.attempts) for s in sampled),
        "reached": sum(any(a.outcome is not AttemptOutcome.no_answer for a in s.attempts) for s in sampled),
        "right_party_confirmed": sum(any(a.right_party_confirmed for a in s.attempts) for s in sampled),
        "completed": sum(s.status is FinalStatus.completed for s in sampled),
    }
    exits = {
        status: sum(s.status is status for s in sampled)
        for status in FinalStatus
        if status is not FinalStatus.completed
    }
    assert stages["completed"] + sum(exits.values()) == n, "every sampled loan has exactly one final status"
    return Funnel(
        sampled=n,
        attempts=sum(len(s.attempts) for s in sampled),
        stages=tuple(
            FunnelRow(key=key, label=wording.STAGE_LABEL[key], value=proportion(count, n))
            for key, count in stages.items()
        ),
        exits=tuple(
            FunnelRow(key=status.value, label=wording.STATUS_LABEL[status], value=proportion(count, n))
            for status, count in exits.items()
        ),
    )


def timing(batch: Batch) -> Timing:
    """Days since the sale on the day of an attempt.

    first_attempt_days: minimum, median (the lower middle value of an even count) and maximum of
    the first attempt's day, over attempted loans. completed_within_window: completed calls whose
    completed attempt was on day 30 or earlier. attempts_after_window: attempts on day 31 or later.
    """
    first = sorted(s.attempts[0].day_since_sale for s in batch.sampled if s.attempts)
    completed = batch.completed
    return Timing(
        first_attempt_days=(first[0], statistics.median_low(first), first[-1]) if first else None,
        completed_within_window=proportion(
            sum(s.attempts[-1].day_since_sale <= WINDOW_DAYS for s in completed), len(completed)
        ),
        attempts_after_window=sum(a.day_since_sale > WINDOW_DAYS for s in batch.sampled for a in s.attempts),
    )


def tiers(batch: Batch) -> tuple[TierRow, ...]:
    """The tier of each analysed call (one per sampled loan whose last attempt completed)."""
    completed = batch.completed
    return tuple(
        TierRow(
            tier=tier,
            label=wording.TIER_LABEL[tier],
            value=proportion(sum(s.triage.tier is tier for s in completed), len(completed)),
        )
        for tier in Tier
    )


def findings(batch: Batch) -> tuple[RuleFinding, ...]:
    """One row per rule, over the analysed calls.

    flagged: calls with at least one flag under the rule; n is every analysed call. undecided:
    calls with a gap under the rule and no flag under it. referred: flagged calls whose summary
    has a `refer` line for the rule. The `evidence` rule appears only if it flagged or left a gap.
    Understanding rules (those under the feedback paragraph itself) come first; each group is
    ordered by share, largest first.
    """
    completed = batch.completed
    clauses = CLAUSES[batch.meta.book.lender_type]
    feedback = clauses[RuleId.kind]
    rows: list[RuleFinding] = []
    for rule in RuleId:
        flagged = [s for s in completed if rule in _flagged(s)]
        undecided = sum(
            rule not in _flagged(s) and any(g.rule_id is rule for g in s.call.result.all_gaps())
            for s in completed
        )
        if rule is RuleId.evidence and not flagged and not undecided:
            continue
        rows.append(
            RuleFinding(
                rule_id=rule,
                rule_label=wording.RULE_LABEL[rule],
                may_engage=wording.may_engage(clauses[rule]),
                statement=wording.RULE_STATEMENT[rule],
                understanding=clauses[rule] == feedback,
                flagged=proportion(len(flagged), len(completed)),
                undecided=undecided,
                referred=sum(
                    any(rule in line.rule_ids and line.tier is Tier.refer for line in s.triage.lines)
                    for s in flagged
                ),
            )
        )
    return tuple(sorted(rows, key=lambda r: (not r.understanding, -(r.flagged.share or 0))))


def referrals(batch: Batch) -> tuple[tuple[DispositionRow, ...], Proportion]:
    """Referrals by the decision that stands (the latest recorded), plus "awaiting" for none.
    n is every referral. The second value is established out of the referrals whose latest
    decision is final (established or not established)."""
    latest = [batch.latest(s.call.call_id) for s in batch.referrals]
    n = len(latest)
    rows = [
        DispositionRow(
            key=decision.value,
            label=wording.DECISION_LABEL[decision],
            value=proportion(sum(d is not None and d.decision is decision for d in latest), n),
        )
        for decision in Decision
    ]
    rows.append(
        DispositionRow(key="awaiting", label=wording.AWAITING_LABEL, value=proportion(latest.count(None), n))
    )
    established = sum(d is not None and d.decision is Decision.established for d in latest)
    decided = sum(batch.decided(s.call.call_id) for s in batch.referrals)
    return tuple(rows), proportion(established, decided)


Group = tuple[str, Callable[[Sampled], str], Callable[[str], str]]  # (by, key of a loan, label of a key)
GROUPS: tuple[Group, ...] = (
    ("loan_kind", lambda s: s.loan.record.loan_kind.value, lambda key: wording.LOAN_KIND_LABEL[key]),
    ("branch", lambda s: s.loan.branch, lambda key: key),
    ("channel", lambda s: s.loan.channel.value, lambda key: wording.CHANNEL_LABEL[key]),
)


def _grouped(members: Sequence[Sampled], key_of: Callable[[Sampled], str]) -> dict[str, list[Sampled]]:
    groups: dict[str, list[Sampled]] = {}
    for s in members:
        groups.setdefault(key_of(s), []).append(s)
    return dict(sorted(groups.items()))


def breakdowns(batch: Batch) -> tuple[Breakdown, ...]:
    """By loan type, branch and sales channel. A row's two shares are of its own completed calls."""

    def row(key: str, label: str, members: list[Sampled]) -> BreakdownRow:
        completed = [s for s in members if s.call is not None]
        return BreakdownRow(
            key=key,
            label=label,
            sampled=len(members),
            completed=len(completed),
            referred=proportion(sum(s.triage.tier is Tier.refer for s in completed), len(completed)),
            understanding_gap=proportion(
                sum(s.triage.tier is Tier.understanding_gap for s in completed), len(completed)
            ),
        )

    return tuple(
        Breakdown(
            by=by,
            label=wording.BREAKDOWN_LABEL[by],
            rows=tuple(
                row(key, label(key), members) for key, members in _grouped(batch.sampled, key_of).items()
            ),
        )
        for by, key_of, label in GROUPS
    )


def _highest(completed: Sequence[Sampled], rule: RuleId) -> str | None:
    """The branch or channel with the highest share of calls flagged under `rule`, among those
    with at least `MIN_GROUP` completed calls. None when none qualifies or none has a flag."""
    places = {
        "branch": lambda key: f"branch {key}",
        "channel": lambda key: f"the {wording.CHANNEL_LABEL[key].lower()} sales channel",
    }
    best: tuple[float, int, str, int] | None = None
    for by, key_of, _ in GROUPS:
        if by not in places:
            continue
        for key, members in _grouped(completed, key_of).items():
            count = sum(rule in _flagged(s) for s in members)
            if len(members) >= MIN_GROUP and count and (best is None or count / len(members) > best[0]):
                best = (count / len(members), count, places[by](key), len(members))
    if best is None:
        return None
    _, count, place, n = best
    return f"highest at {place}: {count} of {n} completed calls"


def policy_review(batch: Batch, rows: Sequence[RuleFinding]) -> tuple[PolicyItem, ...]:
    """The understanding rules with at least one flagged call, most common first."""
    completed = batch.completed
    return tuple(
        PolicyItem(
            rule_id=r.rule_id,
            sentence=f"{r.flagged.count} of {r.flagged.n} customers who completed the call {r.statement}",
            value=r.flagged,
            highest=_highest(completed, r.rule_id),
        )
        for r in rows
        if r.understanding and r.flagged.count
    )


def _coverage(batch: Batch) -> str:
    book = batch.meta.book
    if not batch.draws:
        return "No loans have been drawn yet."
    days = sorted(d.as_of for d in batch.draws)
    return (
        f"This batch covers {len(days)} draw(s) made between {_day(days[0])} and {_day(days[-1])}: "
        f"{len(batch.sampled)} of the {book.loans} loans on the book (sold {_day(book.sold_from)} to "
        f"{_day(book.sold_to)}) were sampled. It does not cover the rest of the period."
    )


def build_report(store: OpsStore, now: datetime) -> ReportView:
    """The report for the batch in `store`, as of `now`."""
    batch = load_batch(store)
    meta = batch.meta
    rule_rows = findings(batch)
    referral_rows, established = referrals(batch)
    return ReportView(
        batch=batch_view(batch),
        generated_at=now,
        paragraph=CLAUSES[meta.book.lender_type][RuleId.kind],
        period_label=f"{_day(meta.period_start)} to {_day(meta.period_end)}",
        coverage=_coverage(batch),
        limits=wording.LIMITS,
        draws=draw_views(batch),
        funnel=funnel(batch),
        timing=timing(batch),
        tiers=tiers(batch),
        findings=rule_rows,
        referrals=referral_rows,
        established_of_decided=established,
        breakdowns=breakdowns(batch),
        policy_review=policy_review(batch, rule_rows),
    )
