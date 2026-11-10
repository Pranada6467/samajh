"""Rough median pitch of each of the 16 Timbre voices (autocorrelation on loud 40 ms frames of three clips
per voice, 8 kHz). Indirect evidence on the male/female mix, which the report takes from the docs. Offline.

  uv run python references/reviews/iter1/probes/amounts_voice_pitch.py
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from samajh.audio import Resample, apply_step, read_wav

ROOT = Path(__file__).resolve().parents[4]
AUDIO = ROOT / ".samajh" / "evalkit" / "amounts-v1"
voice = [json.loads(x) for x in (ROOT / "eval/amounts/run/voice.jsonl").read_text().splitlines()]
by = defaultdict(list)
for v in voice:
    by[(v["tts"]["language"], v["voice"]["voice"], v["voice"]["model"])].append(v)


def pitch(frame, rate):
    mean = sum(frame) / len(frame)
    x = [s - mean for s in frame]
    energy = sum(s * s for s in x)
    if energy == 0:
        return None
    best, best_lag = 0.0, None
    for lag in range(rate // 400, rate // 70):
        c = sum(x[i] * x[i + lag] for i in range(len(x) - lag)) / energy
        if c > best:
            best, best_lag = c, lag
    return rate / best_lag if best_lag and best > 0.5 else None


for (language, name, model), rows in sorted(by.items()):
    values = []
    for v in rows[:3]:
        pcm = read_wav(apply_step((AUDIO / "clips" / f"{v['audio_sha256']}.wav").read_bytes(), Resample(rate=8000)))
        size = 320
        frames = [pcm.samples[i : i + size] for i in range(0, len(pcm.samples) - size, size)]
        loud = sorted(frames, key=lambda f: -sum(s * s for s in f))[: len(frames) // 3]
        values += [p for p in (pitch(list(f), 8000) for f in loud) if p]
    print(f"{language:6s} {name:10s} {model}: median pitch {statistics.median(values):5.0f} Hz over {len(values)} voiced frames")
