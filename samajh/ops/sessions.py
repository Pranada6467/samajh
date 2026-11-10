"""Bring finished phone sessions into the batch: the same attempt log, funnel, queue and report as a
simulated call, marked as a phone call.

    <sessions>/<session_id>/case.json     samajh/server/casefile.py's CaseFile (read as data here)
    <sessions>/<session_id>/session.json  the session log; read only to say why a case file is missing
    <sessions>/<session_id>/call.wav      the call recording, when the session kept it

Every session folder ends in exactly one of three places, and `ingest` never stops on a session:

* **linked**: an attempt on a drawn loan, in the attempt log, the funnel, the queue and the report.
* **outside**: an `OutsideCall`, listed on the pages and never counted.
* **skipped**, with the reason in words. Nothing is written for it, and it is in no count.

A session already brought in (linked or outside) stays where it is whatever its case file says
later. When the case file now gives something else (another analysis, outcome or language, a book
block that no longer matches, a file that no longer reads), the version brought in first is kept
and the session is also listed under **changed after it was brought in**, with what differs. It is
never skipped. The one change taken in is the supersede below. A session brought in whose folder
is no longer in the sessions directory is kept the same way: it stays where it is and is listed as
changed (`FOLDER_GONE`). Every reason kept for a skipped or changed session is cut to
`REASON_LIMIT` characters.

**Reading a case file.** Everything ingest reads from a case file is parsed once, into validated
shapes (`_CaseFile`), before any rule runs: a wrong type, a date outside the years 2000 to 2100 or
a case file that contradicts itself is a skip with the reason. Booleans and counts are taken only
as JSON booleans and integers: `readings_agreed` that is not true or false is treated as not
recorded, a reading whose `ok` is not true or false is not shown as the model's words,
`customer_audio` whose counts are not whole numbers of at least 0 is treated as not recorded, and
`speaker_confirmed` that is not true, false or null is a skip. Behind that, any exception while
bringing in one session becomes a skip naming the exception type, the session's call file is
removed if no entry names it, and the run goes on.

**Which sessions are attempts.** Only a session opened as a loan-book call is an attempt: its case
file carries a `book` block (`batch_id`, `draw_id`, `sold_on`, `call_date`, `day_since_sale`) fixed
when the session was created. Ingest does not trust the server's checks and makes its own. It is
skipped when the loan is not on the batch's book, `batch_id` is another batch, `record_id` is not
the loan id, `sold_on` is not the book's sale date, or `day_since_sale` is not `call_date` minus
the book's sale date; when the call date is before the sale, before the loan's draw, or `draw_id`
is not the draw that holds the loan. A loan on the book that no draw holds is outside ("the loan
was not drawn in this batch"). The attempt's day is `call_date`, in the book's calendar, never the
wall clock: `Attempt.at` is `call_date` at `started_at`'s India time of day, so the India-time
date of `at` is the call date.

A session with no `book` block is never an attempt, whatever its loan id: a loan on the book (drawn
or not) is outside with a reason that says so, using the book's record; a packaged phone record
(`hero`, `informed`, ...) is outside as "not on the lender's book"; anything else is skipped.

**The chain** (`samajh.ops.chain`). Sessions are taken in wall-clock `started_at` order. A new
attempt takes the loan's next number and must be later than the loan's last logged attempt; a
loan whose last attempt ended its chain (any outcome not in `RETRY_AFTER`, including `do_not_call`)
takes no more, and neither does a loan that already has `MAX_ATTEMPTS` logged attempts of any kind
(simulated or phone; the phone server refuses such a call too, and ingest does not rely on that).
The limit applies to a new attempt only: a session already brought in as the loan's last allowed
attempt is still recognised on the next run. A session that fails any of these rules is skipped
with the reason: no attempt already logged is ever renumbered, moved or dropped. A call dated after
day 30 from the sale is logged and shown, and its status keeps it out of the counted calls
(`Sampled.status`).

**Outcomes.** The dialogue's outcome and the case file's `speaker_confirmed` map to an attempt
outcome through `samajh.ops.model.attempt_outcome_for`, the one place that mapping lives. A
`do_not_call`, `human_requested`, `call_back_later` or `written_requested` with `speaker_confirmed`
false came from a speaker nobody confirmed as the borrower: it is `request_unconfirmed` (the loan
is called again), never the borrower's own request. When `speaker_confirmed` is present, `right_party_confirmed`
follows it; a case file whose `speaker_confirmed` contradicts its outcome (false with a completed
call, true with a wrong party, an identity not confirmed or nothing heard) is skipped with the
reason. A session whose outcome is missing from `FROM_DIALOGUE` is skipped with the reason. A
completed call whose case file is `ready` is analysed; one whose case file failed is
`completed_not_analysed` (no tier, never a clear). A case file still `running`, unreadable,
malformed or absent is skipped with the reason.

**A turn the classifier failed on.** The case file's `degraded_turns` lists the customer turns the
dialogue read by its word lists alone, because its LLM turn classifier failed or ran out of time.
Such a call can go wrong unnoticed (someone else taking the phone), so a session with any is void:
it is skipped as "not counted: the classifier failed on N turn(s) (turn ids ...)", its own reason,
and is in no tier, attempt outcome, funnel stage or report count. It takes no attempt number, so the
loan can be called again. A case file without the field has no such turn; one whose field is not a
list of whole numbers is unreadable (a skip). Order: a session that fails a check of the file itself
(not a session id, no case file, unreadable or malformed, another session's, still running, an
outcome with no attempt outcome, a `speaker_confirmed` that contradicts the outcome) is skipped for
that reason, because a file that cannot be read or contradicts itself cannot be trusted for its
`degraded_turns` either, and that defect must be seen; the classifier reason then wins over every
book, loan, draw and chain rule (an unknown loan, a batch or draw that does not match, a chain that
has ended), because a void call is not an attempt at all. A session brought in before this rule
stays where it is and is listed as changed, saying it is still counted.

**Running it again** changes nothing for a session whose case file is unchanged. One change is
taken in: a case file that failed and was rebuilt to `ready` turns that session's
`completed_not_analysed` into `completed` with its analysed call, as an explicit supersede in the
log (`OpsStore.add_attempt`). Any other difference is listed as changed after it was brought in.

**Call files.** A call is saved before the entry that names it, so an interrupted run can leave a
call file no entry names; the next ingest removes it first and writes it again. After every
ingest each phone session's call file is named by exactly one effective attempt or outside call.

The last run's summary (each session in its one list, and the changed list) is kept in the store
(`ingest.json`) so the pages can say how many phone sessions are not in the batch.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from samajh.ops.chain import IST, chain_of, next_number, refusal
from samajh.ops.model import (
    CONFIRMED_BY_OUTCOME,
    FROM_DIALOGUE,
    SESSION_ID_PATTERN,
    Attempt,
    AttemptOutcome,
    BookLoan,
    CallRecord,
    ChangedSession,
    CustomerAudio,
    Draw,
    FollowedBy,
    IngestSummary,
    OutsideCall,
    PhoneSession,
    SkippedSession,
    SpeechReading,
    TurnReadings,
    attempt_outcome_for,
)
from samajh.ops.store import OpsStore, may_supersede
from samajh.ops.wording import CLASSIFIER_FAILED
from samajh.types import CallStep, CaseResult, Language, LoanRecord, Speaker, Transcript, Turn

__all__ = [
    "CHANGED_NOTE",
    "CLASSIFIER_FAILED",
    "IST",
    "PARTIAL_NOTE",
    "Ingested",
    "ingest",
    "packaged_records",
]

_SESSION = re.compile(SESSION_ID_PATTERN)
# A call whose transcript reaches one of these steps got past both identity checks.
_PAST_IDENTITY = frozenset(
    {CallStep.context, CallStep.open_recall, CallStep.teach_back, CallStep.consent_check, CallStep.read_back}
)
PARTIAL_NOTE = (
    "Customer turns only: this case file was written before case files kept the whole transcript, "
    "so the bot's lines and the call steps are not shown."
)
NOT_DRAWN = "the loan was not drawn in this batch"
NOT_ON_BOOK = "the loan is not on the lender's book for this batch"
NO_BOOK_BLOCK = (
    "the session was not opened as a call on the loan book (its case file has no book block), "
    "so it is not an attempt in the sample"
)
CHANGED_NOTE = "case file changed after it was brought in: the version brought in first is kept"
FOLDER_GONE = (
    "the session folder is no longer in the sessions directory; the version brought in first is kept"
)
REASON_LIMIT = 300  # the longest reason kept for a skipped or changed session, "…" included
# The years a case file's dates may fall in. Anything else is a malformed file, not a call: it is
# skipped at the boundary, so no later date arithmetic can overflow.
YEARS = (2000, 2100)

_Seconds = Annotated[StrictFloat, Field(allow_inf_nan=False)]


def _check_year(d: date) -> None:
    if not YEARS[0] <= d.year <= YEARS[1]:
        raise ValueError(f"the date {d.isoformat()} is outside the years {YEARS[0]} to {YEARS[1]}")


class _BookBlock(BaseModel):
    """The case file's `book` block: the loan-book attempt, fixed when the session was created."""

    model_config = ConfigDict(extra="ignore")

    batch_id: StrictStr
    draw_id: StrictStr
    sold_on: date
    call_date: date  # in the book's calendar
    day_since_sale: StrictInt

    @field_validator("sold_on", "call_date")
    @classmethod
    def _in_years(cls, value: date) -> date:
        _check_year(value)
        return value


