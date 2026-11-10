"""Types for the operating layer: the loan book, the sample, the attempt log, review decisions.

    LoanBook --sampler.draw--> Draw --simulate.run_batch--> Attempt (+ CallRecord when a call completed)
    CallRecord --triage.triage (samajh.rules.summarise)--> Triage --views--> reviewer queue, case page
    (book, draws, attempts, calls, decisions) --report.build_report--> the half-yearly report

Nothing here decides anything about a sale. A `Decision` is recorded by a person.

Every simulated call says so in its `source`. A call made on the browser phone carries the
session id of its log under `<state>/sessions/` instead, and nothing else in the schema changes.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, ClassVar, Literal

from pydantic import Field, StringConstraints, model_validator

from samajh.rules import IssueLine
from samajh.scenarios.model import ProductBelief
from samajh.types import (
    CaseResult,
    Frozen,
    Language,
    LenderType,
    LoanRecord,
    SaleConcern,
    Severity,
    Tier,
    Transcript,
)

DEFAULT_UNIT = "Customer Feedback Unit (synthetic), not associated with sales"
WINDOW_DAYS = 30  # feedback is sought within 30 days of the sale (para 85Y / 101Y)
# The most attempts a loan gets, of any kind (simulated or phone): the simulator's default, ingest's
# guard (samajh.ops.chain.refusal) and the phone server's `attempt_limit` all read this one constant.
MAX_ATTEMPTS = 3
SESSION_ID_PATTERN = r"^\d{8}T\d{6}-[0-9a-f]{12}$"  # samajh.server.sessionlog.SESSION_ID

# --- the loan book -----------------------------------------------------------


class Channel(StrEnum):
    """How the sale was made."""

    branch = "branch"
    agent = "agent"  # a direct selling agent
    app = "app"  # the lender's own app


class BookLoan(Frozen):
    """One sale on the lender's book. Synthetic. `sold_on` is the day the 30-day window starts."""

    record: LoanRecord
    sold_on: date
    branch: str  # e.g. "SYN-BR-03"
    channel: Channel


class BookMeta(Frozen):
    """What the book is and how to regenerate it. `synthetic` is always true."""

    synthetic: Literal[True] = True
    lender_name: str
    lender_type: LenderType
    seed: int
    loans: int
    sold_from: date
    sold_to: date
    sha256: str  # of book.jsonl


class AttemptOutcome(StrEnum):
    """How one call attempt ended. `FROM_DIALOGUE` maps the dialogue's own outcomes onto these."""

    no_answer = "no_answer"
    wrong_party = "wrong_party"
    not_confirmed = "not_confirmed"  # identity not confirmed; nothing about the loan was said
    declined = "declined"
    call_back_later = "call_back_later"
    language_switch = "language_switch"  # asked for another language; a call in it is a retry
    incomplete = "incomplete"  # the call started and ended early (asked for a person, turn limit, hung up)
    do_not_call = "do_not_call"  # asked not to be called again: no later attempt is ever made
    written_requested = "written_requested"  # asked for this in writing instead of a call
    completed_not_analysed = "completed_not_analysed"  # the call ended normally; its case file failed
    completed = "completed"
    # A request to stop, to speak to a person or to call later, from a speaker nobody confirmed as the
    # borrower (the case file's `speaker_confirmed` is false): not the borrower's own request, so it
    # ends nothing and the loan is called again (`attempt_outcome_for`).
    request_unconfirmed = "request_unconfirmed"


# samajh.dialogue.machine.Outcome value (and the case file's "in_progress" for a call hung up before
# it ended) -> AttemptOutcome. A new dialogue outcome is one line here: the test
# `test_every_dialogue_outcome_has_an_attempt_outcome` fails until it is added, and ingestion skips
# (with a reason) a session whose outcome is missing. A completed call whose case file failed
# becomes `completed_not_analysed` (samajh.ops.sessions). Read it only through `attempt_outcome_for`,
# which also applies the case file's `speaker_confirmed`.
FROM_DIALOGUE: dict[str, AttemptOutcome] = {
    "completed": AttemptOutcome.completed,
    "wrong_party": AttemptOutcome.wrong_party,
    "not_confirmed": AttemptOutcome.not_confirmed,
    "second_check_failed": AttemptOutcome.not_confirmed,
    "no_go_ahead": AttemptOutcome.declined,
    "declined": AttemptOutcome.declined,
    "human_requested": AttemptOutcome.incomplete,
    "turn_limit": AttemptOutcome.incomplete,
    "call_back_later": AttemptOutcome.call_back_later,
    "language_switch": AttemptOutcome.language_switch,
    "no_response": AttemptOutcome.no_answer,
    "do_not_call": AttemptOutcome.do_not_call,
    "written_requested": AttemptOutcome.written_requested,
    "in_progress": AttemptOutcome.incomplete,
}

