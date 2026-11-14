"""Iteration 4, W4 checkpoint 4: three dialogue faults. Builder-written paraphrases; nothing from eval/acq or data/acq."""

from __future__ import annotations

import random

import pytest
from dialogue_kit import CUSTOMERS, NO_CHECK, play, product, record

from samajh.dialogue import Expecting, Intent, Outcome, RuleInterpreter, load_prompts, start, step
from samajh.dialogue._lexicon import LEXICONS, tokens
from samajh.dialogue.interpret import negated_again
from samajh.dialogue.lint import lint_line
from samajh.types import Language

HI = Language.hi
RULES = RuleInterpreter()
HAPPY = CUSTOMERS[HI].happy()
AT_KIND = HAPPY[:4]  # the kind question is next
DEFERRALS = ["आप अपने सिस्टम में चेक कर लो", "बैंक वालों को तो पता ही होगा", "आपकी फ़ाइल में लिखा होगा, वहीं देख लीजिए"]


@pytest.mark.parametrize("reply", DEFERRALS)
def test_a_deferral_mid_call_is_a_non_answer_with_one_re_ask(reply):
    call = play(record(product()), HI, [*AT_KIND, reply])
    assert call.end is None and call.keys[-2] == "defer.reask", call.keys
    again = play(record(product()), HI, [*AT_KIND, reply, reply])
    assert again.end is None and "bridge.moving_on" in again.keys and again.keys.count("defer.reask") == 1
    assert any(u.asks is not None and u.asks.value == "kind" for u in again.state.unresolved)


def test_a_refusal_beside_a_deferral_is_still_a_refusal():
    call = play(record(product()), HI, [*AT_KIND, "मुझे बात नहीं करनी, आप ख़ुद देख लो"])
    assert call.end is not None and call.end.outcome is Outcome.declined


def test_a_deferral_is_not_read_at_the_opening():
    heard = RULES.interpret("आप रिकॉर्ड में देख लो", language=HI, expecting=Expecting.identity)
    assert heard.intent is not Intent.defers


def test_the_defer_line_is_lint_clean_in_every_language():
    for language in Language:
        template = load_prompts(language).templates["defer.reask"]
        assert lint_line("defer.reask", template) == [] and not any(ch.isdigit() for ch in template)


@pytest.mark.parametrize("text", ["उसके बाद फिर कभी नहीं भरना पड़ा", "दोबारा किसी ने कुछ नहीं कहा", "phir kabhi nahi kata"])
def test_a_negated_again_word_in_an_account_is_neither_a_call_back_nor_a_repeat(text):
    heard = RULES.interpret(text, language=HI, expecting=Expecting.either_or)
    assert heard.intent not in (Intent.call_later, Intent.asks_repeat, Intent.maybe_decline), heard.intent


@pytest.mark.parametrize("text, intent", [("बाद में बात कर लेंगे", Intent.call_later), ("दोबारा बोलिए", Intent.asks_repeat),
                                          ("फिर से बताइए", Intent.asks_repeat)])  # fmt: skip
def test_real_call_back_and_repeat_requests_still_read(text, intent):
    assert RULES.interpret(text, language=HI, expecting=Expecting.open).intent is intent


def test_negated_again_needs_a_negation_and_no_say_word():
    lex = LEXICONS[HI]
    assert negated_again(tokens("फिर कभी नहीं देना पड़ा"), lex)
    assert not negated_again(tokens("फिर से बोलिए, समझ नहीं आया"), lex)


POOL = ["अभी बोलिए, अभी फ़्री हूँ", "फिर कभी नहीं देना पड़ा", "आप अपने सिस्टम में देख लो", "", "क्या?",
        "बाद में बात करते हैं", "हम्म"]  # fmt: skip


def test_no_reply_pool_loops_the_call():
    rng = random.Random(4)
    for _ in range(200):
        state, said = start(record(product()), HI, lender_name="Udaharan Bank", identity=NO_CHECK)
        prefix = [HAPPY[0], "हाँ ठीक है", *HAPPY[3:]][: rng.randrange(1, len(HAPPY) + 1)]
        replies = iter(prefix)
        turns = 0
        while not hasattr(said, "outcome"):
            reply = next(replies, None)
            state, said = step(state, rng.choice(POOL) if reply is None else reply)
            turns += 1
            assert turns < 40, state.turns[-6:]
        assert said.outcome is not Outcome.turn_limit and state.bot_turns < 40


def test_a_named_thing_with_a_forgotten_amount_goes_to_the_product_questions():
    for reply in ["एक बीमा लिया था, उसकी रकम याद नहीं", "policy li thi, paise kitne the pata nahi"]:
        call = play(record(product()), HI, [*HAPPY[:3], reply])
        assert call.keys[-1].startswith("kind."), call.keys
    nothing = play(record(product()), HI, [*HAPPY[:3], "कुछ नहीं लिया था, याद नहीं"])
    assert nothing.keys[-1] == "open_recall.nothing"



