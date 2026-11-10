"""The held-out amounts set (amounts-v2): Hindi and Hinglish, weighted to retail amounts.

`amounts-v1` became a development set when the parser was fixed against it. This set has a new
seed and new carrier sentences, and outside the fraction stratum no amount that v1 has in the
same language. Fraction words allow too few amounts for that (डेढ़ has four), so a fraction item
whose amount v1 also has carries the tag `v1_amount = yes`. Like v1 it never calls the parser
and never chooses an item by what the parser can read.

Strata, per language:
  skipped   an amount with a zero group between two spoken groups ("three lakh two hundred")
  control   the matched pair of a skipped item: same carrier, same leading group, the lower group
            moved up so that no group is skipped ("three lakh two thousand")
  general   retail shapes with no skipped group
  fraction  सवा, डेढ़, ढाई, साढ़े, पौने and their English forms
  large     amounts above the retail band, no skipped group
"""

import random
from decimal import Decimal

from samajh.amounts import spoken_amount
from samajh.evalkit.amounts import grammar
from samajh.evalkit.amounts.grammar import CRORE, HUNDRED, LAKH, THOUSAND
from samajh.types import Language

SEED = 20261111
LANGUAGES = ("hi", "hi-en")
RETAIL_BAND = (500, 500_000)  # rupees, both ends included

# One {amount} slot and no other number word. Carriers 9 to 12 have no currency word. None of
# these sentences is in amounts-v1.
CARRIERS: dict[str, tuple[str, ...]] = {
    "hi": (
        "उन्होंने बताया था कि प्रीमियम {amount} रुपये होगा।",
        "लोन की रकम में से {amount} रुपये बीमा के लिए कट गए।",
        "मुझे लगता है कवर {amount} रुपये का है।",
        "पॉलिसी के लिए {amount} रुपये दिए थे।",
        "किस्त {amount} रुपये की बनती है।",
        "बैंक वालों ने {amount} रुपये सीधे काट लिए।",
        "जहाँ तक याद है, {amount} रुपये लगे थे।",
        "रसीद पर {amount} रुपये लिखा है।",
        "प्रीमियम की रकम {amount} थी।",
        "कुल {amount} का बीमा हुआ है।",
        "हाथ में {amount} आए।",
        "एजेंट ने {amount} बोला था।",
    ),
    "hi-en": (
        "उन्होंने बोला था कि premium {amount} rupees होगा।",
        "loan amount में से {amount} rupees insurance के लिए कट गए।",
        "मुझे लगता है cover {amount} rupees का है।",
        "policy के लिए {amount} rupees pay किए थे।",
        "installment {amount} rupees की बनती है।",
        "bank वालों ने {amount} rupees सीधे deduct कर लिए।",
        "जहाँ तक याद है, {amount} rupees लगे थे।",
        "receipt पर {amount} rupees लिखा है।",
        "premium की amount {amount} थी।",
        "total {amount} का insurance हुआ है।",
        "account में {amount} आए।",
        "agent ने {amount} बोला था।",
    ),
}

_UNITS_1_9 = tuple(range(1, 10))
_ROUND = (*range(10, 21), *range(30, 100, 10))
_IRREGULAR = tuple(c for c in range(21, 100) if c % 10)
_RETAIL_LAKHS = (1, 2, 3, 4)
_BIG_LAKHS = (6, 7, 8, 9, 12, 15, 18, 25, 30, 45, 60)
_CRORES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15)

# (shape, items per language). The first three shapes are the ones v1 found mis-formatted; the
# fourth extends the same pattern one group up.
SKIPPED: tuple[tuple[str, int], ...] = (
    ("lakh_units", 9),
    ("lakh_hundreds", 9),
    ("thousand_units", 10),
    ("crore_thousands", 6),
)
GENERAL: tuple[tuple[str, int], ...] = (
    ("thousand", 8),
    ("hundred", 2),
    ("lakh", 2),
    ("thousand_hundred", 12),
    ("thousand_hundred_rest", 8),
    ("lakh_thousand", 8),
    ("hundred_rest", 4),
    ("lakh_thousand_hundred", 4),
)
LARGE: tuple[tuple[str, int], ...] = (
    ("big_lakh", 2),
    ("big_lakh_thousand", 2),
    ("crore", 2),
    ("crore_lakh", 2),
)

