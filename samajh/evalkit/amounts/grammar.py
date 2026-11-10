"""Seeded test set of spoken rupee amounts: one amount per sentence, the integer as gold.

The set scores `samajh.amounts.parse_amount`, so nothing here may call the parser or choose
items by what it can read. Tamil and Kannada text is not human-reviewed.
"""

import json
import random
from decimal import Decimal

from samajh.amounts import spoken_amount
from samajh.types import Language

HUNDRED, THOUSAND, LAKH, CRORE = 100, 1_000, 100_000, 10_000_000
PER_STRATUM = 15
STRATA = ("plain", "lakh_crore", "fraction", "irregular_21_99")
_ID_PART = {"plain": "plain", "lakh_crore": "lc", "fraction": "frac", "irregular_21_99": "irr"}

# Carriers: one {amount} slot, no other number word. Four of each twelve have no currency word.
CARRIERS: dict[str, tuple[str, ...]] = {
    "hi": (
        "मेरे लोन से {amount} रुपये काटे गए।",
        "{amount} रुपये का लोन मिला था।",
        "प्रीमियम {amount} का था।",
        "बीमा का प्रीमियम {amount} रुपये है।",
        "मेरी ईएमआई {amount} रुपये है।",
        "{amount} का कवर बताया था।",
        "खाते से कटे {amount} रुपये।",
        "हर महीने किस्त {amount} की है।",
        "बीमा कवर {amount} रुपये का है।",
        "मुझे लोन मिला {amount} का।",
        "उन्होंने बीमा के {amount} रुपये लिए।",
        "मेरा लोन {amount} रुपये का है।",
    ),
    "hi-en": (
        "मेरे loan से {amount} rupees कटे।",
        "{amount} rupees का loan मिला था।",
        "premium {amount} का था।",
        "insurance का premium {amount} rupees है।",
        "मेरी EMI {amount} rupees है।",
        "{amount} का cover बताया था।",
        "account से कटे {amount} rupees।",
        "हर महीने EMI {amount} की है।",
        "insurance cover {amount} rupees का है।",
        "मुझे loan मिला {amount} का।",
        "loan के साथ {amount} rupees का insurance दिया।",
        "मेरा loan {amount} rupees का है।",
    ),
    "ta": (
        "கடனில் {amount} ரூபாய் கழித்தார்கள்.",
        "{amount} ரூபாய் கடன் வாங்கினேன்.",
        "{amount} ரூபாய் பிரீமியம் கட்டினேன்.",
        "என் மாத தவணை {amount} ரூபாய்.",
        "காப்பீட்டுத் தொகை {amount} ரூபாய் என்றார்கள்.",
        "எனக்கு {amount} ரூபாய் கடன் கிடைத்தது.",
        "பிரீமியமாக {amount} ரூபாய் பிடித்தார்கள்.",
        "கணக்கிலிருந்து {amount} ரூபாய் எடுத்தார்கள்.",
        "{amount} கடன் வாங்கினேன்.",
        "என் பிரீமியம் {amount}.",
        "{amount} காப்பீடு என்று சொன்னார்கள்.",
        "இஎம்ஐ {amount} கட்டுகிறேன்.",
    ),
    "kn": (
        "ಸಾಲದಿಂದ {amount} ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು.",
        "{amount} ರೂಪಾಯಿ ಸಾಲ ತೆಗೆದುಕೊಂಡೆ.",
        "{amount} ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ.",
        "ನನ್ನ ತಿಂಗಳ ಕಂತು {amount} ರೂಪಾಯಿ.",
        "ವಿಮೆ ಮೊತ್ತ {amount} ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು.",
        "ನನಗೆ {amount} ರೂಪಾಯಿ ಸಾಲ ಸಿಕ್ಕಿತು.",
        "ಪ್ರೀಮಿಯಂ ಎಂದು {amount} ರೂಪಾಯಿ ತೆಗೆದುಕೊಂಡರು.",
        "ಖಾತೆಯಿಂದ {amount} ರೂಪಾಯಿ ಕಡಿತವಾಯಿತು.",
        "{amount} ಸಾಲ ತೆಗೆದುಕೊಂಡೆ.",
        "ನನ್ನ ಪ್ರೀಮಿಯಂ {amount}.",
        "{amount} ವಿಮೆ ಎಂದು ಹೇಳಿದರು.",
        "ಇಎಂಐ {amount} ಕಟ್ಟುತ್ತಿದ್ದೇನೆ.",
    ),
}

