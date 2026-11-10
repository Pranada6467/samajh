"""After the call: the case file of one finished Samajh call.

    <state>/sessions/<session_id>/case.json   the CaseFile below, rewritten atomically

The job runs once the call has ended and been closed (no take can replace another from then on,
so `call.wav` is fixed). Its steps, in order:

    transcript the dialogue's transcript, each turn placed in call.wav, and every reading of it
    recording  call.wav from the session's audio, and its sha256
    batch      Prisma Batch on call.wav: segment times and speaker labels
    align      each customer turn to the Batch segments it overlaps
    extract    samajh.pipeline on the call's transcript (LLM requests in parallel), then the rules
    summary    samajh.rules.summarise: the outcome tier and one line per issue

A step that fails is named in `failed` with its error, and the case is `failed`: whatever the
later steps found is kept for the record, but the file never reads as a clear result. Rerunning
the job is cheap: the Gnani and OpenRouter clients cache every call.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.clients.gnani import BatchOptions, BatchTranscript
from samajh.extract import Llm
from samajh.pipeline import run_text
from samajh.rules import summarise
from samajh.server.loanbook import BookLink
from samajh.server.records import CallRecord
from samajh.server.samajh_dialogue import (
    call_outcome,
    call_speaker_confirmed,
    call_state,
    call_transcript,
    degraded_turns,
    followed_by,
    readings_agreed,
)
from samajh.server.sessionlog import (
    BotEvent,
    CustomerEvent,
    FollowedBy,
    PauseStats,
    Recording,
    SessionLog,
    SttReading,
    TurnLatency,
)
from samajh.types import Speaker

CASE_VERSION = 1
StepName = Literal["transcript", "recording", "batch", "align", "extract", "summary"]
STEPS: tuple[StepName, ...] = ("transcript", "recording", "batch", "align", "extract", "summary")


class BatchClient(Protocol):
    def batch_transcribe(self, audio: bytes, options: BatchOptions, **kwargs: Any) -> BatchTranscript: ...


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StepResult(_Model):
    name: StepName
    ok: bool
    error: str | None = None  # "<ExceptionType>: <message>", never a key or a request body
    seconds: float


class AlignedSegment(_Model):
    index: int
    start: float
    end: float
    speaker: int | None
    overlap_s: float
    text: str


class TurnEvidence(_Model):
    """One customer turn: where it is in call.wav, every reading of it, and what Batch heard there."""

    turn_id: int  # the transcript's turn id, which flags and quotes cite
    seq: int  # the session log event
    start_s: float | None  # position in call.wav
    end_s: float | None
    source: Literal["mic", "file", "none"]  # where the customer audio came from (the session log's)
    text: str  # what the call acted on: the turn as the dialogue recorded it
    acted_on: str | None = None  # the model of the reading `text` is; None when nothing was read
    readings: list[SttReading]  # each labelled with its role and model
    # A turn read twice in which either reading holds a rupee figure: whether both readings gave
    # the same single amount (`samajh.amounts.cross_check`, as the dialogue recorded it). None:
    # read once, or neither reading holds a figure (a plain yes at a read-back).
    readings_agreed: bool | None = None
    # What the bot did next, from its reply's last line (`samajh_dialogue.followed_by`):
    # "read_back", "asked_again" or "other". None only in case files written before this field.
    followed_by: FollowedBy | None = None
    degraded: bool = False  # read without the dialogue's classifier (see CaseFile.degraded_turns)
    segments: list[AlignedSegment] = Field(default_factory=list)
    speaker: int | None = None  # the Batch speaker with the most overlap
    latency: TurnLatency | None = None
    pauses: PauseStats | None = None


class QuoteEvidence(_Model):
    """A flag's or gap's quote, with the audio it came from."""

    kind: Literal["flag", "gap"]
    tier: str
    rule_id: str
    reason: str
    product_id: str | None
    clause: str
    quote: str | None
    turn_id: int | None
    start_s: float | None  # the quoted turn in call.wav; None when there is no quote
    end_s: float | None
    also: list[dict[str, Any]] = Field(default_factory=list)  # further quotes of a conflict flag


class LatencyRow(_Model):
    """End of customer speech to start of bot audio, for one turn, in ms. `None` is not measured."""

    seq: int
    detection_ms: float | None  # the phone's end-of-speech wait; None for file-driven turns
    stt_ms: float  # primary and second reading
    dialogue_ms: float
    tts_ms: float | None  # the reply's audio, on its first fetch; None if never fetched
    other_ms: float  # resample, logging, and the reply's audio cache read
    total_ms: float | None  # detection + server + tts; None when detection is not measured


class CaseFile(_Model):
    version: Literal[1] = CASE_VERSION
    session_id: str
    record_id: str
    loan_id: str
    language: str
    # A loan-book call (samajh.server.loanbook): {batch_id, draw_id, sold_on, call_date,
    # day_since_sale}, fixed when the session was created; dates in the book's calendar. None for
    # a packaged record. `loan_id` and `record_id` are then both the book's loan id.
    book: dict[str, Any] | None = None
    status: Literal["running", "ready", "failed"]
    failed: list[StepName] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    # When the call began: the session's creation time, UTC wall clock, for every case file. It
    # does not change when the case is rebuilt.
    started_at: str
    finished_at: str | None = None
    call_outcome: str  # the dialogue's Outcome, or "in_progress" for a call hung up early
    # True once the year-of-birth check passed, False on any earlier end; None when the dialogue
    # does not say (`samajh_dialogue.speaker_confirmed`). A request to stop or call back from an
    # unconfirmed speaker is not the borrower's own.
    speaker_confirmed: bool | None = None
    ended_reason: str | None
    recording: Recording | None = None
    models: dict[str, Any] = Field(default_factory=dict)  # every model and parameter used
    # Transcript turn ids of the customer turns the dialogue read without its LLM classifier (it
    # failed or ran out of time): [] when none. Set in the head (`new_case`), from the session alone.
    # A session with any is void: samajh.ops does not count it, and the call is to be repeated.
    degraded_turns: list[int] = Field(default_factory=list)
    turns: list[TurnEvidence] = Field(default_factory=list)
    # The customer turns that count (not superseded), by where their audio came from.
    customer_audio: dict[str, int] = Field(default_factory=lambda: {"mic": 0, "file": 0, "none": 0})
    # samajh.types.Transcript of the whole call, bot turns included, each turn placed in call.wav.
    # None in case files written before this field (samajh.ops then rebuilds customer turns only).
    transcript: dict[str, Any] | None = None
    batch_segments: int | None = None
    batch_speakers: list[int] = Field(default_factory=list)
    # Meaningful only when status is "ready". A failed case keeps what was found, for the record.
    tier: str | None = None
    summary: dict[str, Any] | None = None  # samajh.rules.CaseSummary
    evidence: list[QuoteEvidence] = Field(default_factory=list)  # refer first
    result: dict[str, Any] | None = None  # samajh.types.CaseResult
    latency: list[LatencyRow] = Field(default_factory=list)


def _error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def batch_options(log: SessionLog, model: str, num_speakers: int | None) -> BatchOptions:
    """Batch hears the call in the language the primary reading used for its turns."""
    language: Any = "hi-IN"
    language_param = next(
        (
            r.params.get("language_code")
            for e in log.events
            if isinstance(e, CustomerEvent)
            for r in e.readings
        ),
        None,
    )
    if language_param:
        codes = tuple(language_param.split(","))
        language = codes[0] if len(codes) == 1 else codes
    return BatchOptions(
        model=model, language=language, format="transcribe", diarize=True, num_speakers=num_speakers
    )


def align(start: float | None, end: float | None, segments: list[AlignedSegment]) -> list[AlignedSegment]:
    """The segments that overlap `[start, end]`, each with the length of the overlap."""
    if start is None or end is None:
        return []
    out = []
    for seg in segments:
        overlap = min(end, seg.end) - max(start, seg.start)
        if overlap > 0:
            out.append(seg.model_copy(update={"overlap_s": round(overlap, 3)}))
    return out


def latency_rows(log: SessionLog) -> list[LatencyRow]:
    rows = []
    events = log.events
    for event in events:
        if not isinstance(event, CustomerEvent) or event.superseded or event.latency is None:
            continue
        reply = events[event.seq + 1] if event.seq + 1 < len(events) else None
        tts = reply.synth_ms if isinstance(reply, BotEvent) else None
        lat = event.latency
        stt = lat.stt_ms + lat.second_stt_ms
        other = max(0.0, lat.server_ms - stt - lat.dialogue_ms)
        total = None
        if lat.eos_wait_ms is not None and tts is not None:
            total = round(lat.eos_wait_ms + lat.server_ms + tts, 1)
        rows.append(
            LatencyRow(
                seq=event.seq,
                detection_ms=lat.eos_wait_ms,
                stt_ms=round(stt, 1),
                dialogue_ms=lat.dialogue_ms,
                tts_ms=tts,
                other_ms=round(other, 1),
                total_ms=total,
            )
        )
    return rows


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def new_case(log: SessionLog, record: CallRecord) -> CaseFile:
    """The case's head, from the session alone: the same on every build of the same call."""
    customers = [e for e in log.events if isinstance(e, CustomerEvent) and not e.superseded]
    book = BookLink.from_params(log.params).evidence() if "loan" in log.params else None
    return CaseFile(
        session_id=log.session_id,
        record_id=record.id,
        loan_id=record.record.loan_id,
        language=log.params.get("language", ""),
        book=book,
        status="running",
        started_at=log.created_at,
        call_outcome=call_outcome(log),
        speaker_confirmed=call_speaker_confirmed(log),
        # In the head, so a case file whose later steps fail still says the call is void.
        degraded_turns=list(degraded_turns(call_state(log))),
        ended_reason=log.ended_reason,
        customer_audio={kind: sum(e.source == kind for e in customers) for kind in ("mic", "file", "none")},
    )


