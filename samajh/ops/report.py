"""The half-yearly report: counts over one batch, each with its n, and a Wilson 95% interval where
the count is a share of a random sample.

Every count comes from the store's own files (book, draws, attempts, calls, dispositions, calls
outside the sample) through `load_batch`, never from the simulation's hidden truth. The
definitions are in the docstrings below so that a reader can recount them from the raw files.
"""

import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta, timezone

from samajh.ops import wording
from samajh.ops.batch import Batch, Sampled, load_batch
from samajh.ops.model import WINDOW_DAYS, AttemptOutcome, Decision, FinalStatus, PhoneSession
from samajh.ops.store import OpsStore
from samajh.ops.views import (
    Breakdown,
    BreakdownRow,
    Count,
    DispositionRow,
    Funnel,
    FunnelRow,
    Labelled,
    NeverEligible,
    PolicyItem,
    Proportion,
    ReportView,
    RuleFinding,
    Sampling,
    TierRow,
    Timing,
    batch_view,
    draw_views,
    proportion,
)
from samajh.rules import CLAUSES
from samajh.types import RuleId, Tier

MIN_GROUP = 5  # a branch or channel is named as "highest" only with at least this many completed calls
GROUP_ORDER = ("features", "risks", "sale")
IST = timezone(timedelta(hours=5, minutes=30))


