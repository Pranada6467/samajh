"""Table tests for parse_amount. Expected values are written from the languages, not from the code.

Tamil and Kannada tables are not human-reviewed: they hold standard textbook forms plus the
forms Prisma produced in the pilot.
"""

import random
import time
import unicodedata

import pytest

from samajh.amounts import AmbiguityReason, Ambiguous, NoAmount, Parsed, parse_amount, parse_duration_months

LAKH, CRORE = 100_000, 10_000_000


def _words(table: str) -> list[str]:
    return table.split()


def _rupees(text: str) -> int:
    result = parse_amount(text)
    assert isinstance(result, Parsed), f"{text!r} -> {result}"
    assert text[result.span.start : result.span.end] == result.span.text
    return result.rupees


def _bare(text: str) -> int:
    """A number under 100 with no unit and no currency marker: listed, never `Parsed`."""
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == AmbiguityReason.bare_number, f"{text!r} -> {result}"
    (candidate,) = result.candidates
    assert text[candidate.span.start : candidate.span.end] == candidate.span.text
    return candidate.rupees


def _table(rows: str) -> list[tuple[str, int]]:
    """'text = value' per line; underscores and commas in the value are separators."""
    out = []
    for line in rows.strip().splitlines():
        text, value = line.rsplit("=", 1)
        out.append((text.strip(), int(value.replace("_", "").replace(",", ""))))
    return out


# --- Hindi, 0 to 99: one word each, typed out by hand in counting order -----------------

HINDI_0_99 = _words("""
शून्य एक दो तीन चार पांच छह सात आठ नौ
दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस
बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस
तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस
चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास
पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ
साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर
सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी
अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी
नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे
""")


def test_hindi_counting_words_0_to_99():
    assert len(HINDI_0_99) == 100
    assert [_bare(word) for word in HINDI_0_99] == list(range(100))
    assert [_rupees(f"{word} रुपये") for word in HINDI_0_99] == list(range(100))
    assert [_rupees(f"{word} हजार") for word in HINDI_0_99[1:]] == [n * 1000 for n in range(1, 100)]


ENGLISH_BELOW_20 = _words("""
zero one two three four five six seven eight nine
ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen
""")
ENGLISH_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
DEVANAGARI_BELOW_20 = _words("""
ज़ीरो वन टू थ्री फोर फाइव सिक्स सेवन एट नाइन
टेन इलेवन ट्वेल्व थर्टीन फोर्टीन फिफ्टीन सिक्सटीन सेवनटीन एटीन नाइनटीन
""")
DEVANAGARI_TENS = ["ट्वेंटी", "थर्टी", "फोर्टी", "फिफ्टी", "सिक्सटी", "सेवंटी", "एटी", "नाइंटी"]


@pytest.mark.parametrize(
    ("below_20", "tens", "rupees"),
    [(ENGLISH_BELOW_20, ENGLISH_TENS, "rupees"), (DEVANAGARI_BELOW_20, DEVANAGARI_TENS, "रुपीज़")],
)
def test_english_counting_words_0_to_99(below_20, tens, rupees):
    words = below_20 + [f"{ten} {below_20[unit]}" if unit else ten for ten in tens for unit in range(10)]
    assert [_bare(word) for word in words] == list(range(100))
    assert [_rupees(f"{word} {rupees}") for word in words] == list(range(100))


# --- Tamil and Kannada, 1 to 99 --------------------------------------------------------

TAMIL_1_19 = _words("""
ஒன்று இரண்டு மூன்று நான்கு ஐந்து ஆறு ஏழு எட்டு ஒன்பது பத்து
பதினொன்று பன்னிரண்டு பதிமூன்று பதினான்கு பதினைந்து பதினாறு பதினேழு பதினெட்டு பத்தொன்பது
""")
TAMIL_TENS = ["இருபது", "முப்பது", "நாற்பது", "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு"]
# Three decades typed out in full; the joining stem differs between them.
TAMIL_DECADES = {
    20: "இருபத்தொன்று இருபத்திரண்டு இருபத்துமூன்று இருபத்துநான்கு இருபத்தைந்து "
    "இருபத்தாறு இருபத்தேழு இருபத்தெட்டு இருபத்தொன்பது",
    50: "ஐம்பத்தொன்று ஐம்பத்திரண்டு ஐம்பத்திமூன்று ஐம்பத்திநான்கு ஐம்பத்தைந்து ஐம்பத்தாறு ஐம்பத்தேழு ஐம்பத்தெட்டு ஐம்பத்தொன்பது",
    90: "தொண்ணூற்றொன்று தொண்ணூற்றிரண்டு தொண்ணூற்றுமூன்று தொண்ணூற்றுநான்கு தொண்ணூற்றைந்து "
    "தொண்ணூற்றாறு தொண்ணூற்றேழு தொண்ணூற்றெட்டு தொண்ணூற்றொன்பது",
}
TAMIL_JOINING = ["இருபத்து", "முப்பத்து", "நாற்பத்து", "ஐம்பத்து", "அறுபத்து", "எழுபத்து", "எண்பத்து", "தொண்ணூற்று"]

