"""Untrusted upload in, canonical turn audio out: mono 16-bit PCM WAV at the line rate."""

from __future__ import annotations

import struct
import subprocess
import threading
from collections.abc import Sequence
from typing import NamedTuple

import numpy as np

from samajh.clients.gnani import fix_wav_header
from samajh.server.sessionlog import PauseStats

MAX_TURN_SECONDS = 30.0  # Prisma REST limit, inclusive
MIN_TURN_SECONDS = 0.1
FFMPEG_TIMEOUT = 20.0
MIN_SOURCE_RATE, MAX_SOURCE_RATE = 4000, 192_000
MAX_SOURCE_CHANNELS = 8
# PCM, IEEE float, and WAVE_FORMAT_EXTENSIBLE (what some recorders write for plain PCM).
_SOURCE_TAGS = frozenset({1, 3, 0xFFFE})
_PCM_DECODERS = "pcm_u8,pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le"
# A resample is CPU and memory for a moment; a burst of uploads must queue, not fan out.
_ffmpeg_slots = threading.BoundedSemaphore(2)
FRAME_MS = 20
MIN_PAUSE_MS = 200
MIN_NOISE_FLOOR = 0.004  # of full scale


class AudioRejected(Exception):
    """`code` is one of audio_unreadable, audio_too_long, audio_too_short, audio_decoder_failed."""

    def __init__(self, code: str, message: str) -> None:
        self.code, self.message = code, message
        super().__init__(f"{code}: {message}")


class _Fmt(NamedTuple):
    tag: int
    channels: int
    rate: int
    block_align: int
    bits: int
    data_offset: int  # where the samples start
    data_bytes: int  # samples really present; a streaming or zero size field means "to the end"


def _fmt(data: bytes) -> _Fmt | None:
    """The fmt chunk and the data chunk's extent of a RIFF/WAVE file; None if it has neither."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    fmt: tuple[int, int, int, int, int] | None = None
    pos = 12
    while pos + 8 <= len(data):
        chunk, (size,) = data[pos : pos + 4], struct.unpack_from("<I", data, pos + 4)
        body = pos + 8
        if chunk == b"data":
            rest = len(data) - body
            return None if fmt is None else _Fmt(*fmt, body, size if 0 < size <= rest else rest)
        if body + size > len(data):
            return None
        if chunk == b"fmt ":
            if size < 16:
                return None
            tag, channels, rate, _byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", data, body)
            fmt = (tag, channels, rate, block_align, bits)
        pos = body + size + (size & 1)
    return None


def canonical_seconds(data: bytes, line_rate: int) -> float | None:
    """Duration if `data` is exactly what the session stores: PCM, mono, 16-bit, at `line_rate`,
    with nothing after the samples; None for anything else.

    Every header field that a duration could be computed from is pinned, so the length the
    credit guard and the 30 s limit see is the length Prisma gets.
    """
    fmt = _fmt(data)
    if fmt is None or (fmt.tag, fmt.channels, fmt.rate, fmt.block_align, fmt.bits) != (
        1,
        1,
        line_rate,
        2,
        16,
    ):
        return None
    if fmt.data_bytes % 2 or fmt.data_offset + fmt.data_bytes != len(data):
        return None
    return fmt.data_bytes / 2 / line_rate


def _resample(data: bytes, line_rate: int, cap_seconds: int) -> bytes:
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        # The demuxer and the protocol are fixed here, so the upload cannot choose either.
        "-protocol_whitelist", "pipe", "-f", "wav", "-codec_whitelist", _PCM_DECODERS, "-i", "pipe:0",
        "-t", str(cap_seconds), "-vn", "-ac", "1", "-ar", str(line_rate), "-c:a", "pcm_s16le",
        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-bitexact",
        "-f", "wav", "pipe:1",
    ]  # fmt: skip
    try:
        with _ffmpeg_slots:
            done = subprocess.run(
                command, input=data, capture_output=True, timeout=FFMPEG_TIMEOUT, check=False
            )
    except FileNotFoundError:
        raise AudioRejected("audio_decoder_failed", "ffmpeg is not installed") from None
    except subprocess.TimeoutExpired:
        raise AudioRejected("audio_decoder_failed", "ffmpeg timed out") from None
    if done.returncode < 0:
        raise AudioRejected("audio_decoder_failed", "ffmpeg crashed")
    if done.returncode != 0:
        raise AudioRejected("audio_unreadable", "the audio is not a decodable WAV file")
    # ffmpeg cannot seek back on a pipe, so the sizes in its header are placeholders.
    return fix_wav_header(done.stdout)


def to_line_pcm(data: bytes, line_rate: int, cap_seconds: int) -> tuple[bytes, float]:
    """(canonical WAV, its duration). A canonical input keeps its bytes (and so its STT cache
    key); anything else goes through ffmpeg, which stops writing at `cap_seconds`."""
    fmt = _fmt(data)
    if fmt is None:
        raise AudioRejected("audio_unreadable", "the audio is empty or not a WAV file")
    seconds = canonical_seconds(data, line_rate)
    if seconds is not None:
        return fix_wav_header(data), seconds
    # ffmpeg sizes its resampler from the header, so an absurd rate or layout is refused before
    # it runs (a 244-byte file declaring 100 MHz took 4 s and 800 MiB).
    if (
        fmt.tag not in _SOURCE_TAGS
        or not MIN_SOURCE_RATE <= fmt.rate <= MAX_SOURCE_RATE
        or not 1 <= fmt.channels <= MAX_SOURCE_CHANNELS
    ):
        raise AudioRejected("audio_unreadable", "the WAV must be PCM at 4 to 192 kHz with 1 to 8 channels")
    data = _resample(data, line_rate, cap_seconds)
    seconds = canonical_seconds(data, line_rate)
    if seconds is None:
        raise AudioRejected("audio_unreadable", "the audio is not a decodable WAV file")
    return data, seconds


def normalise_turn(data: bytes, line_rate: int) -> bytes:
    """An untrusted upload in, a canonical WAV of 0.1 to 30 s out; `AudioRejected` otherwise."""
    # One second over the limit is enough to tell that the turn is too long.
    wav, seconds = to_line_pcm(data, line_rate, cap_seconds=int(MAX_TURN_SECONDS) + 1)
    if seconds > MAX_TURN_SECONDS:
        raise AudioRejected("audio_too_long", f"a turn can be at most {MAX_TURN_SECONDS:g} s")
    if seconds < MIN_TURN_SECONDS:
        raise AudioRejected("audio_too_short", f"a turn must be at least {MIN_TURN_SECONDS:g} s")
    return wav


def _wav(pcm: bytes, rate: int) -> bytes:
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16,
        b"data", len(pcm),
    )  # fmt: skip
    return header + pcm


def join_clips(
    clips: Sequence[bytes], line_rate: int, gap_seconds: float
) -> tuple[bytes, list[tuple[float, float]]]:
    """Canonical clips joined in order with `gap_seconds` of silence between them: the joined
    canonical WAV, and each clip's (start, end) in it in seconds."""
    gap = bytes(2 * round(gap_seconds * line_rate))
    pcm = bytearray()
    spans: list[tuple[float, float]] = []
    for clip in clips:
        fmt = _fmt(clip)
        if fmt is None or canonical_seconds(clip, line_rate) is None:
            raise ValueError("a clip is not canonical audio at the line rate")
        if spans:
            pcm += gap
        start = len(pcm)
        pcm += clip[fmt.data_offset : fmt.data_offset + fmt.data_bytes]
        spans.append((start / 2 / line_rate, len(pcm) / 2 / line_rate))
    return _wav(bytes(pcm), line_rate), spans


