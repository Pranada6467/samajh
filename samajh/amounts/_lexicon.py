"""Number-word tables for Hindi, English (Latin and Devanagari), Tamil and Kannada.

Every table is keyed through `norm_key`, so spelling variants that differ only by nukta,
chandrabindu/anusvara, half-nasal/anusvara, case or ZWJ/ZWNJ need one entry.
The first variant of each entry is the canonical form `spoken_amount` emits.
Tamil and Kannada tables are not human-reviewed.
"""

import re
import unicodedata
from decimal import Decimal
from typing import NamedTuple


class Atom(NamedTuple):
    """One grammar symbol.

    kind: n (number word), d (digits), m (multiplier), pre (Hindi sawa/saadhe/paune),
    pt (decimal point), jf (joins a following quarter/half/three-quarter), and, obl
    (the word before was a joining form that cannot end an amount).
    """

    kind: str
    value: Decimal = Decimal(0)
    joins: bool = False  # tens that take a following unit digit: "fifty two"


def n(value: int | str, joins: bool = False) -> Atom:
    return Atom("n", Decimal(value), joins)


def m(value: int) -> Atom:
    return Atom("m", Decimal(value))


HUNDRED, THOUSAND, LAKH, MILLION, CRORE = 100, 1_000, 100_000, 1_000_000, 10_000_000
PT, JF, AND, OBL = Atom("pt"), Atom("jf"), Atom("and"), Atom("obl")

_DROP = {0x200C: None, 0x200D: None, 0x093C: None, 0x0901: 0x0902}
_HALF_NASAL = re.compile("[ङञणनम]्(?=[क-ह])")


def norm_key(word: str) -> str:
    """Lookup key: NFC, no ZWJ/ZWNJ, no nukta, chandrabindu and half-nasals as anusvara, casefolded."""
    key = unicodedata.normalize("NFC", word).translate(_DROP).casefold()
    return _HALF_NASAL.sub("ं", key)


class Word(NamedTuple):
    """A word that is a whole token by itself.

    kind: num | and | cur (currency word) | curpfx (currency marker that may precede digits)
    | dur | pct | pctpfx | vague | art | glue (unit letter valid only glued to digits)
    | unitafter (सो) | conn | neg | negpre | cmp | cmpdirect | cmppre (see the table below)
    | plain (an ordinary word that cannot be a number: a Tamil or Kannada noun in the ablative)
    | times (a noun that counts occurrences: "एक बार", "one time").
    """

    kind: str
    atoms: tuple[Atom, ...] = ()
    months: Decimal | None = None  # dur only; None for units that are not months (days, hours)
    days: Decimal | None = None  # dur only; a month counts as 30 days; None for hours and minutes


WORDS: dict[str, Word] = {}


def _add(table: dict, words: str, entry) -> None:
    for word in words.replace("|", " ").split():
        key = norm_key(word)
        if table.setdefault(key, entry) != entry:
            raise ValueError(f"lexicon collision on {word!r}")


def _variants(table: str) -> list[list[str]]:
    return [cell.split("|") for cell in table.split()]


def _words(table: str) -> list[str]:
    return table.split()


# --- Hindi ---------------------------------------------------------------------