KANNADA_1_19 = _words("""
ಒಂದು ಎರಡು ಮೂರು ನಾಲ್ಕು ಐದು ಆರು ಏಳು ಎಂಟು ಒಂಬತ್ತು ಹತ್ತು
ಹನ್ನೊಂದು ಹನ್ನೆರಡು ಹದಿಮೂರು ಹದಿನಾಲ್ಕು ಹದಿನೈದು ಹದಿನಾರು ಹದಿನೇಳು ಹದಿನೆಂಟು ಹತ್ತೊಂಬತ್ತು
""")
KANNADA_TENS = ["ಇಪ್ಪತ್ತು", "ಮೂವತ್ತು", "ನಲವತ್ತು", "ಐವತ್ತು", "ಅರವತ್ತು", "ಎಪ್ಪತ್ತು", "ಎಂಬತ್ತು", "ತೊಂಬತ್ತು"]
KANNADA_DECADES = {
    20: "ಇಪ್ಪತ್ತೊಂದು ಇಪ್ಪತ್ತೆರಡು ಇಪ್ಪತ್ತಮೂರು ಇಪ್ಪತ್ತನಾಲ್ಕು ಇಪ್ಪತ್ತೈದು ಇಪ್ಪತ್ತಾರು ಇಪ್ಪತ್ತೇಳು ಇಪ್ಪತ್ತೆಂಟು ಇಪ್ಪತ್ತೊಂಬತ್ತು",
    50: "ಐವತ್ತೊಂದು ಐವತ್ತೆರಡು ಐವತ್ಮೂರು ಐವತ್ನಾಲ್ಕು ಐವತ್ತೈದು ಐವತ್ತಾರು ಐವತ್ತೇಳು ಐವತ್ತೆಂಟು ಐವತ್ತೊಂಬತ್ತು",
    90: "ತೊಂಬತ್ತೊಂದು ತೊಂಬತ್ತೆರಡು ತೊಂಬತ್ತಮೂರು ತೊಂಬತ್ತನಾಲ್ಕು ತೊಂಬತ್ತೈದು ತೊಂಬತ್ತಾರು ತೊಂಬತ್ತೇಳು ತೊಂಬತ್ತೆಂಟು ತೊಂಬತ್ತೊಂಬತ್ತು",
}


@pytest.mark.parametrize(
    ("below_20", "tens", "decades", "rupees"),
    [
        (TAMIL_1_19, TAMIL_TENS, TAMIL_DECADES, "ரூபாய்"),
        (KANNADA_1_19, KANNADA_TENS, KANNADA_DECADES, "ರೂಪಾಯಿ"),
    ],
    ids=["ta", "kn"],
)
def test_tamil_and_kannada_counting_words(below_20, tens, decades, rupees):
    for read in (_bare, lambda word: _rupees(f"{word} {rupees}")):
        assert [read(word) for word in below_20] == list(range(1, 20))
        assert [read(word) for word in tens] == list(range(20, 100, 10))
        for base, words in decades.items():
            assert [read(word) for word in words.split()] == list(range(base + 1, base + 10))


@pytest.mark.parametrize(
    ("joining", "units", "thousand"),
    [(TAMIL_JOINING, TAMIL_1_19[:9], "ஆயிரம்"), (KANNADA_TENS, KANNADA_1_19[:9], "ಸಾವಿರ")],
    ids=["ta", "kn"],
)
def test_every_compound_21_to_99_written_as_two_words(joining, units, thousand):
    """Prisma wrote 52 thousand as 'ஐம்பத்தி இரண்டாயிரம்': tens and unit as separate words."""
    for tens, ten_word in enumerate(joining, start=2):
        for unit, unit_word in enumerate(units, start=1):
            assert _bare(f"{ten_word} {unit_word}") == tens * 10 + unit
            assert _rupees(f"{ten_word} {unit_word} {thousand}") == (tens * 10 + unit) * 1000


# --- amounts ----------------------------------------------------------------------------

