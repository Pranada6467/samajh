"""The half-yearly report: counts over one batch, each with its n, and a Wilson 95% interval where
the count is a share of a random sample whose eligible sales had about the same chance of being drawn
(`NARROW_RATIO`). When the draws gave them clearly different chances, every share is shown with no
interval and the sampling statement says why (`sampling`).

Every count comes from the store's own files (book, draws, attempts, calls, dispositions, calls
outside the sample) through `load_batch`, never from the simulation's hidden truth. The
definitions are in the docstrings below so that a reader can recount them from the raw files.
"""

import math
import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from typing import Literal

from samajh.ops import wording
from samajh.ops.batch import Batch, Sampled, load_batch
from samajh.ops.model import WINDOW_DAYS, AttemptOutcome, Decision, Draw, FinalStatus, PhoneSession
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
    ReferralSplit,
    ReportTiles,
    ReportView,
    RuleRow,
    Sampling,
    TierRow,
    Timing,
    batch_view,
    draw_views,
    plain_share,
    proportion,
    referral_split,
)
from samajh.rules import CLAUSES
from samajh.types import Basis, RuleId, Tier

MIN_GROUP = 5  # a branch or channel is named as "highest" only with at least this many completed calls
GROUP_ORDER = ("features", "risks", "sale")
IST = timezone(timedelta(hours=5, minutes=30))

# The chances of being drawn count as "about the same" when the highest is at most this many times the
# lowest; only then do unweighted shares carry intervals. Why 1.25: at a ratio r, the unweighted share
# of a mix of two groups is off by at most (sqrt(r) - 1) / (sqrt(r) + 1) of the difference between the
# groups' shares (5.6% of that difference at r = 1.25), and the Kish design effect of weighting is at
# most (1 + r)^2 / (4r) = 1.0125, so an unweighted interval is under 1% too narrow. Exact: narrow or wide
# is decided on the draws' counts as fractions (`_chances`), never on floats, which put 5/12 over 1/3
# at 1.2500000000000002.
NARROW_RATIO = Fraction(5, 4)
_BIAS_BOUND = (math.sqrt(NARROW_RATIO) - 1) / (math.sqrt(NARROW_RATIO) + 1)  # 0.0557

Share = Callable[[int, int], Proportion]  # `proportion` (with an interval) or `plain_share` (without)


