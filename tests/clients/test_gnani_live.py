"""One real Timbre call and one real Prisma call. Run with `-m live`; it spends credits."""

from __future__ import annotations

import io
import random
import re
import wave

import pytest

from samajh.clients.gnani import GnaniClient, PrismaV30, Timbre


@pytest.mark.live
def test_timbre_v30_into_prisma_v30_then_both_cached() -> None:
    gnani = GnaniClient.from_env()
    # The random number makes the text new on every run, so the first calls are never cache hits.
    text = f"नमस्ते, आपके लोन की किस्त {random.randint(100_000, 999_999)} रुपये है।"
    voice = Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN", sample_rate=8000)
    listen = PrismaV30(language="hi-IN", format="transcribe")

    speech = gnani.tts(text, voice)
    assert speech.call.cache_hit is False and speech.call.est_credits > 0
    assert speech.content_type == "audio/wav" and speech.audio_seconds is not None
    assert 1.5 < speech.audio_seconds < 15
    with wave.open(io.BytesIO(speech.audio), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 8000)
        assert w.getnframes() / 8000 == pytest.approx(speech.audio_seconds)

    heard = gnani.stt(speech.audio, listen)
    assert heard.call.cache_hit is False
    assert re.search(r"[ऀ-ॿ]", heard.text)
    assert heard.detected_language == "hi-IN" and heard.model == "prisma-v3.0"

    again = gnani.tts(text, voice)
    assert again.call.cache_hit is True and again.audio == speech.audio
    heard_again = gnani.stt(again.audio, listen)
    assert heard_again.call.cache_hit is True and heard_again.text == heard.text
