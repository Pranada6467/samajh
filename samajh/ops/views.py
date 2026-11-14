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

Every count that is a share of a sample is a `Proportion` (with its interval, unless the report
withholds intervals because the draws gave sales clearly different chances: `Sampling.intervals_shown`);
a count of reviewer decisions is a `Count` (no interval: the decisions are not a sample). No number is
shown without its n.
"""

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from samajh.evalkit.score import wilson
from samajh.evidence.decisions import case_digest
from samajh.ops import wording
from samajh.ops.batch import Batch, Outside, Sampled, load_batch
from samajh.ops.model import (
    FINAL_DECISIONS,
    WINDOW_DAYS,
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
    SpeechReading,
    Triage,
)
from samajh.ops.store import OpsStore
from samajh.rules import IssueLine
from samajh.types import (
    Basis,
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
    """`count` of `n`, with the Wilson 95% interval. `share` and the bounds are None when n is 0; the
    bounds alone are None when the report withholds intervals (`plain_share`)."""

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


class ReferralSplit(Frozen):
    """A count of referrals by what each rests on (`Triage.referral_basis`). It sits beside the
    referral count it splits and sums to it: no referral figure is shown without both parts."""

    customer_statement: int
    record_only: int

    @property
    def total(self) -> int:
        return self.customer_statement + self.record_only


def referral_split(triages: Iterable[Triage | None]) -> ReferralSplit:
    """The referrals among `triages`, by basis. A call with no triage or no referral counts in neither."""
    bases = [t.referral_basis for t in triages if t is not None]
    return ReferralSplit(
        customer_statement=bases.count(Basis.customer_statement), record_only=bases.count(Basis.record_only)
    )


def _sums(split: ReferralSplit | None, count: int, what: str) -> None:
    if split is not None and split.total != count:
        raise ValueError(f"the referral split beside {what} does not sum to it")


# --- batch, shown in the header of every page ---------------------------------


class BatchView(Frozen):
    meta: BatchMeta
    simulated: bool  # every call in the batch is simulated
    simulated_notice: str  # the sentence every page shows about what is synthetic or simulated
    phone_note: str | None  # where the phone calls' customer audio came from, counted; None: no phone call
    access_notice: str  # no sign-in; reviewer names are free text
    sampled: int
    completed: int  # calls the report counts
    referred: int  # referrals the report counts
    open_cases: int  # of those, with no final decision (the report's "open" uses this definition)
    other_referrals: int  # referred calls outside the sample or the window: reviewed, not counted
    # Each referral count above, by what the referral rests on.
    referred_split: ReferralSplit
    open_split: ReferralSplit
    other_referrals_split: ReferralSplit
    basis_labels: tuple[Labelled, ...]  # each Basis with its words (wording.BASIS_LABEL), for the pages

    @model_validator(mode="after")
    def _splits_sum(self) -> "BatchView":
        _sums(self.referred_split, self.referred, "referred")
        _sums(self.open_split, self.open_cases, "open_cases")
        _sums(self.other_referrals_split, self.other_referrals, "other_referrals")
        return self


# --- the queue ------------------------------------------------------------------


class DispositionView(Frozen):
    decision: Decision
    decision_label: str
    final: bool
    note: str
    reviewer: str
    recorded_at: datetime
    case_digest: str | None  # the case digest the decision was made on; None on an older entry
    reviewer_auth: Literal["token"] | None  # "token": the name is the signed-in reviewer's; None: free text


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
    basis: Basis  # what the referral rests on
    basis_label: str  # wording.BASIS_LABEL


class QueueView(Frozen):
    """Counted cases first, open ones first, each group by severity then the oldest call first.
    Then referrals the report does not count (outside the sample or the window)."""

    items: tuple[QueueItem, ...]


# --- one case -------------------------------------------------------------------


class ReadingPart(Frozen):
    """One model's reading of the quoted turn: "<model>: <text>"."""

    model: str  # e.g. "Prisma v3.0"
    text: str  # the model's text byte for byte when `as_written`; else the words for a missing reading
    as_written: bool  # False: the reading failed or holds no text, and `text` says so


