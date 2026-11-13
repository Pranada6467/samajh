"""Iteration 3 amount fixes (references/reviews/iter2/verify-P3a-r3.md, "Amounts" and failure 3).

1. An apology refuses only before a number (a correction, "X sorry Y"); otherwise the parser
   ignores it (round 2: the extractor's change check judges a bare "X sorry").
2. "तक", "tak", "up to", "upto", "till", "within", "के अंदर" beside an amount: the figure is read
   and marked `bound` (round 2). The rules accept a bound cover and refuse a bound premium
   (tests/core/test_amounts_bound_rules.py).
3. A count beside the amount ("do baar", "twice") refuses it.
4. Romanised Hindi number words are read; the ones that are also everyday words ("do", "das",
   "saath", "bara", "tera") count only inside a number phrase.

The safe direction is a refusal. Typed text only; no speech, no real callers.
"""

import pytest

from samajh.amounts import (
    Ambiguous,
    NoAmount,
    Parsed,
    parse_amount,
    parse_approx_amount,
    parse_duration_months,
)


def _reads(text: str, rupees: int) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Parsed) and result.rupees == rupees, f"{parse.__name__}({text!r}) -> {result}"


def _refused(text: str) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Ambiguous), f"{parse.__name__}({text!r}) -> {result}"


def _no_amount(text: str) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert not isinstance(result, Parsed), f"{parse.__name__}({text!r}) -> {result}"


# --- 1. an apology about the line --------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("जी, इकतालीस हज़ार तीन सौ रुपये, सॉरी, नेटवर्क चला गया था।", 41_300),
        ("matlab, iktalis hazaar teen sau rupaye, sorry line pe disturbance hai.", 41_300),
        ("तीस हज़ार रुपये दिए थे, सॉरी, आवाज़ कट रही है।", 30_000),
        ("sattar hazaar rupaye, sorry, aawaz nahi aa rahi thi.", 70_000),
        ("₹64,000. Sorry, I was driving.", 64_000),
        ("अट्ठाईस हज़ार। सोरी, फ़ोन गिर गया था।", 28_000),
        ("जी 41300 रुपये सॉरी नेटवर्क चला गया था", 41_300),  # v2.5 style: no punctuation
        ("41300 sorry line kat gayi thi", 41_300),
        ("पैंतीस हज़ार सॉरी", 35_000),
        ("haan 27,500 sorry awaaz toot rahi hai", 27_500),
    ],
)
def test_an_apology_after_every_number_in_its_own_clause_is_not_doubt(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    "text",
    [
        "इकतालीस हज़ार, सॉरी, बयालीस हज़ार",  # a correction to another full amount
        "पैंतीस हज़ार, सॉरी, छत्तीस",  # a correction to a bare number
        "thirty thousand, sorry, thirty two thousand",
        "sorry 64,000 nahi",
        "सॉरी, सुनाई नहीं दिया। पैंतीस हज़ार।",  # a number follows the apology
        "64,000 sorry, 46,000",
        "41300 sorry 42300",  # unpunctuated correction
        "इकतालीस हज़ार सॉरी बयालीस हज़ार",
    ],
)
def test_an_apology_before_a_number_still_refuses(text):
    _refused(text)


def test_shayad_and_maybe_stay_doubt_anywhere():
    assert not isinstance(parse_amount("पैंतीस हज़ार, नेटवर्क खराब है, शायद।"), Parsed)
    assert not isinstance(parse_amount("64,000, the line is bad, maybe."), Parsed)


def test_an_apology_does_not_turn_a_corrected_duration_into_one():
    assert parse_duration_months("3 साल, सॉरी, 4 साल") is None
    assert parse_duration_months("3 साल, सॉरी, आवाज़ नहीं आई") == 36


# --- 2. a bound is read and marked ------------------------------------------------------


