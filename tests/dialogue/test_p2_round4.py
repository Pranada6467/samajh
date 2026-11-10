"""P2 round 4: the who-check, takeovers without a classifier, the year's near-spellings, opening refusals,
the stale verify line, and round 3's residuals. Behaviour through `start` / `step`, in three arms."""

from __future__ import annotations

import pytest
from dialogue_kit import LENDER, play, product, record
from test_p2_round3 import Labels, sensible

from samajh.clients.errors import TransportError
from samajh.dialogue import Limits, Outcome, RuleInterpreter, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
RULES = RuleInterpreter()
ORDINARY = ["हाँ जी", "1984", "हाँ"]  # the ordinary path to open recall
AT_KIND = [*ORDINARY, "हाँ, एक बीमा लिया था"]
AT_PREMIUM = [*AT_KIND, "बीमा है"]
AT_READ_BACK = [*AT_PREMIUM, "बावन हज़ार"]
AT_SOURCE = [*AT_READ_BACK, "हाँ, सही है"]
AT_STOP = [*AT_KIND, "रहने दो"]
AT_CALLBACK = [*AT_KIND, "बाद में बात करते हैं"]
TAKEOVER = "मैं उनका भाई बोल रहा हूँ"  # a plain takeover: reaches the who-check in every arm
LEAK = ("लोन", "loan", "बीमा", "insurance", "प्रीमियम", "premium", LENDER)


def labelled(label: str) -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: label))


ARMS = {
    "rules": lambda: RULES,
    "raises": lambda: LlmFallbackInterpreter(Labels(error=TransportError("down"))),
    "unclear": lambda: labelled("unclear"),
}


def run(replies, reader=None, language=HI, **kw):
    return play(record(product()), language, replies, interpreter=reader or RULES, **kw)


class Then:
    """The word lists for the first `setup` turns, then `reader`: every arm reaches the same position."""

    def __init__(self, setup: int, reader):
        self.left, self.reader = setup, reader

    def interpret(self, text, **kw):
        if self.left > 0:
            self.left -= 1
            return RULES.interpret(text, **kw)
        return self.reader.interpret(text, **kw)


def run_at(prefix, tail, reader, language=HI, **kw):
    return run([*prefix, *tail], Then(len(prefix), reader), language=language, **kw)


def said_after(call, k: int) -> str:
    """The bot's words from utterance `k` on (0 is the opening question)."""
    return " ".join(u.text for u in call.utterances[k:])


# --- 1. The who-check -------------------------------------------------------------------------

ADMISSIONS = ["हाँ, मैं उनका बेटा, बोलो", "हाँ जी, मैं उनकी वाइफ", "haan, main dost hoon, bolo",
              "जी हाँ, मैं उनका छोटा भाई", "haan bolo, unki taraf se main hoon", "हाँ, मैं भाई हूँ",
              "yes, I am his son, go ahead", "नहीं, वो बाहर हैं"]  # fmt: skip
AFFIRMATIONS = ["हाँ", "जी हाँ", "हाँ जी बोलिए", "haan bhai bolo", "मैं Ramesh बोल रहा हूँ", "main hi bol raha hoon",
                "speaking", "हाँ मैं ही हूँ", "हाँ, मैं रमेश", "जी, मैं ख़ुद बोल रहा हूँ"]  # fmt: skip
WHO_ARMS = {**ARMS, **{label: (lambda label=label: labelled(label)) for label in
                       ("confirms_self", "yes", "answer", "wrong_person", "third_party_handoff")}}  # fmt: skip


@pytest.mark.parametrize("arm", WHO_ARMS)
@pytest.mark.parametrize("reply", ADMISSIONS)
def test_an_admission_at_the_who_check_ends_as_wrong_party_in_every_arm(arm, reply):
    call = run_at([*AT_KIND, TAKEOVER], [reply], WHO_ARMS[arm](), language=HE if reply.isascii() else HI)
    assert call.end.outcome is Outcome.wrong_party, call.keys
    assert call.end.speaker_confirmed is False and call.keys[-1] == "end.third_party"
    assert not any(word in said_after(call, 5) for word in LEAK)