class ReadingsView(Frozen):
    """The line beside an amount quote, finished for the page: the parts joined with " · ", then
    `closing`. No parts when there is no reading to show; `closing` then says why, as a sentence."""

    parts: tuple[ReadingPart, ...]
    closing: str


class QuoteView(Frozen):
    quote: str
    turn_id: int
    start_s: float | None  # position in the call recording, when the session has one
    end_s: float | None
    readings: ReadingsView | None = None  # set on a quote of an amount (premium or cover) only


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
    referral_basis: Basis  # what the referral rests on
    basis_label: str  # wording.BASIS_LABEL
    first_line: str | None  # shown above the summary lines; set only on a referral on the record alone
    case_digest: str | None  # samajh.evidence.decisions.case_digest; a decision must send it back


class DispositionIn(Frozen):
    decision: Decision
    note: Note
    case_digest: str  # the case_digest of the case as the reviewer saw it
    reviewer: Reviewer | None = None  # accepted from older pages and ignored: the token names the reviewer


# --- the attempt log ------------------------------------------------------------


class AttemptView(Frozen):
    number: int
    at: datetime
    day_since_sale: int
    outcome: AttemptOutcome
    outcome_label: str
    simulated: bool
    session_id: str | None
    dialogue_outcome: str | None  # the dialogue's own outcome, as the case file gives it; None when simulated
    # For a request from a speaker not confirmed as the borrower: what the speaker asked, in words
    # (wording.UNCONFIRMED_REQUEST_LABEL); None for every other attempt.
    request: str | None
    # Why the call was not counted (`Attempt.not_counted`: the classifier failed on some turns), for
    # a request logged from such a call; None for every counted attempt. A dump leaves it out while None.
    not_counted: str | None = None

    added_later: ClassVar[frozenset[str]] = frozenset({"not_counted"})


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
    request: str | None  # as on `AttemptView`
    tier: Tier | None
    tier_label: str | None
    case_id: str | None  # set when the call is a referral


class SkippedView(Frozen):
    session_id: str
    reason: str


class ChangedView(Frozen):
    session_id: str
    differs: str  # what differs from the version brought in, in words


class AttemptLogView(Frozen):
    draws: tuple[DrawView, ...]
    loans: tuple[SampledLoanView, ...]  # in draw order
    outside: tuple[OutsideView, ...]  # phone calls outside the sample: never in the statistics
    window_note: str  # attempts after day 30 from the sale, in a sentence
    ingest_note: str  # what the last ingest of phone sessions brought in and left out
    not_ingested: tuple[SkippedView, ...]  # phone sessions the last ingest left out, with the reason
    # Sessions brought in (they are in `loans` or `outside`) whose case file changed afterwards: the
    # version brought in first is kept. Never in `not_ingested`.
    changed_label: str
    changed: tuple[ChangedView, ...]


# --- the half-yearly report ------------------------------------------------------


class FunnelRow(Frozen):
    key: str
    label: str
    value: Proportion  # n is the number sampled
    # Of an exit row's loans, how many end on a request said in a call that was not counted
    # (`Sampled.ended_by_uncounted_call`); already inside `value`. A dump leaves it out while 0.
    not_counted: int = Field(default=0, ge=0)

    added_later: ClassVar[frozenset[str]] = frozenset({"not_counted"})


class Funnel(Frozen):
    sampled: int
    attempts: int  # every attempt, retries included
    stages: tuple[FunnelRow, ...]  # attempted, reached, right party confirmed, completed in the window
    exits: tuple[FunnelRow, ...]  # one per other final status; with completed they sum to sampled


class NeverEligible(Frozen):
    reason: str
    count: int