DIGITS = _table("""
₹52,000 = 52_000
52,000 रुपये = 52_000
52000 = 52_000
52k = 52_000
52K = 52_000
Rs. 52,000 = 52_000
Rs52000 = 52_000
INR 52,000 = 52_000
52,000/- = 52_000
₹ 52,000.00 = 52_000
5,20,000 = 520_000
520,000 = 520_000
1,00,00,000 = 10_000_000
10,000,000 = 10_000_000
५२,००० रुपये = 52_000
௫௨,௦௦௦ ரூபாய் = 52_000
೫೨,೦೦೦ ರೂಪಾಯಿ = 52_000
1.5 लाख = 150_000
१.५ लाख = 150_000
2.5 करोड़ = 25_000_000
1.5 lakh rupees = 150_000
2 lakhs = 200_000
3 lac = 300_000
1.25 crore = 12_500_000
4 crores = 40_000_000
20 thousand = 20_000
20 hazaar = 20_000
20 hazar = 20_000
5lakh = 500_000
1.5 லட்சம் = 150_000
2.5 கோடி ரூபாய் = 25_000_000
1.5 ಲಕ್ಷ = 150_000
5 लाख 20 हज़ार = 520_000
5 लाख 20,000 = 520_000
""")

# Prisma's ITN shape: the fraction word stays in front of digits that already hold the unit.
ITN = _table("""
सवा 2,00,000 = 225_000
साढ़े 3,000 = 3_500
पौने ₹2,00,000 = 175_000
पौने 2,00,000 रुपये = 175_000
साढ़े 10,00,000 = 1_050_000
सवा 1,00,00,000 = 12_500_000
साढ़े 500 = 550
साढ़े 12,000 = 12_500
डेढ़ 1,00,000 = 150_000
ढाई ₹1,00,00,000 = 25_000_000
डेढ़ 100 = 150
ஒன்றரை ₹1,00,000 = 150_000
இரண்டரை ₹1,00,00,000 = 25_000_000
மூன்றரை 1,000 = 3_500
ಒಂದೂವರೆ ₹1,00,000 = 150_000
ಎರಡೂವರೆ 1,00,00,000 = 25_000_000
साढ़े 3 हज़ार = 3_500
सवा 2 लाख = 225_000
""")

HINDI = _table("""
अड़तीस हज़ार चार सौ पचास = 38_450
पाँच लाख बीस हज़ार = 520_000
पांच लाख बीस हजार = 520_000
बावन हज़ार = 52_000
सौ = 100
एक सौ = 100
नौ सौ निन्यानवे = 999
हज़ार रुपये = 1_000
एक लाख = 100_000
एक करोड़ = 10_000_000
दो करोड़ पचास लाख = 25_000_000
पंद्रह सौ = 1_500
एक लाख एक = 100_001
सवा दो लाख = 225_000
साढ़े तीन हज़ार = 3_500
पौने दो लाख = 175_000
डेढ़ लाख = 150_000
ढाई करोड़ = 25_000_000
डेढ़ सौ = 150
ढाई सौ = 250
डेढ़ हज़ार = 1_500
ढाई हज़ार = 2_500
सवा लाख = 125_000
सवा सौ = 125
पौन लाख = 75_000
पौने लाख = 75_000
साढ़े पाँच सौ = 550
साढ़े सात लाख = 750_000
पौने तीन करोड़ = 27_500_000
सवा पाँच हज़ार = 5_250
आधा लाख = 50_000
छः सौ = 600
छे हज़ार = 6_000
""")

ENGLISH = _table("""
twenty five thousand = 25_000
Twenty-Five Thousand = 25_000
one point five lakh = 150_000
two point two five lakh = 225_000
eleven thousand two hundred = 11_200
ten lakh = 1_000_000
one hundred = 100
hundred = 100
nine hundred ninety nine = 999
one hundred and fifty = 150
two thousand and five = 2_005
fifteen hundred = 1_500
one hundred fifty thousand = 150_000
two crore fifty lakh = 25_000_000
five lakh twenty thousand four hundred fifty = 520_450
one million = 1_000_000
two and a half lakh = 250_000
one and a half crore = 15_000_000
half lakh = 50_000
ट्वेंटी फ़ाइव थाउज़ेंड = 25_000
वन पॉइंट फ़ाइव लाख = 150_000
इलेवन थाउज़ेंड टू हंड्रेड = 11_200
टेन लाख = 1_000_000
फिफ्टी टू थाउज़ेंड = 52_000
थ्री लाख ट्वेंटी थाउज़ेंड = 320_000
टू करोड़ = 20_000_000
""")

