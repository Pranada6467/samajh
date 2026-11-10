"""P2 round 3: the ordinary confirmation, recall evidence, repeated figures, two readings, classifier use."""

from __future__ import annotations

import itertools
import threading
import time
from types import SimpleNamespace

import pytest
from dialogue_kit import CUSTOMERS, LENDER, play, product, record

from samajh.clients.errors import TransportError
from samajh.dialogue import CallState, Expecting, Outcome, prefetch, start, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.dialogue.machine import AtBirthYear, AtStopCheck
from samajh.types import Language, Speaker

HI, HE = Language.hi, Language.hi_en
STRONG = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984"]
LOAN_WORDS = ("लोन", "loan", "बीमा", "insurance", "पॉलिसी", "policy", "एफडी", "FD", "premium", "प्रीमियम")


class Labels:
    """A fake `LlmClient`: a label chosen from the reply text by `pick`, or an error; counts calls."""

    def __init__(self, pick=lambda reply, stage: "unclear", error: Exception | None = None, delay: float = 0):
        self.pick, self.error, self.delay, self.calls = pick, error, delay, []
        self._lock = threading.Lock()

    def complete(self, schema, messages, **kwargs):
        content = messages[-1].content
        with self._lock:
            self.calls.append(content)
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        stage = content.split("\n")[0]
        reply = content.rsplit("Reply: ", 1)[-1]
        return SimpleNamespace(value=schema(label=self.pick(reply, stage)))


def sensible(reply: str, stage: str) -> str:
    if "first_name" in stage:
        return "confirms_self" if any(w in reply for w in ("मैं", "main", "speaking")) else "yes"
    if "go_ahead" in stage:
        return "yes"
    if "birth_year" in stage:
        return "answer"
    return "answer"


ARMS = {
    "rules": None,
    "sensible": lambda: LlmFallbackInterpreter(Labels(sensible)),
    "raises": lambda: LlmFallbackInterpreter(Labels(error=TransportError("down"))),
}


def interp(arm):
    return {} if ARMS[arm] is None else {"interpreter": ARMS[arm]()}


def text_of(call) -> str:
    return " ".join(line.text for line in call.lines)


# --- Part A: ordinary confirmations ------------------------------------------------------------

ORDINARY = ["हाँ बोलिए", "जी बोलिए", "हाँ जी", "हाँ, रमेश जी से हो रही है", "haan main Ramesh", "yes",
            "haan ji boliye", "जी कहिए", "haan bolo", "yes tell me"]  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ORDINARY)
def test_an_ordinary_confirmation_reaches_the_birth_year_with_no_reask(arm, reply):
    call = play(record(), HI, [reply], **interp(arm))
    assert "right_party.reask" not in call.keys
    if arm == "sensible" and call.keys[-1] == "disclosure.go_ahead":  # the classifier heard "I": strong
        assert "main" in reply or "मैं" in reply
    else:
        assert call.keys[-1] == "second_check.ask", call.keys
        assert LENDER not in text_of(call)


@pytest.mark.parametrize("arm", ARMS)
def test_the_ordinary_path_order_of_lines(arm):
    call = play(record(product()), HI, ["हाँ जी", "1984", "हाँ"], **interp(arm))
    assert call.keys == (
        "right_party.ask",
        "purpose.before_confirm", "disclosure.never_ask", "second_check.ask",
        "disclosure.who", "disclosure.not_sales", "disclosure.recording", "disclosure.go_ahead",
        "context.loan", "disclosure.rights", "open_recall.ask",
    )  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
def test_a_plain_yes_at_the_reask_is_an_ordinary_confirmation_and_a_second_ambiguous_reply_ends(arm):
    call = play(record(), HI, ["नमस्ते", "जी हाँ"], **interp(arm))
    assert call.keys[-1] == "second_check.ask"
    assert call.keys.count("right_party.reask") == 1 and "purpose.before_confirm" not in call.keys
    call = play(record(), HI, ["नमस्ते", "हेलो"], **interp(arm))
    assert call.end.outcome is Outcome.not_confirmed


def test_the_strong_path_is_unchanged():
    call = play(record(product()), HI, STRONG)
    assert call.keys == (
        "right_party.ask",
        "disclosure.who", "disclosure.not_sales", "disclosure.recording", "disclosure.go_ahead",
        "disclosure.never_ask", "verify.short", "second_check.ask",
        "context.loan", "disclosure.rights", "open_recall.ask",
    )  # fmt: skip


def test_ordinary_path_failed_year_closes_without_the_lender():
    call = play(record(), HI, ["हाँ जी", "1990", "1991"])
    assert call.end.outcome is Outcome.second_check_failed and call.keys[-1] == "end.third_party"
    assert LENDER not in text_of(call)