class _Reading(BaseModel):
    """A case file's `turns[].readings[]` entry: the fields the case page shows, read as data.
    `ok` absent is true (the server's default); `ok` that is not a JSON boolean is false, so the
    text is never shown as the model's words. `error` that is not a string is not shown."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["primary", "second"]
    model: StrictStr
    ok: bool = True
    text: StrictStr | None = None
    error: str | None = None

    @field_validator("ok", mode="before")
    @classmethod
    def _strict_ok(cls, value: Any) -> bool:
        return value if isinstance(value, bool) else False

    @field_validator("error", mode="before")
    @classmethod
    def _error_text(cls, value: Any) -> str | None:
        return value if isinstance(value, str) else None


_FOLLOWED_BY = frozenset(get_args(FollowedBy))


class _Turn(BaseModel):
    """A case file's `turns[]` entry. `readings_agreed` that is not a JSON boolean is not recorded
    (None); `followed_by` outside `FollowedBy` is not recorded. `listed`: the turn has a `readings`
    field (a case file written before turns kept readings has none)."""

    model_config = ConfigDict(extra="ignore")

    turn_id: StrictInt
    text: StrictStr | None = None
    start_s: _Seconds | None = None
    end_s: _Seconds | None = None
    readings: list[_Reading] | None = None
    readings_agreed: bool | None = None
    followed_by: FollowedBy | None = None

    @field_validator("readings_agreed", mode="before")
    @classmethod
    def _strict_agreed(cls, value: Any) -> bool | None:
        return value if isinstance(value, bool) else None

    @field_validator("followed_by", mode="before")
    @classmethod
    def _known_followed_by(cls, value: Any) -> str | None:
        return value if isinstance(value, str) and value in _FOLLOWED_BY else None

    @property
    def listed(self) -> bool:
        return "readings" in self.model_fields_set


def _customer_audio(value: Any) -> CustomerAudio | None:
    """The counts when each of mic, file and none is a JSON whole number of at least 0; else None
    (not recorded, or not readable, in the case file)."""
    if not isinstance(value, dict):
        return None
    counts = {kind: value.get(kind) for kind in ("mic", "file", "none")}
    if all(type(n) is int and n >= 0 for n in counts.values()):
        return CustomerAudio(**counts)
    return None


def _extraction_model(models: Any) -> str:
    extraction = models.get("extraction") if isinstance(models, dict) else None
    model = extraction.get("model") if isinstance(extraction, dict) else None
    return model if isinstance(model, str) and model else "extraction model not named in the case file"


class _CaseFile(BaseModel):
    """The fields of a case file this module reads, parsed once. Everything else in the file is
    ignored. After validation every field has the type it names and every date is in `YEARS`."""

    model_config = ConfigDict(extra="ignore")

    session_id: StrictStr
    record_id: StrictStr
    loan_id: StrictStr
    language: Language
    book: _BookBlock | None = None
    status: Literal["running", "ready", "failed"]
    started_at: datetime  # UTC after validation; the case file writes UTC
    call_outcome: StrictStr
    speaker_confirmed: StrictBool | None = None  # None: the case file does not say
    # The customer turns read without the dialogue's classifier; [] in a case file written before it.
    degraded_turns: list[StrictInt] = []
    recording: Any = None
    models: Any = None
    turns: list[_Turn] = []
    customer_audio: Any = None
    transcript: Transcript | None = None
    result: Any = None
    # Derived once from the fields above (`_derive`); private, so no key in the file can set them.
    _recording_sha256: str | None = PrivateAttr(None)
    _analysis: str = PrivateAttr("")
    _audio: CustomerAudio | None = PrivateAttr(None)
    _case_result: CaseResult | None = PrivateAttr(None)  # set when ready and the call completed

    @field_validator("started_at", mode="before")
    @classmethod
    def _text_time(cls, value: Any) -> Any:
        if not isinstance(value, str):
            raise ValueError("the start time is not written as text")  # noqa: TRY004 (pydantic reads ValueError only)
        return value

    @field_validator("started_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        try:
            utc = (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC)
            utc.astimezone(IST)
        except OverflowError:
            raise ValueError(f"the time is outside the years {YEARS[0]} to {YEARS[1]}") from None
        _check_year(utc.date())
        return utc

    @model_validator(mode="after")
    def _derive(self) -> "_CaseFile":
        sha = self.recording.get("sha256") if isinstance(self.recording, dict) else None
        self._recording_sha256 = sha if isinstance(sha, str) else None
        self._analysis = _extraction_model(self.models)
        self._audio = _customer_audio(self.customer_audio)
        if self.status == "ready" and self.call_outcome == "completed":
            try:
                self._case_result = CaseResult.model_validate(self.result)
            except ValidationError as error:
                first = error.errors()[0]
                where = ".".join(("result", *(str(part) for part in first["loc"])))
                raise _Skip(f"case file could not be read: {where}: {first['msg']}") from None
        return self

    @property
    def started(self) -> datetime:
        """`started_at`, in UTC."""
        return self.started_at

    @property
    def recording_sha256(self) -> str | None:
        return self._recording_sha256

    @property
    def analysis(self) -> str:
        """The extraction model the case file names, or words saying it names none."""
        return self._analysis

    @property
    def audio(self) -> CustomerAudio | None:
        """`customer_audio` when its counts are readable; None when not recorded or not readable."""
        return self._audio

    @property
    def case_result(self) -> CaseResult | None:
        """The rules' result, validated, when the case file is ready and the call completed."""
        return self._case_result


