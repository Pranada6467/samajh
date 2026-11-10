"""P3a fix round 3: bounds, an unexplained number beside the amount, "one" after a round amount,
and ordinary words before a number that the misspelt-fraction check used to refuse.

The safe direction is always a refusal: a bound, a count or a stray number beside an amount must
never come back as a confident figure. The negative controls are ordinary sentences that must
keep parsing. Hindi, Hinglish and English; typed text only.
"""

import pytest

from samajh.amounts import (
    Ambiguous,
    Approximate,
    Parsed,
    parse_amount,
    parse_approx_amount,
    parse_duration_months,
)


def _refused(text: str) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Ambiguous), f"{parse.__name__}({text!r}) -> {result}"


def _reads(text: str, rupees: int) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Parsed) and result.rupees == rupees, f"{parse.__name__}({text!r}) -> {result}"


# --- 1. a lower or upper bound is not the figure -------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "कम से कम पचास हज़ार",
        "कम-से-कम 50,000 रुपये",
        "ज़्यादा से ज़्यादा दो लाख",
        "अधिक से अधिक एक लाख कटे",
        "कम से कम पचास हज़ार तो दिए थे",
        "पचास हज़ार कम से कम",
        "न्यूनतम पचास हज़ार",
        "अधिकतम दो लाख रुपये",
        "मिनिमम 50,000",
        "kam se kam 50,000",
        "kam se kam pachaas hazaar",
        "zyada se zyada 2 lakh",
        "jyada se jyada 2 lakh rupaye",
        "at least 50,000",
        "at least fifty thousand rupees",
        "at most 2 lakh",
        "minimum 50 thousand",
        "maximum 2 lakh",
        "more than 50,000",
        "less than fifty thousand",
        "50,000 se zyada",
        "पचास हज़ार से ज़्यादा",
        "पचास हज़ार से ऊपर",
        "शायद कम से कम पचास हज़ार",  # a doubt word must not turn a bound into Approximate(50000, 50000)
        "लगभग at least 50,000",
    ],
)
def test_a_bound_is_refused_never_the_plain_figure(text):
    _refused(text)


def test_a_bound_never_becomes_an_approximate_point():
    assert not isinstance(parse_approx_amount("करीब कम से कम पचास हज़ार"), Approximate | Parsed)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("तीन लाख तक", 300_000),  # decided: "up to" reads as the figure
        ("कम पैसे नहीं थे। पचास हज़ार दिए", 50_000),  # the comparison is in another clause
        ("मैंने पचास हज़ार दिए", 50_000),
    ],
)
def test_ordinary_sentences_near_bounds_still_read(text, rupees):
    _reads(text, rupees)


# --- 2. an unexplained number in the same clause as the amount -----------------------------


@pytest.mark.parametrize(
    "text",
    [
        "पचास हज़ार दो बार कटे",
        "दो एफडी पचास हज़ार की",
        "तीन लक पचास हज़ार",
        "दो बार पचास हज़ार कटे",
        "तीन किस्तें 50,000 की",
        "मेरी दो पॉलिसी हैं पचास हज़ार वाली",
        "2 FD 50,000 ki",
        "do teen baar 50,000 kate the",  # "teen" is a romanised number word: refused by itself
        "three policies of 50,000 each",
        "पांच तारीख को पचास हज़ार कटे",  # a date is a number the parse cannot explain
        "तीन लख पचास हज़ार",
        "चार लाक पचास हज़ार रुपये",
        "पचास हज़ार यानी पचास",
    ],
)
def test_a_number_the_parse_cannot_explain_makes_the_turn_ambiguous(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        # a duration binds its number
        ("दो साल के लिए पचास हज़ार", 50_000),
        ("24 महीने के लिए 50,000 रुपये", 50_000),
        ("पचास हज़ार दो साल के लिए", 50_000),
        ("पचास हज़ार एक साल का", 50_000),
        ("for 3 years, fifty thousand rupees", 50_000),
        ("5 saal ke liye 2 lakh", 200_000),
        # a percent binds its number
        ("10% पर पचास हज़ार", 50_000),
        # "one" as an article or "once" counts nothing
        ("एक बीमा पचास हज़ार का", 50_000),
        ("एक बार पचास हज़ार कटे", 50_000),
        ("one policy of fifty thousand", 50_000),
        ("पचास हज़ार रुपये एक बार देना है", 50_000),
        # a number in another clause
        ("दो बातें हैं। पचास हज़ार दिए", 50_000),
        # digits and Hinglish
        ("Maine 50,000 rupees diye the", 50_000),
        ("50 hazaar diye the", 50_000),
        ("₹50,000 कटे", 50_000),
        ("इकतालीस हज़ार तीन सौ एक", 41_301),
    ],
)
def test_numbers_the_parse_explains_leave_the_amount(text, rupees):
    _reads(text, rupees)


