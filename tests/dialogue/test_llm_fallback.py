"""The turn classifier: asked about every reading the word lists are not sure of; every label honoured;
asymmetric defaults when it fails (nobody confirmed at the opening, one "shall I go on?" later)."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from dialogue_kit import CUSTOMERS, play, record

from samajh.clients.errors import CapExceeded, LlmOutputInvalid, RateLimited, TransportError
from samajh.dialogue import Expecting, Intent, Outcome, step
from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi
Q = "क्या आप Ramesh जी हैं?"


class FakeLlm:
    """Stands in for `LlmClient`: answers every call with one label (a "yes" at the go-ahead), or raises."""

    def __init__(self, label: str | None = None, error: Exception | None = None) -> None:
        self.label, self.error, self.calls, self.options = label, error, [], []

    def complete(self, schema, messages, **kwargs):
        self.calls.append(messages)
        self.options.append(kwargs)
        if self.error:
            raise self.error
        content = messages[-1].content
        go_ahead = "Stage: go_ahead" in content and self.label not in ("yes", "no", "unclear")
        # W4: the setup claim of a whole call now reaches the classifier too; it is answered as a classifier would.
        setup = "Stage: first_name" in content and content.endswith(f"Reply: {CUSTOMERS[HI].identity}")
        return SimpleNamespace(value=schema(label="yes" if go_ahead else "confirms_self" if setup else self.label))


def read(llm, text: str, expecting: Expecting, question: str = "वो क्या है?"):
    return LlmFallbackInterpreter(llm).interpret(text, language=HI, expecting=expecting, question=question)


@pytest.mark.parametrize(
    "text, expecting",
    [
        ("मैं उनकी पत्नी बोल रही हूँ", Expecting.identity),  # a tight relation word: a veto (W4)
        ("1984", Expecting.birth_year),
        ("हमारे ये तो 1984 के हैं", Expecting.birth_year),  # W4: the year question never reaches a model
        ("मुझे बात नहीं करनी", Expecting.open),
        ("किसी इंसान से बात कराइए", Expecting.open),
        ("पता नहीं", Expecting.open),
        ("क्या?", Expecting.open),
        ("", Expecting.open),
        ("बावन हज़ार", Expecting.amount),
        ("हाँ बावन हज़ार", Expecting.confirmation),
    ],
)
def test_the_classifier_is_not_called_when_the_rules_settle_the_turn(text, expecting):
    llm = FakeLlm("refuse")
    read(llm, text, expecting)
    assert llm.calls == []


@pytest.mark.parametrize(
    "text, expecting",
    [
        ("हाँ जी, थोड़ा जल्दी", Expecting.go_ahead),  # round 3: a go-ahead reply with more than yes-words
        ("ji main Ramesh", Expecting.identity),  # a name: not tight
        ("हाँ साहब बोलिए", Expecting.identity),  # a title: not tight
        ("हाँ जी, बोल रहा हूँ", Expecting.identity),  # W4: a tight claim is judged by the context classifier too
        ("जी", Expecting.identity),  # W4: a tight acknowledgement too
        ("आज बहुत गर्मी है", Expecting.open),  # a free reply later in the call
    ],
)
def test_the_classifier_is_called_on_every_unsettled_reading(text, expecting):
    llm = FakeLlm("unclear")
    read(llm, text, expecting, question=Q)
    assert len(llm.calls) == 1


def test_the_classifier_sees_the_stage_the_question_and_the_reply():
    llm = FakeLlm("answer")
    read(llm, "आज बहुत गर्मी है", Expecting.open)
    (messages,) = llm.calls
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[1].content.endswith("Question: वो क्या है?\nReply: आज बहुत गर्मी है")
    assert messages[1].content.startswith("Stage: ")


@pytest.mark.parametrize(
    "label, expecting, intent",
    [
        ("confirms_self", Expecting.identity, Intent.yes),
        ("wrong_person", Expecting.identity, Intent.wrong_person),  # honoured, no longer ignored
        ("third_party_handoff", Expecting.identity, Intent.wrong_person),
        ("who_or_why", Expecting.identity, Intent.asks_who),
        ("refuse", Expecting.open, Intent.decline),
        ("stop", Expecting.amount, Intent.decline),
        ("human_request", Expecting.told, Intent.wants_human),
        ("call_back", Expecting.open, Intent.call_later),
        ("remove_number", Expecting.open, Intent.do_not_call),
        ("written_request", Expecting.either_or, Intent.written_request),
        ("third_party_handoff", Expecting.open, Intent.wrong_person),
        ("who_or_why", Expecting.open, Intent.asks_who),
        ("answer", Expecting.open, Intent.said),
        ("dont_know", Expecting.amount, Intent.dont_know),
        ("unclear", Expecting.open, Intent.unclear),
        ("yes", Expecting.go_ahead, Intent.asks_repeat),  # wave 2: no yes or go-on word in the reply
        ("no", Expecting.go_ahead, Intent.no),
        ("refuse", Expecting.stop_check, Intent.maybe_decline),
        # labels that make no sense for the question asked leave the rules' reading
        ("yes", Expecting.open, Intent.said),
        # Round 3: "yes" at the first-name question is an ordinary confirmation; "answer" leaves the
        # word lists' reading, which for "ji main Ramesh" is an ordinary confirmation too.
        ("yes", Expecting.identity, Intent.acknowledges),
        ("answer", Expecting.identity, Intent.acknowledges),
    ],
)
def test_every_label_becomes_its_intent(label, expecting, intent):
    text = {Expecting.identity: "ji main Ramesh", Expecting.stop_check: "देखते हैं"}.get(
        expecting, "आज बहुत गर्मी है"
    )
    assert read(FakeLlm(label), text, expecting, question=Q).intent is intent


def test_a_year_is_confirmed_only_when_the_classifier_reads_it_as_the_speakers_own():
    text = "हमारे ये तो 1984 के हैं"  # wave 5: a year the word lists leave loose
    # W4: no classifier is asked at the year; a loose year with no first-person word confirms nobody.
    for llm in (FakeLlm("answer"), FakeLlm(error=TransportError("down"))):
        heard = read(llm, text, Expecting.birth_year)
        assert heard.year is None and not heard.degraded and llm.calls == []


def test_the_fallback_names_its_own_model_and_leaves_room_for_the_reply():
    llm = FakeLlm("answer")
    read(llm, "आज बहुत गर्मी है", Expecting.open)
    (options,) = llm.options
    assert options["model"] == FALLBACK_MODEL and "/" in FALLBACK_MODEL
    assert options["max_tokens"] >= 200


@pytest.mark.parametrize(
    "error",
    [
        CapExceeded(unit="USD", cap=1.0, spent=1.0, estimate=0.01),
        TransportError("down"),
        LlmOutputInvalid(model="m", attempts=1, last_error="finish_reason=length, empty content"),
        RateLimited(status=429, code=None, message="slow down"),
        ValueError("anything else a client might raise"),
    ],
)
def test_a_failed_classifier_keeps_the_word_lists_reading_marked_degraded(error, caplog):
    with caplog.at_level("WARNING", logger="samajh.dialogue.llm_fallback"):
        heard = read(FakeLlm(error=error), "वो तो बावन हज़ार ले गए", Expecting.open)
    assert heard.intent is Intent.said and heard.degraded and heard.amount_inr == 52000
    (logged,) = caplog.records
    assert type(error).__name__ in logged.getMessage() and FALLBACK_MODEL in logged.getMessage()
    assert "बावन" not in logged.getMessage()  # the log names the failure, not what the customer said


class SlowLlm(FakeLlm):
    def complete(self, schema, messages, **kwargs):
        time.sleep(1.0)
        return super().complete(schema, messages, **kwargs)


def test_a_late_classifier_is_cut_off_at_the_timeout():
    began = time.monotonic()
    heard = LlmFallbackInterpreter(SlowLlm("refuse"), timeout_s=0.1).interpret(
        "आज बहुत गर्मी है", language=HI, expecting=Expecting.open, question="वो क्या है?"
    )
    assert time.monotonic() - began < 0.5
    assert heard.intent is Intent.said and heard.degraded


def test_a_failed_classifier_at_the_first_name_confirms_nobody():
    # Round 3: the word lists' ordinary confirmation stands (birth year next, lender not named); a reply
    # that is no confirmation at all still ends the call at the second try.
    down = LlmFallbackInterpreter(FakeLlm(error=TransportError("down")))
    call = play(record(), HI, ["ji main Ramesh"], interpreter=down)
    assert call.keys[-1] == "second_check.ask" and "disclosure.who" not in call.keys
    call = play(record(), HI, ["Ramesh?", "Ramesh?"], interpreter=down)
    assert call.end.outcome is Outcome.not_confirmed and "disclosure.who" not in call.keys


def test_a_failed_classifier_later_asks_once_whether_to_go_on_then_reads_by_the_word_lists():
    customer = CUSTOMERS[HI]
    down = LlmFallbackInterpreter(FakeLlm(error=TransportError("down")))
    call = play(record(), HI, [*customer.happy()[:3], "आज बहुत गर्मी है"], interpreter=down)
    assert call.keys[-1] == "stop_check.decline"
    call = play(record(), HI, [*customer.happy()[:3], "आज बहुत गर्मी है", "हाँ", "एक एफडी", "आज भी गर्मी है"],
                interpreter=down)  # fmt: skip
    assert call.keys.count("stop_check.decline") == 1 and call.keys[-1] == "premium.ask"
    assert len(call.state.degraded_turns) >= 2


class Explodes:
    def interpret(self, *args, **kwargs):
        raise RuntimeError("an interpreter bug")


def test_an_interpreter_exception_never_escapes_step():
    call = play(record(), HI, ["हाँ जी, बोल रहा हूँ"])
    state, said = step(call.state, "हाँ", interpreter=Explodes())
    assert said.lines[-1].key == "second_check.ask" and state.degraded_turns


@pytest.mark.parametrize(
    "label, outcome",
    [
        ("refuse", Outcome.declined),
        ("stop", Outcome.declined),
        ("human_request", Outcome.human_requested),
        ("remove_number", Outcome.do_not_call),
        ("written_request", Outcome.written_requested),
        ("third_party_handoff", Outcome.wrong_party),
    ],
)
def test_a_classifier_label_ends_the_call_with_its_own_outcome(label, outcome):
    customer = CUSTOMERS[HI]
    call = play(record(), HI, [*customer.happy()[:3], "देखिए ये सब तो बेटा ही संभालता है"],
                interpreter=LlmFallbackInterpreter(FakeLlm(label)))  # fmt: skip
    assert call.end is not None and call.end.outcome is outcome


def test_who_or_why_at_open_recall_is_answered_and_never_taken_as_the_answer():
    customer = CUSTOMERS[HI]
    fb = LlmFallbackInterpreter(FakeLlm("who_or_why"))
    call = play(record(), HI, [*customer.happy()[:3], "ये किस बारे में पूछ रहे हो?", "ये किस बारे में है?"],
                interpreter=fb)  # fmt: skip
    assert call.end is None and call.keys[-2:] == ("verify.after_loan", "open_recall.ask")
    assert call.keys.count("verify.after_loan") == 2


def test_a_confirms_self_label_without_a_first_person_word_confirms_nobody():
    assert (
        read(FakeLlm("confirms_self"), "haan batao kya baat hai", Expecting.identity, question=Q).intent
        is not Intent.yes
    )
    assert (
        read(FakeLlm("confirms_self"), "ji main Ramesh", Expecting.identity, question=Q).intent is Intent.yes
    )


def test_a_weak_stop_signal_stays_a_question_unless_the_classifier_reads_an_answer_or_an_end():
    text = "चलो रखता हूँ"
    assert read(FakeLlm("unclear"), text, Expecting.open).intent is Intent.maybe_decline
    assert read(FakeLlm("off_topic"), text, Expecting.open).intent is Intent.maybe_decline
    assert read(FakeLlm("stop"), text, Expecting.open).intent is Intent.decline
    assert read(FakeLlm("answer"), text, Expecting.open).intent is Intent.said


def test_a_go_on_word_against_an_end_label_asks_once_instead_of_ending():
    class AlwaysCallBack(FakeLlm):
        def complete(self, schema, messages, **kwargs):
            return SimpleNamespace(value=schema(label="call_back"))

    heard = LlmFallbackInterpreter(AlwaysCallBack()).interpret(
        "abhi thoda busy hoon par chalo pooch lo",
        language=Language.hi_en,
        expecting=Expecting.go_ahead,
        question=Q,
    )
    assert heard.intent is Intent.maybe_decline


@pytest.mark.parametrize(
    "label, text, language, expecting",
    [
        ("no", "nahi ji", Language.hi_en, Expecting.identity),  # G4-12
    ],
)
def test_a_label_the_question_does_not_act_on_confirms_nobody_and_is_not_a_failed_classifier(
    label, text, language, expecting
):
    # The classifier answered; only a failure, a timeout or `unclear` marks the turn degraded, because a
    # degraded turn voids the whole session in ops.
    llm = FakeLlm(label)
    heard = LlmFallbackInterpreter(llm).interpret(text, language=language, expecting=expecting, question=Q)
    assert len(llm.calls) == 1
    assert not heard.degraded and heard.year is None and heard.intent is not Intent.yes
    unsure = LlmFallbackInterpreter(FakeLlm("unclear"))
    assert unsure.interpret(text, language=language, expecting=expecting, question=Q).degraded


def test_dont_know_at_the_birth_year_takes_the_same_path_as_a_failed_classifier_without_voiding_the_call():
    replies = ["हाँ जी", "याद नहीं आ रहा अभी"]
    judged = play(record(), HI, replies, interpreter=LlmFallbackInterpreter(FakeLlm("dont_know")))
    down = play(record(), HI, replies, interpreter=LlmFallbackInterpreter(FakeLlm(error=TransportError("x"))))
    assert judged.keys == down.keys
    # W4: the year reply reaches no classifier, so neither arm marks it degraded.
    year_turn = [t for t in judged.state.turns if t.speaker.value == "customer"][-1].id
    assert year_turn not in judged.state.degraded_turns and year_turn not in down.state.degraded_turns
