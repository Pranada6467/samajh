"""The HTTP side of a call: sessions, turns, audio, and the static phone page.

The log on disk is the call. Each change is one atomic rewrite of `session.json`, which holds the
events and the dialogue's state together, so a customer turn is applied exactly once and any
server run can continue a call that an earlier run began. Sessions in memory are a cache of that
file plus the lock that orders the requests of one call.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import os
import queue
import re
import threading
import time
import wave
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from concurrent.futures import Future
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar, get_args
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.datastructures import QueryParams
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from samajh.clients._runtime import state_dir
from samajh.clients.errors import BadResponse, ConfigError
from samajh.clients.gnani import PrismaV25, PrismaV30, Timbre, Transcript, wav_seconds
from samajh.extract import Llm
from samajh.identity import parse_policy
from samajh.server.audio import (
    MAX_TURN_SECONDS,
    AudioRejected,
    join_clips,
    normalise_turn,
    pause_stats,
    to_line_pcm,
)
from samajh.server.casefile import CaseFile, StepResult, build_case, new_case
from samajh.server.dialogue import Dialogue, DialogueFactory, Heard, Step
from samajh.server.errors import ApiProblem, Stage, problem_from
from samajh.server.identity_routes import identity_router
from samajh.server.loanbook import LINK_PARAMS, LoanBook, LoanRefused, resolve_record
from samajh.server.review_routes import review_router
from samajh.server.samajh_dialogue import (
    IDENTITY_PARAM,
    answers_year_question,
    followed_by,
    identity_param,
    readings_agreed,
    shown_event,
    shown_log,
    withhold_reply,
)
from samajh.server.sessionlog import (
    AUDIO_NAME,
    BotEvent,
    BotLineLog,
    BrowserListen,
    BrowserPlayback,
    ClassifierCall,
    CustomerEvent,
    ErrorEvent,
    LineRate,
    PhoneTurn,
    Recording,
    SessionLog,
    SessionStore,
    SttModelName,
    SttReading,
    TtsCall,
    TurnLatency,
    new_session_id,
)
from samajh.server.settings import Settings, load_settings
from samajh.server.speech import (
    LIVE,
    PATIENT,
    ClientProfile,
    SpeechClient,
    live_client,
    second_profile,
    stt_options,
    stt_params,
    tts_options,
)
from samajh.server.stream import StreamFactory, StreamHub
from samajh.types import Language

if TYPE_CHECKING:
    from samajh.server.records import CallRecord, RecordBook

REPO = Path(__file__).resolve().parents[2]
WEB_DIR = REPO / "web"
MAX_TURN_BYTES = 6 * 1024 * 1024  # 30 s of 48 kHz stereo 16-bit is 5.8 MB
MAX_JSON_BYTES = 16 * 1024
# A two-product call in which every answer is unclear takes 43 customer turns.
MAX_TURNS = 60
MAX_EVENTS = 999  # AUDIO_NAME has three digits for the seq
MAX_BOT_SECONDS = 120  # per line
LINE_GAP_SECONDS = 0.15  # silence between the lines of one utterance
# Sessions held in memory. Past this many, idle ones are dropped (finished calls first); a
# dropped call is read from its log again by the next request for it.
MAX_LIVE_SESSIONS = 64
CLIP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.wav$")
SOURCES = ("mic", "file", "none")
PHONE_MODES = ("vad", "ptt", "file")
UPLOAD_SECONDS = 20.0  # a turn's body must arrive within this
# Names a browser on this machine uses for the server. "testserver" is Starlette's TestClient.
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]", "testserver")
LANGUAGES = (
    {"id": "hi", "label": "Hindi", "experimental": False},
    {"id": "hi-en", "label": "Hinglish", "experimental": False},
    {"id": "ta", "label": "Tamil", "experimental": True},
    {"id": "kn", "label": "Kannada", "experimental": True},
)

M = TypeVar("M", bound=BaseModel)
T = TypeVar("T")


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSession(_Body):
    # None: the server's default (`/api/health` names it). Any name the app was not built with is
    # refused (422 unknown_dialogue); the app `python -m samajh.server` runs has only "samajh".
    dialogue: str | None = None
    line_rate: LineRate = 8000
    params: dict[str, str] = {}
    # The right-party setting for this one call (the phone's demo picker), the fields of
    # `samajh.identity.IdentityPolicy`; None: the server's `[identity]`. Anything outside the menu
    # is refused (422 invalid_identity). Stored in the session params as canonical JSON.
    identity: dict[str, Any] | None = None
    # False: this call never streams its primary reading. Absent or true: it streams when the
    # server's `[streaming]` is on; a session can turn streaming off, never on.
    streaming: bool | None = None


class EndSession(_Body):
    reason: Literal["hangup"] = "hangup"


@dataclass(frozen=True)
class _TurnRequest:
    source: Literal["mic", "file", "none"]
    reply_to: int
    part: int
    eos_wait_ms: float | None
    phone: PhoneTurn | None
    stream: bool = False  # `stream=1`: the phone streamed this reply (samajh.server.stream)


class _Gnani:
    """The injected client, or the real one built on first use so the server starts without a key."""

    def __init__(self, client: SpeechClient | None, profile: ClientProfile) -> None:
        self._client, self._profile = client, profile
        self._lock = threading.Lock()

    def get(self) -> SpeechClient:
        with self._lock:
            if self._client is None:
                self._client = live_client(self._profile)
            return self._client

    def configured(self) -> bool:
        try:
            self.get()
        except ConfigError:
            return False
        return True


@dataclass
class _Live:
    """One call in memory. `log` is replaced, never edited in place, when a change is saved."""

    log: SessionLog
    started: float  # time.monotonic() at the moment the session was created, in any server run
    dialogue: Dialogue | None = None  # built on the first turn this server run handles
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # every read and change of `log`
    # Held from before a turn's body is read until its reply is stored, so one upload per call is
    # buffered at a time and a duplicate request finds the first one's stored reply.
    turns: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0  # requests in flight; a session in use is never dropped from memory
    # Bot events whose lines are being made or were made in this server run, by seq.
    speech: dict[int, _SpeechJob] = field(default_factory=dict)

    @classmethod
    def resumed(cls, log: SessionLog) -> _Live:
        try:
            age = (datetime.now(UTC) - datetime.fromisoformat(log.created_at)).total_seconds()
        except (ValueError, TypeError):  # not a time, or one without a zone
            age = 0.0
        # `at` never runs backwards, whatever the wall clock did between the two runs.
        return cls(log, time.monotonic() - max(age, max((e.at for e in log.events), default=0.0)))

    def now(self) -> float:
        return round(time.monotonic() - self.started, 3)


class _TooLate(Exception):
    pass


_Line = tuple[bytes, TtsCall]  # one line's canonical WAV at the line rate, and its Timbre call


@dataclass(frozen=True)
class _Spoken:
    """An event's lines joined as `_speak` always joined them, ready to commit."""

    wav: bytes
    spans: list[tuple[float, float]]
    calls: list[TtsCall]
    synth_ms: float


class _SpeechJob:
    """One bot event's lines, made in order in a worker thread: a future per line and one for
    the joined audio. The last line's future is set after `done`, so whoever waits for the last
    line finds the joined audio ready to commit. A failure fails that line and every later one."""

    def __init__(self, seq: int, count: int, made: Mapping[int, _Line]) -> None:
        self.seq = seq
        self.lines: list[Future[_Line]] = [Future() for _ in range(count)]
        self.done: Future[_Spoken] = Future()
        # Set once a request has answered with this job's failure: only then does the next
        # request start a fresh job, so a failure made before anyone asked is still reported.
        self.reported = False
        # Set when a later take of the turn this event answers begins: no further line is started.
        self.cancelled = False
        for index, line in made.items():
            self.lines[index].set_result(line)

    def failed(self) -> bool:
        return self.done.done() and self.done.exception() is not None

    def made(self) -> dict[int, _Line]:
        return {i: f.result() for i, f in enumerate(self.lines) if f.done() and f.exception() is None}

    def fail_from(self, index: int, exc: BaseException) -> None:
        for future in [*self.lines[index:], self.done]:
            if not future.done():
                future.set_exception(exc)