class Sampling(Frozen):
    """Which sales could be sampled, and whether their chances were close enough for unweighted shares
    to carry intervals. Intervals elsewhere describe sampling among eligible sales only."""

    sales_in_period: int  # sales on the book made in the report period
    eligible: int  # of those, covered by a draw
    sampled: int
    never_eligible: tuple[NeverEligible, ...]  # with the reason; they sum to sales_in_period - eligible
    inclusion_low: float | None  # the smallest and largest draw's drawn / eligible
    inclusion_high: float | None
    inclusion_ratio: float | None  # high / low; None when no sale was eligible or the lowest is 0
    chances: Literal["none", "narrow", "wide"]  # none: nothing to draw from; narrow: ratio <= NARROW_RATIO
    intervals_shown: bool  # False when the chances are wide: every share in the report then has no bounds
    statement: str


class Timing(Frozen):
    """Days from the sale. The rule's 30 days are counted to the attempt, not to the draw."""

    first_attempt_days: tuple[int, int, int] | None  # min, median, max over attempted loans
    attempted: int  # the n of first_attempt_days
    attempts_after_window: Count  # n is every attempt
    phone_attempts_after_window: int  # of those, phone calls
    completed_late: int  # calls completed after day 30: shown apart, never counted
    note: str  # the attempts after day 30, in a sentence


class TierRow(Frozen):
    tier: Tier
    label: str
    value: Proportion  # n is analysed calls
    referred_split: ReferralSplit | None = None  # on the refer row only: its count by basis

    @model_validator(mode="after")
    def _split(self) -> "TierRow":
        if (self.tier is Tier.refer) != (self.referred_split is not None):
            raise ValueError("the refer row, and only it, carries a referral split")
        _sums(self.referred_split, self.value.count, "the refer row")
        return self


class RuleRow(Frozen):
    """One rule over the analysed calls. `flagged` counts calls with at least one flag under the
    rule and its n is every analysed call (each rule runs on every call). `undecided` calls had a
    gap under the rule and no flag. `referred` of the flagged calls have a `refer` line for the rule.

    `referred_split` splits `referred` by the basis of the rule's own refer lines
    (`IssueLine.basis`), not the call's: `record_only` counts referred calls where every refer line
    naming the rule rests on the record alone, `customer_statement` those where at least one rests
    on what the customer said. A call referred on what the customer said under another rule can
    so count as record-only here."""

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
    referred_split: ReferralSplit
    # counted calls whose outcome is understanding gap and whose summary has an understanding-gap
    # line naming this rule
    understanding_gap: int
    previous: Proportion | None  # the previous period's share; None when there is no previous period

    @model_validator(mode="after")
    def _split(self) -> "RuleRow":
        _sums(self.referred_split, self.referred, "the rule's referred count")
        return self


class DispositionRow(Frozen):
    key: str  # a Decision value, or "none"
    label: str
    value: Count  # n is counted referrals
    split: ReferralSplit  # `value.count` by basis

    @model_validator(mode="after")
    def _split(self) -> "DispositionRow":
        _sums(self.split, self.value.count, "the decision count")
        return self


class BreakdownRow(Frozen):
    key: str
    label: str
    sampled: int
    completed: int
    referred: Proportion  # n is this row's completed calls
    rest_referred: Proportion  # every other row together
    understanding_gap: Proportion
    rest_understanding_gap: Proportion
    referred_split: ReferralSplit  # `referred.count` by basis
    rest_referred_split: ReferralSplit  # `rest_referred.count` by basis

    @model_validator(mode="after")
    def _split(self) -> "BreakdownRow":
        _sums(self.referred_split, self.referred.count, "the row's referrals")
        _sums(self.rest_referred_split, self.rest_referred.count, "the other rows' referrals")
        return self


class Breakdown(Frozen):
    by: str  # "loan_kind", "branch" or "channel"
    label: str
    rows: tuple[BreakdownRow, ...]


class PolicyItem(Frozen):
    """One rule with flagged calls, put to the policy review, most serious first, then most common."""

    rule_id: RuleId
    group: str
    seriousness_label: str
    sentence: str  # "31 of 58 customers who completed the call could not state ..."
    value: Proportion
    highest: str | None  # the branch or channel with the highest share against the rest, as a phrase


