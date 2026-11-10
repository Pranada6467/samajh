"""Resolve what the LLM points at in the one customer reply it was shown: clause numbers and spans.

The comparison form is the one `samajh.rules.to_beliefs` uses: Unicode NFC, casefolded,
punctuation, symbols and format characters removed, whitespace collapsed, matched on whole
words. A span that is not a run of consecutive whole words of the reply is not found.

Nothing here returns the LLM's text. A clause number or a found span comes back as a slice of
the reply itself, so the evidence stored downstream is the customer's transcript, never model
output.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from samajh.amounts import CLAUSE_END, Parsed, parse_amount, parse_duration_days, parse_duration_months

Reader = Callable[[str, bool], int | None]  # (text, exact) -> number, or None when unsure

_WORD = re.compile(r"\S+")


def comparison_form(text: str) -> str:
    """Must stay equal to `samajh.rules.normalise._norm`; a test pins the two together."""
    kept = []
    for ch in unicodedata.normalize("NFC", text).casefold():
        category = unicodedata.category(ch)
        if category[0] == "Z":
            kept.append(" ")
        elif category[0] not in "PS" and category != "Cf":
            kept.append(ch)
    return " ".join("".join(kept).split())


@dataclass(frozen=True)
class _Word:
    form: str
    start: int
    end: int
    clause: int


@dataclass(frozen=True)
class Found:
    """A span located in a reply. Both strings are slices of the reply."""

    words: str  # exactly the matched words
    clauses: str  # the whole clauses that contain them


class Reply:
    """One customer reply, split into clauses and words the way the rule engine splits it."""

    def __init__(self, text: str) -> None:
        self.text = text
        words: list[_Word] = []
        clause_start = 0
        bounds = [*(m.span() for m in CLAUSE_END.finditer(text)), (len(text), len(text))]
        for clause, (stop, resume) in enumerate(bounds):
            for m in _WORD.finditer(text, clause_start, stop):
                # One token can hold several comparison words: a space-like character that
                # `\S` does not treat as a space splits it there, exactly as the engine does.
                for form in comparison_form(m.group()).split():
                    words.append(_Word(form, m.start(), m.end(), clause))
            clause_start = resume
        self._words = words
        self._clauses = sorted({w.clause for w in words})  # only clauses that hold a word

    @property
    def blank(self) -> bool:
        """Silence: no word was transcribed."""
        return not self._words

    @property
    def word_count(self) -> int:
        return len(self._words)

    def whole(self) -> str:
        return self.text.strip()

    def clauses(self) -> tuple[str, ...]:
        """The clauses as the prompt numbers them, from 1."""
        return tuple(self._slice(k, k) for k in self._clauses)

    def cover(self, numbers: tuple[int, ...]) -> str | None:
        """The run of whole clauses from the lowest to the highest of `numbers`.

        None when there is no number or one is out of range. Numbers that are apart are joined
        by everything between them, so the result is always one unbroken slice of the reply.
        """
        if not numbers or min(numbers) < 1 or max(numbers) > len(self._clauses):
            return None
        return self._slice(self._clauses[min(numbers) - 1], self._clauses[max(numbers) - 1])

    def _slice(self, first_clause: int, last_clause: int) -> str:
        inside = [w for w in self._words if first_clause <= w.clause <= last_clause]
        return self.text[inside[0].start : inside[-1].end]

    def find(self, span: str | None) -> Found | None:
        """The first run of whole words equal to `span`, or None. Never a partial word."""
        wanted = comparison_form(span).split() if span else []
        if not wanted:
            return None
        forms = [w.form for w in self._words]
        for k in range(len(forms) - len(wanted) + 1):
            if forms[k : k + len(wanted)] == wanted:
                first, last = self._words[k], self._words[k + len(wanted) - 1]
                return Found(
                    words=self.text[first.start : last.end], clauses=self._slice(first.clause, last.clause)
                )
        return None


def rupees(text: str, exact: bool) -> int | None:
    result = parse_amount(text, exact=exact)
    return result.rupees if isinstance(result, Parsed) else None


def months(text: str, exact: bool) -> int | None:
    return parse_duration_months(text, exact=exact)


def days(text: str, exact: bool) -> int | None:
    return parse_duration_days(text, exact=exact)


def tighten(words: str, read: Reader) -> str:
    """Trim a found span to the words that are the number and nothing else.

    The engine accepts a value span only when it reads, exactly, to the number in the reply.
    A model often copies a word too many ("बावन हज़ार कटे"). The parser, not the model, decides
    which sub-run is the number. A span that does not read to one number is returned unchanged
    and the engine marks it `value_not_parsed`.
    """
    number = read(words, False)
    if number is None or read(words, True) == number:
        return words
    tokens = words.split()
    for size in range(len(tokens) - 1, 0, -1):
        for k in range(len(tokens) - size + 1):
            candidate = " ".join(tokens[k : k + size])
            if read(candidate, True) == number:
                return candidate
    return words
