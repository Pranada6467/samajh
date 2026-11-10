"""A misspelt fraction or unit word next to a number is refused, not dropped.

Verifier finding 3 (references/reviews/iter1/verifier-decision-chain.md): "सारे तीन लाख" was
read as 3,00,000. The verifier named six Devanagari spellings and two romanised ones; his
full lists (55 and 170 spellings) were not saved, so `DEVANAGARI` and `ROMANISED` below are
written here in the same shapes. They are our spellings: whether Prisma writes any is not known.
"""

import pytest

from samajh.amounts import AmbiguityReason, Ambiguous, Parsed, parse_amount, parse_approx_amount

VERIFIER_NAMED = ["सारे", "साढ़ें", "पौना", "पौनें", "स्वा", "सवां"]
DEVANAGARI = [
    *VERIFIER_NAMED,
    "साड़ें",
    "साढ़ै",
    "साढ़ी",
    "साढ़",
    "सादें",
    "सारें",
    "साडें",
    "पोना",
    "पौनी",
    "पोनें",
    "पौनै",
    "पौनि",
    "सव्वां",
    "सवाँ",
    "सवे",
]
ROMANISED = [
    "pauney",
    "sarhe",
    "saadhey",
    "savaa",
    "saarhe",
    "sadhey",
    "saadey",
    "sadey",
    "saadhay",
    "saadhee",
    "sarhey",
    "saare",
    "sawaa",
    "suva",
    "sawwa",
    "savva",
    "pawne",
    "poune",
    "paunay",
    "ponay",
    "poney",
    "pavney",
    "paunee",
    "pouney",
]
BEFORE_DIGITS = ["{} 2 lakh", "{} 3,00,000", "{} ₹2,00,000"]


def refused(text: str) -> bool:
    result = parse_amount(text)
    return isinstance(result, Ambiguous) and result.reason is AmbiguityReason.malformed


@pytest.mark.parametrize("word", VERIFIER_NAMED)
def test_the_verifiers_devanagari_spellings_are_refused(word):
    assert refused(f"{word} तीन लाख"), parse_amount(f"{word} तीन लाख")
    assert refused(f"{word} 3,00,000")
    assert refused(f"प्रीमियम {word} ₹3,00,000 था")


@pytest.mark.parametrize("text", ["pauney 2 lakh", "sarhe 3,00,000", "सारे तीन लाख रुपये।"])
def test_the_verifiers_examples_are_refused_by_both_functions(text):
    assert refused(text)
    approx = parse_approx_amount(text)
    assert isinstance(approx, Ambiguous) and approx.reason is AmbiguityReason.malformed


def test_devanagari_sweep_all_refused():
    read = [w for w in DEVANAGARI if not refused(f"{w} तीन लाख")]
    assert read == []


def test_romanised_sweep_most_refused():
    cases = [shape.format(w) for w in ROMANISED for shape in BEFORE_DIGITS]
    read = [c for c in cases if not refused(c)]
    assert len(read) <= len(cases) // 10, read


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("मैंने तीन लाख दिए", 300_000),
        ("कुल तीन लाख", 300_000),
        ("premium बावन हज़ार था", 52_000),
        ("total 52,000", 52_000),
        ("loan se 52,000 kata", 52_000),
        ("sab milakar 3 lakh", 300_000),
        ("भाई तीन लाख दिए", 300_000),  # one letter from ढाई, but "ढाई तीन लाख" is not an amount
        ("पूरे तीन लाख", 300_000),
        ("पक्का दो लाख", 200_000),
        ("बाज़ार से पचास हज़ार", 50_000),
        ("they said 50,000", 50_000),
        ("phone 2 lakh ka tha", 200_000),
        ("loan done 2 lakh", 200_000),
        ("दो लाख लगे", 200_000),
        ("पचास हज़ार कटा", 50_000),
    ],
)
def test_an_ordinary_word_next_to_a_number_is_still_ignored(text, rupees):
    result = parse_amount(text)
    assert isinstance(result, Parsed), result
    assert result.rupees == rupees


@pytest.mark.parametrize(
    "text",
    [
        "एक लख पचास हज़ार",  # was 50,000
        "2 lak 50 thousand",  # was 50,000
        "दो लाख पचास हजर",  # was 2,00,050
        "दो लाख पचास हजर रुपये",
        "2 lakh 50 thousnd",
        "fifty two thousnd",  # was Ambiguous(bare_number) 52: now refused as malformed
    ],
)
def test_a_misspelt_unit_word_after_a_number_is_refused(text):
    assert refused(text), parse_amount(text)


def test_a_misspelt_fraction_before_a_duration_is_not_an_amount_question():
    assert parse_amount("सारे तीन साल").status == "none"
