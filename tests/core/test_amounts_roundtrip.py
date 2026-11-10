"""Round trip: parse_amount(spoken_amount(n, language)) == n, and the same for digit forms.

For Hindi and Hinglish this checks the speaker against the parser's hand-written word tables.
For Tamil and Kannada it is circular: the parser accepts what our own speaker emits, and
neither has been reviewed by a fluent speaker. The non-circular evidence for those two
languages is the pilot rows (test_amounts_pilot.py) and the hand-written tables in
test_amounts_parse.py.
"""

import random

import pytest

from samajh.amounts import (
    NOT_HUMAN_REVIEWED,
    AmbiguityReason,
    Ambiguous,
    Parsed,
    format_inr,
    parse_amount,
    spoken_amount,
)
from samajh.types import Language

LIMIT = 1_000_000_000
UNITS = (100, 1_000, 100_000, 10_000_000)


def _numbers() -> list[int]:
    rng = random.Random(20261110)
    edges = [u * k + d for u in UNITS for k in (1, 2, 9, 10, 99) for d in (-1, 0, 1)]
    return sorted(
        {
            *range(1, 1101),
            *range(1_000, 100_001, 1_000),
            *edges,
            LIMIT - 1,
            *(rng.randrange(1, LIMIT) for _ in range(3_000)),
            # small numbers are where the irregular words are; sample each magnitude too
            *(rng.randrange(1, 10**k) for k in range(4, 9) for _ in range(300)),
        }
    )


NUMBERS = _numbers()


def test_sample_is_as_large_as_promised():
    assert len(NUMBERS) > 4_000 and NUMBERS[0] == 1 and NUMBERS[-1] == LIMIT - 1


RUPEES = {Language.hi: "रुपये", Language.hi_en: "rupees", Language.ta: "ரூபாய்", Language.kn: "ರೂಪಾಯಿ"}


def _is(result, n: int, words: str) -> bool:
    return isinstance(result, Parsed) and result.rupees == n and result.span.text == words


def _is_bare(result, n: int, words: str) -> bool:
    """Under 100 with no unit and no currency word: never `Parsed`, the number is the one candidate."""
    return (
        isinstance(result, Ambiguous)
        and result.reason == AmbiguityReason.bare_number
        and len(result.candidates) == 1
        and _is(result.candidates[0], n, words)
    )


@pytest.mark.parametrize("language", list(Language))
def test_spoken_form_parses_back(language):
    wrong = []
    for n in NUMBERS:
        words = spoken_amount(n, language)
        with_rupees = parse_amount(f"{words} {RUPEES[language]}")
        alone = parse_amount(words)
        exact = parse_amount(f"{words} {RUPEES[language]}", exact=True)
        if not (_is(with_rupees, n, words) and exact == with_rupees):
            wrong.append((n, words, with_rupees))
        if not (_is_bare if n < 100 else _is)(alone, n, words):
            wrong.append((n, words, alone))
    assert not wrong, f"{len(wrong)} of {len(NUMBERS)}: {wrong[:5]}"


@pytest.mark.parametrize("language", list(Language))
def test_spoken_form_never_uses_digits_or_repeats_a_value(language):
    forms = {spoken_amount(n, language) for n in range(1, 2_001)}
    assert len(forms) == 2_000
    assert not any(ch.isdigit() for form in forms for ch in form)


@pytest.mark.parametrize("prefix", ["", "₹", "Rs. ", "रुपये "])
def test_digit_form_parses_back(prefix):
    wrong = []
    for n in NUMBERS:
        result, parsed = parse_amount(prefix + format_inr(n)), _digits(prefix, n)
        bare = Ambiguous(reason=AmbiguityReason.bare_number, candidates=(parsed,))
        if result != (bare if n < 100 and not prefix else parsed):
            wrong.append(n)
    assert not wrong, wrong[:5]


def _digits(prefix: str, n: int) -> Parsed:
    text = format_inr(n)
    return Parsed(rupees=n, span={"start": len(prefix), "end": len(prefix) + len(text), "text": text})


