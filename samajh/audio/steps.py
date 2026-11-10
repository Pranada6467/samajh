"""Phone-line degradations for the speech-to-text evaluation: resample, G.711 mu-law, band-limit, noise.

Every step is a pure function of (WAV bytes, step). `AudioStore` keeps each step's output on disk under
a key that does not include the ffmpeg version, so a stored clip survives an ffmpeg upgrade and the paid
speech-to-text call made on it is never repeated. Record `ffmpeg_version()` next to results instead.

The two noises are synthetic approximations built from ffmpeg noise generators. They are not recordings:
- "babble" is babble-like, not speech: six band-limited pink-noise streams, each amplitude-modulated at
  its own syllable-like rate. It has no real talkers, so no words, pitch, formants or pauses.
- "street" is street-like: low-frequency rumble with slow level swells plus a little broadband hiss.
  It has no horns, engines passing, voices or any other transient.
Results under these noises show how the recogniser copes with stationary-ish masking at a known SNR.
They do not show how it copes with a real crowd or a real road.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from array import array
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from samajh.audio.pcm import Pcm, pcm_from_s16le, read_wav, rms, s16le, write_wav

TRANSFORM_VERSION = 1  # bump when a step's output changes on purpose; it is part of every store key

NoiseKind = Literal["babble", "street"]


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Resample(_Step):
    kind: Literal["resample"] = "resample"
    rate: Literal[8000, 16000]


class MuLaw(_Step):
    """Resample to 8 kHz, G.711 mu-law encode, decode. The output is 8 kHz 16-bit PCM."""

    kind: Literal["mulaw"] = "mulaw"


class BandLimit(_Step):
    """A cheap GSM-like band-limit: 4th-order high-pass and low-pass, 6 dB down at each edge.

    This is not a GSM codec (this ffmpeg build has none): it removes the bands a narrowband phone
    channel removes and adds none of the codec's distortion. The sample rate is unchanged.
    """

    kind: Literal["bandlimit"] = "bandlimit"
    low_hz: int = 300
    high_hz: int = 3400


class AddNoise(_Step):
    """Add synthetic noise at `snr_db`.

    The SNR is the ratio of mean powers over the whole clip, silences included, at the input's sample
    rate and before any codec or band-limit. A later MuLaw or BandLimit step removes part of the noise
    (most of the street rumble lies below 300 Hz), so the SNR the recogniser meets can be higher.
    The noise seed is derived from `seed` and the input bytes: every clip gets its own realisation.
    """

    kind: Literal["noise"] = "noise"
    noise: NoiseKind
    snr_db: float
    seed: int = 0


Step = Annotated[Resample | MuLaw | BandLimit | AddNoise, Field(discriminator="kind")]

_BITEXACT = ["-bitexact", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1"]


def _ffmpeg(args: Sequence[str], stdin: bytes | None = None) -> bytes:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", *args]
    try:
        done = subprocess.run(cmd, input=stdin, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is not installed or not on PATH") from exc
    if done.returncode != 0:
        raise RuntimeError(
            f"ffmpeg exited with {done.returncode}: {done.stderr.decode(errors='replace').strip()}"
        )
    return done.stdout


def ffmpeg_version() -> str:
    """The installed ffmpeg's version string, e.g. "8.1.2". Not part of any store key."""
    try:
        done = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("ffmpeg is not installed or not on PATH") from exc
    return done.stdout.decode(errors="replace").split()[2]


def _filter(pcm: Pcm, out_rate: int, *output_args: str) -> bytes:
    """Run the samples through ffmpeg; the output is raw, mono, at `out_rate`."""
    source = ["-f", "s16le", "-ar", str(pcm.rate), "-ac", "1", "-i", "pipe:0"]
    return _ffmpeg(
        [*source, *output_args, "-ac", "1", "-ar", str(out_rate), *_BITEXACT, "pipe:1"], s16le(pcm)
    )


def _resample(pcm: Pcm, rate: int) -> Pcm:
    if pcm.rate == rate:
        return pcm
    return pcm_from_s16le(rate, _filter(pcm, rate, "-f", "s16le"))


def _mulaw(pcm: Pcm) -> Pcm:
    encoded = _filter(pcm, 8000, "-c:a", "pcm_mulaw", "-f", "mulaw")
    decode = ["-f", "mulaw", "-ar", "8000", "-ac", "1", "-i", "pipe:0", "-f", "s16le", *_BITEXACT, "pipe:1"]
    return pcm_from_s16le(8000, _ffmpeg(decode, encoded))


def _bandlimit(pcm: Pcm, low_hz: int, high_hz: int) -> Pcm:
    if not 0 < low_hz < high_hz < pcm.rate / 2:
        raise ValueError(f"band {low_hz} to {high_hz} Hz does not fit a {pcm.rate} Hz clip")
    # Each biquad is 2nd order; two in a row give the 24 dB/octave edges a phone channel has.
    graph = f"highpass=f={low_hz},highpass=f={low_hz},lowpass=f={high_hz},lowpass=f={high_hz}"
    return pcm_from_s16le(pcm.rate, _filter(pcm, pcm.rate, "-af", graph, "-f", "s16le"))