class ReportTiles(Frozen):
    """The counts at the top of the report, each the same field a table below shows (see
    `report.tiles`). Counts only: no share, no interval."""

    synthetic: str  # the batch's notice, as the page's limits show it
    sold: int  # Sampling.sales_in_period
    sampled: int  # Sampling.sampled (= Funnel.sampled)
    completed: int  # the funnel's "completed" stage count
    referred: int  # the refer tier row's count
    referred_split: ReferralSplit  # the refer tier row's split
    understanding_gap: int  # the understanding gap tier row's count
    most_common_gap: Labelled  # the rule row with the most understanding-gap calls; key "none" if none
    most_common_gap_count: int  # that row's `understanding_gap`; 0 when none

    @model_validator(mode="after")
    def _split(self) -> "ReportTiles":
        _sums(self.referred_split, self.referred, "the referred tile")
        return self


class ReportView(Frozen):
    tiles: ReportTiles
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
    groups: tuple[Labelled, ...]  # the rule groups in order, with their headings
    risk_note: str
    seriousness_note: str
    rules: tuple[RuleRow, ...]  # every rule that returned an outcome, by group then seriousness
    referrals: tuple[DispositionRow, ...]
    open_referrals: Count  # no final decision; the same count as the page header
    supported_of_decided: Count  # n is referrals with a final decision
    decided_split: ReferralSplit  # `supported_of_decided.n` by basis
    supported_split: ReferralSplit  # `supported_of_decided.count` by basis
    other_referrals: int  # referred calls the report does not count
    open_referrals_split: ReferralSplit
    other_referrals_split: ReferralSplit
    basis_note: str  # wording.BASIS_NOTE: what the two kinds of referral are; shown once
    rule_split_note: str  # wording.RULE_SPLIT_NOTE: the rules table splits by the rule's own lines
    outside_calls: int  # phone calls outside the sample
    phone_sessions_not_ingested: int | None  # left out by the last ingest; None when none has run
    phone_sessions_changed: int | None  # brought in, case file changed since (still counted); None: no ingest
    ingest_note: str
    breakdowns: tuple[Breakdown, ...]
    policy_review: tuple[PolicyItem, ...]

    @model_validator(mode="after")
    def _splits_sum(self) -> "ReportView":
        _sums(self.open_referrals_split, self.open_referrals.count, "the open referrals")
        _sums(self.other_referrals_split, self.other_referrals, "the other referrals")
        _sums(self.decided_split, self.supported_of_decided.n, "the decided referrals")
        _sums(self.supported_split, self.supported_of_decided.count, "the supported referrals")
        return self


# --- building the views ------------------------------------------------------------

_RANK = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}
LATE = "completed after day 30 from the sale"


class NotAReferral(LookupError):
    """No referred call has this case id."""


class CaseChanged(Exception):
    """The case's digest differs from the one the decision was made on."""


def proportion(count: int, n: int) -> Proportion:
    """`count` of `n` with its Wilson 95% interval; no share and no bounds when n is 0."""
    if n == 0:
        return Proportion(count=count, n=0, share=None, low=None, high=None)
    low, high = wilson(count, n)
    return Proportion(count=count, n=n, share=count / n, low=low, high=high)


def plain_share(count: int, n: int) -> Proportion:
    """`count` of `n` and the share, with no interval: for a report whose draws gave sales clearly
    different chances, where an unweighted interval would describe no population."""
    return Proportion(count=count, n=n, share=count / n if n else None, low=None, high=None)


