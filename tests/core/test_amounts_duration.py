"""parse_duration_months and parse_duration_days: a whole number, or None unless exactly one unambiguous duration."""

import pytest

from samajh.amounts import parse_duration_days, parse_duration_months


@pytest.mark.parametrize(
    ("text", "months"),
    [
        # Hindi
        ("5 साल", 60),
        ("पाँच साल", 60),
        ("एक साल", 12),
        ("दस वर्ष", 120),
        ("डेढ़ साल", 18),
        ("ढाई साल", 30),
        ("सवा साल", 15),
        ("साढ़े तीन साल", 42),
        ("पौने दो साल", 21),
        ("आधा साल", 6),
        ("1.5 साल", 18),
        ("छह महीने", 6),
        ("18 महीने", 18),
        ("36 माह", 36),
        ("2 साल 6 महीने", 30),
        ("दो साल छह महीने", 30),
        ("पाँच साल के लिए था", 60),
        ("5 साल, मतलब 60 महीने", 60),
        ("पाँच साल, 60 महीने", 60),
        ("5 लाख का लोन 5 साल के लिए", 60),
        ("50 साल", 600),
        # English, Latin and Devanagari
        ("60 months", 60),
        ("five years", 60),
        ("1.5 years", 18),
        ("5-year", 60),
        ("two and a half years", 30),
        ("1 year 6 months", 18),
        ("फाइव ईयर्स", 60),
        ("ट्वेल्व मंथ्स", 12),
        # Tamil
        ("ஐந்து வருடம்", 60),
        ("5 வருஷம்", 60),
        ("இரண்டு ஆண்டுகள்", 24),
        ("ஒன்றரை வருடம்", 18),
        ("அரை வருடம்", 6),
        ("ஒரு வருடம்", 12),
        ("ஆறு மாதம்", 6),
        ("பதினெட்டு மாதங்கள்", 18),
        # Kannada
        ("ಐದು ವರ್ಷ", 60),
        ("5 ವರ್ಷಗಳು", 60),
        ("ಒಂದೂವರೆ ವರ್ಷ", 18),
        ("ಆರು ತಿಂಗಳು", 6),
        ("ಹದಿನೆಂಟು ತಿಂಗಳು", 18),
    ],
)
def test_duration(text, months):
    assert parse_duration_months(text) == months


@pytest.mark.parametrize(
    "text",
    [
        "",
        "साल",
        "पता नहीं",
        "52,000 रुपये",
        "5",
        "30 दिन",
        "2 हफ़्ते",
        "5 साल या 10 साल",
        "5 साल 30 दिन",
        "डेढ़ महीना",
        "0 साल",
        "दो तीन साल",
        "साढ़े साल",
        "ஐந்து",
        "ಹತ್ತು ದಿನ",
        # years and months join only when the months are under 12
        "1 साल 12 महीने",
        "5 साल 60 महीने",
        "5 साल 10 साल",
        # ranges, alternatives, negation, comparison
        "5 से 6 साल",
        "तीन या पाँच साल",
        "पाँच साल नहीं तीन",
        "पाँच साल नहीं",
        "5 साल से कम",
        "less than 5 years",
        # a price per month, not a duration
        "पाँच हज़ार महीना",
        "52,000 महीना",
        "51 साल",
    ],
)
def test_no_single_duration(text):
    assert parse_duration_months(text) is None


@pytest.mark.parametrize(
    ("text", "months"),
    [
        ("5 साल", 60),
        ("पाँच साल।", 60),
        ("2 साल 6 महीने", 30),
        ("two and a half years", 30),
        ("ஒரு வருடம்", 12),
        ("ಐದು ವರ್ಷ", 60),
        ("5 साल, 60 महीने", 60),
    ],
)
def test_exact_duration(text, months):
    assert parse_duration_months(text, exact=True) == months


@pytest.mark.parametrize(
    "text",
    [
        "पाँच साल के लिए था",
        "5 साल, मतलब 60 महीने",
        "5 साल 52,000",
        "₹52,000 5 साल",
        "करीब 5 साल",
        "5 साल नहीं",
        "5",
        "",
    ],
)
def test_exact_duration_rejects_anything_else(text):
    assert parse_duration_months(text, exact=True) is None


# --- days: the cancellation window. Tamil and Kannada rows are not human-reviewed. ---


@pytest.mark.parametrize(
    ("text", "days"),
    [
        ("30 दिन", 30),
        ("तीस दिन", 30),
        ("पंद्रह दिन", 15),
        ("३० दिन", 30),
        ("दो हफ़्ते", 14),
        ("एक महीना", 30),
        ("एक महीने के अंदर", 30),
        ("हाँ, तीस दिन के अंदर रद्द कर सकते हैं", 30),
        ("30 दिन, यानी एक महीना", 30),
        ("डेढ़ महीना", 45),
        ("एक साल", 365),
        ("15 days", 15),
        ("thirty days", 30),
        ("within 30 days", 30),
        ("2 weeks", 14),
        ("थर्टी डेज़", 30),
        ("30 நாட்கள்", 30),
        ("முப்பது நாள்", 30),
        ("ஒரு மாதம்", 30),
        ("ಮೂವತ್ತು ದಿನ", 30),
        ("2 ವಾರ", 14),
        ("ಒಂದು ತಿಂಗಳು", 30),
    ],
)
def test_duration_in_days(text, days):
    assert parse_duration_days(text) == days


@pytest.mark.parametrize(
    "text",
    [
        "",
        "दिन",
        "पता नहीं",
        "कुछ दिन",
        "30",
        "24 घंटे",
        "डेढ़ दिन",
        "1 महीना 10 दिन",
        "30 दिन या 15 दिन",
        "15 से 30 दिन",
        "तीस दिन नहीं",
        "30 दिन से कम",
        "52,000 दिन",
        "11 साल",
        "0 दिन",
    ],
)
def test_no_single_duration_in_days(text):
    assert parse_duration_days(text) is None


def test_exact_duration_in_days():
    assert parse_duration_days("तीस दिन", exact=True) == 30
    assert parse_duration_days("30 days", exact=True) == 30
    assert parse_duration_days("हाँ, तीस दिन के अंदर", exact=True) is None
    assert parse_duration_days("30", exact=True) is None


# --- found by the independent review ---


@pytest.mark.parametrize(
    "text",
    [
        "15 – 30 दिन",
        "15, 30 दिन",
        "15/30 दिन",
        "हफ़्ता दस दिन",
        "30 दिन तो नहीं",
        "30 दिन, सॉरी 15",
        "ಮೂವತ್ತು ದಿನಾಂಕ",  # a date, not a number of days
        "saadhe 30 days",
    ],
)
def test_review_findings_are_not_a_day_count(text):
    assert parse_duration_days(text) is None


@pytest.mark.parametrize("text", ["3, 5 साल", "तीन साल छह", "saadhe 3 years", "5 साल तो नहीं"])
def test_review_findings_are_not_a_month_count(text):
    assert parse_duration_months(text) is None
