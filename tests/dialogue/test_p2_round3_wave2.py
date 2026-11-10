"""P2 round 3, wave 2: the verifier's conditions on 993edf4, each tested both ways."""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, LENDER, play, product, record
from test_p2_round3 import ARMS, STRONG, Labels, figure_positions, interp, sensible, text_of

from samajh.clients.errors import TransportError
from samajh.dialogue import Expecting, Outcome, RuleInterpreter, load_prompts, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.dialogue.machine import AtCallbackTime, AtStopCheck
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
RULES = RuleInterpreter()
AT_RECALL = [*STRONG]
AT_KIND = [*STRONG, "एक एफडी ली थी"]


def keys_after(replies, rec=None, **kw):
    return play(rec or record(product()), HI, replies, **kw)


# --- W1: substance settles a free answer only without a risk cue -------------------------------


@pytest.mark.parametrize("text", [
    "बीमा-वीमा की बात बैंक जाकर करूँगा, अभी नहीं", "Insurance ki baat mujhe phone pe nahi karni",
    "मेरे बेटे से बात करो, सब कागज़ वही रखता है", "मैनेजर साहब से बात करवाइए, तभी बताऊँगा",
    "Policy ki details main khud dekh lunga, aap rehne do",
])  # fmt: skip
def test_a_product_word_with_a_risk_cue_goes_to_the_classifier(text):
    assert not RULES.interpret(text, language=HE, expecting=Expecting.open).settled


@pytest.mark.parametrize("text", ["एक बीमा लिया था", "लोन में से कट गया", "फॉर्म पर साइन किया था बस"])
def test_a_plain_account_of_the_sale_is_still_settled(text):
    assert RULES.interpret(text, language=HE, expecting=Expecting.open).settled


# --- W2: address forms, claim plus question, the re-ask ---------------------------------------


@pytest.mark.parametrize("reply", ["हाँ भाई बोलो", "हाँ भाई, मैं ही रमेश हूँ", "haan bhai Ramesh hi bol raha hoon",
                                   "yes sir", "haan yaar bolo"])  # fmt: skip
def test_an_address_form_beside_a_yes_is_not_a_relation(reply):
    call = keys_after([reply])
    assert call.end is None and call.keys[-1] in ("second_check.ask", "disclosure.go_ahead"), call.keys


@pytest.mark.parametrize("reply", ["मैं उनका भाई बोल रहा हूँ", "भाई हूँ उनका"])
def test_a_relation_in_an_i_am_frame_still_ends(reply):
    assert keys_after([reply]).end.outcome is Outcome.wrong_party


@pytest.mark.parametrize("reply", ["हाँ, मैं ही रमेश हूँ। आप कौन?", "Yes, Ramesh speaking, kaun?"])
def test_a_confirmation_with_a_who_question_is_a_confirmation(reply):
    call = keys_after([reply])
    assert "right_party.reask" not in call.keys
    assert call.keys[-1] in ("second_check.ask", "disclosure.go_ahead")
    assert "purpose.before_confirm" in call.keys or "disclosure.who" in call.keys


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["हाँ", "हाँ जी, बोलिए", "हाँ जी, रमेश ही बोल रहा है"])
def test_a_plain_confirmation_after_the_reask_reaches_the_year(arm, reply):
    call = keys_after(["नमस्ते", reply], **interp(arm))
    assert call.keys[-1] == "second_check.ask", call.keys


# --- W3: refusal words beside a go-on word ----------------------------------------------------

GO_ON = ["बंद मत कीजिए, बोलिए", "phone mat kaatna, haan pucho", "koi dikkat nahi, pucho",
         "नहीं कोई बात नहीं, पूछ लीजिए", "नहीं नहीं, बोलिए, मैं ही हूँ", "अभी बिज़ी था, अब बोलो"]  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", GO_ON)
def test_a_go_on_word_beside_a_refusal_at_the_go_ahead_never_ends_the_call(arm, reply):
    call = keys_after(["हाँ जी, बोल रहा हूँ", reply], **interp(arm))
    assert call.end is None, call.keys
    # Wave 3: "no problem" forms are a yes despite the no-word; other conflicted replies are re-asked.
    allowed = {"second_check.ask"} if arm == "sensible" else {"disclosure.reask", "second_check.ask"}
    assert call.keys[-1] in allowed


def test_a_classifier_answer_at_the_go_ahead_without_a_yes_word_is_asked_again():
    reader = LlmFallbackInterpreter(Labels(lambda r, s: "answer"))
    call = keys_after(["हाँ जी, बोल रहा हूँ", "देखिए, आज मौसम खराब है"], interpreter=reader)
    assert call.end is None and call.keys[-1] == "disclosure.reask"