TAMIL = _table("""
ஐம்பத்தி இரண்டாயிரம் = 52_000
ஐம்பத்திரண்டாயிரம் = 52_000
ஐம்பத்திரண்டு ஆயிரம் = 52_000
மூன்று லட்சத்து இருபதாயிரம் = 320_000
ஒன்றரை லட்சம் = 150_000
இரண்டரை கோடி = 25_000_000
நூறு = 100
இருநூறு = 200
முந்நூறு = 300
நானூறு = 400
ஐநூறு = 500
அறுநூறு = 600
எழுநூறு = 700
எண்ணூறு = 800
தொள்ளாயிரம் = 900
நூற்று ஐம்பது = 150
நூற்றைம்பது = 150
இருநூற்று ஐம்பது = 250
தொள்ளாயிரத்து ஐம்பது = 950
ஆயிரம் = 1_000
இரண்டாயிரம் = 2_000
மூவாயிரம் = 3_000
நான்காயிரம் = 4_000
நாலாயிரம் = 4_000
ஐயாயிரம் = 5_000
ஐந்தாயிரம் = 5_000
ஆறாயிரம் = 6_000
ஏழாயிரம் = 7_000
எட்டாயிரம் = 8_000
ஒன்பதாயிரம் = 9_000
பத்தாயிரம் = 10_000
பதினோராயிரம் = 11_000
பன்னிரண்டாயிரம் = 12_000
பதினைந்தாயிரம் = 15_000
இருபதாயிரம் = 20_000
இருபத்தையாயிரம் = 25_000
ஐம்பதாயிரம் = 50_000
தொண்ணூறாயிரம் = 90_000
ஆயிரத்து ஐநூறு = 1_500
ஆயிரத்தைநூறு = 1_500
இரண்டாயிரத்து ஐநூறு = 2_500
பத்தாயிரத்து ஐநூறு = 10_500
ஒரு லட்சம் = 100_000
ஒரு லட்சத்து ஐம்பதாயிரம் = 150_000
ஐந்து லட்சத்து இருபதாயிரம் = 520_000
பத்து லட்சம் = 1_000_000
ஒரு கோடி = 10_000_000
இரண்டு கோடியே ஐம்பது லட்சம் = 25_000_000
மூன்றரை லட்சம் = 350_000
நான்கரை லட்சம் = 450_000
ஒன்றேகால் லட்சம் = 125_000
ஒன்றே கால் லட்சம் = 125_000
இரண்டேமுக்கால் லட்சம் = 275_000
முக்கால் லட்சம் = 75_000
அரை லட்சம் = 50_000
கால் லட்சம் = 25_000
ரெண்டு லட்சம் = 200_000
மூணு லட்சம் = 300_000
நாலு லட்சம் = 400_000
அஞ்சு லட்சம் = 500_000
அம்பதாயிரம் = 50_000
அம்பத்தி ரெண்டாயிரம் = 52_000
இருபத்தஞ்சாயிரம் = 25_000
ரெண்டரை லட்சம் = 250_000
நூத்தி அம்பது = 150
ஐம்பதாயிரம் ஒரு பாலிசிக்கு = 50_000
""")

KANNADA = _table("""
ಐವತ್ತೆರಡು ಸಾವಿರ = 52_000
ಮೂರು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ = 320_000
ಒಂದುವರೆ ಲಕ್ಷ = 150_000
ಒಂದೂವರೆ ಲಕ್ಷ = 150_000
ಎರಡೂವರೆ ಕೋಟಿ = 25_000_000
ನೂರು = 100
ಇನ್ನೂರು = 200
ಮುನ್ನೂರು = 300
ನಾನೂರು = 400
ಐನೂರು = 500
ಆರುನೂರು = 600
ಏಳುನೂರು = 700
ಎಂಟುನೂರು = 800
ಒಂಬೈನೂರು = 900
ನೂರ ಐವತ್ತು = 150
ನೂರೈವತ್ತು = 150
ಇನ್ನೂರ ಐವತ್ತು = 250
ಸಾವಿರ = 1_000
ಒಂದು ಸಾವಿರ = 1_000
ಎರಡು ಸಾವಿರ = 2_000
ಹತ್ತು ಸಾವಿರ = 10_000
ಇಪ್ಪತ್ತು ಸಾವಿರ = 20_000
ಸಾವಿರದ ಐನೂರು = 1_500
ಎರಡು ಸಾವಿರದ ಐನೂರು = 2_500
ಒಂದು ಲಕ್ಷ = 100_000
ಒಂದು ಲಕ್ಷದ ಐವತ್ತು ಸಾವಿರ = 150_000
ಐದು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ = 520_000
ಹತ್ತು ಲಕ್ಷ = 1_000_000
ಒಂದು ಕೋಟಿ = 10_000_000
ಎರಡು ಕೋಟಿ ಐವತ್ತು ಲಕ್ಷ = 25_000_000
ಮೂರೂವರೆ ಲಕ್ಷ = 350_000
ನಾಲ್ಕೂವರೆ ಸಾವಿರ = 4_500
ಒಂದೂಕಾಲು ಲಕ್ಷ = 125_000
ಒಂದೂ ಮುಕ್ಕಾಲು ಲಕ್ಷ = 175_000
ಮುಕ್ಕಾಲು ಲಕ್ಷ = 75_000
ಅರ್ಧ ಲಕ್ಷ = 50_000
ಕಾಲು ಲಕ್ಷ = 25_000
ಮೂರು ಲಕ್ಷದ ಸಾಲ = 300_000
ಐವತ್ತು ಸಾವಿರದ ವಿಮೆ = 50_000
""")


