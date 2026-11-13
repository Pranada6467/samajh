"""Hedged amounts and narrow ranges, and two markers on answers: doubt and "as long as the loan".

`parse_amount` refuses "शायद बावन हज़ार" and "पचास से बावन हज़ार" on purpose: neither names one
amount. A customer who says either has still answered. `parse_approx_amount` reads them as an
`Approximate` (low, high) so the rules can compare the record with the range and still ask for a
read-back. It never widens what `parse_amount` accepts as exact, and a correction, a comparison,
a negator or a wide range stays `Ambiguous`.

Hindi, Hinglish and English only. Tamil and Kannada doubt words are not listed (iteration-2
scope), so a Tamil or Kannada hedge stays refused, as before.
"""

import re
from decimal import Decimal
from typing import ClassVar, Literal

from samajh.amounts._grammar import evaluate
from samajh.amounts._lexicon import Atom, near_coefficient, near_fraction, near_unit, norm_key
from samajh.amounts._parse import (
    _CURRENCY,
    _GAP,
    CLAUSE_END,
    AmbiguityReason,
    Ambiguous,
    AmountResult,
    NoAmount,
    Parsed,
    Span,
    _sorry_counts,
    parse_amount,
    takes_coefficient,
)
from samajh.amounts._text import Tok, scan
from samajh.types import Frozen

# A range whose high end is more than this many times its low end says too little to compare
# with a record. The parser refuses it and the rules never pass it: this is the one place.
MAX_RANGE_RATIO = 2


def too_wide(low: int, high: int) -> bool:
    """A spoken range too wide to be compared with the record: "दो से पांच लाख"."""
    return high > MAX_RANGE_RATIO * low


class Approximate(Frozen):
    """An amount said as "about X" (`low == high`) or as a narrow range "X to Y" (`low < high`)."""

    status: Literal["approximate"] = "approximate"
    low: int
    high: int
    span: Span
    bound: bool = False  # "करीब पचास हज़ार तक": a ceiling, as `Parsed.bound`
    added_later: ClassVar[frozenset[str]] = frozenset({"bound"})


# A letter in any script we read: Python's \w leaves out Indic vowel signs. The danda is not one.
_L = "[\\wऀ-ॣ०-෿]"
_N = "़?"  # an optional nukta: क़रीब and करीब are one word
_DOUBT_PHRASES = (
    # Hindi, Devanagari
    rf"के\s+(?:आस\s*-?\s*पास|क{_N}रीब)",
    r"आस\s*-?\s*पास",
    rf"त?क{_N}रीबन?",
    r"लगभग",
    r"शायद",
    rf"अंदा[जज]{_N}न",
    rf"मेरे\s+ख{_N}याल\s+से",
    r"(?:मुझे\s+|ऐसा\s+)?(?:लगता|लगती|लग\s+रहा|लग\s+रही)\s+है(?:\s+कि)?",
    # Hinglish and English, Latin
    r"(?:ke\s+)?(?:aas\s*-?\s*paas|aaspaas|aspaas|kareeb(?:an)?|karib(?:an)?)",
    r"lagbhag|lagbag|taqreeban|takreeban|takriban|shayad|shaayad",
    r"(?:mujhe\s+)?lag(?:ta|ti|\s+raha|\s+rahi)\s+hai(?:\s+ki)?",
    r"maybe|perhaps|probably|approximately|approx|roughly|around|about|nearly|almost",
    r"i\s+think|i\s+guess|i\s+believe|something\s+like",
)
_DOUBT = re.compile(rf"(?<!{_L})(?:{'|'.join(_DOUBT_PHRASES)})(?!{_L})")