def _day(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


def _flagged(s: Sampled) -> set[RuleId]:
    return {flag.rule_id for flag in s.call.result.all_flags()}


def funnel(batch: Batch) -> Funnel:
    """Sampled: every drawn loan of every draw. Each stage is a share of sampled.

    attempted: at least one attempt. reached: any attempt whose outcome is not no_answer.
    right party confirmed: any attempt with `right_party_confirmed`. completed: completed within
    30 days of the sale and analysed (`FinalStatus.completed`). Exits: one row per other final
    status (see `Sampled.status`). Completed plus the exits equals sampled.
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


def sampling(batch: Batch) -> Sampling:
    """Sales in the period: book loans sold from period start to period end. Eligible: in some
    draw's eligible list. Each never-eligible sale gets one reason: sold before the first draw's
    window, sold after the last draw, or sold in a gap of more than 30 days between two draws."""
    meta, draws = batch.meta, batch.draws
    in_period = [
        (loan.record.loan_id, loan.sold_on)
        for loan in batch.book
        if meta.period_start <= loan.sold_on <= meta.period_end
    ]
    eligible = {loan_id for d in draws for loan_id in d.eligible}
    reasons: Counter[str] = Counter()
    for loan_id, sold in in_period:
        if loan_id in eligible:
            continue
        if not draws:
            reasons["no draw has been made"] += 1
        elif sold < draws[0].as_of - timedelta(days=draws[0].max_day):
            reasons["sold more than 30 days before the first draw"] += 1
        elif sold > draws[-1].as_of:
            reasons["sold after the last draw"] += 1
        else:
            reasons["sold in a gap of more than 30 days between two draws"] += 1
    rates = [d.inclusion for d in draws if d.inclusion is not None]
    shares = sorted({d.rate for d in draws})
    n_eligible = sum(loan_id in eligible for loan_id, _ in in_period)
    sampled = len(batch.sampled)
    never = len(in_period) - n_eligible
    statement = (
        f"Each draw took {' or '.join(f'{r:.0%}' for r in shares) or 'a share'} of the sales made since the "
        "previous draw that were still within 30 days of the sale, so draw windows never overlap and every "
        "eligible sale had about the same chance of being sampled"
        + (f" (between {min(rates):.1%} and {max(rates):.1%}, by rounding)" if rates else "")
        + f". Shares and intervals describe the {n_eligible} eligible sales only; the {never} sale(s) no draw "
        "covered are not represented. Shares are unweighted because the chances are equal up to rounding."
    )
    return Sampling(
        sales_in_period=len(in_period),
        eligible=n_eligible,
        sampled=sampled,
        never_eligible=tuple(NeverEligible(reason=r, count=c) for r, c in reasons.most_common()),
        inclusion_low=min(rates) if rates else None,
        inclusion_high=max(rates) if rates else None,
        statement=statement,
    )


def timing(batch: Batch) -> Timing:
    """Days since the sale on the day of an attempt.

    first_attempt_days: minimum, median (the lower middle value of an even count) and maximum of
    the first attempt's day, over attempted loans. attempts_after_window: attempts on day 31 or
    later, of every attempt (none by design). completed_late: loans whose call completed after day 30.
    """
    first = sorted(s.attempts[0].day_since_sale for s in batch.sampled if s.attempts)
    attempts = [a for s in batch.sampled for a in s.attempts]
    return Timing(
        first_attempt_days=(first[0], statistics.median_low(first), first[-1]) if first else None,
        attempted=len(first),
        attempts_after_window=Count(
            count=sum(a.day_since_sale > WINDOW_DAYS for a in attempts), n=len(attempts)
        ),
        completed_late=len(batch.late),
    )


def tiers(batch: Batch) -> tuple[TierRow, ...]:
    """The tier of each counted call (completed within 30 days of the sale and analysed)."""
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
    """One row per rule, over the counted calls.

    flagged: calls with at least one flag under the rule; n is every counted call. undecided:
    calls with a gap under the rule and no flag under it. referred: flagged calls whose summary
    has a `refer` line naming the rule. The `evidence` rule appears only if it flagged or left a
    gap. Rows are grouped (features, risks, how it was sold), then by seriousness, then by share.
    """
    completed = batch.completed
    clauses = CLAUSES[batch.meta.book.lender_type]
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
                group=wording.GROUP[rule],
                seriousness=wording.SERIOUSNESS[rule],
                seriousness_label=wording.SERIOUSNESS_LABEL[wording.SERIOUSNESS[rule]],
                flagged=proportion(len(flagged), len(completed)),
                undecided=undecided,
                referred=sum(
                    any(rule in line.rule_ids and line.tier is Tier.refer for line in s.triage.lines)
                    for s in flagged
                ),
                previous=None,
            )
        )
    return tuple(
        sorted(rows, key=lambda r: (GROUP_ORDER.index(r.group), r.seriousness, -(r.flagged.share or 0)))
    )


def referrals(batch: Batch) -> tuple[tuple[DispositionRow, ...], Count, Count]:
    """Counted referrals by the decision that stands (the latest recorded), plus "none" for no
    decision yet; n is every counted referral. Then the open referrals (no final decision: the
    page header's count), and "supported" out of the referrals whose latest decision is final."""
    ids = tuple(s.call.call_id for s in batch.referrals)
    latest = [batch.latest(case_id) for case_id in ids]
    n = len(latest)
    rows = [
        DispositionRow(
            key=decision.value,
            label=wording.DECISION_LABEL[decision],
            value=Count(count=sum(d is not None and d.decision is decision for d in latest), n=n),
        )
        for decision in Decision
    ]
    rows.append(
        DispositionRow(
            key="none", label=wording.NO_DECISION_LABEL, value=Count(count=latest.count(None), n=n)
        )
    )
    supported = sum(d is not None and d.decision is Decision.concern_supported for d in latest)
    decided = n - batch.open(ids)
    return tuple(rows), Count(count=batch.open(ids), n=n), Count(count=supported, n=decided)


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
    """By loan type, branch and sales channel. Each row's shares are of its own counted calls, set
    against the same share over every other row together."""
    counted = batch.completed

    def share(members: Sequence[Sampled], tier: Tier) -> Proportion:
        return proportion(sum(s.triage.tier is tier for s in members), len(members))

    def row(key: str, label: str, members: list[Sampled], key_of: Callable[[Sampled], str]) -> BreakdownRow:
        mine = [s for s in members if s.counted]
        rest = [s for s in counted if key_of(s) != key]
        return BreakdownRow(
            key=key,
            label=label,
            sampled=len(members),
            completed=len(mine),
            referred=share(mine, Tier.refer),
            rest_referred=share(rest, Tier.refer),
            understanding_gap=share(mine, Tier.understanding_gap),
            rest_understanding_gap=share(rest, Tier.understanding_gap),
        )

    return tuple(
        Breakdown(
            by=by,
            label=wording.BREAKDOWN_LABEL[by],
            rows=tuple(
                row(key, label(key), members, key_of)
                for key, members in _grouped(batch.sampled, key_of).items()
            ),
        )
        for by, key_of, label in GROUPS
    )


def _highest(completed: Sequence[Sampled], rule: RuleId) -> str | None:
    """The branch or channel with the highest share of calls flagged under `rule`, among those
    with at least `MIN_GROUP` counted calls, set against all the others. None when none qualifies."""
    places = {
        "branch": (lambda key: f"branch {key}", "the other branches"),
        "channel": (
            lambda key: f"the {wording.CHANNEL_LABEL[key].lower()} sales channel",
            "the other channels",
        ),
    }
    best: tuple[float, str, Proportion, Proportion, str] | None = None
    for by, key_of, _ in GROUPS:
        if by not in places:
            continue
        name, others = places[by]
        for key, members in _grouped(completed, key_of).items():
            count = sum(rule in _flagged(s) for s in members)
            rest = [s for s in completed if key_of(s) != key]
            if len(members) >= MIN_GROUP and count and (best is None or count / len(members) > best[0]):
                mine_p = proportion(count, len(members))
                rest_p = proportion(sum(rule in _flagged(s) for s in rest), len(rest))
                best = (count / len(members), name(key), mine_p, rest_p, others)
    if best is None:
        return None
    _, place, mine, rest, others = best
    return (
        f"highest at {place}: {mine.count} of {mine.n} counted calls ({_pct(mine)}), against "
        f"{rest.count} of {rest.n} at {others} ({_pct(rest)})"
    )


def _pct(p: Proportion) -> str:
    return f"95% interval {p.low:.0%} to {p.high:.0%}" if p.n else "no calls"


def policy_review(batch: Batch, rows: Sequence[RuleFinding]) -> tuple[PolicyItem, ...]:
    """Every rule with at least one flagged call: the most serious first, then the most common."""
    completed = batch.completed
    flagged = sorted((r for r in rows if r.flagged.count), key=lambda r: (r.seriousness, -r.flagged.count))
    return tuple(
        PolicyItem(
            rule_id=r.rule_id,
            group=r.group,
            seriousness_label=r.seriousness_label,
            sentence=f"{r.flagged.count} of {r.flagged.n} customers who completed the call {r.statement}",
            value=r.flagged,
            highest=_highest(completed, r.rule_id),
        )
        for r in flagged
    )


def _reading(batch: Batch) -> tuple[Labelled, ...]:
    """How the counted calls were made and read, e.g. "Simulated (scripted transcript), read by X"."""
    seen: Counter[str] = Counter()
    for s in batch.completed:
        how = "Phone call" if isinstance(s.call.source, PhoneSession) else "Simulated (scripted transcript)"
        seen[f"{how}, read by {s.call.analysis}"] += 1
    return tuple(Labelled(key=k, label=f"{c} calls") for k, c in seen.most_common())


def _as_of(batch: Batch) -> date:
    """The book's clock: the day of the last attempt, else of the last draw, else the period start."""
    days = [a.at.astimezone(IST).date() for s in batch.sampled for a in s.attempts]
    if days:
        return max(days)
    return batch.draws[-1].as_of if batch.draws else batch.meta.period_start


def _coverage(batch: Batch) -> str:
    book = batch.meta.book
    if not batch.draws:
        return "No loans have been drawn yet."
    days = sorted(d.as_of for d in batch.draws)
    return (
        f"This batch covers {len(days)} draw(s) made between {_day(days[0])} and {_day(days[-1])}: "
        f"{len(batch.sampled)} of the {book.loans} loans on the book (sold {_day(book.sold_from)} to "
        f"{_day(book.sold_to)}) were sampled."
    )


def build_report(store: OpsStore, now: datetime | None = None) -> ReportView:
    """The report for the batch in `store`. It is dated by the book's clock, not by `now`."""
    batch = load_batch(store)
    meta = batch.meta
    rule_rows = findings(batch)
    referral_rows, open_referrals, supported = referrals(batch)
    limits = wording.LIMITS if batch.simulated else (*wording.LIMITS, wording.PHONE_LIMIT)
    return ReportView(
        batch=batch_view(batch),
        as_of=_as_of(batch),
        as_of_note=wording.AS_OF_NOTE,
        paragraph=CLAUSES[meta.book.lender_type][RuleId.kind],
        period_label=f"{_day(meta.period_start)} to {_day(meta.period_end)}",
        unit=meta.unit,
        reading=_reading(batch),
        coverage=_coverage(batch),
        limits=limits,
        previous_period=None,
        draws=draw_views(batch),
        sampling=sampling(batch),
        funnel=funnel(batch),
        timing=timing(batch),
        tiers=tiers(batch),
        groups=tuple(Labelled(key=g, label=wording.GROUP_LABEL[g]) for g in GROUP_ORDER),
        risk_note=wording.RISK_NOTE,
        seriousness_note=wording.SERIOUSNESS_NOTE,
        findings=rule_rows,
        referrals=referral_rows,
        open_referrals=open_referrals,
        supported_of_decided=supported,
        other_referrals=len(batch.other_referrals),
        outside_calls=len(batch.outside),
        breakdowns=breakdowns(batch),
        policy_review=policy_review(batch, rule_rows),
    )