def test_who_is_this_before_the_year_on_the_ordinary_path_does_not_name_the_lender():
    call = play(record(), HI, ["हाँ जी", "आप कौन बोल रहे हैं?"])
    assert call.keys[-2:] == ("purpose.before_confirm", "second_check.ask") and LENDER not in text_of(call)


THIRD_PARTY = ["हाँ जी, मैं उनकी पत्नी बोल रही हूँ", "हाँ, वो घर पर नहीं हैं", "रॉन्ग नंबर", "वो बाहर गए हैं",
               "साहब मीटिंग में हैं"]  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", THIRD_PARTY)
@pytest.mark.parametrize("before", [[], ["हाँ जी"], ["हाँ जी, बोल रहा हूँ"], ["हाँ जी, बोल रहा हूँ", "हाँ"]])
def test_a_third_party_at_any_opening_step_ends_with_nothing_learned(arm, reply, before):
    # At the first-name question a third party ends the call; at the go-ahead and the birth-year question
    # (either path) the round-2 rules apply: it ends, or the year is asked again and never passed.
    call = play(record(product()), HI, [*before, reply], **interp(arm))
    assert "context.loan" not in call.keys and call.keys.count("disclosure.go_ahead") <= 1
    if not before:
        assert call.end is not None and call.end.outcome is Outcome.wrong_party, call.keys
    if not before or before == ["हाँ जी"]:
        assert LENDER not in text_of(call)


OPENING_REPLIES = ["हाँ जी", "हाँ जी, बोल रहा हूँ", "हेलो", "आप कौन?", "kis baare mein hai?", "1984", "1990",
                   "बाद में कॉल करना", "रुकिए", "हाँ", "नहीं", "", "क्या?", "मैं गाड़ी चला रहा हूँ", "हम्म"]  # fmt: skip


def test_invariant_no_lender_before_a_strong_claim_or_the_year_and_no_loan_before_the_year():
    """Walk every three-reply opening on both paths, rules only."""
    rec = record(product())
    for replies in itertools.product(OPENING_REPLIES, repeat=3):
        state, said = start(rec, HI, lender_name=LENDER)
        strong, year_passed = False, False
        for k, reply in enumerate(replies):
            position = state.position
            state, said = step(state, reply)
            if position.at == "identity" and state.position.at == "go_ahead":
                strong = True
            if isinstance(position, AtBirthYear) and state.position.at in ("go_ahead", "recall"):
                year_passed = True
            utterance = said.utterance if hasattr(said, "utterance") else said
            for line in utterance.lines:
                if not (strong or year_passed):
                    assert LENDER not in line.text and "lender" not in line.slots, (replies, line.key)
                if not year_passed:
                    assert not any(word in line.text for word in LOAN_WORDS), (replies, line.key)
            if state.position.at == "ended":
                break


def test_a_state_saved_before_round_3_still_loads():
    state, _ = start(record(), HI, lender_name=LENDER)
    state, _ = step(state, "हाँ जी, बोल रहा हूँ")
    state, _ = step(state, "हाँ")
    saved = state.model_dump(mode="json")
    saved["position"].pop("early", None)
    old = CallState.model_validate(saved)
    assert old.position == AtBirthYear() and not old.position.early
    stopped = state.model_copy(update={"position": AtStopCheck(wish="decline", resume=state.position)})
    saved = stopped.model_dump(mode="json")
    saved["position"]["resume"].pop("early", None)
    assert CallState.model_validate_json(stopped.model_dump_json()) == stopped
    assert CallState.model_validate(saved).position.resume == AtBirthYear()


# --- Part D: open recall ----------------------------------------------------------------------

NAMES_SOMETHING = ["पता नहीं क्या था, कुछ बावन हज़ार कटे थे", "कुछ नहीं लिया पर बावन हज़ार कट गए",
                   "हाँ कुछ तो लिया था, नाम याद नहीं"]  # fmt: skip
NAMES_NOTHING = ["कुछ नहीं लिया, बस लोन लिया था", "पता नहीं", "याद नहीं", "नहीं जी, सिर्फ़ लोन"]
DENIES = {"labels": lambda reply, stage: "dont_know" if "question" in stage else sensible(reply, stage)}


def recall_arms():
    return {
        "rules": {},
        "dont_know": {"interpreter": LlmFallbackInterpreter(Labels(DENIES["labels"]))},
        "no": {"interpreter": LlmFallbackInterpreter(
            Labels(lambda r, s: "no" if "question" in s else sensible(r, s)))},
        "raises": {"interpreter": LlmFallbackInterpreter(Labels(error=TransportError("down")))},
    }  # fmt: skip


