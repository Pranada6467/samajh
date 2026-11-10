"""What the review pages read: the JSON contract between `samajh/server/review_routes.py` and
`web/review/`. Every label a page shows for a rule, tier, outcome or decision comes from here
(through `samajh.ops.wording`), so the wording rules are checked in one place.

    GET  /api/review/batch                      -> BatchView
    GET  /api/review/queue                      -> QueueView      only `refer` cases, most severe first
    GET  /api/review/cases/{case_id}            -> CaseView       404 unless the case is a referral
    POST /api/review/cases/{case_id}/disposition   body DispositionIn -> CaseView
    GET  /api/review/attempts                   -> AttemptLogView the sample, every attempt, calls outside it
    GET  /api/review/draws                      -> list[Draw]     the selection audit, verbatim
    GET  /api/review/report                     -> ReportView

Every count that is a share of a sample is a `Proportion` (with its interval); a count of reviewer
decisions is a `Count` (no interval: the decisions are not a sample). No number is shown without its n.
"""

from datetime import date, datetime
from pathlib import Path

from samajh.evalkit.score import wilson
from samajh.ops import wording
from samajh.ops.batch import Batch, Outside, Sampled, load_batch
from samajh.ops.model import (
    FINAL_DECISIONS,
    AttemptOutcome,
    BatchMeta,
    CallRecord,
    CallSource,
    Channel,
    Decision,
    Disposition,
    FinalStatus,
    Note,
    PhoneSession,
    Reviewer,
    Triage,
)
from samajh.ops.store import OpsStore
from samajh.rules import IssueLine
from samajh.types import (
    Frozen,
    Language,
    LenderType,
    LoanKind,
    LoanRecord,
    Product,
    ProductId,
    RuleId,
    Severity,
    Speaker,
    Tier,
    Turn,
)


class Proportion(Frozen):
    """`count` of `n`, with the Wilson 95% interval. `share` and the bounds are None when n is 0."""

    count: int
    n: int
    share: float | None
    low: float | None
    high: float | None


class Count(Frozen):
    """`count` of `n`, with no interval."""

    count: int
    n: int


class Labelled(Frozen):
    """A code and the words a page shows for it."""

    key: str
    label: str


# --- batch, shown in the header of every page ---------------------------------


class BatchView(Frozen):
    meta: BatchMeta
    simulated: bool  # every call in the batch is simulated
    simulated_notice: str  # the sentence every page shows about what is synthetic or simulated
    access_notice: str  # no sign-in; reviewer names are free text
    sampled: int
    completed: int  # calls the findings count
    referred: int  # referrals the report counts
    open_cases: int  # of those, with no final decision (the report's "open" uses this definition)
    other_referrals: int  # referred calls outside the sample or the window: reviewed, not counted


# --- the queue ------------------------------------------------------------------


class DispositionView(Frozen):
    decision: Decision
    decision_label: str
    final: bool
    note: str
    reviewer: str
    recorded_at: datetime


class QueueItem(Frozen):
    case_id: str
    loan_id: str
    borrower: str
    language: Language
    branch: str | None  # None for a call outside the sample
    channel: Channel | None
    sold_on: date | None
    at: datetime  # when the call was made
    day_since_sale: int | None  # on the day of the call
    severity: Severity
    headline: str  # the first summary line, as one sentence
    refer_lines: int
    may_engage: tuple[str, ...]  # paragraphs, each once
    simulated: bool
    in_report: bool  # counted in the half-yearly report
    not_counted_because: str | None  # why the report does not count it
    disposition: DispositionView | None  # the latest, if any


class QueueView(Frozen):
    """Counted cases first, open ones first, each group by severity then the oldest call first.
    Then referrals the report does not count (outside the sample or the window)."""

    items: tuple[QueueItem, ...]


# --- one case -------------------------------------------------------------------


class QuoteView(Frozen):
    quote: str
    turn_id: int
    start_s: float | None  # position in the call recording, when the session has one
    end_s: float | None


class IssueLineView(Frozen):
    """One line of the deduplicated case summary (`samajh.rules.summarise`), with its words."""

    tier: Tier
    tier_label: str
    product_id: ProductId | None  # None for a case-level line
    title: str  # the issue, in one sentence
    record_value: str  # the record's side
    quote: QuoteView | None  # the customer's best quote
    rule_ids: tuple[RuleId, ...]
    rule_labels: tuple[str, ...]
    may_engage: tuple[str, ...]  # e.g. "may engage para 85G"; a check of our own adds nothing


