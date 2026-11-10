"""The LLM fallback is asked only about turns the rules cannot place, and can only relabel them."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from dialogue_kit import CUSTOMERS, play, record

from samajh.clients.errors import CapExceeded, LlmOutputInvalid, RateLimited, TransportError
from samajh.dialogue import UNCLEAR, Expecting, Intent, Outcome
from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi


class FakeLlm:
    """Stands in for `LlmClient`: answers every call with one label, or raises."""

    def __init__(self, label: str | None = None, error: Exception | None = None) -> None:
        self.label, self.error, self.calls, self.options = label, error, [], []

    def complete(self, schema, messages, **kwargs):
        self.calls.append(messages)
        self.options.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(value=schema(label=self.label))


def read(llm: FakeLlm, text: str, expecting: Expecting, question: str = "आपके हिसाब से वो चीज़ क्या है?"):
    return LlmFallbackInterpreter(llm).interpret(text, language=HI, expecting=expecting, question=question)


@pytest.mark.parametrize(
    "text, expecting",
    [
        ("हाँ जी, बोल रहा हूँ", Expecting.identity),
        ("मुझे बात नहीं करनी", Expecting.open),
        ("किसी इंसान से बात कराइए", Expecting.open),
        ("पता नहीं", Expecting.open),
        ("क्या?", Expecting.open),
        ("", Expecting.open),
        ("हम्म", Expecting.open),
        ("बावन हज़ार", Expecting.amount),
        ("हाँ बावन हज़ार", Expecting.confirmation),
        ("उन्नीस सौ चौरासी", Expecting.birth_year),
    ],
)
def test_the_llm_is_not_called_when_the_rules_settle_the_turn(text, expecting):
    llm = FakeLlm("decline")
    read(llm, text, expecting)
    assert llm.calls == []


def test_the_llm_sees_the_question_and_the_reply_and_nothing_else():
    llm = FakeLlm("answer")
    read(llm, "आज बहुत गर्मी है", Expecting.open)
    (messages,) = llm.calls
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[1].content == "Question: आपके हिसाब से वो चीज़ क्या है?\nReply: आज बहुत गर्मी है"


@pytest.mark.parametrize(
    "label, expecting, intent",
    [
        ("off_topic", Expecting.open, Intent.off_topic),
        # the LLM never ends a call: its stop labels become a question to the customer
        ("decline", Expecting.open, Intent.maybe_decline),
        ("wants_human", Expecting.told, Intent.maybe_human),
        ("decline", Expecting.identity, Intent.maybe_decline),
        ("no", Expecting.go_ahead, Intent.maybe_decline),
        ("yes", Expecting.stop_check, Intent.yes),
        ("wrong_person", Expecting.identity, Intent.said),
        ("no", Expecting.identity, Intent.said),
        ("dont_know", Expecting.amount, Intent.dont_know),
        ("asks_repeat", Expecting.open, Intent.asks_repeat),
        ("answer", Expecting.open, Intent.said),
        ("yes", Expecting.go_ahead, Intent.yes),
        ("no", Expecting.confirmation, Intent.no),
        # labels that make no sense for the question asked are dropped
        ("yes", Expecting.open, Intent.said),
        ("no", Expecting.amount, Intent.said),
        ("wrong_person", Expecting.open, Intent.said),
        ("off_topic", Expecting.identity, Intent.said),
        ("off_topic", Expecting.confirmation, Intent.said),
    ],
)
def test_label_becomes_intent_only_where_it_fits_the_question(label, expecting, intent):
    assert read(FakeLlm(label), "आज बहुत गर्मी है", expecting).intent is intent


def test_numbers_always_come_from_the_rules():
    heard = read(FakeLlm("off_topic"), "पाँच लाख का लोन था, उसमें से बावन हज़ार कटे", Expecting.open)
    assert heard.intent is Intent.off_topic and heard.amount_inr is None
    heard = read(FakeLlm("answer"), "वो तो बावन हज़ार ले गए", Expecting.open)
    assert heard.amount_inr == 52000


def test_the_fallback_names_its_own_model_and_leaves_room_for_the_reply():
    """The client's default model is chosen for extraction and can change; this call sits in a live turn."""
    llm = FakeLlm("answer")
    read(llm, "आज बहुत गर्मी है", Expecting.open)
    (options,) = llm.options
    assert options["model"] == FALLBACK_MODEL and "/" in FALLBACK_MODEL
    assert options["max_tokens"] >= 200  # 30 came back cut off and empty from a reasoning model