async def _wait(future: Future[T]) -> T:
    # Shielded: a request that goes away must not cancel a line another request is waiting for.
    return await asyncio.shield(asyncio.wrap_future(future))


def _line_wav(pcm: bytes, rate: int) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return out.getvalue()


def _cut(wav: bytes, rate: int, start_s: float, end_s: float) -> bytes:
    """One line out of an event's joined audio (a canonical mono 16-bit WAV)."""
    with wave.open(io.BytesIO(wav)) as f:
        frames = f.readframes(f.getnframes())
    return _line_wav(frames[2 * round(start_s * rate) : 2 * round(end_s * rate)], rate)


class _Gate:
    """Foreground speech requests (a turn's STT, a line made on demand) in flight or waiting. No
    speech request runs in the background: a line in flight cannot be pre-empted, and the account
    has one REST slot, so a background line could make a customer's turn wait past its lock bound
    (session 20261113T231244-5156873b7fce: 503 `gnani_busy` behind a 7 s line)."""

    def __init__(self) -> None:
        self._busy = 0
        self._idle = threading.Condition()

    @contextmanager
    def foreground(self) -> Iterator[None]:
        with self._idle:
            self._busy += 1
        try:
            yield
        finally:
            with self._idle:
                self._busy -= 1
                self._idle.notify_all()

    def wait_idle(self, stop: threading.Event) -> None:
        with self._idle:
            while self._busy and not stop.is_set():
                self._idle.wait(0.2)


log = logging.getLogger(__name__)


def _prefetch(dialogue: Dialogue, state: str, text: str) -> None:
    """Let the dialogue start reading the primary transcript before the second reading is awaited.
    Skipped for empty text or a dialogue without `prefetch`; a failure is logged, never raised."""
    prefetch = getattr(dialogue, "prefetch", None)
    if prefetch is None or not text.strip():
        return
    try:
        prefetch(state, text)
    except Exception:
        log.warning("dialogue prefetch raised; the turn goes on", exc_info=True)


def _within(seconds: float, call: Callable[[], T]) -> T:
    """`call()`, or `_TooLate` once `seconds` have passed. The call cannot be interrupted, so it
    runs in a thread of its own that is left to finish; its result is then dropped."""
    done: queue.SimpleQueue[tuple[T | None, Exception | None]] = queue.SimpleQueue()

    def run() -> None:
        try:
            done.put((call(), None))
        except Exception as exc:  # noqa: BLE001 - handed to the waiting thread, which raises it
            done.put((None, exc))

    threading.Thread(target=run, daemon=True, name="second-reading").start()
    try:
        result, error = done.get(timeout=seconds)
    except queue.Empty:
        raise _TooLate from None
    if error is not None:
        raise error
    return result  # type: ignore[return-value]


def _ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000, 1)


def _not_found(what: str) -> ApiProblem:
    return ApiProblem(404, "session", f"{what}_not_found", f"no such {what}")


def _not_active() -> ApiProblem:
    return ApiProblem(409, "session", "session_not_active", "the call has ended or cannot be continued")


def _out_of_order(why: str) -> ApiProblem:
    return ApiProblem(409, "session", "turn_out_of_order", why)


def _audio_url(session_id: str, name: str) -> str:
    return f"/api/sessions/{session_id}/audio/{name}"


def _summary(log: SessionLog) -> dict[str, Any]:
    return {
        "session_id": log.session_id,
        "status": log.status,
        "ended_reason": log.ended_reason,
        "events": len(log.events),
        "turns": len(_customer_turns(log)),
        "recording_seconds": log.recording.seconds if log.recording else None,
    }


def _customer_turns(log: SessionLog) -> list[CustomerEvent]:
    return [e for e in log.events if isinstance(e, CustomerEvent) and not e.superseded]


def _call_language(params: Mapping[str, str]) -> Language:
    try:
        return Language(params.get("language", "hi"))
    except ValueError:
        return Language.hi


def _reading(
    role: Literal["primary", "second"], options: PrismaV30 | PrismaV25, transcript: Transcript
) -> SttReading:
    return SttReading(
        role=role,
        model=options.model,
        # A flag, not the words: the name is not stored a second time.
        params=stt_params(options) | ({"keyterms": "1"} if getattr(options, "keyterms", ()) else {}),
        text=transcript.text,
        literal=transcript.literal,
        detected_language=transcript.detected_language,
        cache_hit=transcript.call.cache_hit,
        seconds=transcript.call.seconds,
        attempts=transcript.call.attempts,
        est_credits=transcript.call.est_credits,
        request_id=transcript.request_id,
        cache_key=transcript.call.cache_key,
        http_status=None if transcript.call.cache_hit else 200,
    )


def position_of(state: str | None) -> dict[str, str | int | float | bool | None] | None:
    """The scalar values of the dialogue state's `position` object; None when there is none.
    Never more of the state: it holds every turn's text."""
    try:
        position = json.loads(state)["position"]  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - any unreadable state has no position
        return None
    if not isinstance(position, dict):
        return None
    return {
        k: v
        for k, v in position.items()
        if isinstance(k, str) and (v is None or isinstance(v, str | int | float | bool))
    }


def _classifier(step: Step) -> ClassifierCall | None:
    found = getattr(step, "classifier", None)
    if isinstance(found, ClassifierCall):
        return found
    if isinstance(found, BaseModel | dict):
        try:
            return ClassifierCall.model_validate(
                found.model_dump() if isinstance(found, BaseModel) else found
            )
        except ValidationError:
            return None
    return None


def _acted_on(readings: list[SttReading], text: str) -> SttReading | None:
    """The reading whose text the dialogue recorded as the turn. When both readings say the same,
    the primary is named (either is true). None: nothing was read, or the text is neither."""
    return next((r for r in readings if r.ok and r.text and r.text == text), None)


def _plan(
    log: SessionLog, reply_to: int, part: int
) -> tuple[CustomerEvent, BotEvent] | Literal["fresh", "supersede"]:
    """What a turn identified by `(reply_to, part)` is: one already answered (the stored events),
    the answer to the open prompt, or a later take of the last answer. ApiProblem otherwise."""
    current = [e for e in log.events if not isinstance(e, ErrorEvent) and not e.superseded]
    asked = current[-1]
    answer = next((e for e in current if isinstance(e, CustomerEvent) and e.reply_to == reply_to), None)
    if answer is None:
        if reply_to != asked.seq:
            raise _out_of_order("reply_to is not the prompt this call is waiting on")
        if log.status != "active":
            raise _not_active()
        return "fresh"
    reply = log.events[answer.seq + 1]
    assert isinstance(reply, BotEvent)
    if part == answer.part:
        return answer, reply
    if part < answer.part:
        raise ApiProblem(409, "session", "turn_superseded", "a later take of this turn has been stored")
    if reply is not asked:
        raise _out_of_order("the call has moved on from that turn")
    if log.closed:
        raise _out_of_order("the call is closed: its case file has been started")
    # A take can reopen a call that the reply to the earlier take ended, never one hung up.
    if log.status != "active" and log.ended_reason != "dialogue":
        raise _not_active()
    return "supersede"


WARM_BOUND_S = 8.0  # session create stops starting first-name lines after this