class _Skip(Exception):
    """This session is skipped; `reason` says why, in words. `changed`: what to list instead when an
    earlier run brought the session in (None: `reason` itself)."""

    def __init__(self, reason: str, changed: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.changed = changed


def _turns(n: int) -> str:
    return f"{n} turn" if n == 1 else f"{n} turns"


def _classifier_failed(turns: list[int]) -> _Skip:
    """A session with a turn the classifier failed on: void, never counted, the call to be repeated."""
    ids = ", ".join(str(t) for t in turns)
    said = f"the classifier failed on {_turns(len(turns))} (turn ids {ids})"
    return _Skip(
        f"{CLASSIFIER_FAILED} {_turns(len(turns))} (turn ids {ids})",
        changed=f"{said}, and the session was brought in before ingest left such sessions out: "
        "the version brought in first is kept and still counted",
    )


def _why(error: Exception) -> str:
    """The reason for a session that could not be brought in, in words, naming the exception type."""
    if isinstance(error, _Skip):
        return error.reason
    return f"the case file could not be brought in ({type(error).__name__}: {error})"


def _capped(reason: str) -> str:
    """`reason` cut to `REASON_LIMIT` characters, ending in "…" when cut."""
    return reason if len(reason) <= REASON_LIMIT else reason[: REASON_LIMIT - 1] + "…"


@dataclass
class Ingested:
    """What one run did: every session folder in exactly one of linked, outside and skipped
    (`skipped` holds the reason). `changed` holds (session id, what differs) for linked or outside
    sessions whose case file changed after they were brought in."""

    linked: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    changed: list[tuple[str, str]] = field(default_factory=list)

    def describe(self) -> str:
        lines = [
            (
                f"{len(self.linked)} session(s) on drawn loans, {len(self.outside)} outside the sample, "
                f"{len(self.skipped)} skipped; {len(self.changed)} of those brought in had a {CHANGED_NOTE}"
            )
        ]
        lines += [f"  skipped {sid}: {why}" for sid, why in self.skipped]
        lines += [f"  changed after it was brought in {sid}: {what}" for sid, what in self.changed]
        return "\n".join(lines)

    def summary(self) -> IngestSummary:
        return IngestSummary(
            linked=tuple(self.linked),
            outside=tuple(self.outside),
            skipped=tuple(SkippedSession(session_id=sid, reason=why) for sid, why in self.skipped),
            changed=tuple(ChangedSession(session_id=sid, differs=what) for sid, what in self.changed),
        )

    def refuse(
        self,
        sid: str,
        reason: str,
        brought: dict[str, Literal["linked", "outside"]],
        changed: str | None = None,
    ) -> None:
        """A session that is not brought in this run: skipped, unless an earlier run brought it in,
        in which case it stays where it is and is listed as changed (with `changed` when given,
        else `reason`)."""
        place = brought.get(sid)
        if place is None:
            self.skipped.append((sid, _capped(reason)))
            return
        (self.linked if place == "linked" else self.outside).append(sid)
        self.changed.append((sid, _capped(changed or reason)))


def packaged_records() -> Callable[[str], LoanRecord | None]:
    """The phone's own records (samajh/server/records and `SAMAJH_RECORDS_DIR`), by record id."""
    from samajh.server.records import default_book  # the phone's record files; no network

    book = default_book()

    def lookup(record_id: str) -> LoanRecord | None:
        try:
            return book.get(record_id).record
        except KeyError:
            return None

    return lookup


def attempt_outcome(case: _CaseFile) -> AttemptOutcome:
    """The attempt outcome of a finished session (`attempt_outcome_for`); a completed call whose
    case file is not ready is `completed_not_analysed`. Raises KeyError for an unknown outcome."""
    outcome = attempt_outcome_for(case.call_outcome, case.speaker_confirmed)
    if outcome is AttemptOutcome.completed and case.status != "ready":
        return AttemptOutcome.completed_not_analysed
    return outcome


def transcript_of(case: _CaseFile) -> tuple[Transcript, str | None]:
    """The whole transcript when the case file has it; else the customer turns alone, with a note."""
    if case.transcript is not None:
        return case.transcript, None
    if any(t.text is None for t in case.turns):
        raise _Skip("the case file has no transcript and a customer turn without text")
    turns = tuple(
        Turn(
            id=t.turn_id,
            speaker=Speaker.customer,
            step=CallStep.teach_back,  # not in the case file; never shown on the pages
            text=t.text,
            start_s=t.start_s,
            end_s=t.end_s,
        )
        for t in case.turns
    )
    return Transcript(
        call_id=case.session_id, loan_id=case.loan_id, language=case.language, turns=turns
    ), PARTIAL_NOTE


def right_party_confirmed(case: _CaseFile, outcome: AttemptOutcome) -> bool:
    """Both identity checks passed. The case file's `speaker_confirmed` when it has one. Without it:
    fixed by the outcome where the outcome fixes it, else from the transcript's steps when the case
    file has it, else false (an undercount, never an overcount)."""
    if case.speaker_confirmed is not None:
        return case.speaker_confirmed
    fixed = CONFIRMED_BY_OUTCOME.get(outcome)
    if fixed is not None:
        return fixed
    if case.transcript is None:
        return False
    return any(turn.step in _PAST_IDENTITY for turn in case.transcript.turns)


def _source(case: _CaseFile) -> PhoneSession:
    return PhoneSession(
        session_id=case.session_id, recording_sha256=case.recording_sha256, customer_audio=case.audio
    )


def readings_of(case: _CaseFile) -> tuple[TurnReadings, ...] | None:
    """Each customer turn's speech readings, `readings_agreed` and `followed_by`, copied from the case
    file as they stand (texts byte for byte; agreement as the case file records it, never
    recomputed). Only turns with a `readings` field are listed. None when no turn has one: a case
    file written before turns kept their readings."""
    listed = [t for t in case.turns if t.listed]
    if not listed:
        return None
    return tuple(
        TurnReadings(
            turn_id=t.turn_id,
            readings=tuple(SpeechReading(**r.model_dump()) for r in t.readings or ()),
            agreed=t.readings_agreed,
            followed_by=t.followed_by,
        )
        for t in listed
    )


def _call_record(case: _CaseFile, attempt_id: str) -> CallRecord:
    transcript, note = transcript_of(case)
    assert case.case_result is not None  # an analysed call: ready and completed (`_CaseFile._derive`)
    return CallRecord(
        readings=readings_of(case),
        call_id=case.session_id,
        attempt_id=attempt_id,
        loan_id=case.loan_id,
        source=_source(case),
        transcript=transcript,
        result=case.case_result,
        analysis=case.analysis,
        transcript_note=note,
    )


# --- reading a session folder -------------------------------------------------------


def _no_case_reason(folder: Path) -> str:
    """Why a session folder has no case file, as far as its session log says."""
    try:
        log = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "no case file (case.json) and no session log"
    except (OSError, ValueError):
        return "no case file (case.json); the session log could not be read"
    if not isinstance(log, dict):
        return "no case file (case.json); the session log could not be read"
    stub = "; it used the test dialogue (stub), not the Samajh call" if log.get("dialogue") == "stub" else ""
    if log.get("status") == "active":
        return f"no case file (case.json): the session log says the call never ended (still active){stub}"
    if log.get("status") == "ended":
        how = log.get("ended_reason") or "reason not given"
        return f"no case file (case.json): the call ended ({how}) but no case was built for it{stub}"
    return f"no case file (case.json){stub}"


def _contradiction(case: _CaseFile) -> str | None:
    """Why the case file's `speaker_confirmed` contradicts its own outcome, in words; None when it
    does not (or the case file does not say)."""
    if case.speaker_confirmed is None:
        return None
    outcome = attempt_outcome(case)
    fixed = CONFIRMED_BY_OUTCOME.get(outcome)
    if fixed is None or fixed is case.speaker_confirmed:
        return None
    said = "true" if case.speaker_confirmed else "false"
    return (
        f"the case file contradicts itself: speaker_confirmed is {said}, but the call ended as "
        f"{case.call_outcome}"
    )


def _read_case(folder: Path) -> _CaseFile:
    sid = folder.name
    if not _SESSION.fullmatch(sid):
        raise _Skip("not a session id")
    path = folder / "case.json"
    if not path.is_file():
        raise _Skip(_no_case_reason(folder))
    try:
        case = _CaseFile.model_validate_json(path.read_bytes())
    except OSError as error:
        raise _Skip(f"case file could not be read ({type(error).__name__})") from None
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(part) for part in first["loc"]) or "the file"
        raise _Skip(f"case file could not be read: {where}: {first['msg']}") from None
    if case.session_id != sid:
        raise _Skip("case file names another session")
    if case.status == "running":
        raise _Skip("case file still running")
    if case.call_outcome not in FROM_DIALOGUE:
        raise _Skip(
            f"the dialogue outcome {case.call_outcome!r} has no attempt outcome "
            "(add it to samajh.ops.model.FROM_DIALOGUE)"
        )
    if why := _contradiction(case):
        raise _Skip(why)
    if case.degraded_turns:  # after the file's own checks, before any book, loan or chain rule
        raise _classifier_failed(case.degraded_turns)
    return case