@pytest.mark.parametrize(
    ("text", "rupees"),
    [*DIGITS, *ITN, *HINDI, *ENGLISH, *TAMIL, *KANNADA],
)
def test_amount(text, rupees):
    assert _rupees(text) == rupees


# --- spelling and encoding variants -------------------------------------------------------


@pytest.mark.parametrize(
    ("variants", "rupees"),
    [
        (["पाँच हज़ार", "पांच हजार", "पाँच हजार", "पांच हज़ार"], 5_000),
        (["छह सौ", "छः सौ", "छे सौ"], 600),
        (["ट्वेंटी फ़ाइव थाउज़ेंड", "ट्वेन्टी फाइव थाउजेंड", "ट्वेंटी फाइव थाउज़ेन्ड"], 25_000),
        (["साढ़े तीन हज़ार", "साढे तीन हजार"], 3_500),
        (["डेढ़ लाख", "डेढ लाख"], 150_000),
        (["पंद्रह हज़ार", "पन्द्रह हज़ार"], 15_000),
        (["twenty five thousand", "TWENTY FIVE THOUSAND", "Twenty-five  thousand"], 25_000),
        (["லட்சம்", "லக்ஷம்", "இலட்சம்"], 100_000),
    ],
)
def test_spelling_variants_are_equal(variants, rupees):
    assert [_rupees(text) for text in variants] == [rupees] * len(variants)


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize(
    ("text", "rupees"),
    [("पौने दो लाख रुपये जमा किए।", 175_000), ("ஐம்பத்திரண்டாயிரம் ரூபாய்", 52_000), ("ಐವತ್ತೆರಡು ಸಾವಿರ", 52_000)],
)
def test_unicode_normal_form_does_not_matter_and_span_indexes_the_input(form, text, rupees):
    given = unicodedata.normalize(form, text)
    result = parse_amount(given)
    assert isinstance(result, Parsed) and result.rupees == rupees
    assert given[result.span.start : result.span.end] == result.span.text


def test_zero_width_joiners_are_ignored_and_the_span_keeps_them():
    text = "लोन प‍चास ह‌ज़ार का है"
    result = parse_amount(text)
    assert isinstance(result, Parsed) and result.rupees == 50_000
    assert result.span.text == "प‍चास ह‌ज़ार" == text[result.span.start : result.span.end]


def test_span_is_the_amount_inside_the_sentence():
    text = "मेरे लोन से बावन हज़ार रुपये कटे।"
    result = parse_amount(text)
    assert result == Parsed(rupees=52_000, span={"start": 12, "end": 22, "text": "बावन हज़ार"})


# --- never guess --------------------------------------------------------------------------

M, F, N, X, B = (
    AmbiguityReason.malformed,
    AmbiguityReason.fraction_without_unit,
    AmbiguityReason.non_integer,
    AmbiguityReason.multiple_amounts,
    AmbiguityReason.bare_number,
)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("साढ़े तीन", F),
        ("डेढ़", F),
        ("पौने", F),
        ("three and a half", F),
        ("सवा 250", F),
        ("साढ़े 30", F),
        ("ढाई 2,00,000", M),
        ("ஒன்றரை ₹2,00,000", M),
        ("डेढ़ 1,50,000", M),
        ("साढ़े लाख", M),
        ("दो तीन लाख", M),
        ("दो-तीन लाख", M),
        ("बीस पच्चीस हज़ार", M),
        ("पाँच हज़ार दो लाख", M),
        ("5 लाख 20,00,000", M),
        ("ढाई लाख पाँच हज़ार", M),
        ("one point twenty five lakh", M),
        ("ten lakh and fifty thousand", M),
        ("1,2,3", M),
        ("52,00", M),
        ("10.11.2026", M),
        ("लाखों रुपये", M),
        ("हज़ारों", M),
        ("52000.50", N),
        ("1.5", N),
        ("1.2345 हज़ार", N),
        ("पाँच लाख, बीस हज़ार", X),
        ("5 लाख का लोन और 20 हज़ार का बीमा", X),
        ("premium 52,000 cover 5,00,000", X),
        ("3 या 4", X),
        # Tamil joining forms cannot end an amount, and case endings are not read.
        ("மூன்று லட்சத்து", M),
        ("ஐம்பத்தி", M),
        ("இருபதாயிரத்தை கழித்தார்கள்", M),
        ("மூன்று லட்சத்து இருபதாயிரத்தை", M),
        ("ಐವತ್ತು ಸಾವಿರವನ್ನು", M),
        # "hundreds of", "thousands of": a number was meant, none was named
        ("ನೂರಾರು ರೂಪಾಯಿ", M),
        ("ಸಾವಿರಾರು ರೂಪಾಯಿ", M),
        ("ஆயிரக்கணக்கில்", M),
        # "five or six thousand"
        ("ஐந்தாறு ஆயிரம்", M),
        ("ಐದಾರು ಸಾವಿರ", M),
    ],
)
def test_ambiguous(text, reason):
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == reason