def _derive_seed(*parts: object) -> int:
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:4], "big") >> 1  # anoisesrc takes a non-negative 32-bit seed


_BABBLE_RATES_HZ = (3.1, 3.9, 4.6, 5.3, 6.1, 6.8)


def _noise_graph(kind: NoiseKind, seconds: float, rate: int, seed: int) -> str:
    def src(color: str, index: int, amplitude: float = 1.0) -> str:
        stream_seed = _derive_seed(kind, seed, index)
        return f"anoisesrc=c={color}:r={rate}:d={seconds:.4f}:a={amplitude}:seed={stream_seed}"

    top = min(3500, rate // 2 - 200)
    if kind == "babble":
        # Pink noise falls 3 dB per octave, which puts more of the energy low, as in speech.
        streams = [
            f"{src('pink', i)},highpass=f=200,lowpass=f={top},tremolo=f={hz}:d=0.9[s{i}]"
            for i, hz in enumerate(_BABBLE_RATES_HZ)
        ]
    else:
        streams = [
            f"{src('brown', 0)},highpass=f=60,lowpass=f=1500,tremolo=f=0.23:d=0.6[s0]",
            f"{src('pink', 1, 0.5)},highpass=f=60,lowpass=f=2000,tremolo=f=0.41:d=0.5[s1]",
            f"{src('white', 2, 0.01)}[s2]",
        ]
    inputs = "".join(f"[s{i}]" for i in range(len(streams)))
    return ";".join(streams) + f";{inputs}amix=inputs={len(streams)}:duration=longest[out]"


def synth_noise(kind: NoiseKind, seconds: float, rate: int, seed: int) -> Pcm:
    """`seconds` of synthetic noise (see the module docstring), deterministic for a given seed."""
    count = round(seconds * rate)
    # The source runs a little long and is cut to the exact sample count.
    graph = _noise_graph(kind, seconds + 0.1, rate, seed)
    raw = _ffmpeg(
        ["-filter_complex", graph, "-map", "[out]", "-ac", "1", "-f", "s16le", *_BITEXACT, "pipe:1"]
    )
    samples = pcm_from_s16le(rate, raw).samples[:count]
    if len(samples) != count:
        raise RuntimeError(f"ffmpeg produced {len(samples)} noise samples, expected {count}")
    return Pcm(rate, samples)


def mix_at_snr(speech: Pcm, noise: Pcm, snr_db: float) -> tuple[Pcm, float]:
    """speech + gain*noise at exactly `snr_db` over the whole clip.

    Returns the mix and the common factor (1.0 unless the sum would clip) by which speech and noise
    were both scaled; scaling both leaves the SNR unchanged.
    """
    if speech.rate != noise.rate or len(speech.samples) != len(noise.samples):
        raise ValueError("speech and noise must have the same sample rate and length")
    speech_rms, noise_rms = rms(speech.samples), rms(noise.samples)
    if speech_rms == 0 or noise_rms == 0:
        raise ValueError("cannot set an SNR on a silent clip")
    gain = speech_rms / (noise_rms * 10 ** (snr_db / 20))
    mixed = [s + gain * n for s, n in zip(speech.samples, noise.samples, strict=True)]
    scale = min(1.0, 32767 / max(abs(x) for x in mixed))
    return Pcm(speech.rate, array("h", (round(scale * x) for x in mixed))), scale


def _add_noise(wav: bytes, pcm: Pcm, step: AddNoise) -> Pcm:
    seed = _derive_seed(step.seed, hashlib.sha256(wav).hexdigest())
    noise = synth_noise(step.noise, len(pcm.samples) / pcm.rate, pcm.rate, seed)
    return mix_at_snr(pcm, noise, step.snr_db)[0]


def apply_step(wav: bytes, step: Step) -> bytes:
    """One degradation of a 16-bit mono WAV; the result is a canonical WAV of the same duration."""
    pcm = read_wav(wav)
    match step:
        case Resample():
            out = _resample(pcm, step.rate)
        case MuLaw():
            out = _mulaw(pcm)
        case BandLimit():
            out = _bandlimit(pcm, step.low_hz, step.high_hz)
        case AddNoise():
            out = _add_noise(wav, pcm, step)
    return write_wav(out)


def step_key(input_sha256: str, step: Step) -> str:
    payload = [TRANSFORM_VERSION, step.model_dump(mode="json"), input_sha256]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AudioStore:
    """Step outputs on disk at `root/<key[:2]>/<key>.wav`. A stored output is never recomputed."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def apply(self, wav: bytes, steps: Sequence[Step]) -> bytes:
        for step in steps:
            key = step_key(hashlib.sha256(wav).hexdigest(), step)
            path = self._root / key[:2] / f"{key}.wav"
            if path.exists():
                wav = path.read_bytes()
                continue
            wav = apply_step(wav, step)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(wav)
                os.replace(tmp, path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        return wav
