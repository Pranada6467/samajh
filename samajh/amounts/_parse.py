"""Find number runs in a text and decide whether they name exactly one amount or duration."""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from typing import Literal

from samajh.amounts._grammar import Value, evaluate
from samajh.amounts._lexicon import (
    AND,
    CRORE,
    EMPHATIC,
    HUNDRED,
    JF,
    LAKH,
    PLURAL_UNITS,
    POSTPOSITIONS,
    TA_ONE_BEFORE_NOUN,
    THOUSAND,
    Atom,
    near_coefficient,
    near_fraction,
    near_unit,
    norm_key,
)
from samajh.amounts._text import Tok, scan
from samajh.types import Frozen

_HALF = (Atom("n", Decimal("0.5")),)
_ONE = (Atom("n", Decimal(1)),)
_GAP = re.compile(r"[\s\-‌‍]*")
_CURRENCY = ("cur", "curpfx")
# Words that join two numbers into a range, a choice or a correction instead of separating them.
_LINKS = {"conn", "neg", "negpre", "and", *_CURRENCY}
_MAX_MONTHS = 600
# Where a clause ends. A comma or full stop between digits belongs to the number.
CLAUSE_END = re.compile(r"[।॥;!?\n…]|(?<!\d)[,.]|[,.](?!\d)")
_HEDGE_AFTER = {"neg", "negpre", "cmp", "cmpdirect"}
# A comparison or bound before the number hedges it too ("कम से कम पचास हज़ार", "at least 50,000").
_HEDGE_BEFORE = {"negpre", "cmppre", "cmp"}
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
    bound: bool  # bound to a percent sign or a clock word: "12%", "साढ़े तीन बजे"
    filler: bool  # "கால்", "half", "point", "ஒரு" alone: everyday words, not numbers
    first_tok: int
    last_tok: int
    hedged: bool = False  # negated or compared: "पचास हज़ार नहीं", "पचास हज़ार से कम"
    big_unit: bool = False  # has a thousand-or-larger unit word, so it is not a duration
    stem: bool = False  # a word that only looks like a number (ಐವತ್ತರಿಂದ): counts only next to an amount
    corrects: bool = False  # a negator stands directly before it: "बावन हज़ार था, नहीं पचपन"
    modifier: bool = False  # it counts the next word, not rupees: "एक बार", "दो बार", "one policy"


_ONE_UNIT = {Decimal(u) for u in (HUNDRED, THOUSAND, LAKH, CRORE)}


