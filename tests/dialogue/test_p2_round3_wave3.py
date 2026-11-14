"""P2 round 3, wave 3: the remaining failures on fresh inputs, each tested both ways."""

from __future__ import annotations

import pytest
from dialogue_kit import LENDER, play, product, record
from test_p2_round3 import STRONG, Labels, sensible
from test_p2_round3_wave2 import AT_KIND, AT_RECALL, OPEN

from samajh.clients.errors import TransportError
from samajh.dialogue import Outcome, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.dialogue.machine import AtCallbackTime
from samajh.types import Language

HI = Language.hi


def run(replies, **kw):
    return play(record(product()), HI, replies, **kw)


# --- X1: a date of birth --------------------------------------------------------------------


@pytest.mark.parametrize("reply", ["उन्नीस सौ चौरासी, पंद्रह जून।", "Nineteen eighty four, June mein.",
                                   "मेरी पैदाइश चौरासी की है।", "15 June 1984"])  # fmt: skip
def test_a_date_of_birth_with_the_right_year_passes(reply):
    assert run([*OPEN, reply]).keys[-1] == "open_recall.ask"


def test_a_date_of_birth_with_the_wrong_year_fails():
    assert run([*OPEN, "उन्नीस सौ तिरासी, पंद्रह जून।"]).end.outcome is Outcome.second_check_failed


# --- X2: a guess uses the one attempt -------------------------------------------------------


@pytest.mark.parametrize("guess", ["शायद चौरासी?", "1984 hoga shayad?", "Maybe 1984, not sure.",
                                   "उन्नीस सौ अस्सी या चौरासी, ठीक से याद नहीं।", "nineteen eighty... six? no, four?"])  # fmt: skip
def test_a_guess_ends_the_check_whatever_the_year(guess):
    call = run([*OPEN, guess, "1984"])
    assert call.end.outcome is Outcome.second_check_failed and call.keys[-1] == "end.check_failed"


@pytest.mark.parametrize("reply", ["1984?", "1984"])
def test_a_question_mark_alone_is_not_a_guess(reply):
    assert run([*OPEN, reply]).keys[-1] == "open_recall.ask"


def test_a_reply_with_no_number_keeps_the_reask():
    call = run([*OPEN, "याद नहीं", "1984"])
    assert call.keys[-1] == "open_recall.ask" and "second_check.reask" in call.keys


# --- X3: cooperative replies at the go-ahead ------------------------------------------------


@pytest.mark.parametrize("reply", ["हाँ, कोई परेशानी नहीं है, चलिए।", "रुकिए मत, बोलते रहिए।", "Haan, no issues, start karo."])
def test_a_cooperative_reply_at_the_go_ahead_never_ends(reply):
    call = run(["हाँ जी, बोल रहा हूँ", reply])
    assert call.end is None and call.keys[-1] in ("second_check.ask", "disclosure.reask")


@pytest.mark.parametrize("reply", ["नहीं जी, रहने दीजिए", "मुझे बात नहीं करनी"])
def test_a_plain_no_at_the_go_ahead_still_ends(reply):
    assert run(["हाँ जी, बोल रहा हूँ", reply]).end is not None


# --- X4: "now" with go on wins at the call-back question ------------------------------------


@pytest.mark.parametrize("now", ["अरे नहीं, अभी कर लेते हैं, पूछिए।", "नहीं, अभी ठीक है, आगे बढ़िए।",
                                 "अभी ही पूछ लो, बाद में टाइम नहीं मिलेगा।", "No, now is fine, continue."])  # fmt: skip
def test_now_and_go_on_resumes(now):
    call = run([*AT_KIND, "बाद में कॉल करना"])
    assert isinstance(call.state.position, AtCallbackTime)
    _, said = step(call.state, now)
    assert not hasattr(said, "outcome") and said.lines[-1].key in ("kind.ask", "kind.ask_named", "kind.reask")


def test_not_now_later_still_ends():
    call = run([*AT_KIND, "बाद में कॉल करना"])
    assert step(call.state, "अभी नहीं, बाद में")[1].outcome is Outcome.call_back_later


# --- X5 and X8: takeovers -------------------------------------------------------------------

TAKEOVERS = ["रमेश जी अभी उठ के गए हैं, मैं दुकान का लड़का हूँ।", "Hi, this is his brother, he had to step out.",
             "Hello? Uncle ne phone diya, main unka bhatija hoon.", "Unko chakkar aa gaya, main padosi hoon, kya baat hai?",
             "पापा ने फ़ोन मुझे दे दिया, मैं उनका बेटा हूँ।", "हैलो? कौन? मम्मी, ये किसका फ़ोन है?",
             "Sir abhi call pe nahi hain, main unka accountant hoon."]  # fmt: skip