_HI = _variants("""
शून्य एक दो तीन चार पाँच छह|छः|छे|छै सात आठ नौ
दस ग्यारह|ग्यारा बारह|बारा तेरह चौदह|चौदा पंद्रह|पंदरह|पंद्रा सोलह|सोला सत्रह|सतरह|सत्रा अठारह|अट्ठारह|अठारा उन्नीस
बीस इक्कीस बाईस|बाइस तेईस|तेइस चौबीस पच्चीस|पचीस छब्बीस सत्ताईस|सत्ताइस अट्ठाईस|अठाईस|अट्ठाइस|अठाइस उनतीस|उन्तीस
तीस इकतीस|इकत्तीस बत्तीस तैंतीस|तैतीस|तेंतीस चौंतीस|चौतीस पैंतीस|पैतीस छत्तीस सैंतीस|सैतीस अड़तीस|अढ़तीस उनतालीस|उन्तालीस
चालीस इकतालीस बयालीस|बयालिस तैंतालीस|तैतालीस|तिरालीस चौवालीस|चवालीस|चौंवालीस पैंतालीस|पैतालीस छियालीस|छयालीस सैंतालीस|सैतालीस अड़तालीस|अढ़तालीस उनचास|उन्चास
पचास इक्यावन|इक्कावन बावन तिरपन|तिरेपन चौवन|चौअन पचपन छप्पन सत्तावन अट्ठावन|अठावन उनसठ
साठ इकसठ बासठ तिरसठ|तिरेसठ चौंसठ|चौसठ पैंसठ|पैसठ छियासठ|छयासठ सड़सठ|सरसठ अड़सठ|अठसठ उनहत्तर|उन्हत्तर
सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर|पिचहत्तर|पिछत्तर छिहत्तर सतहत्तर अठहत्तर उनासी|उन्यासी
अस्सी|असी इक्यासी बयासी तिरासी चौरासी पचासी|पिचासी छियासी सत्तासी|सतासी अट्ठासी|अठासी नवासी
नब्बे|नव्वे|नबे इक्यानवे|इक्यानबे बानवे|बानबे तिरानवे|तिरानबे चौरानवे|चौरानबे पंचानवे|पचानवे|पंचानबे|पिचानवे|पिचानबे छियानवे|छियानबे सत्तानवे|सत्तानबे अट्ठानवे|अठानवे|अट्ठानबे निन्यानवे|निन्यानबे|निन्नानवे
""")
assert len(_HI) == 100
HI_NUM = [cell[0] for cell in _HI]
HI_UNITS = ((CRORE, "करोड़"), (LAKH, "लाख"), (THOUSAND, "हज़ार"), (HUNDRED, "सौ"))

for _value, _cell in enumerate(_HI):
    _add(WORDS, " ".join(_cell), Word("num", (n(_value),)))
    for _word in _cell:
        if len(_word) > 3 and _word.endswith("ीस"):  # short-i spelling: चालिस, छत्तिस
            _add(WORDS, _word[:-2] + "िस", Word("num", (n(_value),)))
for _value, _word in HI_UNITS:
    _add(WORDS, _word, Word("num", (m(_value),)))
_add(WORDS, "सवा सव्वा", Word("num", (Atom("pre", Decimal("0.25")),)))
_add(WORDS, "साढ़े साड़े साडे सादे", Word("num", (Atom("pre", Decimal("0.5")),)))
_add(WORDS, "पौने पौन पोने पौणे पवने", Word("num", (Atom("pre", Decimal("-0.25")),)))
_add(WORDS, "डेढ़ डेड़", Word("num", (n("1.5"),)))
_add(WORDS, "ढाई अढ़ाई", Word("num", (n("2.5"),)))
_add(WORDS, "आधा आधे", Word("num", (n("0.5"),)))
_add(WORDS, "दशमलव", Word("num", (PT,)))
# "पांच सो": सौ misspelt as the everyday word सो. A unit only between a number and another
# number, a currency word or the end of the phrase (see samajh.amounts._parse).
_add(WORDS, "सो", Word("unitafter", (m(HUNDRED),)))
# "thousands of": a number was meant but none was named.
_add(WORDS, "सैकड़ों हज़ारों लाखों करोड़ों", Word("vague"))
# The speaker is unsure or is correcting themselves: no number next to these is safe to read.
_add(WORDS, "शायद सॉरी सोरी shayad maybe perhaps sorry", Word("vague"))
# Romanised Hindi number and fraction words. Out of scope to read, so a text that has one is
# refused instead of read without it ("saadhe 5 hazaar", "52 hazaar paanch sau"). The list is
# not complete: "ek", "do" and "saath" are left out because they are everyday words.
_add(
    WORDS,
    """
    teen chaar paanch panch chhe chhah saat aath nau das gyarah barah pandrah bees pachees pachis
    tees chalis chalees pachas pachaas bavan baavan bawan pachpan sattar assi nabbe sau
    sawa sava saadhe sadhe saade paune pone pavne dedh derh dhai dhaai adhai aadha adha
    """,
    Word("vague"),
)
# Kannada "tens of", "hundreds of": by sandhi alone ನೂರಾರು would read as ನೂರು + ಆರು = 106.
_add(WORDS, "ಹತ್ತಾರು ನೂರಾರು ಸಾವಿರಾರು ಲಕ್ಷಾಂತರ ಕೋಟ್ಯಂತರ", Word("vague"))

