"""The LLM fallback is asked only about turns the rules cannot place, and can only relabel them."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from dialogue_kit import CUSTOMERS, play, record

from samajh.clients.errors import CapExceeded, LlmOutputInvalid, RateLimited, TransportError
from samajh.dialogue import Expecting, Intent, Outcome
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi


class FakeLlm:
    """Stands in for `LlmClient`: answers every call with one label, or raises."""

    def __init__(self, label: str | None = None, error: Exception | None = None) -> None:
        self.label, self.error, self.calls = label, error, []

    def complete(self, schema, messages, **kwargs):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return SimpleNamespace(value=schema(label=self.label))


def read(llm: FakeLlm, text: str, expecting: Expecting, question: str = "आपकी समझ से वह चीज़ क्या है?"):
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
    assert messages[1].content == "Question: आपकी समझ से वह चीज़ क्या है?\nReply: आज बहुत गर्मी है"


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


@pytest.mark.parametrize(
    "error",
    [
        CapExceeded(unit="USD", cap=1.0, spent=1.0, estimate=0.01),
        TransportError("down"),
        LlmOutputInvalid(model="m", attempts=3, last_error="bad json"),
        RateLimited(status=429, code=None, message="slow down"),
    ],
)
def test_a_failed_llm_call_leaves_the_rule_reading(error):
    llm = FakeLlm(error=error)
    assert read(llm, "आज बहुत गर्मी है", Expecting.open).intent is Intent.said
    assert len(llm.calls) == 1


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