# Canonical strata: a shape is a tuple of (unit, pool of counts); the amount is the sum of count x unit.
_ONES = tuple(range(1, 10))
_REGULAR = (*range(1, 21), *range(30, 100, 10))
_IRREGULAR = tuple(c for c in range(21, 100) if c % 10)
_ANY = tuple(range(1, 100))
_FIVES = tuple(range(5, 100, 5))
_REST = (10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90)
_CRORES = (*range(1, 21), 30, 40)

Shape = tuple[tuple[int, tuple[int, ...]], ...]
# stratum -> (round shapes, how many round items, compound shapes)
CANONICAL: dict[str, tuple[tuple[Shape, ...], int, tuple[Shape, ...]]] = {
    "plain": (
        (((HUNDRED, _ONES),), ((THOUSAND, _REGULAR),)),
        5,
        (
            ((THOUSAND, _REGULAR), (HUNDRED, _ONES)),
            ((THOUSAND, _ANY), (HUNDRED, _ONES), (1, (50,))),
            ((HUNDRED, _ONES), (1, _REST)),
            ((THOUSAND, _ANY), (HUNDRED, _ONES)),
            ((THOUSAND, _REGULAR), (1, _REST)),
        ),
    ),
    "lakh_crore": (
        (((LAKH, _REGULAR),), ((CRORE, (*_CRORES, 50)),)),
        5,
        (
            ((LAKH, _REGULAR), (THOUSAND, _FIVES)),
            ((CRORE, _CRORES), (LAKH, _FIVES)),
            ((LAKH, _REGULAR), (HUNDRED, _ONES)),
            ((CRORE, _ONES), (LAKH, _REGULAR), (THOUSAND, _FIVES)),
            ((LAKH, _ONES), (THOUSAND, _REGULAR), (HUNDRED, _ONES)),
        ),
    ),
}
# What follows the irregular count: nothing (round) or a second group.
_IRREGULAR_SHAPES: tuple[Shape, ...] = (
    ((THOUSAND, ()),),
    ((THOUSAND, ()), (HUNDRED, _ONES)),
    ((LAKH, ()),),
    ((LAKH, ()), (THOUSAND, _REGULAR)),
)

# Fraction forms: (form tag, items, phrases always used, further phrases sampled, units).
# A phrase is (words, multiplier); gold is multiplier x unit.
Phrases = tuple[tuple[str, str], ...]
Units = tuple[tuple[str, int], ...]
_HI_UNITS: Units = (("सौ", HUNDRED), ("हज़ार", THOUSAND), ("लाख", LAKH), ("करोड़", CRORE))
_EN_UNITS: Units = (("lakh", LAKH), ("crore", CRORE))
_EN_UNITS_3: Units = (("thousand", THOUSAND), *_EN_UNITS)
_TA_UNITS: Units = (("லட்சம்", LAKH), ("கோடி", CRORE))
_TA_UNITS_3: Units = (("ஆயிரம்", THOUSAND), *_TA_UNITS)
_KN_UNITS: Units = (("ಲಕ್ಷ", LAKH), ("ಕೋಟಿ", CRORE))
_KN_UNITS_3: Units = (("ಸಾವಿರ", THOUSAND), *_KN_UNITS)
_HI_SAWA: Phrases = (("सवा दो", "2.25"), ("सवा तीन", "3.25"), ("सवा चार", "4.25"), ("सवा पाँच", "5.25"))
_HI_SAADHE: Phrases = (
    ("साढ़े तीन", "3.5"),
    ("साढ़े चार", "4.5"),
    ("साढ़े पाँच", "5.5"),
    ("साढ़े छह", "6.5"),
    ("साढ़े सात", "7.5"),
    ("साढ़े आठ", "8.5"),
    ("साढ़े नौ", "9.5"),
)
_HI_PAUNE: Phrases = (("पौने दो", "1.75"), ("पौने तीन", "2.75"), ("पौने चार", "3.75"), ("पौने पाँच", "4.75"))