def _day(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


def _flagged(s: Sampled) -> set[RuleId]:
    return {flag.rule_id for flag in s.call.result.all_flags()}


def funnel(batch: Batch, share: Share = proportion) -> Funnel:
    """Sampled: every drawn loan of every draw. Each stage is a share of sampled.

    attempted: at least one attempt. reached: any attempt whose outcome is not no_answer.
    right party confirmed: any attempt with `right_party_confirmed`. completed: completed within
    30 days of the sale and analysed (`FinalStatus.completed`). Exits: one row per other final
    status (see `Sampled.status`). Completed plus the exits equals sampled. An exit row's
    `not_counted` is how many of its loans end on a request said in a call that was not counted
    (`Sampled.ended_by_uncounted_call`).
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
    uncounted = Counter(s.status for s in sampled if s.ended_by_uncounted_call)
    assert stages["completed"] + sum(exits.values()) == n, "every sampled loan has exactly one final status"
    return Funnel(
        sampled=n,
        attempts=sum(len(s.attempts) for s in sampled),
        stages=tuple(
            FunnelRow(key=key, label=wording.STAGE_LABEL[key], value=share(count, n))
            for key, count in stages.items()
        ),
        exits=tuple(
            FunnelRow(
                key=status.value,
                label=wording.STATUS_LABEL[status],
                value=share(count, n),
                not_counted=uncounted[status],
            )
            for status, count in exits.items()
        ),
    )


def sampling(batch: Batch) -> Sampling:
    """Sales in the period: book loans sold from period start to period end. Eligible: in some
    draw's eligible list. Each never-eligible sale gets one reason: sold before the first draw's
    window, sold after the last draw, or sold in a gap of more than 30 days between two draws.

    The chance of being drawn is each draw's drawn / eligible (`Draw.inclusion`); the range is over
    draws with an eligible sale. `intervals_shown` is False when the range is wide (`_chances`)."""
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
    rates = [Fraction(len(d.drawn), len(d.eligible)) for d in draws if d.eligible]
    n_eligible = sum(loan_id in eligible for loan_id, _ in in_period)
    exact_low, exact_high = (min(rates), max(rates)) if rates else (None, None)
    chances = _chances(exact_low, exact_high)
    # floats from here on, for display only
    low = float(exact_low) if exact_low is not None else None
    high = float(exact_high) if exact_high is not None else None
    ratio = float(exact_high / exact_low) if exact_low and exact_high is not None else None
    return Sampling(
        sales_in_period=len(in_period),
        eligible=n_eligible,
        sampled=len(batch.sampled),
        never_eligible=tuple(NeverEligible(reason=r, count=c) for r, c in reasons.most_common()),
        inclusion_low=low,
        inclusion_high=high,
        inclusion_ratio=ratio,
        chances=chances,
        intervals_shown=chances != "wide",
        statement=_sampling_statement(
            draws, chances, low, high, ratio, n_eligible, len(in_period) - n_eligible
        ),
    )


def _chances(low: Fraction | None, high: Fraction | None) -> Literal["none", "narrow", "wide"]:
    """From the lowest and highest chance of being drawn, each a draw's drawn over eligible as an
    exact fraction. none: no sale could be drawn (no draw, no eligible sale, or none drawn); narrow:
    the highest is at most `NARROW_RATIO` times the lowest; wide: otherwise, including a lowest of 0."""
    if low is None or high is None or high == 0:
        return "none"
    return "narrow" if low > 0 and high <= NARROW_RATIO * low else "wide"


def _sampling_statement(
    draws: Sequence[Draw],
    chances: str,
    low: float | None,
    high: float | None,
    ratio: float | None,
    n_eligible: int,
    never: int,
) -> str:
    """The sampling statement. It says "about the same chance" only when the chances are narrow, and
    always gives the range of chances when there is one."""
    if not draws:
        return "No draw has been made yet, so no sale has been sampled and no share describes a sample."
    shares = " or ".join(f"{r:.0%}" for r in sorted({d.rate for d in draws}))
    how = (
        f"Each draw took {shares} of the sales made since the previous draw that were still within 30 days "
        "of the sale, so draw windows never overlap."
    )
    uncovered = f"The {never} sale(s) in the period that no draw covered are not represented."
    if chances == "none":
        return (
            f"{how} No eligible sale was drawn ({n_eligible} sale(s) were eligible), so no share describes a "
            f"sample. {uncovered}"
        )
    assert low is not None and high is not None
    span = f"{low:.1%}" if low == high else f"between {low:.1%} and {high:.1%}"
    if chances == "narrow":
        assert ratio is not None
        return (
            f"{how} Every eligible sale had about the same chance of being sampled: {span} (the highest is "
            f"{ratio:.2f} times the lowest, within the {float(NARROW_RATIO):.2f} this report allows). Shares and "
            f"intervals describe the {n_eligible} eligible sales only. {uncovered} Shares are unweighted: "
            f"with chances this close, weighting would move a share by at most {_BIAS_BOUND:.1%} of the "
            "difference between the groups it mixes and widen an interval by under 1%."
        )
    times = (
        f"the highest is {ratio:.2f} times the lowest" if ratio else "some eligible sales could not be drawn"
    )
    return (
        f"{how} The chance of being sampled differed between eligible sales: {span} ({times}; this report "
        f"shows intervals only when the highest is at most {float(NARROW_RATIO):.2f} times the lowest). The shares "
        "in this report are unweighted counts of the calls analysed. Sales with a higher chance of being "
        "drawn are over-represented in them, so they do not estimate the share among all sales in the "
        f"period. For that reason no interval is shown on any share. {uncovered}"
    )


def timing(batch: Batch) -> Timing:
    """Days since the sale on the day of an attempt.

    first_attempt_days: minimum, median (the lower middle value of an even count) and maximum of
    the first attempt's day, over attempted loans. attempts_after_window: attempts on day 31 or
    later, of every attempt; the simulator makes none, so they are phone calls
    (phone_attempts_after_window), logged and never counted. completed_late: loans whose call
    completed after day 30.
    """
    first = sorted(s.attempts[0].day_since_sale for s in batch.sampled if s.attempts)
    attempts = [a for s in batch.sampled for a in s.attempts]
    after = [a for a in attempts if a.day_since_sale > WINDOW_DAYS]
    phone = sum(isinstance(a.source, PhoneSession) for a in after)
    return Timing(
        first_attempt_days=(first[0], statistics.median_low(first), first[-1]) if first else None,
        attempted=len(first),
        attempts_after_window=Count(count=len(after), n=len(attempts)),
        phone_attempts_after_window=phone,
        completed_late=len(batch.late),
        note=wording.window_note(len(after), phone, len(attempts)),
    )


def tiers(batch: Batch, share: Share = proportion) -> tuple[TierRow, ...]:
    """The tier of each counted call (completed within 30 days of the sale and analysed). The refer
    row also splits its count by what each referral rests on."""
    completed = batch.completed
    return tuple(
        TierRow(
            tier=tier,
            label=wording.TIER_LABEL[tier],
            value=share(sum(s.triage.tier is tier for s in completed), len(completed)),
            referred_split=referral_split(s.triage for s in completed) if tier is Tier.refer else None,
        )
        for tier in Tier
    )


def rule_rows(batch: Batch, share: Share = proportion) -> tuple[RuleRow, ...]:
    """One row per rule, over the counted calls.

    flagged: calls with at least one flag under the rule; n is every counted call. undecided:
    calls with a gap under the rule and no flag under it. referred: flagged calls whose summary
    has a `refer` line naming the rule. referred_split: those referred calls by the basis of the
    rule's own refer lines (record_only when every refer line naming the rule rests on the record
    alone; see `RuleRow`). The `evidence` rule appears only if it flagged or left a gap. Rows are grouped (features, risks, how it was sold), then by seriousness, then by share.
    """
    completed = batch.completed
    clauses = CLAUSES[batch.meta.book.lender_type]
    rows: list[RuleRow] = []
    for rule in RuleId:
        flagged = [s for s in completed if rule in _flagged(s)]
        refer_lines = [
            [line for line in s.triage.lines if rule in line.rule_ids and line.tier is Tier.refer]
            for s in flagged
        ]
        referred = [lines for lines in refer_lines if lines]
        on_statement = sum(
            any(line.basis is Basis.customer_statement for line in lines) for lines in referred
        )
        undecided = sum(
            rule not in _flagged(s) and any(g.rule_id is rule for g in s.call.result.all_gaps())
            for s in completed
        )
        if rule is RuleId.evidence and not flagged and not undecided:
            continue
        rows.append(
            RuleRow(
                rule_id=rule,
                rule_label=wording.RULE_LABEL[rule],
                may_engage=wording.may_engage(clauses[rule]),
                statement=wording.RULE_STATEMENT[rule],
                group=wording.GROUP[rule],
                seriousness=wording.SERIOUSNESS[rule],
                seriousness_label=wording.SERIOUSNESS_LABEL[wording.SERIOUSNESS[rule]],
                flagged=share(len(flagged), len(completed)),
                undecided=undecided,
                referred=len(referred),
                referred_split=ReferralSplit(
                    customer_statement=on_statement, record_only=len(referred) - on_statement
                ),
                understanding_gap=sum(
                    s.triage.tier is Tier.understanding_gap
                    and any(
                        rule in line.rule_ids and line.tier is Tier.understanding_gap
                        for line in s.triage.lines
                    )
                    for s in completed
                ),
                previous=None,
            )
        )
    return tuple(
        sorted(rows, key=lambda r: (GROUP_ORDER.index(r.group), r.seriousness, -(r.flagged.share or 0)))
    )


def referrals(
    batch: Batch,
) -> tuple[tuple[DispositionRow, ...], Count, Count, ReferralSplit, ReferralSplit]:
    """Counted referrals by the decision that stands (the latest recorded), plus "none" for no
    decision yet; n is every counted referral. Then the open referrals (no final decision: the
    page header's count), and "supported" out of the referrals whose latest decision is final."""
    ids = tuple(s.call.call_id for s in batch.referrals)
    latest = [batch.latest(case_id) for case_id in ids]
    n = len(latest)
    stands = list(zip(batch.referrals, latest, strict=True))

    def row(key: str, label: str, chosen: list[Sampled]) -> DispositionRow:
        return DispositionRow(
            key=key,
            label=label,
            value=Count(count=len(chosen), n=n),
            split=referral_split(s.triage for s in chosen),
        )

    rows = [
        row(
            decision.value,
            wording.DECISION_LABEL[decision],
            [s for s, d in stands if d is not None and d.decision is decision],
        )
        for decision in Decision
    ]
    rows.append(row("none", wording.NO_DECISION_LABEL, [s for s, d in stands if d is None]))
    supported = sum(d is not None and d.decision is Decision.concern_supported for d in latest)
    decided = n - batch.open(ids)
    decided_split = referral_split(s.triage for s in batch.referrals if batch.decided(s.call.call_id))
    supported_split = referral_split(
        s.triage for s, d in stands if d is not None and d.decision is Decision.concern_supported
    )
    return (
        tuple(rows),
        Count(count=batch.open(ids), n=n),
        Count(count=supported, n=decided),
        decided_split,
        supported_split,
    )


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


def breakdowns(batch: Batch, share: Share = proportion) -> tuple[Breakdown, ...]:
    """By loan type, branch and sales channel. Each row's shares are of its own counted calls, set
    against the same share over every other row together."""
    counted = batch.completed

    def tier_share(members: Sequence[Sampled], tier: Tier) -> Proportion:
        return share(sum(s.triage.tier is tier for s in members), len(members))

    def row(key: str, label: str, members: list[Sampled], key_of: Callable[[Sampled], str]) -> BreakdownRow:
        mine = [s for s in members if s.counted]
        rest = [s for s in counted if key_of(s) != key]
        return BreakdownRow(
            key=key,
            label=label,
            sampled=len(members),
            completed=len(mine),
            referred=tier_share(mine, Tier.refer),
            rest_referred=tier_share(rest, Tier.refer),
            referred_split=referral_split(s.triage for s in mine),
            rest_referred_split=referral_split(s.triage for s in rest),
            understanding_gap=tier_share(mine, Tier.understanding_gap),
            rest_understanding_gap=tier_share(rest, Tier.understanding_gap),
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


def _highest(completed: Sequence[Sampled], rule: RuleId, share: Share = proportion) -> str | None:
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
                mine_p = share(count, len(members))
                rest_p = share(sum(rule in _flagged(s) for s in rest), len(rest))
                best = (count / len(members), name(key), mine_p, rest_p, others)
    if best is None:
        return None
    _, place, mine, rest, others = best
    return (
        f"highest at {place}: {mine.count} of {mine.n} counted calls ({_pct(mine)}), against "
        f"{rest.count} of {rest.n} at {others} ({_pct(rest)})"
    )


def _pct(p: Proportion) -> str:
    """The interval in words, or the plain share when the report withholds intervals."""
    if not p.n or p.share is None:
        return "no calls"
    if p.low is None or p.high is None:
        return f"{p.share:.0%}"
    return f"95% interval {p.low:.0%} to {p.high:.0%}"


def policy_review(batch: Batch, rows: Sequence[RuleRow], share: Share = proportion) -> tuple[PolicyItem, ...]:
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
            highest=_highest(completed, r.rule_id, share),
        )
        for r in flagged
    )


