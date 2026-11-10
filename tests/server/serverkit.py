"""Test helpers: WAV builders and a fake Gnani client. Nothing here touches the network."""

from __future__ import annotations

import hashlib
import io
import math
import struct
import time
import wave
from collections.abc import Callable

from samajh.clients.gnani import CallInfo, PrismaV25, PrismaV30, Speech, Timbre, Transcript


def make_wav(seconds: float, rate: int = 8000, channels: int = 1, tone: float = 220.0) -> bytes:
    frames = round(seconds * rate)
    samples = (int(8000 * math.sin(2 * math.pi * tone * i / rate)) for i in range(frames))
    pcm = b"".join(struct.pack("<h", s) * channels for s in samples)
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return out.getvalue()


def wav_shape(data: bytes) -> tuple[int, int, int, int]:
    """(channels, sample width, rate, frames) as the stdlib reads them."""
    with wave.open(io.BytesIO(data)) as f:
        return f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()


class FakeSpeech:
    """Stands in for GnaniClient: canned transcripts in order, a tone for every prompt, and a
    cache keyed like the real one (same input, second call is a hit)."""

    def __init__(self, transcripts: list[str] | None = None) -> None:
        self.transcripts = list(transcripts or [])  # one per new clip, whichever model reads it
        self.model_transcripts: dict[str, list[str]] = {}  # a model that reads clips its own way
        self.stt_calls: list[tuple[bytes, PrismaV30 | PrismaV25]] = []
        self.tts_calls: list[tuple[str, Timbre]] = []
        self.stt_error: Exception | None = None  # every model
        self.model_errors: dict[str, Exception] = {}
        self.model_delays: dict[str, float] = {}  # seconds slept before a model answers
        self.tts_error: Exception | None = None
        self.tts_audio: Callable[[Timbre], bytes] = lambda o: make_wav(0.4, o.sample_rate)
        self._seen: dict[str, str] = {}

    def _info(self, key: str, hit: bool, credits: float) -> CallInfo:
        return CallInfo(
            cache_hit=hit,
            cache_key=key,
            seconds=0.0 if hit else 0.01,
            est_credits=0.0 if hit else credits,
            attempts=0 if hit else 1,
        )

    def stt(self, audio: bytes, options: PrismaV30 | PrismaV25, *, audio_format: str = "wav") -> Transcript:
        self.stt_calls.append((audio, options))
        time.sleep(self.model_delays.get(options.model, 0.0))
        error = self.stt_error or self.model_errors.get(options.model)
        if error is not None:
            raise error
        key = hashlib.sha256(audio + options.model_dump_json().encode()).hexdigest()
        hit = key in self._seen
        if not hit:
            own = self.model_transcripts.get(options.model)
            if own is not None:
                self._seen[key] = own.pop(0) if own else "हाँ"
            else:
                # Models with no list of their own agree on what a clip says.
                clip = hashlib.sha256(audio).hexdigest()
                if clip not in self._seen:
                    self._seen[clip] = self.transcripts.pop(0) if self.transcripts else "हाँ"
                self._seen[key] = self._seen[clip]
        v25 = options.model == "prisma-v2.5"
        return Transcript(
            text=self._seen[key],
            literal="शब्दों में" if v25 else None,
            model=options.model,
            detected_language=None if v25 else "hi-IN",
            request_id="req-fake",
            truncated=False,
            call=self._info(key, hit, 0.03),
        )

    def tts(self, text: str, options: Timbre) -> Speech:
        self.tts_calls.append((text, options))
        if self.tts_error is not None:
            raise self.tts_error
        key = hashlib.sha256((text + options.model_dump_json()).encode()).hexdigest()
        hit = key in self._seen
        self._seen[key] = text
        audio = self.tts_audio(options)
        return Speech(
            audio=audio,
            content_type="audio/wav",
            container="wav",
            sample_rate=options.sample_rate,
            audio_seconds=0.4,
            request_id="req-fake",
            call=self._info(key, hit, 0.002 * len(text)),
        )


def make_speech(parts: list[tuple[float, bool]], rate: int = 8000) -> bytes:
    """A clip of (seconds, voiced) stretches: a tone where voiced, digital silence elsewhere."""
    pcm = b""
    for seconds, voiced in parts:
        clip = make_wav(seconds, rate) if voiced else None
        pcm += clip[44:] if clip else bytes(2 * round(seconds * rate))
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return out.getvalue()