def batch_view(batch: Batch) -> BatchView:
    referrals = batch.referrals
    open_ids = {s.call.call_id for s in referrals if not batch.decided(s.call.call_id)}
    return BatchView(
        meta=batch.meta,
        simulated=batch.simulated,
        simulated_notice=wording.SIMULATED_NOTICE if batch.simulated else wording.MIXED_NOTICE,
        phone_note=wording.phone_note(batch.phone_sessions),
        access_notice=wording.ACCESS_NOTICE,
        sampled=len(batch.sampled),
        completed=len(batch.completed),
        referred=len(referrals),
        open_cases=batch.open(tuple(s.call.call_id for s in referrals)),
        other_referrals=len(batch.other_referrals),
        referred_split=referral_split(s.triage for s in referrals),
        open_split=referral_split(s.triage for s in referrals if s.call.call_id in open_ids),
        other_referrals_split=referral_split(o.triage for o in batch.other_referrals),
        basis_labels=tuple(Labelled(key=b.value, label=wording.BASIS_LABEL[b]) for b in Basis),
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
        case_digest=d.case_digest,
        reviewer_auth=d.reviewer_auth,
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
        basis=_basis(c),
        basis_label=wording.BASIS_LABEL[_basis(c)],
    )


def _basis(c: _Case) -> Basis:
    assert c.triage.referral_basis is not None  # a case is a referral
    return c.triage.referral_basis


def queue_view(batch: Batch) -> QueueView:
    """Referrals only. Counted cases before the rest; open cases before decided ones; then the most
    severe first, then the oldest call first, then by loan id. (85Y sets no review deadline.)"""
    items = [_queue_item(batch, c) for c in _cases(batch)]
    items.sort(key=lambda i: (not i.in_report, batch.decided(i.case_id), _RANK[i.severity], i.at, i.loan_id))
    return QueueView(items=tuple(items))


AMOUNT_RULES = frozenset({RuleId.premium, RuleId.cover})


def _part(reading: SpeechReading) -> ReadingPart:
    model = wording.model_label(reading.model)
    if reading.ok and reading.text:
        return ReadingPart(model=model, text=reading.text, as_written=True)
    missing = f"{wording.READINGS_NO_TEXT} ({reading.error})" if reading.error else wording.READINGS_NO_TEXT
    return ReadingPart(model=model, text=missing, as_written=False)


# (readings_agreed, followed_by) -> the closing words. A pair not listed ("other", or no followed_by
# recorded) says only same or differ.
_CLOSING: dict[tuple[bool, str | None], str] = {
    (True, "read_back"): wording.READINGS_SAME_READ_BACK,
    (True, "asked_again"): wording.READINGS_SAME_ASKED_AGAIN,
    (False, "asked_again"): wording.READINGS_DIFFER_ASKED_AGAIN,
    (False, "read_back"): wording.READINGS_DIFFER_READ_BACK,
}


def readings_view(call: CallRecord, turn_id: int) -> ReadingsView:
    """The readings line for a quote from `turn_id`, from the case file's own fields as ingest kept
    them. The closing words come only from `readings_agreed` and `followed_by`: "same" or "differ"
    is never worked out here, two readings with no recorded agreement are not called either, and
    what followed is said only when the case file records it as a read-back or a second asking."""
    if _simulated(call.source):
        return ReadingsView(parts=(), closing=wording.READINGS_TEXT_CALL)
    if call.readings is None:
        return ReadingsView(parts=(), closing=wording.READINGS_NOT_KEPT)
    turn = next((t for t in call.readings if t.turn_id == turn_id), None)
    if turn is None or not turn.readings:
        return ReadingsView(parts=(), closing=wording.READINGS_NONE_FOR_TURN)
    primary = next((r for r in turn.readings if r.role == "primary"), None)
    second = next((r for r in turn.readings if r.role == "second"), None)
    parts = tuple(_part(r) for r in (primary, second) if r is not None)
    if second is None or primary is None:
        closing = wording.READINGS_ONE
    elif turn.agreed is None:
        closing = wording.READINGS_NOT_COMPARED
    else:
        bare = wording.READINGS_SAME if turn.agreed else wording.READINGS_DIFFER
        closing = _CLOSING.get((turn.agreed, turn.followed_by), bare)
    return ReadingsView(parts=parts, closing=closing)


def _amount_quotes(call: CallRecord) -> set[tuple[int, str]]:
    """(turn id, quote) of every premium or cover outcome on the call: the quotes of an amount."""
    outcomes = (*call.result.all_flags(), *call.result.all_gaps())
    return {
        (o.turn_id, o.quote)
        for o in outcomes
        if o.rule_id in AMOUNT_RULES and o.quote is not None and o.turn_id is not None
    }


