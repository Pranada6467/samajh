"""A small number that says how often, or a "one" that is a determiner, is not a rupee amount.

Found by the scenario set (data/scenarios/W4-report.md, U01-ta): "ஒரே தடவைதான்" (only once)
after a premium was read as a second amount of 1 and the turn was refused. The same
construction in Hindi, English and Kannada had the same fault, and without a currency word
in between it gave a wrong amount ("पचास हज़ार एक बार" -> 50,001).
Tamil and Kannada rows are not human-reviewed.
"""

import pytest

from samajh.amounts import AmbiguityReason, Ambiguous, NoAmount, Parsed, parse_amount

U01_TA = "பன்னிரண்டரை ஆயிரம் ரூபாய், ஒரே தடவைதான் கட்டணும்"  # the scripted call, unchanged


def test_u01_ta_only_once_after_the_premium_is_not_a_second_amount():
    result = parse_amount(U01_TA)
    assert isinstance(result, Parsed), result
    assert result.rupees == 12_500
    assert result.span.text == "பன்னிரண்டரை ஆயிரம்"


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        # Tamil: ஒரே is "only one / a single", like the article ஒரு
        ("பன்னிரண்டரை ஆயிரம் ரூபாய் ஒரே முறை", 12_500),
        ("ஐம்பதாயிரம் ஒரே தடவை", 50_000),
        ("ஐம்பதாயிரம் ரூபாய், இரண்டு தடவை", 50_000),
        # Hindi
        ("पचास हज़ार रुपये, एक बार देना है", 50_000),
        ("पचास हज़ार रुपये एक बार देना है", 50_000),
        ("पचास हज़ार रुपये, एक ही बार देना है", 50_000),
        ("पचास हज़ार रुपये, दो बार", 50_000),
        ("₹50,000, 2 बार", 50_000),
        # no currency word in between: the number used to join the amount (50,001)
        ("पचास हज़ार एक बार देना है", 50_000),
        ("पचास हज़ार एक ही बार देना है", 50_000),
        ("पचास हज़ार दो बार कटे", 50_000),
        # Hinglish and English
        ("50 hazaar rupaye, ek baar dena hai", 50_000),
        ("50,000 rupaye ek time", 50_000),
        ("fifty thousand rupees, one time payment", 50_000),
        ("fifty thousand rupees one time", 50_000),
        ("fifty thousand one time", 50_000),
        ("fifty thousand rupees, two times", 50_000),
        # Kannada
        ("ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ, ಒಂದು ಸಲ ಕಟ್ಟಬೇಕು", 50_000),
        ("ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ, ಒಂದೇ ಸಲ ಕಟ್ಟಬೇಕು", 50_000),
        ("ಐವತ್ತು ಸಾವಿರ ಒಂದು ಸಲ", 50_000),
        ("ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ, ಎರಡು ಬಾರಿ", 50_000),
        # a determiner "one" before any other noun
        ("पचास हज़ार रुपये, एक पॉलिसी", 50_000),
        ("fifty thousand rupees, one policy", 50_000),
        ("ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ, ಒಂದು ಪಾಲಿಸಿ", 50_000),
        ("fifty thousand rupees, one year", 50_000),
        # after a unit word with nothing in between: the one used to be a units digit (50,001)
        ("पचास हज़ार एक FD में", 50_000),
        ("पचास हज़ार एक policy", 50_000),
        ("पचास हज़ार एक बीमा", 50_000),
        ("एक लाख एक पॉलिसी के लिए", 100_000),
        ("पचास हज़ार एक साल का", 50_000),
        ("पचास हज़ार एक दिए", 50_000),  # known cost: a verb reads the same as a noun
        ("ஐம்பதாயிரம் ஒரு பாலிசி", 50_000),
        ("ஐம்பதாயிரம் ஒரே பாலிசி", 50_000),
        ("ಐವತ್ತು ಸಾವಿರ ಒಂದು ಪಾಲಿಸಿ", 50_000),
        ("ಒಂದು ಲಕ್ಷ ಒಂದು ಪಾಲಿಸಿಗೆ", 100_000),
        ("fifty thousand one insurance", 50_000),
        ("one lakh one policy", 100_000),
        ("2 lakh one FD", 200_000),
    ],
)
def test_a_count_or_a_determiner_after_an_amount_leaves_the_amount(text, rupees):
    result = parse_amount(text)
    assert isinstance(result, Parsed), f"{text!r} -> {result}"
    assert result.rupees == rupees


@pytest.mark.parametrize(
    "text", ["ஒரே தடவைதான் கட்டணும்", "ஒரே முறை", "ஒரு தடவை", "ek baar", "ek time", "ಒಂದೇ ಸಲ", "one year"]
)
def test_once_by_itself_is_no_amount(text):
    assert parse_amount(text) == NoAmount()


@pytest.mark.parametrize("text", ["एक बार", "एक ही बार", "one time", "ಒಂದು ಸಲ", "one policy", "दो बार"])
def test_a_lone_count_in_a_script_we_read_stays_a_bare_number_and_never_an_amount(text):
    # The contract for a number under 100 by itself ("एक FD", "दो बार बोला, दो बार") is unchanged.
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == AmbiguityReason.bare_number


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("एक लाख", 100_000),
        ("एक लाख रुपये", 100_000),
        ("एक हज़ार एक बार", 1_000),
        ("ஒரு லட்சம்", 100_000),
        ("ஒரே லட்சம்", 100_000),
        ("ஒன்றே கால் லட்சம்", 125_000),
        ("ಒಂದು ಲಕ್ಷ", 100_000),
        ("one thousand rupees", 1_000),
        ("one lakh", 100_000),
        ("एक रुपया", 1),
        ("पचास हज़ार एक", 50_001),
        ("पचास हज़ार एक रुपये", 50_001),
        ("fifty thousand one rupees", 50_001),
        ("ஐம்பதாயிரத்து ஒன்று", 50_001),
        ("ಐವತ್ತು ಸಾವಿರದ ಒಂದು ರೂಪಾಯಿ", 50_001),
        ("पचास हज़ार एक सौ", 50_100),
        ("fifty thousand one hundred", 50_100),
    ],
)
def test_real_amounts_with_a_one_are_unchanged(text, rupees):
    result = parse_amount(text)
    assert isinstance(result, Parsed), f"{text!r} -> {result}"
    assert result.rupees == rupees


@pytest.mark.parametrize(
    "text",
    [
        "पचास हज़ार रुपये, एक",  # nothing after it: may be a correction or the rest of the amount
        "पचास हज़ार रुपये, 1",
        "पचास हज़ार रुपये नहीं एक बार",  # a negator joins them
        "पचास हज़ार रुपये या एक बार",
        "पचास हज़ार रुपये, एक लाक रुपये",  # an unknown word before a currency word may be a unit
        "पचास हज़ार रुपये, बावन था",  # only "one" is a determiner
        "5,00,000 दो बार कटे",  # digits then a word: refused as before
        "पचास हज़ार एक लाक रुपये",  # an unknown word before a currency word may be a unit
    ],
)
def test_a_small_number_that_may_still_be_an_amount_keeps_the_turn_refused(text):
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