def build_case(
    log: SessionLog,
    record: CallRecord,
    *,
    recording: Callable[[], tuple[Recording, bytes]],
    batch: Callable[[], BatchClient],
    llm: Callable[[], Llm],
    batch_model: str = "prisma-v3.0",
    num_speakers: int | None = 2,
    batch_timeout_s: float = 600.0,
    extraction_model: str | None = None,
) -> CaseFile:
    """Every step of the job for one closed call. Never raises for a failed step: it is recorded.

    `recording` returns call.wav (assembled if need be) and its bytes. `batch` and `llm` build
    their clients on first use, so a missing key fails its step, not the job.
    """
    case = new_case(log, record)
    case.models = {
        "stt_primary": {"model": log.stt.model, "format": log.stt.format},
        "stt_second": {
            "model": log.stt.second_model,
            "format": log.stt.second_format,
            "timeout_s": log.stt.second_timeout_s,
        },
        # samajh.server.samajh_dialogue.readings: on a turn read twice the dialogue gets this first.
        "dialogue_reads_first": f"{log.stt.second_model} when it has text, else {log.stt.model}",
        "tts": log.tts.model_dump(),
        "line_rate": log.line_rate,
    }

    def run(name: StepName, work: Callable[[], None]) -> bool:
        clock = time.perf_counter()
        try:
            work()
        except Exception as exc:  # noqa: BLE001 - every failure is recorded as this step's
            case.steps.append(StepResult(name=name, ok=False, error=_error(exc), seconds=_since(clock)))
            case.failed.append(name)
            return False
        case.steps.append(StepResult(name=name, ok=True, seconds=_since(clock)))
        return True

    found: dict[str, Any] = {}

    def do_transcript() -> None:
        state = call_state(log)
        agreed = {r.turn_id: r.agreed for r in state.second_readings}
        customers = [e for e in log.events if isinstance(e, CustomerEvent) and not e.superseded]
        # Customer turns of the transcript in order; `call_transcript` checks they match the events.
        found["transcript"] = transcript = call_transcript(log)
        case.transcript = transcript.model_dump(mode="json")
        spoken = [t for t in transcript.turns if t.speaker is Speaker.customer]
        case.turns = [
            TurnEvidence(
                turn_id=turn.id,
                seq=event.seq,
                start_s=turn.start_s,
                end_s=turn.end_s,
                source=event.source,
                text=event.transcript,
                acted_on=_acted_model(event),
                readings=event.readings,
                readings_agreed=readings_agreed(event.readings, agreed.get(turn.id)),
                followed_by=_followed_by(log, event),
                degraded=turn.id in case.degraded_turns,
                latency=event.latency,
                pauses=event.pauses,
            )
            for turn, event in zip(spoken, customers, strict=True)
        ]
        case.latency = latency_rows(log)

    audio: dict[str, bytes] = {}
    segments: list[AlignedSegment] = []

    def do_recording() -> None:
        case.recording, audio["call"] = recording()

    def do_batch() -> None:
        options = batch_options(log, batch_model, num_speakers)
        case.models["batch"] = options.model_dump(mode="json")
        heard = batch().batch_transcribe(audio["call"], options, poll_interval=3.0, timeout=batch_timeout_s)
        segments.extend(
            AlignedSegment(
                index=s.index, start=s.start, end=s.end, speaker=s.speaker, overlap_s=0.0, text=s.text
            )
            for s in heard.segments
        )
        case.batch_segments = len(segments)
        case.batch_speakers = sorted({s.speaker for s in segments if s.speaker is not None})

    def do_align() -> None:
        for turn in case.turns:
            turn.segments = align(turn.start_s, turn.end_s, segments)
            by_speaker: dict[int, float] = {}
            for seg in turn.segments:
                if seg.speaker is not None:
                    by_speaker[seg.speaker] = by_speaker.get(seg.speaker, 0.0) + seg.overlap_s
            turn.speaker = max(by_speaker, key=by_speaker.__getitem__) if by_speaker else None

    def do_extract() -> None:
        client = llm()
        case.models["extraction"] = {"model": extraction_model or _model_name(client)}
        found["run"] = run_text(found["transcript"], record.record, client, model=extraction_model)

    def do_summary() -> None:
        result = found["run"].result
        summary = summarise(record.record, result)
        case.result = result.model_dump(mode="json")
        case.summary = summary.model_dump(mode="json")
        case.tier = str(result.tier)
        spans = {t.id: (t.start_s, t.end_s) for t in found["transcript"].turns}
        case.evidence = _evidence(result, spans)

    if run("transcript", do_transcript):
        if run("recording", do_recording) and run("batch", do_batch):
            run("align", do_align)
        if run("extract", do_extract):
            run("summary", do_summary)
    for name in STEPS:  # a step that never ran because an earlier one failed is failed too
        if name not in {s.name for s in case.steps}:
            case.failed.append(name)
            case.steps.append(
                StepResult(name=name, ok=False, error="not run: an earlier step failed", seconds=0.0)
            )
    case.status = "failed" if case.failed else "ready"
    case.finished_at = _now()
    return case