def pause_stats(wav: bytes) -> PauseStats | None:
    """Where the speech and the pauses are in a mono 16-bit WAV, from frame energy alone.

    A 20 ms frame is voiced when its RMS is at least three times the clip's noise floor: the 10th
    percentile frame RMS, never lower than `MIN_NOISE_FLOOR`. The floor is also held to a tenth
    of the 95th percentile, so a clip with no silence in it (a tightly cut TTS file) is read as
    speech throughout and not as noise. None: not such a WAV, or no voiced frame.
    """
    fmt = _fmt(wav)
    if fmt is None or (fmt.tag, fmt.channels, fmt.bits) != (1, 1, 16):
        return None
    frame = fmt.rate * FRAME_MS // 1000
    count = fmt.data_bytes // 2 // frame if frame else 0
    if count == 0:
        return None
    samples = np.frombuffer(wav, dtype="<i2", count=count * frame, offset=fmt.data_offset)
    rms = np.sqrt(np.mean((samples.reshape(count, frame) / 32768.0) ** 2, axis=1))
    low, high = np.percentile(rms, [10, 95])
    floor = max(min(float(low), float(high) / 10), MIN_NOISE_FLOOR)
    voiced = np.flatnonzero(rms >= 3 * floor)
    if voiced.size == 0:
        return None
    first, last = int(voiced[0]), int(voiced[-1])
    gaps = (np.diff(voiced) - 1) * FRAME_MS
    pauses = [float(gap) for gap in gaps if gap >= MIN_PAUSE_MS]
    return PauseStats(
        speech_ms=float((last - first + 1) * FRAME_MS),
        leading_ms=float(first * FRAME_MS),
        trailing_ms=float((count - 1 - last) * FRAME_MS),
        pauses_ms=pauses,
        longest_pause_ms=max(pauses, default=0.0),
    )