# --- one session -----------------------------------------------------------------


@dataclass(frozen=True)
class _Batch:
    batch_id: str
    loans: dict[str, BookLoan]
    draws: tuple[Draw, ...]

    def draw_of(self, loan_id: str) -> Draw | None:
        return next((d for d in self.draws if any(x.loan_id == loan_id for x in d.drawn)), None)


def _fields(existing: BaseModel, fresh: BaseModel) -> str:
    """The names of the fields that differ, for the changed list."""
    names = [name for name in type(fresh).model_fields if getattr(existing, name) != getattr(fresh, name)]
    return ", ".join(names) or "nothing visible"


def _without_followed_by(call: CallRecord) -> CallRecord:
    if call.readings is None:
        return call
    turns = tuple(t.model_copy(update={"followed_by": None}) for t in call.readings)
    return call.model_copy(update={"readings": turns})


def _same_call(saved: CallRecord | None, fresh: CallRecord) -> bool:
    """The saved call is the one the case file gives now. Fields added to the saved call later are
    treated alike: a call saved before `CallRecord.readings` existed has none, and one saved before
    `TurnReadings.followed_by` existed has none on any turn. Such a call counts as the same when
    everything else is, and is left as it is (its case page then shows no readings, or no words on
    what followed), so a second ingest still changes nothing."""
    if saved is None:
        return False
    if saved == fresh:
        return True
    if saved.readings is None:
        return saved == fresh.model_copy(update={"readings": None})
    if all(t.followed_by is None for t in saved.readings):
        return saved == _without_followed_by(fresh)
    return False