def test_a_deferral_with_a_refusal_is_no_deferral_and_a_bare_i_still_defers():
    heard = RULES.interpret("आप records में देख लो, पर मुझे और बात करने की ज़रूरत नहीं", language=HI,
                            expecting=Expecting.open)  # fmt: skip
    assert heard.intent is not Intent.defers
    assert RULES.interpret("main nahi bata sakti, bank se hi pooch lo", language=Language.hi_en,
                           expecting=Expecting.open).intent is Intent.defers  # fmt: skip


def test_a_long_deferral_goes_to_the_classifier_and_its_end_label_wins():
    from types import SimpleNamespace

    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    class Refuses:
        def complete(self, schema, messages, **kwargs):
            stage = messages[-1].content.split("\n")[0]
            label = "confirms_self" if "first_name" in stage else "yes" if "go_ahead" in stage else "refuse"
            return SimpleNamespace(value=schema(label=label))

    reply = "देखिए ये सब तो आपके रिकॉर्ड में लिखा ही होगा, मुझे इसके बारे में ज़्यादा कुछ बोलना नहीं"
    call = play(record(product()), HI, [*AT_KIND, reply], interpreter=LlmFallbackInterpreter(Refuses()))
    assert call.end is not None and call.end.outcome is Outcome.declined


def test_a_forgotten_amount_with_a_trailing_me_or_a_variant_spelling_is_not_nothing():
    for reply in ["हाँ बिमा लिया था, कितने का याद नहीं मुझे", "haan insurance li thi kitne ki yaad nahi mujhe"]:
        call = play(record(product()), HI, [*HAPPY[:3], reply])
        assert call.keys[-1].startswith("kind."), (reply, call.keys)


# --- Follow-up (latency worker's replay with the classifier failing): a one-time frequency answer ended `declined` ---


class _NoCredit:
    """Every classifier request fails, as with HTTP 402 from the provider."""

    def complete(self, *args, **kwargs):
        raise RuntimeError("402 insufficient credits")


def _at_frequency(language: Language, interpreter):
    """A call played on the happy path until the bot has just asked the payment-frequency question."""
    state, said = start(record(product()), language, lender_name="Udaharan Bank", identity=NO_CHECK)
    for reply in CUSTOMERS[language].happy():
        if said.lines[-1].key == "payment_frequency.ask":
            return state
        state, said = step(state, reply, interpreter=interpreter)
        assert not hasattr(said, "outcome"), said
    raise AssertionError("never reached the payment-frequency question")


def _arms():
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    return {"rules": RULES, "classifier_failing": LlmFallbackInterpreter(_NoCredit())}


FREQUENCY_ANSWERS = ["One time, एक ही बार।", "one time", "ek baar", "ek hi baar", "sirf ek baar", "एक ही बार दिया था",
                     "har mahine", "monthly", "saal mein ek baar"]  # fmt: skip


@pytest.mark.parametrize("arm", ["rules", "classifier_failing"])
@pytest.mark.parametrize("language", [HI, Language.hi_en])
def test_an_ordinary_frequency_answer_moves_on_without_a_stop_check(arm, language):
    interpreter = _arms()[arm]
    for answer in FREQUENCY_ANSWERS:
        state = _at_frequency(language, interpreter)
        after, said = step(state, answer, interpreter=interpreter)
        keys = [line.key for line in (said.utterance.lines if hasattr(said, "outcome") else said.lines)]
        assert not hasattr(said, "outcome"), (answer, keys)
        assert not any(key.startswith("stop_check") for key in keys), (answer, keys)
        answered = len(state.turns) + 1  # the frequency answer's turn id; the opening turns may be degraded
        assert answered not in after.degraded_turns, (answer, after.degraded_turns)


@pytest.mark.parametrize("arm", ["rules", "classifier_failing"])
def test_a_real_refusal_at_the_frequency_question_still_ends_declined(arm):
    interpreter = _arms()[arm]
    for refusal in ("मुझे बात नहीं करनी", "एक बार, पर अब मुझे बात नहीं करनी, फ़ोन रखिए"):
        state = _at_frequency(HI, interpreter)
        _, said = step(state, refusal, interpreter=interpreter)
        assert getattr(said, "outcome", None) is Outcome.declined, refusal


def test_the_lead_in_lines_are_never_the_line_the_customer_answers():
    """`language.switched` and `defer.reask` lead into a question (the P5 player relies on it: `NO_REPLY`)."""
    deferred = play(record(product()), HI, [*AT_KIND, DEFERRALS[0]])
    switched = play(record(product()), HI, [CUSTOMERS[HI].identity, "हाँ, पर तमिल में बोलिए"], identity=NO_CHECK)
    for call, lead in ((deferred, "defer.reask"), (switched, "language.switched")):
        assert lead in call.keys, call.keys
        assert all(u.lines[-1].key != lead for u in call.utterances)