def _line_view(line: IssueLine, turns: dict[int, Turn], call: CallRecord) -> IssueLineView:
    quote = None
    if line.quote is not None and line.turn_id is not None:
        turn = turns.get(line.turn_id)
        start, end = (turn.start_s, turn.end_s) if turn else (None, None)
        amount = (line.turn_id, line.quote) in _amount_quotes(call)
        quote = QuoteView(
            quote=line.quote,
            turn_id=line.turn_id,
            start_s=start,
            end_s=end,
            readings=readings_view(call, line.turn_id) if amount else None,
        )
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
    lines = [_line_view(line, turns, call) for line in c.triage.lines]
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
        referral_basis=_basis(c),
        basis_label=wording.BASIS_LABEL[_basis(c)],
        first_line=c.triage.first_line,
        case_digest=case_digest(batch.root, sessions, case_id) if batch.root is not None else None,
    )


def record_disposition(
    store: OpsStore,
    case_id: str,
    body: DispositionIn,
    now: datetime,
    sessions: Path | None = None,
    *,
    reviewer: str | None = None,
    reviewer_auth: Literal["token"] | None = None,
) -> CaseView:
    """Append a reviewer's decision on a referred call and return the case as it now stands.

    `reviewer`: the signed-in reviewer's name (the route passes the token's name with
    reviewer_auth="token"); without it, the body's free-text name. Raises `CaseChanged` when
    `body.case_digest` is not the case's digest now: nothing is appended."""
    name = reviewer if reviewer is not None else body.reviewer
    if name is None:
        raise ValueError("a decision needs a reviewer")
    with store.locked():
        case_view(load_batch(store), case_id)  # only a referral can be decided
        current = case_digest(store.root, sessions, case_id)
        if body.case_digest != current:
            raise CaseChanged(case_id)
        store.add_disposition(
            Disposition(
                case_id=case_id,
                decision=body.decision,
                note=body.note,
                reviewer=name,
                recorded_at=now,
                case_digest=current,
                reviewer_auth=reviewer_auth,
            )
        )
    return case_view(load_batch(store), case_id, sessions)


def _request(outcome: AttemptOutcome, dialogue_outcome: str | None) -> str | None:
    """What an unconfirmed speaker asked, in words, beside a `request_unconfirmed` attempt."""
    if outcome is not AttemptOutcome.request_unconfirmed or dialogue_outcome is None:
        return None
    return wording.UNCONFIRMED_REQUEST_LABEL.get(dialogue_outcome, dialogue_outcome)


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
                    dialogue_outcome=a.dialogue_outcome,
                    request=_request(a.outcome, a.dialogue_outcome),
                    not_counted=a.not_counted,
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
            request=_request(o.call.outcome, o.call.dialogue_outcome),
            tier=o.triage.tier if o.triage else None,
            tier_label=wording.TIER_LABEL[o.triage.tier] if o.triage else None,
            case_id=o.record.call_id if o.triage and o.triage.tier is Tier.refer else None,
        )

    attempts = [a for s in batch.sampled for a in s.attempts]
    after = [a for a in attempts if a.day_since_sale > WINDOW_DAYS]
    return AttemptLogView(
        draws=draw_views(batch),
        loans=tuple(loan_view(s) for s in batch.sampled),
        outside=tuple(outside_view(o) for o in batch.outside),
        window_note=wording.window_note(
            len(after), sum(isinstance(a.source, PhoneSession) for a in after), len(attempts)
        ),
        ingest_note=wording.ingest_note(batch.ingest),
        not_ingested=tuple(
            SkippedView(session_id=s.session_id, reason=s.reason)
            for s in (batch.ingest.skipped if batch.ingest else ())
        ),
        changed_label=wording.CHANGED_LABEL,
        changed=tuple(
            ChangedView(session_id=c.session_id, differs=c.differs)
            for c in (batch.ingest.changed if batch.ingest else ())
        ),
    )