def _write(
    store: OpsStore,
    existing: Attempt | OutsideCall | None,
    fresh: Attempt | OutsideCall,
    call: CallRecord | None,
    add: Callable[[Any], None],
) -> None:
    """Log `fresh` (and save its call first), take in an allowed supersede of `existing`, or leave an
    unchanged session as it is. Raises `_Skip` with what differs for any other difference (the
    caller lists the session as changed after it was brought in)."""
    if existing is None:
        if call is not None:
            store.save_call(call)
        add(fresh)
        return
    superseding = fresh.model_copy(update={"supersedes": AttemptOutcome.completed_not_analysed})
    if existing in (fresh, superseding):
        saved = store.call(call.call_id) if call is not None else None
        if call is not None and not _same_call(saved, call):
            what = _fields(saved, call) if saved is not None else "the saved call is missing"
            raise _Skip(f"the analysed call differs from the one brought in ({what})")
        return
    if call is not None and may_supersede(existing, superseding):
        store.save_call(call)
        add(superseding)
        return
    raise _Skip(f"the case file differs from what was brought in ({_fields(existing, fresh)})")


def _logged_elsewhere(store: OpsStore, sid: str, attempt_id: str | None) -> str | None:
    """What differs when the session is already in the store in another form than the one computed now."""
    attempts = [
        a for a in store.attempts() if isinstance(a.source, PhoneSession) and a.source.session_id == sid
    ]
    in_outside = any(o.session_id == sid for o in store.outside())
    if attempt_id is None and attempts:
        return "brought in as an attempt; the case file now gives a call outside the sample"
    if attempt_id is not None and in_outside:
        return "brought in as a call outside the sample; the case file now gives an attempt"
    if attempt_id is not None and any(a.attempt_id != attempt_id for a in attempts):
        return "brought in as another attempt (another draw or loan)"
    return None


