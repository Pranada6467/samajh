"""Behaviour the independent review of 2026-11-10 proved wrong, pinned. Each test failed before its fix.

The Hindi and Hinglish sentences are the reviewer's own probes, not recordings; no human said them.
"""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, LANGUAGES, play, product, record

from samajh.amounts import parse_amount
from samajh.dialogue import (
    PRODUCT_QUESTIONS,
    CallState,
    Expecting,
    Intent,
    Limits,
    Outcome,
    RuleInterpreter,
    start,
    step,
)
from samajh.dialogue.lint import lint_line
from samajh.rules import evaluate, to_beliefs
from samajh.types import CallStep, Language, Question, RawExtraction, RuleId, Speaker

HI, HE = Language.hi, Language.hi_en
E = Expecting
RULES = RuleInterpreter()
IDENTITY, GO_AHEAD, YEAR, RECALL, FIRST_ANSWER = 0, 1, 2, 3, 4
PREMIUM = FIRST_ANSWER + PRODUCT_QUESTIONS.index(Question.premium)
READ_BACK = FIRST_ANSWER + len(PRODUCT_QUESTIONS) + 1
LOAN_WORDS = ("लोन", "loan")


def says_nothing_of_a_loan(call) -> bool:
    return not any(word in line.text.casefold() for line in call.lines for word in LOAN_WORDS)


# --- 1. the loan is never named to someone who has said they are not the borrower ------------


@pytest.mark.parametrize(
    "reply",
    [
        "मैं उनकी पत्नी हूँ, उनका जन्म 1984 में हुआ",
        "पापा का जन्म 1984 का है",
        "रॉन्ग नंबर है, 1984",
        "he is my husband, he was born in 1984",
    ],
)
def test_someone_who_says_they_are_not_the_borrower_cannot_pass_the_second_check(reply):
    customer = CUSTOMERS[HI]
    call = play(record(), HI, [customer.identity, customer.go_ahead, reply])
    assert call.end is not None and call.end.outcome is Outcome.wrong_party
    assert call.keys[-1] == "end.neutral" and says_nothing_of_a_loan(call)


@pytest.mark.parametrize("reply", ["मैं उनका बेटा हूँ, हाँ बताइए", "हाँ बोलिए, वैसे मैं उनकी पत्नी हूँ"])
def test_someone_who_says_so_when_asked_to_go_on_ends_the_call(reply):
    call = play(record(), HI, [CUSTOMERS[HI].identity, reply])
    assert call.end is not None and call.end.outcome is Outcome.wrong_party
    assert call.keys[-1] == "end.neutral"


@pytest.mark.parametrize(
    "language, reply",
    [
        (HI, "हाँ जी, उसकी मम्मी बोल रही हूँ"),
        (HI, "मैं उसका भाई हूँ, हाँ बोलिए"),
        (HI, "जी मैं इनकी वाइफ बोल रही हूँ"),
        (HI, "रमेश तो ऑफिस गए हैं, बताइए"),
        (HI, "जी वो बाहर हैं आप बताइए"),
        (HI, "रमेश जी अभी नहा रहे हैं, हाँ कहिए"),
        (HE, "this is his brother speaking"),
        (HE, "he's at work, yes tell me"),
        (HE, "yes, मैं उसकी sister बोल रही हूँ"),
    ],
)
def test_a_reply_that_speaks_of_the_borrower_as_someone_else_is_not_a_yes(language, reply):
    call = play(record(), language, [reply])
    assert call.end is not None and call.end.outcome is Outcome.wrong_party
    assert call.keys == ("right_party.ask", "end.neutral")


@pytest.mark.parametrize(
    "dob, reply",
    [
        ("2001-03-04", "एक बार फिर बोलिए"),  # "say that once more": the "एक" was read as the year 01
        ("2002-03-04", "दो"),
        ("2005-03-04", "पाँच"),
        ("2000-01-01", "zero"),
        ("2001-03-04", "one second"),
    ],
)
def test_a_single_digit_is_not_a_birth_year(dob, reply):
    customer = CUSTOMERS[HI]
    call = play(record(dob=dob), HI, [customer.identity, customer.go_ahead, reply])
    assert call.keys[-1] == "second_check.reask" and says_nothing_of_a_loan(call)


@pytest.mark.parametrize(
    "dob, reply", [("2002-03-04", "2002"), ("2002-03-04", "दो हज़ार दो"), ("1984-06-15", "84")]
)
def test_the_year_itself_still_passes(dob, reply):
    customer = CUSTOMERS[HI]
    call = play(record(dob=dob), HI, [customer.identity, customer.go_ahead, reply])
    assert call.keys[-1] == "open_recall.ask"


