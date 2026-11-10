"""Regressions for the parser gaps found by the 240-sentence evaluation (eval/amounts/REPORT.md, section 4).

Every transcript marked "real" is Prisma's own output, copied from eval/amounts/run/stt.jsonl;
the gold is the amount the sentence was generated from. The other rows are neighbours of the
same rule, written by hand. Tamil and Kannada rows are not human-reviewed.

Order follows the report: shapes that returned a WRONG amount first, then shapes that returned
no answer, then the shapes that stay refused on purpose, then the two-reading cross-check.
"""

import pytest

from samajh.amounts import (
    Agreed,
    AmbiguityReason,
    Ambiguous,
    NoAmount,
    Parsed,
    ReadBackNeeded,
    cross_check,
    parse_amount,
)

LAKH, CRORE = 100_000, 10_000_000


def _rupees(text: str) -> int:
    result = parse_amount(text)
    assert isinstance(result, Parsed), f"{text!r} -> {result}"
    return result.rupees


def _refused(text: str) -> Ambiguous:
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    return result


# --- 1. "X and a half UNIT" in Devanagari returned half a unit --------------------------------

AND_A_HALF = [
    # real, v2.5 text and literal
    ("मेरी ई एम आई वन एंड अ हाफ क्रोर रुपये है।", 15 * CRORE // 10),
    ("मेरी ई एम आई वन एंड अ हाफ क्रोर रुपीज़ है।", 15 * CRORE // 10),
    ("मेरी ई एम आई वन एंड अ हाफ क्रोर रूपीज़ है।", 15 * CRORE // 10),
    ("लोन के साथ टू एंड अ हाफ लाख रुपये का इंश्योरेंस दिया।", 250_000),
    ("लोन के साथ टू एंड अ हाफ लैक रूपीज़ का इंश्योरेंस दिया।", 250_000),
    ("इंश्योरेंस का प्रीमियम सिक्स एंड अ हाफ क्रोर रुपये है।", 65 * CRORE // 10),
    ("इंश्योरेंस का प्रीमियम सिक्स एंड अ हाफ क्रोर रूपीज़ है।", 65 * CRORE // 10),
    # neighbours
    ("वन एंड हाफ क्रोर", 15 * CRORE // 10),
    ("थ्री एंड ए हाफ थाउज़ंड रूपीस", 3_500),
    ("one and a half crore rupees", 15 * CRORE // 10),
]


@pytest.mark.parametrize(("text", "rupees"), AND_A_HALF)
def test_number_and_a_half_unit_in_devanagari(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize(
    "text",
    [
        "वन एंड द हाफ क्रोर रुपये",  # a word between "and" and the half that is not an article
        "टू एंड सम हाफ लाख",
        "two and the half lakh rupees",
        "एंड हाफ लाख रुपये",  # the number before "and" was lost
    ],
)
def test_a_half_left_dangling_after_and_is_never_read_as_half_a_unit(text):
    assert _refused(text).reason == AmbiguityReason.malformed


# --- 2. An unread word next to a number was dropped without notice ----------------------------

KANNADA_SPELLINGS = [
    # real: ನಾನ್ನೂರು / ನಾನ್ನೂರ (400), ಅರುವತ್ತು (60)
    ("ವಿಮೆ ಮೊತ್ತ ನಲವತ್ತೊಂಬತ್ತು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು", 49_400),
    ("ವಿಮೆ ಮೊತ್ತ ನಲವತ್ತ ಒಂಬತ್ತು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದ್ರು", 49_400),
    ("ಅರವತ್ತನಾಲ್ಕು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 64_400),
    ("ಮುನ್ನೂರ ಅರುವತ್ತು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 360),
    ("ಪ್ರೀಮಿಯಂ ಎಂದು ನಾನ್ನೂರು ರೂಪಾಯಿ ತೆಗೆದುಕೊಂಡರು", 400),
    ("ಇಪ್ಪತ್ತೊಂದು ಸಾವಿರದ ನಾನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಸಾಲ ತೆಗೆದುಕೊಂಡೆ", 21_450),
    ("ಇಎಂಐ ಅರುವತ್ತು ಲಕ್ಷ ಕಟ್ಟುತ್ತಿದ್ದೇನೆ", 60 * LAKH),
    ("ನನ್ನ ಪ್ರೀಮಿಯಂ ಅರುವತ್ತು ಲಕ್ಷದ ನಲವತ್ತು ಸಾವಿರ", 6_040_000),
    ("ನಾಲ್ಕು ಕೋಟಿ ಅರುವತ್ತು ಲಕ್ಷ ಸಾಲ ತೆಗೆದುಕೊಂಡೆ", 46_000_000),
    ("ಸಾಲದಿಂದ ಅರುವತ್ತು ಲಕ್ಷದ ಮುನ್ನೂರು ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು", 6_000_300),
    # real: tens written with a virama, fused or split
    ("ಅರವತ್ತ್ನಾಲ್ಕು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 64_400),
    ("ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ಲಕ್ಷ ರೂಪಾಯಿ ಕಡಿತವಾಯಿತು", 74 * LAKH),
    ("ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ ನಾಲ್ಕು ಲಕ್ಷ ರೂಪಾಯಿ ಕಡಿತವಾಯಿತು", 74 * LAKH),
    ("ಅರವತ್ತ್ ಒಂಬತ್ತು ಲಕ್ಷದ ಆರು ಸಾವಿರ ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 6_906_000),
    ("ಇಪ್ಪತ್ತ್ ಎಂಟು ಲಕ್ಷ ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 28 * LAKH),
    ("ನನ್ನ ಪ್ರೀಮಿಯಂ ಐವತ್ತ್ಮೂರು ಸಾವಿರದ ಏಳು ನೂರು", 53_700),
    ("ಐವತ್ತ್ ನಾಲ್ಕು ಲಕ್ಷ ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 54 * LAKH),
    ("ಐವತ್ತ್ನಾಲ್ಕು ಲಕ್ಷ ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 54 * LAKH),
    ("ಅರವತ್ತ್ ಆರು ಸಾವಿರದ ಏಳುನೂರ ಐವತ್ತು ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 66_750),
    ("ಅರವತ್ತ್ ಆರು ಸಾವಿರದ ಏಳ್ನೂರ ಐವತ್ತು ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 66_750),
    # neighbours: every tens word takes the virama form
    ("ಮೂವತ್ತ್ ಎರಡು ಸಾವಿರ ರೂಪಾಯಿ", 32_000),
    ("ತೊಂಬತ್ತ್ಮೂರು ಲಕ್ಷ", 93 * LAKH),
    ("ಅರುವತ್ತೈದು ಸಾವಿರ", 65_000),
]


@pytest.mark.parametrize(("text", "rupees"), KANNADA_SPELLINGS)
def test_kannada_spellings_prisma_writes(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize(
    "text",
    [
        # A word the lexicon cannot read stands between the number and its currency word: it
        # may be the rest of the number. The spellings are made up; the shape is the report's.
        "ವಿಮೆ ಮೊತ್ತ ನಲವತ್ತೊಂಬತ್ತು ಸಾವಿರದ ನಾನ್ನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು",
        "ಮುನ್ನೂರ ಅರ್ವತ್ತು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ",
        "64,000 ನಾನ್ನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ",
        "पचास हज़ार पांसौ रुपये कटे",
        "फिफ्टी थाउज़ंड फाइवंड्रेड रूपीज़",
        "fifty thousand fivehundred rupees",
        "ஐம்பதாயிரத்து ஐநூத்தி ரூபாய் கட்டினேன்",
    ],
)
def test_unread_word_between_a_number_and_its_currency_word_is_refused(text):
    result = parse_amount(text)
    assert not isinstance(result, Parsed), f"{text!r} -> {result}"
    assert not isinstance(result, NoAmount)


# --- 3. A fraction word the table lacked, in front of unit digits -----------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("எழரை 1,00,00,000 காப்பீடு என்று சொன்னார்கள்", 75 * CRORE // 10),  # real, v2.5 text
        ("எழரை கோடி காப்பீடு என்று சொன்னார்கள்", 75 * CRORE // 10),  # real, v2.5 literal
        ("எழரை லட்சம் ரூபாய்", 750_000),
        ("ஏழரை கோடி", 75 * CRORE // 10),
    ],
)
def test_tamil_seven_and_a_half_with_a_short_vowel(text, rupees):
    assert _rupees(text) == rupees


# --- 4. A garbled grouped number was multiplied by a thousand word ----------------------------


@pytest.mark.parametrize(
    "text",
    [
        "मेरा लोन 6,13,00,020 थाउज़ंड रुपये",  # real: gold 6,13,20,000, parser said 61300020000
        "मेरे लोन से 9,00,014 थाउज़ंड ₹100 कटे।",  # real: gold 9,14,100, parser said 900014100
        "6,13,000 हज़ार रुपये",
        "5,000 thousand rupees",
        "12,000 लाख रुपये",
        "1,500 ஆயிரம் ரூபாய்",
        "2,000 ಸಾವಿರ ರೂಪಾಯಿ",
        "2,000 सौ रुपये",  # the same for a hundred or more before a hundred word
        "500 hundred rupees",
    ],
)
def test_a_thousand_or_more_before_a_thousand_or_lakh_word_is_refused(text):
    assert _refused(text).reason == AmbiguityReason.malformed


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("500 thousand rupees", 500_000),
        ("1,000 करोड़ रुपये", 1_000 * CRORE),
        ("99 लाख", 99 * LAKH),
        ("बारह सौ रुपये", 1_200),
        ("99 hundred rupees", 9_900),
    ],
)
def test_ordinary_coefficients_still_multiply(text, rupees):
    assert _rupees(text) == rupees


# --- no-answer gaps -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("अकाउंट से कटे सेवेनटीन थाउज़ंड सेवेंटी रूपीस", 17_070),  # real, v2.5 literal
        ("सेवेनटी थाउज़ंड रूपीज़", 70_000),
    ],
)
def test_hinglish_spellings_in_devanagari(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        # real: a bare thousand after a noun in the ablative ("from the account")
        ("கணக்கிலிருந்து ஆயிரம் ரூபாய் எடுத்தார்கள்", 1_000),
        ("கணக்கில் இருந்து ஆயிரம் ரூபாய் எடுத்தார்கள்", 1_000),
        ("கணக்கில் இருந்து ஆயிரம் ரூபாய் எடுத்தார்கள்.", 1_000),
        # neighbours
        ("கடனிலிருந்து லட்சம் ரூபாய் பிடித்தார்கள்", LAKH),
        ("ಖಾತೆಯಿಂದ ಸಾವಿರ ರೂಪಾಯಿ ಕಡಿತವಾಯಿತು", 1_000),
        ("ಸಾಲದಿಂದ ಲಕ್ಷ ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು", LAKH),
        ("खाते से हज़ार रुपये कटे", 1_000),
    ],
)
def test_bare_unit_after_a_word_in_the_ablative_is_one_unit(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize("text", ["சுமார் ஆயிரம் ரூபாய்", "ಸುಮಾರು ಸಾವಿರ ರೂಪಾಯಿ", "साथ हज़ार रुपये"])
def test_bare_unit_after_any_other_unknown_word_is_still_refused(text):
    assert _refused(text).reason == AmbiguityReason.malformed


HIGHER_DIGITS_LOWER_WORDS = [
    # real, v2.5 text: Prisma formatted the higher groups and left the lower ones as words
    ("उन्होंने बीमा के 5,00,000 दो सौ रुपये लिए।", 500_200),
    ("எனக்கு 8,00,000 ஐயாயிரத்து ₹500 கடன் கிடைத்தது", 805_500),
    ("ப்ரீமியமாக 4 கோடியே 8,00,000 ஐம்பத்தையாயிரம் ரூபாய் பிடித்தார்கள்", 40_855_000),
    ("காப்பீட்டுத் தொகை 10,00,000 இருபத்தையாயிரம் ரூபாய் என்றார்கள்", 1_025_000),
    ("ಸಾಲದಿಂದ 60,00,000 ಮುನ್ನೂರು ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು", 6_000_300),
    ("ವಿಮೆ ಮೊತ್ತ 49,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು", 49_400),
    ("64,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 64_400),
    ("21,000 ನಾನ್ನೂರ ₹50 ಸಾಲ ತೆಗೆದುಕೊಂಡೆ", 21_450),
    # neighbours
    ("5,00,000 टू हंड्रेड रूपीज़", 500_200),
    ("2,00,00,000 पाँच लाख रुपये", 20_500_000),
    ("52,000 five hundred rupees", 52_500),
]


@pytest.mark.parametrize(("text", "rupees"), HIGHER_DIGITS_LOWER_WORDS)
def test_higher_groups_in_digits_then_lower_groups_in_words_add_up(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize(
    "text",
    [
        "5,00,000 दो बार कटे",  # no unit word after the digits: "twice", not 5,00,002
        "5,00,000 बीस रुपये",
        "5,500 दो सौ रुपये",  # the digits leave no room for the words
        "5,00,000 पाँच लाख रुपये",
        "5,00,000 दस लाख रुपये",
        "1,00,000 50,000 रुपये",  # digits after digits are two numbers
        "उन्होंने बीमा के 5,00,000 200 रुपये लिए।",  # real, v3.0
        "500 पाँच सौ रुपये",
    ],
)
def test_digits_followed_by_words_that_do_not_continue_them_are_refused(text):
    result = parse_amount(text)
    assert not isinstance(result, Parsed), f"{text!r} -> {result}"


# --- shapes that stay refused: the transcript alone does not decide them -----------------------

REFUSED_ON_PURPOSE = [
    # A clock time before a unit (v2.5 wrote साढ़े आठ सौ as 08:30 100). "paid ₹1,000 at 08:30" is
    # the plain reading of the same text.
    ("08:30 100 का कवर बताया था।", 850),
    ("08:30 ₹1,000 ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 8_500),
    ("ನನಗೆ 01:45 ₹1,00,000 ಸಾಲ ಸಿಕ್ಕಿತು", 175_000),
    ("ಪ್ರೀಮಿಯಂ ಎಂದು 03:30 ₹1,00,000 ತೆಗೆದುಕೊಂಡರು", 350_000),
    # A number word directly before digits. The two real shapes below need opposite rules
    # (count x unit against tens + units), so neither is applied.
    ("नाइंटी ₹1,80,000 का लोन मिला था", 9_080_000),
    ("मेरी ई एम आई नाइंटी ₹4,13,000 है", 9_413_000),
    ("பதினோரு ₹1,00,00,000 கடன் வாங்கினேன்", 11 * CRORE),
    ("பதிமூன்று 1,050 கடன் வாங்க", 13_050),
    ("ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ₹1,00,000 ಕಡಿತವಾಯಿತು", 74 * LAKH),
    ("ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ ₹4,00,000 ಕಡಿತವಾಯಿತು", 74 * LAKH),
    ("ಅರವತ್ತ್ 9,06,000 ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 6_906_000),
    ("ಅರವತ್ತ್ 6,750 ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 66_750),
    ("ಅರವತ್ತ್ 6,000 ಏಳ್ನೂರ 50 ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 66_750),
    ("ಅರವತ್ತ್ನಾಲ್ಕು 1,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ", 64_400),
    ("ನನ್ನ ಪ್ರೀಮಿಯಂ ಐವತ್ತ್ಮೂರು 1,700", 53_700),
    ("ಐವತ್ತ್ನಾಲ್ಕು 1,00,000 ವಿಮೆ ಎಂದು ಹೇಳಿದರು", 54 * LAKH),
    # ಒಂದು is "one" and also "a": one-and-three-quarters lakh, or a three-quarter lakh.
    ("ನನಗೆ ಒಂದು ಮುಕ್ಕಾಲು ಲಕ್ಷ ರೂಪಾಯಿ ಸಾಲ ಸಿಕ್ಕಿತು", 175_000),
    ("ಇಎಂಐ ಒಂದು ಕಾಲು ಕೋಟಿ ಕಟ್ಟುತ್ತಿದ್ದೇನೆ.", 125 * LAKH),
    # 3/4 before a unit: three quarters, or "three or four".
    ("எம்மா, 3/4 லட்சம் கட்டுறேன்.", 75_000),
    # Prisma's own formatting errors that leave a trace in the text.
    ("ಅರ್ಧ 50,00,000 ರೂಪಾಯಿ ಸಾಲ ತೆಗೆದುಕೊಂಡೆ.", 50 * LAKH),  # v3.0: the half is already applied
    ("ನನ್ನ ತಿಂಗಳ ಕಂತು 20,20 ರೂಪಾಯಿ.", 20_020),  # v3.0
    ("लोन के साथ टू प्वाइंट ₹25,00,00,000 का इंश्योरेंस दिया", 225 * LAKH),  # v2.5
    ("अकाउंट से कटे थ्री प्वाइंट ₹5,00,000", 350_000),  # v2.5
    ("लोन के साथ 7.50000000 रुपये का इंश्योरेंस दिया", 75 * CRORE // 10),  # v2.5
]


@pytest.mark.parametrize(("text", "gold"), REFUSED_ON_PURPOSE)
def test_real_transcripts_the_parser_refuses_instead_of_guessing(text, gold):
    """Known limit: each of these is a re-ask. None may come back as an amount other than gold."""
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result} (gold {gold})"


# --- two readings of the same turn --------------------------------------------------------------


def test_two_readings_that_agree_give_the_amount():
    v25 = parse_amount("उन्होंने बीमा के 5,00,000 दो सौ रुपये लिए।")
    v30 = parse_amount("उन्होंने बीमा के 5,00,200 रुपये लिए।")
    assert cross_check(v25, v30) == Agreed(rupees=500_200)


def test_two_readings_that_differ_need_a_read_back():
    # real: gold 3,00,200; v3.0 wrote digits that are another number
    v25 = parse_amount("3,00,200 ரூபாய் பிரீமியம் கட்டினேன்")
    v30 = parse_amount("3,02,000 ரூபாய் பிரீமியம் கட்டினேன்.")
    assert cross_check(v25, v30) == ReadBackNeeded(readings=(300_200, 302_000))


@pytest.mark.parametrize("missing", ["मेरी ईएमआई डेट नहीं", "नाइंटी ₹1,80,000 का लोन मिला था", "बावन", ""])
def test_a_reading_with_no_single_amount_needs_a_read_back(missing):
    good = parse_amount("90,80,000 का लोन मिला था")
    assert cross_check(good, parse_amount(missing)) == ReadBackNeeded(readings=(9_080_000, None))
    assert cross_check(parse_amount(missing), good) == ReadBackNeeded(readings=(None, 9_080_000))
    assert cross_check(parse_amount(missing), parse_amount(missing)) == ReadBackNeeded(readings=(None, None))
