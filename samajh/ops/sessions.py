"""Bring finished phone sessions into the batch: the same attempt log, funnel, queue and report as a
simulated call, marked as a phone call.

    <sessions>/<session_id>/case.json   samajh/server/casefile.py's CaseFile (read as data here)
    <sessions>/<session_id>/call.wav    the call recording, when the session kept it

A session whose loan id (or the phone's record id) is a drawn loan of this batch becomes an attempt
on that loan in that draw. Any other session is an `OutsideCall`: listed on the pages, never in the
sampled statistics. A call that completed and whose case file is `ready` becomes an analysed call;
a completed call whose case file failed is `completed_not_analysed` (an attempt with no finding,
never a clear). A case still `running` is skipped until it finishes. Safe to run again.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from samajh.ops.model import (
    FROM_DIALOGUE,
    SESSION_ID_PATTERN,
    Attempt,
    AttemptOutcome,
    BookLoan,
    CallRecord,
    Draw,
    OutsideCall,
    PhoneSession,
)
from samajh.ops.store import OpsStore
from samajh.types import CallStep, CaseResult, Language, LoanRecord, Speaker, Transcript, Turn

IST = timezone(timedelta(hours=5, minutes=30))
_SESSION = re.compile(SESSION_ID_PATTERN)
# A call whose transcript reaches one of these steps got past both identity checks.
_PAST_IDENTITY = frozenset(
    {CallStep.context, CallStep.open_recall, CallStep.teach_back, CallStep.consent_check, CallStep.read_back}
)
PARTIAL_NOTE = (
    "Customer turns only: this case file was written before case files kept the whole transcript, "
    "so the bot's lines and the call steps are not shown."
)


class _CaseFile(BaseModel):
    """The fields of a case file this module reads. Everything else in the file is ignored."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    record_id: str
    loan_id: str
    language: str
    status: str
    started_at: datetime
    call_outcome: str
    recording: dict[str, Any] | None = None
    models: dict[str, Any] = {}
    turns: list[dict[str, Any]] = []
    transcript: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


@dataclass
class Ingested:
    """What one run did. `skipped` holds session ids with the reason, in words."""

    linked: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    def describe(self) -> str:
        lines = [f"{len(self.linked)} session(s) on drawn loans, {len(self.outside)} outside the sample"]
        lines += [f"  skipped {sid}: {why}" for sid, why in self.skipped]
        return "\n".join(lines)


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
    """The attempt outcome of a finished session. Raises ValueError for an outcome not in `FROM_DIALOGUE`."""
    try:
        outcome = FROM_DIALOGUE[case.call_outcome]
    except KeyError:
        raise ValueError(f"no attempt outcome for the dialogue outcome {case.call_outcome!r}") from None
    if outcome is AttemptOutcome.completed and case.status != "ready":
        return AttemptOutcome.completed_not_analysed
    return outcome


def transcript_of(case: _CaseFile) -> tuple[Transcript, str | None]:
    """The whole transcript when the case file has it; else the customer turns alone, with a note."""
    if case.transcript is not None:
        return Transcript.model_validate(case.transcript), None
    turns = tuple(
        Turn(
            id=t["turn_id"],
            speaker=Speaker.customer,
            step=CallStep.teach_back,  # not in the case file; never shown on the pages
            text=t["text"],
            start_s=t.get("start_s"),
            end_s=t.get("end_s"),
        )
        for t in case.turns
    )
    language = Language(case.language)
    return Transcript(
        call_id=case.session_id, loan_id=case.loan_id, language=language, turns=turns
    ), PARTIAL_NOTE


def right_party_confirmed(case: _CaseFile, outcome: AttemptOutcome) -> bool:
    """Both identity checks passed. From the transcript's steps when the case file has it; without
    it, only a completed call counts as confirmed (an undercount, never an overcount)."""
    if outcome in (AttemptOutcome.completed, AttemptOutcome.completed_not_analysed):
        return True
    if outcome in (AttemptOutcome.no_answer, AttemptOutcome.wrong_party, AttemptOutcome.not_confirmed):
        return False
    if case.transcript is None:
        return False
    return any(turn.step in _PAST_IDENTITY for turn in Transcript.model_validate(case.transcript).turns)


