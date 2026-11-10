"""Reviewer probe: cost of one normalise_turn() call on a WAV whose FIRST fmt chunk declares an
absurd rate and whose LAST fmt chunk passes the server's header check. Offline (ffmpeg only).

    uv run python references/reviews/iter1/probes/server_two_fmt_cost.py FIRST_RATE FIRST_CHANNELS DATA_BYTES [single]
"""
import resource
import struct
import sys
import time

from samajh.server.audio import AudioRejected, normalise_turn

rate, channels, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
single = len(sys.argv) > 4


def fmt(rate: int, channels: int = 1) -> bytes:
    block = channels * 2
    return b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate, (rate * block) & 0xFFFFFFFF, block, 16)


chunks = fmt(rate, channels) if single else fmt(rate, channels) + fmt(48000)
body = b"WAVE" + chunks + b"data" + struct.pack("<I", n) + (b"\x10\x20" * (n // 2 + 1))[:n]
wav = b"RIFF" + struct.pack("<I", len(body)) + body
started = time.monotonic()
try:
    outcome = f"accepted {len(normalise_turn(wav, 8000))} bytes"
except AudioRejected as exc:
    outcome = f"refused {exc.code}"
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
print(f"first fmt {rate} Hz x{channels}{' (only fmt)' if single else ', last fmt 48000 Hz x1'}, {n} data bytes, file {len(wav)} bytes: "
      f"{outcome}; wall {time.monotonic() - started:.2f} s, ffmpeg cpu {usage.ru_utime + usage.ru_stime:.2f} s, ffmpeg peak RSS {usage.ru_maxrss / 1048576:.0f} MiB")
