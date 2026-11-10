"""Behaviour of samajh.audio. Inputs are built here; nothing is read from disk and nothing calls a network."""

from __future__ import annotations

import hashlib
import math
import random
import struct
import subprocess
from array import array
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from samajh.audio import (
    AddNoise,
    AudioStore,
    BandLimit,
    MuLaw,
    Pcm,
    Resample,
    Step,
    apply_step,
    ffmpeg_version,
    mix_at_snr,
    read_wav,
    rms,
    snr_db,
    step_key,
    synth_noise,
    write_wav,
)

RATE = 16000


def tone(hz: float, amplitude: int = 8000, seconds: float = 2.0, rate: int = RATE) -> Pcm:
    count = int(seconds * rate)
    return Pcm(
        rate, array("h", (round(amplitude * math.sin(2 * math.pi * hz * i / rate)) for i in range(count)))
    )


def pseudo_speech(seed: int = 1, seconds: float = 2.0) -> bytes:
    """Three drifting tones under a 4 Hz envelope: loud and quiet stretches, like syllables."""
    rng = random.Random(seed)
    partials = [(rng.uniform(150, 3000), rng.uniform(0, 6.28)) for _ in range(3)]
    samples = array("h")
    for i in range(int(seconds * RATE)):
        t = i / RATE
        envelope = 0.55 + 0.45 * math.sin(2 * math.pi * 4 * t)
        samples.append(
            round(3000 * envelope * sum(math.sin(2 * math.pi * hz * t + ph) for hz, ph in partials))
        )
    return write_wav(Pcm(RATE, samples))


def seconds_of(pcm: Pcm) -> float:
    return len(pcm.samples) / pcm.rate


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- pcm


def test_wav_round_trip_has_a_canonical_header() -> None:
    pcm = tone(440)
    wav = write_wav(pcm)
    assert wav[:4] == b"RIFF" and wav[36:40] == b"data" and len(wav) == 44 + 2 * len(pcm.samples)
    assert read_wav(wav) == pcm
    assert write_wav(read_wav(wav)) == wav


def test_read_wav_accepts_a_streaming_header() -> None:
    wav = bytearray(write_wav(tone(440)))
    wav[4:8] = wav[40:44] = b"\xff\xff\xff\xff"
    assert read_wav(bytes(wav)) == tone(440)


@pytest.mark.parametrize(("channels", "bits"), [(2, 16), (1, 8)])
def test_read_wav_rejects_anything_but_16_bit_mono(channels: int, bits: int) -> None:
    block = channels * bits // 8
    body = bytes(block * 100)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(body), b"WAVE", b"fmt ", 16, 1, channels, RATE, RATE * block, block, bits, b"data", len(body),
    )  # fmt: skip
    with pytest.raises(ValueError, match="16-bit mono"):
        read_wav(header + body)


def test_read_wav_rejects_bytes_that_are_not_a_wav() -> None:
    with pytest.raises(ValueError):
        read_wav(b"not a wav file at all")


def test_snr_db_is_a_power_ratio() -> None:
    assert rms([3, -3, 3, -3]) == 3
    assert snr_db([10, -10], [1, -1]) == pytest.approx(20)


# ---------------------------------------------------------------- resample, mu-law, band-limit


def test_resample_halves_the_rate_and_keeps_the_duration() -> None:
    out = read_wav(apply_step(write_wav(tone(440)), Resample(rate=8000)))
    assert out.rate == 8000
    assert seconds_of(out) == pytest.approx(2.0, abs=0.010)


def test_resample_up_keeps_the_duration() -> None:
    out = read_wav(apply_step(write_wav(tone(440, rate=8000)), Resample(rate=16000)))
    assert out.rate == 16000
    assert seconds_of(out) == pytest.approx(2.0, abs=0.010)


def test_mulaw_is_the_same_signal_at_8_khz_with_quantisation_noise() -> None:
    wav = write_wav(tone(440, amplitude=20000))
    plain = read_wav(apply_step(wav, Resample(rate=8000)))
    mulaw = read_wav(apply_step(wav, MuLaw()))
    assert mulaw.rate == 8000
    assert seconds_of(mulaw) == pytest.approx(2.0, abs=0.010)
    assert mulaw.samples != plain.samples
    error = [m - p for m, p in zip(mulaw.samples, plain.samples, strict=True)]
    assert snr_db(plain.samples, error) > 25