# --- 2. an account of the sale that quotes a refusal does not end the call -------------------

NARRATIVES = [
    (HI, "मैंने कहा था मुझे इंटरेस्ट नहीं है पर उन्होंने ज़बरदस्ती दे दिया", "decline"),
    (HI, "उन्होंने बोला बाद में बात करेंगे इस बारे में", "decline"),
    (HI, "बैंक वालों ने कहा फोन रख दो हम देख लेंगे", "decline"),
    (HI, "उस टाइम मैं बिजी हूं बोला था तो उन्होंने जल्दी जल्दी साइन करा लिया", "decline"),
    (HI, "उन्होंने कहा था कॉल मत करना ब्रांच में", "decline"),
    (HI, "एजेंट ने कहा था मैनेजर से बात करा देंगे पर किसी ने नहीं कराई", "human"),
    (HI, "ब्रांच से बात करनी है बोला तो टाल दिया", "human"),
    (HE, "I told them I am not interested but they said it is compulsory", "decline"),
    (HE, "they told me do not call the branch", "decline"),
    (HE, "they said talk to the manager later", "human"),
    (HE, "maine bola tha mujhe interest nahin hai", "decline"),
]


@pytest.mark.parametrize("language, reply, wish", NARRATIVES)
def test_a_refusal_quoted_in_an_answer_is_asked_about_and_does_not_end_the_call(language, reply, wish):
    customer = CUSTOMERS[language]
    call = play(record(), language, [*customer.happy()[:FIRST_ANSWER], reply])
    assert call.end is None and call.keys[-1] == f"stop_check.{wish}"
    call = play(record(), language, [*customer.happy()[:FIRST_ANSWER], reply, customer.reject])
    assert call.end is None and call.keys[-1] == "kind.reask"


@pytest.mark.parametrize(
    "language, reply",
    [
        (HI, "मैंने बोला ना मुझे बात नहीं करनी"),
        (HI, "देखिए मुझे अभी बिल्कुल टाइम नहीं है आप बाद में कॉल कीजिए"),
        (HE, "I am not interested, please don't call"),
        (HE, "mujhe kisi agent se baat karni hai"),
    ],
)
def test_a_refusal_before_the_questions_start_ends_the_call_at_once(language, reply):
    call = play(record(), language, [CUSTOMERS[language].identity, reply])
    assert call.end is not None and call.end.outcome in (Outcome.declined, Outcome.human_requested)
    assert not [key for key in call.keys if key.startswith("stop_check")]


# --- 3. "do you want to stop?" is not asked over and over --------------------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_stop_question_is_asked_twice_at_most_then_a_third_signal_ends_the_call(language):
    customer = CUSTOMERS[language]
    replies = [*customer.happy()[:FIRST_ANSWER], *[customer.weak_stop, customer.reject] * 20]
    call = play(record(), language, replies)
    assert call.end is not None and call.end.outcome is Outcome.declined
    assert call.keys.count("stop_check.decline") == Limits().max_stop_checks == 2
    assert call.keys[-1] == "end.declined"


# --- 4. replies to a read-back -------------------------------------------------------------------


@pytest.mark.parametrize(
    "language, reply",
    [
        (HI, "शायद पचपन हज़ार"),
        (HI, "पचपन"),
        (HE, "not fifty two, fifty five thousand"),
        (HE, "it was 55,000 not 52,000"),
        (HE, "fifty five"),
    ],
)
def test_a_reply_that_names_another_figure_is_never_answered_with_the_same_read_back(language, reply):
    customer = CUSTOMERS[language]
    call = play(record(), language, [*customer.happy()[:READ_BACK], reply])
    assert call.keys[-1] == "read_back.restate"
    call = play(
        record(), language, [*customer.happy()[:READ_BACK], reply, customer.corrected, customer.confirm]
    )
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    assert call.state.premium_of(0) == 55000


@pytest.mark.parametrize("language, reply", [(HI, "शायद"), (HI, "शायद बावन हज़ार"), (HI, "हम्म")])
def test_a_hedge_that_names_no_other_figure_gets_the_read_back_once_more(language, reply):
    call = play(record(), language, [*CUSTOMERS[language].happy()[:READ_BACK], reply])
    assert call.keys[-1] == "read_back.reconfirm"


