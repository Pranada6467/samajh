"""The HTTP side of a call: sessions, turns, audio, and the static phone page.

Live sessions (the ones this process created) are kept in memory with their Dialogue; the log on
disk is rewritten after every change, so a finished call can be read by a later server run.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from samajh.clients._runtime import state_dir
from samajh.clients.errors import BadResponse, ConfigError
from samajh.clients.gnani import wav_seconds
from samajh.server.audio import MAX_TURN_SECONDS, AudioRejected, normalise_turn, to_line_pcm
from samajh.server.dialogue import (
    BotUtterance,
    CallView,
    Dialogue,
    DialogueFactory,
    Exchange,
    Heard,
    stub_factory,
)
from samajh.server.errors import ApiProblem, Stage, problem_from
from samajh.server.sessionlog import (
    AUDIO_NAME,
    BotEvent,
    CustomerEvent,
    ErrorEvent,
    LineRate,
    SessionLog,
    SessionStore,
    SttCall,
    SttModelName,
    SttSettings,
    TtsCall,
    TtsSettings,
    TurnLatency,
    new_session_id,
)
from samajh.server.speech import (
    LIVE,
    PATIENT,
    SpeechClient,
    live_client,
    stt_options,
    stt_params,
    tts_options,
)

REPO = Path(__file__).resolve().parents[2]
WEB_DIR = REPO / "web"
MAX_TURN_BYTES = 6 * 1024 * 1024  # 30 s of 48 kHz stereo 16-bit is 5.8 MB
MAX_JSON_BYTES = 16 * 1024
MAX_TURNS = 40
MAX_EVENTS = 999  # AUDIO_NAME has three digits for the seq
MAX_BOT_SECONDS = 120
# Each live call holds its Dialogue in memory. Past this many the oldest is dropped: its log stays
# on disk and readable, and further turns on it get 409 session_not_active.
MAX_LIVE_SESSIONS = 64
CLIP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.wav$")
SOURCES = ("mic", "file", "none")
UPLOAD_SECONDS = 20.0  # a turn's body must arrive within this
# Names a browser on this machine uses for the server. "testserver" is Starlette's TestClient.
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]", "testserver")

M = TypeVar("M", bound=BaseModel)


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSession(_Body):
    dialogue: str = "stub"
    line_rate: LineRate = 8000
    stt_model: SttModelName = "prisma-v3.0"
    params: dict[str, str] = {}


class EndSession(_Body):
    reason: Literal["hangup"] = "hangup"


class _Gnani:
    """The injected client, or the real one built on first use so the server starts without a key."""

    def __init__(self, client: SpeechClient | None, profile: Literal["live", "patient"]) -> None:
        self._client = client
        self._profile = LIVE if profile == "live" else PATIENT
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
    log: SessionLog
    dialogue: Dialogue
    started: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    uploading: bool = False  # one turn body per call is buffered at a time

    def now(self) -> float:
        return round(time.monotonic() - self.started, 3)


def _ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000, 1)


def _not_found(what: str) -> ApiProblem:
    return ApiProblem(404, "session", f"{what}_not_found", f"no such {what}")


def _not_active() -> ApiProblem:
    return ApiProblem(
        409, "session", "session_not_active", "the call has ended or belongs to an earlier server run"
    )


def _audio_url(session_id: str, name: str) -> str:
    return f"/api/sessions/{session_id}/audio/{name}"


def _bot_json(session_id: str, event: BotEvent) -> dict[str, Any]:
    return {
        "seq": event.seq,
        "text": event.text,
        "language": event.language,
        "end_call": event.end_call,
        "audio_url": _audio_url(session_id, f"bot-{event.seq:03d}.wav"),
    }


def _summary(log: SessionLog) -> dict[str, Any]:
    return {
        "session_id": log.session_id,
        "status": log.status,
        "ended_reason": log.ended_reason,
        "events": len(log.events),
        "turns": sum(isinstance(e, CustomerEvent) for e in log.events),
        "recording_seconds": log.recording.seconds if log.recording else None,
    }


def _turn_json(log: SessionLog, customer: CustomerEvent, bot: BotEvent) -> dict[str, Any]:
    stt = customer.stt
    name = (customer.audio or "").removeprefix("audio/")
    return {
        "customer": {
            "seq": customer.seq,
            "transcript": customer.transcript,
            "literal": customer.literal,
            "detected_language": customer.detected_language,
            "audio_url": _audio_url(log.session_id, name) if name else None,
            "audio_seconds": customer.audio_seconds,
            "stt": stt and {"model": stt.model, "cache_hit": stt.cache_hit, "attempts": stt.attempts},
            "latency": customer.latency and customer.latency.model_dump(),
        },
        "bot": _bot_json(log.session_id, bot),
        "ended": bot.end_call,
    }


def _answer_to(log: SessionLog, bot_seq: int) -> dict[str, Any] | None:
    """The stored reply to the turn that answered prompt `bot_seq`, if that prompt was answered."""
    after = [e for e in log.events if e.seq > bot_seq and not isinstance(e, ErrorEvent)]
    if len(after) >= 2 and isinstance(after[0], CustomerEvent) and isinstance(after[1], BotEvent):
        return _turn_json(log, after[0], after[1])
    return None


def _view(log: SessionLog, heard: Heard | None) -> CallView:
    exchanges: list[Exchange] = []
    for event in log.events:
        if isinstance(event, BotEvent):
            said = BotUtterance(
                text=event.text, language=event.language, end_call=event.end_call, tags=event.tags
            )
            exchanges.append(Exchange(bot=said, heard=None))
        elif isinstance(event, CustomerEvent):
            answer = Heard(
                text=event.transcript, literal=event.literal, detected_language=event.detected_language
            )
            exchanges[-1] = Exchange(bot=exchanges[-1].bot, heard=answer)
    if heard is not None:
        exchanges[-1] = Exchange(bot=exchanges[-1].bot, heard=heard)
    return CallView(session_id=log.session_id, params=log.params, exchanges=tuple(exchanges))


class _Calls:
    """Everything a route does that blocks. Called from worker threads, one call per session at a
    time (the route holds the session's lock)."""

    def __init__(self, store: SessionStore, gnani: _Gnani, dialogues: Mapping[str, DialogueFactory]) -> None:
        self.store, self.gnani, self.dialogues = store, gnani, dialogues
        self.live: dict[str, _Live] = {}

    def save(self, log: SessionLog) -> None:
        if log.status == "ended":
            log.recording = self.store.assemble_recording(log)
        self.store.save(log)

    def log_of(self, session_id: str) -> SessionLog:
        """The log of a session of an earlier server run."""
        log = self.store.load(session_id)
        if log is None:
            raise _not_found("session")
        return log

    def _ask(self, live: _Live, heard: Heard | None) -> BotEvent:
        log = live.log
        said = live.dialogue.next(_view(log, heard), heard)
        if not isinstance(said, BotUtterance):
            raise TypeError("the dialogue did not return a BotUtterance")
        # An utterance this session cannot speak, or cannot transcribe the reply to, fails here,
        # before it is logged, and not on the customer's next turn.
        tts_options(log.tts, said.language, log.line_rate)
        if not said.end_call:
            stt_options(log.stt, said.language)
        return BotEvent(
            seq=len(log.events) + (heard is not None),
            at=live.now(),
            text=said.text,
            language=said.language,
            end_call=said.end_call,
            tags=dict(said.tags),
        )

    def create(self, request: CreateSession) -> _Live:
        factory = self.dialogues.get(request.dialogue)
        if factory is None:
            raise ApiProblem(422, "request", "unknown_dialogue", "no dialogue has that name")
        try:
            dialogue = factory(request.params)
        except ValueError:
            raise ApiProblem(422, "request", "invalid_params", "the dialogue refused these params") from None
        log = SessionLog(
            session_id=new_session_id(),
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            dialogue=request.dialogue,
            params=request.params,
            line_rate=request.line_rate,
            stt=SttSettings(model=request.stt_model),
            tts=TtsSettings(),
        )
        live = _Live(log, dialogue)
        try:
            log.events.append(self._ask(live, None))
        except Exception as exc:
            raise problem_from(exc, "dialogue") from exc
        self.save(log)
        self.live[log.session_id] = live
        while len(self.live) > MAX_LIVE_SESSIONS:
            # A finished call goes first; only then the oldest one still in progress.
            ended = (sid for sid, call in self.live.items() if call.log.status == "ended")
            del self.live[next(ended, next(iter(self.live)))]
        return live

    def _fail(self, live: _Live, exc: Exception, stage: Stage, **audio: Any) -> ApiProblem:
        problem = problem_from(exc, stage)
        last = live.log.events[-1]
        # A prompt fetched again and again while Timbre is down must not fill the log. Failed
        # turns are counted against the event limit when the turn starts.
        repeat = (
            stage == "tts"
            and isinstance(last, ErrorEvent)
            and (last.code, last.message)
            == (
                problem.code,
                problem.message,
            )
        )
        if repeat or len(live.log.events) >= MAX_EVENTS:
            return problem
        live.log.events.append(
            ErrorEvent(
                seq=len(live.log.events),
                at=live.now(),
                stage=problem.stage,
                status=problem.status,
                code=problem.code,
                message=problem.message,
                **audio,
            )
        )
        self.save(live.log)
        return problem

    def turn(
        self,
        live: _Live,
        source: Literal["mic", "file", "none"],
        body: bytes | None,
        eos_wait_ms: float | None,
        received: float,
        reply_to: int | None = None,
    ) -> dict[str, Any]:
        log = live.log
        if reply_to is not None:
            # The same turn sent again (the first reply was lost on the way back) gets the stored
            # reply. Without this the audio would answer the next question as well.
            prompts = [e.seq for e in log.events if isinstance(e, BotEvent)]
            if reply_to != prompts[-1]:
                stored = _answer_to(log, reply_to) if reply_to in prompts else None
                if stored is None:
                    raise ApiProblem(
                        409, "session", "turn_out_of_order", "reply_to is not a prompt of this call"
                    )
                return stored
        if log.status != "active":
            raise _not_active()
        turns = sum(isinstance(e, CustomerEvent) for e in log.events)
        if turns >= MAX_TURNS or len(log.events) + 2 > MAX_EVENTS:
            raise ApiProblem(409, "session", "turn_limit", f"a call has at most {MAX_TURNS} customer turns")
        seq, at = len(log.events), live.now()
        asked = next(e for e in reversed(log.events) if isinstance(e, BotEvent))
        name = f"customer-{seq:03d}.wav"
        audio: dict[str, Any] = {}
        stt: SttCall | None = None
        heard = Heard(text="")
        normalise_ms = stt_ms = 0.0
        stage: Stage = "audio"
        try:
            if source != "none":
                if body is None:
                    raise AudioRejected("audio_too_large", f"a turn can be at most {MAX_TURN_BYTES} bytes")
                clock = time.perf_counter()
                wav = normalise_turn(body, log.line_rate)
                normalise_ms = _ms(clock)
                audio = {
                    "audio": self.store.write_audio(log.session_id, name, wav),
                    "audio_seconds": wav_seconds(wav),
                }
                stage = "stt"
                options = stt_options(log.stt, asked.language)
                clock = time.perf_counter()
                transcript = self.gnani.get().stt(wav, options)
                stt_ms = _ms(clock)
                heard = Heard(
                    text=transcript.text,
                    literal=transcript.literal,
                    detected_language=transcript.detected_language,
                )
                stt = SttCall(
                    mode="rest",
                    model=transcript.model,
                    params=stt_params(options),
                    cache_hit=transcript.call.cache_hit,
                    seconds=transcript.call.seconds,
                    attempts=transcript.call.attempts,
                    est_credits=transcript.call.est_credits,
                    request_id=transcript.request_id,
                )
            stage = "dialogue"
            clock = time.perf_counter()
            bot = self._ask(live, heard)
            dialogue_ms = _ms(clock)
        except Exception as exc:
            raise self._fail(live, exc, stage, **audio) from exc
        latency = TurnLatency(
            normalise_ms=normalise_ms,
            stt_ms=stt_ms,
            dialogue_ms=dialogue_ms,
            server_ms=_ms(received),
            eos_wait_ms=eos_wait_ms,
        )
        customer = CustomerEvent(
            seq=seq,
            at=at,
            source=source,
            transcript=heard.text,
            literal=heard.literal,
            detected_language=heard.detected_language,
            stt=stt,
            latency=latency,
            **audio,
        )
        log.events += [customer, bot]
        if bot.end_call:
            log.status, log.ended_reason = "ended", "dialogue"
        self.save(log)
        return _turn_json(log, customer, bot)

    def audio(self, log: SessionLog, name: str, live: _Live | None) -> bytes:
        """One event's audio. Served only if the log refers to it; a bot prompt that has not been
        spoken yet is synthesised now, which only the server run that owns the call may do."""
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
        # After a hang-up nothing more is spoken; the prompt that ends a call still is.
        if live is None or live.log.ended_reason == "hangup":
            raise _not_active()
        return self._speak(live, unspoken[0], name)

    def _speak(self, live: _Live, event: BotEvent, name: str) -> bytes:
        log = live.log
        try:
            options = tts_options(log.tts, event.language, log.line_rate)
            speech = self.gnani.get().tts(event.text, options)
            try:
                wav, seconds = to_line_pcm(speech.audio, log.line_rate, MAX_BOT_SECONDS)
            except AudioRejected:
                raise BadResponse("Timbre: the audio could not be read as PCM WAV") from None
        except Exception as exc:
            raise self._fail(live, exc, "tts") from exc
        event.audio = self.store.write_audio(log.session_id, name, wav)
        event.audio_seconds = seconds
        event.tts = TtsCall(
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
        self.save(log)
        return wav

    def end(self, live: _Live) -> dict[str, Any]:
        if live.log.status == "active":
            live.log.status, live.log.ended_reason = "ended", "hangup"
        self.save(live.log)
        return _summary(live.log)

    def recording(self, log: SessionLog) -> bytes:
        self.store.assemble_recording(log)
        self.save(log)
        data = self.store.read_recording(log.session_id)
        assert data is not None
        return data


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
    state: Path | None = None,
    dialogues: Mapping[str, DialogueFactory] | None = None,
    web_dir: Path | None = WEB_DIR,
    clips_dir: Path | None = None,
    profile: Literal["live", "patient"] = "live",
    allowed_hosts: Sequence[str] = LOCAL_HOSTS,
) -> FastAPI:
    registry = dict(dialogues) if dialogues is not None else {"stub": stub_factory}
    client = _Gnani(gnani, profile)
    calls = _Calls(SessionStore((state or state_dir()) / "sessions"), client, registry)
    clips_dir = clips_dir or _default_clips_dir()
    app = FastAPI(title="Samajh voice transport", docs_url=None, redoc_url=None, openapi_url=None)
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

    def live_session(session_id: str) -> _Live:
        live = calls.live.get(session_id)
        if live is None:
            calls.log_of(session_id)  # 404 unless an earlier run stored it
            raise _not_active()
        return live

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "gnani_key_configured": client.configured(),
            "dialogues": sorted(registry),
            "line_rates": [8000, 16000],
            "stt_models": ["prisma-v3.0", "prisma-v2.5"],
            "streaming": False,
            "limits": {
                "max_turn_bytes": MAX_TURN_BYTES,
                "max_turn_seconds": int(MAX_TURN_SECONDS),
                "max_turns": MAX_TURNS,
            },
        }

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
        log = live.log
        return {
            "session_id": log.session_id,
            "line_rate": log.line_rate,
            "stt_model": log.stt.model,
            "bot": _bot_json(log.session_id, log.events[0]),
        }

    @app.post("/api/sessions/{session_id}/turns")
    async def turn(session_id: str, request: Request) -> dict[str, Any]:
        live = live_session(session_id)
        source = request.query_params.get("source")
        if source not in SOURCES:
            raise ApiProblem(422, "request", "invalid_source", "source must be mic, file or none")
        eos_wait_ms: float | None = None
        if "eos_wait_ms" in request.query_params:
            try:
                eos_wait_ms = float(request.query_params["eos_wait_ms"])
            except ValueError:
                eos_wait_ms = math.nan
            if not 0 <= eos_wait_ms <= 600_000:
                raise ApiProblem(422, "request", "invalid_eos_wait_ms", "eos_wait_ms must be a number of ms")
        reply_to: int | None = None
        if "reply_to" in request.query_params:
            raw = request.query_params["reply_to"]
            if not (raw.isascii() and raw.isdigit() and len(raw) <= 3):
                raise ApiProblem(422, "request", "invalid_reply_to", "reply_to must be a prompt's seq")
            reply_to = int(raw)
        if live.uploading:
            raise ApiProblem(409, "session", "turn_in_progress", "this call is already sending a turn", True)
        live.uploading = True
        try:
            body: bytes | None = None
            if source != "none":
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
                return await anyio.to_thread.run_sync(
                    calls.turn, live, source, body, eos_wait_ms, received, reply_to
                )
        finally:
            live.uploading = False

    @app.get("/api/sessions/{session_id}/audio/{name}")
    async def audio(session_id: str, name: str) -> Response:
        live = calls.live.get(session_id)
        if live is None:
            data = await anyio.to_thread.run_sync(calls.audio, calls.log_of(session_id), name, None)
        else:
            async with live.lock:
                data = await anyio.to_thread.run_sync(calls.audio, live.log, name, live)
        return Response(data, media_type="audio/wav")

    @app.post("/api/sessions/{session_id}/end")
    async def end(session_id: str, request: Request) -> dict[str, Any]:
        await _json(request, EndSession)
        live = calls.live.get(session_id)
        if live is None:
            log = calls.log_of(session_id)
            if log.status != "ended":
                raise _not_active()
            return _summary(log)
        async with live.lock:
            return await anyio.to_thread.run_sync(calls.end, live)

    @app.get("/api/sessions/{session_id}")
    async def session(session_id: str) -> dict[str, Any]:
        live = calls.live.get(session_id)
        if live is None:
            return calls.log_of(session_id).model_dump(mode="json")
        async with live.lock:
            return live.log.model_dump(mode="json")

    @app.get("/api/sessions/{session_id}/recording.wav")
    async def recording(session_id: str) -> Response:
        live = calls.live.get(session_id)
        if live is None:
            data = await anyio.to_thread.run_sync(calls.recording, calls.log_of(session_id))
        else:
            async with live.lock:
                data = await anyio.to_thread.run_sync(calls.recording, live.log)
        return Response(data, media_type="audio/wav")

    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app
