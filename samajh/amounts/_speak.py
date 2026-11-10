"""Read-back forms: canonical compositional words, no fraction words."""

from samajh.amounts._lexicon import (
    CRORE,
    EN_NUM,
    EN_TENS,
    EN_UNITS,
    HI_NUM,
    HI_UNITS,
    HUNDRED,
    KN_HUNDREDS,
    KN_NUM,
    KN_TENS,
    LAKH,
    TA_HUNDREDS,
    TA_NUM,
    TA_TENS,
    TA_THOUSANDS,
    THOUSAND,
    ta_oblique,
)
from samajh.amounts._sandhi import KANNADA, TAMIL, fuse
from samajh.types import Language

NOT_HUMAN_REVIEWED: frozenset[Language] = frozenset({Language.ta, Language.kn})
_LIMIT = 1_000_000_000


def format_inr(rupees: int) -> str:
    """Indian digit grouping, no rupee sign: 520000 -> "5,20,000"."""
    if rupees < 0:
        raise ValueError("format_inr takes a non-negative amount")
    digits = str(rupees)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([*groups, tail])


def _split(rupees: int) -> tuple[int, int, int, int, int]:
    crore, rest = divmod(rupees, CRORE)
    lakh, rest = divmod(rest, LAKH)
    thousand, rest = divmod(rest, THOUSAND)
    return crore, lakh, thousand, *divmod(rest, HUNDRED)


def _en_below_100(value: int) -> str:
    if value < 20:
        return EN_NUM[value]
    tens, unit = divmod(value, 10)
    return EN_TENS[tens - 2] + (f" {EN_NUM[unit]}" if unit else "")


def _by_units(rupees: int, units, below_100) -> str:
    parts = [f"{below_100(count)} {word}" for count, (_, word) in zip(_split(rupees), units) if count]
    return " ".join([*parts, below_100(rupees % 100)] if rupees % 100 else parts)


def _ta_below_100(value: int, last: list[str] = TA_NUM) -> str:
    """`last` supplies the final digit's form, so the same rule builds இருபத்தொரு and இருபத்தோராயிரம்."""
    if value < 20:
        return last[value] if value < len(last) and last[value] else TA_NUM[value]
    tens, unit = divmod(value, 10)
    if not unit:
        return TA_TENS[tens - 2]
    oblique, word = ta_oblique(TA_TENS[tens - 2]), last[unit]
    fused = fuse(TAMIL, oblique, word)
    return fused if fused != oblique + word else f"{oblique} {word}"


# Counting forms of one and eleven: ஒரு லட்சம், இருபத்தொரு லட்சம், பதினொரு லட்சம்.
_TA_ONE = ["", "ஒரு"] + TA_NUM[2:11] + ["பதினொரு"]
_TA_UNIT_THOUSANDS = [""] + [TA_THOUSANDS.get(d) or fuse(TAMIL, TA_NUM[d], "ஆயிரம்") for d in range(1, 10)]


def _ta_thousands(count: int) -> str:
    if count == 1:
        return "ஆயிரம்"
    if count == 11:
        return "பதினோராயிரம்"
    if count < 10 or count > 20 and count % 10:
        return _ta_below_100(count, _TA_UNIT_THOUSANDS)
    return fuse(TAMIL, _ta_below_100(count), "ஆயிரம்")


def _ta(rupees: int) -> str:
    """Tamil read-back. Best effort, not human-reviewed."""
    crore, lakh, thousand, hundred, rest = _split(rupees)
    parts = []  # (form, form when more follows)
    if crore:
        parts.append((f"{_ta_below_100(crore, _TA_ONE)} கோடி", f"{_ta_below_100(crore, _TA_ONE)} கோடியே"))
    if lakh:
        parts.append((f"{_ta_below_100(lakh, _TA_ONE)} லட்சம்", f"{_ta_below_100(lakh, _TA_ONE)} லட்சத்து"))
    if thousand:
        parts.append((_ta_thousands(thousand), ta_oblique(_ta_thousands(thousand))))
    if hundred:
        parts.append((TA_HUNDREDS[hundred - 1], ta_oblique(TA_HUNDREDS[hundred - 1])))
    if rest:
        parts.append((_ta_below_100(rest), ""))
    return " ".join([*(joining for _, joining in parts[:-1]), parts[-1][0]])


def _kn_below_100(value: int) -> str:
    if value < 20:
        return KN_NUM[value]
    tens, unit = divmod(value, 10)
    if not unit:
        return KN_TENS[tens - 2]
    fused = fuse(KANNADA, KN_TENS[tens - 2], KN_NUM[unit])
    # Before a consonant the tens word only drops its final u: ಇಪ್ಪತ್ತಮೂರು.
    return fused if fused != KN_TENS[tens - 2] + KN_NUM[unit] else KN_TENS[tens - 2][:-1] + KN_NUM[unit]


def _kn(rupees: int) -> str:
    """Kannada read-back. Best effort, not human-reviewed."""
    crore, lakh, thousand, hundred, rest = _split(rupees)
    parts = []  # (form, form when more follows)
    if crore:
        parts.append((f"{_kn_below_100(crore)} ಕೋಟಿ",) * 2)
    if lakh:
        parts.append((f"{_kn_below_100(lakh)} ಲಕ್ಷ", f"{_kn_below_100(lakh)} ಲಕ್ಷದ"))
    if thousand:
        parts.append((f"{_kn_below_100(thousand)} ಸಾವಿರ", f"{_kn_below_100(thousand)} ಸಾವಿರದ"))
    if hundred:
        parts.append((KN_HUNDREDS[hundred - 1], KN_HUNDREDS[hundred - 1][:-1]))
    if rest:
        parts.append((_kn_below_100(rest), ""))
    return " ".join([*(joining for _, joining in parts[:-1]), parts[-1][0]])


def spoken_amount(rupees: int, language: Language) -> str:
    """The amount in words for the read-back, in the language's own script.

    Canonical and compositional, never a fraction word: 175000 in Hindi is
    "एक लाख पचहत्तर हज़ार", not "पौने दो लाख", so the customer hears the amount a second way.
    `hi-en` is English words with Indian units. Tamil and Kannada output is best effort and
    not human-reviewed (see `NOT_HUMAN_REVIEWED`). Raises ValueError outside 1 <= rupees < 100 crore.
    """
    if not 1 <= rupees < _LIMIT:
        raise ValueError(f"spoken_amount supports 1 <= rupees < {_LIMIT}, got {rupees}")
    match language:
        case Language.hi:
            return _by_units(rupees, HI_UNITS, HI_NUM.__getitem__)
        case Language.hi_en:
            return _by_units(rupees, EN_UNITS, _en_below_100)
        case Language.ta:
            return _ta(rupees)
        case Language.kn:
            return _kn(rupees)