def test_a_duration_after_a_round_amount_is_still_read_as_the_duration():
    assert parse_duration_months("पचास हज़ार दो साल के लिए") == 24
    assert parse_duration_months("दो साल के लिए") == 24


# --- 3. a small number after a round amount ------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "पचास हज़ार एक जमा किए",
        "पचास हज़ार एक चुकाए",
        "पचास हज़ार एक पे किए",
        "पचास हज़ार एक भर दिए",
        "पचास हज़ार एक निकले",
        "पचास हज़ार एक बार",
        "पचास हज़ार एक पॉलिसी के",
        "पचास हज़ार एक FD में",
        "पचास हज़ार एक ही बार कटा",
        "एक लाख एक दिया",
        "दो लाख एक बीमा के लिए",
        "fifty thousand one was deducted",
        "50 thousand one gave",
        "fifty thousand one policy",
        "50 हज़ार एक दिए",
        "50 हज़ार 1 कटा",
        # other small numbers: a count or a units digit, never read as either
        "पचास हज़ार दो एफडी",
        "fifty thousand two FDs",
        "एक लाख बीस दिए",
        "पचास हज़ार दो नहीं",
        "पचास हज़ार एक का बीमा",  # "one" may be the article even before a postposition
        "पचास हज़ार दो पॉलिसी में",
    ],
)
def test_a_small_number_after_a_round_amount_and_before_a_word_is_refused(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("पचास हज़ार एक", 50_001),  # nothing after it: how 50,001 is said
        ("पचास हज़ार एक रुपये", 50_001),
        ("पचास हज़ार एक रुपया दिया", 50_001),
        ("fifty thousand one rupees", 50_001),
        ("पचास हज़ार एक सौ", 50_100),
        ("दो लाख एक हज़ार", 201_000),
        ("तीन सौ एक दिए", 301),
        ("नौ सौ एक लगे थे", 901),
        ("इकतालीस हज़ार तीन सौ एक दिए", 41_301),
        ("ग्यारह सौ एक जमा किए", 1_101),
        ("पचास हज़ार रुपये एक बार", 50_000),
        # a postposition closes an amount whose last number is not "one"
        ("हर महीने किस्त उन्नीस हज़ार अस्सी की है", 19_080),
        ("EMI six thousand thirty ki hai", 6_030),
        ("बीस हज़ार पचास का प्रीमियम", 20_050),
    ],
)
def test_one_that_is_part_of_the_number_or_closed_off_still_reads(text, rupees):
    _reads(text, rupees)


# --- 4. ordinary words directly before a number --------------------------------------------


@pytest.mark.parametrize(
    "word",
    [
        "Maine", "maine", "mane", "mene", "mainne", "humne", "usne", "unhone", "unhe", "inhe",
        "mera", "meri", "mere", "sirf", "sir", "pura", "poora", "pure", "poore", "paise", "paisa",
        "bade", "bada", "arre", "are", "suna", "sahi", "pakka", "pata", "dono", "teeno", "thoda",
        "karib", "around", "gave", "मैंने", "उन्होंने", "सिर्फ़", "पूरे", "रहा", "रहे", "भाई",
    ],
)  # fmt: skip
def test_an_ordinary_word_before_a_number_does_not_block_it(word):
    for tail, rupees in ((" 50,000 rupees diye the", 50_000), (" 50 हज़ार दिए", 50_000), (" दो लाख", 200_000)):
        result = parse_amount(word + tail)
        assert isinstance(result, Parsed) and result.rupees == rupees, f"{word + tail!r} -> {result}"


