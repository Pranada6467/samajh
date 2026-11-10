"""Reviewer probe: WAVs the server passes through unchanged ("canonical") whose duration other
decoders read differently. Offline: samajh.server.audio + ffprobe only.

    uv run python references/reviews/iter1/probes/server_wav_disagreement.py <scratch dir>
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

from samajh.clients.gnani import wav_seconds
from samajh.server.audio import canonical_seconds, normalise_turn

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def riff(body: bytes) -> bytes:
    return b"RIFF" + struct.pack("<I", len(body)) + body


def fmt(rate: int, byte_rate: int | None = None) -> bytes:
    return b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2 if byte_rate is None else byte_rate, 2, 16)


def data(seconds: float, rate: int = 8000) -> bytes:
    pcm = b"\x10\x20" * round(seconds * rate)
    return b"data" + struct.pack("<I", len(pcm)) + pcm


cases = {
    "plain-20s": riff(b"WAVE" + fmt(8000) + data(20)),
    "two-fmt-4k-then-8k-20s": riff(b"WAVE" + fmt(4000) + fmt(8000) + data(20)),
    "two-fmt-2k-then-8k-30s": riff(b"WAVE" + fmt(2000) + fmt(8000) + data(30)),
    "byte-rate-1-1s": riff(b"WAVE" + fmt(8000, 1) + data(1)),
    "byte-rate-8000-30s": riff(b"WAVE" + fmt(8000, 8000) + data(30)),
}
for name, wav in cases.items():
    path = out / f"{name}.wav"
    path.write_bytes(wav)
    kept = normalise_turn(wav, 8000) == wav
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=sample_rate,duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=False,
    )
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "pipe:1"], capture_output=True, check=False
    )
    print(f"{name:<26} server canonical_seconds={canonical_seconds(wav, 8000)} client wav_seconds={wav_seconds(wav)} "
          f"passed through unchanged={kept} | ffprobe (rate,stream dur / format dur)={probe.stdout.split()} "
          f"ffmpeg decoded bytes={len(decoded.stdout)}")