class TurnView(Frozen):
    turn_id: int
    speaker: Speaker
    text: str
    start_s: float | None
    end_s: float | None
    cited: bool  # a summary line quotes this turn


class LoanView(Frozen):
    """The lender's record as the reviewer sees it. No date of birth."""

    loan_id: str
    borrower: str
    lender_type: LenderType
    loan_kind: LoanKind
    sanctioned_inr: int
    disbursed_inr: int
    sold_on: date | None  # None for a call outside the sample (the phone's record has no book row)
    branch: str | None
    channel: Channel | None
    products: tuple[Product, ...]


class CallView(Frozen):
    call_id: str
    source: CallSource
    simulated: bool
    language: Language
    at: datetime
    attempt_number: int | None  # None outside the sample
    day_since_sale: int | None
    analysis: str
    transcript_note: str | None
    recording_url: str | None  # "/api/sessions/<id>/recording.wav" for a phone session that kept call.wav


class CaseView(Frozen):
    case_id: str
    tier: Tier
    tier_label: str
    severity: Severity
    in_report: bool
    not_counted_because: str | None
    loan: LoanView
    call: CallView
    refer_lines: tuple[IssueLineView, ...]  # why the case is here
    other_lines: tuple[IssueLineView, ...]  # incomplete questions and understanding gaps on the same call
    undecided: tuple[Labelled, ...]  # rules that could not decide, with the reason as the label
    transcript: tuple[TurnView, ...]
    decisions: tuple[Labelled, ...]  # the choices the reviewer has, in order
    disposition: DispositionView | None
    history: tuple[DispositionView, ...]  # oldest first


class DispositionIn(Frozen):
    decision: Decision
    note: Note
    reviewer: Reviewer


# --- the attempt log ------------------------------------------------------------


class AttemptView(Frozen):
    number: int
    at: datetime
    day_since_sale: int
    outcome: AttemptOutcome
    outcome_label: str
    simulated: bool
    session_id: str | None


class SampledLoanView(Frozen):
    loan_id: str
    draw_id: str
    sold_on: date
    day_since_sale_at_draw: int
    language: Language
    branch: str
    channel: Channel
    attempts: tuple[AttemptView, ...]
    status: FinalStatus
    status_label: str
    tier: Tier | None  # set when a call was analysed
    tier_label: str | None
    case_id: str | None  # set when the call is a referral


class DrawView(Frozen):
    draw_id: str
    as_of: date
    after: date | None
    min_day: int
    max_day: int
    rate: float
    seed: int
    eligible: int
    drawn: int
    inclusion: float | None  # drawn over eligible
    verified: bool  # recomputed from the book, and the window starts where the previous one ended


class OutsideView(Frozen):
    session_id: str
    record_id: str
    loan_id: str
    reason: str
    at: datetime
    language: Language
    outcome: AttemptOutcome
    outcome_label: str
    dialogue_outcome: str
    tier: Tier | None
    tier_label: str | None
    case_id: str | None  # set when the call is a referral


class AttemptLogView(Frozen):
    draws: tuple[DrawView, ...]
    loans: tuple[SampledLoanView, ...]  # in draw order
    outside: tuple[OutsideView, ...]  # phone calls outside the sample: never in the statistics


# --- the half-yearly report ------------------------------------------------------


class FunnelRow(Frozen):
    key: str
    label: str
    value: Proportion  # n is the number sampled


class Funnel(Frozen):
    sampled: int
    attempts: int  # every attempt, retries included
    stages: tuple[FunnelRow, ...]  # attempted, reached, right party confirmed, completed in the window
    exits: tuple[FunnelRow, ...]  # one per other final status; with completed they sum to sampled


class NeverEligible(Frozen):
    reason: str
    count: int


class Sampling(Frozen):
    """Which sales could be sampled. Intervals elsewhere describe sampling among eligible sales only."""

    sales_in_period: int  # sales on the book made in the report period
    eligible: int  # of those, covered by a draw
    sampled: int
    never_eligible: tuple[NeverEligible, ...]  # with the reason; they sum to sales_in_period - eligible
    inclusion_low: float | None  # the smallest and largest draw's drawn / eligible
    inclusion_high: float | None
    statement: str


class Timing(Frozen):
    """Days from the sale. The rule's 30 days are counted to the attempt, not to the draw."""

    first_attempt_days: tuple[int, int, int] | None  # min, median, max over attempted loans
    attempted: int  # the n of first_attempt_days
    attempts_after_window: Count  # n is every attempt
    completed_late: int  # calls completed after day 30: shown apart, never in the findings