class Sessions:
    """The calls this server can reach: those in memory, and every log on disk.

    The blocking methods run in worker threads, one per session at a time: the caller holds the
    session's lock. `locked` and `save` are the way in for a router outside this module.
    """

    def __init__(
        self,
        store: SessionStore,
        gnani: _Gnani,
        second: _Gnani,
        dialogues: Mapping[str, DialogueFactory],
        settings: Settings,
        default_dialogue: str,
        loans: LoanBook | None = None,
    ) -> None:
        self.store, self.gnani, self.second = store, gnani, second
        self.dialogues, self.settings, self.default_dialogue = dialogues, settings, default_dialogue
        self.loans = loans
        self.live: dict[str, _Live] = {}
        self.gate = _Gate()
        # Set by `create_app` when prewarming is on: given a new session's log, its first-name
        # lines, made inside `create` (before the response) when not already cached.
        self.warm_plan: Callable[[SessionLog], Sequence[tuple[str, Timbre]]] | None = None
        # Set by `create_app`: the record book, for the first name sent as a Prisma keyterm.
        self.records: RecordBook | None = None
        # Set by `create_app`: the primary reading by streaming, when `[streaming]` is on.
        self.streams: StreamHub | None = None

    @asynccontextmanager
    async def use(self, session_id: str) -> AsyncIterator[_Live]:
        """The session, from memory or from its log. 404 if there is no readable log."""
        live = self.live.get(session_id)
        if live is None:
            log = await anyio.to_thread.run_sync(self.store.load, session_id)
            if log is None:
                raise _not_found("session")
            live = self.live.setdefault(session_id, _Live.resumed(log))
        live.users += 1
        try:
            self._trim()
            yield live
        finally:
            live.users -= 1

    @asynccontextmanager
    async def locked(self, session_id: str) -> AsyncIterator[SessionLog]:
        """The session's log, with every other request of that call held off meanwhile. Change it
        in place and `save` it (in a worker thread) before leaving the block."""
        async with self.use(session_id) as live, live.lock:
            yield live.log

    def save(self, log: SessionLog) -> None:
        """Write the log; an ended call's `call.wav` is assembled first."""
        if log.status == "ended":
            log.recording = self.store.assemble_recording(log)
        self.store.save(log)

    def adopt(self, live: _Live) -> None:
        self.live[live.log.session_id] = live
        self._trim(keep=live)

    def _trim(self, keep: _Live | None = None) -> None:
        idle = [s for s, call in self.live.items() if call.users == 0 and call is not keep]
        idle.sort(key=lambda s: self.live[s].log.status != "ended")  # stable: oldest first
        for session_id in idle[: max(0, len(self.live) - MAX_LIVE_SESSIONS)]:
            del self.live[session_id]

    def _commit(self, live: _Live, change: Callable[[SessionLog], None]) -> None:
        """Apply `change` to a copy of the log and write it. Memory follows the disk: if the
        write fails, the call is where it was."""
        draft = live.log.model_copy(deep=True)
        change(draft)
        self.save(draft)
        live.log = draft

    def bot_json(self, log: SessionLog, event: BotEvent) -> dict[str, Any]:
        patience = self.settings.turn_taking[event.listen]
        return {
            "seq": event.seq,
            "text": event.text,
            "lines": [
                {
                    "key": line.key,
                    "text": line.text,
                    "audio_url": f"/api/sessions/{log.session_id}/lines/{event.seq}/{i}.wav",
                }
                for i, line in enumerate(event.lines)
            ],
            "line_gap_ms": round(LINE_GAP_SECONDS * 1000),
            "language": event.language,
            "end_call": event.end_call,
            "audio_url": _audio_url(log.session_id, f"bot-{event.seq:03d}.wav"),
            "listen": {"kind": event.listen, "cut_ms": patience.cut_ms, "grace_ms": patience.grace_ms},
            "second_reading": event.second_reading,
        }

    def turn_json(self, log: SessionLog, customer: CustomerEvent, bot: BotEvent) -> dict[str, Any]:
        customer = shown_event(log, customer)  # a log written before the year reply was withheld
        name = (customer.audio or "").removeprefix("audio/")
        shown = {"role", "model", "ok", "error", "text", "cache_hit", "seconds"}
        return {
            "customer": {
                "seq": customer.seq,
                "part": customer.part,
                "transcript": customer.transcript,
                "acted_on": customer.acted_on,
                "literal": customer.literal,
                "detected_language": customer.detected_language,
                "readings": [r.model_dump(include=shown) for r in customer.readings],
                "readings_agreed": customer.readings_agreed,
                "followed_by": customer.followed_by,
                "degraded": customer.degraded,
                "audio_url": _audio_url(log.session_id, name) if name else None,
                "audio_seconds": customer.audio_seconds,
                "latency": customer.latency and customer.latency.model_dump(),
                "pauses": customer.pauses and customer.pauses.model_dump(),
            },
            "bot": self.bot_json(log, bot),
            "ended": bot.end_call,
            # The dialogue's outcome on the reply that ends the call, else None; and whether the
            # person on the line had passed the identity checks (None: the dialogue does not say).
            "outcome": bot.tags.get("outcome") if bot.end_call else None,
            "speaker_confirmed": log.speaker_confirmed,
        }

    def stored_reply(self, log: SessionLog, reply_to: int, part: int) -> dict[str, Any] | None:
        """The reply already given to this turn, if it has one. ApiProblem for a turn that can
        never be taken, so that its audio need not be read."""
        plan = _plan(log, reply_to, part)
        return None if isinstance(plan, str) else self.turn_json(log, *plan)

    def _bot_event(self, log: SessionLog, step: Step, seq: int, at: float) -> BotEvent:
        if not isinstance(step, Step):
            raise TypeError("the dialogue did not return a Step")
        said = step.say
        # An utterance this session cannot speak, or cannot transcribe the reply to, fails here,
        # before it is logged, and not on the customer's next turn.
        tts_options(log.tts, said.language, log.line_rate)
        if not said.end_call:
            stt_options(log.stt, said.language)
            if said.second_reading:
                stt_options(log.stt, said.language, "second")
        return BotEvent(
            seq=seq,
            at=at,
            text=said.text,
            lines=[BotLineLog(key=line.key, text=line.text, tags=dict(line.tags)) for line in said.lines],
            language=said.language,
            end_call=said.end_call,
            listen=said.listen,
            second_reading=said.second_reading,
            tags=dict(said.tags),
        )

    def _link(self, params: dict[str, str]) -> dict[str, str]:
        """The params to store: a `loan` session gets its link to the batch (`LINK_PARAMS`) here,
        once, after the check that a call may be placed on it. ApiProblem when it may not. A
        session on a packaged record has no link, so a client that sends one is refused."""
        if "loan" not in params:
            if params.keys() & set(LINK_PARAMS):
                raise ApiProblem(422, "request", "invalid_params", "only a loan-book call has a batch link")
            return params
        if "record" in params:
            raise ApiProblem(
                422, "request", "record_and_loan", "a session names a record or a loan, not both"
            )
        if params.keys() & (set(LINK_PARAMS) - {"call_date"}):  # the client may ask for a call date
            raise ApiProblem(422, "request", "invalid_params", "the batch link is set by the server")
        if self.loans is None:
            raise ApiProblem(409, "request", "no_batch", "this server has no loan book")
        try:
            link = self.loans.open_call(params["loan"], params.get("call_date"))
        except LoanRefused as refused:
            raise ApiProblem(refused.status, "request", refused.code, refused.message) from None
        return params | link.params()

    def create(self, request: CreateSession) -> _Live:
        name = request.dialogue or self.default_dialogue
        factory = self.dialogues.get(name)
        if factory is None:
            raise ApiProblem(422, "request", "unknown_dialogue", "no dialogue has that name")
        params = self._link(dict(request.params))
        if IDENTITY_PARAM in params:
            raise ApiProblem(422, "request", "invalid_params", "send the identity setting as `identity`")
        if request.identity is not None:
            try:
                policy = parse_policy(request.identity)
            except ValueError as error:
                raise ApiProblem(422, "request", "invalid_identity", str(error)) from None
            params[IDENTITY_PARAM] = identity_param(policy)
        try:
            dialogue = factory(params)
        except ValueError:
            raise ApiProblem(422, "request", "invalid_params", "the dialogue refused these params") from None
        log = SessionLog(
            session_id=new_session_id(),
            created_at=datetime.now(UTC).isoformat(timespec="milliseconds"),
            dialogue=name,
            params=params,
            line_rate=request.line_rate,
            stt=self.settings.stt,
            tts=self.settings.tts_for(_call_language(params)),
        )
        live = _Live(log, time.monotonic(), dialogue)
        try:
            step = dialogue.start()
            log.events.append(self._bot_event(log, step, 0, live.now()))
            log.dialogue_state = step.state
            log.speaker_confirmed = step.speaker_confirmed
        except Exception as exc:
            raise problem_from(exc, "dialogue") from exc
        self.save(log)
        if request.streaming is False and self.streams is not None:
            self.streams.off.add(log.session_id)
        if self.warm_plan is not None:
            self._warm(self.warm_plan(log))
        self._job(live, 0)
        return live

    def _keyterms(
        self, log: SessionLog, asked: BotEvent, options: PrismaV30 | PrismaV25
    ) -> PrismaV30 | PrismaV25:
        """A REST v3.0 reply to a right-party line gets the record's first name as its one keyterm
        (the first name only: it is not a value under test). Anything else is left as it is."""
        if not isinstance(options, PrismaV30) or not any(
            (line.key or "").startswith("right_party.") for line in asked.lines
        ):
            return options
        try:
            record, _ = resolve_record(log.params, self.records, self.loans)
        except ValueError:
            return options
        first = record.record.borrower.name.split()[0]
        return options.model_copy(update={"keyterms": (first,)})

    def _warm(self, lines: Sequence[tuple[str, Timbre]]) -> None:
        """Make the lines not yet cached, in the foreground, before the session's first response.
        No new line starts after `WARM_BOUND_S`; a failure stops the rest. Either way it is
        logged and the call goes on: the reply job makes a missing line on demand."""
        from samajh.server.prompts import is_cached

        deadline = time.monotonic() + WARM_BOUND_S
        try:
            client = self.gnani.get()
            for text, options in lines:
                if is_cached(client, text, options):
                    continue
                if time.monotonic() > deadline:
                    log.warning(
                        "session create: first-name lines past %.0f s; the rest on demand", WARM_BOUND_S
                    )
                    return
                with self.gate.foreground():
                    client.tts(text, options)
        except Exception as exc:  # noqa: BLE001 - the reply job makes the line on demand
            log.warning("session create: a first-name line failed; the rest on demand: %s", exc)

    def _dialogue(self, live: _Live) -> Dialogue:
        if live.dialogue is None:
            factory = self.dialogues.get(live.log.dialogue)
            if factory is None:
                raise _not_active()
            try:
                live.dialogue = factory(live.log.params)
            except ValueError:
                raise _not_active() from None
        return live.dialogue

    def _fail(self, live: _Live, exc: Exception, stage: Stage, **audio: Any) -> ApiProblem:
        problem = problem_from(exc, stage)
        log = live.log
        last = log.events[-1]
        # A prompt fetched again and again while Timbre is down must not fill the log. Failed
        # turns are counted against the event limit when the turn starts.
        repeat = (
            stage == "tts"
            and isinstance(last, ErrorEvent)
            and (last.code, last.message) == (problem.code, problem.message)
        )
        if repeat or len(log.events) >= MAX_EVENTS:
            return problem
        failed = ErrorEvent(
            seq=len(log.events),
            at=live.now(),
            stage=problem.stage,
            status=problem.status,
            code=problem.code,
            message=problem.message,
            **audio,
        )
        self._commit(live, lambda draft: draft.events.append(failed))
        return problem

    def _second(self, log: SessionLog, asked: BotEvent, wav: bytes) -> SttReading:
        """The second model's reading, or a missing one: it never fails the turn, and never
        holds it for longer than the session's bound."""
        status: int | None = None
        attempts = 0  # unknown for a timed-out reading
        options = stt_options(log.stt, asked.language, "second")
        clock = time.perf_counter()
        try:
            transcript = _within(log.stt.second_timeout_s, lambda: self.second.get().stt(wav, options))
        except _TooLate:
            error = "timeout"
        except Exception as exc:  # noqa: BLE001 - any failure is a missing reading, by its code
            problem = problem_from(exc, "stt")
            error, status = problem.code, problem.upstream_status
            cause: BaseException | None = exc
            while cause is not None and not isinstance(getattr(cause, "attempts", None), int):
                cause = cause.__cause__
            attempts = cause.attempts if cause is not None else 0  # type: ignore[attr-defined]
        else:
            return _reading("second", options, transcript)
        return SttReading(
            role="second",
            model=options.model,
            params=stt_params(options),
            ok=False,
            error=error,
            seconds=round(time.perf_counter() - clock, 3),
            http_status=status,
            attempts=attempts,
        )

    def _streams_hands_free(self, live: _Live, request: _TurnRequest) -> bool:
        """The phone streams every hands-free microphone take when the session streams (it never
        sends `stream=1`), so a missing stream on such a turn is a fallback to mark, not plain REST."""
        return (
            self.streams is not None
            and self.streams.enabled_for(live.log.session_id)
            and request.source == "mic"
            and request.phone is not None
            and request.phone.mode == "vad"
        )

    def _primary(
        self, live: _Live, request: _TurnRequest, options: PrismaV30 | PrismaV25, wav: bytes, received: float
    ) -> SttReading:
        """The stream's reading when this reply was streamed, else REST (marked with why the
        stream was not used, when one was expected)."""
        fallback: str | None = None
        if self.streams is not None:
            wait = self.streams.config.commit_timeout_s + 0.5 - (time.perf_counter() - received)
            got = self.streams.take(
                live.log.session_id,
                request.reply_to,
                request.part,
                requested=request.stream or self._streams_hands_free(live, request),
                received=received,
                wait_s=max(wait, 0),
            )
            if isinstance(got, SttReading):
                return got
            fallback = got
        with self.gate.foreground():
            transcript = self.gnani.get().stt(wav, options)
        reading = _reading("primary", options, transcript)
        if fallback is not None:
            reading = reading.model_copy(update={"params": reading.params | {"stream_fallback": fallback}})
        return reading

    def turn(self, live: _Live, request: _TurnRequest, body: bytes | None, received: float) -> dict[str, Any]:
        log = live.log
        plan = _plan(log, request.reply_to, request.part)
        if not isinstance(plan, str):
            return self.turn_json(log, *plan)
        if len(_customer_turns(log)) >= MAX_TURNS + (plan == "supersede") or len(log.events) + 2 > MAX_EVENTS:
            raise ApiProblem(409, "session", "turn_limit", f"a call has at most {MAX_TURNS} customer turns")
        dialogue = self._dialogue(live)
        # A later take is heard in place of the earlier one, from the state before that one.
        state = log.dialogue_undo if plan == "supersede" else log.dialogue_state
        asked = log.events[request.reply_to]
        if state is None or not isinstance(asked, BotEvent):
            raise _not_active()
        earlier = (
            next(e for e in _customer_turns(log) if e.reply_to == request.reply_to)
            if plan == "supersede"
            else None
        )
        if earlier is not None:
            # The earlier take's reply is being replaced: stop making its lines before this
            # take's STT needs the one slot. If this take fails, a fetch restarts that job.
            pending = live.speech.get(earlier.seq + 1)
            if pending is not None:
                pending.cancelled = True
        seq, at = len(log.events), live.now()
        audio: dict[str, Any] = {}
        readings: list[SttReading] = []
        pauses = None
        heard = Heard(text="")
        normalise_ms = stt_ms = second_ms = 0.0
        stage: Stage = "audio"
        try:
            if request.source != "none":
                if body is None:
                    raise AudioRejected("audio_too_large", f"a turn can be at most {MAX_TURN_BYTES} bytes")
                clock = time.perf_counter()
                wav = normalise_turn(body, log.line_rate)
                normalise_ms = _ms(clock)
                audio = {
                    "audio": self.store.write_audio(log.session_id, f"customer-{seq:03d}.wav", wav),
                    "audio_seconds": wav_seconds(wav),
                }
                pauses = pause_stats(wav)
                stage = "stt"
                options = self._keyterms(log, asked, stt_options(log.stt, asked.language))
                clock = time.perf_counter()
                readings.append(self._primary(live, request, options, wav, received))
                stt_ms = _ms(clock)
                _prefetch(dialogue, state, readings[0].text)
                second: str | None = None
                if asked.second_reading:
                    clock = time.perf_counter()
                    with self.gate.foreground():
                        readings.append(self._second(log, asked, wav))
                    second_ms = _ms(clock)
                    second = readings[1].text if readings[1].ok else ""
                heard = Heard(
                    text=readings[0].text,
                    literal=readings[0].literal,
                    detected_language=readings[0].detected_language,
                    second=second,
                )
            stage = "dialogue"
            clock = time.perf_counter()
            step = dialogue.step(state, heard)
            bot = self._bot_event(log, step, seq + 1, live.now())
            dialogue_ms = _ms(clock)
        except Exception as exc:
            raise self._fail(live, exc, stage, **audio) from exc
        transcript = heard.text if step.heard is None else step.heard
        acted = _acted_on(readings, transcript)
        customer = CustomerEvent(
            seq=seq,
            at=at,
            source=request.source,
            reply_to=request.reply_to,
            part=request.part,
            transcript=transcript,
            acted_on=acted.role if acted else None,
            literal=acted.literal if acted else heard.literal,
            detected_language=heard.detected_language,
            readings=readings,
            readings_agreed=readings_agreed(readings, step.agreed),
            degraded=step.degraded,
            followed_by=followed_by(bot.lines),
            latency=TurnLatency(
                normalise_ms=normalise_ms,
                stt_ms=stt_ms,
                second_stt_ms=second_ms,
                dialogue_ms=dialogue_ms,
                server_ms=_ms(received),
                eos_wait_ms=request.eos_wait_ms,
            ),
            pauses=pauses,
            phone=request.phone,
            classifier=_classifier(step),
            state_before=position_of(state),
            state_after=position_of(step.state),
            **audio,
        )
        if answers_year_question(asked.lines):  # never logged or sent: `samajh_dialogue.WITHHELD`
            customer = withhold_reply(customer)

        def apply(draft: SessionLog) -> None:
            if earlier is not None:
                for event in draft.events[earlier.seq : earlier.seq + 2]:  # the take and its reply
                    event.superseded = True
                draft.status, draft.ended_reason, draft.recording = "active", None, None
            else:
                draft.dialogue_undo = draft.dialogue_state
            draft.events += [customer, bot]
            draft.dialogue_state = step.state
            draft.speaker_confirmed = step.speaker_confirmed
            if bot.end_call:
                draft.status, draft.ended_reason = "ended", "dialogue"

        self._commit(live, apply)
        self._job(live, bot.seq)
        return self.turn_json(live.log, customer, bot)

    def _refuse(self, log: SessionLog, event: BotEvent) -> None:
        """After a hang-up nothing more is spoken; the prompt that ends a call still is, until the
        case file is started, because from then on the recording must not change."""
        if log.ended_reason == "hangup" or log.closed:
            raise _not_active()
        if event.superseded:
            raise ApiProblem(409, "session", "turn_superseded", "a later take replaced this reply")

    def _job(self, live: _Live, seq: int) -> _SpeechJob:
        """The job making event `seq`'s lines; started now if there is none, or if the last one
        failed (a fresh job keeps the lines already made)."""
        job = live.speech.get(seq)
        if job is not None and not (job.failed() and (job.reported or job.cancelled)):
            return job
        event = live.log.events[seq]
        assert isinstance(event, BotEvent)
        job = _SpeechJob(seq, len(event.lines), job.made() if job else {})
        live.speech[seq] = job
        threading.Thread(
            target=self._make, args=(live, event, job), name=f"samajh-speak-{seq}", daemon=True
        ).start()
        return job

    def _make(self, live: _Live, event: BotEvent, job: _SpeechJob) -> None:
        """Every line is its own Timbre call, so the client's cache serves a line that another
        call has spoken; the clips are joined into the event's one audio file. Runs in its own
        thread, holding no lock; each line is a foreground request (`_Gate`)."""
        clock = time.perf_counter()
        rate = live.log.line_rate
        index = 0
        try:
            options = tts_options(live.log.tts, event.language, rate)
            made: list[_Line] = []
            for index, line in enumerate(event.lines):
                if job.lines[index].done():
                    made.append(job.lines[index].result())
                    continue
                current = live.log.events[event.seq]
                self._refuse(live.log, current)  # type: ignore[arg-type]
                if job.cancelled:
                    raise ApiProblem(409, "session", "turn_superseded", "a later take is being heard")
                line_clock = time.perf_counter()
                with self.gate.foreground():
                    speech = self.gnani.get().tts(line.text, options)
                try:
                    clip = to_line_pcm(speech.audio, rate, MAX_BOT_SECONDS)[0]
                except AudioRejected:
                    raise BadResponse("Timbre: the audio could not be read as PCM WAV") from None
                call = TtsCall(
                    model=options.model,
                    voice=options.voice,
                    language=options.language,
                    sample_rate=options.sample_rate,
                    cache_hit=speech.call.cache_hit,
                    seconds=speech.call.seconds,
                    attempts=speech.call.attempts,
                    est_credits=speech.call.est_credits,
                    request_id=speech.request_id,
                    synth_ms=_ms(line_clock),
                )
                made.append((clip, call))
                if index < len(event.lines) - 1:
                    job.lines[index].set_result((clip, call))
            index = len(event.lines) - 1
            wav, spans = join_clips([clip for clip, _ in made], rate, LINE_GAP_SECONDS)
            job.done.set_result(_Spoken(wav, spans, [call for _, call in made], _ms(clock)))
            if not job.lines[index].done():
                job.lines[index].set_result(made[index])
        except BaseException as exc:  # noqa: BLE001 - handed to whoever waits for these lines
            job.fail_from(index, exc)

    def _commit_spoken(self, live: _Live, job: _SpeechJob) -> None:
        """Write the joined audio and its line fields once. Nothing is committed (409) once the
        call was hung up or closed or the event superseded: audio made before then counts only
        if it was committed."""
        log = live.log
        event = log.events[job.seq]
        assert isinstance(event, BotEvent)
        if event.audio is not None:
            return
        self._refuse(log, event)
        spoken = job.done.result()
        reference = self.store.write_audio(log.session_id, f"bot-{job.seq:03d}.wav", spoken.wav)

        def apply(draft: SessionLog) -> None:
            said = draft.events[job.seq]
            assert isinstance(said, BotEvent)
            said.audio, said.audio_seconds = reference, spoken.spans[-1][1]
            said.synth_ms = spoken.synth_ms
            for line, call, (start, end) in zip(said.lines, spoken.calls, spoken.spans, strict=True):
                line.tts, line.start_s, line.end_s = call, round(start, 6), round(end, 6)

        self._commit(live, apply)

    async def _settle(self, live: _Live, job: _SpeechJob, future: Future[T]) -> T:
        """Wait, without the session's lock, for one of `job`'s futures; then, under the lock,
        log a failure (`_fail` dedups repeats) or commit the joined audio if it is ready."""
        try:
            result = await _wait(future)
        except ApiProblem:
            raise
        except Exception as exc:
            job.reported = True
            async with live.lock:
                problem = await anyio.to_thread.run_sync(self._fail, live, exc, "tts")
            raise problem from exc
        if job.done.done() and job.done.exception() is None:
            async with live.lock:
                await anyio.to_thread.run_sync(self._commit_spoken, live, job)
        return result

    def audio(self, live: _Live, name: str) -> bytes | _SpeechJob:
        """One event's audio, or the job to wait for when a bot prompt has not been spoken yet.
        Served only if the log refers to it. The caller holds the session's lock."""
        log = live.log
        if not AUDIO_NAME.fullmatch(name):
            raise _not_found("audio")
        if any(e.audio == f"audio/{name}" for e in log.events):
            data = self.store.read_audio(log.session_id, name)
            if data is None:
                raise _not_found("audio")
            return data
        unspoken = [e for e in log.events if isinstance(e, BotEvent) and name == f"bot-{e.seq:03d}.wav"]
        if not unspoken:
            raise _not_found("audio")
        self._refuse(log, unspoken[0])
        return self._job(live, unspoken[0].seq)

    async def joined(self, live: _Live, name: str) -> bytes:
        async with live.lock:
            got = await anyio.to_thread.run_sync(self.audio, live, name)
        if isinstance(got, bytes):
            return got
        return (await self._settle(live, got, got.done)).wav

    def _line(self, live: _Live, seq: int, index: int) -> bytes | tuple[_SpeechJob, Future[_Line]]:
        log = live.log
        event = log.events[seq] if 0 <= seq < len(log.events) else None
        if not isinstance(event, BotEvent) or not 0 <= index < len(event.lines):
            raise _not_found("line")
        job = live.speech.get(seq)
        if event.audio is not None:
            if job is not None and job.lines[index].done() and job.lines[index].exception() is None:
                return job.lines[index].result()[0]
            line = event.lines[index]
            data = self.store.read_audio(log.session_id, event.audio.removeprefix("audio/"))
            if data is None or line.start_s is None or line.end_s is None:
                raise _not_found("line")
            return _cut(data, log.line_rate, line.start_s, line.end_s)
        self._refuse(log, event)
        job = self._job(live, seq)
        return job, job.lines[index]

    async def line(self, live: _Live, seq: int, index: int) -> bytes:
        """One line of a bot event as its own WAV, as soon as it is made."""
        async with live.lock:
            got = await anyio.to_thread.run_sync(self._line, live, seq, index)
        if isinstance(got, bytes):
            return got
        return (await self._settle(live, *got))[0]

    def note_browser(self, live: _Live, seq: int, report: BrowserListen | BrowserPlayback) -> None:
        """Store the phone's report on event `seq`. Only session.json is rewritten: never the
        recording, the dialogue state or the status, whatever the call's status."""
        draft = live.log.model_copy(deep=True)
        event = draft.events[seq]
        fits = {CustomerEvent: BrowserListen, BotEvent: BrowserPlayback}.get(type(event))
        if fits is None or not isinstance(report, fits):
            raise ApiProblem(422, "request", "wrong_event", "this report does not fit that event")
        event.browser = report  # type: ignore[union-attr]
        self.store.save(draft)
        live.log = draft

    def end(self, live: _Live) -> dict[str, Any]:
        def apply(draft: SessionLog) -> None:
            draft.status, draft.ended_reason = "ended", "hangup"

        if live.log.status == "active":
            self._commit(live, apply)
        return _summary(live.log)

    def recording(self, live: _Live) -> bytes:
        log = live.log
        if log.status == "ended" and not log.closed:
            self._commit(live, lambda draft: None)
        elif log.status == "active":
            self.store.assemble_recording(log)
        data = self.store.read_recording(log.session_id)
        if data is None:
            raise _not_found("recording")
        return data


