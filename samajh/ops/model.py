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
from typing import Annotated, Literal

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

WINDOW_DAYS = 30  # feedback is sought within 30 days of the sale (para 85Y / 101Y)
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
    incomplete = "incomplete"  # the right party started the call and it ended early
    completed = "completed"


# samajh.dialogue.machine.Outcome value -> AttemptOutcome. A new dialogue outcome is one line here.
FROM_DIALOGUE: dict[str, AttemptOutcome] = {
    "completed": AttemptOutcome.completed,
    "wrong_party": AttemptOutcome.wrong_party,
    "not_confirmed": AttemptOutcome.not_confirmed,
    "second_check_failed": AttemptOutcome.not_confirmed,
    "no_go_ahead": AttemptOutcome.declined,
    "declined": AttemptOutcome.declined,
    "human_requested": AttemptOutcome.incomplete,
    "turn_limit": AttemptOutcome.incomplete,
}

RETRY_AFTER = frozenset({AttemptOutcome.no_answer, AttemptOutcome.call_back_later})


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

    Eligible: sold between `min_day` and `max_day` days before `as_of` (inclusive) and not drawn
    by an earlier draw of this batch. `drawn` is `random.Random(f"{seed}|{as_of}").sample` over
    the sorted eligible ids. `sampler.verify_draw` recomputes it from the book.
    """

    draw_id: str  # "D-2027-02-08"
    as_of: date
    min_day: int = Field(ge=0)
    max_day: int = Field(le=WINDOW_DAYS)
    size: int = Field(ge=1)  # the size asked for; fewer are drawn when fewer are eligible
    seed: int
    book_sha256: str
    eligible: tuple[str, ...]  # loan ids, sorted
    already_drawn: tuple[str, ...]  # inside the window, left out because an earlier draw took them
    drawn: tuple[DrawnLoan, ...]  # in draw order


# --- the attempt log ---------------------------------------------------------


class SimulatedCall(Frozen):
    """No phone was involved: the outcome and any transcript were scripted."""

    kind: Literal["simulated"] = "simulated"
    script: str  # what wrote the transcript, e.g. "samajh.scenarios.script.teach_back"


class PhoneSession(Frozen):
    """A call on the browser phone. Its log, audio and recording are under `<state>/sessions/<id>/`."""

    kind: Literal["phone_session"] = "phone_session"
    session_id: Annotated[str, StringConstraints(pattern=SESSION_ID_PATTERN)]
    recording_sha256: str | None = None


CallSource = Annotated[SimulatedCall | PhoneSession, Field(discriminator="kind")]


class Attempt(Frozen):
    """One try at reaching one sampled customer."""

    attempt_id: str  # "<draw_id>/<loan_id>/<number>": the same attempt is never logged twice
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

    @model_validator(mode="after")
    def _coherent(self) -> "Attempt":
        confirmed_by_outcome = {
            AttemptOutcome.completed: True,
            AttemptOutcome.incomplete: True,
            AttemptOutcome.no_answer: False,
            AttemptOutcome.wrong_party: False,
            AttemptOutcome.not_confirmed: False,
        }
        expected = confirmed_by_outcome.get(self.outcome)
        if expected is not None and self.right_party_confirmed is not expected:
            raise ValueError(f"outcome {self.outcome} contradicts right_party_confirmed")
        if self.outcome is AttemptOutcome.completed and self.call_id is None:
            raise ValueError("a completed attempt names its analysed call")
        return self


class CallRecord(Frozen):
    """One analysed call: the transcript and what the rules made of it."""

    call_id: str
    attempt_id: str
    loan_id: str
    source: CallSource
    transcript: Transcript
    result: CaseResult
    analysis: str  # how the result was produced, e.g. "openai/gpt-6-luna" or "scripted extraction"


class FinalStatus(StrEnum):
    """Where one sampled loan stands after its attempts. Exactly one per sampled loan."""

    not_attempted = "not_attempted"
    unreachable = "unreachable"  # every attempt went unanswered
    wrong_party = "wrong_party"
    not_confirmed = "not_confirmed"
    declined = "declined"
    call_back_later = "call_back_later"  # asked for a later call that has not happened
    incomplete = "incomplete"
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

    established = "established"
    not_established = "not_established"
    call_customer = "call_customer"
    needs_information = "needs_information"


FINAL_DECISIONS = frozenset({Decision.established, Decision.not_established})

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