@pytest.mark.parametrize("arm", ["rules", "dont_know", "no", "raises"])
@pytest.mark.parametrize("reply", NAMES_SOMETHING)
def test_a_reply_that_names_something_starts_the_product_questions(arm, reply):
    call = play(record(product()), HI, [*STRONG, reply], **recall_arms()[arm])
    assert "open_recall.nothing" not in call.keys and call.keys[-1] != "consent.ask", call.keys


@pytest.mark.parametrize("arm", ["rules", "dont_know", "raises"])
@pytest.mark.parametrize("reply", NAMES_NOTHING)
def test_a_reply_that_names_nothing_goes_to_the_follow_up(arm, reply):
    call = play(record(product()), HI, [*STRONG, reply], **recall_arms()[arm])
    assert call.keys[-1] == "open_recall.nothing", call.keys


@pytest.mark.parametrize("arm", ["rules", "dont_know", "raises"])
def test_at_the_follow_up_a_required_act_starts_the_product_questions(arm):
    replies = [*STRONG, "पता नहीं", "बोला था कि ये करवाना पड़ेगा, वरना लोन नहीं मिलेगा"]
    call = play(record(product()), HI, replies, **recall_arms()[arm])
    assert call.keys[-1] != "consent.ask" and "teach_back.intro" in call.keys, call.keys
    call = play(record(product()), HI, [*STRONG, "पता नहीं", "नहीं जी, सिर्फ़ लोन"], **recall_arms()[arm])
    assert call.keys[-1] == "consent.ask"


@pytest.mark.parametrize("reply", NAMES_NOTHING)
def test_naming_nothing_sounds_the_same_whatever_the_product_count(reply):
    heard = []
    for count in range(4):
        rec = record(*(product(f"P{k + 1}") for k in range(max(count, 1))))
        if count == 0:
            rec = rec.model_copy(update={"products": ()})
        call = play(rec, HI, [*STRONG, reply, "कुछ नहीं"])
        heard.append([u.text for u in call.utterances])
    assert all(h == heard[0] for h in heard)


def test_with_no_products_a_reply_that_names_something_goes_to_consent():
    empty = record().model_copy(update={"products": ()})
    call = play(empty, HI, [*STRONG, NAMES_SOMETHING[0]])
    assert call.keys[-1] == "consent.ask"


# --- Part C: a repeated figure at a read-back -------------------------------------------------


def at_read_back(language):
    customer = CUSTOMERS[language]
    call = play(record(product()), language, [*STRONG, "एक एफडी ली थी", "एफडी है", "बावन हज़ार"])
    assert call.keys[-1] == "read_back.confirm", call.keys
    return call.state, customer


@pytest.mark.parametrize("language", [HI, HE])
@pytest.mark.parametrize("reply", ["52,000 दिए थे", "हाँ बावन हज़ार", "fifty two thousand hi diye the",
                                   ("52,000 दिए थे", "हाँ जी"), ("बावन हज़ार दिए", "52000")])  # fmt: skip
def test_repeating_the_figure_confirms_it(language, reply):
    state, _ = at_read_back(language)
    first, second = reply if isinstance(reply, tuple) else (reply, None)
    _, said = step(state, first, second_reading=second)
    assert said.lines[-1].key not in ("read_back.reconfirm", "read_back.restate", "read_back.confirm")


@pytest.mark.parametrize("language", [HI, HE])
def test_a_different_figure_is_a_correction_and_a_denial_with_the_figure_is_not_a_confirmation(language):
    state, _ = at_read_back(language)
    _, said = step(state, "पचपन हज़ार दिए थे")
    assert said.lines[-1].key == "read_back.confirm"
    assert "पचपन" in said.lines[-1].text or "fifty five" in said.lines[-1].text
    _, said = step(state, "नहीं, बावन हज़ार नहीं")
    assert said.lines[-1].key == "read_back.restate"


# --- Part F: a stop signal in either reading --------------------------------------------------

THIRD = "मैं वो नहीं हूँ, उनका भाई बोल रहा हूँ"
STOPS = {
    "मुझे बात नहीं करनी, कॉल बंद करो": "ended:declined",
    "कल शाम को कॉल करना": "ended:call_back_later",
    "बस करो": "stop_check",
}


def figure_positions():
    base = [*STRONG, "एक एफडी ली थी", "एफडी है"]
    return {
        "premium": base,
        "read_back": [*base, "बावन हज़ार"],
        "restate": [*base, "बावन हज़ार", "नहीं"],
    }


def effect(state, first, second, **kw):
    after, said = step(state, first, second_reading=second, **kw)
    if hasattr(said, "outcome"):
        return f"ended:{said.outcome.value}", after
    return ("stop_check" if isinstance(after.position, AtStopCheck) else said.lines[-1].key), after


