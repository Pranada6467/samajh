"""The dialogue protocol, the stub, and the options derived from a bot utterance."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from samajh.clients.gnani import PrismaV25, PrismaV30
from samajh.server.dialogue import MAX_LINES, BotLine, BotUtterance, Heard, Step, StubDialogue, stub_factory
from samajh.server.sessionlog import SttSettings, TtsSettings
from samajh.server.speech import LIVE, PATIENT, second_profile, stt_options, stt_params, tts_options


def run_stub(answers: list[str]) -> list[BotUtterance]:
    first = stub_factory({}).start()
    said, state = [first.say], first.state
    for answer in answers:
        # A fresh dialogue each turn: everything it knows is in the state it handed back.
        step = stub_factory({}).step(state, Heard(text=answer))
        said.append(step.say)
        state = step.state
    return said


def test_stub_asks_three_questions_then_closes() -> None:
    said = run_stub(["पचास हज़ार", "", "बीमा"])
    assert [u.end_call for u in said] == [False, False, False, True]
    assert [u.tags["stub_step"] for u in said] == ["q1", "q2", "q3", "close"]
    assert said[0].text == StubDialogue.QUESTIONS[0]
    assert said[1].text == "मैंने सुना: पचास हज़ार " + StubDialogue.QUESTIONS[1]
    assert [line.key for line in said[1].lines] == [None, "stub.q2"]
    assert said[2].text.startswith(StubDialogue.NOTHING_HEARD)
    assert said[3].text.endswith(StubDialogue.CLOSING)
    assert {u.language for u in said} == {"hi-IN"}
    assert [u.second_reading for u in said] == [True, False, False, False]


def test_stub_refuses_a_turn_after_the_end_and_bounds_a_long_answer() -> None:
    dialogue = stub_factory({})
    state = dialogue.start().state
    for _ in range(3):
        step = dialogue.step(state, Heard(text="क" * 5000))
        state = step.state
    assert all(len(line.text) <= 600 for line in step.say.lines)
    with pytest.raises(ValueError):
        dialogue.step(state, Heard(text="x"))


def test_an_utterance_is_bounded_and_frozen() -> None:
    line = BotLine(text="x")
    with pytest.raises(ValidationError):
        BotLine(text="")
    with pytest.raises(ValidationError):
        BotLine(text="x" * 601)
    with pytest.raises(ValidationError):
        BotUtterance(lines=(), language="hi-IN")
    with pytest.raises(ValidationError):
        BotUtterance(lines=(line,) * (MAX_LINES + 1), language="hi-IN")
    with pytest.raises(ValidationError):
        BotUtterance(lines=(line,), language="xx-XX")
    with pytest.raises(ValidationError):
        BotUtterance(lines=(line,), language="hi-IN").end_call = True
    long = BotUtterance(lines=(BotLine(text="क" * 600), BotLine(text="ख" * 600)), language="hi-IN")
    assert len(long.text) == 1201
    assert Step(state="s", say=long).say.listen == "open"


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


def test_the_second_reading_uses_the_second_model_and_format() -> None:
    settings = SttSettings(format="verbatim")
    assert stt_options(settings, "hi-en", "second") == PrismaV25(language="hi-IN", format="transcribe")
    swapped = SttSettings(model="prisma-v2.5", second_model="prisma-v3.0", second_format="verbatim")
    assert stt_options(swapped, "hi-en", "second") == PrismaV30(
        language=("hi-IN", "en-IN"), format="verbatim"
    )
    with pytest.raises(ValueError):
        stt_options(settings, "auto", "second")


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


def test_the_second_reading_profile_gives_up_at_the_bound() -> None:
    profile = second_profile(2.5)
    assert profile.retry.max_attempts == 1
    assert (profile.timeout, profile.lock_timeout, profile.deadline) == (2.5, 2.5, 2.5)
