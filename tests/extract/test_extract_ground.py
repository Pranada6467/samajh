"""Resolving what the model points at: clause numbers and copied spans."""

import pytest

from samajh.extract._ground import Reply, comparison_form, days, months, rupees, tighten
from samajh.rules.normalise import _norm

REPLY = "नहीं, यह तो बीमा है, इसका पैसा वापस नहीं आता।"


@pytest.mark.parametrize(
    "text",
    [
        REPLY,
        "Insurance है, loan protection वाला. 12,500 rupees!",
        "ஆமா, 30 நாள் உள்ள ரத்து பண்ணலாம்னு சொன்னாங்க.",
        "ವಿಮೆಗೆ ಒಪ್ಪಿದ್ದೆ, ಮೊಬೈಲ್‌ಗೆ ಬಂದ OTP ಕೊಟ್ಟೆ.",
        "क्या-क्या?  ₹52,000 रुपये… “हाँ”",
        "ＦＤ  है\tना\nहाँ",
    ],
)
def test_comparison_form_is_the_rule_engines(text):
    assert comparison_form(text) == _norm(text)


def test_a_found_span_is_returned_in_the_replys_own_words():
    found = Reply(REPLY).find("इसका  पैसा वापस नहीं आता")
    assert found.words == "इसका पैसा वापस नहीं आता"
    assert found.clauses == "इसका पैसा वापस नहीं आता"


def test_a_span_inside_a_clause_is_widened_to_the_whole_clause():
    found = Reply("यह बीमा नहीं है, एफ़डी है।").find("यह बीमा")
    assert found.words == "यह बीमा"
    assert found.clauses == "यह बीमा नहीं है"  # the negation cannot be cut off


def test_a_span_across_clauses_covers_each_clause_it_touches():
    assert Reply(REPLY).find("बीमा है, इसका पैसा").clauses == "यह तो बीमा है, इसका पैसा वापस नहीं आता"


@pytest.mark.parametrize(
    "span",
    [
        "नहीं, इसका पैसा वापस नहीं आता",  # two parts joined across a clause the model skipped
        "पैसा नहीं वापस आता",  # reordered
        "बीम",  # part of a word
        "बीमा है इसका पैसा वापस आता",  # a word dropped
        "यह तो FD है",  # not said
        "No, this is insurance",  # translated
        "",
        "   ",
        "।,!",
        None,
    ],
)
def test_a_span_that_is_not_a_run_of_whole_words_is_not_found(span):
    assert Reply(REPLY).find(span) is None


def test_case_punctuation_and_unicode_form_do_not_hide_a_real_span():
    reply = Reply("Insurance है, Loan Protection वाला.")
    assert reply.find("insurance है").words == "Insurance है"
    assert reply.find("loan protection वाला!").words == "Loan Protection वाला"
    decomposed = "क़"  # क + nukta, the decomposed form of क़
    assert Reply("क़ीमत ज़्यादा थी").find(f"{decomposed}ीमत").words == "क़ीमत"


def test_clauses_are_numbered_from_one_and_skip_empty_ones():
    reply = Reply("कवर? ... कवर का मुझे नहीं पता।")
    assert reply.clauses() == ("कवर", "कवर का मुझे नहीं पता")
    assert reply.cover((2,)) == "कवर का मुझे नहीं पता"
    assert reply.cover((1, 2)) == "कवर? ... कवर का मुझे नहीं पता"


def test_clause_numbers_that_are_apart_cover_everything_between_them():
    assert Reply(REPLY).cover((3, 1)) == "नहीं, यह तो बीमा है, इसका पैसा वापस नहीं आता"


@pytest.mark.parametrize("numbers", [(), (0,), (4,), (1, 9), (-1,)])
def test_a_missing_or_out_of_range_clause_number_resolves_to_nothing(numbers):
    assert Reply(REPLY).cover(numbers) is None


def test_digit_grouping_does_not_split_a_clause():
    assert Reply("5,00,000 का कवर है, बस।").clauses() == ("5,00,000 का कवर है", "बस")


@pytest.mark.parametrize("text", ["", "   ", "...", "।", "—"])
def test_a_reply_with_no_word_is_blank(text):
    assert Reply(text).blank


@pytest.mark.parametrize(
    "words, read, tight",
    [
        ("बावन हज़ार कटे थे", rupees, "बावन हज़ार"),
        ("करीब 52,000 rupees", rupees, "52,000 rupees"),
        ("बावन हज़ार", rupees, "बावन हज़ार"),
        ("पाँच साल के लिए", months, "पाँच साल"),
        ("30 நாள் உள்ள", days, "30 நாள்"),
        ("कटे थे", rupees, "कटे थे"),  # no number: left for the engine to refuse
        ("पचास या बावन हज़ार", rupees, "पचास या बावन हज़ार"),  # two amounts: never narrowed to one
    ],
)
def test_tighten_keeps_only_the_number_and_never_picks_between_two(words, read, tight):
    assert tighten(words, read) == tight