# Doubt about exactness ("पक्का नहीं पता", "ठीक से याद नहीं", "exact yaad nahi"). Only the hedge marker
# reads it (`has_doubt_word(..., exactness=True)`): it never makes a figure approximate.
_EXACT_WORD = (
    r"(?:पक्का|पक्की|ठीक\s+से|सही\s+से|pakka|pakki|theek\s+se|thik\s+se|sahi\s+se|exact|exactly"
    rf"|ए[गक]्ज{_N}ैक्ट(?:ली)?)"  # एग्ज़ैक्ट, एग्जैक्ट, एक्ज़ैक्ट, एग्ज़ैक्टली; a nukta either way
)
_DONT_KNOW = r"(?:नहीं|नही|nahi|nahin|nhi)"
_KNOW = r"(?:पता|मालूम|याद|pata|maloom|malum|yaad|yad)"
_EXACTNESS = re.compile(
    rf"(?<!{_L})(?:{_EXACT_WORD}\s+(?:{_DONT_KNOW}\s+{_KNOW}|{_KNOW}\s+{_DONT_KNOW}|{_DONT_KNOW})"
    rf"|not\s+sure|not\s+exactly|don'?t\s+remember\s+exactly)(?!{_L})"
)

_LOAN = r"(?:लोन|ऋण|क़?र्ज़?|loan)"
_TENURE_PHRASES = (
    rf"जब\s+तक\s+{_LOAN}\s+(?:चलेगा|चले|चलता|है|रहेगा|रहे)",
    rf"जितने\s+(?:दिन|साल|समय)\s+{_LOAN}",
    rf"{_LOAN}\s+(?:जितना|जितने|जितनी)",
    rf"{_LOAN}\s+की\s+(?:अवधि|मियाद|टेन्योर|टेन्यूर)",
    rf"{_LOAN}\s+(?:ख{_N}त्म|खतम|पूरा|बंद)\s+होने\s+तक",
    rf"{_LOAN}\s+के\s+बराबर",
    rf"jab\s+tak\s+{_LOAN}\s+(?:chalega|chale|chalta|hai|rahega|rahe)",
    rf"jitne\s+(?:din|saal)\s+{_LOAN}",
    rf"{_LOAN}\s+(?:jitna|jitne|jitni)",
    rf"{_LOAN}\s+(?:khatam|khatm|khtm|pura|poora|band)\s+hone\s+tak",
    rf"{_LOAN}\s+ke\s+barabar",
    rf"(?:till|until)\s+(?:the\s+)?{_LOAN}\s+(?:is\s+over|ends|is\s+repaid|is\s+paid|is\s+closed|closes|runs)",
    rf"same\s+as\s+(?:the\s+)?{_LOAN}",
    rf"as\s+long\s+as\s+(?:the\s+)?{_LOAN}",
    rf"(?:for\s+)?(?:the\s+)?{_LOAN}\s+(?:tenure|term|period)",
)
_TENURE = re.compile(rf"(?<!{_L})(?:{'|'.join(_TENURE_PHRASES)})(?!{_L})")

# Precomposed nukta letters to their base letter, one character for one, so offsets hold.
_FOLD = {
    0x958: 0x915,
    0x959: 0x916,
    0x95A: 0x917,
    0x95B: 0x91C,
    0x95C: 0x921,
    0x95D: 0x922,
    0x95E: 0x92B,
    0x95F: 0x92F,
}


def _fold(text: str) -> str:
    return "".join(c if len(c.lower()) != 1 else c.lower() for c in text.translate(_FOLD))


def has_doubt_word(text: str, *, exactness: bool = False) -> bool:
    """A word of doubt or approximation is in `text`: "शायद", "करीब", "के आसपास", "I think".

    With `exactness`, a doubt about exactness also counts ("पक्का नहीं पता", "ठीक से याद नहीं",
    "exact yaad nahi"). A marker only. It never makes a wrong answer right; it tells the reviewer
    the customer was unsure. "लगता नहीं" ("I don't think so") is a negation, not doubt, and is not matched.
    """
    folded = _fold(text)
    return _DOUBT.search(folded) is not None or (exactness and _EXACTNESS.search(folded) is not None)


def is_loan_tenure(text: str) -> bool:
    """`text` gives a duration as the loan's own: "जब तक लोन चलेगा", "till the loan is over".

    False when the text also has a number, a word that may be a number, or a negator: then it
    says something more than "as long as the loan" and must be read another way.
    """
    if any(tok.kind in ("num", "bad", "neg", "negpre") for tok in scan(text)):
        return False
    return _TENURE.search(_fold(text)) is not None


def _mask_doubt(text: str) -> tuple[str, bool]:
    """`text` with each doubt phrase blanked to spaces (offsets kept), and whether any was found."""
    folded = _fold(text)
    out, found = list(text), False
    for match in _DOUBT.finditer(folded):
        found = True
        out[match.start() : match.end()] = " " * (match.end() - match.start())
    return "".join(out), found