Phrase = tuple[str, str]  # words, multiplier
_SAADHE_HI: tuple[Phrase, ...] = grammar._HI_SAADHE
_SAWA_HI: tuple[Phrase, ...] = (("सवा", "1.25"), *grammar._HI_SAWA)
_PAUNE_HI: tuple[Phrase, ...] = grammar._HI_PAUNE
_HI_UNITS = (
    ("सौ", HUNDRED),
    ("हज़ार", THOUSAND),
    ("हज़ार", THOUSAND),
    ("लाख", LAKH),
    ("लाख", LAKH),
    ("करोड़", CRORE),
)
_MIX_UNITS = (
    ("thousand", THOUSAND),
    ("thousand", THOUSAND),
    ("lakh", LAKH),
    ("lakh", LAKH),
    ("crore", CRORE),
)
_EN_UNITS = (("lakh", LAKH), ("lakh", LAKH), ("lakh", LAKH), ("crore", CRORE))
# (form, items, phrases, units): gold is multiplier x unit.
FRACTIONS: dict[str, tuple[tuple[str, int, tuple[Phrase, ...], tuple[tuple[str, int], ...]], ...]] = {
    "hi": (
        ("sawa", 3, _SAWA_HI, _HI_UNITS),
        ("saadhe", 4, _SAADHE_HI, _HI_UNITS),
        ("paune", 3, _PAUNE_HI, _HI_UNITS),
        ("dedh", 3, (("डेढ़", "1.5"),), _HI_UNITS),
        ("dhai", 3, (("ढाई", "2.5"),), _HI_UNITS),
    ),
    "hi-en": (
        (
            "and_a_half",
            4,
            tuple(
                (f"{word} and a half", f"{n}.5")
                for n, word in enumerate(("one", "two", "three", "four", "five", "six"), 1)
            ),
            _EN_UNITS,
        ),
        (
            "point",
            4,
            (
                ("one point five", "1.5"),
                ("two point five", "2.5"),
                ("three point five", "3.5"),
                ("four point five", "4.5"),
                ("one point two five", "1.25"),
                ("two point seven five", "2.75"),
            ),
            _EN_UNITS,
        ),
        ("dedh", 2, (("डेढ़", "1.5"),), _MIX_UNITS),
        ("dhai", 2, (("ढाई", "2.5"),), _MIX_UNITS),
        ("saadhe", 2, _SAADHE_HI, _MIX_UNITS),
        ("sawa", 1, _SAWA_HI, _MIX_UNITS),
        ("paune", 1, _PAUNE_HI, _MIX_UNITS),
    ),
}


def skips_a_group(rupees: int) -> bool:
    """True when a zero group sits between two non-zero groups: 5,00,200 or 6,025 or 2,00,45,000.

    The groups are the ones Indian amounts are spoken in: crore, lakh, thousand, hundred, below 100.
    """
    crore, rest = divmod(rupees, CRORE)
    lakh, rest = divmod(rest, LAKH)
    thousand, rest = divmod(rest, THOUSAND)
    used = [bool(part) for part in (crore, lakh, thousand, *divmod(rest, HUNDRED))]
    if True not in used:
        return False
    first, last = used.index(True), len(used) - 1 - used[::-1].index(True)
    return not all(used[first : last + 1])


def in_retail_band(rupees: int) -> bool:
    return RETAIL_BAND[0] <= rupees <= RETAIL_BAND[1]


def _mixed(rng: random.Random) -> int:
    """A count below 100: a third each of 1 to 9, teens and round tens, and 21 to 99 irregular."""
    return rng.choice(rng.choice((_UNITS_1_9, _ROUND, _IRREGULAR)))


def _lakhs(rng: random.Random, index: int, of: int) -> int:
    """Retail lakhs for all but the last two items of a shape, which go above the band."""
    return rng.choice(_RETAIL_LAKHS if index < of - 2 else _BIG_LAKHS)


def _skipped_pair(rng: random.Random, shape: str, index: int, of: int) -> tuple[int, int]:
    """(skipped amount, its control). The control keeps the leading group and moves the lower one up."""
    if shape == "lakh_units":
        lakh, rest = _lakhs(rng, index, of), _mixed(rng)
        return lakh * LAKH + rest, lakh * LAKH + rest * THOUSAND
    if shape == "lakh_hundreds":
        lakh, hundred = _lakhs(rng, index, of), rng.choice(_UNITS_1_9)
        return lakh * LAKH + hundred * HUNDRED, lakh * LAKH + hundred * THOUSAND
    if shape == "thousand_units":
        thousand, rest = _mixed(rng), _mixed(rng)
        # A count above 9 cannot be a number of hundreds: fold it into 1 to 9.
        return thousand * THOUSAND + rest, thousand * THOUSAND + ((rest - 1) % 9 + 1) * HUNDRED
    if shape == "crore_thousands":
        crore, thousand = rng.choice(_CRORES), _mixed(rng)
        return crore * CRORE + thousand * THOUSAND, crore * CRORE + thousand * LAKH
    raise ValueError(shape)


def _plain(rng: random.Random, shape: str) -> int:
    hundred, rest = rng.choice(_UNITS_1_9), rng.choice((*_ROUND, *_IRREGULAR, 5, 8))
    match shape:
        case "thousand":
            return _mixed(rng) * THOUSAND
        case "hundred":
            return rng.choice((5, 6, 7, 8, 9)) * HUNDRED
        case "lakh":
            return rng.choice((1, 2, 3, 4, 5)) * LAKH
        case "thousand_hundred":
            return _mixed(rng) * THOUSAND + hundred * HUNDRED
        case "thousand_hundred_rest":
            return _mixed(rng) * THOUSAND + hundred * HUNDRED + rest
        case "lakh_thousand":
            return rng.choice(_RETAIL_LAKHS) * LAKH + _mixed(rng) * THOUSAND
        case "hundred_rest":
            return rng.choice((5, 6, 7, 8, 9)) * HUNDRED + rest
        case "lakh_thousand_hundred":
            return rng.choice(_RETAIL_LAKHS) * LAKH + _mixed(rng) * THOUSAND + hundred * HUNDRED
        case "big_lakh":
            return rng.choice(_BIG_LAKHS) * LAKH
        case "big_lakh_thousand":
            return rng.choice(_BIG_LAKHS) * LAKH + _mixed(rng) * THOUSAND
        case "crore":
            return rng.choice(_CRORES) * CRORE
        case "crore_lakh":
            return rng.choice(_CRORES) * CRORE + _mixed(rng) * LAKH
    raise ValueError(shape)