def _as_attempt(store: OpsStore, case: _CaseFile, loan: BookLoan, draw: Draw, at: datetime) -> None:
    assert case.book is not None
    loan_id, sid = loan.record.loan_id, case.session_id
    attempt_id = f"{draw.draw_id}/{loan_id}/{sid}"
    if why := _logged_elsewhere(store, sid, attempt_id):
        raise _Skip(why)
    chain = chain_of(store.attempts(), loan_id)
    existing = next((a for a in chain if a.attempt_id == attempt_id), None)
    if existing is None and (why := refusal(chain, at)):
        raise _Skip(why)
    outcome = attempt_outcome(case)
    analysed = outcome is AttemptOutcome.completed
    fresh = Attempt(
        attempt_id=attempt_id,
        draw_id=draw.draw_id,
        loan_id=loan_id,
        number=existing.number if existing else next_number(chain),
        at=at,
        day_since_sale=(case.book.call_date - loan.sold_on).days,
        language=case.language,
        source=_source(case),
        outcome=outcome,
        right_party_confirmed=right_party_confirmed(case, outcome),
        dialogue_outcome=case.call_outcome,
        call_id=sid if analysed else None,
    )
    _write(store, existing, fresh, _call_record(case, attempt_id) if analysed else None, store.add_attempt)