@pytest.mark.parametrize(
    "error, reason",
    [
        (CapExceeded(unit="USD", cap=1.0, spent=1.0, estimate=0.01), "would cross cap"),
        (TransportError("down"), "down"),
        (LlmOutputInvalid(model="m", attempts=1, last_error="finish_reason=length, empty content"),
         "finish_reason=length, empty content"),
        (RateLimited(status=429, code=None, message="slow down"), "slow down"),
    ],
)  # fmt: skip
def test_a_failed_llm_call_is_read_as_unclear_and_the_reason_is_logged(error, reason, caplog):
    llm = FakeLlm(error=error)
    with caplog.at_level("WARNING", logger="samajh.dialogue.llm_fallback"):
        heard = read(llm, "वो तो बावन हज़ार ले गए", Expecting.open)
    assert heard.intent is Intent.unclear and heard.amount_inr == 52000  # the rules' figure is kept
    assert Intent.unclear in UNCLEAR  # so every position asks once more
    assert len(llm.calls) == 1
    (logged,) = caplog.records
    assert type(error).__name__ in logged.getMessage() and reason in logged.getMessage()
    assert FALLBACK_MODEL in logged.getMessage()
    assert "बावन" not in logged.getMessage()  # the log names the failure, not what the customer said


def test_a_failed_llm_call_gets_the_question_asked_once_more_and_never_ends_the_call():
    customer = CUSTOMERS[HI]
    down = LlmFallbackInterpreter(FakeLlm(error=TransportError("down")))
    replies = [*customer.happy()[:3], "आज बहुत गर्मी है", "आज बहुत गर्मी है"]
    call = play(record(), HI, replies, interpreter=down)
    assert call.end is None
    assert call.keys[-5:] == (
        "open_recall.ask",
        "open_recall.reask",
        "bridge.moving_on",
        "teach_back.intro",
        "kind.ask",
    )
    assert [u.step.value for u in call.state.unresolved] == ["open_recall"]


def test_an_off_topic_label_gets_the_question_asked_once_more():
    customer = CUSTOMERS[HI]
    replies = [*customer.happy()[:3], "आज बहुत गर्मी है", "आज बहुत गर्मी है"]
    call = play(record(), HI, replies, interpreter=LlmFallbackInterpreter(FakeLlm("off_topic")))
    assert call.keys[-5:] == (
        "open_recall.ask",
        "open_recall.reask",
        "bridge.moving_on",
        "teach_back.intro",
        "kind.ask",
    )
    assert [u.step.value for u in call.state.unresolved] == ["open_recall"]


@pytest.mark.parametrize(
    "label, check, outcome",
    [
        ("decline", "stop_check.decline", Outcome.declined),
        ("wants_human", "stop_check.human", Outcome.human_requested),
    ],
)
def test_a_stop_label_from_the_llm_is_checked_with_the_customer_before_the_call_ends(label, check, outcome):
    customer = CUSTOMERS[HI]
    said = "देखिए अभी मैं दुकान पर हूँ, ग्राहक खड़े हैं"
    opening = customer.happy()[:3]

    stops = play(
        record(), HI, [*opening, said, customer.confirm], interpreter=LlmFallbackInterpreter(FakeLlm(label))
    )
    assert stops.keys[-2] == check and stops.end.outcome is outcome

    goes_on = play(
        record(), HI, [*opening, said, "नहीं नहीं"], interpreter=LlmFallbackInterpreter(FakeLlm(label))
    )
    assert goes_on.end is None
    assert goes_on.keys[-2:] == (check, "open_recall.reask")
