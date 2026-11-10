"""Find number runs in a text and decide whether they name exactly one amount or duration."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from typing import Literal

from samajh.amounts._grammar import Value, evaluate
from samajh.amounts._lexicon import AND, JF, PLURAL_UNITS, TA_ONE_BEFORE_NOUN, THOUSAND, Atom, norm_key
from samajh.amounts._text import Tok, scan
from samajh.types import Frozen

_HALF = (Atom("n", Decimal("0.5")),)
_GAP = re.compile(r"[\s\-‌‍]*")
_CURRENCY = ("cur", "curpfx")
# Words that join two numbers into a range, a choice or a correction instead of separating them.
_LINKS = {"conn", "neg", "negpre", "and", *_CURRENCY}
_MAX_MONTHS = 600
# Where a clause ends. A comma or full stop between digits belongs to the number.
CLAUSE_END = re.compile(r"[।॥;!?\n…]|(?<!\d)[,.]|[,.](?!\d)")
_HEDGE_AFTER = {"neg", "negpre", "cmp", "cmpdirect"}
_HEDGE_BEFORE = {"negpre", "cmppre"}
_MAX_DAYS = 3650


class Span(Frozen):
    """Where in the input the amount was found: `text == input[start:end]`."""

    start: int
    end: int
    text: str


class Parsed(Frozen):
    """Exactly one amount, in whole rupees."""

    status: Literal["parsed"] = "parsed"
    rupees: int
    span: Span


class AmbiguityReason(StrEnum):
    """Why the text does not name exactly one amount."""

    multiple_amounts = "multiple_amounts"
    fraction_without_unit = "fraction_without_unit"
    non_integer = "non_integer"
    malformed = "malformed"
    bare_number = "bare_number"  # only a number under 100 with no unit and no currency marker


class Ambiguous(Frozen):
    """Numbers were said, but not exactly one readable amount. `candidates` are the readable ones."""

    status: Literal["ambiguous"] = "ambiguous"
    reason: AmbiguityReason
    candidates: tuple[Parsed, ...]


class NoAmount(Frozen):
    """No number in the text."""

    status: Literal["none"] = "none"


AmountResult = Parsed | Ambiguous | NoAmount


@dataclass(frozen=True, slots=True)
class _Run:
    start: int
    end: int
    value: Value
    strong: bool  # at least 100, or has a unit word, or has a currency marker next to it
    unit: Tok | None  # the duration unit directly after the run
    percent: bool
    filler: bool  # "கால்", "half", "point", "ஒரு" alone: everyday words, not numbers
    first_tok: int
    last_tok: int
    hedged: bool = False  # negated or compared: "पचास हज़ार नहीं", "पचास हज़ार से कम"
    big_unit: bool = False  # has a thousand-or-larger unit word, so it is not a duration
    stem: bool = False  # a word that only looks like a number (ಐವತ್ತರಿಂದ): counts only next to an amount
    corrects: bool = False  # a negator stands directly before it: "बावन हज़ार था, नहीं पचपन"


def _hedged(kind, first: int, last: int) -> bool:
    """A negator or comparative next to the tokens first..last, looking past a currency marker."""
    before = first - 1
    if kind(before, before + 1) in _CURRENCY:
        before -= 1
    if kind(before, before + 1) in ("negpre", "cmppre"):
        return True
    after = last + 1
    if kind(after, after - 1) in _CURRENCY:
        after += 1
    step = kind(after, after - 1)
    return step in ("neg", "negpre", "cmpdirect") or (step == "conn" and kind(after + 1, after) == "cmp")


def _runs(text: str) -> tuple[list[Tok], list[_Run]]:
    toks = scan(text)

    def touching(a: int, b: int) -> bool:
        return 0 <= a and b < len(toks) and _GAP.fullmatch(text, toks[a].end, toks[b].start) is not None

    def kind(k: int, after: int) -> str:
        return toks[k].kind if touching(*sorted((k, after))) else ""

    runs: list[_Run] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok.kind == "bad":
            runs.append(
                _Run(
                    tok.start, tok.end, Value(None), tok.strong, None, False, False, i, i, stem=not tok.strong
                )
            )
        if tok.kind != "num":
            i += 1
            continue
        atoms: list[Atom] = list(tok.atoms)
        currency = kind(i - 1, i) in ("cur", "curpfx")
        j = i
        while True:
            step = kind(j + 1, j)
            last = atoms[-1]
            # "बता दो 5 लाख": a whole number word never takes digits after it.
            takes_digits = not (last.kind == "n" and last.value == last.value.to_integral_value())
            word = step == "num" and (takes_digits or toks[j + 1].atoms[0].kind != "d")
            unit_letter = step == "glue" and toks[j + 1].start == toks[j].end and last.kind == "d"
            # "पांच सो": सो is सौ only when a number, a currency word or the end follows.
            so = (
                step == "unitafter"
                and last.kind in "nd"
                and last.value < 100
                and kind(j + 2, j + 1) in ("", "num", *_CURRENCY)
            )
            if word or unit_letter or so:
                atoms += toks[j + 1].atoms
                j += 1
            elif (
                step == "art"
                and atoms == list(_HALF)
                and kind(j + 2, j + 1) == "num"
                and toks[j + 2].atoms[0].kind == "m"
            ):
                atoms += toks[j + 2].atoms  # half a lakh
                j += 2
            elif step == "and":
                k = j + 3 if kind(j + 2, j + 1) == "art" else j + 2
                if kind(k, k - 1) != "num":
                    break
                if toks[k].atoms == _HALF:
                    atoms += (JF, *_HALF)  # two and a half
                elif k == j + 2:
                    atoms += (AND, *toks[k].atoms)
                else:
                    break
                j = k
            elif (
                step == "curpfx"
                and takes_digits
                and kind(j + 2, j + 1) == "num"
                and toks[j + 2].atoms[0].kind == "d"
            ):
                atoms += toks[j + 2].atoms  # पौने ₹2,00,000
                currency = True
                j += 2
            else:
                break
        while j > i and toks[j].atoms == TA_ONE_BEFORE_NOUN:
            j -= 1  # "ஐம்பதாயிரம் ஒரு பாலிசி": the ஒரு belongs to the next word
            del atoms[-2:]
        after = kind(j + 1, j)
        value = evaluate(atoms)
        if after == "bad":  # a number with an ending we cannot read: இருபதாயிரத்தை
            value, j = Value(None), j + 1
        if atoms[0].kind == "m" and (
            kind(i - 1, i) in ("other", "bad") or norm_key(text[tok.start : tok.end]) in PLURAL_UNITS
        ):
            # A unit with no number: the word before it may be a number we do not know
            # ("साथ हज़ार", "bavan hazaar", "कई लाख"), and "lakhs of rupees" names none.
            value = Value(None)
        if after == "dur" and tuple(atoms) == TA_ONE_BEFORE_NOUN:
            value = Value(Decimal(1))  # ஒரு வருடம்
        if after == "curpfx" and kind(j + 2, j + 1) == "num" and toks[j + 2].atoms[0].kind == "d":
            after = ""  # "दो ₹5 लाख": the marker belongs to the digits after it
        strong = (
            currency
            or after in ("cur", "curpfx", "bad")
            or any(a.kind == "m" or (a.kind in "nd" and a.value >= 100) for a in atoms)
        )
        runs.append(
            _Run(
                start=tok.start,
                end=toks[j].end,
                value=value,
                strong=strong,
                unit=toks[j + 1] if after == "dur" else None,
                percent=after == "pct" or kind(i - 1, i) == "pctpfx",
                filler=tuple(atoms) == TA_ONE_BEFORE_NOUN
                or (len(atoms) == 1 and (atoms[0].kind == "pt" or 0 < atoms[0].value < 1)),
                first_tok=i,
                last_tok=j,
                hedged=_hedged(kind, i, j + 1 if after == "dur" else j),
                big_unit=any(a.kind == "m" and a.value >= THOUSAND for a in atoms),
                corrects=kind(i - 1, i) in ("neg", "negpre"),
            )
        )
        i = j + 1
    return toks, runs


def _hedged_in_clause(text: str, toks: list[Tok], start: int, end: int) -> bool:
    """A negator or comparative in the same clause as text[start:end], at any distance.

    After the number: "बावन हज़ार तो नहीं था", "बावन हज़ार से भी ज़्यादा". Before it, for the English
    words only: "it was never 52,000". A Hindi "नहीं" before a number opens a correction
    ("नहीं, पचपन हज़ार") and does not hedge it.
    """
    before = [m.end() for m in CLAUSE_END.finditer(text, 0, start)]
    clause_start = before[-1] if before else 0
    after = CLAUSE_END.search(text, end)
    clause_end = after.start() if after else len(text)
    return any(
        (end <= tok.start < clause_end and tok.kind in _HEDGE_AFTER)
        or (clause_start <= tok.start < start and tok.kind in _HEDGE_BEFORE)
        for tok in toks
    )


def _linked(toks: list[Tok], a: _Run, b: _Run) -> bool:
    """No ordinary word separates the two runs: only connectors, negators, currency or punctuation."""
    return all(tok.kind in _LINKS for tok in toks[a.last_tok + 1 : b.first_tok])


def parse_amount(text: str, *, exact: bool = False) -> AmountResult:
    """The one rupee amount named in `text`, in any of the four call languages.

    Language-agnostic: digits (ASCII or native), number words in Devanagari, Latin, Tamil
    and Kannada script, and Prisma's inverse-text-normalised shape where a fraction word is
    left in front of the digits ("सवा 2,00,000" = 2,25,000). Never guesses: anything other
    than exactly one amount is `Ambiguous` or `NoAmount`.

    Several numbers in one text. A candidate is WEAK when it is under 100 and has neither a
    unit word nor a currency marker next to it ("एक FD", "बता दो", "दो तीन बार"). Rule:
      * exactly one distinct strong value -> `Parsed`; a weak candidate is ignored only when
        at least one ordinary word separates it from the strong one. With nothing, only
        punctuation, or only connectors/negators between them ("50 से 60 हज़ार", "बावन या
        पचपन हज़ार", "बावन हज़ार नहीं पचपन") the weak one counts and the result is `Ambiguous`,
        and so does a weak one with a negator directly before it ("बावन हज़ार था, नहीं पचपन");
      * the same value repeated counts once;
      * a strong candidate that cannot be read -> `Ambiguous` with its reason;
      * only weak candidates: one distinct value -> `Ambiguous(bare_number)`, a number that
        may not be an amount at all ("बावन", "पैसे दे दो"); several -> `multiple_amounts`;
      * anything else with candidates -> `Ambiguous(multiple_amounts)`.
    A candidate is `Ambiguous(malformed)`, and still listed, when a negator follows it
    ("पचास हज़ार नहीं था"), "not"/"no" precedes it, or it is compared ("पचास हज़ार से कम",
    "less than 50,000"). For a counted candidate this holds anywhere in the same clause
    ("बावन हज़ार तो नहीं था", "it was never 52,000"); a clause ends at punctuation. A text with
    a word of doubt or correction ("शायद", "सॉरी", "maybe") or a romanised Hindi number or
    fraction word ("saadhe", "paanch", "sau") is `Ambiguous(malformed)`. A unit word with no number ("हज़ार रुपये") is one unit at the start,
    after punctuation, a currency marker or a word the lexicon knows; directly after an
    unknown word ("साथ हज़ार", "कई लाख", "bavan hazaar") it is `Ambiguous(malformed)`,
    because that word may be the number. A bare plural unit ("lakhs of rupees") is too.
    A number directly followed by a duration unit ("5 साल") or a percent sign is not a
    candidate. A fraction word by itself that is also an everyday word (கால், ಕಾಲು, half),
    and the Tamil article ஒரு by itself, are not candidates.

    `exact=True` is for a short quote that should be the amount and nothing else: the result
    is `Parsed` only when everything outside `Parsed.span` is whitespace, punctuation or a
    currency marker or word. Any other word or number gives `Ambiguous(malformed)` with the
    amount as the one candidate. In the default mode an unknown word in front of a complete
    number ("पक्का दो लाख") is not noticed; `exact=True` is what catches it.

    Not handled: romanised Hindi number words are out of scope. The common ones are refused
    wherever they stand; one that is not in the lexicon is refused only directly before a
    unit word. A bare number after a lakh or crore is read literally ("एक लाख बीस" is
    1,00,020), though in speech it often means 1,20,000: the read-back is the check. Tamil and Kannada numbers carrying a
    case ending are reported `Ambiguous(malformed)`, not read.
    """
    toks, runs = _runs(text)
    runs = [r for r in runs if not (r.unit is not None or r.percent or (r.filler and not r.strong))]
    counted = {id(r) for r in runs if r.strong or (r.corrects and any(o.strong for o in runs))}
    for a, b in pairwise(runs):
        if a.strong != b.strong and _linked(toks, a, b):
            counted |= {id(a), id(b)}

    candidates: list[Parsed] = []
    strong_ok: list[Parsed] = []
    weak_ok: list[Parsed] = []
    strong_bad: list[AmbiguityReason] = []
    weak_bad: list[AmbiguityReason] = []
    for run in runs:
        strong = id(run) in counted
        if run.stem and not strong:
            continue
        value = run.value.value
        parsed = reason = None
        if value is None:
            reason = AmbiguityReason.malformed
        elif run.value.unit_missing:
            reason = AmbiguityReason.fraction_without_unit
        elif value != value.to_integral_value():
            reason = AmbiguityReason.non_integer
        else:
            span = Span(start=run.start, end=run.end, text=text[run.start : run.end])
            parsed = Parsed(rupees=int(value), span=span)
            candidates.append(parsed)
            if run.hedged or (strong and _hedged_in_clause(text, toks, run.start, run.end)):
                reason = AmbiguityReason.malformed
        if reason is not None:
            (strong_bad if strong else weak_bad).append(reason)
        else:
            (strong_ok if strong else weak_ok).append(parsed)

    listed = tuple(candidates)
    if strong_bad:
        return Ambiguous(reason=strong_bad[0], candidates=listed)
    if strong_ok:
        if len({p.rupees for p in strong_ok}) > 1:
            return Ambiguous(reason=AmbiguityReason.multiple_amounts, candidates=listed)
        found = strong_ok[0]
        outside = [t for t in toks if not (found.span.start <= t.start and t.end <= found.span.end)]
        if exact and any(t.kind not in _CURRENCY for t in outside):
            return Ambiguous(reason=AmbiguityReason.malformed, candidates=(found,))
        return found
    if weak_bad:
        return Ambiguous(reason=weak_bad[0], candidates=listed)
    if weak_ok:
        one = len({p.rupees for p in weak_ok}) == 1
        reason = AmbiguityReason.bare_number if one else AmbiguityReason.multiple_amounts
        return Ambiguous(reason=reason, candidates=listed)
    return NoAmount()


def _one_duration(text: str, exact: bool, scale_of: Callable[[Tok], Decimal | None], joins: bool) -> int | None:
    """The one duration in `text` as a whole number of the unit `scale_of` measures, or None.

    `joins`: years and months directly after one another add up ("2 साल 6 महीने").
    """
    toks, runs = _runs(text)
    if any(run.value.value is None and run.strong and run.unit is None for run in runs):
        return None  # a number we cannot read, or a word of doubt or correction
    for a, b in pairwise(runs):
        between = toks[a.last_tok + (2 if a.unit is not None else 1) : b.first_tok]
        other = b if a.unit is not None else a
        ranged = (a.unit is not None or b.unit is not None) and (other.unit is not None or not other.strong)
        if ranged and between and all(tok.kind in _LINKS for tok in between):
            return None
        # "15, 30 दिन", "15 – 30 दिन", "तीन साल छह": a bare number with only punctuation
        # between it and a duration is a range or an unfinished duration.
        if ranged and not between and (a.unit is None) != (b.unit is None):
            return None
    found: list[Decimal] = []
    used = 0  # tokens that belong to a duration
    prev: _Run | None = None
    for run in runs:
        if run.unit is None:
            prev = None
            continue
        value, scale = run.value.value, scale_of(run.unit)
        if value is None or scale is None or run.hedged or run.big_unit:
            return None
        if _hedged_in_clause(text, toks, run.start, run.unit.end):
            return None
        before = toks[run.first_tok - 1] if run.first_tok else None
        if before is not None and before.kind == "dur" and (prev is None or before is not prev.unit):
            return None  # "हफ़्ता दस दिन": a unit with no number, then a duration
        amount = value * scale
        used += run.last_tok - run.first_tok + 2
        if (
            prev is not None
            and run.first_tok == prev.last_tok + 2
            and not text[prev.unit.end : run.start].strip()
        ):
            # "2 साल 6 महीने". "1 साल 12 महीने" and "5 साल 10 साल" are not one duration.
            if not (joins and prev.unit.months == 12 and run.unit.months == 1 and amount < 12):
                return None
            found[-1] += amount
        else:
            found.append(amount)
        prev = run
    if len(set(found)) != 1 or (exact and used != len(toks)):
        return None
    total = found[0]
    return int(total) if total > 0 and total == total.to_integral_value() else None


def parse_duration_months(text: str, *, exact: bool = False) -> int | None:
    """Whole months named in `text`, or None unless there is exactly one unambiguous duration.

    "5 साल" -> 60, "डेढ़ साल" -> 18, "60 months" -> 60, "2 साल 6 महीने" -> 30. Years and months
    join only when the months are under 12 and only whitespace separates them. The same
    duration said twice counts once ("5 साल, मतलब 60 महीने" -> 60). None for: two different
    durations; a connector or negator between a duration and another number ("5 से 6 साल",
    "पाँच साल नहीं तीन"); a negated or compared duration; a number with a thousand-or-larger
    unit ("पाँच हज़ार महीना" is a price); days, weeks, a fractional number of months, or more
    than 600 months. `exact=True`: None unless the text is the duration and nothing else.
    """
    months = _one_duration(text, exact, lambda unit: unit.months, joins=True)
    return months if months is not None and months <= _MAX_MONTHS else None


def parse_duration_days(text: str, *, exact: bool = False) -> int | None:
    """Whole days named in `text`, for a cancellation window. Same rules as `parse_duration_months`.

    "30 दिन" -> 30, "दो हफ़्ते" -> 14, "एक महीना" -> 30, "1 year" -> 365: a week is 7 days, a
    month 30 and a year 365. Two units never add up ("1 महीना 10 दिन" -> None). None for hours,
    minutes, a fractional number of days ("डेढ़ दिन"), or more than 3650 days.
    """
    days = _one_duration(text, exact, lambda unit: unit.days, joins=False)
    return days if days is not None and days <= _MAX_DAYS else None