class TierRow(Frozen):
    tier: Tier
    label: str
    value: Proportion  # n is analysed calls


class RuleFinding(Frozen):
    """One rule over the analysed calls. `flagged` counts calls with at least one flag under the
    rule and its n is every analysed call (each rule runs on every call). `undecided` calls had a
    gap under the rule and no flag. `referred` of the flagged calls have a `refer` line for the rule."""

    rule_id: RuleId
    rule_label: str
    may_engage: str | None
    statement: str  # e.g. "could not state the cancellation window on the record"
    group: str  # "features", "risks" or "sale"
    seriousness: int  # 1 is the most serious
    seriousness_label: str
    flagged: Proportion
    undecided: int
    referred: int
    previous: Proportion | None  # the previous period's share; None when there is no previous period


class DispositionRow(Frozen):
    key: str  # a Decision value, or "none"
    label: str
    value: Count  # n is counted referrals


class BreakdownRow(Frozen):
    key: str
    label: str
    sampled: int
    completed: int
    referred: Proportion  # n is this row's completed calls
    rest_referred: Proportion  # every other row together
    understanding_gap: Proportion
    rest_understanding_gap: Proportion


class Breakdown(Frozen):
    by: str  # "loan_kind", "branch" or "channel"
    label: str
    rows: tuple[BreakdownRow, ...]


class PolicyItem(Frozen):
    """One finding put to the policy review, most serious first, then most common."""

    rule_id: RuleId
    group: str
    seriousness_label: str
    sentence: str  # "31 of 58 customers who completed the call could not state ..."
    value: Proportion
    highest: str | None  # the branch or channel with the highest share against the rest, as a phrase


class ReportView(Frozen):
    batch: BatchView
    as_of: date  # the book's clock: the day of the last attempt (synthetic)
    as_of_note: str
    paragraph: str  # "85Y" for a bank, "101Y" for an NBFC
    period_label: str  # "1 January 2027 to 30 June 2027"
    unit: str  # who ran the mechanism
    reading: tuple[Labelled, ...]  # how the calls were read: "<method>" -> "<count> calls"
    coverage: str  # what part of the period this batch covers, in a sentence
    limits: tuple[str, ...]  # what is simulated and what the numbers cannot show; printed on the page
    previous_period: str | None  # None: no previous period
    draws: tuple[DrawView, ...]
    sampling: Sampling
    funnel: Funnel
    timing: Timing
    tiers: tuple[TierRow, ...]
    groups: tuple[Labelled, ...]  # the finding groups in order, with their headings
    risk_note: str
    seriousness_note: str
    findings: tuple[RuleFinding, ...]  # every rule that returned an outcome, by group then seriousness
    referrals: tuple[DispositionRow, ...]
    open_referrals: Count  # no final decision; the same count as the page header
    supported_of_decided: Count  # n is referrals with a final decision
    other_referrals: int  # referred calls the report does not count
    outside_calls: int  # phone calls outside the sample
    breakdowns: tuple[Breakdown, ...]
    policy_review: tuple[PolicyItem, ...]


# --- building the views ------------------------------------------------------------

_RANK = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}
LATE = "completed after day 30 from the sale"


class NotAReferral(LookupError):
    """No referred call has this case id."""


def proportion(count: int, n: int) -> Proportion:
    """`count` of `n` with its Wilson 95% interval; no share and no bounds when n is 0."""
    if n == 0:
        return Proportion(count=count, n=0, share=None, low=None, high=None)
    low, high = wilson(count, n)
    return Proportion(count=count, n=n, share=count / n, low=low, high=high)


def batch_view(batch: Batch) -> BatchView:
    referrals = batch.referrals
    return BatchView(
        meta=batch.meta,
        simulated=batch.simulated,
        simulated_notice=wording.SIMULATED_NOTICE if batch.simulated else wording.MIXED_NOTICE,
        access_notice=wording.ACCESS_NOTICE,
        sampled=len(batch.sampled),
        completed=len(batch.completed),
        referred=len(referrals),
        open_cases=batch.open(tuple(s.call.call_id for s in referrals)),
        other_referrals=len(batch.other_referrals),
    )


def draw_views(batch: Batch) -> tuple[DrawView, ...]:
    return tuple(
        DrawView(
            draw_id=d.draw_id,
            as_of=d.as_of,
            after=d.after,
            min_day=d.min_day,
            max_day=d.max_day,
            rate=d.rate,
            seed=d.seed,
            eligible=len(d.eligible),
            drawn=len(d.drawn),
            inclusion=d.inclusion,
            verified=batch.verified[d.draw_id],
        )
        for d in batch.draws
    )