def _unused(draw, used: set[int]):
    """The first draw whose amounts are all new for this language."""
    for _ in range(500):
        drawn = draw()
        amounts = drawn if isinstance(drawn, tuple) else (drawn,)
        if len(set(amounts)) == len(amounts) and not used.intersection(amounts):
            used.update(amounts)
            return drawn
    raise RuntimeError("no unused amount left for this shape")


def _fractions(rng: random.Random, language: str, used: set[int]) -> list[tuple[int, str, str]]:
    out = []
    spoken: set[str] = set()
    for form, count, phrases, units in FRACTIONS[language]:
        # A unit listed twice in `units` is drawn twice as often.
        options = [
            (int(Decimal(multiplier) * unit), f"{words} {unit_word}")
            for words, multiplier in phrases
            for unit_word, unit in units
            if (Decimal(multiplier) * unit) % 1 == 0
        ]
        for _ in range(count):
            # Distinct wordings, not distinct amounts: "one and a half lakh" and "डेढ़ lakh" may both appear.
            free = [option for option in options if option[1] not in spoken]
            if not free:
                raise RuntimeError(f"no unused {form} wording left in {language}")
            amount, words = rng.choice(free)
            spoken.add(words)
            used.add(amount)
            out.append((amount, words, form))
    return out


def _language_rows(seed: int, language: str) -> list[dict]:
    rng = random.Random(f"{seed}:{language}")
    in_v1 = {row["gold"]["amount_inr"] for row in grammar.generate() if row["language"] == language}
    used: set[int] = set()
    carriers = CARRIERS[language]
    tongue = Language(language)
    rows: list[dict] = []

    def row(
        stratum: str, shape: str, number: int, amount: int, words: str, carrier: int, **tags: str
    ) -> dict:
        return {
            "id": f"amt2-{language}-{stratum}-{number:03d}",
            "language": language,
            "text": carriers[carrier].format(amount=words),
            "gold": {"amount_inr": amount},
            "tags": {
                "stratum": stratum,
                "shape": shape,
                "band": "retail" if in_retail_band(amount) else "outside",
                "carrier": f"{language}-d{carrier + 1:02d}",
                # Voices are balanced inside a block; a skipped item and its control share one.
                "block": "gap" if stratum in ("skipped", "control") else stratum,
                **tags,
            },
        }

    def carrier_cycle(n: int) -> list[int]:
        order = [i % len(carriers) for i in range(n)]
        rng.shuffle(order)
        return order

    # Fractions first: they have the fewest possible amounts.
    fractions = _fractions(rng, language, used)
    for number, ((amount, words, form), carrier) in enumerate(
        zip(fractions, carrier_cycle(len(fractions)), strict=True), start=1
    ):
        seen = "yes" if amount in in_v1 else "no"
        rows.append(row("fraction", form, number, amount, words, carrier, v1_amount=seen))
    used |= in_v1

    pairs = [(shape, i, of) for shape, of in SKIPPED for i in range(of)]
    for number, ((shape, i, of), carrier) in enumerate(
        zip(pairs, carrier_cycle(len(pairs)), strict=True), start=1
    ):
        skipped, control = _unused(lambda s=shape, i=i, of=of: _skipped_pair(rng, s, i, of), used)
        pair = f"{language}-p{number:03d}"
        rows.append(
            row("skipped", shape, number, skipped, spoken_amount(skipped, tongue), carrier, pair=pair)
        )
        rows.append(
            row("control", shape, number, control, spoken_amount(control, tongue), carrier, pair=pair)
        )

    for stratum, shapes in (("general", GENERAL), ("large", LARGE)):
        flat = [shape for shape, of in shapes for _ in range(of)]
        for number, (shape, carrier) in enumerate(zip(flat, carrier_cycle(len(flat)), strict=True), start=1):
            amount = _unused(lambda s=shape: _plain(rng, s), used)
            rows.append(row(stratum, shape, number, amount, spoken_amount(amount, tongue), carrier))
    return rows


def generate(seed: int = SEED) -> list[dict]:
    """280 manifest rows. The order is a seeded shuffle that alternates the two languages, so any
    prefix is a fair small sample of both."""
    by_language = []
    for language in LANGUAGES:
        rows = _language_rows(seed, language)
        random.Random(f"{seed}:{language}:order").shuffle(rows)
        by_language.append(rows)
    return [row for pair in zip(*by_language, strict=True) for row in pair]