def _acted_model(event: CustomerEvent) -> str | None:
    by_role = {r.role: r.model for r in event.readings}
    return by_role.get(event.acted_on) if event.acted_on else None


def _followed_by(log: SessionLog, event: CustomerEvent) -> FollowedBy:
    reply = log.events[event.seq + 1] if event.seq + 1 < len(log.events) else None
    return followed_by(reply.lines) if isinstance(reply, BotEvent) else "other"


def _since(clock: float) -> float:
    return round(time.perf_counter() - clock, 3)


def _model_name(client: object) -> str | None:
    inner = getattr(client, "_llm", client)
    name = getattr(inner, "_model", None)
    return name if isinstance(name, str) else None


_TIER_ORDER = {"refer": 0, "incomplete": 1, "understanding_gap": 2, "clear": 3}


def _evidence(result: Any, spans: dict[int, tuple[float | None, float | None]]) -> list[QuoteEvidence]:
    def at(turn_id: int | None) -> tuple[float | None, float | None]:
        return spans.get(turn_id, (None, None)) if turn_id is not None else (None, None)

    rows: list[QuoteEvidence] = []
    for flag in result.all_flags():
        start, end = at(flag.turn_id)
        rows.append(
            QuoteEvidence(
                kind="flag",
                tier=str(flag.tier),
                rule_id=str(flag.rule_id),
                reason=str(flag.reason),
                product_id=flag.product_id,
                clause=flag.clause,
                quote=flag.quote,
                turn_id=flag.turn_id,
                start_s=start,
                end_s=end,
                also=[
                    {
                        "quote": e.quote,
                        "turn_id": e.turn_id,
                        "start_s": at(e.turn_id)[0],
                        "end_s": at(e.turn_id)[1],
                    }
                    for e in flag.also
                ],
            )
        )
    for gap in result.all_gaps():
        start, end = at(gap.turn_id)
        rows.append(
            QuoteEvidence(
                kind="gap",
                tier=str(gap.tier),
                rule_id=str(gap.rule_id),
                reason=str(gap.reason),
                product_id=gap.product_id,
                clause=gap.clause,
                quote=gap.quote,
                turn_id=gap.turn_id,
                start_s=start,
                end_s=end,
            )
        )
    rows.sort(key=lambda r: (_TIER_ORDER.get(r.tier, 9), r.kind != "flag"))
    return rows