FRACTIONS: dict[str, tuple[tuple[str, int, Phrases, Phrases, Units], ...]] = {
    "hi": (
        ("sawa", 3, (("सवा", "1.25"),), _HI_SAWA, _HI_UNITS),
        ("saadhe", 3, (), _HI_SAADHE, _HI_UNITS),
        ("paune", 3, (), _HI_PAUNE, _HI_UNITS),
        ("dedh", 3, (("डेढ़", "1.5"),), (), _HI_UNITS),
        ("dhai", 3, (("ढाई", "2.5"),), (), _HI_UNITS),
    ),
    "hi-en": (
        (
            "and_a_half",
            3,
            (("one and a half", "1.5"), ("two and a half", "2.5")),
            (("three and a half", "3.5"), ("four and a half", "4.5"), ("six and a half", "6.5")),
            _EN_UNITS,
        ),
        (
            "point",
            4,
            (
                ("one point five", "1.5"),
                ("two point two five", "2.25"),
                ("three point five", "3.5"),
                ("seven point five", "7.5"),
            ),
            (),
            _EN_UNITS,
        ),
        ("dedh", 1, (("डेढ़", "1.5"),), (), _EN_UNITS_3),
        ("dhai", 1, (("ढाई", "2.5"),), (), _EN_UNITS_3),
        ("saadhe", 2, (), _HI_SAADHE, _EN_UNITS_3),
        ("sawa", 2, (), _HI_SAWA, _EN_UNITS_3),
        ("paune", 2, (), _HI_PAUNE, _EN_UNITS_3),
    ),
    "ta": (
        ("half", 2, (("அரை", "0.5"),), (), _TA_UNITS),
        ("three_quarter", 2, (("முக்கால்", "0.75"),), (), _TA_UNITS),
        ("n_quarter", 3, (("ஒன்றேகால்", "1.25"), ("இரண்டேகால்", "2.25")), (), _TA_UNITS),
        ("n_three_quarter", 2, (("ஒன்றே முக்கால்", "1.75"),), (), _TA_UNITS),
        (
            "n_half",
            6,
            (("ஒன்றரை", "1.5"), ("இரண்டரை", "2.5"), ("மூன்றரை", "3.5")),
            (
                ("நான்கரை", "4.5"),
                ("ஐந்தரை", "5.5"),
                ("ஆறரை", "6.5"),
                ("ஏழரை", "7.5"),
                ("எட்டரை", "8.5"),
                ("ஒன்பதரை", "9.5"),
            ),
            _TA_UNITS_3,
        ),
    ),
    "kn": (
        ("half", 2, (("ಅರ್ಧ", "0.5"),), (), _KN_UNITS),
        ("three_quarter", 2, (("ಮುಕ್ಕಾಲು", "0.75"),), (), _KN_UNITS),
        ("n_quarter", 3, (("ಒಂದೂಕಾಲು", "1.25"), ("ಎರಡೂಕಾಲು", "2.25")), (), _KN_UNITS),
        ("n_three_quarter", 2, (("ಒಂದೂ ಮುಕ್ಕಾಲು", "1.75"),), (), _KN_UNITS),
        (
            "n_half",
            6,
            (("ಒಂದೂವರೆ", "1.5"), ("ಎರಡೂವರೆ", "2.5"), ("ಮೂರೂವರೆ", "3.5")),
            (
                ("ನಾಲ್ಕೂವರೆ", "4.5"),
                ("ಐದೂವರೆ", "5.5"),
                ("ಆರೂವರೆ", "6.5"),
                ("ಏಳೂವರೆ", "7.5"),
                ("ಎಂಟೂವರೆ", "8.5"),
                ("ಒಂಬತ್ತೂವರೆ", "9.5"),
            ),
            _KN_UNITS_3,
        ),
    ),
}

Item = tuple[int, str, str, str]  # amount, amount words, round, form