@pytest.mark.parametrize("arm", WHO_ARMS)
@pytest.mark.parametrize("reply", AFFIRMATIONS)
def test_an_affirmation_at_the_who_check_resumes_the_question(arm, reply):
    call = run_at([*AT_KIND, TAKEOVER], [reply], WHO_ARMS[arm](), language=HE if reply.isascii() else HI)
    if arm in ("wrong_person", "third_party_handoff") and reply in ("मैं Ramesh बोल रहा हूँ", "हाँ, मैं रमेश"):
        # A name is outside what the interpreter can settle alone (it does not know the name), so the
        # classifier is asked; an end label ends the call.
        assert call.end.outcome is Outcome.wrong_party
        return
    assert call.end is None and call.keys[-1] in ("kind.ask", "kind.reask"), call.keys


@pytest.mark.parametrize("label, resumes", [("confirms_self", True), ("yes", False), ("answer", False),
                                            ("unclear", False)])  # fmt: skip
def test_the_classifier_confirms_an_unexplained_reply_only_with_confirms_self_and_an_i(label, resumes):
    reply = "जी हाँ, मैं ही हूँ, कहिए क्या जानना है"  # "क्या जानना है" is outside the closed vocabulary
    call = run_at([*AT_KIND, TAKEOVER], [reply], labelled(label))
    assert (call.end is None) is resumes, call.keys
    no_i = run_at([*AT_KIND, TAKEOVER], ["जी हाँ, कहिए क्या जानना है"], labelled("confirms_self"))
    assert no_i.end.outcome is Outcome.wrong_party


def test_an_unexplained_reply_ends_with_the_word_lists_alone():
    for reader in (RULES, ARMS["raises"]()):
        call = run_at([*AT_KIND, TAKEOVER], ["जी हाँ, मैं ही हूँ, कहिए क्या जानना है"], reader)
        assert call.end.outcome is Outcome.wrong_party


def test_every_wrong_party_end_carries_speaker_confirmed_false():
    takeover_end = run([*AT_KIND, TAKEOVER, "नहीं"])
    capped = run([*AT_KIND, TAKEOVER, "हाँ", TAKEOVER, "हाँ", TAKEOVER])
    classifier_end = run_at(AT_KIND, ["main unki wife hoon"], labelled("wrong_person"))
    for call in (takeover_end, capped, classifier_end):
        assert call.end.outcome is Outcome.wrong_party and call.end.speaker_confirmed is False, call.keys
        assert call.state.speaker_confirmed is False


# --- 2. Takeovers with the classifier off or failing --------------------------------------------

SIGNS = ["हेलो? मैं उनका भाई, क्या पूछ रहे थे", "ये मेरे पति का लोन है, मुझसे बात करो",
         "hello main unka beta, papa chale gaye", "haan ab main bol raha hoon, unka bhai",
         "sir wo chale gaye, main unka driver", "रुकिए, उनकी बेटी बोल रही हूँ", "hello? kaun? kya chal raha hai?",
         "मेरे बेटे ने सब भरा था, मुझे नहीं पता"]  # fmt: skip
STAGES = {"recall": ORDINARY, "kind": AT_KIND, "premium": AT_PREMIUM, "read_back": AT_READ_BACK,
          "source": AT_SOURCE, "stop": AT_STOP, "callback": AT_CALLBACK}  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("stage", STAGES)
@pytest.mark.parametrize("sign", SIGNS)
def test_a_sign_of_another_speaker_gets_the_who_check_first(arm, stage, sign):
    prefix = STAGES[stage]
    call = run_at(prefix, [sign], ARMS[arm](), language=HE if sign.isascii() else HI)
    assert call.end is None and call.keys[-1] == "right_party.reask", call.keys
    assert not any(word in call.utterances[-1].text for word in LEAK)
    assert "stop_check.decline" not in call.keys[-1:] and "verify.after_loan" not in call.keys[-1:]
    ended = run_at(prefix, [sign, "हाँ, मैं उनका भाई"], ARMS[arm]())
    assert ended.end.outcome is Outcome.wrong_party
    resumed = run_at(prefix, [sign, "हाँ"], ARMS[arm]())  # known: a false "हाँ" passes
    assert resumed.end is None and resumed.keys[-1] != "right_party.reask"


def test_the_who_check_from_the_callback_question_asks_when_again():
    call = run([*AT_CALLBACK, "मैं उनका बेटा हूँ, पापा शाम को आएँगे", "हाँ जी"])
    assert call.keys[-2:] == ("right_party.reask", "callback.when"), call.keys


def test_a_strong_sign_is_not_cleared_by_a_classifier_answer_and_is_ended_by_wrong_person():
    assert run_at(AT_KIND, ["hello main unka beta, papa chale gaye"], labelled("answer")).keys[-1] \
        == "right_party.reask"  # fmt: skip
    ended = run_at(AT_KIND, ["hello main unka beta, papa chale gaye"], labelled("wrong_person"))
    assert ended.end.outcome is Outcome.wrong_party


