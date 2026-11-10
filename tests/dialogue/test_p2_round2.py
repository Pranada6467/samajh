"""Call v2, round 2 (after the iteration-2 verifier): structure, not more word lists.

Rules only unless a fake classifier is passed. Sentences are LLM-written text, not speech.
"""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, play, product, record

from samajh.amounts import parse_amount
from samajh.dialogue import Expecting, Outcome, expecting, step
from samajh.dialogue.machine import AtReadBack, AtSayAgain, AtTeachBack
from samajh.types import Language, LoanRecord, Question

HI, HE = Language.hi, Language.hi_en
OPEN = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984"]


# --- 1 and 8: asymmetric defaults at the opening ----------------------------------------------


@pytest.mark.parametrize(
    "replies",
    [
        ["साहब मीटिंग में हैं"],
        ["वो गाड़ी चला रहे हैं, बाद में कॉल करना"],
        ["हाँ जी, बोल रहा हूँ", "हाँ", "पति का 1984"],
    ],
)
def test_someone_describing_the_borrower_is_a_third_party_not_a_call_back(replies):
    call = play(record(), HI, replies)
    assert call.end.outcome is Outcome.wrong_party and call.keys[-1] == "end.third_party"


@pytest.mark.parametrize(
    "year_reply", ["हमारे ये तो चौरासी के हैं", "उन्नीस सौ चौरासी, क्यों?", "जी अपना तो 1984 का है"]
)
def test_a_year_among_other_words_never_passes_without_the_classifier(year_reply):
    call = play(record(), HI, [*OPEN[:2], year_reply])
    assert call.keys[-1] == "second_check.reask" and "context.loan" not in call.keys


def test_nothing_before_a_claim_names_the_lender_or_the_loan():
    for replies in (["कौन बोल रहा है?", "किस बारे में है?", "जी"], ["हेलो", "हाँ बोलिए"]):
        call = play(record(), HI, replies)
        said = " ".join(line.text for line in call.lines)
        assert "Udaharan" not in said and "लोन" not in said


def test_the_year_question_carries_one_short_line_on_checking_the_call():
    call = play(record(), HI, OPEN[:2])
    assert [line.key for line in call.utterances[-1].lines] == [
        "disclosure.never_ask", "verify.short", "second_check.ask",
    ]  # fmt: skip


# --- 4: what open recall already answered is not asked again -------------------------------------


def test_a_figure_given_in_open_recall_is_read_back_instead_of_asked_again():
    call = play(record(), HI, [*OPEN, "हाँ, एक बीमा लिया था, बावन हज़ार का", "बीमा है"])
    assert "premium.ask" not in call.keys and call.keys[-1] == "read_back.confirm"
    assert parse_amount(call.lines[-1].text).rupees == 52000
    (carried,) = call.state.carried_forward
    assert carried.question is Question.premium and carried.product_id == "P1"
    recall_turn = call.state.turns[carried.turn_id - 1]
    assert "बावन हज़ार" in recall_turn.text
    after = play(record(), HI, [*OPEN, "हाँ, एक बीमा लिया था, बावन हज़ार का", "बीमा है", "हाँ सही है"])
    assert after.keys[-1] == "payment_source.ask"


def test_a_recall_figure_that_is_wrong_is_corrected_at_the_read_back():
    call = play(record(), HI, [*OPEN, "बावन हज़ार का कुछ लिया था", "पता नहीं", "नहीं, पचपन हज़ार", "हाँ"])
    assert call.state.premium_of(0) == 55000 and call.keys[-1] == "payment_source.ask"


# --- 5: amount turns ---------------------------------------------------------------------------


def at_cover(language=HI):
    call = play(
        record(),
        language,
        [*OPEN, "एक एफडी ली थी", "एफडी", "बावन हज़ार", "हाँ", "लोन से", "एक बार", "मेरी मर्ज़ी थी"],
    )
    assert isinstance(call.state.position, AtTeachBack) and call.state.position.question is Question.cover
    return call.state


def test_the_cover_question_takes_two_readings_like_the_premium():
    state = at_cover()
    assert expecting(state.position) is Expecting.amount  # so the phone fetches the second reading
    state, said = step(state, "पाँच लाख तक", second_reading="पचास लाख तक")
    assert isinstance(state.position, AtSayAgain) and said.lines[-1].key == "cover.say_again"
    assert said.lines[-1].asks is Question.cover
    state, said = step(state, "पाँच लाख", second_reading="5,00,000")
    assert isinstance(state.position, AtReadBack) and state.position.item == "cover"


def test_an_ambiguous_figure_is_never_read_back():
    _state, said = step(
        play(record(), HI, [*OPEN, "एक एफडी ली थी", "एफडी"]).state, "बावन हज़ार दिए, पाँच लाख का कवर है"
    )
    assert said.lines[-1].key == "premium.reask"


def test_read_backs_say_the_figure_once_in_words():
    call = play(record(), HI, [*OPEN, "एक एफडी ली थी", "एफडी", "बावन हज़ार"])
    line = call.lines[-1]
    assert line.key == "read_back.confirm" and not any(ch.isdigit() for ch in line.text)


# --- 6: the record's product count --------------------------------------------------------------


def records() -> list[LoanRecord]:
    zero = record().model_copy(update={"products": ()})
    return [
        zero,
        record(product("P1")),
        record(product("P1"), product("P2")),
        record(*[product(f"P{k}") for k in (1, 2, 3)]),
    ]


NAMED_NOTHING = [
    [*OPEN, "कुछ नहीं लिया"],
    [*OPEN, "कुछ नहीं लिया", "नहीं"],
    [*OPEN, "हम्म", "क्या?"],
    [*OPEN, "हम्म", "क्या?", "हम्म"],
    [*OPEN, "पता नहीं", "नहीं, कुछ याद नहीं"],
    ["हाँ जी, बोल रहा हूँ", "आप कौन?", "हाँ", "1984", "कुछ नहीं"],
]


@pytest.mark.parametrize("script", NAMED_NOTHING)
def test_a_customer_who_named_nothing_hears_the_same_whatever_the_product_count(script):
    heard = [[line.text for line in play(rec, HI, script).lines] for rec in records()]
    assert all(lines == heard[0] for lines in heard[1:])
    assert not any("हमारे रिकॉर्ड" in text for text in heard[2])


def test_the_count_shows_only_after_the_customer_named_something_or_the_follow_up_was_answered():
    """What a listener can infer: nothing about the count before naming something or answering the
    follow-up. After that, "the first thing on our record" says there are two or more, the plain
    intro says one, and going straight to consent says none."""
    named = [*OPEN, "एक एफडी ली थी"]
    first = [play(rec, HI, named).utterances[-1].lines[0].key for rec in records()]
    assert first == ["consent.ask", "teach_back.intro", "teach_back.intro_nth", "teach_back.intro_nth"]


def test_two_products_sound_alike_until_the_first_product_is_done():
    script = [*OPEN, "एक एफडी ली थी", "एफडी", "पता नहीं"]
    a = [line.text for line in play(record(product("P1"), product("P2")), HI, script).lines]
    b = [line.text for line in play(record(*[product(f"P{k}") for k in (1, 2, 3)]), HI, script).lines]
    assert a == b


@pytest.mark.parametrize("language", [HI, HE])
def test_an_informed_call_still_ends_completed(language):
    call = play(record(), language, CUSTOMERS[language].happy())
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