class CaseJobs:
    """The after-call job of each closed Samajh call: one thread per call, at most one at a time.

    `case.json` is the job's state. A job that a server run left "running" (it stopped
    mid-job) is started again by the next request for the case; the clients' caches make the
    rerun cost nothing for the steps that had finished. A "failed" case is rerun on request.
    """

    def __init__(
        self,
        sessions: Sessions,
        records: RecordBook | None,
        batch: _Gnani,
        llm: Callable[[], Llm],
        loans: LoanBook | None = None,
    ) -> None:
        self.sessions, self.records, self.batch, self.llm = sessions, records, batch, llm
        self.loans = loans
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def _record(self, log: SessionLog) -> CallRecord:
        """The call's record, resolved from its stored params. Never asks whether a call may be
        placed: a loan-book call that has been ingested must still have its case read and rebuilt."""
        if log.dialogue != "samajh" or (self.records is None and self.loans is None):
            raise ApiProblem(409, "session", "no_case_file", "only a Samajh call has a case file")
        try:
            return resolve_record(log.params, self.records, self.loans)[0]
        except ValueError:
            raise ApiProblem(
                409, "session", "no_case_file", "the call's record is not on this server"
            ) from None

    def read(self, session_id: str) -> CaseFile | None:
        data = self.sessions.store.read_case(session_id)
        if data is None:
            return None
        try:
            return CaseFile.model_validate_json(data)
        except ValidationError:
            return None

    def running(self, session_id: str) -> bool:
        with self._lock:
            thread = self._threads.get(session_id)
            return thread is not None and thread.is_alive()

    def start(self, live: _Live) -> dict[str, Any]:
        """Close the call if need be and start its job, unless one is running or has finished.
        The caller holds the session's lock."""
        log = live.log
        record = self._record(log)
        if log.status != "ended":
            raise ApiProblem(409, "session", "session_active", "the call has not ended")
        case = self.read(log.session_id)
        if case is not None and (case.status == "ready" or self.running(log.session_id)):
            return case.model_dump(mode="json")
        if not log.closed:

            def close(draft: SessionLog) -> None:
                draft.closed = True

            self.sessions._commit(live, close)
        snapshot = live.log.model_copy(deep=True)
        case = new_case(snapshot, record)
        self.sessions.store.write_case(snapshot.session_id, case.model_dump_json(indent=2).encode())
        thread = threading.Thread(
            target=self._run, args=(snapshot, record), daemon=True, name=f"case-{snapshot.session_id}"
        )
        with self._lock:
            self._threads[snapshot.session_id] = thread
        thread.start()
        return case.model_dump(mode="json")

    def _run(self, log: SessionLog, record: CallRecord) -> None:
        store, settings = self.sessions.store, self.sessions.settings

        def recording() -> tuple[Recording, bytes]:
            made = store.assemble_recording(log)
            data = store.read_recording(log.session_id)
            if data is None:
                raise ValueError("call.wav was not written")
            return made, data

        try:
            case = build_case(
                log,
                record,
                recording=recording,
                batch=self.batch.get,
                llm=self.llm,
                batch_model=settings.batch.model,
                num_speakers=settings.batch.num_speakers,
                batch_timeout_s=settings.batch.timeout_s,
            )
        except Exception as exc:  # noqa: BLE001 - the case must never be left "running" by a bug
            case = new_case(log, record)
            case.status, case.failed = "failed", ["transcript"]
            case.steps = [StepResult(name="transcript", ok=False, error=f"{type(exc).__name__}", seconds=0.0)]
        store.write_case(log.session_id, case.model_dump_json(indent=2).encode())

    def get(self, live: _Live) -> dict[str, Any]:
        log = live.log
        self._record(log)
        case = self.read(log.session_id)
        if case is None:
            raise ApiProblem(404, "session", "case_not_started", "the case file has not been started")
        if case.status == "running" and not self.running(log.session_id):
            return self.start(live)
        return case.model_dump(mode="json")