# --- English, Latin script -------------------------------------------------------

EN_NUM = _words("""
zero one two three four five six seven eight nine
ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen
""")
EN_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
EN_UNITS = ((CRORE, "crore"), (LAKH, "lakh"), (THOUSAND, "thousand"), (HUNDRED, "hundred"))

for _value, _word in enumerate(EN_NUM):
    _add(WORDS, _word, Word("num", (n(_value),)))
for _value, _word in enumerate(EN_TENS, start=2):
    _add(WORDS, _word, Word("num", (n(_value * 10, joins=True),)))
_add(WORDS, "fourty", Word("num", (n(40, joins=True),)))
_add(WORDS, "hundred hundreds", Word("num", (m(HUNDRED),)))
_add(WORDS, "thousand thousands hazaar hazar", Word("num", (m(THOUSAND),)))
_add(WORDS, "lakh lac lakhs lacs", Word("num", (m(LAKH),)))
_add(WORDS, "million millions", Word("num", (m(MILLION),)))
_add(WORDS, "crore crores", Word("num", (m(CRORE),)))
_add(WORDS, "point", Word("num", (PT,)))
_add(WORDS, "half", Word("num", (n("0.5"),)))
_add(WORDS, "and", Word("and"))
_add(WORDS, "a an ए अ", Word("art"))  # only read inside "two and a half"
# Romanised Hindi writes "ke/ka" as "k", so the unit letters count only when glued to digits.
_add(WORDS, "k", Word("glue", (m(THOUSAND),)))
_add(WORDS, "cr", Word("glue", (m(CRORE),)))

# --- English number words written in Devanagari (Prisma v3.0 indic-auto does this) ---

_EN_DEVA = _variants("""
ज़ीरो वन टू थ्री फोर फाइव|फाईव सिक्स सेवन|सेवेन एट|ऐट नाइन|नाईन
टेन इलेवन|एलेवन|इलेवेन ट्वेल्व|ट्वेल्फ थर्टीन फोर्टीन|फॉर्टीन फिफ्टीन सिक्सटीन|सिक्स्टीन सेवनटीन|सेवेंटीन|सेवंटीन|सेवेनटीन एटीन|एट्टीन नाइनटीन|नाइंटीन
""")
_EN_DEVA_TENS = _variants(
    "ट्वेंटी|ट्वंटी थर्टी फोर्टी|फॉर्टी फिफ्टी सिक्सटी|सिक्स्टी सेवंटी|सेवेंटी|सेवनटी|सेवेनटी एटी|एट्टी नाइंटी|नाइनटी"
)
assert len(_EN_DEVA) == 20 and len(_EN_DEVA_TENS) == 8
for _value, _cell in enumerate(_EN_DEVA):
    _add(WORDS, " ".join(_cell), Word("num", (n(_value),)))
for _value, _cell in enumerate(_EN_DEVA_TENS, start=2):
    _add(WORDS, " ".join(_cell), Word("num", (n(_value * 10, joins=True),)))