@pytest.mark.parametrize(("hz", "low_db", "high_db"), [(100, -200, -6), (3900, -200, -6), (1000, -1, 0.1)])
def test_bandlimit_passes_the_phone_band_only(hz: int, low_db: float, high_db: float) -> None:
    source = tone(hz)
    out = read_wav(apply_step(write_wav(source), BandLimit()))
    assert out.rate == RATE and len(out.samples) == len(source.samples)
    # Skip the first half second: the filters ring when the tone starts.
    change_db = 20 * math.log10(rms(out.samples[RATE // 2 :]) / rms(source.samples[RATE // 2 :]))
    assert low_db < change_db < high_db


def test_bandlimit_rejects_a_band_above_nyquist() -> None:
    with pytest.raises(ValueError, match="does not fit"):
        apply_step(write_wav(tone(440, rate=8000)), BandLimit(low_hz=300, high_hz=4000))


def test_steps_parse_by_kind_and_forbid_unknown_fields() -> None:
    adapter: TypeAdapter[Step] = TypeAdapter(Step)
    assert adapter.validate_python({"kind": "noise", "noise": "street", "snr_db": 5}) == AddNoise(
        noise="street", snr_db=5.0
    )
    assert adapter.validate_python({"kind": "mulaw"}) == MuLaw()
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "resample", "rate": 44100})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "bandlimit", "codec": "gsm"})


# ---------------------------------------------------------------- noise


def test_anoisesrc_is_deterministic_for_a_fixed_seed() -> None:
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "anoisesrc=c=pink:r=16000:d=1:seed=42",
    ]
    cmd += ["-f", "s16le", "-bitexact", "pipe:1"]
    first = subprocess.run(cmd, capture_output=True, check=True).stdout
    second = subprocess.run(cmd, capture_output=True, check=True).stdout
    assert len(first) == 32000 and first == second


@pytest.mark.parametrize("kind", ["babble", "street"])
def test_synth_noise_has_the_asked_length_and_depends_only_on_its_arguments(kind: str) -> None:
    noise = synth_noise(kind, 1.5, RATE, seed=3)
    assert noise.rate == RATE and len(noise.samples) == 24000
    assert synth_noise(kind, 1.5, RATE, seed=3) == noise
    assert synth_noise(kind, 1.5, RATE, seed=4) != noise
    assert max(abs(x) for x in noise.samples) < 32767  # the generator itself does not clip


@pytest.mark.parametrize("kind", ["babble", "street"])
@pytest.mark.parametrize("target_db", [10.0, 5.0])
def test_noise_is_mixed_at_the_target_snr(kind: str, target_db: float) -> None:
    wav = pseudo_speech()
    speech = read_wav(wav)
    out = read_wav(apply_step(wav, AddNoise(noise=kind, snr_db=target_db)))
    assert out.rate == RATE and len(out.samples) == len(speech.samples)
    # Without clipping the common scale is 1, so what was added is out - speech.
    assert max(abs(x) for x in out.samples) < 32767
    added = [o - s for o, s in zip(out.samples, speech.samples, strict=True)]
    achieved = snr_db(speech.samples, added)
    print(f"achieved SNR {kind} target {target_db}: {achieved:.3f} dB")
    assert achieved == pytest.approx(target_db, abs=0.3)


def test_a_mix_that_would_clip_scales_speech_and_noise_together() -> None:
    speech = tone(440, amplitude=30000)
    noise = synth_noise("babble", 2.0, RATE, seed=1)
    out, scale = mix_at_snr(speech, noise, 5.0)
    assert scale < 1
    assert max(abs(x) for x in out.samples) <= 32767
    scaled = [scale * s for s in speech.samples]
    added = [o - s for o, s in zip(out.samples, scaled, strict=True)]
    assert snr_db(scaled, added) == pytest.approx(5.0, abs=0.3)