@pytest.mark.parametrize("language", LANGUAGES)
def test_dont_know_to_a_read_back_is_recorded_and_not_pressed(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, [*customer.happy()[:READ_BACK], customer.dont_know])
    assert call.end is not None and call.end.outcome is Outcome.completed
    assert [key for key in call.keys if key.startswith("read_back")] == ["read_back.confirm"]
    assert [(u.step, u.asks) for u in call.end.unresolved] == [(CallStep.read_back, Question.premium)]
    assert "close.may_call_back" in call.keys


def test_dont_know_beats_the_no_inside_it_when_a_read_back_is_answered():
    assert RULES.interpret("पता नहीं", language=HI, expecting=E.confirmation).intent is Intent.dont_know
    assert RULES.interpret("नहीं, गलत है", language=HI, expecting=E.confirmation).intent is Intent.no


# --- 5. two readings of an amount turn (DESIGN.md section 15, item 16) -------------------------


def test_two_readings_that_agree_are_taken_and_still_read_back():
    customer = CUSTOMERS[HI]
    replies = customer.happy()
    replies[PREMIUM] = ("बावन हज़ार", "52,000")
    call = play(record(), HI, replies)
    state = call.state
    assert call.end.outcome is Outcome.completed and call.keys.count("read_back.confirm") == 1
    assert state.premium_of(0) == 52000
    (other,) = state.second_readings
    assert other.agreed and other.text == "52,000"
    assert state.turns[other.turn_id - 1].text == "बावन हज़ार"


def test_a_figure_only_the_second_reading_holds_goes_to_read_back_and_is_not_asked_again():
    customer = CUSTOMERS[HI]
    replies = customer.happy()
    replies[PREMIUM] = ("bavan hazaar", "52,000")  # the first reading is one the parser refuses
    call = play(record(), HI, replies)
    state, end = call.state, call.end
    assert "premium.reask" not in call.keys and end.outcome is Outcome.completed and end.unresolved == ()
    read_back = next(
        t for t in end.transcript.turns if t.step is CallStep.read_back and t.speaker is Speaker.bot
    )
    assert parse_amount(read_back.text).rupees == 52000
    (other,) = state.second_readings
    assert not other.agreed and other.text == "bavan hazaar"
    # the turn on record is the reading the call acted on, so the rules read the figure the bot read back
    assert end.transcript.turns[other.turn_id - 1].text == "52,000"


def test_readings_that_differ_read_back_the_first_and_offer_the_second_once_it_is_rejected():
    """Prisma v3.0 mis-formats "तीन लाख दो सौ" as 3,02,000 (CLAUDE.md); v2.5 keeps the words."""
    customer = CUSTOMERS[HI]
    replies = customer.happy()[:READ_BACK]
    replies[PREMIUM] = ("3,02,000", "तीन लाख दो सौ")
    replies += [customer.reject, ("3,02,000", "तीन लाख दो सौ"), customer.confirm]
    call = play(record(product(premium_inr=300200)), HI, replies)
    state, end = call.state, call.end
    assert [key for key in call.keys if key.startswith("read_back")] == [
        "read_back.confirm",
        "read_back.restate",
        "read_back.confirm",
    ]
    read_backs = [t for t in end.transcript.turns if t.speaker is Speaker.bot and "यानी" in t.text]
    assert [parse_amount(t.text).rupees for t in read_backs] == [302000, 300200]
    assert end.outcome is Outcome.completed and end.unresolved == () and state.premium_of(0) == 300200
    assert [(r.agreed, r.text) for r in state.second_readings] == [
        (False, "तीन लाख दो सौ"),
        (False, "3,02,000"),
    ]


def test_the_rules_pass_a_premium_that_only_the_second_reading_got_right():
    customer = CUSTOMERS[HI]
    rec = record(product(premium_inr=300200, consent={"method": "signed_form", "at": "2026-10-20"}))
    replies = customer.happy()[:READ_BACK]
    replies[PREMIUM] = ("3,02,000", "तीन लाख दो सौ")
    replies += [customer.reject, ("3,02,000", "तीन लाख दो सौ"), customer.confirm]
    transcript = play(rec, HI, replies).end.transcript
    restated = next(
        t for t in transcript.turns if t.speaker is Speaker.customer and t.text == "तीन लाख दो सौ"
    )
    confirmed = [t for t in transcript.turns if t.speaker is Speaker.customer][-1]
    assert confirmed.step is CallStep.read_back and confirmed.text == customer.confirm
    raw = RawExtraction.model_validate(
        {
            "call_id": transcript.call_id,
            "recall": {"asked": True},
            "products": [
                {
                    "product_id": "P1",
                    "premium": {
                        "status": "stated",
                        "value": "तीन लाख दो सौ",
                        "evidence": {"quote": restated.text, "turn_id": restated.id},
                    },
                    "premium_readback": {
                        "status": "stated",
                        "value": True,
                        "evidence": {"quote": confirmed.text, "turn_id": confirmed.id},
                    },
                }
            ],
        }
    )
    result = evaluate(rec, to_beliefs(raw, rec, transcript))
    assert RuleId.premium in result.products[0].passed