_add(WORDS, "हंड्रेड हंडरेड हंड्रेड्स", Word("num", (m(HUNDRED),)))
_add(WORDS, "थाउज़ेंड थाउज़ंड थाउसेंड थाउसंड थाउज़ेंड्स थाउज़ंड्स थाउसेंड्स", Word("num", (m(THOUSAND),)))
_add(WORDS, "लैक लैख लैक्स", Word("num", (m(LAKH),)))
_add(WORDS, "मिलियन", Word("num", (m(MILLION),)))
_add(WORDS, "क्रोर क्रोर्स", Word("num", (m(CRORE),)))
# A plural unit with no number in front names no amount: "lakhs of rupees".
PLURAL_UNITS = frozenset(
    norm_key(_word)
    for _word in _words("hundreds thousands lakhs lacs millions crores हंड्रेड्स थाउज़ेंड्स थाउज़ंड्स थाउसेंड्स लैक्स क्रोर्स")
)
_add(WORDS, "पॉइंट पोइंट प्वाइंट पाइंट", Word("num", (PT,)))
_add(WORDS, "हाफ", Word("num", (n("0.5"),)))
_add(WORDS, "एंड ऐंड", Word("and"))

# --- words that hedge or join amounts ----------------------------------------------
# Tamil and Kannada entries are not human-reviewed.

# Between two numbers these make a range or a choice: "50 से 60 हज़ार", "बावन या पचपन हज़ार".
_add(WORDS, "से या और लेकर to or se ya அல்லது மற்றும் ಅಥವಾ ಮತ್ತು", Word("conn"))
# Directly after an amount: "पचास हज़ार नहीं था".
_add(WORDS, "नहीं नही नहि ना nahi nahin இல்லை இல்ல ಅಲ್ಲ ಇಲ್ಲ", Word("neg"))
# Directly before or after an amount: "not 52,000".
_add(WORDS, "not no never", Word("negpre"))
# After an amount and a connector: "पचास हज़ार से कम", "50,000 or more".
_add(WORDS, "कम ज़्यादा जादा अधिक ऊपर नीचे more less", Word("cmp"))
# Directly after an amount: "ஐம்பதாயிரம் ரூபாய்க்கு மேல்", "ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿಗಿಂತ ಹೆಚ್ಚು".
_add(WORDS, "மேல் கீழ் குறைவு குறைவாக ಹೆಚ್ಚು ಕಡಿಮೆ", Word("cmpdirect"))
# Directly before an amount: "less than 50,000", "under 50,000".
_add(WORDS, "than under over above below", Word("cmppre"))

# --- currency, durations, percent ------------------------------------------------

_add(WORDS, "rs inr रु ரூ ರೂ", Word("curpfx"))
_add(
    WORDS,
    "rupee rupees rupaye rupay rupiya रुपये रुपए रुपया रुपयों रुपय रूपये रूपए रूपया रुपी रुपीज़ रुपीस रूपी रूपीज़ रूपीस",
    Word("cur"),
)
_YEAR, _MONTH = Decimal(12), Decimal(1)
_DAYS_YEAR, _DAYS_MONTH, _DAYS_WEEK, _DAYS_DAY = Decimal(365), Decimal(30), Decimal(7), Decimal(1)
_add(WORDS, "year years yr yrs साल सालों वर्ष वर्षों बरस ईयर ईयर्स इयर इयर्स", Word("dur", (), _YEAR, _DAYS_YEAR))
_add(WORDS, "month months महीना महीने महीनों माह मंथ मंथ्स", Word("dur", (), _MONTH, _DAYS_MONTH))
_add(WORDS, "day days दिन दिनों डे डेज़", Word("dur", (), None, _DAYS_DAY))
_add(WORDS, "week weeks हफ़्ता हफ़्ते हफ़्तों सप्ताह", Word("dur", (), None, _DAYS_WEEK))
_add(WORDS, "hour hours minute minutes घंटा घंटे घंटों मिनट", Word("dur"))
_add(WORDS, "percent प्रतिशत परसेंट फीसदी फ़ीसद சதவீதம் சதவிகிதம்", Word("pct"))
_add(WORDS, "ಶೇಕಡ ಶೇಕಡಾ", Word("pctpfx"))
# The number before one of these says how often, not how much: "एक बार", "one time".
_add(WORDS, "बार दफ़ा दफ़े मर्तबा टाइम time times baar", Word("times"))
# "एक ही बार": the particle may stand between the number and the noun.
EMPHATIC = frozenset({norm_key("ही")})

