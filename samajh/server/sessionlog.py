"""The event log of one call, and where it lives on disk.

    <state>/sessions/<session_id>/session.json      the SessionLog below, rewritten atomically
    <state>/sessions/<session_id>/audio/bot-000.wav      one file per event that has audio,
    <state>/sessions/<session_id>/audio/customer-001.wav named <speaker>-<seq>.wav
    <state>/sessions/<session_id>/call.wav          the whole call, bot and customer in order

Every audio file is mono 16-bit PCM WAV at the session's line rate, so the call recording is a
plain concatenation with `RECORDING_GAP_SECONDS` of silence between events. Two clocks appear:
`at` is wall time since the session was created (when it happened in the live call), and
`rec_start`/`rec_end` are positions in `call.wav` (what a Prisma Batch segment time refers to).
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import secrets
import tempfile
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from samajh.clients.gnani import TtsLanguage

LOG_VERSION = 1
LineRate = Literal[8000, 16000]
SttModelName = Literal["prisma-v3.0", "prisma-v2.5"]
# Batch split two voices only when a pause separated them (api-probe-iter1.md section 1).
RECORDING_GAP_SECONDS = 0.5
SESSION_ID = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{12}$")  # 20261110T142233-9f2c4e1ab07d
AUDIO_NAME = re.compile(r"^(bot|customer)-\d{3}\.wav$")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TtsCall(_Model):
    model: str
    voice: str
    language: str
    sample_rate: int
    cache_hit: bool
    seconds: float  # wall time of the Timbre call; 0 on a cache hit
    attempts: int
    est_credits: float
    request_id: str | None = None


class SttCall(_Model):
    mode: Literal["rest", "stream"]
    model: str
    params: dict[str, str]  # every option sent with the audio (language_code, format, ...)
    cache_hit: bool
    seconds: float  # wall time of the Prisma call; 0 on a cache hit
    attempts: int
    est_credits: float
    request_id: str | None = None


class TurnLatency(_Model):
    """Milliseconds. `server_ms` runs from the last request byte read to the response being ready."""

    normalise_ms: float  # decode and resample to the line rate
    stt_ms: float
    dialogue_ms: float
    server_ms: float
    # Reported by the phone: from the last voiced frame to the moment the upload started
    # (the end-of-speech detector's wait plus encoding). None for file-driven turns.
    eos_wait_ms: float | None = None


class _Event(_Model):
    seq: int  # index in SessionLog.events
    at: float  # seconds since the session was created (wall clock)
    audio: str | None = None  # "audio/<name>.wav", relative to the session directory
    audio_seconds: float | None = None
    rec_start: float | None = None  # position in call.wav; None when the event has no audio
    rec_end: float | None = None


class BotEvent(_Event):
    type: Literal["bot"] = "bot"
    text: str
    language: TtsLanguage
    end_call: bool
    tags: dict[str, str] = Field(default_factory=dict)
    tts: TtsCall | None = None  # None until the audio has been synthesised (on first fetch)


class CustomerEvent(_Event):
    type: Literal["customer"] = "customer"
    source: Literal["mic", "file", "none"]  # "none": the customer said nothing; no audio, no STT
    transcript: str
    literal: str | None = None
    detected_language: str | None = None
    stt: SttCall | None = None
    latency: TurnLatency | None = None


class ErrorEvent(_Event):
    """A failed step. `audio` is the customer audio the failed turn carried, when there was one."""

    type: Literal["error"] = "error"
    stage: Literal["audio", "stt", "tts", "dialogue"]
    status: int  # the HTTP status the phone was given
    code: str
    message: str


Event = Annotated[BotEvent | CustomerEvent | ErrorEvent, Field(discriminator="type")]


class SttSettings(_Model):
    model: SttModelName = "prisma-v3.0"
    format: Literal["verbatim", "transcribe"] = "transcribe"


class TtsSettings(_Model):
    model: Literal["timbre-v3.0", "timbre-v2.5"] = "timbre-v3.0"
    voice: str = "Shivani"


class Recording(_Model):
    file: Literal["call.wav"] = "call.wav"
    sample_rate: int
    seconds: float
    gap_seconds: float
    sha256: str


class SessionLog(_Model):
    version: Literal[1] = LOG_VERSION
    session_id: str
    created_at: str  # UTC ISO 8601
    dialogue: str
    params: dict[str, str]
    line_rate: LineRate
    stt: SttSettings
    tts: TtsSettings
    status: Literal["active", "ended"] = "active"
    ended_reason: Literal["dialogue", "hangup"] | None = None
    events: list[Event] = Field(default_factory=list)
    recording: Recording | None = None  # set once the call has ended and call.wav is written


def new_session_id() -> str:
    """UTC timestamp plus 48 random bits; always matches SESSION_ID."""
    return f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{secrets.token_hex(6)}"


def lay_out(events: list[Event], gap_seconds: float = RECORDING_GAP_SECONDS) -> None:
    """Set `rec_start`/`rec_end` on every event that has audio, in seq order, in place.

    The first audio starts at 0; each next one starts `gap_seconds` after the previous ends.
    Error events never enter the recording (their audio is evidence of a failed attempt only).
    """
    cursor = 0.0
    for event in sorted(events, key=lambda e: e.seq):
        event.rec_start = event.rec_end = None
        if isinstance(event, ErrorEvent) or event.audio is None or event.audio_seconds is None:
            continue
        event.rec_start = round(cursor, 6)
        event.rec_end = round(cursor + event.audio_seconds, 6)
        cursor = event.rec_end + gap_seconds


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


class SessionStore:
    """Reads and writes sessions under `root` (`<state>/sessions`). Paths are built here only,
    from ids and names that match SESSION_ID and AUDIO_NAME; anything else raises ValueError."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _dir(self, session_id: str) -> Path:
        if not SESSION_ID.fullmatch(session_id):
            raise ValueError("malformed session id")
        return self.root / session_id

    def _audio(self, session_id: str, name: str) -> Path:
        if not AUDIO_NAME.fullmatch(name):
            raise ValueError("malformed audio name")
        return self._dir(session_id) / "audio" / name

    def save(self, log: SessionLog) -> None:
        """`lay_out` the events, then write session.json atomically (temp file + os.replace)."""
        lay_out(log.events)
        _write_atomic(self._dir(log.session_id) / "session.json", log.model_dump_json(indent=2).encode())

    def load(self, session_id: str) -> SessionLog | None:
        """The stored log, or None if the id is malformed, unknown or the file does not parse."""
        if not SESSION_ID.fullmatch(session_id):
            return None
        data = _read(self._dir(session_id) / "session.json")
        try:
            return None if data is None else SessionLog.model_validate_json(data)
        except ValueError:
            return None

    def write_audio(self, session_id: str, name: str, wav: bytes) -> str:
        """Store one event's audio atomically; returns the log reference "audio/<name>"."""
        _write_atomic(self._audio(session_id, name), wav)
        return f"audio/{name}"

    def read_audio(self, session_id: str, name: str) -> bytes | None:
        return _read(self._audio(session_id, name))

    def assemble_recording(self, log: SessionLog) -> Recording:
        """Write call.wav from the bot and customer events that have audio, in seq order, with
        the gaps `lay_out` assumed. Idempotent: the same log and audio give the same bytes."""
        gap = b"\0\0" * round(RECORDING_GAP_SECONDS * log.line_rate)
        parts: list[bytes] = []
        for event in sorted(log.events, key=lambda e: e.seq):
            if isinstance(event, ErrorEvent) or event.audio is None:
                continue
            data = self.read_audio(log.session_id, event.audio.removeprefix("audio/"))
            if data is None:
                raise ValueError(f"event {event.seq}: audio file is missing")
            with wave.open(io.BytesIO(data)) as clip:
                if (clip.getnchannels(), clip.getsampwidth(), clip.getframerate()) != (1, 2, log.line_rate):
                    raise ValueError(f"event {event.seq}: audio is not mono 16-bit at the line rate")
                parts.append(clip.readframes(clip.getnframes()))
        pcm = gap.join(parts)
        out = io.BytesIO()
        with wave.open(out, "wb") as call:
            call.setnchannels(1)
            call.setsampwidth(2)
            call.setframerate(log.line_rate)
            call.writeframes(pcm)
        _write_atomic(self._dir(log.session_id) / "call.wav", out.getvalue())
        return Recording(
            sample_rate=log.line_rate,
            seconds=len(pcm) / 2 / log.line_rate,
            gap_seconds=RECORDING_GAP_SECONDS,
            sha256=hashlib.sha256(out.getvalue()).hexdigest(),
        )

    def read_recording(self, session_id: str) -> bytes | None:
        return _read(self._dir(session_id) / "call.wav")