# The dialogue outcomes that are a request of the borrower's own: from a speaker the case file says
# was not confirmed (`speaker_confirmed` false) each is `request_unconfirmed` instead.
UNCONFIRMED_REQUESTS = frozenset({"do_not_call", "human_requested", "call_back_later"})


def attempt_outcome_for(dialogue_outcome: str, speaker_confirmed: bool | None) -> AttemptOutcome:
    """The one mapping from a session's (dialogue outcome, `speaker_confirmed`) to its attempt
    outcome. `speaker_confirmed` None (the case file does not say) and True give `FROM_DIALOGUE`;
    False turns the requests in `UNCONFIRMED_REQUESTS` into `request_unconfirmed`. Raises KeyError
    for a dialogue outcome not in `FROM_DIALOGUE`."""
    outcome = FROM_DIALOGUE[dialogue_outcome]
    if speaker_confirmed is False and dialogue_outcome in UNCONFIRMED_REQUESTS:
        return AttemptOutcome.request_unconfirmed
    return outcome


# The outcomes whose `right_party_confirmed` is fixed by the outcome itself (`Attempt` checks it,
# and ingest skips a case file whose `speaker_confirmed` says the opposite).
CONFIRMED_BY_OUTCOME: dict[AttemptOutcome, bool] = {
    AttemptOutcome.completed: True,
    AttemptOutcome.completed_not_analysed: True,
    AttemptOutcome.no_answer: False,
    AttemptOutcome.wrong_party: False,
    AttemptOutcome.not_confirmed: False,
    AttemptOutcome.request_unconfirmed: False,
}

# The only outcomes after which a loan is called again. Every other outcome ends the loan's chain of
# attempts: no attempt after it is made (simulate) or accepted (sessions).
RETRY_AFTER = frozenset(
    {
        AttemptOutcome.no_answer,
        AttemptOutcome.call_back_later,
        AttemptOutcome.language_switch,
        AttemptOutcome.request_unconfirmed,
    }
)


class SimStep(Frozen):
    """What one simulated attempt does. `right_party_confirmed`: both identity checks passed."""

    outcome: AttemptOutcome
    right_party_confirmed: bool


class SimCustomer(Frozen):
    """The simulation's hidden truth for one loan: what the customer believes and how they answer
    the phone. Written by the book generator. The queue and the report never read it.

    `attempts` is the scripted result of attempt 1, 2, ...; the runner stops at the first outcome
    outside `RETRY_AFTER` or at its attempt limit.
    """

    loan_id: str
    archetype: str  # the generator's name for this kind of customer, e.g. "told_it_is_an_fd"
    beliefs: tuple[ProductBelief, ...]
    concerns: tuple[SaleConcern, ...] = ()
    attempts: tuple[SimStep, ...]


# --- the sample --------------------------------------------------------------


class DrawnLoan(Frozen):
    loan_id: str
    sold_on: date
    day_since_sale: int  # on the draw's `as_of` day


class Draw(Frozen):
    """One random selection, with everything needed to audit and repeat it.

    Windows do not overlap: eligible are the loans sold after `after` (the previous draw's
    `as_of`; None for the first draw) and between `min_day` and `max_day` days before `as_of`
    (inclusive). So every sale is eligible in at most one draw, and each draw takes the same
    share `rate` of its eligible sales: `round(rate * eligible)` loans, at least one when any is
    eligible. `drawn` is `random.Random(f"{seed}|{as_of}").sample` over the sorted eligible ids.
    `sampler.verify_draw` recomputes it from the book.
    """

    draw_id: str  # "D-2027-02-08"
    as_of: date
    after: date | None  # sales on or before this day belong to an earlier draw
    min_day: int = Field(ge=0)
    max_day: int = Field(le=WINDOW_DAYS)
    rate: float = Field(gt=0, le=1)
    seed: int
    book_sha256: str
    eligible: tuple[str, ...]  # loan ids, sorted
    drawn: tuple[DrawnLoan, ...]  # in draw order

    @property
    def inclusion(self) -> float | None:
        """The chance an eligible sale was drawn: drawn over eligible."""
        return len(self.drawn) / len(self.eligible) if self.eligible else None


# --- the attempt log ---------------------------------------------------------


class SimulatedCall(Frozen):
    """No phone was involved: the outcome and any transcript were scripted."""

    kind: Literal["simulated"] = "simulated"
    script: str  # what wrote the transcript, e.g. "samajh.scenarios.script.teach_back"


class CustomerAudio(Frozen):
    """Counts of a phone session's customer turns by where their audio came from, as its case file
    records them: the microphone, a prepared audio file, or no audio."""

    mic: int = Field(ge=0)
    file: int = Field(ge=0)
    none: int = Field(ge=0)