def test_noise_is_reproducible_and_differs_by_seed_and_by_input() -> None:
    wav, other = pseudo_speech(seed=1), pseudo_speech(seed=2)
    step = AddNoise(noise="babble", snr_db=10)

    def added(clip: bytes, noise_step: AddNoise) -> list[int]:
        mixed = read_wav(apply_step(clip, noise_step)).samples
        return [m - s for m, s in zip(mixed, read_wav(clip).samples, strict=True)]

    assert apply_step(wav, step) == apply_step(wav, step)

    def similarity(a: list[int], b: list[int]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True)) / (rms(a) * rms(b) * len(a))

    base = added(wav, step)
    assert similarity(base, base) == pytest.approx(1.0)
    assert abs(similarity(base, added(wav, AddNoise(noise="babble", snr_db=10, seed=1)))) < 0.2
    assert abs(similarity(base, added(other, step))) < 0.2


def test_silent_input_cannot_take_noise() -> None:
    silence = write_wav(Pcm(RATE, array("h", bytes(2 * RATE))))
    with pytest.raises(ValueError, match="silent"):
        apply_step(silence, AddNoise(noise="street", snr_db=10))


def test_street_noise_sits_lower_in_the_spectrum_than_babble() -> None:
    def share_below_500_hz(kind: str) -> float:
        noise = synth_noise(kind, 4.0, RATE, seed=5)
        above = read_wav(apply_step(write_wav(noise), BandLimit(low_hz=500, high_hz=7000)))
        return 1 - (rms(above.samples) / rms(noise.samples)) ** 2

    babble, street = share_below_500_hz("babble"), share_below_500_hz("street")
    print(f"energy share below 500 Hz: babble {babble:.2f}, street {street:.2f}")
    assert street > 0.7
    assert babble < 0.6


def test_babble_level_fluctuates_more_than_steady_noise_would() -> None:
    noise = synth_noise("babble", 4.0, RATE, seed=5)
    frame = RATE // 50  # 20 ms
    levels = [rms(noise.samples[i : i + frame]) for i in range(0, len(noise.samples) - frame, frame)]
    assert max(levels) / min(levels) > 2


# ---------------------------------------------------------------- failures and the store


def test_missing_ffmpeg_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
        apply_step(write_wav(tone(440)), MuLaw())


def test_ffmpeg_failure_carries_its_stderr() -> None:
    with pytest.raises(RuntimeError, match="ffmpeg exited with"):
        synth_noise("babble", 1.0, 0, seed=1)


def test_ffmpeg_version_is_reported() -> None:
    assert ffmpeg_version()[0].isdigit()


def test_step_key_changes_with_the_step_and_with_the_input() -> None:
    a, b = sha(b"a"), sha(b"b")
    keys = {
        step_key(a, AddNoise(noise="babble", snr_db=10)),
        step_key(a, AddNoise(noise="babble", snr_db=5)),
        step_key(a, AddNoise(noise="street", snr_db=10)),
        step_key(a, AddNoise(noise="babble", snr_db=10, seed=1)),
        step_key(a, BandLimit()),
        step_key(a, BandLimit(high_hz=3000)),
        step_key(a, MuLaw()),
        step_key(a, Resample(rate=8000)),
        step_key(b, MuLaw()),
    }
    assert len(keys) == 9
    assert step_key(a, AddNoise(noise="babble", snr_db=10)) == step_key(
        a, AddNoise(noise="babble", snr_db=10.0)
    )


def test_store_returns_a_stored_result_without_running_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wav = pseudo_speech()
    steps = [AddNoise(noise="street", snr_db=10), MuLaw()]
    store = AudioStore(tmp_path)
    first = store.apply(wav, steps)
    assert first == apply_step(apply_step(wav, steps[0]), steps[1])

    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    noisy_key = step_key(sha(wav), steps[0])
    final_key = step_key(sha(apply_step(wav, steps[0])), steps[1])
    assert files == sorted(f"{k[:2]}/{k}.wav" for k in (noisy_key, final_key))
    assert (tmp_path / final_key[:2] / f"{final_key}.wav").read_bytes() == first

    def no_ffmpeg(*args: object, **kwargs: object) -> None:
        raise AssertionError("ffmpeg was run for a stored result")

    monkeypatch.setattr(subprocess, "run", no_ffmpeg)
    assert AudioStore(tmp_path).apply(wav, steps) == first
    with pytest.raises(AssertionError):
        store.apply(wav, [MuLaw()])  # a chain that is not stored still has to run


def test_store_with_no_steps_returns_the_input(tmp_path: Path) -> None:
    wav = pseudo_speech()
    assert AudioStore(tmp_path).apply(wav, []) is wav
    assert list(tmp_path.iterdir()) == []