def tiles(
    notice: str, chosen: Sampling, reach: Funnel, outcomes: Sequence[TierRow], rules: Sequence[RuleRow]
) -> ReportTiles:
    """The counts at the top of the page, taken from the same fields the tables below show, so they
    agree by construction. The most common gap is the rule row with the most understanding-gap
    calls; on a tie, the one higher in the rules table. "none" when no counted call has one."""
    tier = {row.tier: row.value.count for row in outcomes}
    (refer_row,) = (row for row in outcomes if row.tier is Tier.refer)
    assert refer_row.referred_split is not None  # the refer row always carries one
    top = max(rules, key=lambda r: r.understanding_gap, default=None)  # max keeps the first of a tie
    if top is None or top.understanding_gap == 0:
        gap, count = Labelled(key="none", label=wording.NO_GAP), 0
    else:
        gap, count = Labelled(key=top.rule_id.value, label=top.rule_label), top.understanding_gap
    return ReportTiles(
        synthetic=notice,
        sold=chosen.sales_in_period,
        sampled=chosen.sampled,
        completed=next(row.value.count for row in reach.stages if row.key == "completed"),
        referred=tier[Tier.refer],
        referred_split=refer_row.referred_split,
        understanding_gap=tier[Tier.understanding_gap],
        most_common_gap=gap,
        most_common_gap_count=count,
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
    chosen = sampling(batch)
    share: Share = proportion if chosen.intervals_shown else plain_share
    rules = rule_rows(batch, share)
    referral_rows, open_referrals, supported, decided_split, supported_split = referrals(batch)
    attempts = [a for s in batch.sampled for a in s.attempts]
    phone_attempts = sum(isinstance(a.source, PhoneSession) for a in attempts)
    limits = wording.limits(
        chosen.intervals_shown,
        simulated=len(attempts) - phone_attempts,
        phone_attempts=phone_attempts,
        phone_outside=len(batch.outside),
        phone_note=wording.phone_note(batch.phone_sessions),
    )
    header = batch_view(batch)
    reach = funnel(batch, share)
    outcomes = tiers(batch, share)
    return ReportView(
        tiles=tiles(header.simulated_notice, chosen, reach, outcomes, rules),
        batch=header,
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
        sampling=chosen,
        funnel=reach,
        timing=timing(batch),
        tiers=outcomes,
        groups=tuple(Labelled(key=g, label=wording.GROUP_LABEL[g]) for g in GROUP_ORDER),
        risk_note=wording.RISK_NOTE,
        seriousness_note=wording.SERIOUSNESS_NOTE,
        rules=rules,
        referrals=referral_rows,
        open_referrals=open_referrals,
        supported_of_decided=supported,
        decided_split=decided_split,
        supported_split=supported_split,
        other_referrals=len(batch.other_referrals),
        open_referrals_split=header.open_split,
        other_referrals_split=header.other_referrals_split,
        basis_note=wording.BASIS_NOTE,
        rule_split_note=wording.RULE_SPLIT_NOTE,
        outside_calls=len(batch.outside),
        phone_sessions_not_ingested=len(batch.ingest.skipped) if batch.ingest else None,
        phone_sessions_changed=len(batch.ingest.changed) if batch.ingest else None,
        ingest_note=wording.ingest_note(batch.ingest),
        breakdowns=breakdowns(batch, share),
        policy_review=policy_review(batch, rules, share),
    )
