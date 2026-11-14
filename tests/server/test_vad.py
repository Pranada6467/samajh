"""End-of-speech timing of web/vad.js, run under Node on synthetic WAVs (tone bursts over low noise)."""

from __future__ import annotations

import json
import math
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

SCRIPT = Path(__file__).with_name("vad_check.mjs")
NOISE = 0.004  # peak; RMS about 0.0023, under the detector's fixed floor
TONE = 0.3
MIN_SPEECH_MS = 120
HANGOVER_MS = 700
TOLERANCE_MS = 45  # two 20 ms frames plus slack


def write_wav(path: Path, plan: list[tuple[str, int]], rate: int = 8000) -> Path:
    """`plan` is a list of ("tone" | "quiet", milliseconds). Every sample carries seeded noise."""
    rng = random.Random(7)
    samples = []
    for kind, ms in plan:
        for _ in range(rate * ms // 1000):
            value = rng.uniform(-NOISE, NOISE)
            if kind == "tone":
                value += TONE * math.sin(2 * math.pi * 300 * len(samples) / rate)
            samples.append(int(value * 32767))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def run_vad(path: Path, *args: str) -> dict:
    done = subprocess.run(
        [NODE, str(SCRIPT), str(path), *args], check=False, capture_output=True, text=True, timeout=30
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def kinds(result: dict) -> list[str]:
    return [event["type"] for event in result["events"]]


@pytest.mark.parametrize("rate", [8000, 16000, 44100, 48000])
@pytest.mark.parametrize("chunk", ["128", "1000"])
def test_one_utterance_start_and_end_times(tmp_path: Path, rate: int, chunk: str) -> None:
    wav = write_wav(tmp_path / "one.wav", [("quiet", 500), ("tone", 1000), ("quiet", 300)], rate)
    result = run_vad(wav, "--chunk", chunk)
    assert result["sampleRate"] == rate
    assert result["durationMs"] == pytest.approx(1800, abs=1)
    assert kinds(result) == ["speech_start", "speech_end"]
    start, end = result["events"]
    assert start["voicedFromMs"] == pytest.approx(500, abs=TOLERANCE_MS)
    assert start["atMs"] == pytest.approx(500 + MIN_SPEECH_MS, abs=TOLERANCE_MS)
    assert end["lastVoicedMs"] == pytest.approx(1500, abs=TOLERANCE_MS)
    assert end["atMs"] == pytest.approx(1500 + HANGOVER_MS, abs=TOLERANCE_MS)


def test_a_400_ms_pause_does_not_end_the_utterance(tmp_path: Path) -> None:
    wav = write_wav(
        tmp_path / "short-pause.wav", [("quiet", 300), ("tone", 600), ("quiet", 400), ("tone", 600)]
    )
    result = run_vad(wav)
    assert kinds(result) == ["speech_start", "speech_end"]
    end = result["events"][1]
    assert end["lastVoicedMs"] == pytest.approx(1900, abs=TOLERANCE_MS)
    assert end["atMs"] == pytest.approx(1900 + HANGOVER_MS, abs=TOLERANCE_MS)


def test_a_1200_ms_pause_ends_the_utterance_inside_the_pause(tmp_path: Path) -> None:
    wav = write_wav(
        tmp_path / "long-pause.wav", [("quiet", 300), ("tone", 600), ("quiet", 1200), ("tone", 600)]
    )
    result = run_vad(wav)
    assert kinds(result) == ["speech_start", "speech_end", "speech_start", "speech_end"]
    first_end, second_start = result["events"][1], result["events"][2]
    assert first_end["lastVoicedMs"] == pytest.approx(900, abs=TOLERANCE_MS)
    assert first_end["atMs"] == pytest.approx(900 + HANGOVER_MS, abs=TOLERANCE_MS)
    assert first_end["atMs"] < 2100 < second_start["atMs"]


def test_a_shorter_hangover_ends_at_the_400_ms_pause(tmp_path: Path) -> None:
    wav = write_wav(
        tmp_path / "short-pause.wav", [("quiet", 300), ("tone", 600), ("quiet", 400), ("tone", 600)]
    )
    result = run_vad(wav, "--hangover-ms", "300")
    assert kinds(result) == ["speech_start", "speech_end", "speech_start", "speech_end"]
    assert result["events"][1]["atMs"] == pytest.approx(900 + 300, abs=TOLERANCE_MS)


def test_low_noise_alone_is_not_speech(tmp_path: Path) -> None:
    result = run_vad(write_wav(tmp_path / "noise.wav", [("quiet", 3000)]))
    assert result["events"] == []


def test_a_click_shorter_than_min_speech_is_not_speech(tmp_path: Path) -> None:
    wav = write_wav(tmp_path / "click.wav", [("quiet", 500), ("tone", 60), ("quiet", 1000)])
    assert run_vad(wav)["events"] == []


def test_without_a_tail_the_end_is_not_reported(tmp_path: Path) -> None:
    wav = write_wav(tmp_path / "cut.wav", [("quiet", 300), ("tone", 600)])
    assert kinds(run_vad(wav, "--tail-ms", "0")) == ["speech_start"]


def steady_noise(path: Path, peak: float, ms: int = 5000, rate: int = 8000) -> Path:
    rng = random.Random(11)
    samples = [int(rng.uniform(-peak, peak) * 32767) for _ in range(rate * ms // 1000)]
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def test_room_noise_learned_in_one_turn_is_not_taken_for_speech_in_the_next(tmp_path: Path) -> None:
    # Uniform noise with peak 0.035 has RMS 0.02: five times the detector's fixed floor.
    wav = steady_noise(tmp_path / "room.wav", peak=0.035)
    cold = run_vad(wav, "--tail-ms", "0")
    assert kinds(cold)[:1] == ["speech_start"]  # a detector that starts from the floor is fooled
    learned = cold["state"]["noiseRms"]
    assert kinds(run_vad(wav, "--tail-ms", "0", "--initial-noise", str(min(learned, 0.02)))) == []


def test_pauses_are_reported_only_when_asked(tmp_path: Path) -> None:
    wav = write_wav(
        tmp_path / "pauses.wav",
        [("quiet", 300), ("tone", 600), ("quiet", 400), ("tone", 600), ("quiet", 100), ("tone", 300)],
    )
    assert kinds(run_vad(wav)) == ["speech_start", "speech_end"]
    result = run_vad(wav, "--pause-ms", "150")
    assert kinds(result) == ["speech_start", "pause", "speech_end"]
    pause = result["events"][1]
    assert pause["fromMs"] == pytest.approx(900, abs=TOLERANCE_MS)
    assert pause["toMs"] == pytest.approx(1300, abs=TOLERANCE_MS)
