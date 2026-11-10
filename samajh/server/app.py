"""The HTTP side of a call: sessions, turns, audio, and the static phone page.

The log on disk is the call. Each change is one atomic rewrite of `session.json`, which holds the
events and the dialogue's state together, so a customer turn is applied exactly once and any
server run can continue a call that an earlier run began. Sessions in memory are a cache of that
file plus the lock that orders the requests of one call.
"""

from __future__ import annotations

import asyncio
import math
import os
import queue
import re
import threading
import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar, get_args
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.datastructures import QueryParams
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from samajh.clients._runtime import state_dir
from samajh.clients.errors import BadResponse, ConfigError
from samajh.clients.gnani import PrismaV25, PrismaV30, Transcript, wav_seconds
from samajh.server.audio import (
    MAX_TURN_SECONDS,
    AudioRejected,
    join_clips,
    normalise_turn,
    pause_stats,
    to_line_pcm,
)
from samajh.server.dialogue import Dialogue, DialogueFactory, Heard, Step, stub_factory
from samajh.server.errors import ApiProblem, Stage, problem_from
from samajh.server.review_routes import review_router
from samajh.server.sessionlog import (
    AUDIO_NAME,
    BotEvent,
    BotLineLog,
    CustomerEvent,
    ErrorEvent,
    LineRate,
    PhoneTurn,
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
from samajh.types import Language

if TYPE_CHECKING:
    from samajh.server.records import RecordBook

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
    dialogue: str | None = None  # None: the server's default (`/api/health` names it)
    line_rate: LineRate = 8000
    params: dict[str, str] = {}


class EndSession(_Body):
    reason: Literal["hangup"] = "hangup"


@dataclass(frozen=True)
class _TurnRequest:
    source: Literal["mic", "file", "none"]
    reply_to: int
    part: int
    eos_wait_ms: float | None
    phone: PhoneTurn | None


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
        params=stt_params(options),
        text=transcript.text,
        literal=transcript.literal,
        detected_language=transcript.detected_language,
        cache_hit=transcript.call.cache_hit,
        seconds=transcript.call.seconds,
        attempts=transcript.call.attempts,
        est_credits=transcript.call.est_credits,
        request_id=transcript.request_id,
    )


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
    ) -> None:
        self.store, self.gnani, self.second = store, gnani, second
        self.dialogues, self.settings, self.default_dialogue = dialogues, settings, default_dialogue
        self.live: dict[str, _Live] = {}

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
            "lines": [{"key": line.key, "text": line.text} for line in event.lines],
            "language": event.language,
            "end_call": event.end_call,
            "audio_url": _audio_url(log.session_id, f"bot-{event.seq:03d}.wav"),
            "listen": {"kind": event.listen, "cut_ms": patience.cut_ms, "grace_ms": patience.grace_ms},
            "second_reading": event.second_reading,
        }

    def turn_json(self, log: SessionLog, customer: CustomerEvent, bot: BotEvent) -> dict[str, Any]:
        name = (customer.audio or "").removeprefix("audio/")
        shown = {"role", "model", "ok", "error", "text", "cache_hit", "seconds"}
        return {
            "customer": {
                "seq": customer.seq,
                "part": customer.part,
                "transcript": customer.transcript,
                "readings": [r.model_dump(include=shown) for r in customer.readings],
                "audio_url": _audio_url(log.session_id, name) if name else None,
                "audio_seconds": customer.audio_seconds,
                "latency": customer.latency and customer.latency.model_dump(),
                "pauses": customer.pauses and customer.pauses.model_dump(),
            },
            "bot": self.bot_json(log, bot),
            "ended": bot.end_call,
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

    def create(self, request: CreateSession) -> _Live:
        name = request.dialogue or self.default_dialogue
        factory = self.dialogues.get(name)
        if factory is None:
            raise ApiProblem(422, "request", "unknown_dialogue", "no dialogue has that name")
        try:
            dialogue = factory(request.params)
        except ValueError:
            raise ApiProblem(422, "request", "invalid_params", "the dialogue refused these params") from None
        log = SessionLog(
            session_id=new_session_id(),
            created_at=datetime.now(UTC).isoformat(timespec="milliseconds"),
            dialogue=name,
            params=request.params,
            line_rate=request.line_rate,
            stt=self.settings.stt,
            tts=self.settings.tts_for(_call_language(request.params)),
        )
        live = _Live(log, time.monotonic(), dialogue)
        try:
            step = dialogue.start()
            log.events.append(self._bot_event(log, step, 0, live.now()))
            log.dialogue_state = step.state
        except Exception as exc:
            raise problem_from(exc, "dialogue") from exc
        self.save(log)
        return live

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
        options = stt_options(log.stt, asked.language, "second")
        clock = time.perf_counter()
        try:
            transcript = _within(log.stt.second_timeout_s, lambda: self.second.get().stt(wav, options))
        except _TooLate:
            error = "timeout"
        except Exception as exc:  # noqa: BLE001 - any failure is a missing reading, by its code
            error = problem_from(exc, "stt").code
        else:
            return _reading("second", options, transcript)
        return SttReading(
            role="second",
            model=options.model,
            params=stt_params(options),
            ok=False,
            error=error,
            seconds=round(time.perf_counter() - clock, 3),
        )

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
                options = stt_options(log.stt, asked.language)
                clock = time.perf_counter()
                readings.append(_reading("primary", options, self.gnani.get().stt(wav, options)))
                stt_ms = _ms(clock)
                second: str | None = None
                if asked.second_reading:
                    clock = time.perf_counter()
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
        customer = CustomerEvent(
            seq=seq,
            at=at,
            source=request.source,
            reply_to=request.reply_to,
            part=request.part,
            transcript=heard.text,
            literal=heard.literal,
            detected_language=heard.detected_language,
            readings=readings,
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
            **audio,
        )

        def apply(draft: SessionLog) -> None:
            if earlier is not None:
                for event in draft.events[earlier.seq : earlier.seq + 2]:  # the take and its reply
                    event.superseded = True
                draft.status, draft.ended_reason, draft.recording = "active", None, None
            else:
                draft.dialogue_undo = draft.dialogue_state
            draft.events += [customer, bot]
            draft.dialogue_state = step.state
            if bot.end_call:
                draft.status, draft.ended_reason = "ended", "dialogue"

        self._commit(live, apply)
        return self.turn_json(live.log, customer, bot)

    def audio(self, live: _Live, name: str) -> bytes:
        """One event's audio. Served only if the log refers to it; a bot prompt that has not been
        spoken yet is synthesised now."""
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
        # After a hang-up nothing more is spoken; the prompt that ends a call still is, until the
        # case file is started, because from then on the recording must not change.
        if log.ended_reason == "hangup" or log.closed:
            raise _not_active()
        if unspoken[0].superseded:
            raise ApiProblem(409, "session", "turn_superseded", "a later take replaced this reply")
        return self._speak(live, unspoken[0], name)

    def _speak(self, live: _Live, event: BotEvent, name: str) -> bytes:
        """Every line is its own Timbre call, so the client's cache serves a line that another
        call has spoken; the clips are joined into the event's one audio file."""
        log = live.log
        clock = time.perf_counter()
        calls: list[TtsCall] = []
        clips: list[bytes] = []
        try:
            options = tts_options(log.tts, event.language, log.line_rate)
            for line in event.lines:
                speech = self.gnani.get().tts(line.text, options)
                try:
                    clips.append(to_line_pcm(speech.audio, log.line_rate, MAX_BOT_SECONDS)[0])
                except AudioRejected:
                    raise BadResponse("Timbre: the audio could not be read as PCM WAV") from None
                calls.append(
                    TtsCall(
                        model=options.model,
                        voice=options.voice,
                        language=options.language,
                        sample_rate=options.sample_rate,
                        cache_hit=speech.call.cache_hit,
                        seconds=speech.call.seconds,
                        attempts=speech.call.attempts,
                        est_credits=speech.call.est_credits,
                        request_id=speech.request_id,
                    )
                )
            wav, spans = join_clips(clips, log.line_rate, LINE_GAP_SECONDS)
        except Exception as exc:
            raise self._fail(live, exc, "tts") from exc
        reference = self.store.write_audio(log.session_id, name, wav)

        def apply(draft: SessionLog) -> None:
            spoken = draft.events[event.seq]
            assert isinstance(spoken, BotEvent)
            spoken.audio, spoken.audio_seconds = reference, spans[-1][1]
            spoken.synth_ms = _ms(clock)
            for line, call, (start, end) in zip(spoken.lines, calls, spans, strict=True):
                line.tts, line.start_s, line.end_s = call, round(start, 6), round(end, 6)

        self._commit(live, apply)
        return wav

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
    return _TurnRequest(source, reply_to, 1 if part is None else part, eos_wait_ms, phone)


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
        if scope["type"] == "http":
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
            if problem is not None:
                await JSONResponse(problem.body(), status_code=problem.status)(scope, receive, send)
                return
        await self.app(scope, receive, send)


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
) -> FastAPI:
    """`second` is the client for the second reading of a turn; without it an injected `gnani`
    serves both, and the real second client gives up at the settings' bound."""
    settings = settings or load_settings()
    if dialogues is None:
        # Imported here so that an app given its own dialogues does not need these modules.
        from samajh.server.records import default_book
        from samajh.server.samajh_dialogue import samajh_factory

        records = records or default_book()
        dialogues = {"samajh": samajh_factory(records, settings), "stub": stub_factory}
    registry = dict(dialogues)
    client = _Gnani(gnani, LIVE if profile == "live" else PATIENT)
    calls = Sessions(
        SessionStore((state or state_dir()) / "sessions"),
        client,
        _Gnani(second or gnani, second_profile(settings.stt.second_timeout_s)),
        registry,
        settings,
        "samajh" if "samajh" in registry else next(iter(registry)),
    )
    clips_dir = clips_dir or _default_clips_dir()
    app = FastAPI(title="Samajh voice transport", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = calls
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
            "streaming": False,
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
            "bot": calls.bot_json(log, first),
        }

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
        async with calls.use(session_id) as live, live.lock:
            data = await anyio.to_thread.run_sync(calls.audio, live, name)
        return Response(data, media_type="audio/wav")

    @app.post("/api/sessions/{session_id}/end")
    async def end(session_id: str, request: Request) -> dict[str, Any]:
        await _json(request, EndSession)
        async with calls.use(session_id) as live, live.lock:
            return await anyio.to_thread.run_sync(calls.end, live)

    @app.get("/api/sessions/{session_id}")
    async def session(session_id: str) -> dict[str, Any]:
        async with calls.locked(session_id) as log:
            return log.model_dump(mode="json", exclude={"dialogue_state", "dialogue_undo"})

    @app.get("/api/sessions/{session_id}/recording.wav")
    async def recording(session_id: str) -> Response:
        async with calls.use(session_id) as live, live.lock:
            data = await anyio.to_thread.run_sync(calls.recording, live)
        return Response(data, media_type="audio/wav")

    app.include_router(review_router(state or state_dir()))
    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app
