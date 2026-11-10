"""`parse_approx_amount`: a hedged amount or a narrow range is read; a correction is not."""

import pytest

from samajh.amounts import (
    AmbiguityReason,
    Ambiguous,
    Approximate,
    NoAmount,
    Parsed,
    parse_amount,
    parse_approx_amount,
)

HEDGED = [
    ("करीब पचास हज़ार", 50_000),
    ("लगभग 50,000", 50_000),
    ("शायद बावन हज़ार", 52_000),
    ("पचास हज़ार के आसपास", 50_000),
    ("लगता है बावन हज़ार था", 52_000),
    ("maybe 52,000", 52_000),
    ("I think it was around fifty thousand", 50_000),
    ("shayad 52,000", 52_000),
    ("kareeb 50 hazaar", 50_000),
    ("करीब लाख रुपये", 100_000),
]
RANGES = [
    ("पचास बावन हज़ार के आसपास", 50_000, 52_000),
    ("50-52 हज़ार", 50_000, 52_000),
    ("पचास से बावन हज़ार", 50_000, 52_000),
    ("50,000 से 52,000", 50_000, 52_000),
    ("50 to 52 thousand", 50_000, 52_000),
    ("बावन या पचपन हज़ार", 52_000, 55_000),
    ("50-52 hazaar", 50_000, 52_000),  # digits and a romanised unit word read
    ("पचास हज़ार से बावन हज़ार तक", 50_000, 52_000),
    ("शायद पचास से बावन हज़ार रुपये", 50_000, 52_000),
    ("एक से डेढ़ लाख", 100_000, 150_000),
    ("एक दो लाख", 100_000, 200_000),
    ("एक लाख से एक लाख बीस हज़ार", 100_000, 120_000),
    # the judge's ordinary customer: a negator in another clause does not touch the range
    ("ठीक से याद नहीं, पचास बावन हज़ार के आसपास था", 50_000, 52_000),
    ("पता नहीं ठीक से, पचास से बावन हज़ार", 50_000, 52_000),
]
STAYS_AMBIGUOUS = [
    "बावन नहीं पचपन हज़ार",
    "पचास हज़ार नहीं था",
    "पचास हज़ार से कम",
    "बावन हज़ार था, नहीं पचपन",
    "पचास से बावन हज़ार नहीं था",
    "याद नहीं पचास से बावन हज़ार",  # same clause: the negator may be about the amount
    "पचास से बावन हज़ार, नहीं पचपन",
    "less than 50,000",
    "पचास या बावन या पचपन हज़ार",  # three ends
    "पचास बावन पचपन हज़ार",
    "दो से पांच लाख",  # high is more than twice low
    "बावन से पचास हज़ार",  # not low to high
    "पचास से पचास हज़ार",
    "नब्बे हज़ार से एक लाख",  # the ends do not share a unit
    "50,000 से पचपन हज़ार",
    "पचास और बावन हज़ार",  # "and" may be a sum
    "पचास हज़ार, बावन हज़ार",  # a restart, not a range
    "पचास हज़ार बावन हज़ार",
    "पचास से बावन हज़ार, या साठ हज़ार",
    "पचास से बावन हज़ार, मतलब 51,000",
    "pachas se bavan hazaar",  # romanised number words are out of scope
    "सॉरी, बावन हज़ार",  # a correction word is not a hedge
    "करीब सारे तीन लाख",
    "करीब पचास",
]


@pytest.mark.parametrize(("text", "rupees"), HEDGED)
def test_a_hedged_amount_is_approximate_with_equal_ends(text, rupees):
    result = parse_approx_amount(text)
    assert isinstance(result, Approximate), result
    assert (result.low, result.high) == (rupees, rupees)
    assert text[result.span.start : result.span.end] == result.span.text


@pytest.mark.parametrize(("text", "low", "high"), RANGES)
def test_a_narrow_range_is_approximate(text, low, high):
    result = parse_approx_amount(text)
    assert isinstance(result, Approximate), result
    assert (result.low, result.high) == (low, high)
    assert text[result.span.start : result.span.end] == result.span.text


@pytest.mark.parametrize("text", STAYS_AMBIGUOUS)
def test_corrections_comparisons_and_wide_ranges_stay_ambiguous(text):
    assert isinstance(parse_approx_amount(text), Ambiguous), parse_approx_amount(text)


@pytest.mark.parametrize("text", [t for t, *_ in RANGES] + ["शायद बावन हज़ार", "maybe 52,000"])
def test_parse_amount_still_refuses_what_only_the_approximate_reader_reads(text):
    assert isinstance(parse_amount(text), Ambiguous), parse_amount(text)


@pytest.mark.parametrize(
    "text",
    ["एक लाख बीस हज़ार", "बावन हज़ार रुपये", "₹52,000", "मैंने तीन लाख दिए", "पचास हज़ार एक बार", "5,00,000 दो सौ"],
)
def test_a_plain_amount_is_exactly_what_parse_amount_returns(text):
    plain = parse_amount(text)
    assert isinstance(plain, Parsed)
    assert parse_approx_amount(text) == plain


def test_no_number_is_no_amount():
    assert isinstance(parse_approx_amount("पता नहीं शायद"), NoAmount)


def test_the_read_back_line_for_a_range_reads_as_that_range():
    line = "आपने बताया था पचास से बावन हज़ार, यानी 50,000 से 52,000। क्या यह सही है?"
    result = parse_approx_amount(line)
    assert isinstance(result, Approximate), result
    assert (result.low, result.high) == (50_000, 52_000)


def test_the_read_back_line_for_one_figure_reads_as_parsed():
    line = "आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?"
    result = parse_approx_amount(line)
    assert isinstance(result, Parsed), result
    assert result.rupees == 52_000


def test_a_read_back_line_whose_two_forms_differ_is_ambiguous():
    line = "आपने बताया था पचास से बावन हज़ार, यानी 50,000 से 55,000। क्या यह सही है?"
    assert isinstance(parse_approx_amount(line), Ambiguous)


@pytest.mark.parametrize(
    ("text", "low", "high"),
    [
        ("करीब पचास हज़ार रुपये।", 50_000, 50_000),
        ("शायद ₹52,000", 52_000, 52_000),
        ("पचास हज़ार के आसपास", 50_000, 50_000),
        ("पचास से बावन हज़ार", 50_000, 52_000),
        ("लगभग 50-52 हज़ार रुपये", 50_000, 52_000),
        ("पचास हज़ार से लेकर बावन हज़ार तक", 50_000, 52_000),
        ("I think around 50,000", 50_000, 50_000),
    ],
)
def test_exact_accepts_hedges_connectors_and_currency_around_the_amount(text, low, high):
    result = parse_approx_amount(text, exact=True)
    assert isinstance(result, Approximate), result
    assert (result.low, result.high) == (low, high)


def test_exact_plain_amount_is_parsed():
    assert parse_approx_amount("बावन हज़ार रुपये", exact=True) == parse_amount("बावन हज़ार रुपये", exact=True)


@pytest.mark.parametrize(
    "text",
    [
        "करीब पचास हज़ार दिए थे",
        "पक्का पचास से बावन हज़ार",
        "आपने बताया था पचास से बावन हज़ार, यानी 50,000 से 52,000। क्या यह सही है?",
        "premium करीब पचास हज़ार",
    ],
)
def test_exact_refuses_any_other_word(text):
    result = parse_approx_amount(text, exact=True)
    assert isinstance(result, Ambiguous), result
    assert result.reason is AmbiguityReason.malformed
