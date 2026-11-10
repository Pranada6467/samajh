from __future__ import annotations

import io
import struct
import wave

import pytest

from samajh.clients.gnani.wav import fix_wav_header, wav_sample_rate, wav_seconds


def pcm_wav(seconds: float, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x01\x00" * round(seconds * rate))
    return buf.getvalue()


def streaming(wav: bytes) -> bytes:
    """The header Timbre sends: RIFF and data sizes are 0xFFFFFFFF."""
    return wav[:4] + b"\xff" * 4 + wav[8:40] + b"\xff" * 4 + wav[44:]


def frames(data: bytes) -> int:
    with wave.open(io.BytesIO(data), "rb") as w:
        return w.getnframes()


def test_streaming_header_gives_real_duration_and_a_readable_file() -> None:
    broken = streaming(pcm_wav(2.4))
    assert wav_seconds(broken) == pytest.approx(2.4)
    fixed = fix_wav_header(broken)
    assert len(fixed) == len(broken)
    assert frames(fixed) == 19200
    assert struct.unpack_from("<I", fixed, 4)[0] == len(fixed) - 8


def test_normal_wav_is_unchanged() -> None:
    wav = pcm_wav(0.5, rate=16000)
    assert wav_seconds(wav) == pytest.approx(0.5)
    assert fix_wav_header(wav) is wav


@pytest.mark.parametrize(
    "data", [b"", b"ID3\x03 not a wav at all", b"RIFF\x00\x00\x00\x00AVI LIST", b"RIFF\xff\xff\xff\xffWAVE"]
)
def test_non_wav_is_none_and_unchanged(data: bytes) -> None:
    assert wav_seconds(data) is None
    assert fix_wav_header(data) is data


def test_non_pcm_wav_is_not_understood() -> None:
    wav = bytearray(pcm_wav(0.1))
    struct.pack_into("<H", wav, 20, 7)  # format tag: mu-law
    assert wav_seconds(bytes(wav)) is None
    assert fix_wav_header(bytes(wav)) == bytes(wav)


@pytest.mark.parametrize("extra", [b"LIST\x04\x00\x00\x00abcd", b"odd \x03\x00\x00\x00abc\x00"])
def test_extra_chunk_before_data(extra: bytes) -> None:
    wav = pcm_wav(1.0)
    shifted = streaming(wav)[:36] + extra + streaming(wav)[36:]
    assert wav_seconds(shifted) == pytest.approx(1.0)
    assert frames(fix_wav_header(shifted)) == 8000


def test_chunk_after_data_is_kept_out_of_the_duration() -> None:
    wav = pcm_wav(1.0)
    tailed = wav[:4] + struct.pack("<I", len(wav) + 4) + wav[8:] + b"LIST\x04\x00\x00\x00abcd"
    assert wav_seconds(tailed) == pytest.approx(1.0)
    assert fix_wav_header(tailed) is tailed


def test_sample_rate_comes_from_the_fmt_chunk() -> None:
    assert wav_sample_rate(pcm_wav(0.1, rate=16000)) == 16000
    assert wav_sample_rate(streaming(pcm_wav(0.1))) == 8000
    assert wav_sample_rate(b"ID3 not a wav") is None


def test_data_size_zero_with_samples_after_it_uses_the_real_length() -> None:
    wav = pcm_wav(31.0)
    lying = wav[:40] + b"\x00" * 4 + wav[44:]
    assert wav_seconds(lying) == pytest.approx(31.0)
    assert frames(fix_wav_header(lying)) == 31 * 8000


def test_header_only_wav_is_zero_seconds() -> None:
    assert wav_seconds(pcm_wav(0.0)) == 0.0
    assert wav_seconds(streaming(pcm_wav(0.0))) == 0.0