def takes_coefficient(atoms: Sequence[Atom]) -> bool:
    """A number starting with these atoms may follow डेढ़, ढाई or आधा: a unit word, or digits that
    are exactly one unit ("डेढ़ 1,00,000", Prisma's partial formatting)."""
    first = atoms[0]
    return first.kind == "m" or (first.kind == "d" and first.value in _ONE_UNIT)


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

    def word_at(k: int) -> str:
        return text[toks[k].start : toks[k].end]

    def counts_times(k: int) -> bool:
        """Token k stands directly before a noun of occurrence: "एक बार", "एक ही बार"."""
        step = kind(k + 1, k)
        if step == "other" and norm_key(text[toks[k + 1].start : toks[k + 1].end]) in EMPHATIC:
            step = kind(k + 2, k + 1)
        return step == "times"

    def determiner(k: int) -> bool:
        """Token k is a lone word "one" before an ordinary word that no currency word follows
        (so that word is not a misspelt unit): "एक पॉलिसी", "one policy", "ಒಂದು ವರ್ಷ"."""
        return (
            toks[k].atoms == _ONE
            and kind(k + 1, k) in ("other", "plain", "dur")
            and kind(k + 2, k + 1) not in _CURRENCY
        )

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
        last = toks[j].atoms
        tail_after_unit = (
            j > i
            and toks[j - 1].kind == "num"
            and toks[j - 1].atoms[-1].kind == "m"
            and len(last) == 1
            and last[0].kind in "nd"
            and 0 < last[0].value < 100
            and last[0].value == last[0].value.to_integral_value()
        )
        unsure_tail = False
        if tail_after_unit and toks[j - 1].atoms[-1].value >= THOUSAND:
            # After a thousand-or-larger unit word a small number ends the amount only before a
            # currency word or the end of the clause ("पचास हज़ार एक" is 50,001), and a number
            # other than one also before a postposition ("उन्नीस हज़ार अस्सी की है"). Before a
            # duration, percent or clock word it is that word's number ("पचास हज़ार दो साल").
            # Before anything else it may be the units digit or a count ("पचास हज़ार एक दिए",
            # "पचास हज़ार दो एफडी", "fifty thousand one policy"), and "one" anywhere may be the
            # article: both readings stay possible, so the run is refused.
            after = kind(j + 1, j)
            closes = after in ("", *_CURRENCY) or (
                after == "other" and last[0].value != 1 and norm_key(word_at(j + 1)) in POSTPOSITIONS
            )
            if after in ("dur", "pct", "clock"):
                j -= 1
                del atoms[-1:]
            elif not closes:
                unsure_tail = True
        elif tail_after_unit and counts_times(j):
            # "तीन सौ दो बार": the count is its own run. Otherwise a number after a hundreds word
            # is part of the amount ("तीन सौ एक दिए" is 301).
            j -= 1
            del atoms[-1:]
        after = kind(j + 1, j)
        value = Value(None) if unsure_tail else evaluate(atoms)
        if after == "bad":  # a number with an ending we cannot read: இருபதாயிரத்தை
            value, j = Value(None), j + 1
        first = atoms[0]
        if first.kind == "n" and 0 < first.value < 1:
            # "वन एंड द हाफ क्रोर": a fraction that an "and" should have joined to the number
            # before it is not half a unit by itself.
            back = i - 2 if kind(i - 1, i) in ("art", "other") else i - 1
            if kind(back, back + 1) == "and":
                value = Value(None)
        if atoms[0].kind == "m" and (
            kind(i - 1, i) in ("other", "bad") or norm_key(text[tok.start : tok.end]) in PLURAL_UNITS
        ):
            # A unit with no number: the word before it may be a number we do not know
            # ("साथ हज़ार", "bavan hazaar", "कई लाख"), and "lakhs of rupees" names none.
            value = Value(None)
        before = i - 2 if kind(i - 1, i) in _CURRENCY else i - 1
        misspelt = (
            kind(before, before + 1) == "other"
            and (near_fraction(word_at(before)) or (takes_coefficient(atoms) and near_coefficient(word_at(before))))
        ) or (after == "other" and near_unit(word_at(j + 1)))
        if misspelt:
            # "सारे तीन लाख", "pauney 2 lakh", "एक लख पचास हज़ार": the unknown word may be a
            # fraction or unit word misspelt, and dropping it would give a wrong amount.
            value = Value(None)
        if after == "dur" and tuple(atoms) == TA_ONE_BEFORE_NOUN:
            value = Value(Decimal(1))  # ஒரு வருடம்
        if after == "curpfx" and kind(j + 2, j + 1) == "num" and toks[j + 2].atoms[0].kind == "d":
            after = ""  # "दो ₹5 लाख": the marker belongs to the digits after it
        article = tuple(atoms) == TA_ONE_BEFORE_NOUN
        # A number before a noun of occurrence, or a lone word "one" before an ordinary word
        # that no currency word follows (so the word is not a misspelt unit).
        modifier = counts_times(j) or (i == j and determiner(j))
        strong = (
            misspelt
            # "ஆயிரம் ரூபாய் ஒரே தடவை", "हज़ार रुपये एक बार": that currency word closes the amount before it
            or (currency and not (article or modifier))
            or after in ("cur", "curpfx", "bad")
            or any(a.kind == "m" or (a.kind in "nd" and a.value >= 100) for a in atoms)
        )
        if strong and after == "other" and kind(j + 2, j + 1) == "cur":
            # "ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ" with ನಾನ್ನೂರು unknown: a word we cannot read between an
            # amount and its currency word may be the rest of the number.
            value = Value(None)
        runs.append(
            _Run(
                start=tok.start,
                end=toks[j].end,
                value=value,
                strong=strong,
                unit=toks[j + 1] if after == "dur" else None,
                bound=after in ("pct", "clock") or kind(i - 1, i) == "pctpfx",
                filler=article
                or (len(atoms) == 1 and (atoms[0].kind == "pt" or 0 < atoms[0].value < 1)),
                first_tok=i,
                last_tok=j,
                hedged=_hedged(kind, i, j + 1 if after == "dur" else j),
                big_unit=any(a.kind == "m" and a.value >= THOUSAND for a in atoms),
                corrects=kind(i - 1, i) in ("neg", "negpre"),
                modifier=modifier,
            )
        )
        i = j + 1
    return toks, runs