def _as_outside(store: OpsStore, case: _CaseFile, reason: str, record: LoanRecord, at: datetime) -> None:
    sid = case.session_id
    if why := _logged_elsewhere(store, sid, None):
        raise _Skip(why)
    outcome = attempt_outcome(case)
    analysed = outcome is AttemptOutcome.completed
    fresh = OutsideCall(
        session_id=sid,
        record_id=case.record_id,
        loan_id=case.loan_id,
        reason=reason,
        at=at,
        language=case.language,
        source=_source(case),
        outcome=outcome,
        dialogue_outcome=case.call_outcome,
        record=record,
        call_id=sid if analysed else None,
    )
    existing = next((o for o in store.outside() if o.session_id == sid), None)
    call = _call_record(case, f"outside/{sid}") if analysed else None
    _write(store, existing, fresh, call, store.add_outside)


def _one(
    store: OpsStore, batch: _Batch, case: _CaseFile, records: Callable[[str], LoanRecord | None]
) -> Literal["linked", "outside"]:
    """Bring in one readable, finished session. Raises `_Skip` with the reason."""
    loan = batch.loans.get(case.loan_id)
    book = case.book
    if book is None:
        if loan is not None:
            reason = NOT_DRAWN if batch.draw_of(case.loan_id) is None else NO_BOOK_BLOCK
            _as_outside(store, case, reason, loan.record, case.started)
            return "outside"
        record = records(case.record_id)
        if record is None:
            raise _Skip(f"record {case.record_id!r} is neither on the book nor a phone record")
        _as_outside(store, case, NOT_ON_BOOK, record, case.started)
        return "outside"

    if loan is None:
        raise _Skip(f"loan {case.loan_id!r} is not on this batch's book")
    if book.batch_id != batch.batch_id:
        raise _Skip(f"the case file names batch {book.batch_id!r}, not this batch ({batch.batch_id})")
    if case.record_id != case.loan_id:
        raise _Skip(f"the case file's record id {case.record_id!r} is not its loan id")
    if book.sold_on != loan.sold_on:
        raise _Skip(f"the case file's sale date {book.sold_on} is not the book's ({loan.sold_on})")
    day = (book.call_date - loan.sold_on).days
    if book.day_since_sale != day:
        raise _Skip(
            f"the case file's day since the sale ({book.day_since_sale}) is not the call date minus the "
            f"book's sale date ({day})"
        )
    if day < 0:
        raise _Skip(f"the call date {book.call_date} is before the sale ({loan.sold_on})")
    at = datetime.combine(book.call_date, case.started.astimezone(IST).timetz())
    draw = batch.draw_of(case.loan_id)
    if draw is None:
        _as_outside(store, case, NOT_DRAWN, loan.record, at)
        return "outside"
    if book.draw_id != draw.draw_id:
        raise _Skip(f"the case file names draw {book.draw_id!r}, but the loan was drawn in {draw.draw_id}")
    if book.call_date < draw.as_of:
        raise _Skip(f"the call date {book.call_date} is before the loan's draw ({draw.as_of})")
    _as_attempt(store, case, loan, draw, at)
    return "linked"