def test_a_weak_sign_that_says_nothing_of_the_speaker_to_the_classifier_still_gets_the_who_check():
    for label in ("asks_repeat", "who_or_why", "off_topic"):
        call = run_at(AT_KIND, ["hello? kaun? kya chal raha hai?"], labelled(label), language=HE)
        assert call.keys[-1] == "right_party.reask", (label, call.keys)


def test_after_a_weak_sign_the_classifier_let_pass_an_unjudged_turn_gets_the_who_check():
    answers_then_fails = Labels(lambda reply, stage: "answer")
    reader = LlmFallbackInterpreter(answers_then_fails)
    call = run_at(AT_KIND, ["मेरे बेटे ने सब भरा था, बीमा था"], reader)
    assert call.end is None and call.keys[-1] != "right_party.reask" and call.state.speaker_doubt
    answers_then_fails.error = TransportError("down")
    _, said = step(call.state, "हम्म, वो जो था ना", interpreter=reader)
    assert said.lines[-1].key == "right_party.reask"


def test_who_checks_have_their_own_cap_and_end_as_wrong_party():
    limits = Limits(max_who_checks=1)
    call = run([*AT_KIND, TAKEOVER, "हाँ", "main unki wife hoon"], limits=limits)
    assert call.end.outcome is Outcome.wrong_party and call.keys[-1] == "end.third_party"
    # A call that used its "shall I go on?" checks still gets a who-check.
    used = run([*AT_KIND, "रहने दो", "हाँ", TAKEOVER], limits=Limits(max_stop_checks=1))
    assert used.keys[-1] == "right_party.reask", used.keys


@pytest.mark.parametrize("arm", ARMS)
def test_a_plain_answer_is_not_a_sign(arm):
    for reply in ("एक बीमा है, एजेंट ने बताया था", "नॉमिनी मेरी पत्नी है", "लोन में से कट गया"):
        assert run_at(AT_KIND, [reply], ARMS[arm]()).keys[-1] != "right_party.reask", reply


# --- 3. The birth year: near-spellings ------------------------------------------------------------

YEAR_ARMS = {**ARMS, "answers": lambda: LlmFallbackInterpreter(Labels(sensible))}


@pytest.mark.parametrize("arm", YEAR_ARMS)
@pytest.mark.parametrize("reply", ["उन्नीस सौ चौरसी", "उन्निस सौ चौरासी", "उन्नीस सौ चोरासी", "unnis sau chaurasee"])
def test_a_near_spelling_of_the_right_year_passes(arm, reply):
    call = run(["हाँ जी", reply], YEAR_ARMS[arm](), language=HE if reply.isascii() else HI)
    assert call.end is None and call.keys[-1] == "disclosure.go_ahead", call.keys


@pytest.mark.parametrize("arm", YEAR_ARMS)
@pytest.mark.parametrize("reply", ["उन्नीस सौ पचासी", "उन्नीस सौ तिरासि", "उन्नीस सौ चौरानवे"])
def test_another_year_or_a_near_spelling_of_another_year_still_fails(arm, reply):
    call = run(["हाँ जी", reply], YEAR_ARMS[arm]())
    assert call.end.outcome is Outcome.second_check_failed, call.keys


def test_an_uncorrectable_number_like_word_after_sau_is_no_year():
    call = run(["हाँ जी", "उन्नीस सौ चौरस"])
    assert call.end is None and call.keys[-1] == "second_check.reask"
    assert run(["हाँ जी", "उन्नीस सौ चौरस", "पता नहीं"]).end.outcome is Outcome.second_check_failed


# --- 4. A refusal at the opening ----------------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply, outcome", [
    ("नहीं करनी कोई बात, रखो", Outcome.declined), ("मुझे बात नहीं करनी है", Outcome.declined),
    ("mujhe koi baat nahi karni", Outcome.declined), ("दोबारा कॉल मत करना, नंबर हटा दो", Outcome.do_not_call),
    ("नहीं", Outcome.wrong_party), ("नहीं, वो घर पर नहीं हैं, बाद में करना", Outcome.wrong_party),
    ("वो नहीं हैं, बात नहीं हो सकती", Outcome.wrong_party),
])  # fmt: skip
def test_a_refusal_at_the_opening_is_a_refusal(arm, reply, outcome):
    for prefix in ([], ["नमस्ते"]):  # the first-name question and its re-ask
        call = run([*prefix, reply], ARMS[arm]())
        assert call.end.outcome is outcome, (prefix, call.keys)
        assert call.end.speaker_confirmed is False and LENDER not in call.end.utterance.text


