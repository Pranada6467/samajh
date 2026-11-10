"""What the review pages read: the JSON contract between `samajh/server/review_routes.py` and
`web/review/`. Every label a page shows for a rule, tier, outcome or decision comes from here
(through `samajh.ops.wording`), so the wording rules are checked in one place.

    GET  /api/review/batch                      -> BatchView
    GET  /api/review/queue                      -> QueueView      only `refer` cases, most severe first
    GET  /api/review/cases/{case_id}            -> CaseView       404 unless the case is a referral
    POST /api/review/cases/{case_id}/disposition   body DispositionIn -> CaseView
    GET  /api/review/attempts                   -> AttemptLogView the sample and every attempt
    GET  /api/review/draws                      -> list[Draw]     the selection audit, verbatim
    GET  /api/review/report                     -> ReportView

Every count that is a share of something is a `Proportion`, so no number is shown without its n.
"""

from datetime import date, datetime

from samajh.evalkit.score import wilson
from samajh.ops import wording
from samajh.ops.batch import Batch, Sampled, load_batch
from samajh.ops.model import (
    FINAL_DECISIONS,
    WINDOW_DAYS,
    AttemptOutcome,
    BatchMeta,
    CallSource,
    Channel,
    Decision,
    Disposition,
    FinalStatus,
    Note,
    PhoneSession,
    Reviewer,
)
from samajh.ops.store import OpsStore
from samajh.rules import IssueLine
from samajh.types import (
    Frozen,
    Language,
    LenderType,
    LoanKind,
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


class Labelled(Frozen):
    """A code and the words a page shows for it."""

    key: str
    label: str


# --- batch, shown in the header of every page ---------------------------------


class BatchView(Frozen):
    meta: BatchMeta
    simulated_notice: str | None  # the sentence every page shows while the batch is simulated
    sampled: int
    completed: int
    referred: int
    awaiting_review: int  # referrals with no final decision


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
    branch: str
    channel: Channel
    sold_on: date
    day_since_sale: int  # on the day of the call
    days_left_in_window: int  # 30 minus day_since_sale, floored at 0
    severity: Severity
    headline: str  # the first summary line, as one sentence
    refer_lines: int
    may_engage: tuple[str, ...]  # paragraphs, each once
    simulated: bool
    disposition: DispositionView | None  # the latest, if any


class QueueView(Frozen):
    """Open cases first (no final decision), each group ordered by severity, then by days left."""

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
    sold_on: date
    branch: str
    channel: Channel
    products: tuple[Product, ...]


class CallView(Frozen):
    call_id: str
    source: CallSource
    simulated: bool
    language: Language
    at: datetime
    attempt_number: int
    day_since_sale: int
    analysis: str
    recording_url: str | None  # "/api/sessions/<id>/recording.wav" for a phone session that has one


class CaseView(Frozen):
    case_id: str
    tier: Tier
    tier_label: str
    severity: Severity
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
    min_day: int
    max_day: int
    size: int
    seed: int
    eligible: int
    already_drawn: int
    drawn: int
    verified: bool  # the draw was recomputed from the book and matched


class AttemptLogView(Frozen):
    draws: tuple[DrawView, ...]
    loans: tuple[SampledLoanView, ...]  # in draw order


# --- the half-yearly report ------------------------------------------------------


class FunnelRow(Frozen):
    key: str
    label: str
    value: Proportion  # n is the number sampled


class Funnel(Frozen):
    sampled: int
    attempts: int  # every attempt, retries included
    stages: tuple[
        FunnelRow, ...
    ]  # attempted, reached, right party confirmed, completed: each within the last
    exits: tuple[
        FunnelRow, ...
    ]  # one per FinalStatus other than completed; with completed they sum to sampled


class Timing(Frozen):
    """Days from the sale. The rule's 30 days are counted to the attempt, not to the draw."""

    first_attempt_days: tuple[int, int, int] | None  # min, median, max over attempted loans
    completed_within_window: Proportion  # n is completed calls
    attempts_after_window: int


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
    understanding: bool  # the rule falls under the feedback paragraph itself (85Y / 101Y)
    flagged: Proportion
    undecided: int
    referred: int


class DispositionRow(Frozen):
    key: str  # a Decision value, or "awaiting"
    label: str
    value: Proportion  # n is referrals


class BreakdownRow(Frozen):
    key: str
    label: str
    sampled: int
    completed: int
    referred: Proportion  # n is this row's completed calls
    understanding_gap: Proportion


class Breakdown(Frozen):
    by: str  # "loan_kind", "branch" or "channel"
    label: str
    rows: tuple[BreakdownRow, ...]


class PolicyItem(Frozen):
    """One understanding gap put to the policy review, most common first."""

    rule_id: RuleId
    sentence: str  # "31 of 58 customers who completed the call could not state ..."
    value: Proportion
    highest: str | None  # where the share is highest among branches and channels with n >= 5, as a phrase


class ReportView(Frozen):
    batch: BatchView
    generated_at: datetime
    paragraph: str  # "85Y" for a bank, "101Y" for an NBFC
    period_label: str  # "1 January 2027 to 30 June 2027"
    coverage: str  # what part of the period this batch covers, in a sentence
    limits: tuple[str, ...]  # what is simulated and what the numbers cannot show; printed on the page
    draws: tuple[DrawView, ...]
    funnel: Funnel
    timing: Timing
    tiers: tuple[TierRow, ...]
    findings: tuple[RuleFinding, ...]  # every rule that returned an outcome, understanding rules first
    referrals: tuple[DispositionRow, ...]
    established_of_decided: Proportion  # n is referrals with a final decision
    breakdowns: tuple[Breakdown, ...]
    policy_review: tuple[PolicyItem, ...]


# --- building the views ------------------------------------------------------------

_RANK = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}


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
        simulated_notice=wording.SIMULATED_NOTICE if batch.meta.simulated else None,
        sampled=len(batch.sampled),
        completed=len(batch.completed),
        referred=len(referrals),
        awaiting_review=sum(not batch.decided(s.call.call_id) for s in referrals),
    )