def test_a_plain_refusal_at_the_go_ahead_still_ends():
    assert keys_after(["हाँ जी, बोल रहा हूँ", "मुझे बात नहीं करनी"]).end is not None


def test_a_conflicted_refusal_later_gets_the_stop_check():
    call = keys_after([*AT_KIND, "मैं किसी इंसान से बात नहीं करना चाहता, आप ही पूछो, वो बीमा है"])
    assert call.end is None and isinstance(call.state.position, AtStopCheck)


# --- W4: "now" at the call-back question ------------------------------------------------------


@pytest.mark.parametrize("now", ["अभी बोलिए, अभी फ़्री हूँ", "abhi bol do", "now is fine"])
def test_now_at_the_call_back_question_resumes_the_question(now):
    call = keys_after([*AT_KIND, "बाद में कॉल करना"])
    assert isinstance(call.state.position, AtCallbackTime)
    _, said = step(call.state, now)
    assert not hasattr(said, "outcome") and said.lines[-1].key in ("kind.ask", "kind.reask")


@pytest.mark.parametrize("later", ["कल शाम को", "अभी नहीं, कल"])
def test_a_time_at_the_call_back_question_ends_as_before(later):
    call = keys_after([*AT_KIND, "बाद में कॉल करना"])
    _, said = step(call.state, later)
    assert said.outcome is Outcome.call_back_later


def test_a_saved_call_back_state_without_resume_ends_as_before():
    call = keys_after([*AT_KIND, "बाद में कॉल करना"])
    old = call.state.model_copy(update={"position": AtCallbackTime()})
    _, said = step(old, "अभी बोलिए")
    assert said.outcome is Outcome.call_back_later


# --- W5: one attempt at the birth year --------------------------------------------------------

OPEN = ["हाँ जी, बोल रहा हूँ", "हाँ"]


@pytest.mark.parametrize("replies", [["1983", "1984"], ["1984 ya 85"]])
def test_a_wrong_year_or_two_years_fail_at_once(replies):
    call = keys_after([*OPEN, *replies])
    assert call.end.outcome is Outcome.second_check_failed and len(call.utterances) == 4


def test_a_question_about_the_year_does_not_pass():
    # Wave 3: a confirmation-seeking tag makes the reply a guess, which uses the one attempt.
    call = keys_after([*OPEN, "1984 है ना? सही है?"])
    assert call.end.outcome is Outcome.second_check_failed


@pytest.mark.parametrize("year", ["सन् चौरासी", "उन्नीस सौ चौरासी साल", "nineteen eighty-four, sir",
                                  "चौरासी, उन्नीस सौ चौरासी", "Mera janam 1984 mein hua tha", "84 mein hua tha"])  # fmt: skip
def test_ordinary_first_person_year_phrasings_pass(year):
    call = keys_after([*OPEN, year])
    assert call.keys[-1] == "open_recall.ask", call.keys


def test_the_ordinary_path_fails_a_wrong_year_without_the_lender():
    call = keys_after(["हाँ जी", "1983"])
    assert call.end.outcome is Outcome.second_check_failed and call.keys[-1] == "end.third_party"
    assert LENDER not in text_of(call)


# --- W6: speaker_confirmed --------------------------------------------------------------------

ENDS = {"मेरा नंबर हटा दो": Outcome.do_not_call, "किसी इंसान से बात कराओ": Outcome.human_requested,
        "कल शाम को कॉल करना": Outcome.call_back_later}  # fmt: skip


@pytest.mark.parametrize("reply", ENDS)
@pytest.mark.parametrize("before", [[], ["हाँ जी, बोल रहा हूँ"], OPEN, ["हाँ जी"]])
def test_an_end_before_the_year_is_unconfirmed(reply, before):
    call = keys_after([*before, reply])
    assert call.end.outcome is ENDS[reply] and call.end.speaker_confirmed is False


@pytest.mark.parametrize("reply", ENDS)
def test_an_end_after_the_year_is_confirmed(reply):
    call = keys_after([*AT_RECALL, reply])
    assert call.end.outcome is ENDS[reply] and call.end.speaker_confirmed is True


# --- W7: a mid-call takeover with no judgment -------------------------------------------------

TAKEOVER = ["मैं रमेश नहीं हूँ", "ये रमेश जी का फ़ोन है, वो बाहर गए हैं", "main unki wife hoon"]
ACCOUNTS = ["नॉमिनी मेरी पत्नी है", "एजेंट ने बोला था", "उन्होंने साइन करवाया"]
DOWN = {"rules": lambda: RULES, "raises": lambda: LlmFallbackInterpreter(Labels(error=TransportError("x"))),
        "unclear": lambda: LlmFallbackInterpreter(Labels(lambda r, s: "unclear"))}  # fmt: skip