class PhoneSession(Frozen):
    """A call on the browser phone. Its log, audio and recording are under `<state>/sessions/<id>/`.
    `customer_audio` is None when the case file does not record it (case files written before it)."""

    kind: Literal["phone_session"] = "phone_session"
    session_id: Annotated[str, StringConstraints(pattern=SESSION_ID_PATTERN)]
    recording_sha256: str | None = None
    customer_audio: CustomerAudio | None = None


CallSource = Annotated[SimulatedCall | PhoneSession, Field(discriminator="kind")]


class Attempt(Frozen):
    """One try at reaching one sampled customer."""

    # "<draw_id>/<loan_id>/<number>" for a simulated attempt, "<draw_id>/<loan_id>/<session_id>" for a
    # phone session: the same attempt is never logged twice.
    attempt_id: str
    draw_id: str
    loan_id: str
    number: int = Field(ge=1)
    at: datetime
    day_since_sale: int
    language: Language
    source: CallSource
    outcome: AttemptOutcome
    right_party_confirmed: bool
    dialogue_outcome: str | None = None  # the dialogue's own end-of-call outcome, when one ran
    call_id: str | None = None  # the analysed call, when the attempt left a transcript to analyse
    # Set on a later log line that replaces the earlier line with the same attempt id: the only
    # replacement allowed is a phone session's `completed_not_analysed` by `completed` once its
    # case file was rebuilt (samajh.ops.sessions). Both lines stay in attempts.jsonl; readers take
    # the last line per attempt id (`OpsStore.attempts`).
    supersedes: Literal[AttemptOutcome.completed_not_analysed] | None = None

    @model_validator(mode="after")
    def _coherent(self) -> "Attempt":
        expected = CONFIRMED_BY_OUTCOME.get(self.outcome)
        if expected is not None and self.right_party_confirmed is not expected:
            raise ValueError(f"outcome {self.outcome} contradicts right_party_confirmed")
        if self.outcome is AttemptOutcome.completed and self.call_id is None:
            raise ValueError("a completed attempt names its analysed call")
        return self


class SpeechReading(Frozen):
    """One Prisma reading of a customer turn, copied from the case file's `turns[].readings[]` as it
    stands (samajh.server.sessionlog.SttReading): nothing is parsed or normalised."""

    role: Literal["primary", "second"]
    model: str  # as the case file names it, e.g. "prisma-v3.0"
    ok: bool
    text: str | None  # exactly as the model wrote it
    error: str | None = None  # why a reading is missing, e.g. "timeout"


# What the bot did right after a customer turn, as the case file's `turns[].followed_by` says
# (samajh.server.sessionlog.FollowedBy).
FollowedBy = Literal["read_back", "asked_again", "other"]


class TurnReadings(Frozen):
    """Every reading of one customer turn, the case file's `readings_agreed` for it and its
    `followed_by`, as written there (samajh.server.casefile.TurnEvidence). `agreed` is never
    recomputed here. `followed_by` is None when the case file does not record it (written before the
    field) or records a value not in `FollowedBy`. Added after the first stores were written: a call
    saved without it loads as None, and a dump leaves it out while it is None."""

    added_later: ClassVar[frozenset[str]] = frozenset({"followed_by"})

    turn_id: int
    readings: tuple[SpeechReading, ...]
    agreed: bool | None
    followed_by: FollowedBy | None = None


class CallRecord(Frozen):
    """One analysed call: the transcript and what the rules made of it.

    `readings`: for a phone session, the case file's speech readings of each customer turn that
    lists them. None for a simulated call, and for a case file written before turns kept their
    readings (no turn has a `readings` field). Added after the first stores were written: a call
    saved without it loads as None, and a dump leaves it out while it is None."""

    added_later: ClassVar[frozenset[str]] = frozenset({"readings"})

    call_id: str
    attempt_id: str
    loan_id: str
    source: CallSource
    transcript: Transcript
    result: CaseResult
    analysis: str  # how the result was produced, e.g. "openai/gpt-6-luna" or "scripted extraction"
    transcript_note: str | None = None  # set when the transcript is partial, e.g. customer turns only
    readings: tuple[TurnReadings, ...] | None = None


class FinalStatus(StrEnum):
    """Where one sampled loan stands after its attempts. Exactly one per sampled loan."""

    not_attempted = "not_attempted"
    unreachable = "unreachable"  # every attempt went unanswered
    wrong_party = "wrong_party"
    not_confirmed = "not_confirmed"
    declined = "declined"
    call_back_later = "call_back_later"  # asked for a later call that has not happened
    language_switch = "language_switch"  # asked for another language; no call in it has happened
    # the last attempt, within 30 days of the sale, was a request from a speaker not confirmed as the
    # borrower; no call since (on day 30 or later it is not_reached_in_time, like any retry outcome)
    request_unconfirmed = "request_unconfirmed"
    not_reached_in_time = "not_reached_in_time"  # still to retry when day 30 from the sale passed
    incomplete = "incomplete"
    do_not_call = "do_not_call"  # asked not to be called again
    written_requested = "written_requested"  # asked for this in writing instead
    completed_not_analysed = "completed_not_analysed"  # completed, but the case file failed: not analysed
    completed_late = "completed_late"  # completed after day 30 from the sale: shown apart, not counted
    completed = "completed"