def _stream_hub(settings: Settings, client: _Gnani, factory: StreamFactory | None) -> StreamHub:
    """Streams through the real client's key, ledger and cap unless a factory is injected."""
    config = settings.streaming
    if factory is None and config.enabled:
        from samajh.clients.gnani.stream import stream_session

        def factory(options: Any) -> Any:
            return stream_session(client.get(), options, max_stream_seconds=config.max_stream_seconds)

    rate = 0.010
    if config.enabled and factory is not None:
        try:
            rate = float(getattr(client.get(), "_stt_rate", rate))
        except ConfigError:
            pass
    return StreamHub(config, factory, rate)


def sessions_of(app: FastAPI) -> Sessions:
    """The seam for a router that lives outside this module (the after-call case file)."""
    sessions: Sessions = app.state.sessions
    return sessions


def _whole(query: QueryParams, name: str, low: int) -> int | None:
    if name not in query:
        return None
    raw = query[name]
    if not (raw.isascii() and raw.isdigit() and len(raw) <= 3 and int(raw) >= low):
        raise ApiProblem(422, "request", f"invalid_{name}", f"{name} must be a whole number from {low}")
    return int(raw)


def _millis(query: QueryParams, name: str) -> float | None:
    if name not in query:
        return None
    try:
        value = float(query[name])
    except ValueError:
        value = math.nan
    if not 0 <= value <= 600_000:
        raise ApiProblem(422, "request", f"invalid_{name}", f"{name} must be a number of ms")
    return value