def _brought_in(store: OpsStore) -> dict[str, Literal["linked", "outside"]]:
    """Every phone session already in the store, and where."""
    place: dict[str, Literal["linked", "outside"]] = {o.session_id: "outside" for o in store.outside()}
    for a in store.attempts():
        if isinstance(a.source, PhoneSession):
            place[a.source.session_id] = "linked"
    return place


def ingest(store: OpsStore, sessions: Path, records: Callable[[str], LoanRecord | None]) -> Ingested:
    """Every session folder under `sessions` into `store`, by the rules in this module's docstring.
    Holds the store's lock for the whole run. Raises only when the store holds no batch (or the
    store itself cannot be read or written)."""
    found = Ingested()
    with store.locked():
        meta = store.meta()
        batch = _Batch(meta.batch_id, {b.record.loan_id: b for b in store.book()}, store.draws())
        store.drop_unreferenced_session_calls()
        brought = _brought_in(store)
        folders = sorted(p for p in sessions.iterdir() if p.is_dir()) if sessions.is_dir() else []
        cases: list[_CaseFile] = []
        for folder in folders:
            try:
                cases.append(_read_case(folder))
            except Exception as error:  # noqa: BLE001 - no session may stop the run
                found.refuse(
                    folder.name, _why(error), brought, error.changed if isinstance(error, _Skip) else None
                )
        for case in sorted(cases, key=lambda c: (c.started, c.session_id)):
            try:
                kind = _one(store, batch, case, records)
            except Exception as error:  # noqa: BLE001 - no session may stop the run
                store.drop_unreferenced_session_calls()  # no call file without its entry
                found.refuse(case.session_id, _why(error), brought)
            else:
                (found.linked if kind == "linked" else found.outside).append(case.session_id)
        if sessions.is_dir():
            present = {folder.name for folder in folders}
            for sid in sorted(set(brought) - present):
                found.refuse(sid, FOLDER_GONE, brought)
        store.save_ingest_summary(found.summary())
    return found
