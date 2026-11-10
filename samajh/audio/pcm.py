"""Mono 16-bit PCM in memory, WAV in and out, and the two level measures the noise mix needs."""

from __future__ import annotations

import io
import math
import struct
import sys
import wave
from array import array
from collections.abc import Sequence
from dataclasses import dataclass

from samajh.clients.gnani.wav import fix_wav_header


@dataclass(frozen=True)
class Pcm:
    rate: int
    samples: array  # array('h'), mono


def pcm_from_s16le(rate: int, raw: bytes) -> Pcm:
    samples = array("h")
    samples.frombytes(raw[: len(raw) - (len(raw) & 1)])
    if sys.byteorder == "big":
        samples.byteswap()
    return Pcm(rate, samples)


def s16le(pcm: Pcm) -> bytes:
    if sys.byteorder == "big":
        swapped = array("h", pcm.samples)
        swapped.byteswap()
        return swapped.tobytes()
    return pcm.samples.tobytes()


def read_wav(data: bytes) -> Pcm:
    """Parse a 16-bit PCM mono WAV. A streaming header (sizes 0xFFFFFFFF) is repaired first."""
    try:
        with wave.open(io.BytesIO(fix_wav_header(data)), "rb") as w:
            channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            raw = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"not a PCM WAV: {exc}") from exc
    if channels != 1 or width != 2:
        raise ValueError(f"need 16-bit mono PCM, got {channels} channel(s) at {8 * width} bits")
    return pcm_from_s16le(rate, raw)


def write_wav(pcm: Pcm) -> bytes:
    """Canonical 44-byte header followed by the samples; the same Pcm always gives the same bytes."""
    body = s16le(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(body), b"WAVE", b"fmt ", 16, 1, 1, pcm.rate, pcm.rate * 2, 2, 16, b"data", len(body),
    )  # fmt: skip
    return header + body


def rms(samples: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in samples) / len(samples)) if len(samples) else 0.0


def snr_db(signal: Sequence[float], noise: Sequence[float]) -> float:
    """10*log10(mean power of signal / mean power of noise)."""
    return 20 * math.log10(rms(signal) / rms(noise))