def _disposition_view(d: Disposition | None) -> DispositionView | None:
    if d is None:
        return None
    return DispositionView(
        decision=d.decision,
        decision_label=wording.DECISION_LABEL[d.decision],
        final=d.decision in FINAL_DECISIONS,
        note=d.note,
        reviewer=d.reviewer,
        recorded_at=d.recorded_at,
    )


def _simulated(source: CallSource) -> bool:
    return not isinstance(source, PhoneSession)


def _engaged(clauses: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(phrase for phrase in map(wording.may_engage, clauses) if phrase))


class _Case:
    """One referred call, sampled or not, as the queue and the case page need it."""

    def __init__(self, item: Sampled | Outside, counted: bool) -> None:
        if isinstance(item, Sampled):
            self.call: CallRecord = item.call
            self.triage: Triage = item.triage
            self.record: LoanRecord = item.loan.record
            self.loan = item.loan
            last = item.attempts[-1]
            self.at, self.day, self.number = last.at, last.day_since_sale, last.number
            self.why = None if counted else LATE
        else:
            self.call, self.triage, self.record, self.loan = item.record, item.triage, item.call.record, None
            self.at, self.day, self.number = item.call.at, None, None
            self.why = item.call.reason
        self.in_report = counted
        self.case_id = self.call.call_id


def _cases(batch: Batch) -> list[_Case]:
    return [_Case(s, True) for s in batch.referrals] + [_Case(o, False) for o in batch.other_referrals]


def _queue_item(batch: Batch, c: _Case) -> QueueItem:
    refer = [line for line in c.triage.lines if line.tier is Tier.refer]
    return QueueItem(
        case_id=c.case_id,
        loan_id=c.record.loan_id,
        borrower=c.record.borrower.name,
        language=c.call.transcript.language,
        branch=c.loan.branch if c.loan else None,
        channel=c.loan.channel if c.loan else None,
        sold_on=c.loan.sold_on if c.loan else None,
        at=c.at,
        day_since_sale=c.day,
        severity=c.triage.severity,
        headline=refer[0].title,
        refer_lines=len(refer),
        may_engage=_engaged(tuple(clause for line in refer for clause in line.clauses)),
        simulated=_simulated(c.call.source),
        in_report=c.in_report,
        not_counted_because=c.why,
        disposition=_disposition_view(batch.latest(c.case_id)),
    )


def queue_view(batch: Batch) -> QueueView:
    """Referrals only. Counted cases before the rest; open cases before decided ones; then the most
    severe first, then the oldest call first, then by loan id. (85Y sets no review deadline.)"""
    items = [_queue_item(batch, c) for c in _cases(batch)]
    items.sort(key=lambda i: (not i.in_report, batch.decided(i.case_id), _RANK[i.severity], i.at, i.loan_id))
    return QueueView(items=tuple(items))


def _line_view(line: IssueLine, turns: dict[int, Turn]) -> IssueLineView:
    quote = None
    if line.quote is not None and line.turn_id is not None:
        turn = turns.get(line.turn_id)
        start, end = (turn.start_s, turn.end_s) if turn else (None, None)
        quote = QuoteView(quote=line.quote, turn_id=line.turn_id, start_s=start, end_s=end)
    return IssueLineView(
        tier=line.tier,
        tier_label=wording.TIER_LABEL[line.tier],
        product_id=line.product_id,
        title=line.title,
        record_value=line.record_value,
        quote=quote,
        rule_ids=line.rule_ids,
        rule_labels=tuple(wording.RULE_LABEL[rule] for rule in line.rule_ids),
        may_engage=_engaged(line.clauses),
    )


