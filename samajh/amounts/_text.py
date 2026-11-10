"""Tokeniser: original-string offsets in, classified tokens out."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from samajh.amounts._lexicon import STEMS, WORDS, Atom, Word, norm_key
from samajh.amounts._sandhi import SCRIPTS, number_stem, segment

# A fraction of exactly three digits is refused: "52.000" may be 52 or a dotted 52,000.
_GROUPED = re.compile(r"(\d+|\d{1,2}(,\d\d)*,\d{3}|\d{1,3}(,\d{3})+)(\.(\d{1,2}|\d{4,}))?")
# A unit glued to digits is read ("5lakh", "52k", "Rs52000", "5साल"); any other letters are not ("ie6").
_GLUE_OK = {"glue", "cur", "curpfx", "dur", "pct"}


@dataclass(frozen=True, slots=True)
class Tok:
    start: int
    end: int
    kind: str  # Word.kind, or: bad (a number we cannot read), other
    atoms: tuple[Atom, ...] = ()
    months: Decimal | None = None
    days: Decimal | None = None
    strong: bool = False  # bad only: certainly a number, so it must block a parse


def _char_class(char: str) -> str:
    if char in "‌‍":
        return "w"
    category = unicodedata.category(char)
    if category == "Nd":
        return "d"
    if category == "No":
        return "f"  # ½, ¼, superscripts: a number we do not read
    return "w" if category[0] in "LM" else "x"


def _classify(word: str) -> tuple[Word, bool]:
    """The word's entry, and for an unreadable number whether it certainly is one."""
    key = norm_key(word)
    if key in WORDS:
        entry = WORDS[key]
        return (Word("bad"), True) if entry.kind == "vague" else (entry, False)
    for script in SCRIPTS:
        if not script.owns(key):
            continue
        readings = segment(script, key)
        if len(readings) == 1:
            return Word("num", next(iter(readings))), False
        if readings:
            return Word("bad"), True
        for stem, entry in STEMS:
            if key.startswith(stem):
                return entry, False
        looks_numeric, has_unit = number_stem(script, key)
        if looks_numeric:
            return Word("bad"), has_unit
    return Word("other"), False


def _pieces(text: str) -> list[tuple[int, int, str]]:
    """(start, end, class) for each run of letters (w), digits (d) or known symbol (s)."""
    out = []
    i, size = 0, len(text)
    while i < size:
        start, cls = i, _char_class(text[i])
        if cls == "w":
            while i < size and _char_class(text[i]) == "w":
                i += 1
        elif cls == "f":
            i += 1
        elif cls == "d":
            if start > 0 and text[start - 1] == "." and (start == 1 or text[start - 2].isspace()):
                start -= 1  # ".5": keep the dot so the number is refused, not read as 5
            i += 1
            while i < size and (
                _char_class(text[i]) == "d"
                or (text[i] in ",." and i + 1 < size and _char_class(text[i + 1]) == "d")
            ):
                i += 1
        elif text[i] in "₹%":
            i, cls = i + 1, "s"
        elif text.startswith("/-", i):
            i, cls = i + 2, "s"
        else:
            i += 1
            continue
        out.append((start, i, cls))
    return out


def _tok(text: str, start: int, end: int, cls: str) -> Tok:
    raw = text[start:end]
    if cls == "s":
        return Tok(start, end, {"₹": "curpfx", "%": "pct"}.get(raw, "cur"))
    if cls == "f":
        return Tok(start, end, "bad", strong=True)
    if cls == "d":
        plain = "".join(c if c in ",." else str(unicodedata.digit(c)) for c in raw)
        if not _GROUPED.fullmatch(plain):
            return Tok(start, end, "bad", strong=True)
        return Tok(start, end, "num", (Atom("d", Decimal(plain.replace(",", ""))),))
    entry, strong = _classify(raw)
    if entry.kind == "curpfx" and text.startswith(".", end):
        end += 1  # "Rs."
    return Tok(start, end, entry.kind, entry.atoms, entry.months, entry.days, strong)


def scan(text: str) -> list[Tok]:
    """Tokens in order. Punctuation and unknown symbols are left out; gaps show in the offsets."""
    toks: list[Tok] = []
    pieces = _pieces(text)
    i = 0
    while i < len(pieces):
        j = i + 1
        while (
            j < len(pieces)
            and pieces[j][0] == pieces[j - 1][1]
            and "s" not in (pieces[j][2], pieces[j - 1][2])
        ):
            j += 1
        chunk = [_tok(text, *piece) for piece in pieces[i:j]]
        letters = [t for t, piece in zip(chunk, pieces[i:j], strict=True) if piece[2] == "w"]
        if j - i > 1 and not all(
            t.kind in _GLUE_OK or (t.kind == "num" and t.atoms[0].kind == "m") for t in letters
        ):
            chunk = [Tok(pieces[i][0], pieces[j - 1][1], "other")]
        toks += chunk
        i = j
    return toks
