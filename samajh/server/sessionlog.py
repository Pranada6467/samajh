"""The event log of one call, and where it lives on disk.

    <state>/sessions/<session_id>/session.json      the SessionLog below, rewritten atomically
    <state>/sessions/<session_id>/audio/bot-000.wav      one file per event that has audio,
    <state>/sessions/<session_id>/audio/customer-001.wav named <speaker>-<seq>.wav
    <state>/sessions/<session_id>/call.wav          the whole call, bot and customer in order
    <state>/sessions/<session_id>/case.json         the after-call case file, once started

Every audio file is mono 16-bit PCM WAV at the session's line rate, so the call recording is a
plain concatenation with `RECORDING_GAP_SECONDS` of silence between events. Two clocks appear:
`at` is wall time since the session was created (when it happened in the live call), and
`rec_start`/`rec_end` are positions in `call.wav` (what a Prisma Batch segment time refers to).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import tempfile
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field

from samajh.clients.gnani import TtsLanguage
from samajh.evidence.case_seal import seal_case
from samajh.evidence.digest import file_sha256
from samajh.evidence.session import CHAIN_FILE, append_chain, event_digest, session_fields, session_seal
from samajh.server.dialogue import ListenKind

LOG_VERSION = 2
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
    # Wall ms in this server for this line: the Timbre call (or cache read) plus conversion to
    # line PCM. None in logs written before this field.
    synth_ms: float | None = None


class SttReading(_Model):
    """One speech model's transcript of a customer turn, with everything that was sent."""

    role: Literal["primary", "second"]
    mode: Literal["rest", "stream"] = "rest"
    model: str  # the model asked for
    params: dict[str, str]  # every option sent with the audio (language_code, format, ...)
    ok: bool = True
    # Why a second reading is missing: "timeout", or the code of the client error. A missing
    # reading has text "" and is handed to the dialogue as a disagreement, never as agreement.
    error: str | None = None
    text: str = ""
    literal: str | None = None
    detected_language: str | None = None
    cache_hit: bool = False
    seconds: float = 0.0  # wall time of the Prisma call, the wait for the key included
    attempts: int = 0
    est_credits: float = 0.0
    request_id: str | None = None
    cache_key: str | None = None  # joins the Gnani ledger (.samajh/ledger.jsonl)
    # 200 for a reading fetched now; None for a cache hit; for a failed second reading, the
    # upstream HTTP status when the error carries one, else None.
    http_status: int | None = None


class TurnLatency(_Model):
    """Milliseconds. `server_ms` runs from the last request byte read to the response being ready."""

    normalise_ms: float  # decode and resample to the line rate
    stt_ms: float  # the primary reading
    second_stt_ms: float = 0.0  # the second reading, or the time waited for it before giving up
    dialogue_ms: float
    server_ms: float
    # Reported by the phone: from the last voiced frame to the moment the upload started
    # (the end-of-speech detector's wait plus encoding). None for file-driven turns.
    eos_wait_ms: float | None = None


class PauseStats(_Model):
    """Measured by the server on the stored turn audio (`samajh.server.audio.pause_stats`), so a
    microphone turn, an uploaded file and a replayed call are measured the same way."""

    speech_ms: float  # first voiced frame to last voiced frame
    leading_ms: float
    trailing_ms: float
    pauses_ms: list[float]  # unvoiced gaps of at least 200 ms inside the speech, in order
    longest_pause_ms: float  # 0 when there is none


class PhoneTurn(_Model):
    """What the phone says about how it took the turn. Untrusted: logged, never acted on."""

    mode: Literal["vad", "ptt", "file"]
    cut_ms: float | None = None  # the silence after which it sent this take
    grace_ms: float | None = None  # how long after the last voiced frame the customer could resume


# Strict: a bool or a numeric string is refused; a JSON integer is still a valid float.
Millis = Annotated[float, Field(ge=0, le=600000, allow_inf_nan=False, strict=True)]
Position = dict[str, str | int | float | bool | None]


class _Strict(_Model):
    model_config = ConfigDict(extra="forbid", strict=True)


