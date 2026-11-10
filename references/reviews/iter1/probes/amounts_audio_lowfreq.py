"""Why does the in-band SNR of some noisy clips fall far below nominal? Per-clip low-frequency share of
the clean Timbre clip, DC offset, and the scale applied to avoid clipping. Offline, read-only.

  uv run python references/reviews/iter1/probes/amounts_audio_lowfreq.py
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from array import array
from collections import defaultdict
from pathlib import Path

from pydantic import TypeAdapter

from samajh.audio import BandLimit, Resample, Step, apply_step, read_wav, synth_noise
from samajh.audio.steps import _derive_seed

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"
AUDIO = ROOT / ".samajh" / "evalkit" / "amounts-v1"
STEP = TypeAdapter(Step)


def jl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def power(x):
    return sum(v * v for v in x) / len(x)


voice = jl(RUN / "voice.jsonl")
by_voice = defaultdict(list)
low_share = {}
for v in voice:
    clip = (AUDIO / "clips" / f"{v['audio_sha256']}.wav").read_bytes()
    pcm = read_wav(clip)
    mean = sum(pcm.samples) / len(pcm.samples)
    s8 = read_wav(apply_step(clip, Resample(rate=8000)))
    band = read_wav(apply_step(apply_step(clip, Resample(rate=8000)), BandLimit()))
    hp = read_wav(apply_step(apply_step(clip, Resample(rate=8000)), BandLimit(low_hz=300, high_hz=3990)))
    share_in = power(band.samples) / power(s8.samples)
    share_low = 1 - power(hp.samples) / power(s8.samples)
    low_share[v["item_id"]] = share_low
    by_voice[f"{v['voice']['voice']} ({v['voice']['model'][7:]})"].append((share_low, share_in, mean, math.sqrt(power(pcm.samples)), max(abs(x) for x in pcm.samples)))

print("clean Timbre clips, by voice: share of energy below ~300 Hz (median, max) | share inside 300-3400 Hz (median) | DC mean (max abs) | RMS median | clips peaking at full scale")
for name, rows in sorted(by_voice.items(), key=lambda kv: -statistics.median(r[0] for r in kv[1])):
    print(
        f"  {name:20s} n={len(rows):2d}  low {statistics.median(r[0] for r in rows):.2f} / {max(r[0] for r in rows):.2f}"
        f" | in-band {statistics.median(r[1] for r in rows):.2f} | dc {max(abs(r[2]) for r in rows):6.1f}"
        f" | rms {statistics.median(r[3] for r in rows):7.0f} | at full scale {sum(r[4] >= 32767 for r in rows)}"
    )
allv = [r for rows in by_voice.values() for r in rows]
print(f"all 240 clips: low-frequency share median {statistics.median(r[0] for r in allv):.2f}, max {max(r[0] for r in allv):.2f}; "
      f"clips at full scale {sum(r[4] >= 32767 for r in allv)}; RMS min {min(r[3] for r in allv):.0f} max {max(r[3] for r in allv):.0f} "
      f"({20 * math.log10(max(r[3] for r in allv) / min(r[3] for r in allv)):.1f} dB range)")

# scale applied in the noisy mixes, and its relation to correctness is not examined here
stt = jl(RUN / "stt.jsonl")
seen = {}
for r in stt:
    if r["steps"] and r["steps"][0]["kind"] == "noise":
        seen[(r["item_id"], r["condition"])] = r
scales = defaultdict(list)
for (item_id, condition), r in sorted(seen.items()):
    clip = (AUDIO / "clips" / f"{r['clip_sha256']}.wav").read_bytes()
    step = STEP.validate_python(r["steps"][0])
    speech = read_wav(clip)
    noise = synth_noise(step.noise, len(speech.samples) / speech.rate, speech.rate, _derive_seed(step.seed, hashlib.sha256(clip).hexdigest()))
    gain = math.sqrt(power(speech.samples)) / (math.sqrt(power(noise.samples)) * 10 ** (step.snr_db / 20))
    peak = max(abs(s + gain * n) for s, n in zip(speech.samples, noise.samples, strict=True))
    scales[condition].append(min(1.0, 32767 / peak))
for condition, values in scales.items():
    down = [v for v in values if v < 1]
    print(f"{condition}: clips scaled down {len(down)}/{len(values)}; smallest scale {min(values):.3f} ({20 * math.log10(min(values)):.1f} dB); "
          f"median of the scaled ones {statistics.median(down) if down else 1:.3f}")
