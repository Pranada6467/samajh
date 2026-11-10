"""The dialogue protocol, the stub, and the options derived from a bot utterance."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from samajh.clients.gnani import PrismaV25, PrismaV30
from samajh.server.dialogue import BotUtterance, CallView, Exchange, Heard, StubDialogue, stub_factory
from samajh.server.sessionlog import SttSettings, TtsSettings
from samajh.server.speech import LIVE, PATIENT, stt_options, stt_params, tts_options


def run_stub(answers: list[str]) -> list[BotUtterance]:
    dialogue = stub_factory({})
    said = [dialogue.next(CallView(session_id="s", params={}, exchanges=()), None)]
    exchanges: list[Exchange] = []
    for answer in answers:
        heard = Heard(text=answer)
        exchanges.append(Exchange(bot=said[-1], heard=heard))
        said.append(dialogue.next(CallView(session_id="s", params={}, exchanges=tuple(exchanges)), heard))
    return said


def test_stub_asks_three_questions_then_closes() -> None:
    said = run_stub(["पचास हज़ार", "", "बीमा"])
    assert [u.end_call for u in said] == [False, False, False, True]
    assert [u.tags["stub_step"] for u in said] == ["q1", "q2", "q3", "close"]
    assert said[0].text == StubDialogue.QUESTIONS[0]
    assert said[1].text == "मैंने सुना: पचास हज़ार " + StubDialogue.QUESTIONS[1]
    assert said[2].text.startswith(StubDialogue.NOTHING_HEARD)
    assert said[3].text.endswith(StubDialogue.CLOSING)
    assert {u.language for u in said} == {"hi-IN"}


def test_stub_keeps_a_long_answer_inside_the_utterance_limit() -> None:
    assert len(run_stub(["क" * 5000])[1].text) <= 600


def test_an_utterance_is_bounded_and_frozen() -> None:
    with pytest.raises(ValidationError):
        BotUtterance(text="", language="hi-IN")
    with pytest.raises(ValidationError):
        BotUtterance(text="x" * 601, language="hi-IN")
    with pytest.raises(ValidationError):
        BotUtterance(text="x", language="xx-XX")
    with pytest.raises(ValidationError):
        BotUtterance(text="x", language="hi-IN").text = "y"


@pytest.mark.parametrize(
    ("model", "bot_language", "expected"),
    [
        ("prisma-v3.0", "hi-IN", PrismaV30(language="hi-IN", format="transcribe")),
        ("prisma-v2.5", "hi-IN", PrismaV25(language="hi-IN", format="transcribe")),
        ("prisma-v3.0", "hi-en", PrismaV30(language=("hi-IN", "en-IN"), format="transcribe")),
        ("prisma-v2.5", "hi-en", PrismaV25(language="hi-IN", format="transcribe")),
        ("prisma-v3.0", "ta-IN", PrismaV30(language="ta-IN", format="transcribe")),
        ("prisma-v2.5", "kn-IN", PrismaV25(language="kn-IN", format="transcribe")),
        ("prisma-v3.0", "auto", PrismaV30(language="indic-auto", format="transcribe")),
    ],
)
def test_stt_language_follows_the_bot(model: str, bot_language: str, expected: object) -> None:
    assert stt_options(SttSettings(model=model), bot_language) == expected


def test_v25_cannot_follow_an_auto_utterance() -> None:
    with pytest.raises(ValueError):
        stt_options(SttSettings(model="prisma-v2.5"), "auto")


def test_format_comes_from_the_settings_and_params_are_the_exact_option_set() -> None:
    options = stt_options(SttSettings(format="verbatim"), "hi-en")
    assert stt_params(options) == {"language_code": "hi-IN,en-IN", "format": "verbatim"}
    assert stt_params(stt_options(SttSettings(model="prisma-v2.5"), "hi-IN")) == {
        "language_code": "hi-IN",
        "format": "transcribe",
    }


def test_tts_options_use_the_line_rate_and_the_utterance_language() -> None:
    options = tts_options(TtsSettings(), "hi-IN", 16000)
    assert (options.model, options.voice, options.language) == ("timbre-v3.0", "Shivani", "hi-IN")
    assert (options.sample_rate, options.container) == (16000, "wav")


def test_client_profiles() -> None:
    assert (LIVE.retry.max_attempts, LIVE.retry.base_delay, LIVE.retry.max_delay) == (2, 0.3, 1.0)
    assert (LIVE.timeout, LIVE.lock_timeout) == (6.0, 5.0)
    assert (PATIENT.retry.max_attempts, PATIENT.retry.base_delay, PATIENT.retry.max_delay) == (4, 1.0, 8.0)
    assert (PATIENT.timeout, PATIENT.lock_timeout) == (20.0, 120.0)
