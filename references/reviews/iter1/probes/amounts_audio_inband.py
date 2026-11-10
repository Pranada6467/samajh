"""(1) Cross-check the low-frequency share of the clean clips with an FFT (no ffmpeg filter involved).
(2) Per-clip in-band (300-3400 Hz) SNR of the babble5 clips against which sentences were lost.
Offline, read-only.

  uv run python references/reviews/iter1/probes/amounts_audio_inband.py
"""

from __future__ import annotations

import cmath
import hashlib
import json
import math
import statistics
from array import array
from collections import defaultdict
from pathlib import Path

from pydantic import TypeAdapter

from samajh.audio import BandLimit, Pcm, Resample, Step, apply_step, read_wav, step_key, write_wav

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"
AUDIO = ROOT / ".samajh" / "evalkit" / "amounts-v1"
STEP = TypeAdapter(Step)


def jl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def power(x):
    return sum(v * v for v in x) / len(x)


def fft(a):
    n = len(a)
    if n == 1:
        return a
    even, odd = fft(a[0::2]), fft(a[1::2])
    out = [0j] * n
    for k in range(n // 2):
        t = cmath.exp(-2j * cmath.pi * k / n) * odd[k]
        out[k], out[k + n // 2] = even[k] + t, even[k] - t
    return out


def band_shares(pcm: Pcm, edges=(300, 3400)) -> tuple[float, float, float]:
    size = 1024
    acc = [0.0] * (size // 2)
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / size) for i in range(size)]
    for start in range(0, len(pcm.samples) - size, size // 2):
        spec = fft([complex(pcm.samples[start + i] * window[i]) for i in range(size)])
        for k in range(1, size // 2):
            acc[k] += abs(spec[k]) ** 2
    hz = pcm.rate / size
    total = sum(acc)
    low = sum(p for k, p in enumerate(acc) if k * hz < edges[0])
    mid = sum(p for k, p in enumerate(acc) if edges[0] <= k * hz <= edges[1])
    return low / total, mid / total, 1 - (low + mid) / total


voice = {v["item_id"]: v for v in jl(RUN / "voice.jsonl")}
print("FFT (Hann, 1024 points at 16 kHz) share of clean-clip energy: below 300 Hz | 300-3400 Hz | above 3400 Hz")
picked = {}
for v in voice.values():
    picked.setdefault(v["voice"]["voice"], v)
for name, v in sorted(picked.items()):
    pcm = read_wav((AUDIO / "clips" / f"{v['audio_sha256']}.wav").read_bytes())
    low, mid, high = band_shares(pcm)
    print(f"  {name:10s} {v['item_id']:20s} {low:.2f} | {mid:.2f} | {high:.2f}")

scores = jl(RUN / "scores.jsonl")
right = {(s["item_id"], s["condition"], s["stt"]["model"]): s["correct"] for s in scores
         if s["method"] == "parser" and s["output"] == "text" and s["stt"]["format"] == "transcribe" and s["stt"]["language"] == "item"}
stt = jl(RUN / "stt.jsonl")
for condition in ("babble5", "babble10"):
    rows = {r["item_id"]: r for r in stt if r["condition"] == condition}
    inband = {}
    for item_id, r in rows.items():
        clip = (AUDIO / "clips" / f"{r['clip_sha256']}.wav").read_bytes()
        key = step_key(hashlib.sha256(clip).hexdigest(), STEP.validate_python(r["steps"][0]))
        noisy = read_wav((AUDIO / "conditions" / key[:2] / f"{key}.wav").read_bytes())
        speech = read_wav(clip)
        scale = 1.0
        peak_noisy = max(abs(x) for x in noisy.samples)
        if peak_noisy >= 32767:  # the mix was scaled; recover the scale by least squares on speech
            scale = None
        if scale is None:
            # noisy = scale*(s + g*n); s and n are nearly uncorrelated, so project noisy on s
            scale = sum(a * b for a, b in zip(noisy.samples, speech.samples)) / sum(b * b for b in speech.samples)
        s = [scale * x for x in speech.samples]
        n = [a - b for a, b in zip(noisy.samples, s)]

        def band(x):
            pcm = Pcm(16000, array("h", (max(-32768, min(32767, round(v))) for v in x)))
            return read_wav(apply_step(apply_step(write_wav(pcm), Resample(rate=8000)), BandLimit()))

        inband[item_id] = 10 * math.log10(power(band(s).samples) / power(band(n).samples))
    print(f"\n{condition}: in-band (300-3400 Hz) SNR by voice, and parser result on v3.0 / v2.5 (phone right -> condition wrong = lost)")
    by_voice = defaultdict(list)
    for item_id, snr in inband.items():
        by_voice[voice[item_id]["voice"]["voice"]].append(item_id)
    for name, ids in sorted(by_voice.items(), key=lambda kv: statistics.median(inband[i] for i in kv[1])):
        lost30 = sum(right[i, "phone", "prisma-v3.0"] and not right[i, condition, "prisma-v3.0"] for i in ids)
        lost25 = sum(right[i, "phone", "prisma-v2.5"] and not right[i, condition, "prisma-v2.5"] for i in ids)
        print(f"  {name:10s} n={len(ids):2d} in-band SNR median {statistics.median(inband[i] for i in ids):5.1f} dB (min {min(inband[i] for i in ids):5.1f}) | lost v3.0 {lost30} | lost v2.5 {lost25}")
    ordered = sorted(inband, key=inband.get)
    half = len(ordered) // 2
    for label, ids in (("lower half of in-band SNR", ordered[:half]), ("upper half", ordered[half:])):
        lost30 = sum(right[i, "phone", "prisma-v3.0"] and not right[i, condition, "prisma-v3.0"] for i in ids)
        lost25 = sum(right[i, "phone", "prisma-v2.5"] and not right[i, condition, "prisma-v2.5"] for i in ids)
        print(f"  {label}: n={len(ids)}, in-band SNR {inband[ids[0]]:.1f} to {inband[ids[-1]]:.1f} dB, lost v3.0 {lost30}, lost v2.5 {lost25}")
