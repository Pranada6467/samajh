"""RIFF/WAVE helpers. Timbre sends a streaming header (RIFF and data sizes 0xFFFFFFFF), which
Python's `wave` module misreads, so duration and the header fix are computed from the real bytes."""

from __future__ import annotations

import struct
from typing import NamedTuple


class _Layout(NamedTuple):
    sample_rate: int
    block_align: int
    size_offset: int  # where the data chunk's size field sits
    declared: int
    real: int  # data bytes actually present


def _scan(data: bytes) -> _Layout | None:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    fmt: tuple[int, int] | None = None
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        (size,) = struct.unpack_from("<I", data, pos + 4)
        body = pos + 8
        if chunk_id == b"data":
            if fmt is None:
                return None
            # A size that runs past the end of the file is a streaming placeholder, and a size of 0
            # with bytes after it is a header that was never filled in: use what is there.
            rest = len(data) - body
            return _Layout(*fmt, size_offset=pos + 4, declared=size, real=size if 0 < size <= rest else rest)
        if body + size > len(data):
            return None
        if chunk_id == b"fmt ":
            if size < 16:
                return None
            tag, _channels, rate, _byte_rate, block_align = struct.unpack_from("<HHIIH", data, body)
            if tag != 1 or rate == 0 or block_align == 0:
                return None
            fmt = (rate, block_align)
        pos = body + size + (size & 1)  # chunks are padded to an even length
    return None


def wav_seconds(data: bytes) -> float | None:
    """Duration of a PCM WAV from its fmt chunk and the bytes really present; None if not one."""
    layout = _scan(data)
    if layout is None:
        return None
    return (layout.real // layout.block_align) / layout.sample_rate


def wav_sample_rate(data: bytes) -> int | None:
    """Sample rate from the fmt chunk of a PCM WAV; None if not one."""
    layout = _scan(data)
    return None if layout is None else layout.sample_rate


def fix_wav_header(data: bytes) -> bytes:
    """Rewrite wrong RIFF and data sizes to the real lengths; anything else is returned unchanged."""
    layout = _scan(data)
    if layout is None:
        return data
    riff = struct.pack("<I", len(data) - 8)
    if layout.declared == layout.real and data[4:8] == riff:
        return data
    fixed = bytearray(data)
    fixed[4:8] = riff
    struct.pack_into("<I", fixed, layout.size_offset, layout.real)
    return bytes(fixed)