CONTROLS = ["नॉमिनी मेरी पत्नी है", "मेरे भाई का भी वहीं लोन है", "एजेंट ने बोला था"]
ARMS = {
    "rules": dict,
    "raises": lambda: {"interpreter": LlmFallbackInterpreter(Labels(error=TransportError("down")))},
    "answers": lambda: {"interpreter": LlmFallbackInterpreter(Labels(sensible))},
    # W4: the setup claim and go-ahead now reach the classifier; they get the labels a classifier would give.
    "who_or_why": lambda: {"interpreter": LlmFallbackInterpreter(
        Labels(lambda r, s: sensible(r, s) if "first_name" in s or "go_ahead" in s else "who_or_why"))},
}


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", TAKEOVERS)
def test_a_takeover_gets_the_who_check_before_anything_else(arm, reply):
    call = run([*AT_KIND, reply], **ARMS[arm]())
    assert call.keys[-1] == "right_party.who_check", call.keys
    assert "verify.after_loan" not in call.keys and LENDER not in call.utterances[-1].text


def test_a_classifier_end_label_still_ends_a_takeover():
    reader = LlmFallbackInterpreter(Labels(lambda r, s: "wrong_person"))
    call = run([*AT_KIND, "पापा ने फ़ोन मुझे दे दिया, मैं उनका बेटा हूँ।"], interpreter=reader)
    assert call.end.outcome is Outcome.wrong_party


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", CONTROLS)
def test_an_account_is_not_a_takeover(arm, reply):
    keys = run([*AT_KIND, reply], **ARMS[arm]()).keys
    if reply.startswith("मेरे भाई का") and arm in ("rules", "raises", "who_or_why"):
        # Round 4: "my relative's ..." is a weak sign of another speaker; with no classifier label (or one
        # that says nothing about who is speaking) the who-check is the safe default (one question). An
        # "answer" label decides it.
        assert keys[-1] == "right_party.who_check"
    else:
        assert keys[-1] != "right_party.who_check"


def test_a_plain_who_question_from_the_borrower_still_gets_the_verify_line():
    call = run([*AT_KIND, "आप कौन बोल रहे हैं? ये फ्रॉड तो नहीं?"])
    assert "verify.after_loan" in call.keys


# --- X6: recall replies that name something in another clause -------------------------------


@pytest.mark.parametrize("reply", [
    "Pata nahi, but loan amount se kuch paisa deduct hua tha.",
    "Not sure, bas extra charges lage the, around ten thousand.",
    "Kuch toh tha, staff ne bola isse loan jaldi pass hoga, naam nahi pata.",
    "Hmm, kuch protection type ka tha shayad, details nahi pata.",
    "मुझे तो समझ नहीं आया, बैंक वाले भैया ने कहा इसमें फ़ायदा है, तो हाँ कर दी।",
])  # fmt: skip
def test_a_reply_that_names_something_in_another_clause_starts_the_products(reply):
    assert run([*AT_RECALL, reply]).keys[-1] == "kind.ask_named"


@pytest.mark.parametrize("reply", ["कुछ नहीं लिया, बस लोन लिया था", "नहीं, कुछ नहीं कटा", "पता नहीं", "याद नहीं",
                                   "नहीं जी, सिर्फ़ लोन", "Nope, aur kuch nahi", "Don't think so."])  # fmt: skip
def test_a_reply_that_names_nothing_still_goes_to_the_follow_up(reply):
    assert run([*AT_RECALL, reply]).keys[-1] == "open_recall.nothing"


# --- X7: any length after the re-ask --------------------------------------------------------


def test_a_long_yes_after_the_reask_is_an_ordinary_confirmation():
    assert run(["कौन?", "हाँ, सही जगह फ़ोन किया है, बोलिए।"]).keys[-1] == "second_check.ask"


def test_the_first_reply_keeps_the_bound():
    assert run(["हाँ, सही जगह फ़ोन किया है, बोलिए।"]).keys[-1] == "right_party.reask"


def test_a_long_yes_with_a_third_person_word_after_the_reask_does_not_confirm():
    call = run(["कौन?", "हाँ, वो अभी यहाँ आने वाले हैं, बोलिए"])
    assert call.end is not None and "second_check.ask" not in call.keys


def test_strong_path_still_unchanged():
    assert run(STRONG).keys[-1] == "open_recall.ask"