class ClassifierCall(_Model):
    """The dialogue's LLM turn classifier on one turn, as the dialogue reports it."""

    ran: bool  # the LLM classifier was asked on this turn
    label: str | None = None  # its label, None when it did not run or gave none
    # From begin to answer: an upper bound on the LLM's own time; with a prefetch it includes the
    # second-reading wait.
    latency_ms: float | None = None
    model: str | None = None
    degraded: bool = False  # it failed or ran out of time (as CustomerEvent.degraded)
    # Wall time inside the classifier's `interpret` calls in this step, summed: what it added to
    # the turn after the readings were in.
    wait_ms: float | None = None


class VadMark(_Strict):
    type: Literal["speech_start", "pause", "cut", "resume", "grace_expired", "send"]
    at_ms: Millis  # ms since listening opened for this turn
    ms: Millis | None = None  # "pause": the unvoiced gap's length; "cut": silence waited


class BrowserListen(_Strict):
    """How the phone took a customer turn. Posted by the browser: untrusted, logged, never acted on."""

    mode: Literal["vad", "ptt", "file"]
    cut_ms: Millis | None = None
    grace_ms: Millis | None = None
    marks: list[VadMark] = Field(default_factory=list, max_length=400)
    takes: int = Field(default=1, ge=0, le=1000)  # takes sent for this turn
    grace_used: bool = False  # the customer resumed inside the grace window at least once
    eos_wait_ms: Millis | None = None
    post_ms: Millis | None = None  # upload start to reply received
    echo_cancellation: bool | None = None  # MediaStreamTrack.getSettings().echoCancellation


class TalkOver(_Strict):
    start_ms: Millis  # ms after the bot audio started playing
    ms: Millis  # length of the voiced run heard on the mic


class BrowserPlayback(_Strict):
    """One bot utterance as the browser played it. Untrusted, logged, never acted on."""

    bot_start_ms: Millis | None = None  # end of the customer's speech to the first sample, browser clock
    output_latency_ms: Millis | None = None  # AudioContext.outputLatency * 1000
    played_ms: Millis | None = None
    completed: bool | None = None
    # Voiced runs on the mic while this audio played, echo cancellation on: residual bot echo can
    # still count, so this is "speech heard during bot audio", not proof the customer spoke.
    talk_over: list[TalkOver] = Field(default_factory=list, max_length=200)


class _Event(_Model):
    seq: int  # index in SessionLog.events
    at: float  # seconds since the session was created (wall clock)
    audio: str | None = None  # "audio/<name>.wav", relative to the session directory
    audio_seconds: float | None = None
    rec_start: float | None = None  # position in call.wav; None when the event is not in it
    rec_end: float | None = None
    # A longer take of the same customer turn replaced this event (a customer take and the bot's
    # reply to it are superseded together). It stays in the log and is in no recording, no
    # transcript and no dialogue state.
    superseded: bool = False


class BotLineLog(_Model):
    key: str | None = None
    text: str
    tags: dict[str, str] = Field(default_factory=dict)
    # Position of this line inside the event's audio; None until the audio has been made.
    start_s: float | None = None
    end_s: float | None = None
    tts: TtsCall | None = None


class BotEvent(_Event):
    type: Literal["bot"] = "bot"
    text: str  # the lines joined with a space
    lines: list[BotLineLog] = Field(default_factory=list)
    language: TtsLanguage
    end_call: bool
    listen: ListenKind = "open"
    second_reading: bool = False
    tags: dict[str, str] = Field(default_factory=dict)
    # Wall time to make this utterance's audio on its first fetch (every line's Timbre call or
    # cache read, plus the join). None until then.
    synth_ms: float | None = None
    browser: BrowserPlayback | None = None  # posted by the phone; never in turn_json


# What the bot did right after a customer turn, from its next line (`samajh_dialogue.followed_by`):
# read a figure back, asked for the figure again, or anything else.
FollowedBy = Literal["read_back", "asked_again", "other"]