# --- triage: the tier and summary come from the core (samajh.types.Tier, samajh.rules.summarise) ---


class Triage(Frozen):
    """The tier of one call and its deduplicated summary. Built by `samajh.ops.triage.triage` only."""

    tier: Tier
    severity: Severity | None  # the highest severity among the `refer` flags; None unless tier is refer
    lines: tuple[IssueLine, ...]  # `samajh.rules.summarise`: refer, then incomplete, then understanding gaps

    @model_validator(mode="after")
    def _coherent(self) -> "Triage":
        refer = [line for line in self.lines if line.tier is Tier.refer]
        if (self.tier is Tier.refer) != bool(refer) or (self.severity is None) != (not refer):
            raise ValueError("tier refer, a refer line and a severity go together")
        return self


# --- the reviewer's decision ---------------------------------------------------


class Decision(StrEnum):
    """What the reviewer decided. Only a person records one."""

    concern_supported = "concern_supported"  # the reviewer's view: the file supports the concern
    concern_not_supported = "concern_not_supported"
    call_customer = "call_customer"
    needs_information = "needs_information"


FINAL_DECISIONS = frozenset({Decision.concern_supported, Decision.concern_not_supported})

Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Reviewer = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class Disposition(Frozen):
    """One recorded decision on one case. The log is append-only; the latest entry stands."""

    case_id: str  # the call_id of the referred call
    decision: Decision
    note: Note
    reviewer: Reviewer
    recorded_at: datetime


# --- the batch -----------------------------------------------------------------


class BatchMeta(Frozen):
    """One run of the mechanism over one book. `simulated` is true while any call is simulated."""

    batch_id: str
    book: BookMeta
    period_start: date  # the half-year the report covers
    period_end: date
    simulated: bool
    created_at: datetime
    unit: str = DEFAULT_UNIT  # who runs the mechanism: a unit not associated with sales


# --- calls that are not in the sample ------------------------------------------


class OutsideCall(Frozen):
    """A phone session that is not an attempt in the sample (see samajh.ops.sessions). Listed, never
    counted. `supersedes` as on `Attempt`."""

    session_id: Annotated[str, StringConstraints(pattern=SESSION_ID_PATTERN)]
    record_id: str
    loan_id: str
    reason: str  # why it is outside the sample, in words
    at: datetime
    language: Language
    source: CallSource
    outcome: AttemptOutcome
    dialogue_outcome: str
    record: LoanRecord  # the book's record for a loan on the book, else the phone's record
    call_id: str | None = None  # the analysed call, when the call completed and its case file is ready
    supersedes: Literal[AttemptOutcome.completed_not_analysed] | None = None


# --- what the last ingest of phone sessions did ------------------------------------


class SkippedSession(Frozen):
    session_id: str  # the folder name under the sessions directory
    reason: str  # in words


class ChangedSession(Frozen):
    """A session already brought in whose case file now gives something else. The version brought in
    first is kept: the session stays linked or outside, and is never skipped."""

    session_id: str
    differs: str  # what differs, in words (the fields, or the rule the case file now fails)


class IngestSummary(Frozen):
    """The last `samajh.ops.sessions.ingest`: every session folder it saw, each in exactly one of
    linked, outside and skipped. `changed` lists the linked or outside sessions whose case file
    changed after they were brought in. Kept in the store so the pages can say how many phone
    sessions are not in the batch. `changed` was added later: an older ingest.json loads with none."""

    added_later: ClassVar[frozenset[str]] = frozenset({"changed"})

    linked: tuple[str, ...]  # attempts on drawn loans
    outside: tuple[str, ...]  # listed, never counted
    skipped: tuple[SkippedSession, ...]  # in no count
    changed: tuple[ChangedSession, ...] = ()  # each also in linked or outside

    @model_validator(mode="after")
    def _one_place(self) -> "IngestSummary":
        skipped = [s.session_id for s in self.skipped]
        places = [*self.linked, *self.outside, *skipped]
        if len(places) != len(set(places)):
            raise ValueError("a session is in more than one of linked, outside and skipped")
        if not {c.session_id for c in self.changed} <= {*self.linked, *self.outside}:
            raise ValueError("a changed session is neither linked nor outside")
        return self

    @property
    def sessions(self) -> int:
        return len(self.linked) + len(self.outside) + len(self.skipped)