@pytest.mark.parametrize(
    ("rupees", "text"),
    [
        (0, "0"),
        (7, "7"),
        (999, "999"),
        (1_000, "1,000"),
        (52_000, "52,000"),
        (520_000, "5,20,000"),
        (10_000_000, "1,00,00,000"),
        (999_999_999, "99,99,99,999"),
        (12_345_678_901, "12,34,56,78,901"),
    ],
)
def test_format_inr(rupees, text):
    assert format_inr(rupees) == text


def test_format_inr_rejects_negative():
    with pytest.raises(ValueError):
        format_inr(-1)


@pytest.mark.parametrize(
    ("rupees", "language", "words"),
    [
        (175_000, Language.hi, "एक लाख पचहत्तर हज़ार"),
        (52_000, Language.hi, "बावन हज़ार"),
        (38_450, Language.hi, "अड़तीस हज़ार चार सौ पचास"),
        (25_000_000, Language.hi, "दो करोड़ पचास लाख"),
        (100, Language.hi, "एक सौ"),
        (520_000, Language.hi_en, "five lakh twenty thousand"),
        (11_200, Language.hi_en, "eleven thousand two hundred"),
        (
            999_999_999,
            Language.hi_en,
            "ninety nine crore ninety nine lakh ninety nine thousand nine hundred ninety nine",
        ),
        # Tamil and Kannada: the forms Timbre was given in the pilot (ta01, ta03, kn01, kn03).
        (52_000, Language.ta, "ஐம்பத்திரண்டாயிரம்"),
        # eleven before a unit takes its counting form, like one and twenty-one
        (11_000, Language.ta, "பதினோராயிரம்"),
        (21_000, Language.ta, "இருபத்தோராயிரம்"),
        (111_000, Language.ta, "ஒரு லட்சத்து பதினோராயிரம்"),
        (1_100_000, Language.ta, "பதினொரு லட்சம்"),
        (110_000_000, Language.ta, "பதினொரு கோடி"),
        (111_100_000, Language.ta, "பதினொரு கோடியே பதினொரு லட்சம்"),
        (11, Language.ta, "பதினொன்று"),
        (320_000, Language.ta, "மூன்று லட்சத்து இருபதாயிரம்"),
        (52_000, Language.kn, "ಐವತ್ತೆರಡು ಸಾವಿರ"),
        (320_000, Language.kn, "ಮೂರು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ"),
    ],
)
def test_spoken_amount(rupees, language, words):
    assert spoken_amount(rupees, language) == words


@pytest.mark.parametrize("rupees", [0, -5, LIMIT, LIMIT + 1])
@pytest.mark.parametrize("language", list(Language))
def test_spoken_amount_rejects_out_of_range(rupees, language):
    with pytest.raises(ValueError):
        spoken_amount(rupees, language)


def test_tamil_and_kannada_are_labelled_not_human_reviewed():
    assert frozenset({Language.ta, Language.kn}) == NOT_HUMAN_REVIEWED
    assert "not human-reviewed" in spoken_amount.__doc__


# The read-back prompt says the amount twice, in words and in digits. The normaliser counts a
# customer's "yes" only when the prompt parses back to the amount that was heard, so the prompt
# built from `spoken_amount` and `format_inr` must parse in every language. Tamil and Kannada
# joining words are not human-reviewed.
READ_BACK = {
    Language.hi: "{words}, यानी {digits}, सही है?",
    Language.hi_en: "{words}, yaani {digits}, sahi hai?",
    Language.ta: "{words}, அதாவது {digits}, சரியா?",
    Language.kn: "{words}, ಅಂದರೆ {digits}, ಸರಿನಾ?",
}


@pytest.mark.parametrize("language", list(Language))
def test_read_back_prompt_parses_back_to_its_own_amount(language):
    amounts = [n for n in NUMBERS if n >= 100]
    assert len(amounts) > 1000
    for rupees in amounts:
        prompt = READ_BACK[language].format(words=spoken_amount(rupees, language), digits=format_inr(rupees))
        result = parse_amount(prompt)
        assert isinstance(result, Parsed) and result.rupees == rupees, prompt


def test_read_back_of_an_amount_under_100_without_a_currency_word_is_not_guessed():
    result = parse_amount("निन्यानवे, यानी 99, सही है?")
    assert isinstance(result, Ambiguous)
    assert isinstance(parse_amount("निन्यानवे रुपये, यानी ₹99, सही है?"), Parsed)