class CustomerEvent(_Event):
    type: Literal["customer"] = "customer"
    source: Literal["mic", "file", "none"]  # "none": the customer said nothing; no audio, no STT
    reply_to: int | None = None  # seq of the bot event this answers
    part: int = 1  # 1 for the first take of the turn; a later, longer take has a higher number
    # What the dialogue acted on: the customer turn as it recorded it. On a turn read twice that
    # is the second reading (v2.5) when it has text, else the primary (samajh_dialogue.readings),
    # unless only the other reading held a figure. `acted_on` names the reading.
    transcript: str
    acted_on: Literal["primary", "second"] | None = None  # None: nothing was read
    literal: str | None = None  # of the reading acted on (v2.5 only has one)
    detected_language: str | None = None  # of the primary reading (v3.0 only has one)
    # In the order they were made: primary, then second. [] when nothing was said.
    readings: list[SttReading] = Field(default_factory=list)
    # A turn read twice in which either reading holds a rupee figure: whether the dialogue recorded
    # the two readings as the same amount (`SecondReading.agreed`). None: read once, no figure in
    # either reading, a dialogue that does not say, or a log written before this field.
    readings_agreed: bool | None = None
    followed_by: FollowedBy | None = None  # None only in logs written before this field
    # The dialogue's LLM turn classifier failed or ran out of time on this turn, so the word lists
    # read it (`samajh_dialogue.degraded_turns`). A session with such a turn can be voided.
    degraded: bool = False
    latency: TurnLatency | None = None
    pauses: PauseStats | None = None
    phone: PhoneTurn | None = None
    classifier: ClassifierCall | None = None  # None: the dialogue does not say
    # Scalar values of the dialogue state's `position` before and after this turn; never the state.
    state_before: Position | None = None
    state_after: Position | None = None
    browser: BrowserListen | None = None  # posted by the phone; never in turn_json


class ErrorEvent(_Event):
    """A failed step. `audio` is the customer audio the failed turn carried, when there was one."""

    type: Literal["error"] = "error"
    stage: Literal["audio", "stt", "tts", "dialogue"]
    status: int  # the HTTP status the phone was given
    code: str
    message: str


Event = Annotated[BotEvent | CustomerEvent | ErrorEvent, Field(discriminator="type")]


class SttSettings(_Model):
    """The primary reading of every turn, and the second reading of the turns that ask for one."""

    model: SttModelName = "prisma-v3.0"
    format: Literal["verbatim", "transcribe"] = "transcribe"
    second_model: SttModelName = "prisma-v2.5"
    second_format: Literal["verbatim", "transcribe"] = "transcribe"
    second_timeout_s: float = 2.5


class TtsSettings(_Model):
    model: Literal["timbre-v3.0", "timbre-v2.5"] = "timbre-v3.0"
    voice: str = "Shivani"


class Recording(_Model):
    file: Literal["call.wav"] = "call.wav"
    sample_rate: int
    seconds: float
    gap_seconds: float
    sha256: str


class ChainState(_Model):
    """The session's evidence chain as of this file (format: `samajh.evidence`)."""

    version: Literal[1] = 1
    entries: int
    head: str
    seal: str | None = None  # set once `recording` is


class SessionLog(_Model):
    version: Literal[2] = LOG_VERSION
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
    # The Dialogue's state after the last event, and before the last customer turn (so that a
    # longer take of that turn can replace it). Written in the same file as the events, so the
    # two never disagree. Not served by the HTTP API.
    dialogue_state: str | None = None
    dialogue_undo: str | None = None
    # Set when the after-call job first starts. From then on no take may replace another.
    closed: bool = False
    # As the dialogue's state says after the last event (`samajh_dialogue.speaker_confirmed`):
    # True once the year-of-birth check has passed, False before. None: the dialogue does not say.
    speaker_confirmed: bool | None = None
    # None in logs written before the evidence chain existed.
    chain: ChainState | None = None


def new_session_id() -> str:
    """UTC timestamp plus 48 random bits; always matches SESSION_ID."""
    return f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{secrets.token_hex(6)}"


