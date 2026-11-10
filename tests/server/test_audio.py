"""`normalise_turn` against real ffmpeg."""

from __future__ import annotations

import struct

import pytest
from serverkit import make_wav, wav_shape

from samajh.clients.gnani import wav_seconds
from samajh.server import audio
from samajh.server.audio import AudioRejected, normalise_turn


def rejected(data: bytes, line_rate: int = 8000) -> str:
    with pytest.raises(AudioRejected) as caught:
        normalise_turn(data, line_rate)
    return caught.value.code


def streaming_header(wav: bytes) -> bytes:
    """The same audio with the 0xFFFFFFFF size fields Timbre and ffmpeg pipes write."""
    broken = bytearray(wav)
    broken[4:8] = broken[40:44] = b"\xff\xff\xff\xff"
    return bytes(broken)


@pytest.mark.parametrize("rate", [8000, 16000])
def test_a_canonical_clip_keeps_its_bytes(rate: int) -> None:
    clip = make_wav(1.0, rate)
    assert normalise_turn(clip, rate) == clip


def test_a_canonical_clip_with_a_streaming_header_only_gets_its_header_fixed() -> None:
    clip = make_wav(1.0)
    assert normalise_turn(streaming_header(clip), 8000) == clip


@pytest.mark.parametrize("line_rate", [8000, 16000])
def test_48k_stereo_becomes_line_rate_mono(line_rate: int) -> None:
    out = normalise_turn(make_wav(1.5, 48000, channels=2), line_rate)
    channels, width, rate, frames = wav_shape(out)
    assert (channels, width, rate) == (1, 2, line_rate)
    assert frames / rate == pytest.approx(1.5, abs=0.01)
    assert struct.unpack("<I", out[4:8])[0] == len(out) - 8  # header sizes are real
    assert max(abs(s) for (s,) in struct.iter_unpack("<h", out[44:])) > 1000  # the tone survived


def test_a_clip_at_the_other_line_rate_is_resampled() -> None:
    assert wav_shape(normalise_turn(make_wav(1.0, 16000), 8000))[2] == 8000


def test_conversion_is_deterministic() -> None:
    upload = make_wav(0.7, 44100, channels=2)
    assert normalise_turn(upload, 8000) == normalise_turn(upload, 8000)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello",
        b"\x00" * 4096,
        b"ID3\x03" + b"\x00" * 4096,  # another container: the demuxer is never guessed
        b"RIFF\x24\x00\x00\x00WAVE" + b"\x01" * 600,
        make_wav(1.0, 48000)[:40],
        b"RIFF\x00\x00\x00\x00AVI " + b"\x00" * 600,
    ],
)
def test_garbage_and_empty_uploads_are_unreadable(data: bytes) -> None:
    assert rejected(data) == "audio_unreadable"


def test_length_limits() -> None:
    assert rejected(make_wav(30.5)) == "audio_too_long"
    assert rejected(make_wav(30.5, 16000), 8000) == "audio_too_long"  # through ffmpeg
    assert rejected(make_wav(0.05)) == "audio_too_short"
    assert rejected(make_wav(0.05, 48000), 8000) == "audio_too_short"
    assert wav_seconds(normalise_turn(make_wav(30.0), 8000)) == 30.0  # the limit is inclusive
    assert wav_seconds(normalise_turn(make_wav(0.1), 8000)) == 0.1


def test_what_is_stored_is_what_was_decoded_not_what_was_uploaded() -> None:
    clip = bytearray(make_wav(31.0, 16000))
    clip[40:44] = struct.pack("<I", 16000)  # the data chunk claims half a second; the rest is junk
    assert wav_seconds(normalise_turn(bytes(clip), 8000)) == pytest.approx(0.5, abs=0.01)
    stored = normalise_turn(bytes(clip), 16000)  # at the line rate already, but not canonical
    assert wav_seconds(stored) == 0.5 and len(stored) == 44 + 16000


def test_a_missing_decoder_is_a_decoder_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    assert rejected(make_wav(1.0, 48000)) == "audio_decoder_failed"
    clip = make_wav(1.0)
    assert normalise_turn(clip, 8000) == clip  # the canonical path needs no decoder


def test_a_slow_decoder_is_a_decoder_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio, "FFMPEG_TIMEOUT", 0.0001)
    assert rejected(make_wav(20.0, 48000, channels=2)) == "audio_decoder_failed"


def with_fmt(wav: bytes, **fields: int) -> bytes:
    """`wav` (44-byte header) with fmt fields overwritten: tag, channels, rate, block_align, bits."""
    offsets = {"tag": (20, "<H"), "channels": (22, "<H"), "rate": (24, "<I"), "block_align": (32, "<H")}
    offsets["bits"] = (34, "<H")
    out = bytearray(wav)
    for name, value in fields.items():
        offset, layout = offsets[name]
        struct.pack_into(layout, out, offset, value)
    return bytes(out)


def test_a_header_that_understates_the_length_does_not_get_past_the_limit() -> None:
    # block_align is what the Gnani client divides by: 31 s of audio would read as a fraction
    # of a second, slip under the 30 s limit and be charged as almost nothing.
    lying = with_fmt(make_wav(31.0), block_align=60000)
    assert rejected(lying) == "audio_too_long"
    honest = normalise_turn(with_fmt(make_wav(2.0), block_align=60000), 8000)
    assert wav_seconds(honest) == pytest.approx(2.0, abs=0.01)


@pytest.mark.parametrize(
    "fields",
    [
        {"rate": 100_000_007},  # ffmpeg sizes its resampler from this
        {"rate": 1},
        {"channels": 0},
        {"channels": 200},
        {"tag": 85},  # MP3 inside a WAV
        {"tag": 2},  # ADPCM
    ],
)
def test_a_wav_ffmpeg_should_not_be_given_is_refused_before_it_runs(
    fields: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_ffmpeg(*args: object, **kwargs: object) -> None:
        raise AssertionError("ffmpeg was started")

    monkeypatch.setattr(audio.subprocess, "run", no_ffmpeg)
    assert rejected(with_fmt(make_wav(1.0, 44100), **fields)) == "audio_unreadable"