@pytest.mark.parametrize("arm", DOWN)
@pytest.mark.parametrize("reply", TAKEOVER)
def test_a_possible_takeover_asks_who_is_speaking(arm, reply):
    reader = DOWN[arm]()
    call = keys_after([*AT_KIND, reply], interpreter=reader)
    assert call.keys[-1] == "right_party.reask" and call.end is None
    last = call.utterances[-1].text
    assert LENDER not in last and "लोन" not in last
    if arm == "raises":
        assert call.state.degraded_turns and call.state.degraded_turns[-1] == call.state.turns[-2].id
    resumed = keys_after([*AT_KIND, reply, "हाँ, मैं ही बोल रहा हूँ"], interpreter=reader)
    assert resumed.end is None and resumed.keys[-1] in ("kind.ask", "kind.reask")
    ended = keys_after([*AT_KIND, reply, "नहीं"], interpreter=reader)
    assert ended.end.outcome is Outcome.wrong_party and ended.keys[-1] == "end.third_party"


def test_a_working_classifier_decides_a_takeover():
    ends = LlmFallbackInterpreter(Labels(lambda r, s: "wrong_person" if "wife" in r else sensible(r, s)))
    assert keys_after([*AT_KIND, "main unki wife hoon"], interpreter=ends).end.outcome is Outcome.wrong_party
    # Wave 3 (X8): a classifier that answers anything but an end label cannot clear the flag.
    goes_on = LlmFallbackInterpreter(Labels(sensible))
    assert keys_after([*AT_KIND, "main unki wife hoon"], interpreter=goes_on).keys[-1] == "right_party.reask"


@pytest.mark.parametrize("reply", ACCOUNTS)
def test_an_account_naming_a_relative_or_staff_is_not_a_takeover(reply):
    assert keys_after([*AT_KIND, reply]).keys[-1] != "right_party.reask"


def test_a_takeover_in_one_of_two_readings_is_acted_on():
    state = keys_after(figure_positions()["premium"]).state
    for pair in (("बावन हज़ार", "main unki wife hoon"), ("main unki wife hoon", "बावन हज़ार")):
        _, said = step(state, *pair[:1], second_reading=pair[1])
        assert said.lines[-1].key == "right_party.reask"


def test_takeover_checks_are_capped():
    call = keys_after([*AT_KIND, "main unki wife hoon", "हाँ, मैं ही बोल रहा हूँ", "मैं रमेश नहीं हूँ",
                       "हाँ, मैं ही बोल रहा हूँ", "main unki wife hoon"])  # fmt: skip
    assert call.end.outcome is Outcome.wrong_party


# --- W8: recall replies that deny and name nothing --------------------------------------------


@pytest.mark.parametrize("reply", ["जो था लोन ही था, और कुछ नहीं", "मुझे नहीं लगता कुछ और लिया था",
                                   "ना जी, बस गोल्ड लोन", "Nope, aur kuch nahi",
                                   "कुछ नहीं, बस सोना गिरवी रखा और पैसे लिए"])  # fmt: skip
def test_a_denial_that_names_nothing_goes_to_the_follow_up(reply):
    assert keys_after([*AT_RECALL, reply]).keys[-1] == "open_recall.nothing"


def test_dont_think_so_at_the_follow_up_goes_to_consent():
    assert keys_after([*AT_RECALL, "पता नहीं", "Don't think so."]).keys[-1] == "consent.ask"


def test_a_reply_that_names_something_still_starts_the_products():
    assert keys_after([*AT_RECALL, "एक एफडी ली थी"]).keys[-1] == "kind.ask"


# --- W9: the two lines and the second product -------------------------------------------------


def test_the_two_new_lines():
    hi, he = load_prompts(HI), load_prompts(HE)
    assert hi.templates["cancel_window.reask"].startswith("मतलब, उसे बंद या कैंसल कराने")
    assert he.templates["cancel_window.reask"].startswith("मतलब, उसे बंद या cancel कराने")
    assert "{ordinal}" not in hi.templates["teach_back.intro_nth"] + he.templates["teach_back.intro_nth"]
    assert "{ordinal}" in load_prompts(Language.ta).templates["teach_back.intro_nth"]


def test_naming_nothing_at_the_second_product_goes_to_consent():
    customer = CUSTOMERS[HI]
    rec = record(product("P1"), product("P2"), product("P3"))
    replies = customer.happy(products=1)[:-1]
    call = play(rec, HI, [*replies, "नहीं, और कुछ नहीं लिया"])
    assert "teach_back.intro_nth" in call.keys and call.keys[-1] == "consent.ask", call.keys
    assert {u.product_id for u in call.state.unresolved} >= {"P2", "P3"}