def test_ambiguous_lists_the_readable_candidates():
    text = "5 लाख का लोन और 20 हज़ार का बीमा"
    result = parse_amount(text)
    assert isinstance(result, Ambiguous)
    assert [(c.rupees, c.span.text) for c in result.candidates] == [(500_000, "5 लाख"), (20_000, "20 हज़ार")]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "कुछ नहीं पता",
        "I do not know",
        "ie6",
        "h1 and b2b",
        "5 साल",
        "डेढ़ साल",
        "12%",
        "12 प्रतिशत",
        "18 months",
        "ஐந்து வருடம்",
        "ಐದು ವರ್ಷ",
        "கால் வந்தது",
        "half of it",
        "good point",
        "\u200d",
        "ஒரு பாலிசி",
    ],
)
def test_no_amount(text):
    assert parse_amount(text) == NoAmount()


# --- the weak-candidate rule ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        # one strong value: weak numbers around it are ignored
        ("एक FD में 52,000 रुपये", 52_000),
        ("दो तीन बार बताया, बावन हज़ार कटे", 52_000),
        ("5 साल का 52,000 premium", 52_000),
        ("12% ब्याज पर 5 लाख", 500_000),
        ("साढ़े तीन बजे बोला 52,000 रुपये", 52_000),
        ("one policy for twenty five thousand", 25_000),
        # the same value twice counts once
        ("52,000 यानी बावन हज़ार", 52_000),
        ("₹1,50,000, डेढ़ लाख", 150_000),
        # a unit word or a currency marker makes a small number strong
        ("एक FD, 50 रुपये", 50),
        ("2 बार, ₹5", 5),
    ],
)
def test_weak_candidates(text, rupees):
    assert _rupees(text) == rupees


# --- a number under 100 with no unit and no currency marker is not an amount ------------------


@pytest.mark.parametrize(
    ("text", "listed"),
    [
        ("बावन", [52]),
        ("पाँच का कवर", [5]),
        ("पैसे दे दो", [2]),
        ("थैंक्स फ़ोर कॉलिंग", [4]),
        ("एक FD", [1]),
        ("बता दो", [2]),
        ("5", [5]),
        ("99", [99]),
        ("दो बार बोला, दो बार", [2, 2]),
        ("दो सो रहे हैं", [2]),
    ],
)
def test_bare_number_is_ambiguous_and_listed(text, listed):
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == B
    assert [c.rupees for c in result.candidates] == listed


@pytest.mark.parametrize(("text", "rupees"), [("बावन रुपये", 52), ("₹52", 52), ("Rs. 5", 5), ("100", 100)])
def test_currency_marker_or_three_digits_make_a_small_number_an_amount(text, rupees):
    assert _rupees(text) == rupees


# --- a word the lexicon does not know, next to a number -----------------------------------------

VARIANTS = _table("""
चालिस हज़ार = 40_000
छत्तिस हज़ार = 36_000
पिचहत्तर हज़ार = 75_000
पिचासी हज़ार = 85_000
पिचानवे हज़ार = 95_000
ग्यारा हज़ार = 11_000
बारा हज़ार = 12_000
नबे हज़ार = 90_000
असी हज़ार = 80_000
पोने दो लाख = 175_000
पौणे दो लाख = 175_000
सव्वा दो लाख = 225_000
डेड़ लाख = 150_000
पांच सो = 500
पांच सो रुपये = 500
पांच सो पचास = 550
फिफ्टी टू थाउज़ेंड्स = 52_000
fifty two thousands = 52_000
half a lakh = 50_000
ಐದ್ ಲಕ್ಷ = 500_000
ಐವತ್ತೆರಡ್ ಸಾವಿರ = 52_000
ಐವತ್ತು ಸಾವ್ರ = 50_000
ஆயிரம் ரூபாய் = 1_000
லோன், ஆயிரம் ரூபாய் = 1_000
₹ लाख = 100_000
और सौ रुपये = 100
""")