def lay_out(events: list[Event], gap_seconds: float = RECORDING_GAP_SECONDS) -> None:
    """Set `rec_start`/`rec_end` on every event that has audio, in seq order, in place.

    The first audio starts at 0; each next one starts `gap_seconds` after the previous ends.
    Error events never enter the recording (their audio is evidence of a failed attempt only),
    and neither do superseded events.
    """
    cursor = 0.0
    for event in sorted(events, key=lambda e: e.seq):
        event.rec_start = event.rec_end = None
        if isinstance(event, ErrorEvent) or event.superseded:
            continue
        if event.audio is None or event.audio_seconds is None:
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


def _stored_chain(data: bytes) -> object:
    try:
        parsed = json.loads(data)
    except ValueError:
        return None
    return parsed.get("chain") if isinstance(parsed, dict) else None


class SessionStore:
    """Reads and writes sessions under `root` (`<state>/sessions`). Paths are built here only,
    from ids and names that match SESSION_ID and AUDIO_NAME; anything else raises ValueError."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._audio_hashes: dict[tuple[str, int, int], str] = {}

    def _dir(self, session_id: str) -> Path:
        if not SESSION_ID.fullmatch(session_id):
            raise ValueError("malformed session id")
        return self.root / session_id

    def _audio(self, session_id: str, name: str) -> Path:
        if not AUDIO_NAME.fullmatch(name):
            raise ValueError("malformed audio name")
        return self._dir(session_id) / "audio" / name

    def _audio_sha(self, session_dir: Path, ref: str | None) -> str | None:
        """sha256 of an event's audio file, cached by (path, size, mtime_ns); None when missing."""
        if ref is None:
            return None
        path = session_dir / ref
        try:
            st = path.stat()
        except OSError:
            return None
        key = (str(path), st.st_size, st.st_mtime_ns)
        if key not in self._audio_hashes:
            self._audio_hashes[key] = file_sha256(path)
        return self._audio_hashes[key]

    def save(self, log: SessionLog) -> None:
        """`lay_out` the events, append what changed to the session's evidence chain
        (`samajh.evidence.session`), set `log.chain` in place, then write session.json atomically
        (temp file + os.replace). A session first written before the chain existed is adopted on
        this save: its earlier history is not covered."""
        lay_out(log.events)
        session_dir = self._dir(log.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(str(session_dir / ".chain.lock")):
            adopted = False
            if not (session_dir / CHAIN_FILE).exists():
                # A stored log with no chain was written before the chain existed: adopt it. One that
                # has a chain lost its chain.jsonl: start afresh, not adopted, and verification of
                # the old chain head is lost with it.
                stored = _read(session_dir / "session.json")
                adopted = stored is not None and _stored_chain(stored) is None
            events = [(e.seq, event_digest(e), self._audio_sha(session_dir, e.audio)) for e in log.events]
            entries, head = append_chain(session_dir, session_fields(log), events, adopted=adopted)
            seal = session_seal(head, log.recording.sha256) if log.recording is not None else None
            log.chain = ChainState(entries=entries, head=head, seal=seal)
            _write_atomic(session_dir / "session.json", log.model_dump_json(indent=2).encode())

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
        """Write call.wav from the bot and customer events that have audio and are not
        superseded, in seq order, with the gaps `lay_out` assumed. Idempotent: the same log and
        audio give the same bytes."""
        gap = b"\0\0" * round(RECORDING_GAP_SECONDS * log.line_rate)
        parts: list[bytes] = []
        for event in sorted(log.events, key=lambda e: e.seq):
            if isinstance(event, ErrorEvent) or event.superseded or event.audio is None:
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

    def write_case(self, session_id: str, data: bytes) -> None:
        """The after-call case file (`samajh.server.casefile`), written atomically and, when it
        carries a `seal`, sealed over its final bytes (`samajh.evidence.case_seal.seal_case`)."""
        _write_atomic(self._dir(session_id) / "case.json", seal_case(data))

    def read_case(self, session_id: str) -> bytes | None:
        return _read(self._dir(session_id) / "case.json")
