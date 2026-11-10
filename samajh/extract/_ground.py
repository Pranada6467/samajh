"""Resolve what the LLM points at in the one customer reply it was shown: clause numbers and spans.

The comparison form is the one `samajh.rules.to_beliefs` uses: Unicode NFC, casefolded,
punctuation, symbols and format characters removed, whitespace collapsed, matched on whole
words. A span that is not a run of consecutive whole words of the reply is not found.

Nothing here returns the LLM's text. A clause number or a found span comes back as a slice of
the reply itself, so the evidence stored downstream is the customer's transcript, never model
output. A found span is never shortened: a word next to a number may change the number
("साढ़े" heard as "सारे"), so the rules get the span whole and accept it only if it reads exactly.

`rupees`, `months` and `days` say what a span reads to. They are used only to tell whether two
answers to one question differ, never to accept a value.
"""

import re
import unicodedata
from dataclasses import dataclass

from samajh.amounts import (
    CLAUSE_END,
    Approximate,
    Parsed,
    parse_approx_amount,
    parse_duration_days,
    parse_duration_months,
)

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


def rupees(text: str) -> tuple[int, int] | None:
    """The amount a span reads to, as (low, high): equal for one figure, apart for a spoken range."""
    result = parse_approx_amount(text)
    if isinstance(result, Parsed):
        return result.rupees, result.rupees
    if isinstance(result, Approximate):
        return result.low, result.high
    return None


def amount_reading(text: str) -> tuple[int, int, bool] | None:
    """(low, high, approximate): approximate for a hedged amount or a range."""
    result = parse_approx_amount(text)
    if isinstance(result, Parsed):
        return result.rupees, result.rupees, False
    if isinstance(result, Approximate):
        return result.low, result.high, True
    return None


def months(text: str) -> int | None:
    return parse_duration_months(text)


def days(text: str) -> int | None:
    return parse_duration_days(text)