def _bound(text: str, rupees: int) -> None:
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Parsed) and (result.rupees, result.bound) == (rupees, True), (
            f"{parse.__name__}({text!r}) -> {result}"
        )


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("पचास हज़ार तक।", 50_000),
        ("up to 40,000 rupees.", 40_000),
        ("साठ हज़ार रुपये तक दिए", 60_000),
        ("60 hazaar tak", 60_000),
        ("60 hazaar rupaye tak kata", 60_000),
        ("upto 75,000", 75_000),
        ("up to seventy five thousand", 75_000),
        ("till 30,000", 30_000),
        ("within 40,000", 40_000),
        ("चालीस हज़ार के अंदर", 40_000),
        ("chalis hazaar ke andar", 40_000),
        ("साठ हज़ार तक ही", 60_000),
        ("Rs 30,000 tak", 30_000),
        ("तीन लाख तक का कवर है", 300_000),  # no attributive exemption: always marked
        ("चालीस हज़ार तक का था", 40_000),
        ("chalis hazaar tak ka tha", 40_000),
        ("40000 tak ki premium thi", 40_000),
        ("साढ़े तीन लाख तक मिलता है", 350_000),
    ],
)
def test_a_bound_reads_the_ceiling_and_is_marked(text, rupees):
    _bound(text, rupees)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("अब तक साठ हज़ार कट चुके हैं।", 60_000),  # "so far", not beside the amount
        ("साठ हज़ार अब तक कटे", 60_000),
        ("I am up. 30,000 it was.", 30_000),  # "up" not followed by "to"
        ("कल तक बताया था, साठ हज़ार", 60_000),
        ("पचास हज़ार दिए थे", 50_000),
        ("पाँच साल के लिए साठ हज़ार", 60_000),
    ],
)
def test_an_amount_that_is_not_a_bound_is_not_marked(text, rupees):
    _reads(text, rupees)
    assert parse_amount(text).bound is False


def test_a_hedged_bound_stays_marked_when_approximate():
    result = parse_approx_amount("करीब पचास हज़ार तक")
    assert (result.status, result.low, result.bound) == ("approximate", 50_000, True)


def test_a_bound_marker_leaves_old_dumps_unchanged():
    assert "bound" not in parse_amount("पचास हज़ार").model_dump()
    assert parse_amount("पचास हज़ार तक").model_dump()["bound"] is True


# --- 3. a count beside the amount -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "do baar 20 hazaar kate.",
        "do baar 15 hazaar kate",
        "teen baar das hazaar kata",
        "20 hazaar do baar kate",
        "twice 30,000 kat gaye",
        "30,000 twice",
        "thirty thousand twice",
        "it was cut thrice, 12,000",
        "char baar pachees hazaar",
    ],
)
def test_a_count_beside_the_amount_is_refused(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("ek baar 30 hazaar diya", 30_000),  # once multiplies nothing
        ("ek hi baar pachees hazaar diye", 25_000),
        ("I called twice. The premium was 30,000.", 30_000),  # a count in another clause
    ],
)
def test_once_or_a_count_in_another_clause_still_reads(text, rupees):
    _reads(text, rupees)


# --- 4. romanised Hindi number words ----------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("bavan hazaar", 52_000),
        ("baawan hazar rupaye", 52_000),
        ("chaubees hazaar paanch sau rupaye", 24_500),
        ("ek lakh bees hazaar", 120_000),
        ("do lakh", 200_000),
        ("do lakh de diye", 200_000),
        ("ikyavan hazaar teen sau", 51_300),
        ("nabbe hazaar", 90_000),
        ("satattar hazaar", 77_000),
        ("tin hazaar rupaye", 3_000),
        ("nau sau", 900),
        ("das hazaar", 10_000),
        ("saath hazaar", 60_000),
        ("chhattis hajar", 36_000),
        ("teen karod", 30_000_000),
        ("unnees hazaar chaar sau", 19_400),
        ("52 hazaar paanch sau", 52_500),
        ("pachaas hazaar de do", 50_000),
        ("sat saal ke liye 20 hazaar", 20_000),  # "sat" bound to a duration
        ("assi hazaar diye the", 80_000),
    ],
)
def test_romanised_number_words_read(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    "text",
    [
        "paise de do",
        "das baje call aaya tha",
        "unke saath gaye the",
        "tera paisa wapas do",
        "bara bank hai",
        "main us din baith sat raha",
        "che guevara ki tshirt",
        "teen age ladka",
        "bis karo bhai",
    ],
)
def test_everyday_words_that_spell_a_number_make_no_amount(text):
    _no_amount(text)
    assert parse_amount(text) == NoAmount() or isinstance(parse_amount(text), Ambiguous)