@pytest.mark.parametrize(("text", "rupees"), VARIANTS)
def test_spelling_variant_or_bare_unit(text, rupees):
    assert _rupees(text) == rupees


@pytest.mark.parametrize(
    "text",
    [
        # the word before the unit is a number we cannot read: साठ misheard, romanised Hindi
        "साथ हज़ार",
        "bavan hazaar",
        "paune do lakh",
        "pachees hazar rupaye",
        # "several", "a few"
        "कई लाख",
        "कुछ हज़ार रुपये",
        "பல ஆயிரம்",
        "சில ஆயிரம்",
        "ಕೆಲವು ಸಾವಿರ",
        "lakhs of rupees",
        "thousands",
        "पूरे सौ रुपये",
    ],
)
def test_unit_after_an_unknown_word_is_malformed(text):
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == M


# --- ranges, alternatives, negation, comparison ---------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "बावन हज़ार नहीं पचपन",
        "50 से 60 हज़ार",
        "5 से 6 लाख",
        "बावन या पचपन हज़ार",
        "बावन और पचपन हज़ार",
        "ஐம்பது அல்லது அறுபதாயிரம்",
        "ಐವತ್ತರಿಂದ ಅರವತ್ತು ಸಾವಿರ",
        "ஐம்பதிலிருந்து அறுபதாயிரம்",
        "ಐವತ್ತು ಅಥವಾ ಅರವತ್ತು ಸಾವಿರ",
        "50 to 60 thousand",
        "fifty or sixty thousand",
        "50–60 हज़ार",
        "50-60 हज़ार",
        "पचास, साठ हज़ार",
        "बावन हज़ार था, नहीं पचपन",
        # nothing at all between the weak number and the amount
        "मुझे बता दो 5 लाख",
        "पचास हज़ार से कम",
        "पचास हज़ार से ज़्यादा",
        "पचास हज़ार रुपये से ऊपर",
        "less than 50,000",
        "more than fifty thousand",
        "under ₹50,000",
        "पचास हज़ार नहीं था",
        "52,000 रुपये नहीं",
        "बावन हज़ार नही",
        "बावन हज़ार ना",
        "not 52,000",
        "no fifty thousand",
        "fifty thousand not",
        "ஐம்பதாயிரம் இல்லை",
        "ಐವತ್ತು ಸಾವಿರ ಅಲ್ಲ",
        "ಐವತ್ತು ಸಾವಿರ ಇಲ್ಲ",
    ],
)
def test_range_alternative_negation_or_comparison_is_ambiguous(text):
    result = parse_amount(text)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason in (X, M)


def test_negated_amount_is_listed():
    result = parse_amount("पचास हज़ार नहीं था")
    assert isinstance(result, Ambiguous) and result.reason == M
    assert [(c.rupees, c.span.text) for c in result.candidates] == [(50_000, "पचास हज़ार")]


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("मेरे लोन से 52,000 रुपये कटे।", 52_000),
        ("नहीं, बावन हज़ार था", 52_000),
        ("नहीं बावन हज़ार था", 52_000),
        ("पचास हज़ार से कटे", 50_000),
        ("पता नहीं, बावन हज़ार होगा", 52_000),  # the negator is in another clause
        ("बावन हज़ार दिए, और कुछ नहीं लिया", 52_000),
        # known and accepted
        ("दो लाख दो", 200_002),
        ("करीब पचास हज़ार", 50_000),
    ],
)
def test_connector_or_negator_elsewhere_does_not_block(text, rupees):
    assert _rupees(text) == rupees


# --- exact=True: the text is the amount and nothing else ------------------------------------------


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("बावन हज़ार", 52_000),
        ("₹52,000", 52_000),
        ("52,000 रुपये", 52_000),
        ("Rs. 52,000/-", 52_000),
        ("डेढ़ लाख रुपये", 150_000),
        ("five lakh twenty thousand rupees", 520_000),
        (" ஐம்பத்திரண்டாயிரம் ரூபாய். ", 52_000),
        ("ಐವತ್ತೆರಡು ಸಾವಿರ ರೂಪಾಯಿ", 52_000),
        ("पोने दो लाख", 175_000),  # a spelling of पौने the lexicon knows
    ],
)
def test_exact_accepts_only_the_amount(text, rupees):
    assert parse_amount(text, exact=True) == parse_amount(text)
    result = parse_amount(text, exact=True)
    assert isinstance(result, Parsed) and result.rupees == rupees


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("पक्का दो लाख", 200_000),  # an unknown word in front: it may change the number
        ("करीब दो लाख", 200_000),
        ("एक लाख बावन हज़ार का", 152_000),
        ("बावन हज़ार नहीं", 52_000),
        ("लोन से 52,000", 52_000),
        ("5 साल 52,000", 52_000),
        ("12% 52,000", 52_000),
        ("एक FD में 52,000 रुपये", 52_000),  # a weak number that the default mode ignores
        ("52,000 यानी बावन हज़ार", 52_000),
        ("fifty two thousand only", 52_000),
    ],
)
def test_exact_rejects_anything_else_and_lists_the_candidate(text, rupees):
    result = parse_amount(text, exact=True)
    assert isinstance(result, Ambiguous), f"{text!r} -> {result}"
    assert result.reason == M
    assert [c.rupees for c in result.candidates] == [rupees]