# Words that may join the two ends of a range, by `norm_key`. Not "और"/"and": that may be a sum.
_RANGE_LINK = {norm_key(w) for w in ("से", "to", "या", "or", "se", "ya")}
_FROM = {norm_key("लेकर"), "lekar"}
_UNTIL = {norm_key(w) for w in ("तक", "tak", "till")}
# Any of these anywhere: the text corrects, negates or compares, so no range is read.
_REFUSE = {"bad", "and"}
# These only in the clause of a range: "पचास से बावन हज़ार नहीं था", not "याद नहीं, पचास से बावन हज़ार".
_REFUSE_IN_CLAUSE = {"neg", "negpre", "cmp", "cmpdirect", "cmppre"}


def _top_unit(atoms: list[Atom]) -> Decimal | None:
    units = [a.value for a in atoms if a.kind == "m"]
    return max(units) if units else None


def _range_of(low: list[Atom], high: list[Atom], dash: bool, juxtaposed: bool) -> tuple[int, int] | None:
    """(low, high) for one split of a stretch, or None when the split is not a narrow range."""
    hv = evaluate(high)
    if hv.value is None or hv.unit_missing or hv.value != hv.value.to_integral_value():
        return None
    lv = evaluate(low)
    if lv.value is None:
        return None
    bare = _top_unit(low) is None and (lv.unit_missing or lv.value < 100)
    if bare:
        # "पचास से बावन हज़ार", "एक से डेढ़ लाख": the low end borrows the high end's one unit.
        if sum(a.kind == "m" for a in high) != 1 or high[-1].kind != "m":
            return None
        lv = evaluate([*low, high[-1]])
    else:
        # "50,000 से 52,000", "एक लाख से एक लाख बीस हज़ार": both ends written alike, same top unit.
        if juxtaposed and not dash:
            return None  # "पचास हज़ार बावन हज़ार": a restart, not a range
        digits = [all(a.kind == "d" for a in side) for side in (low, high)]
        if digits[0] != digits[1] or _top_unit(low) != _top_unit(high):
            return None
    if lv.value is None or lv.unit_missing or lv.value != lv.value.to_integral_value():
        return None
    lo, hi = int(lv.value), int(hv.value)
    return (lo, hi) if 0 < lo < hi and not too_wide(lo, hi) else None


def _stretch_range(text: str, toks: list[Tok]) -> tuple[int, int] | None:
    """The one narrow range a stretch of number, link and currency tokens names, or None."""
    core = [t for t in toks if t.kind not in _CURRENCY]
    while core and norm_key(text[core[-1].start : core[-1].end]) in _UNTIL:
        core.pop()
    keys = [norm_key(text[t.start : t.end]) for t in core]
    seps = [k for k, t in enumerate(core) if t.kind != "num"]
    if seps:
        # One link word, or "से लेकर", between two runs of number words.
        if not (
            (len(seps) == 1 and keys[seps[0]] in _RANGE_LINK)
            or (
                len(seps) == 2
                and seps[1] == seps[0] + 1
                and keys[seps[0]] in _RANGE_LINK
                and keys[seps[1]] in _FROM
            )
        ):
            return None
        splits = [(seps[0], seps[-1] + 1)]
    else:
        splits = [(k, k) for k in range(1, len(core))]
    found = set()
    for left_end, right_start in splits:
        low, high = core[:left_end], core[right_start:]
        if not low or not high:
            return None
        gap = text[low[-1].end : high[0].start]
        reading = _range_of(
            [a for t in low for a in t.atoms],
            [a for t in high for a in t.atoms],
            dash="-" in gap,
            juxtaposed=not seps,
        )
        if reading is not None:
            found.add(reading)
    return found.pop() if len(found) == 1 else None