def draw_views(batch: Batch) -> tuple[DrawView, ...]:
    return tuple(
        DrawView(
            draw_id=d.draw_id,
            as_of=d.as_of,
            min_day=d.min_day,
            max_day=d.max_day,
            size=d.size,
            seed=d.seed,
            eligible=len(d.eligible),
            already_drawn=len(d.already_drawn),
            drawn=len(d.drawn),
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


def _queue_item(batch: Batch, s: Sampled) -> QueueItem:
    refer = [line for line in s.triage.lines if line.tier is Tier.refer]
    day = s.attempts[-1].day_since_sale
    return QueueItem(
        case_id=s.call.call_id,
        loan_id=s.loan.record.loan_id,
        borrower=s.loan.record.borrower.name,
        language=s.call.transcript.language,
        branch=s.loan.branch,
        channel=s.loan.channel,
        sold_on=s.loan.sold_on,
        day_since_sale=day,
        days_left_in_window=max(0, WINDOW_DAYS - day),
        severity=s.triage.severity,
        headline=refer[0].title,
        refer_lines=len(refer),
        may_engage=_engaged(tuple(clause for line in refer for clause in line.clauses)),
        simulated=_simulated(s.call.source),
        disposition=_disposition_view(batch.latest(s.call.call_id)),
    )


def queue_view(batch: Batch) -> QueueView:
    """Referrals only. Cases with no final decision first; in each group the most severe first,
    then the fewest days left in the 30-day window, then by loan id."""
    items = [_queue_item(batch, s) for s in batch.referrals]
    items.sort(key=lambda i: (batch.decided(i.case_id), _RANK[i.severity], i.days_left_in_window, i.loan_id))
    return QueueView(items=tuple(items))


def _engaged(clauses: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(phrase for phrase in map(wording.may_engage, clauses) if phrase))


def _line_view(line: IssueLine, turns: dict[int, Turn]) -> IssueLineView:
    quote = None
    if line.quote is not None and line.turn_id is not None:
        turn = turns[line.turn_id]
        quote = QuoteView(quote=line.quote, turn_id=line.turn_id, start_s=turn.start_s, end_s=turn.end_s)
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


def case_view(batch: Batch, case_id: str) -> CaseView:
    """One referred call. Raises `NotAReferral` for any other id."""
    s = next((s for s in batch.referrals if s.call.call_id == case_id), None)
    if s is None:
        raise NotAReferral(case_id)
    record, call, completed = s.loan.record, s.call, s.attempts[-1]
    turns = {turn.id: turn for turn in call.transcript.turns}
    lines = [_line_view(line, turns) for line in s.triage.lines]
    cited = {line.turn_id for line in s.triage.lines if line.quote is not None}
    undecided = {
        (gap.rule_id, gap.reason): Labelled(
            key=gap.rule_id.value, label=f"{wording.RULE_LABEL[gap.rule_id]}: {wording.GAP_LABEL[gap.reason]}"
        )
        for gap in call.result.all_gaps()
    }
    session = call.source if isinstance(call.source, PhoneSession) else None
    return CaseView(
        case_id=case_id,
        tier=s.triage.tier,
        tier_label=wording.TIER_LABEL[s.triage.tier],
        severity=s.triage.severity,
        loan=LoanView(
            loan_id=record.loan_id,
            borrower=record.borrower.name,
            lender_type=record.lender_type,
            loan_kind=record.loan_kind,
            sanctioned_inr=record.sanctioned_inr,
            disbursed_inr=record.disbursed_inr,
            sold_on=s.loan.sold_on,
            branch=s.loan.branch,
            channel=s.loan.channel,
            products=record.products,
        ),
        call=CallView(
            call_id=call.call_id,
            source=call.source,
            simulated=session is None,
            language=call.transcript.language,
            at=completed.at,
            attempt_number=completed.number,
            day_since_sale=completed.day_since_sale,
            analysis=call.analysis,
            recording_url=f"/api/sessions/{session.session_id}/recording.wav" if session else None,
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


def record_disposition(store: OpsStore, case_id: str, body: DispositionIn, now: datetime) -> CaseView:
    """Append a reviewer's decision on a referred call and return the case as it now stands."""
    case_view(load_batch(store), case_id)  # only a referral can be decided
    store.add_disposition(
        Disposition(
            case_id=case_id, decision=body.decision, note=body.note, reviewer=body.reviewer, recorded_at=now
        )
    )
    return case_view(load_batch(store), case_id)


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

    return AttemptLogView(draws=draw_views(batch), loans=tuple(loan_view(s) for s in batch.sampled))