# Tamil and Kannada inflect these words, so they match by stem.
STEMS: tuple[tuple[str, Word], ...] = (
    ("ரூபா", Word("cur")),
    ("ರೂಪಾಯಿ", Word("cur")),
    ("வருட", Word("dur", (), _YEAR, _DAYS_YEAR)),
    ("வருஷ", Word("dur", (), _YEAR, _DAYS_YEAR)),
    ("ஆண்டு", Word("dur", (), _YEAR, _DAYS_YEAR)),
    ("மாதம்", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("மாதங்", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("மாதத்", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("மாசம்", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("மாசத்", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("நாள்", Word("dur", (), None, _DAYS_DAY)),
    ("நாட்க", Word("dur", (), None, _DAYS_DAY)),
    ("வாரம்", Word("dur", (), None, _DAYS_WEEK)),
    ("வாரங்", Word("dur", (), None, _DAYS_WEEK)),
    ("ವರ್ಷ", Word("dur", (), _YEAR, _DAYS_YEAR)),
    ("ತಿಂಗಳ", Word("dur", (), _MONTH, _DAYS_MONTH)),
    ("ದಿನಾಂಕ", Word("other")),  # "date", not "day"
    ("ದಿನ", Word("dur", (), None, _DAYS_DAY)),
    ("ವಾರ", Word("dur", (), None, _DAYS_WEEK)),
    ("தடவை", Word("times")),
    ("முறை", Word("times")),
    ("வாட்டி", Word("times")),
    ("ಸಲ", Word("times")),
    ("ಬಾರಿ", Word("times")),
)

# --- Tamil and Kannada morphs (segmented by samajh.amounts._sandhi) ----------------


class Morph(NamedTuple):
    atoms: tuple[Atom, ...]
    oblique: bool = False  # joining form: the next number morph may be written attached
    head: bool = False  # may be written attached after any number morph (units, -ವರೆ)
    suffix_only: bool = False  # never a word by itself


def _numbers(table: dict, cells: list[list[str]], first: int, step: int = 1, joins: bool = False) -> None:
    for i, cell in enumerate(cells):
        _add(table, " ".join(cell), Morph((n(first + i * step, joins),)))


# Tamil -------------------------------------------------------------------------------

_TA_UNITS = _variants("""
ஒன்று|ஒண்ணு|ஒன்னு இரண்டு|ரெண்டு|இரெண்டு|ரண்டு மூன்று|மூணு நான்கு|நாலு ஐந்து|அஞ்சு ஆறு ஏழு|எழு எட்டு ஒன்பது|ஒம்பது
பத்து பதினொன்று|பதினொண்ணு|பதினொன்னு|பதினோரு|பதினொரு பன்னிரண்டு|பன்னிரெண்டு|பன்னெண்டு|பனிரெண்டு
பதிமூன்று|பதின்மூன்று|பதிமூணு பதினான்கு|பதினாலு பதினைந்து|பதினஞ்சு பதினாறு பதினேழு பதினெட்டு பத்தொன்பது|பத்தொம்பது
""")
_TA_TENS = _variants("இருபது முப்பது நாற்பது|நாப்பது ஐம்பது|அம்பது அறுபது எழுபது எண்பது|எம்பது தொண்ணூறு|தொன்னூறு")
_TA_HUNDREDS = _variants(
    "நூறு இருநூறு|இரநூறு முந்நூறு|முன்னூறு நானூறு|நாநூறு ஐநூறு|ஐந்நூறு அறுநூறு எழுநூறு எண்ணூறு தொள்ளாயிரம்"
)
assert len(_TA_UNITS) == 19 and len(_TA_TENS) == 8 and len(_TA_HUNDREDS) == 9
TA_NUM = [""] + [cell[0] for cell in _TA_UNITS]
TA_TENS = [cell[0] for cell in _TA_TENS]
TA_HUNDREDS = [cell[0] for cell in _TA_HUNDREDS]
# Coefficient + thousand forms that plain sandhi does not produce.
TA_THOUSANDS = {1: "ஓராயிரம்", 3: "மூவாயிரம்", 5: "ஐயாயிரம்"}


def ta_oblique(word: str) -> str:
    """Joining form: இருபது -> இருபத்து, நூறு -> நூற்று, ஆயிரம் -> ஆயிரத்து."""
    if word.endswith("ம்"):
        return word[:-2] + "த்து"
    if word.endswith("று"):
        return word[:-2] + "ற்று"
    return word[:-2] + "த்து"


TA: dict[str, Morph] = {}
_numbers(TA, _TA_UNITS, 1)
_numbers(TA, _TA_TENS, 20, 10)
for _i, _cell in enumerate(_TA_TENS):
    for _word in _cell:
        _obl = ta_oblique(_word)
        # தொண்ணூத்தி: colloquial -ற்ற- -> -த்த-
        for _form in (_obl, _obl[:-1] + "ி", _obl.replace("ற்று", "த்து"), _obl.replace("ற்று", "த்தி")):
            _add(TA, _form, Morph((n(20 + _i * 10, joins=True), OBL), oblique=True))
for _i, _cell in enumerate(_TA_HUNDREDS, start=1):
    _coef = () if _i == 1 else (n(_i),)
    for _word in _cell:
        _add(TA, _word, Morph((*_coef, m(HUNDRED)), head=_i == 1))
        _obl = ta_oblique(_word)
        for _form in (_obl, _obl[:-1] + "ி", _obl.replace("ற்று", "த்து"), _obl.replace("ற்று", "த்தி")):
            _add(TA, _form, Morph((*_coef, m(HUNDRED), OBL), oblique=True, head=_i == 1))
for _coef, _forms in (
    ((), "ஆயிரம்"),
    ((n(1),), "ஓராயிரம் ஒராயிரம்"),
    ((n(2),), "ஈராயிரம்"),
    ((n(3),), "மூவாயிரம்"),
    ((n(5),), "ஐயாயிரம்"),
    ((n(9),), "ஒன்பதினாயிரம்"),
    ((n(10),), "பதினாயிரம்"),
):
    for _word in _forms.split():
        _add(TA, _word, Morph((*_coef, m(THOUSAND)), head=not _coef))
        _obl = ta_oblique(_word)
        _add(TA, f"{_obl} {_obl[:-1]}ி", Morph((*_coef, m(THOUSAND), OBL), oblique=True, head=not _coef))
for _word in ["லட்சம்", "லக்ஷம்", "இலட்சம்", "லச்சம்"]:
    _add(TA, _word, Morph((m(LAKH),), head=True))
    _obl = ta_oblique(_word)
    _add(TA, f"{_obl} {_obl[:-1]}ி", Morph((m(LAKH), OBL), oblique=True, head=True))
_add(TA, "கோடி", Morph((m(CRORE),), head=True))
_add(TA, "கோடியே", Morph((m(CRORE), OBL), oblique=True, head=True))
# ஒரு is "one" only before a noun or unit, and also the article "a": it cannot end a number.
# ஒரே ("only one, a single": ஒரே தடவை) behaves the same.
TA_ONE_BEFORE_NOUN = (n(1), OBL)
_add(TA, "ஒரு ஒரே", Morph(TA_ONE_BEFORE_NOUN))
_add(TA, "அரை", Morph((n("0.5"),)))
_add(TA, "கால்", Morph((n("0.25"),)))
_add(TA, "முக்கால்", Morph((n("0.75"),)))
_add(TA, "ஏ", Morph((JF,), oblique=True, suffix_only=True))  # ஒன்றே கால் = 1.25
_add(TA, "பூஜ்யம் பூஜ்ஜியம்", Morph((n(0),)))
_add(TA, "புள்ளி பாயிண்ட்", Morph((PT,)))

# Kannada -----------------------------------------------------------------------------

_KN_UNITS = _variants("""
ಒಂದು ಎರಡು|ಎರಡ್ ಮೂರು ನಾಲ್ಕು|ನಾಕು ಐದು|ಐದ್ ಆರು ಏಳು ಎಂಟು ಒಂಬತ್ತು|ಒಂಭತ್ತು
ಹತ್ತು ಹನ್ನೊಂದು ಹನ್ನೆರಡು ಹದಿಮೂರು ಹದಿನಾಲ್ಕು ಹದಿನೈದು ಹದಿನಾರು ಹದಿನೇಳು ಹದಿನೆಂಟು ಹತ್ತೊಂಬತ್ತು|ಹತ್ತೊಂಭತ್ತು
""")
_KN_TENS = _variants("ಇಪ್ಪತ್ತು ಮೂವತ್ತು ನಲವತ್ತು|ನಲ್ವತ್ತು ಐವತ್ತು ಅರವತ್ತು|ಅರುವತ್ತು ಎಪ್ಪತ್ತು ಎಂಬತ್ತು|ಎಂಭತ್ತು ತೊಂಬತ್ತು|ತೊಂಭತ್ತು")
_KN_HUNDREDS = _variants(
    "ನೂರು ಇನ್ನೂರು ಮುನ್ನೂರು ನಾನೂರು|ನಾಲ್ನೂರು|ನಾನ್ನೂರು ಐನೂರು|ಐನ್ನೂರು ಆರುನೂರು|ಆರ್ನೂರು ಏಳುನೂರು|ಏಳ್ನೂರು ಎಂಟುನೂರು|ಎಂಟ್ನೂರು ಒಂಬೈನೂರು|ಒಂಭೈನೂರು"
)
assert len(_KN_UNITS) == 19 and len(_KN_TENS) == 8 and len(_KN_HUNDREDS) == 9
KN_NUM = [""] + [cell[0] for cell in _KN_UNITS]
KN_TENS = [cell[0] for cell in _KN_TENS]
KN_HUNDREDS = [cell[0] for cell in _KN_HUNDREDS]

KN: dict[str, Morph] = {}
_numbers(KN, _KN_UNITS, 1)
_numbers(KN, _KN_TENS, 20, 10, joins=True)
for _i, _cell in enumerate(_KN_TENS):
    for _word in _cell:
        # ಇಪ್ಪತ್ತ / ಇಪ್ಪತ್ / ಇಪ್ಪತ್ತ್ (Prisma v2.5 writes the virama) + ಮೂರು
        _add(
            KN,
            f"{_word[:-1]} {_word[:-2]} {_word[:-1]}್",
            Morph((n(20 + _i * 10, joins=True), OBL), oblique=True),
        )
for _i, _cell in enumerate(_KN_HUNDREDS, start=1):
    _coef = () if _i == 1 else (n(_i),)
    for _word in _cell:
        _add(KN, _word, Morph((*_coef, m(HUNDRED)), head=_i == 1))
        # ನೂರ ಐವತ್ತು. Also the genitive ("of a hundred"), so it may end an amount.
        _add(KN, f"{_word[:-1]} {_word[:-1]}ಾ", Morph((*_coef, m(HUNDRED)), oblique=True, head=_i == 1))
# The -ದ/-ಯ forms join a following number and are also the genitive, so they may end an amount.
for _value, _word, _obl in ((THOUSAND, "ಸಾವಿರ", "ಸಾವಿರದ"), (LAKH, "ಲಕ್ಷ", "ಲಕ್ಷದ"), (CRORE, "ಕೋಟಿ", "ಕೋಟಿಯ")):
    _add(KN, _word, Morph((m(_value),), head=True))
    _add(KN, _obl, Morph((m(_value),), oblique=True, head=True))
_add(KN, "ಸಾವ್ರ", Morph((m(THOUSAND),), head=True))  # colloquial ಸಾವಿರ
_add(KN, "ಅರ್ಧ", Morph((n("0.5"),)))
_add(KN, "ಕಾಲು", Morph((n("0.25"),), head=True))
_add(KN, "ಮುಕ್ಕಾಲು", Morph((n("0.75"),), head=True))
_add(KN, "ವರೆ", Morph((n("0.5"),), head=True, suffix_only=True))  # ಒಂದುವರೆ = 1.5
_add(KN, "ಸೊನ್ನೆ", Morph((n(0),)))
_add(KN, "ಪಾಯಿಂಟ್", Morph((PT,)))
