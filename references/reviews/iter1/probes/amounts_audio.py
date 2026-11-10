"""Measure the phone-line transforms: format, passband, determinism, achieved SNR. Offline, read-only.

Reads clips and stored condition audio under .samajh/evalkit/amounts-v1/ (never writes there); anything
regenerated is held in memory. Needs ffmpeg.

  uv run python references/reviews/iter1/probes/amounts_audio.py
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

from samajh.audio import AddNoise, BandLimit, MuLaw, Pcm, Resample, Step, apply_step, read_wav, step_key, synth_noise, write_wav
from samajh.audio.steps import _derive_seed

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"
AUDIO = ROOT / ".samajh" / "evalkit" / "amounts-v1"
STEP = TypeAdapter(Step)


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def power(x) -> float:
    return sum(v * v for v in x) / len(x) if len(x) else 0.0


def db(ratio: float) -> float:
    return 10 * math.log10(ratio) if ratio > 0 else float("-inf")


def tone(hz: float, rate: int, amplitude: int = 8000, seconds: float = 2.0) -> Pcm:
    return Pcm(rate, array("h", (round(amplitude * math.sin(2 * math.pi * hz * i / rate)) for i in range(int(seconds * rate)))))


def gain_db(src: Pcm, out: Pcm) -> float:
    a = src.samples[len(src.samples) // 4 :]
    b = out.samples[len(out.samples) // 4 :]
    return db(power(b) / power(a))


def passband() -> None:
    print("== passband: gain in dB of a 2 s tone (last three quarters), amplitude 8000 ==")
    freqs = (50, 100, 200, 300, 400, 1000, 2000, 3000, 3400, 3600, 3800, 3950)
    rows = {
        "BandLimit alone on 16 kHz": lambda hz: gain_db(tone(hz, 16000), read_wav(apply_step(write_wav(tone(hz, 16000)), BandLimit()))),
        "BandLimit alone on 8 kHz": lambda hz: gain_db(tone(hz, 8000), read_wav(apply_step(write_wav(tone(hz, 8000)), BandLimit()))),
        "phone = MuLaw (16k -> 8k mu-law)": lambda hz: gain_db(tone(hz, 16000), read_wav(apply_step(write_wav(tone(hz, 16000)), MuLaw()))),
        "narrowband = Resample 8k, BandLimit, MuLaw": lambda hz: gain_db(
            tone(hz, 16000),
            read_wav(apply_step(apply_step(apply_step(write_wav(tone(hz, 16000)), Resample(rate=8000)), BandLimit()), MuLaw())),
        ),
    }
    print("  Hz".ljust(46) + "".join(f"{hz:>7}" for hz in freqs))
    for name, fn in rows.items():
        print("  " + name.ljust(44) + "".join(f"{fn(hz):7.1f}" for hz in freqs))
    # a tone above the 8 kHz Nyquist: does the phone step alias it into the band?
    for hz in (4500, 5000, 6000):
        out = read_wav(apply_step(write_wav(tone(hz, 16000)), MuLaw()))
        print(f"  phone step, {hz} Hz tone in (above the 4 kHz Nyquist): residual {gain_db(tone(hz, 16000), out):.1f} dB")
    out = read_wav(apply_step(write_wav(tone(1000, 16000)), MuLaw()))
    plain = read_wav(apply_step(write_wav(tone(1000, 16000)), Resample(rate=8000)))
    err = [a - b for a, b in zip(out.samples, plain.samples, strict=True)]
    print(f"  mu-law quantisation: signal-to-distortion {db(power(plain.samples) / power(err)):.1f} dB at amplitude 8000; "
          f"output rate {out.rate}, samples {len(out.samples)}")
    quiet = tone(1000, 16000, amplitude=200)
    out = read_wav(apply_step(write_wav(quiet), MuLaw()))
    plain = read_wav(apply_step(write_wav(quiet), Resample(rate=8000)))
    err = [a - b for a, b in zip(out.samples, plain.samples, strict=True)]
    print(f"  mu-law quantisation at amplitude 200: signal-to-distortion {db(power(plain.samples) / power(err)):.1f} dB")


def frames(samples, size: int) -> list[float]:
    return [power(samples[i : i + size]) for i in range(0, len(samples) - size + 1, size)]


def active_mask(clean: list[float], floor_db: float) -> list[bool]:
    ordered = sorted(clean)
    ref = ordered[int(0.95 * (len(ordered) - 1))]
    limit = ref * 10 ** (floor_db / 10)
    return [p >= limit and p > 0 for p in clean]


def masked_snr(speech, noise, size: int, mask: list[bool]) -> float:
    s = n = 0.0
    for i, keep in enumerate(mask):
        if keep:
            s += sum(v * v for v in speech[i * size : (i + 1) * size])
            n += sum(v * v for v in noise[i * size : (i + 1) * size])
    return db(s / n) if n else float("nan")


def noise_spectrum() -> None:
    print("\n== what the two noises are (4 s at 16 kHz, seed 5): share of energy by band ==")
    for kind in ("babble", "street"):
        noise = synth_noise(kind, 4.0, 16000, seed=5)
        total = power(noise.samples)

        def share(low: int, high: int) -> float:
            out = read_wav(apply_step(write_wav(noise), BandLimit(low_hz=low, high_hz=high)))
            return power(out.samples) / total

        size = 320
        levels = [math.sqrt(p) for p in frames(noise.samples, size)]
        print(
            f"  {kind}: below ~300 Hz {1 - share(300, 7900):.2f}; 300-3400 Hz {share(300, 3400):.2f}; above ~3400 Hz {1 - share(1, 3400):.2f}; "
            f"20 ms frame level max/min {max(levels) / min(levels):.1f}, peak sample {max(abs(v) for v in noise.samples)}"
        )


def main() -> None:
    passband()
    noise_spectrum()

    stt = jl(RUN / "stt.jsonl")
    seen = {}
    for r in stt:
        if r["steps"] and r["steps"][0]["kind"] == "noise":
            seen[(r["item_id"], r["condition"])] = r
    print(f"\n== achieved SNR on the {len(seen)} stored noisy clips ==")

    stats: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    identical = differ = clipped = saturated = 0
    silence = []
    peaks = []
    for (item_id, condition), r in sorted(seen.items()):
        clip_bytes = (AUDIO / "clips" / f"{r['clip_sha256']}.wav").read_bytes()
        step = STEP.validate_python(r["steps"][0])
        assert isinstance(step, AddNoise)
        key = step_key(sha(clip_bytes), step)
        stored_bytes = (AUDIO / "conditions" / key[:2] / f"{key}.wav").read_bytes()
        stored = read_wav(stored_bytes)
        speech = read_wav(clip_bytes)
        # regenerate the noise exactly as samajh.audio.steps._add_noise does
        seed = _derive_seed(step.seed, sha(clip_bytes))
        noise = synth_noise(step.noise, len(speech.samples) / speech.rate, speech.rate, seed)
        s_rms, n_rms = math.sqrt(power(speech.samples)), math.sqrt(power(noise.samples))
        gain = s_rms / (n_rms * 10 ** (step.snr_db / 20))
        mixed = [s + gain * n for s, n in zip(speech.samples, noise.samples, strict=True)]
        scale = min(1.0, 32767 / max(abs(x) for x in mixed))
        regen = array("h", (round(scale * x) for x in mixed))
        if regen == stored.samples:
            identical += 1
        else:
            differ += 1
        clipped += scale < 1.0
        saturated += sum(1 for v in stored.samples if abs(v) >= 32767)
        peaks.append(max(abs(v) for v in speech.samples))

        s16 = [scale * v for v in speech.samples]
        n16 = [o - v for o, v in zip(stored.samples, s16, strict=True)]  # what was actually added, rounding included
        size = 320  # 20 ms at 16 kHz
        clean_frames = frames(s16, size)
        bucket = stats[condition]
        bucket["whole clip, 16 kHz (the code's definition)"].append(db(power(s16) / power(n16)))
        for floor in (-40.0, -20.0):
            mask = active_mask(clean_frames, floor)
            bucket[f"speech-active frames (20 ms, >= p95 {floor:+.0f} dB), 16 kHz"].append(masked_snr(s16, n16, size, mask))
            if floor == -40.0:
                silence.append(1 - sum(mask) / len(mask))
        # in the channel the recogniser received: resample speech and noise separately (linear), 8 kHz
        s_pcm = Pcm(16000, array("h", (max(-32768, min(32767, round(v))) for v in s16)))
        n_pcm = Pcm(16000, array("h", (max(-32768, min(32767, round(v))) for v in n16)))
        s8 = read_wav(apply_step(write_wav(s_pcm), Resample(rate=8000)))
        n8 = read_wav(apply_step(write_wav(n_pcm), Resample(rate=8000)))
        bucket["whole clip after the 8 kHz resample (0-4 kHz)"].append(db(power(s8.samples) / power(n8.samples)))
        sb = read_wav(apply_step(write_wav(s8), BandLimit()))
        nb = read_wav(apply_step(write_wav(n8), BandLimit()))
        bucket["whole clip, 300-3400 Hz band at 8 kHz"].append(db(power(sb.samples) / power(nb.samples)))
        mask8 = active_mask(frames(sb.samples, 160), -20.0)
        bucket["speech-active frames (-20 dB), 300-3400 Hz band at 8 kHz"].append(masked_snr(sb.samples, nb.samples, 160, mask8))

    print(f"stored noisy clip == my regeneration from the clip and the seed: {identical} identical, {differ} differ")
    print(f"clips where the mix was scaled down to avoid clipping: {clipped}; samples at full scale in stored noisy clips: {saturated}")
    print(f"clean clip peak sample: min {min(peaks)} median {statistics.median(peaks)} max {max(peaks)}")
    print(f"share of 20 ms frames more than 40 dB below the loud frames (pauses): median {statistics.median(silence):.2f}, max {max(silence):.2f}")
    for condition in ("babble10", "babble5", "street10", "street5"):
        count = len(next(iter(stats[condition].values())))
        print(f"\n  {condition} (n={count}): dB  min / median / max")
        for name, values in stats[condition].items():
            values = [v for v in values if not math.isnan(v)]
            print(f"    {name:62s} {min(values):6.2f} / {statistics.median(values):6.2f} / {max(values):6.2f}")

    # determinism of every step on 5 real clips, and against the store
    print("\n== determinism: each step run twice on 5 cached clips, and against the stored file ==")
    voice = jl(RUN / "voice.jsonl")
    for v in voice[:: len(voice) // 5][:5]:
        clip = (AUDIO / "clips" / f"{v['audio_sha256']}.wav").read_bytes()
        line = [v["item_id"]]
        for name, chain in (
            ("phone", [MuLaw()]),
            ("narrowband", [Resample(rate=8000), BandLimit(), MuLaw()]),
            ("babble5", [AddNoise(noise="babble", snr_db=5), MuLaw()]),
            ("street10", [AddNoise(noise="street", snr_db=10), MuLaw()]),
        ):
            first = second = clip
            stored = clip
            in_store = True
            for step in chain:
                key = step_key(sha(stored), step)
                path = AUDIO / "conditions" / key[:2] / f"{key}.wav"
                in_store = in_store and path.exists()
                stored = path.read_bytes() if path.exists() else b""
                first, second = apply_step(first, step), apply_step(second, step)
            out = read_wav(first)
            line.append(
                f"{name}: twice-equal {first == second}, "
                + (f"== stored {first == stored}" if in_store else "not in store (other fold)")
                + f", {out.rate} Hz, {len(out.samples) / out.rate:.2f} s"
            )
        print("  " + " | ".join(line))


if __name__ == "__main__":
    main()