def _clause(text: str, start: int, end: int) -> tuple[int, int]:
    """Start and end of the clause holding text[start:end]."""
    before = [m.end() for m in CLAUSE_END.finditer(text, 0, start)]
    after = CLAUSE_END.search(text, end)
    return (before[-1] if before else 0, after.start() if after else len(text))


def _hedged_in_clause(text: str, toks: list[Tok], start: int, end: int) -> bool:
    """A negator or comparative in the same clause as text[start:end], at any distance.

    After the number: "बावन हज़ार तो नहीं था", "बावन हज़ार से भी ज़्यादा". Before it, the English
    negators and every comparison or bound: "it was never 52,000", "कम से कम पचास हज़ार". A Hindi
    "नहीं" before a number opens a correction ("नहीं, पचपन हज़ार") and does not hedge it.
    """
    clause_start, clause_end = _clause(text, start, end)
    return any(
        (end <= tok.start < clause_end and tok.kind in _HEDGE_AFTER)
        or (clause_start <= tok.start < start and tok.kind in _HEDGE_BEFORE)
        for tok in toks
    )


def _linked(toks: list[Tok], a: _Run, b: _Run) -> bool:
    """No ordinary word separates the two runs: only connectors, negators, currency or punctuation."""
    return all(tok.kind in _LINKS for tok in toks[a.last_tok + 1 : b.first_tok])


def _explained(run: _Run, found: Parsed, counted: set[int]) -> bool:
    """Whether a run left after the duration, percent, clock and filler runs are set aside is accounted
    for beside the amount `found`: it is counted (the amount itself, or a candidate that already
    made the result), a word that only looks like a number, the same value said again, or a "one"
    that counts the next word ("एक बार", "एक बीमा", "one policy"), which multiplies nothing."""
    return (
        id(run) in counted
        or run.stem
        or run.value.value == found.rupees
        or (run.modifier and run.value.value == 1)
    )


def _touches(toks: list[Tok], loose: list[_Run], found: Parsed, start: int, end: int) -> bool:
    """A loose number meets the amount across a clause break: the amount ends its clause (a
    currency word may follow) and the next clause starts with the number ("पचास हज़ार, दो बार"),
    or a clause ends with the number and the next starts with the amount ("दो बार, पचास हज़ार")."""
    after = [k for k, t in enumerate(toks) if t.start >= found.span.end]
    before = [k for k, t in enumerate(toks) if t.end <= found.span.start]
    ends_clause = all(toks[k].kind in _CURRENCY for k in after if toks[k].start < end)
    starts_clause = all(toks[k].kind in _CURRENCY for k in before if toks[k].end > start)
    next_tok = next((k for k in after if toks[k].start >= end), None)
    prev_tok = next((k for k in reversed(before) if toks[k].end <= start), None)
    return any(
        (ends_clause and run.first_tok == next_tok) or (starts_clause and run.last_tok == prev_tok)
        for run in loose
    )


