"""Reviewer probe: what the shipped end-of-speech detector (web/vad.js, 700 ms) does to a caller
who pauses inside an answer, to a short noise burst, and to steady room noise. Offline: Node only.
Audio is built from the repo's TTS fixtures and from synthetic noise; nothing is a human voice.

    uv run python references/reviews/iter1/probes/server_vad_pauses.py <scratch dir>
"""
from __future__ import annotations

import json
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
RATE = 8000


def read(name: str) -> list[int]:
    with wave.open(str(REPO / "tests/fixtures/server/stub-call" / name)) as f:
        assert (f.getframerate(), f.getnchannels(), f.getsampwidth()) == (RATE, 1, 2)
        return list(struct.unpack(f"<{f.getnframes()}h", f.readframes(f.getnframes())))


def write(name: str, samples: list[int]) -> Path:
    path = OUT / name
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def vad(path: Path, *extra: str) -> dict:
    done = subprocess.run(["node", str(REPO / "tests/server/vad_check.mjs"), str(path), "--tail-ms", "2000", *extra], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


first, second = read("01-loan-amount.wav"), read("02-emi.wav")
a = vad(REPO / "tests/fixtures/server/stub-call/01-loan-amount.wav")["events"]
b = vad(REPO / "tests/fixtures/server/stub-call/02-emi.wav")["events"]
a_end, b_start = a[1]["lastVoicedMs"], b[0]["voicedFromMs"]
head = first[: a_end * RATE // 1000]  # up to the detector's last voiced frame
tail = second[b_start * RATE // 1000 :]  # from the detector's first voiced frame
print(f"A = 01-loan-amount.wav cut at its last voiced frame ({a_end} ms); B = 02-emi.wav from its first voiced frame ({b_start} ms)")
print("1. A, then a pause of digital silence, then B (one answer with a pause in the middle)")
for pause in (400, 500, 600, 640, 660, 680, 700, 720, 760, 800, 900, 1200):
    clip = write(f"pause-{pause}.wav", head + [0] * (pause * RATE // 1000) + tail)
    events = vad(clip)["events"]
    ends = [e for e in events if e["type"] == "speech_end"]
    total = len(head + tail) * 1000 / RATE + pause
    sent = ends[0]["lastVoicedMs"] + 200
    verdict = "one turn, whole answer" if len(ends) == 1 else f"CUT: the phone sends the first {sent:.0f} ms and stops listening; {total - ends[0]['atMs']:.0f} ms of the answer is never captured"
    print(f"   pause {pause:>4} ms: speech_end events {len(ends)}, first at {ends[0]['atMs']:.0f} ms of {total:.0f} ms -> {verdict}")

print("2. a short burst of noise in a quiet room (RMS 0.05, about -26 dBFS), nothing else")
rng = random.Random(7)
for burst in (60, 100, 120, 140, 200, 400):
    samples = [0] * RATE + [int(max(-1, min(1, rng.gauss(0, 0.05))) * 32767) for _ in range(burst * RATE // 1000)] + [0] * RATE
    events = vad(write(f"burst-{burst}.wav", samples))["events"]
    print(f"   {burst:>3} ms burst: events {[(e['type'], e['atMs']) for e in events]} -> {'a customer turn is sent to Prisma' if any(e['type'] == 'speech_end' for e in events) else 'ignored'}")

print("3. steady noise from the first sample for 20 s, no speech (what an open-plan room or a fan is to an energy detector)")
for rms in (0.006, 0.013, 0.02, 0.05):
    samples = [int(max(-1, min(1, rng.gauss(0, rms))) * 32767) for _ in range(20 * RATE)]
    for seed_label, extra in (("first turn (no carried noise floor)", ()), ("later turn (carried floor, capped at 0.02)", ("--initial-noise", str(min(rms, 0.02))))):
        out = vad(write(f"steady-{rms}.wav", samples), *extra)
        events = [(e["type"], round(e["atMs"])) for e in out["events"]]
        print(f"   noise RMS {rms}: {seed_label}: events {events[:4]}{' ...' if len(events) > 4 else ''}; still 'speaking' at the end: {out['state']['speaking']}")