@pytest.mark.parametrize("where", ["premium", "read_back", "restate"])
@pytest.mark.parametrize("stop", STOPS)
@pytest.mark.parametrize("order", ["stop_first", "figure_first"])
def test_a_stop_signal_in_either_reading_wins_over_a_figure(where, stop, order):
    state = play(record(product()), HI, figure_positions()[where]).state
    pair = (stop, "पचपन हज़ार") if order == "stop_first" else ("पचपन हज़ार", stop)
    got, after = effect(state, *pair)
    assert got == STOPS[stop]
    said_by_customer = [t for t in after.turns if t.speaker is Speaker.customer][-1]
    assert said_by_customer.text == stop and after.second_readings[-1].text == "पचपन हज़ार"


@pytest.mark.parametrize("order", ["stop_first", "figure_first"])
def test_a_third_party_in_either_reading_ends_the_call(order):
    llm = Labels(lambda reply, stage: "wrong_person" if "भाई" in reply else "answer")
    state = play(record(product()), HI, figure_positions()["premium"]).state
    pair = (THIRD, "बावन हज़ार") if order == "stop_first" else ("बावन हज़ार", THIRD)
    got, _ = effect(state, *pair, interpreter=LlmFallbackInterpreter(llm))
    assert got == "ended:wrong_party"


def test_two_stop_intents_take_the_more_protective():
    state = play(record(product()), HI, figure_positions()["premium"]).state
    got, _ = effect(state, "कल शाम को कॉल करना", "मुझे बात नहीं करनी, कॉल बंद करो")
    assert got == "ended:declined"


def test_two_readings_with_figures_behave_as_before():
    state = play(record(product()), HI, figure_positions()["premium"]).state
    got, _ = effect(state, "बावन हज़ार", "पचपन हज़ार")
    assert got == "premium.say_again"
    got, _ = effect(state, "बावन हज़ार", "बावन हज़ार")
    assert got == "read_back.confirm"


# --- Part B: when the classifier is asked -----------------------------------------------------


def test_which_turns_reach_the_classifier():
    llm = Labels(sensible)
    replies = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984", "एक बीमा लिया था", "बीमा", "हाँ", "बावन हज़ार", "हाँ"]
    play(record(product()), HI, replies, interpreter=LlmFallbackInterpreter(llm))
    assert llm.calls == []  # tight claim, plain yes, tight year, answers that speak of the sale
    llm = Labels(sensible)
    play(record(product()), HI, ["हाँ जी, बोल रहा हूँ", "हाँ जी, थोड़ा जल्दी", "1984", "आज बहुत गर्मी है"],
         interpreter=LlmFallbackInterpreter(llm))  # fmt: skip
    assert len(llm.calls) == 2  # a go-ahead with more than yes-words; a free reply with no substance


def test_begin_then_interpret_makes_one_call_and_honours_the_remaining_time():
    llm = Labels(lambda r, s: "answer", delay=0.3)
    reader = LlmFallbackInterpreter(llm, timeout_s=0.5)
    args = {"language": HI, "expecting": Expecting.open, "question": "q"}
    reader.begin("आज बहुत गर्मी है", **args)
    time.sleep(0.35)
    t0 = time.monotonic()
    heard = reader.interpret("आज बहुत गर्मी है", **args)
    assert len(llm.calls) == 1 and time.monotonic() - t0 < 0.1 and not heard.degraded
    slow = LlmFallbackInterpreter(Labels(lambda r, s: "answer", delay=1.0), timeout_s=0.4)
    slow.begin("आज बहुत गर्मी है", **args)
    time.sleep(0.3)
    t0 = time.monotonic()
    heard = slow.interpret("आज बहुत गर्मी है", **args)
    assert time.monotonic() - t0 < 0.25 and heard.degraded


def test_a_begun_call_that_fails_leaves_the_safe_default():
    reader = LlmFallbackInterpreter(Labels(error=TransportError("down")))
    args = {"language": HI, "expecting": Expecting.birth_year, "question": "q"}
    reader.begin("हमारे ये तो 1984 के हैं", **args)  # wave 5: "जी अपना तो 1984 का है" now passes
    heard = reader.interpret("हमारे ये तो 1984 के हैं", **args)
    assert heard.year is None and heard.degraded


def test_prefetch_never_raises():
    state, _ = start(record(), HI, lender_name=LENDER)

    class Broken:
        def begin(self, *a, **k):
            raise RuntimeError("boom")

    prefetch(state, "हाँ", interpreter=Broken())
    prefetch(state, "हाँ", interpreter=object())  # no begin: a no-op
    llm = Labels(sensible)
    reader = LlmFallbackInterpreter(llm)
    prefetch(state, "रमेश", interpreter=reader)
    step(state, "रमेश", interpreter=reader)
    assert len(llm.calls) == 1