def _read_range(text: str, exact: bool) -> Approximate | None:
    toks = scan(text)
    if any(t.kind in _REFUSE or (t.kind == "sorry" and _sorry_counts(toks, k)) for k, t in enumerate(toks)):
        return None

    def joins(t: Tok) -> bool:
        key = norm_key(text[t.start : t.end])
        return t.kind == "num" or t.kind in _CURRENCY or key in _RANGE_LINK or key in _FROM or key in _UNTIL

    stretches: list[list[int]] = []
    for k, tok in enumerate(toks):
        touching = k > 0 and _GAP.fullmatch(text, toks[k - 1].end, tok.start) is not None
        if joins(tok) and stretches and stretches[-1][-1] == k - 1 and touching:
            stretches[-1].append(k)
        elif joins(tok):
            stretches.append([k])
    stretches = [s for s in stretches if any(toks[k].kind == "num" for k in s)]
    if not stretches:
        return None
    readings = set()
    for stretch in stretches:
        first, last = stretch[0], stretch[-1]
        before = first - 1
        word = text[toks[before].start : toks[before].end] if before >= 0 else ""
        if before >= 0 and toks[before].kind == "other" and (
            near_fraction(word)
            or (toks[first].kind == "num" and takes_coefficient(toks[first].atoms) and near_coefficient(word))
        ):
            return None  # "सारे पचास से बावन हज़ार": the word before may be a fraction misspelt
        after = last + 1
        if (
            after < len(toks)
            and toks[after].kind == "other"
            and near_unit(text[toks[after].start : toks[after].end])
        ):
            return None
        starts = [m.end() for m in CLAUSE_END.finditer(text, 0, toks[first].start)]
        stop = CLAUSE_END.search(text, toks[last].end)
        clause = (starts[-1] if starts else 0, stop.start() if stop else len(text))
        if any(t.kind in _REFUSE_IN_CLAUSE and clause[0] <= t.start < clause[1] for t in toks):
            return None
        reading = _stretch_range(text, [toks[k] for k in stretch])
        if reading is None:
            return None
        readings.add(reading)
    if len(readings) != 1:
        return None
    low, high = readings.pop()
    if exact and (len(stretches) != 1 or len(stretches[0]) != len(toks)):
        return None
    start, end = toks[stretches[0][0]].start, toks[stretches[0][-1]].end
    return Approximate(low=low, high=high, span=Span(start=start, end=end, text=text[start:end]))


def parse_approx_amount(text: str, *, exact: bool = False) -> AmountResult | Approximate:
    """Like `parse_amount`, but a hedged amount or a narrow range is read as `Approximate`.

    * A plain amount gives exactly what `parse_amount` gives.
    * An amount with a word of doubt or approximation ("करीब पचास हज़ार", "शायद ₹52,000",
      "पचास हज़ार के आसपास", "I think around 50,000") is `Approximate(low == high)`.
    * A narrow range ("पचास बावन हज़ार", "50-52 हज़ार", "पचास से बावन हज़ार", "50,000 से 52,000",
      "पचास हज़ार से लेकर बावन हज़ार तक") is `Approximate(low, high)`: low below high, high at
      most twice low, both ends with the same unit or a bare low end that borrows the high
      end's unit. The same range said twice in two forms counts once (a read-back line).
    * Stays `Ambiguous`: a correction ("बावन नहीं पचपन हज़ार", "सॉरी"), a negated or compared
      amount, three ends, a wide range ("दो से पांच लाख"), ends not low to high, "और"/"and"
      between ends (a sum), two full amounts with only a space between (a restart), and any
      text `parse_amount` refuses for an unreadable or misspelt word.
    `exact=True`: only doubt words, range links, "तक" and currency may stand outside the
    amount; anything else gives `Ambiguous(malformed)`.
    """
    masked, hedged = _mask_doubt(text)
    plain = parse_amount(masked, exact=exact)
    if isinstance(plain, NoAmount):
        return plain
    if isinstance(plain, Parsed):
        if not hedged:
            return plain
        return Approximate(low=plain.rupees, high=plain.rupees, span=plain.span, bound=plain.bound)
    if plain.reason in (AmbiguityReason.multiple_amounts, AmbiguityReason.malformed):
        found = _read_range(masked, exact=False)
        if found is not None:
            if exact and _read_range(masked, exact=True) is None:
                return Ambiguous(reason=AmbiguityReason.malformed, candidates=())
            start, end = found.span.start, found.span.end
            return Approximate(
                low=found.low, high=found.high, span=Span(start=start, end=end, text=text[start:end])
            )
    return parse_amount(text, exact=exact) if hedged else plain