@pytest.mark.parametrize("text", ["", "पता नहीं", "बावन", "50 से 60 हज़ार", "साथ हज़ार"])
def test_exact_never_turns_another_result_into_parsed(text):
    assert parse_amount(text, exact=True) == parse_amount(text)
    assert not isinstance(parse_amount(text), Parsed)


# --- very long words -------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["ಇಪ್ಪತ್ತ" * 500, "ஆ" * 3000, "இருபத்து" * 400 + " ஆயிரம்"])
def test_overlong_word_is_not_a_number_and_is_fast(text):
    started = time.perf_counter()
    result = parse_amount(text)
    parse_duration_months(text)
    assert time.perf_counter() - started < 1.0
    assert not isinstance(result, Parsed)


@pytest.mark.parametrize("text", ["एक दो", "3 या 4", "एक FD, दो RD", "50 रुपये और 60 रुपये"])
def test_several_distinct_candidates_of_equal_strength_are_ambiguous(text):
    assert isinstance(parse_amount(text), Ambiguous)


def test_arbitrary_text_never_raises_and_a_parsed_span_reads_the_same_by_itself():
    rng = random.Random(20261110)
    pieces = [text for text, _ in [*DIGITS, *ITN, *HINDI, *ENGLISH, *TAMIL, *KANNADA]]
    pieces += ["₹", "%", "/-", ",", "।", "-", "\u200d", "FD", "का", "ie6", "1,2", "லட்சத்தை", "ಸಾವಿರವನ್ನು", "साल"]
    alphabet = "".join(pieces)
    for _ in range(4_000):
        words = [rng.choice(pieces) for _ in range(rng.randint(1, 4))]
        noise = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        text = rng.choice([" ", "", ", "]).join([*words, noise])
        parse_duration_months(text)
        result = parse_amount(text)
        if isinstance(result, Parsed):
            assert text[result.span.start : result.span.end] == result.span.text
            assert _rupees(result.span.text) == result.rupees, text


# --- found by the independent review: a wrong `Parsed` is the one result that is never allowed ---

REFUSED_AFTER_REVIEW = [
    # a negator, comparative or correction that is not next to the number
    "बावन हज़ार तो नहीं था",
    "it was never 52,000",
    "बावन हज़ार से भी ज़्यादा",
    "पचपन हज़ार, सॉरी बावन",
    "पचपन हज़ार या शायद साठ",
    "पता नहीं, शायद बावन हज़ार",
    "ஐம்பதாயிரம் இல்ல",
    # romanised Hindi number and fraction words are not read, so the text is refused
    "saadhe 5 hazaar",
    "paune 2 lakh",
    "sawa 2 lakh",
    "52 hazaar paanch sau",
    "bavan, hazaar",
    # digits we cannot be sure of
    "½ lakh",
    ".5 lakh",
    "₹52.000",
]


@pytest.mark.parametrize("text", REFUSED_AFTER_REVIEW)
def test_review_findings_are_refused_not_guessed(text):
    assert not isinstance(parse_amount(text), Parsed), text


@pytest.mark.parametrize(
    ("text", "rupees"),
    [
        ("सादे तीन हज़ार", 3_500),  # साढ़े as recognisers and typists often spell it
        ("साडे तीन हज़ार", 3_500),
        ("पवने दो लाख", 175_000),
        ("नहीं, पचपन हज़ार", 55_000),  # a correction at read-back
        ("Rs.5 lakh", 500_000),
        ("1.5 lakh", 150_000),
        ("5 lakh ka cover hai", 500_000),
    ],
)
def test_review_fixes_do_not_refuse_what_is_readable(text, rupees):
    result = parse_amount(text)
    assert isinstance(result, Parsed) and result.rupees == rupees, f"{text!r} -> {result}"


def test_a_bare_number_after_a_lakh_is_read_literally_known_limit():
    """In speech "एक लाख बीस" often means 1,20,000. The parser reads 1,00,020; the read-back is the check."""
    result = parse_amount("एक लाख बीस")
    assert isinstance(result, Parsed) and result.rupees == 100_020
