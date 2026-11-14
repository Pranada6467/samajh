"""Iteration 4, W4 checkpoint 2: a language request is heard and acted on (a live switch, or the end line)."""

from __future__ import annotations

from types import SimpleNamespace

from dialogue_kit import LENDER, NO_CHECK, play, product, record

from samajh.dialogue import Outcome
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi
C059 = "हाँ, पर मेरी हिंदी ठीक नहीं। तमिल में बोल सकते हैं?"
C024 = "हाँ, बात कर सकते हैं। मेरी हिंदी कमज़ोर है, Telugu में बात कर सकते हैं?"
CLAIM = "हाँ जी, मैं ही रमेश हूँ"
NAMING = ("context.loan", "open_recall", "verify.after_loan", "read_back", "kind.", "teach_back")


class Stub:
    """A fake `LlmClient`: `labels` maps a stage word to (label, language); default answers sensibly."""

    def __init__(self, labels: dict[str, tuple[str, str]] | None = None) -> None:
        self.labels, self.calls = labels or {}, []

    def complete(self, schema, messages, **kwargs):
        content = messages[-1].content
        self.calls.append(content)
        stage = content.split("\n")[0]
        default = ("confirms_self", "none") if "first_name" in stage else ("yes", "none")
        if "question" in stage:
            default = ("answer", "none")
        label, language = next((v for k, v in self.labels.items() if k in stage), default)
        return SimpleNamespace(value=schema(label=label, language=language))


def call(replies, llm=None, *, language=HI, limits=None):
    extra = {} if llm is None else {"interpreter": LlmFallbackInterpreter(llm)}
    if limits is not None:
        extra["limits"] = limits
    return play(record(product()), language, replies, identity=NO_CHECK, **extra)


def test_c059_switches_to_tamil_live_with_a_yes_label_and_with_word_lists_alone():
    for llm in (Stub({"go_ahead": ("yes", "none")}), None):
        c = call([CLAIM, C059], llm)
        assert c.end is None, c.keys
        last = c.utterances[-1]
        assert last.language is Language.ta and last.lines[0].key == "language.switched"
        assert c.state.language is Language.ta and len(c.state.language_switches) == 1
        switch = c.state.language_switches[0]
        assert (switch.from_language, switch.to_language, switch.requested) == (HI, Language.ta, "tamil")


def test_a_telugu_request_ends_with_the_reworded_line():
    c = call([CLAIM, C024], Stub())
    assert c.end.outcome is Outcome.language_switch and c.end.utterance.lines[-1].key == "end.language"
    assert c.state.requested_language == "telugu" and c.state.language is HI
    assert "उस भाषा में नहीं हो सकती" in c.end.utterance.text


def test_a_classifier_language_request_the_word_lists_miss_switches_to_kannada():
    reply = "हाँ ठीक है, पर थोड़ा धीरे और आसान तरीके से"
    c = call([CLAIM, reply], Stub({"go_ahead": ("language_request", "kannada")}))
    assert c.end is None and c.state.language is Language.kn and c.utterances[-1].lines[0].key == "language.switched"


def test_a_third_switch_ends_the_call():
    c = call([CLAIM, "तमिल में बोलिए", "Kannada please", "Tamil please"])
    assert len(c.state.language_switches) == 2
    assert c.end is not None and c.end.outcome is Outcome.language_switch and c.end.language_switches


def test_a_switch_before_the_pass_re_asks_only_the_name_question():
    c = call(["तमिल में बोलिए"], Stub())
    assert c.end is None and c.state.language is Language.ta and not c.state.speaker_confirmed
    assert c.keys[-2:] == ("language.switched", "right_party.ask")
    assert LENDER not in " ".join(u.text for u in c.utterances)
    assert not any(key.startswith(NAMING) for key in c.keys)


def test_after_a_switch_the_call_goes_on_in_the_new_language_and_the_name_check_still_runs():
    c = call(["Tamil please", "ஆமாம், நான் தான் ரமேஷ்"], Stub({"first_name": ("confirms_self", "none")}))
    assert c.state.language is Language.ta and all(u.language is Language.ta for u in c.utterances[1:])


def test_an_own_language_mention_is_not_a_switch():
    for reply in ("हाँ, हिंदी ठीक है", "हिंदी"):
        c = call([CLAIM, reply], Stub())
        assert c.state.language_switches == () and c.state.language is HI
        assert c.end is None or c.end.outcome is not Outcome.language_switch


def test_a_classifier_request_for_the_own_language_puts_the_question_again():
    c = call([CLAIM, "थोड़ा साफ़ बोलिए"], Stub({"go_ahead": ("language_request", "hindi")}))
    assert c.end is None and c.state.language_switches == () and c.keys[-1] == "disclosure.reask"


def test_a_language_request_at_the_year_never_reaches_the_classifier():
    llm = Stub()
    c = play(record(product()), HI, [CLAIM, "हाँ", "तमिल में बोलिए"], interpreter=LlmFallbackInterpreter(llm))
    assert c.state.language is Language.ta and not any("birth_year" in m for m in llm.calls)