@pytest.mark.parametrize(
    "text",
    [
        "do hazaar do",  # give two thousand, or 2,002
        "pachaas hazaar das",  # 50,010, or a stray word
        "saadhe teen lakh",  # fraction words stay refused
        "paune do lakh",
        "teen policy hain 30,000 ki",  # "teen" counts the noun, as "तीन पॉलिसी" does
        "do FD pachaas hazaar ki",
    ],
)
def test_a_collision_word_beside_a_number_without_a_number_phrase_refuses(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("ek insurance liya tha, iktalis hazaar teen sau ka", 41_300),
        ("haan ek policy thi 41,300 ki", 41_300),
        ("ek FD thi, bavan hazaar ki", 52_000),
        ("aik bima tha pachpan hazaar ka", 55_000),
    ],
)
def test_romanised_ek_as_an_article_counts_nothing(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    ("roman", "deva"),
    [
        ("ek insurance liya tha, iktalis hazaar teen sau ka", "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का"),
        ("ek baar 20 hazaar kata tha", "एक बार बीस हज़ार कटा था"),
        ("do policy thi 41,300 ki", "दो पॉलिसी थी 41,300 की"),
    ],
)
def test_romanised_ek_and_do_behave_like_the_devanagari_words(roman, deva):
    assert parse_amount(roman).model_dump(exclude={"span", "candidates"}) == parse_amount(deva).model_dump(
        exclude={"span", "candidates"}
    )


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        # the verifier's eight (references/reviews/iter3/verify-chain.md, failure 3)
        ("loan ke saath ek insurance liya tha 41300 ka", 41_300),
        ("loan ke sath insurance tha 41,300 ka", 41_300),
        ("insurance ke saath 41300 kata", 41_300),
        ("mere saath 41300 ka dhokha hua", 41_300),
        ("tera kya 41300 hi diye the", 41_300),
        ("bara amount tha 41300", 41_300),
        ("unhone kaha de do 41300", 41_300),
        ("41300 saath mein diye", 41_300),
        # my own variants
        ("bank ke saath ek FD bhi thi, 27,500 ki", 27_500),
        ("sath mein 36,000 kate the", 36_000),
        ("bara loan tha, insurance 18,750 ka", 18_750),
        ("tera bhai bola 22,000 de do", 22_000),
        ("das din pehle 19,999 kate", 19_999),  # "das" bound to a duration
        ("aap bata do 64,000 tha", 64_000),
        ("loan ke saath bavan hazaar ka bima", 52_000),  # "saath" before a non-unit number word
        ("loan ke saath pachees hazaar diye", 25_000),
        ("bara chalis hazaar ka loan", 40_000),
        ("insurance tha saath hi 30,000 kata", 30_000),
    ],
)
def test_an_everyday_word_that_spells_a_number_refuses_nothing(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    "text",
    [
        "do policy thi 41,300 ki",
        "teen insurance the 20,000 ke",
        "char FD thi pachaas hazaar ki",
        "do bima liye the 30,000 ke",
        "do plan the 12,000 ka",
    ],
)
def test_a_small_count_before_a_product_noun_refuses(text):
    _refused(text)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("saath policy wala 41,300", 41_300),  # only do/teen/char count a product noun
        ("bara insurance tha 41,300 ka", 41_300),
        ("das policy wale log 41,300 bole", 41_300),
    ],
)
def test_other_collision_words_before_a_product_noun_are_ordinary(text, rupees):
    _reads(text, rupees)


@pytest.mark.parametrize(
    "text",
    [
        # the verifier's recheck: a small count before any noun counts it, as "दो किस्तों में" does
        "do kisht mein 41300",
        "do EMI mein 41300",
        "teen kishton mein 41300",
        "do hisson mein 41300 diye",
        "doh installment 15,000 ke",
        "chaar parts mein 60,000",
        "tin kisht 12,000 ki",
    ],
)
def test_a_small_count_before_any_noun_refuses(text):
    _refused(text)


def test_the_devanagari_count_before_a_noun_is_refused_the_same_way():
    assert isinstance(parse_amount("दो किस्तों में 41300"), Ambiguous)
    assert isinstance(parse_amount("do kiston mein 41300"), Ambiguous)


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("de do na 41300", 41_300),  # "do" after a verb stem is the imperative
        ("bata do na, 41300 tha", 41_300),
        ("kar do jaldi 25,000 ka refund", 25_000),
        ("bhej do message, 18,000 hi the", 18_000),
        ("unhone kaha de do 41300", 41_300),
        ("bees hazaar sath mein processing", 20_000),  # "sath mein": together
        ("pachaas hazaar saath mein kata", 50_000),
    ],
)
def test_do_after_a_verb_and_saath_mein_after_an_amount_refuse_nothing(text, rupees):
    _reads(text, rupees)


def test_do_at_the_end_of_a_reply_is_the_verb():
    assert parse_amount("paise de do") == NoAmount()
    assert parse_amount("paise wapas do") == NoAmount()


def test_romanised_words_never_join_a_correction_into_one_figure():
    _refused("bavan hazaar nahi, pachpan hazaar")
    _refused("chalis hazaar, sorry, bayalis hazaar")


def test_a_romanised_range_of_collision_words_is_never_its_high_end():
    assert isinstance(parse_amount("bees pachees hazaar"), Ambiguous)
    result = parse_approx_amount("bees pachees hazaar")
    assert (result.status, result.low, result.high) == ("approximate", 20_000, 25_000)


def test_romanised_range_reads_as_approximate():
    result = parse_approx_amount("pachas se bavan hazaar")
    assert (result.status, getattr(result, "low", None), getattr(result, "high", None)) == (
        "approximate",
        50_000,
        52_000,
    )