def case_view(batch: Batch, case_id: str, sessions: Path | None = None) -> CaseView:
    """One referred call. Raises `NotAReferral` for any other id. `sessions`: where phone sessions
    keep call.wav, so the page can offer the recording."""
    c = next((c for c in _cases(batch) if c.case_id == case_id), None)
    if c is None:
        raise NotAReferral(case_id)
    record, call = c.record, c.call
    turns = {turn.id: turn for turn in call.transcript.turns}
    lines = [_line_view(line, turns) for line in c.triage.lines]
    cited = {line.turn_id for line in c.triage.lines if line.quote is not None}
    undecided = {
        (gap.rule_id, gap.reason): Labelled(
            key=gap.rule_id.value, label=f"{wording.RULE_LABEL[gap.rule_id]}: {wording.GAP_LABEL[gap.reason]}"
        )
        for gap in call.result.all_gaps()
    }
    session = call.source if isinstance(call.source, PhoneSession) else None
    has_wav = (
        session is not None
        and sessions is not None
        and (sessions / session.session_id / "call.wav").is_file()
    )
    return CaseView(
        case_id=case_id,
        tier=c.triage.tier,
        tier_label=wording.TIER_LABEL[c.triage.tier],
        severity=c.triage.severity,
        in_report=c.in_report,
        not_counted_because=c.why,
        loan=LoanView(
            loan_id=record.loan_id,
            borrower=record.borrower.name,
            lender_type=record.lender_type,
            loan_kind=record.loan_kind,
            sanctioned_inr=record.sanctioned_inr,
            disbursed_inr=record.disbursed_inr,
            sold_on=c.loan.sold_on if c.loan else None,
            branch=c.loan.branch if c.loan else None,
            channel=c.loan.channel if c.loan else None,
            products=record.products,
        ),
        call=CallView(
            call_id=call.call_id,
            source=call.source,
            simulated=session is None,
            language=call.transcript.language,
            at=c.at,
            attempt_number=c.number,
            day_since_sale=c.day,
            analysis=call.analysis,
            transcript_note=call.transcript_note,
            recording_url=f"/api/sessions/{session.session_id}/recording.wav" if has_wav else None,
        ),
        refer_lines=tuple(line for line in lines if line.tier is Tier.refer),
        other_lines=tuple(line for line in lines if line.tier is not Tier.refer),
        undecided=tuple(undecided.values()),
        transcript=tuple(
            TurnView(
                turn_id=t.id,
                speaker=t.speaker,
                text=t.text,
                start_s=t.start_s,
                end_s=t.end_s,
                cited=t.id in cited,
            )
            for t in call.transcript.turns
        ),
        decisions=tuple(Labelled(key=d.value, label=wording.DECISION_LABEL[d]) for d in Decision),
        disposition=_disposition_view(batch.latest(case_id)),
        history=tuple(_disposition_view(d) for d in batch.history.get(case_id, ())),
    )


def record_disposition(
    store: OpsStore, case_id: str, body: DispositionIn, now: datetime, sessions: Path | None = None
) -> CaseView:
    """Append a reviewer's decision on a referred call and return the case as it now stands."""
    case_view(load_batch(store), case_id)  # only a referral can be decided
    store.add_disposition(
        Disposition(
            case_id=case_id, decision=body.decision, note=body.note, reviewer=body.reviewer, recorded_at=now
        )
    )
    return case_view(load_batch(store), case_id, sessions)


def attempt_log_view(batch: Batch) -> AttemptLogView:
    def loan_view(s: Sampled) -> SampledLoanView:
        return SampledLoanView(
            loan_id=s.drawn.loan_id,
            draw_id=s.draw.draw_id,
            sold_on=s.drawn.sold_on,
            day_since_sale_at_draw=s.drawn.day_since_sale,
            language=s.loan.record.borrower.language,
            branch=s.loan.branch,
            channel=s.loan.channel,
            attempts=tuple(
                AttemptView(
                    number=a.number,
                    at=a.at,
                    day_since_sale=a.day_since_sale,
                    outcome=a.outcome,
                    outcome_label=wording.OUTCOME_LABEL[a.outcome],
                    simulated=_simulated(a.source),
                    session_id=a.source.session_id if isinstance(a.source, PhoneSession) else None,
                )
                for a in s.attempts
            ),
            status=s.status,
            status_label=wording.STATUS_LABEL[s.status],
            tier=s.triage.tier if s.triage else None,
            tier_label=wording.TIER_LABEL[s.triage.tier] if s.triage else None,
            case_id=s.call.call_id if s.referred else None,
        )

    def outside_view(o: Outside) -> OutsideView:
        return OutsideView(
            session_id=o.call.session_id,
            record_id=o.call.record_id,
            loan_id=o.call.loan_id,
            reason=o.call.reason,
            at=o.call.at,
            language=o.call.language,
            outcome=o.call.outcome,
            outcome_label=wording.OUTCOME_LABEL[o.call.outcome],
            dialogue_outcome=o.call.dialogue_outcome,
            tier=o.triage.tier if o.triage else None,
            tier_label=wording.TIER_LABEL[o.triage.tier] if o.triage else None,
            case_id=o.record.call_id if o.triage and o.triage.tier is Tier.refer else None,
        )

    return AttemptLogView(
        draws=draw_views(batch),
        loans=tuple(loan_view(s) for s in batch.sampled),
        outside=tuple(outside_view(o) for o in batch.outside),
    )