def _source(case: _CaseFile) -> PhoneSession:
    sha = (case.recording or {}).get("sha256")
    return PhoneSession(session_id=case.session_id, recording_sha256=sha if isinstance(sha, str) else None)


def _analysis(case: _CaseFile) -> str:
    model = (case.models.get("extraction") or {}).get("model")
    return model if isinstance(model, str) and model else "extraction model not named in the case file"


def _call_record(case: _CaseFile, attempt_id: str) -> CallRecord:
    transcript, note = transcript_of(case)
    return CallRecord(
        call_id=case.session_id,
        attempt_id=attempt_id,
        loan_id=case.loan_id,
        source=_source(case),
        transcript=transcript,
        result=CaseResult.model_validate(case.result),
        analysis=_analysis(case),
        transcript_note=note,
    )


def _find(
    book: dict[str, BookLoan], draws: tuple[Draw, ...], case: _CaseFile
) -> tuple[BookLoan, Draw] | None:
    for key in (case.loan_id, case.record_id):
        loan = book.get(key)
        draw = next((d for d in draws for x in d.drawn if loan and x.loan_id == loan.record.loan_id), None)
        if loan and draw:
            return loan, draw
    return None


def ingest(store: OpsStore, sessions: Path, records: Callable[[str], LoanRecord | None]) -> Ingested:
    """Every finished session under `sessions` into `store`. Sessions already ingested are left as they are."""
    found = Ingested()
    book = {loan.record.loan_id: loan for loan in store.book()}
    draws = store.draws()
    paths = sorted(sessions.glob("*/case.json")) if sessions.is_dir() else []
    for path in paths:
        sid = path.parent.name
        if not _SESSION.fullmatch(sid):
            found.skipped.append((sid, "not a session id"))
            continue
        try:
            case = _CaseFile.model_validate_json(path.read_bytes())
        except ValidationError:
            found.skipped.append((sid, "case file could not be read"))
            continue
        if case.session_id != sid:
            found.skipped.append((sid, "case file names another session"))
            continue
        if case.status == "running":
            found.skipped.append((sid, "case file still running"))
            continue
        outcome = attempt_outcome(case)
        analysed = outcome is AttemptOutcome.completed
        at = case.started_at if case.started_at.tzinfo else case.started_at.replace(tzinfo=UTC)
        link = _find(book, draws, case)
        if link is None:
            record = records(case.record_id)
            if record is None:
                found.skipped.append(
                    (sid, f"record {case.record_id!r} is neither on the book nor a phone record")
                )
                continue
            reason = (
                "the loan was not drawn in this batch"
                if case.loan_id in book or case.record_id in book
                else "the loan is not on the lender's book for this batch"
            )
            if analysed:
                store.save_call(_call_record(case, f"outside/{sid}"))
            store.add_outside(
                OutsideCall(
                    session_id=sid,
                    record_id=case.record_id,
                    loan_id=case.loan_id,
                    reason=reason,
                    at=at,
                    language=Language(case.language),
                    source=_source(case),
                    outcome=outcome,
                    dialogue_outcome=case.call_outcome,
                    record=record,
                    call_id=sid if analysed else None,
                )
            )
            found.outside.append(sid)
            continue
        loan, draw = link
        loan_id = loan.record.loan_id
        attempt_id = f"{draw.draw_id}/{loan_id}/{sid}"
        earlier = [a for a in store.attempts() if a.loan_id == loan_id]
        mine = next((a for a in earlier if a.attempt_id == attempt_id), None)
        number = mine.number if mine else 1 + max((a.number for a in earlier), default=0)
        if analysed:
            store.save_call(_call_record(case, attempt_id).model_copy(update={"loan_id": loan_id}))
        store.add_attempt(
            Attempt(
                attempt_id=attempt_id,
                draw_id=draw.draw_id,
                loan_id=loan_id,
                number=number,
                at=at,
                day_since_sale=(at.astimezone(IST).date() - loan.sold_on).days,
                language=Language(case.language),
                source=_source(case),
                outcome=outcome,
                right_party_confirmed=right_party_confirmed(case, outcome),
                dialogue_outcome=case.call_outcome,
                call_id=sid if analysed else None,
            )
        )
        found.linked.append(sid)
    return found