def _draw(rng: random.Random, shapes: tuple[Shape, ...], start: int, used: set[int]) -> tuple[int, str]:
    """An unused amount from the shape at `start`, moving to the next shape only if that one is used up."""
    for k in range(len(shapes)):
        shape = shapes[(start + k) % len(shapes)]
        for _ in range(50):
            amount = sum(unit * rng.choice(pool) for unit, pool in shape)
            if amount not in used:
                used.add(amount)
                return amount, "yes" if len(shape) == 1 else "no"
    raise RuntimeError("no unused amount left in these shapes")


def _canonical(rng: random.Random, language: str, stratum: str, used: set[int]) -> list[Item]:
    round_shapes, n_round, compound = CANONICAL[stratum]
    drawn = [_draw(rng, round_shapes, i, used) for i in range(n_round)]
    drawn += [_draw(rng, compound, i, used) for i in range(PER_STRATUM - n_round)]
    return [
        (amount, spoken_amount(amount, Language(language)), is_round, "canonical")
        for amount, is_round in drawn
    ]


def _irregular(rng: random.Random, language: str, used: set[int]) -> list[Item]:
    """15 distinct counts: four of 29..89, one from every decade, three more."""
    counts = rng.sample(range(29, 99, 10), 4)
    counts += [decade * 10 + rng.randint(1, 8) for decade in range(2, 10)]
    counts += rng.sample([c for c in _IRREGULAR if c not in counts], PER_STRATUM - len(counts))
    rng.shuffle(counts)
    items = []
    for i, count in enumerate(counts):
        shapes = tuple(((shape[0][0], (count,)), *shape[1:]) for shape in _IRREGULAR_SHAPES)
        amount, is_round = _draw(rng, shapes, i, used)
        items.append((amount, spoken_amount(amount, Language(language)), is_round, "canonical"))
    return items


def _fraction(rng: random.Random, language: str, used: set[int]) -> list[Item]:
    items = []
    for form, count, always, further, units in FRACTIONS[language]:
        phrases = [*always, *rng.sample(further, min(len(further), max(0, count - len(always))))]
        units = rng.sample(units, len(units))
        for i in range(count):
            words, multiplier = phrases[i % len(phrases)]
            for k in range(len(units)):
                unit_word, unit = units[(i + k) % len(units)]
                value = Decimal(multiplier) * unit
                if value == value.to_integral_value() and int(value) not in used:
                    break
            else:
                raise RuntimeError(f"no unused unit for {words}")
            used.add(int(value))
            items.append((int(value), f"{words} {unit_word}", "yes", form))
    return items


def _language_rows(seed: int, language: str) -> dict[str, list[dict]]:
    rng = random.Random(f"{seed}:{language}")
    used: set[int] = set()
    # Fractions first: they have the fewest possible amounts, so the other strata draw around them.
    items = {"fraction": _fraction(rng, language, used), "irregular_21_99": _irregular(rng, language, used)}
    items |= {stratum: _canonical(rng, language, stratum, used) for stratum in CANONICAL}
    templates = CARRIERS[language]
    carriers = [i % len(templates) for i in range(PER_STRATUM * len(STRATA))]
    rng.shuffle(carriers)
    rows: dict[str, list[dict]] = {}
    for s, stratum in enumerate(STRATA):
        folds = ["0"] * 8 + ["1"] * 7
        rng.shuffle(folds)
        rows[stratum] = []
        for i, (amount, words, is_round, form) in enumerate(items[stratum]):
            carrier = carriers[s * PER_STRATUM + i]
            rows[stratum].append(
                {
                    "id": f"amt-{language}-{_ID_PART[stratum]}-{i + 1:02d}",
                    "language": language,
                    "text": templates[carrier].format(amount=words),
                    "gold": {"amount_inr": amount},
                    "tags": {
                        "stratum": stratum,
                        "round": is_round,
                        "form": form,
                        "carrier": f"{language}-c{carrier + 1:02d}",
                        "fold": folds[i],
                    },
                }
            )
    return rows


def generate(seed: int = 20261110) -> list[dict]:
    """240 manifest rows, interleaved by language then stratum so any prefix is a fair small sample."""
    by_language = [_language_rows(seed, language) for language in CARRIERS]
    return [
        rows[STRATA[(i + offset) % len(STRATA)]][i // len(STRATA)]
        for i in range(PER_STRATUM * len(STRATA))
        for offset, rows in enumerate(by_language)
    ]


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")