def _turn_request(query: QueryParams) -> _TurnRequest:
    source = query.get("source")
    if source not in SOURCES:
        raise ApiProblem(422, "request", "invalid_source", "source must be mic, file or none")
    reply_to = _whole(query, "reply_to", 0)
    if reply_to is None:
        raise ApiProblem(
            422, "request", "reply_to_required", "reply_to must name the prompt this turn answers"
        )
    part = _whole(query, "part", 1)
    eos_wait_ms = _millis(query, "eos_wait_ms")
    cut_ms, grace_ms = _millis(query, "cut_ms"), _millis(query, "grace_ms")
    phone: PhoneTurn | None = None
    if "mode" in query or cut_ms is not None or grace_ms is not None:
        mode = query.get("mode")
        if mode not in PHONE_MODES:
            raise ApiProblem(422, "request", "invalid_mode", "mode must be vad, ptt or file")
        phone = PhoneTurn(mode=mode, cut_ms=cut_ms, grace_ms=grace_ms)
    stream = query.get("stream", "0")
    if stream not in ("0", "1"):
        raise ApiProblem(422, "request", "invalid_stream", "stream must be 0 or 1")
    return _TurnRequest(source, reply_to, 1 if part is None else part, eos_wait_ms, phone, stream == "1")


async def _read(request: Request, limit: int) -> bytes | None:
    """The body, or None if it is over `limit`. Stops reading at the limit: Content-Length can be
    absent or wrong, so it only serves to refuse early."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return None
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


async def _json(request: Request, model: type[M]) -> M:
    raw = await _read(request, MAX_JSON_BYTES)
    if raw is None:
        raise ApiProblem(
            413, "request", "body_too_large", f"a JSON body can be at most {MAX_JSON_BYTES} bytes"
        )
    try:
        return model.model_validate_json(raw.strip() or b"{}")
    except ValidationError as exc:
        where = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'body'}: {e['msg']}" for e in exc.errors()[:3])
        raise ApiProblem(422, "request", "invalid_request", where) from None


class _LocalOnly:
    """Refuses a request addressed to a host name this server does not go by, or sent by a page
    of another origin. The server has no login, so without this a web page open in the same
    browser could place calls (and spend credits) by posting to 127.0.0.1."""

    def __init__(self, app: ASGIApp, hosts: frozenset[str]) -> None:
        self.app, self.hosts = app, hosts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope["headers"])
            host = headers.get(b"host", b"").decode("latin-1").lower()
            name = host if host.endswith("]") else host.rsplit(":", 1)[0] if ":" in host else host
            if name.count(":") and not name.startswith("["):  # a bare IPv6 host without a port
                name = host
            origin = headers.get(b"origin")
            problem: ApiProblem | None = None
            if name not in self.hosts:
                problem = ApiProblem(
                    403, "request", "host_not_allowed", "this server is not reachable by that name"
                )
            elif origin is not None and urlsplit(origin.decode("latin-1")).netloc.lower() != host:
                problem = ApiProblem(
                    403, "request", "foreign_origin", "requests from another site are refused"
                )
            if problem is not None and scope["type"] == "websocket":
                await receive()  # websocket.connect; a close before accept is a 403 to the browser
                await send({"type": "websocket.close", "code": 1008, "reason": problem.code})
                return
            if problem is not None:
                await JSONResponse(problem.body(), status_code=problem.status)(scope, receive, send)
                return
        await self.app(scope, receive, send)


@cache
def _default_llm() -> Llm:
    from samajh.pipeline import default_llm

    return default_llm()


def _clips(clips_dir: Path | None) -> dict[str, Path]:
    if clips_dir is None or not clips_dir.is_dir():
        return {}
    return {
        path.name: path
        for path in sorted(clips_dir.iterdir())
        if CLIP_NAME.fullmatch(path.name) and not path.is_symlink() and path.is_file()
    }


def _default_clips_dir() -> Path | None:
    configured = os.environ.get("SAMAJH_CLIPS_DIR")
    if configured:
        return Path(configured)
    fixtures = REPO / "tests" / "fixtures" / "server" / "stub-call"
    return fixtures if fixtures.is_dir() else None


def _prewarm_lifespan(
    calls: Sessions, gnani: _Gnani, settings: Settings, records: RecordBook | None, loans: LoanBook
) -> Callable[[FastAPI], Any]:
    from samajh.server import prompts
    from samajh.server.samajh_dialogue import TTS_LANGUAGE

    sources = prompts.servable(records, loans)

    def plan(log: SessionLog) -> list[tuple[str, Timbre]]:
        """A new session's first-name lines in its call language and line rate (cached already
        for a record-book record in a prewarm language and rate; a loan's are made at create)."""
        language = _call_language(log.params)
        options = tts_options(log.tts, TTS_LANGUAGE[language], log.line_rate)
        try:
            record, _ = resolve_record(log.params, records, loans)
        except ValueError:
            return []  # a dialogue without a record (the stub) has no first-name lines
        return [(text, options) for _, text in prompts.record_lines(language, prompts.Slots.of(record))]

    def startup() -> None:
        if not gnani.configured():
            missing = prompts.missing_static(prompts.offline_reader(), settings, sources)
            log.warning(
                "prewarm: NO GNANI KEY: %d static and first-name bot lines are not in the cache and cannot be made; "
                "calls will fail",
                len(missing),
            )
            return
        report = prompts.prewarm_static(
            gnani.get(), settings, sources
        )  # PrewarmFailed, PrewarmOverBudget: no start
        log.warning(
            "prewarm: %d static and record-book first-name lines checked, %d missing, %d made, about %.2f credits (an estimate)",
            report.checked,
            report.missing,
            report.made,
            report.est_credits,
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await anyio.to_thread.run_sync(startup)
        calls.warm_plan = plan
        try:
            yield
        finally:
            calls.warm_plan = None

    return lifespan


def _warm_ledgers(calls: Sessions) -> None:
    """Have each live client read the shared ledger once now, so the credit-cap check of a
    call's first uncached request reads only appended rows. A client without a key, or one
    without `warm_ledger` (a fake), is skipped; a failure is logged, never raised."""
    seen: list[SpeechClient] = []
    for gnani in (calls.gnani, calls.second):
        try:
            client = gnani.get()
        except ConfigError:
            continue
        if any(client is other for other in seen):
            continue
        seen.append(client)
        warm = getattr(client, "warm_ledger", None)
        if warm is None:
            continue
        try:
            warm()
        except Exception as exc:  # noqa: BLE001 - the first capped request reads it instead
            log.warning("could not read the Gnani ledger at start: %s", exc)


def _ledger_lifespan(calls: Sessions, inner: Callable[[FastAPI], Any] | None) -> Callable[[FastAPI], Any]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await anyio.to_thread.run_sync(_warm_ledgers, calls)
        if inner is None:
            yield
            return
        async with inner(app):
            yield

    return lifespan


def create_app(
    *,
    gnani: SpeechClient | None = None,
    second: SpeechClient | None = None,
    state: Path | None = None,
    dialogues: Mapping[str, DialogueFactory] | None = None,
    records: RecordBook | None = None,
    settings: Settings | None = None,
    web_dir: Path | None = WEB_DIR,
    clips_dir: Path | None = None,
    profile: Literal["live", "patient"] = "live",
    allowed_hosts: Sequence[str] = LOCAL_HOSTS,
    batch: SpeechClient | None = None,
    llm: Callable[[], Llm] | None = None,
    prewarm: bool | None = None,
    stream_factory: StreamFactory | None = None,
) -> FastAPI:
    """`second` is the client for the second reading of a turn; without it an injected `gnani`
    serves both, and the real second client gives up at the settings' bound. `batch` runs Prisma
    Batch after the call (an injected `gnani` by default, else the patient real client), and
    `llm` builds the extraction client (default `samajh.pipeline.default_llm`).

    `prewarm` (None: on when the settings enable it and no `gnani` was injected) makes the static
    bot lines and the record book's first-name lines before the server accepts a connection,
    refusing to start if one cannot be made; a session whose first-name lines are not cached makes
    them inside its create. Nothing is synthesised in the background (`samajh.server.prompts`)."""
    settings = settings or load_settings()
    # Sessions, the review batch and the loan book live under `state`. The Gnani and OpenRouter
    # clients keep their lock, cache and ledger under `samajh.clients._runtime.state_dir()`
    # whatever `state` is, so a server on another state directory still shares the one-slot lock.
    root = state or state_dir()
    loans = LoanBook(root)
    if dialogues is None:
        # Imported here so that an app given its own dialogues does not need these modules.
        from samajh.server.records import default_book
        from samajh.server.samajh_dialogue import samajh_factory

        records = records or default_book()
        # The Samajh call only. The stub (which asks about a loan with no identity check) is
        # reachable only by a caller that passes it in `dialogues`: a test, or the in-process replay.
        dialogues = {"samajh": samajh_factory(records, settings, loans=loans)}
    registry = dict(dialogues)
    client = _Gnani(gnani, LIVE if profile == "live" else PATIENT)
    calls = Sessions(
        SessionStore(root / "sessions"),
        client,
        _Gnani(second or gnani, second_profile(settings.stt.second_timeout_s)),
        registry,
        settings,
        "samajh" if "samajh" in registry else next(iter(registry)),
        loans,
    )
    calls.streams = _stream_hub(settings, client, stream_factory)
    calls.records = records
    jobs = CaseJobs(calls, records, _Gnani(batch or gnani, PATIENT), llm or _default_llm, loans)
    clips_dir = clips_dir or _default_clips_dir()
    warm = settings.prewarm.enabled and gnani is None if prewarm is None else prewarm
    prewarming = _prewarm_lifespan(calls, _Gnani(gnani, PATIENT), settings, records, loans) if warm else None
    lifespan = _ledger_lifespan(calls, prewarming) if gnani is None else prewarming
    app = FastAPI(
        title="Samajh voice transport", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.state.sessions = calls
    app.state.cases = jobs
    app.add_middleware(_LocalOnly, hosts=frozenset(h.lower() for h in allowed_hosts))

    @app.exception_handler(ApiProblem)
    async def _problem(request: Request, problem: ApiProblem) -> JSONResponse:
        return JSONResponse(problem.body(), status_code=problem.status)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return await _problem(request, ApiProblem(exc.status_code, "request", code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _crash(request: Request, exc: Exception) -> JSONResponse:
        return await _problem(request, problem_from(exc, "request"))

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "gnani_key_configured": client.configured(),
            "dialogues": sorted(registry),
            "default_dialogue": calls.default_dialogue,
            "line_rates": [8000, 16000],
            "stt_models": list(get_args(SttModelName)),
            # What a call on this server uses, from its settings: the phone's model strip.
            "models": {
                "stt_primary": {"model": settings.stt.model, "format": settings.stt.format},
                "stt_second": {"model": settings.stt.second_model, "format": settings.stt.second_format},
                "tts": {"model": settings.tts.model},
                "batch": {"model": settings.batch.model},
            },
            "streaming": settings.streaming.enabled,
            "languages": list(LANGUAGES),
            "turn_taking": {kind: p.model_dump() for kind, p in settings.turn_taking.items()},
            "limits": {
                "max_turn_bytes": MAX_TURN_BYTES,
                "max_turn_seconds": int(MAX_TURN_SECONDS),
                "max_turns": MAX_TURNS,
            },
        }

    @app.get("/api/records")
    def list_records() -> dict[str, Any]:
        return {"records": records.listing() if records is not None else [], "languages": list(LANGUAGES)}

    @app.get("/api/loans")
    def list_loans() -> dict[str, Any]:
        """The drawn loans of the batch under the state directory that a call may be placed on now."""
        return {"loans": loans.callable(), "languages": list(LANGUAGES)}

    @app.get("/api/clips")
    def list_clips() -> dict[str, Any]:
        listed = ((name, wav_seconds(path.read_bytes())) for name, path in _clips(clips_dir).items())
        return {"clips": [{"name": n, "seconds": round(s, 3)} for n, s in listed if s is not None]}

    @app.get("/api/clips/{name}")
    def clip(name: str) -> Response:
        path = _clips(clips_dir).get(name)
        if path is None:
            raise _not_found("clip")
        return Response(path.read_bytes(), media_type="audio/wav")

    @app.post("/api/sessions", status_code=201)
    async def create_session(request: Request) -> dict[str, Any]:
        wanted = await _json(request, CreateSession)
        live = await anyio.to_thread.run_sync(calls.create, wanted)
        calls.adopt(live)
        log = live.log
        first = log.events[0]
        assert isinstance(first, BotEvent)
        return {
            "session_id": log.session_id,
            "dialogue": log.dialogue,
            "line_rate": log.line_rate,
            "streaming": calls.streams is not None and calls.streams.enabled_for(log.session_id),
            "bot": calls.bot_json(log, first),
        }

    @app.websocket("/api/sessions/{session_id}/stream")
    async def stream(ws: WebSocket, session_id: str) -> None:
        """The phone's audio for one reply, streamed to Prisma (`samajh.server.stream`). Closed
        with 1008 before accepting when streaming is off, the session is not active, or the reply
        is not the prompt now awaiting an answer."""
        hub = calls.streams
        raw = ws.query_params.get("reply_to", "")
        options = None
        if hub is not None and hub.enabled_for(session_id) and raw.isascii() and raw.isdigit():
            reply_to = int(raw)
            try:
                async with calls.use(session_id) as live, live.lock:
                    log = live.log
                    current = [e for e in log.events if not isinstance(e, ErrorEvent) and not e.superseded]
                    asked = current[-1] if current else None  # the one prompt the call waits on
                    if (
                        log.status == "active"
                        and isinstance(asked, BotEvent)
                        and asked.seq == reply_to
                        and not asked.end_call
                    ):
                        options = hub.options(asked.language, log.line_rate)
            except (ApiProblem, ValueError):
                options = None
        if hub is None or options is None:
            await ws.close(code=1008)
            return
        await ws.accept()
        await hub.serve(ws, session_id, reply_to, options)

    @app.post("/api/sessions/{session_id}/turns")
    async def turn(session_id: str, request: Request) -> dict[str, Any]:
        async with calls.use(session_id) as live:
            wanted = _turn_request(request.query_params)
            async with live.turns:
                async with live.lock:
                    stored = calls.stored_reply(live.log, wanted.reply_to, wanted.part)
                if stored is not None:
                    return stored
                body: bytes | None = None
                if wanted.source != "none":
                    try:
                        with anyio.fail_after(UPLOAD_SECONDS):
                            body = await _read(request, MAX_TURN_BYTES)
                    except TimeoutError:
                        raise ApiProblem(
                            408,
                            "request",
                            "upload_timeout",
                            f"the audio did not arrive within {UPLOAD_SECONDS:g} s",
                            True,
                        ) from None
                received = time.perf_counter()
                async with live.lock:
                    return await anyio.to_thread.run_sync(calls.turn, live, wanted, body, received)

    @app.get("/api/sessions/{session_id}/audio/{name}")
    async def audio(session_id: str, name: str) -> Response:
        async with calls.use(session_id) as live:
            data = await calls.joined(live, name)
        return Response(data, media_type="audio/wav")

    @app.get("/api/sessions/{session_id}/lines/{seq}/{name}")
    async def line_audio(session_id: str, seq: str, name: str) -> Response:
        index = name.removesuffix(".wav")
        if not (re.fullmatch(r"\d{1,3}", seq) and name.endswith(".wav") and re.fullmatch(r"\d{1,2}", index)):
            raise _not_found("line")
        async with calls.use(session_id) as live:
            data = await calls.line(live, int(seq), int(index))
        return Response(data, media_type="audio/wav")

    @app.post("/api/sessions/{session_id}/events/{seq}/browser")
    async def browser_report(session_id: str, seq: int, request: Request) -> dict[str, Any]:
        async with calls.use(session_id) as live, live.lock:
            events = live.log.events
            if not 0 <= seq < len(events):
                raise _not_found("event")
            kind = {"customer": BrowserListen, "bot": BrowserPlayback}.get(events[seq].type)
            if kind is None:
                raise ApiProblem(422, "request", "wrong_event", "only bot and customer events take a report")
            report = await _json(request, kind)
            await anyio.to_thread.run_sync(calls.note_browser, live, seq, report)
        return {"ok": True}

    @app.post("/api/sessions/{session_id}/end")
    async def end(session_id: str, request: Request) -> dict[str, Any]:
        await _json(request, EndSession)
        if calls.streams is not None:
            calls.streams.cancel(session_id, "ended")
        async with calls.use(session_id) as live, live.lock:
            return await anyio.to_thread.run_sync(calls.end, live)

    @app.get("/api/sessions/{session_id}")
    async def session(session_id: str) -> dict[str, Any]:
        async with calls.locked(session_id) as log:
            return shown_log(log).model_dump(mode="json", exclude={"dialogue_state", "dialogue_undo"})

    @app.get("/api/sessions/{session_id}/recording.wav")
    async def recording(session_id: str) -> Response:
        async with calls.use(session_id) as live, live.lock:
            data = await anyio.to_thread.run_sync(calls.recording, live)
        return Response(data, media_type="audio/wav")

    @app.post("/api/sessions/{session_id}/case")
    async def start_case(session_id: str) -> dict[str, Any]:
        async with calls.use(session_id) as live, live.lock:
            return await anyio.to_thread.run_sync(jobs.start, live)

    @app.get("/api/sessions/{session_id}/case")
    async def get_case(session_id: str) -> dict[str, Any]:
        async with calls.use(session_id) as live, live.lock:
            return await anyio.to_thread.run_sync(jobs.get, live)

    app.include_router(review_router(root))
    app.include_router(identity_router(settings, records, loans))
    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app