@pytest.mark.parametrize(
    "text",
    [
        # a word that may be the fraction misspelt stays refused
        "sare 3 lakh",
        "saare 3 lakh",
        "सारे तीन लाख",
        "सारा तीन लाख कटा",
        "pone 2 lakh",
        "pauney 2 lakh",
        "sawaa 2 lakh",
        "सवाह दो लाख",
        "देड लाख",
        "देड 1,00,000",
        "ded 1,00,000",
        "dhai lakh",
        "adha lakh",
        "लख पचास हज़ार",
    ],
)
def test_a_word_that_may_be_a_misspelt_fraction_or_unit_is_still_refused(text):
    _refused(text)


# --- round 3b: romanised duration units, and the rule across the whole text --------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("Maine 2 saal pehle 50,000 rupees pay kiya", 50_000),
        ("premium 50,000 tha 2 saal ka", 50_000),
        ("3 saal ke liye 52,000", 52_000),
        ("har 6 mahine 25,000 rupees", 25_000),
        ("15 din pehle 50,000 kate", 50_000),
        ("2 hafte mein 40,000 diye", 40_000),
        ("50,000 rupees 12 mahino ke liye", 50_000),
        ("12% interest pe 2 lakh", 200_000),
        ("ek policy 50,000 ki", 50_000),
        ("पचास हज़ार दिए, दो साल पहले", 50_000),
        ("दो साल पहले लोन लिया। पचास हज़ार दिए", 50_000),
    ],
)
def test_a_number_bound_to_a_romanised_duration_is_explained(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    ("text", "months"),
    [("3 saal", 36), ("2 mahine", 2), ("1 mahina", 1), ("5 sal", 60), ("2 saal 6 mahine", 30)],
)
def test_romanised_durations_read_as_months(text, months):
    assert parse_duration_months(text) == months


def test_romanised_days_read():
    from samajh.amounts import parse_duration_days

    assert parse_duration_days("15 din") == 15
    assert parse_duration_days("2 hafte") == 14


@pytest.mark.parametrize(
    "text",
    ["50,000 rupees 2 baar kate", "2 policy 50,000 ki", "5 tareekh ko 50,000 kate", "3 kist mein 50,000", "2 baar 50,000 kate"],
)
def test_a_count_beside_a_digit_amount_in_hinglish_stays_refused(text):
    _refused(text)


# --- round 3c: a number touching the amount across a clause break; "तीन लक" anywhere ------


@pytest.mark.parametrize(
    "text",
    [
        "पचास हज़ार, दो बार कटे",
        "पचास हज़ार रुपये, दो बार",
        "₹50,000, 2 बार",
        "पचास हज़ार, दो",
        "fifty thousand rupees, two times",
        "50,000, 2 baar",
        "2, ₹50,000",
        "तीन लक, पचास हज़ार",
        "तीन लक। पचास हज़ार दिए",
        "पचास हज़ार दिए। तीन लक",
        "दो लक, 50,000 रुपये",
    ],
)
def test_a_number_touching_the_amount_across_a_break_or_a_misheard_unit_anywhere_refuses(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("दो तीन बार बताया, बावन हज़ार कटे", 52_000),
        ("2 bachche hain, 50,000 diye", 50_000),
        ("50,000 diye. 2 log the", 50_000),
        ("दो बातें हैं। पचास हज़ार दिए", 50_000),
        ("EMI 5,000 hai, 24 kist", 5_000),
        ("पचास हज़ार दिए, दो साल पहले", 50_000),
        ("पचास हज़ार, दो साल के लिए", 50_000),
        ("पचास हज़ार रुपये, एक बार", 50_000),
        ("पचास हज़ार, यानी पचास हज़ार", 50_000),
        ("12%, 2 lakh", 200_000),
        ("दो लोग थे, पचास हज़ार दिए", 50_000),
    ],
)
def test_a_number_in_another_clause_that_does_not_touch_the_amount_is_ignored(text, rupees):
    _reads(text, rupees)