def parse_amount(text: str, *, exact: bool = False) -> AmountResult:
    """The one rupee amount named in `text`, in any of the four call languages.

    Language-agnostic: digits (ASCII or native), number words in Devanagari, Latin, Tamil
    and Kannada script, and Prisma's inverse-text-normalised shape where a fraction word is
    left in front of the digits ("सवा 2,00,000" = 2,25,000). Never guesses: anything other
    than exactly one amount is `Ambiguous` or `NoAmount`.

    Several numbers in one text. A candidate is WEAK when it is under 100 and has neither a
    unit word nor a currency marker next to it ("एक FD", "बता दो", "दो तीन बार"). Rule:
      * a number under 100 directly after a thousand-or-larger unit word ends the amount only
        before a currency word or the end of the clause ("पचास हज़ार एक" is 50,001), and a
        number other than one also before a postposition ("उन्नीस हज़ार अस्सी की"). Before a
        duration, percent or clock word it is that word's number. Before anything else it may
        be the units digit or a count, so the run is `Ambiguous(malformed)`: "पचास हज़ार एक दिए",
        "पचास हज़ार एक बार", "पचास हज़ार दो एफडी", "fifty thousand one policy". After a hundreds
        word it is part of the number ("तीन सौ एक दिए" is 301);
      * exactly one distinct strong value -> `Parsed`, unless another number stands in the same
        clause that nothing explains: then `Ambiguous(multiple_amounts)` ("पचास हज़ार दो बार
        कटे", "दो एफडी पचास हज़ार की", "तीन लक पचास हज़ार"). Explained are a number bound to a
        duration unit, a percent sign or a clock word ("दो साल के लिए पचास हज़ार", "12% पर",
        "साढ़े तीन बजे"), an everyday word that only looks like a number (filler), the same value
        again, and a "one" that counts the next word ("एक बार", "एक बीमा", "one policy"). A weak
        candidate in another clause is ignored. With nothing, only punctuation, or only
        connectors/negators between them ("50 से 60 हज़ार", "बावन या पचपन हज़ार", "बावन हज़ार नहीं
        पचपन") the weak one counts and the result is `Ambiguous`, and so does a weak one with a
        negator directly before it ("बावन हज़ार था, नहीं पचपन");
      * the same value repeated counts once;
      * a strong candidate that cannot be read -> `Ambiguous` with its reason;
      * only weak candidates: one distinct value -> `Ambiguous(bare_number)`, a number that
        may not be an amount at all ("बावन", "पैसे दे दो"); several -> `multiple_amounts`;
      * anything else with candidates -> `Ambiguous(multiple_amounts)`.
    A candidate is `Ambiguous(malformed)`, and still listed, when a negator follows it
    ("पचास हज़ार नहीं था"), "not"/"no" precedes it, or it is compared ("पचास हज़ार से कम",
    "less than 50,000"). For a counted candidate this holds anywhere in the same clause
    ("बावन हज़ार तो नहीं था", "it was never 52,000"), and so does a comparison or bound before it
    ("कम से कम पचास हज़ार", "at least 50,000", "minimum 50,000"); a clause ends at punctuation. A text with
    a word of doubt or correction ("शायद", "सॉरी", "maybe") or a romanised Hindi number or
    fraction word ("saadhe", "paanch", "sau") is `Ambiguous(malformed)`. A unit word with no number ("हज़ार रुपये") is one unit at the start,
    after punctuation, a currency marker or a word the lexicon knows; directly after an
    unknown word ("साथ हज़ार", "कई लाख", "bavan hazaar") it is `Ambiguous(malformed)`,
    because that word may be the number. A bare plural unit ("lakhs of rupees") is too.
    A Tamil or Kannada noun in the ablative ("கணக்கிலிருந்து ஆயிரம்", "ಖಾತೆಯಿಂದ ಸಾವಿರ") is not
    a number, so the unit after it is one unit. An unknown word between an amount and its
    currency word ("पचास हज़ार पांसौ रुपये") may be the rest of the number: `Ambiguous(malformed)`.
    So is a half that "and" did not join to a number ("वन एंड द हाफ क्रोर"), and a number of
    1,000 or more on a thousand or lakh word ("6,13,00,020 थाउज़ंड").
    Prisma v2.5 also leaves lower groups as words after formatted higher groups: "5,00,000
    दो सौ" is 5,00,200 when the digits are whole thousands, lakhs or crores and the words carry
    a unit and fit below them; "5,00,000 दो" and "1,00,000 50,000" are `Ambiguous`.
    A number directly followed by a duration unit ("5 साल"), a percent sign or a clock word is not a
    candidate. A fraction word by itself that is also an everyday word (கால், ಕಾಲು, half),
    and the Tamil ஒரு and ஒரே by themselves, are not candidates.

    `exact=True` is for a short quote that should be the amount and nothing else: the result
    is `Parsed` only when everything outside `Parsed.span` is whitespace, punctuation or a
    currency marker or word. Any other word or number gives `Ambiguous(malformed)` with the
    amount as the one candidate. In the default mode an unknown word in front of a complete
    number ("पक्का दो लाख") is not noticed; `exact=True` is what catches it.

    Not handled: romanised Hindi number words are out of scope. The common ones are refused
    wherever they stand; one that is not in the lexicon is refused only directly before a
    unit word. A bare number after a lakh or crore is read literally ("एक लाख बीस" is
    1,00,020), though in speech it often means 1,20,000: the read-back is the check. Tamil and Kannada numbers carrying a
    case ending are reported `Ambiguous(malformed)`, not read. Refused on purpose, because the
    text alone does not decide them: a number word directly before digits ("नाइंटी ₹1,80,000"
    was 90,80,000 and "नाइंटी ₹4,13,000" was 94,13,000 in Prisma v2.5 output), a clock time
    before an amount ("08:30 100": साढ़े आठ सौ, or 100 at half past eight), Kannada ಒಂದು ಕಾಲು /
    ಒಂದು ಮುಕ್ಕಾಲು before a unit (ಒಂದು is "one" and "a"), and "3/4" before a unit. Digits that
    Prisma formatted wrongly but well ("3,02,000" for 3,00,200) cannot be seen here at all:
    compare two readings with `cross_check`, and read the amount back.
    """
    toks, runs = _runs(text)
    runs = [r for r in runs if not (r.unit is not None or r.bound or (r.filler and not r.strong))]
    counted = {id(r) for r in runs if r.strong or (r.corrects and any(o.strong for o in runs))}
    for a, b in pairwise(runs):
        between = toks[a.last_tok + 1 : b.first_tok]
        starts_new_phrase = b.modifier and all(tok.kind in _CURRENCY for tok in between)
        if a.strong != b.strong and _linked(toks, a, b) and not starts_new_phrase:
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
        start, end = _clause(text, found.span.start, found.span.end)
        loose = [run for run in runs if not _explained(run, found, counted)]
        if any(start <= run.start < end for run in loose) or _touches(toks, loose, found, start, end):
            # "पचास हज़ार दो बार कटे", "दो एफडी पचास हज़ार की", "पचास हज़ार, दो बार": a number beside
            # the amount that nothing accounts for may multiply it or be part of it.
            return Ambiguous(reason=AmbiguityReason.multiple_amounts, candidates=listed)
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


class Agreed(Frozen):
    """Two readings of the same turn gave the same amount."""

    status: Literal["agreed"] = "agreed"
    rupees: int


class ReadBackNeeded(Frozen):
    """The two readings differ, or one has no single amount. `readings`: what each gave."""

    status: Literal["read_back_needed"] = "read_back_needed"
    readings: tuple[int | None, int | None]


def cross_check(first: AmountResult, second: AmountResult) -> Agreed | ReadBackNeeded:
    """Compare two readings of one spoken amount, for example the Prisma v2.5 and v3.0
    transcripts of the same turn, each already through `parse_amount`.

    Prisma returns no confidence score. On the 240-sentence evaluation (TTS voices, phone
    audio) the two models agreed on 200 sentences and 199 of those were right, so agreement
    is the stand-in. It is not a proof: both readings can share an error.
    """
    a, b = (r.rupees if isinstance(r, Parsed) else None for r in (first, second))
    if a is not None and a == b:
        return Agreed(rupees=a)
    return ReadBackNeeded(readings=(a, b))


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