@pytest.mark.parametrize("prefix", [AT_KIND, AT_PREMIUM, AT_READ_BACK, ORDINARY])
def test_the_same_refusal_later_ends_as_declined_with_the_word_lists(prefix):
    assert run([*prefix, "नहीं करनी कोई बात, रखो"]).end.outcome is Outcome.declined


# --- 5. verify.before_loan only before the year ---------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_a_who_question_after_the_year_gets_the_after_loan_answer(arm):
    call = run(["हाँ जी", "1984", "आप कौन बोल रहे हो?"], ARMS[arm]())
    assert call.keys[-2:] == ("verify.after_loan", "disclosure.go_ahead"), call.keys
    strong = run(["हाँ जी, मैं ही बोल रहा हूँ", "आप कौन बोल रहे हो?"], ARMS[arm]())
    assert strong.keys[-2:] == ("verify.before_loan", "disclosure.go_ahead"), strong.keys


# --- 6. Residuals ---------------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["नहीं नहीं, अभी कर लीजिए।", "Na, later nahi, abhi karte hain."])
def test_a_negated_later_with_a_now_word_resumes(arm, reply):
    call = run([*AT_CALLBACK, reply], ARMS[arm]())
    assert call.end is None and call.keys[-1] == "kind.ask", call.keys


@pytest.mark.parametrize("reply", ["अभी नहीं, कल शाम", "abhi nahi, baad mein", "नहीं, अभी बिज़ी हूँ"])
def test_not_now_still_ends_as_a_call_back(reply):
    assert run([*AT_CALLBACK, reply]).end.outcome is Outcome.call_back_later


@pytest.mark.parametrize("arm", ARMS)
def test_i_do_not_remember_at_the_year_gets_the_one_reask(arm):
    call = run(["हाँ जी", "साल? वो तो याद नहीं अभी"], ARMS[arm]())
    assert call.end is None and call.keys[-1] == "second_check.reask", call.keys
    assert run(["हाँ जी", "साल? वो तो याद नहीं अभी", "पता नहीं"], ARMS[arm]()).end.outcome \
        is Outcome.second_check_failed  # fmt: skip
    assert run(["हाँ जी", "वो बाहर गए हैं"], ARMS[arm]()).end.outcome is Outcome.wrong_party


# --- Follow-ups on item 4 (coordinator) -----------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply, outcome", [
    ("नहीं भाई, अभी बात नहीं करनी, फ़ोन रखो", Outcome.declined), ("nahi yaar, baat nahi karni", Outcome.declined),
    ("sir nahi chahiye, phone rakho", Outcome.declined), ("अरे भैया नहीं करनी बात", Outcome.declined),
    ("रहने दो, नहीं करनी कोई बात", Outcome.declined),
    ("नहीं, मैं उनका भाई हूँ, बात नहीं करनी", Outcome.wrong_party), ("भाई साहब घर पर नहीं हैं", Outcome.wrong_party),
    ("नहीं भाई", Outcome.wrong_party),
])  # fmt: skip
def test_an_address_form_inside_a_refusal_at_the_opening_is_address(arm, reply, outcome):
    for prefix in ([], ["नमस्ते"]):
        call = run_at(prefix, [reply], ARMS[arm](), language=HE if reply.isascii() else HI)
        assert call.end.outcome is outcome, (prefix, call.keys)
        assert call.end.speaker_confirmed is False


@pytest.mark.parametrize("arm", ARMS)
def test_a_structural_refusal_beats_a_weak_stop_signal_later_but_a_go_on_word_still_asks(arm):
    assert run_at(AT_KIND, ["रहने दो, नहीं करनी कोई बात"], ARMS[arm]()).end.outcome is Outcome.declined
    asks = run_at(AT_KIND, ["रहने दो वो सब, आप बोलिए"], ARMS[arm]())
    assert asks.end is None, asks.keys


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply, resumes", [("नहीं भाई, मैं ही हूँ", True), ("हाँ भाई मैं ही बोल रहा हूँ", True),
                                            ("हाँ, मैं भाई हूँ उनका", False)])  # fmt: skip
def test_the_who_check_keeps_its_stricter_reading_of_address_forms(arm, reply, resumes):
    call = run_at([*AT_KIND, TAKEOVER], [reply], ARMS[arm]())
    assert (call.end is None) is resumes, call.keys