def test_a_plain_yes_to_a_read_back_stands_whatever_the_second_reading_adds():
    customer = CUSTOMERS[HI]
    replies = customer.happy()[:READ_BACK] + [("हाँ, सही है", "हाँ, सही है 5000")]
    call = play(record(), HI, replies)
    assert call.end.outcome is Outcome.completed and call.state.premium_of(0) == 52000


def test_a_second_reading_is_ignored_where_no_figure_is_asked_for():
    state, _ = start(record(), HI, lender_name="Udaharan Bank")
    state, said = step(state, "रॉन्ग नंबर", second_reading="हाँ जी बोल रहा हूँ")
    assert said.outcome is Outcome.wrong_party and state.second_readings == ()


def test_a_state_with_second_readings_survives_a_json_round_trip():
    customer = CUSTOMERS[HI]
    replies = customer.happy()[: PREMIUM + 1]
    replies[PREMIUM] = ("bavan hazaar", "52,000")
    state = play(record(), HI, replies).state
    assert CallState.model_validate_json(state.model_dump_json()) == state


# --- 6. short refusals the word lists missed are at least asked about ---------------------------


@pytest.mark.parametrize(
    "language, reply",
    [
        (HE, "not interested"),
        (HI, "मुझे नहीं बताना"),
        (HI, "मैं नहीं बताऊंगा"),
        (HI, "टाइम नहीं है मेरे पास"),
        (HI, "अभी बात नहीं कर सकता"),
        (HE, "I don't want to answer"),
        (HI, "ठीक है बाय"),
    ],
)
def test_a_short_refusal_gets_the_stop_question_not_the_next_question(language, reply):
    customer = CUSTOMERS[language]
    call = play(record(), language, [*customer.happy()[:FIRST_ANSWER], reply])
    assert call.keys[-1] == "stop_check.decline"
    call = play(record(), language, [*customer.happy()[:FIRST_ANSWER], reply, customer.confirm])
    assert call.end is not None and call.end.outcome is Outcome.declined


# --- 7. wording the lint let through --------------------------------------------------------------

BAD_LINES = [
    ("second_check.ask", "अपने खाते के आख़िरी चार अंक बताइए।", "secret"),
    ("second_check.ask", "अपने अकाउंट के लास्ट चार डिजिट बताइए।", "secret"),
    ("second_check.ask", "Please tell me the last four digits of your account.", "secret"),
    ("second_check.ask", "अपनी जन्म तारीख़ बताइए।", "secret"),
    ("second_check.ask", "आपकी डेट ऑफ बर्थ क्या है?", "secret"),
    ("second_check.ask", "अपना D.O.B. बताइए।", "secret"),
    ("second_check.ask", "कार्ड के नंबर बताइए।", "secret"),
    ("second_check.ask", "अपनी माँ का नाम बताइए।", "secret"),
    ("close.may_call_back", "आपका पैसा लौटा दिया जाएगा।", "promise of money back"),
    ("close.may_call_back", "पैसा वापस आ जाएगा।", "promise of money back"),
    ("cancel_window.ask", "आपको कैंसल करने का अधिकार है।", "states a right"),
    ("cancel_window.ask", "You have the right to cancel.", "states a right"),
    ("kind.ask", "यह क्रेडिट लाइफ़ है?", "names or explains the product"),
    ("close.thanks", "हमारा नया प्लान लीजिए।", "offer"),
    ("close.thanks", "यह आपके लिए फ़ायदेमंद है, रुकिए।", "offer"),
    ("close.thanks", "This has guaranteed benefits.", "offer"),
    ("close.thanks", "आपकी शिकायत दर्ज कर दी गई है।", "finding"),
]


@pytest.mark.parametrize("key, text, problem", BAD_LINES)
def test_the_lint_rejects_what_the_review_slipped_past_it(key, text, problem):
    problems = lint_line(key, text)
    assert any(problem in found for found in problems), problems
