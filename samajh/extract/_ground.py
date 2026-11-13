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

# Words that may take back or replace an answer: a reply holding one gets the change check whatever
# its clause count, since speech-to-text may leave a withdrawal unpunctuated ("बीमा है नहीं पता नहीं
# क्या है"). Wide on purpose: a false match costs one cheap extra call, a miss can end `clear` on a
# value the customer took back. Matched on whole words in the comparison form.
_MARKER_WORDS = (
    # Hindi, Devanagari
    "नहीं नही नहि नहीँ नई ना नो नॉट रुकिए रुकिये रुको रुक रुकें अरे अरी मतलब सॉरी सारी माफ़ माफ "
    "वैसे गलत ग़लत गलती बल्कि दरअसल एक्चुअली ओह नी छोड़िए छोड़ो"
    # doubt, forgetting and who-knows tails ("…भूल गया", "…कौन जाने")
    " भूल भूली भूले भूलि शायद लगता लगा मालूम पता याद पक्का"
    # romanised Hindi and English
    " nahi nahin nai nhi nahee na no not nope ruko ruk rukiye rukie rukho arre arey are matlab "
    "matlb sorry actually galat galti wrong wait balki vaise waise darasal oh chhodo chodo chhodiye"
    " bhool bhul bhoole bhule bhooli bhuli shayad shaayad lagta laga maloom malum pata yaad pakka maybe "
    "perhaps forgot forget forgotten unsure dont don't idk"
)
_MARKER_RUNS = (
    "i mean", "hold on", "leave it", "forget it", "एक मिनट", "ek minute", "ek min", "असल में", "asal mein",
    "asal me", "जाने दो", "jaane do", "jane do", "कौन जाने", "kaun jaane", "kaun jane", "या कुछ और",
    "ya kuch aur", "या फिर", "ya phir", "ya fir", "ठीक से", "theek se", "thik se",
)  # fmt: skip


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


_MARKERS = frozenset(tuple(comparison_form(p).split()) for p in (*_MARKER_WORDS.split(), *_MARKER_RUNS))
_MARKER_LENGTHS = sorted({len(m) for m in _MARKERS})


# A tail that takes back what came before it in the same clause: who knows, I forgot, or something
# else, I don't know. The change check reads "41300 kya pata" as doubt that still leans to the answer
# (its prompt says so for hedges), so code decides these on one-clause replies. A hedge about
# exactness ("ठीक से याद नहीं", "पक्का नहीं पता") is not a take-back: it leans, as the prompt says.
def _phrases(*items: str) -> frozenset[tuple[str, ...]]:
    return frozenset(tuple(comparison_form(p).split()) for p in items)


_TAILS = _phrases(
    "कौन जाने", "kaun jaane", "kaun jane", "क्या पता", "kya pata", "या कुछ और", "ya kuch aur",
    "या कुछ और भी", "ya kuch aur bhi", "या फिर कुछ और", "ya phir kuch aur", "ya fir kuch aur",
    "पता नहीं", "नहीं पता", "pata nahi", "pata nahin", "nahi pata", "nahin pata", "मालूम नहीं",
    "नहीं मालूम", "maloom nahi", "malum nahi", "nahi maloom", "याद नहीं", "नहीं याद", "yaad nahi",
    "yaad nahin", "nahi yaad", "don't know", "dont know", "not sure", "no idea", "idk",
    "भूल", "भूली", "भूले", "bhool", "bhul", "bhoole", "bhule", "bhooli", "bhuli", "forgot", "forget",
)  # fmt: skip
# "…या फिर" ("…or else") takes the answer back only when it ends the reply.
_END_TAILS = _phrases("या फिर", "ya phir", "ya fir")
_TAIL_LENGTHS = sorted({len(t) for t in _TAILS | _END_TAILS})
# Doubt about exactness leans to the answer: the exactness word itself must come right before the
# tail, or before a "से/se" that comes right before it ("ठीक से याद नहीं"); "से" alone does not count
# ("लोन से या कैश से याद नहीं" is taken back).
_EXACT = frozenset(
    comparison_form(w)
    for w in [
        "ठीक",
        "theek",
        "thik",
        "पक्का",
        "pakka",
        "exact",
        "exactly",
        "पूरा",
        "poora",
        "pura",
        "sahi",
        "सही",
    ]
)
_SE = frozenset({comparison_form("से"), "se"})
_FORGOT = frozenset(comparison_form(w) for w in ["भूल", "bhool", "bhul"])  # "भूल से": by mistake
# Words that name another quantity or detail ("बीमा है रकम याद नहीं", "kab kata yaad nahi"): on a
# question that does not ask for one, the tail is about that detail, not the answer.
_OTHER_DETAIL = frozenset(
    comparison_form(w)
    for w in [
        "कितने", "कितना", "कितनी", "kitne", "kitna", "kitni", "रकम", "amount", "paisa", "paise", "पैसे",
        "पैसा", "कब", "kab", "बाकी", "baaki", "baki", "किस्त", "kisht", "kist", "emi", "साल", "saal",
        "तारीख", "tarikh", "tareekh", "date",
    ]
)  # fmt: skip


# A "no" answer's own words, and fillers that may stand before a tail ("…mujhe nahi pata"): the only
# marker words allowed before a closing don't-know tail (`Reply.ends_in_dont_know_tail`).
_NO_WORDS = frozenset(
    comparison_form(w)
    for w in ["नहीं", "नही", "नहि", "नहीँ", "ना", "no", "not", "nahi", "nahin", "nai", "nhi", "na"]
)
# Fillers that may close a reply after its tail ("…पता नहीं जी").
_AFTER_TAIL = frozenset(
    comparison_form(w) for w in ["जी", "ji", "हाँ", "हां", "haan", "han", "बस", "bas", "ना", "na"]
)
_TAIL_FILLERS = frozenset(
    comparison_form(w) for w in ["मुझे", "मुझको", "तो", "जी", "mujhe", "mujhko", "to", "ji"]
)


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
    numbers: tuple[int, int]  # the first and last of those clauses, numbered as in the prompt


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

    def has_change_marker(self) -> bool:
        """Does the reply hold a word that may take back or replace an answer (`_MARKER_WORDS`)?"""
        forms = [w.form for w in self._words]
        return any(
            tuple(forms[k : k + n]) in _MARKERS for n in _MARKER_LENGTHS for k in range(len(forms) - n + 1)
        )

    def has_take_back_tail(self, *, other_detail_exempts: bool = False) -> bool:
        """Does a who-knows, forgot or don't-know tail (`_TAILS`) follow at least one other word?

        Not when an exactness word comes right before it ("ठीक से याद नहीं", "pakka nahi pata"), for
        "भूल से" (by mistake), and, with `other_detail_exempts`, not when the reply names another
        quantity or detail (`_OTHER_DETAIL`). "या फिर" counts only at the end of the reply.
        """
        forms = [w.form for w in self._words]
        if other_detail_exempts and _OTHER_DETAIL.intersection(forms):
            return False

        def exact_before(k: int) -> bool:
            return forms[k - 1] in _EXACT or (k >= 2 and forms[k - 1] in _SE and forms[k - 2] in _EXACT)

        for n in _TAIL_LENGTHS:
            for k in range(1, len(forms) - n + 1):
                run, end = tuple(forms[k : k + n]), k + n == len(forms)
                if not (run in _TAILS or (end and run in _END_TAILS)) or exact_before(k):
                    continue
                if n == 1 and run[0] in _FORGOT and not end and forms[k + 1] in _SE:
                    continue
                return True
        return False

    def ends_in_dont_know_tail(self) -> bool:
        """The reply ends in a don't-know tail (`_TAILS`, "…पता नहीं", "…mujhe nahi pata") and the
        words before it hold no other marker word (`_MARKER_WORDS`) than a "no" ("नहीं बताया पता नहीं").
        """
        forms = [w.form for w in self._words]
        end, found = len(forms), False
        while end > 1 and forms[end - 1] in _AFTER_TAIL:
            end -= 1
        while True:
            n = next(
                (
                    n
                    for n in reversed(_TAIL_LENGTHS)
                    if end - n >= 1 and tuple(forms[end - n : end]) in _TAILS
                ),
                0,
            )
            if n:
                end, found = end - n, True
            elif found and end > 1 and forms[end - 1] in _TAIL_FILLERS:
                end -= 1
            else:
                break
        rest = forms[:end]
        markers = [
            run
            for k in range(len(rest))
            for n in _MARKER_LENGTHS
            if (run := tuple(rest[k : k + n])) in _MARKERS
        ]
        return found and bool(rest) and all(len(m) == 1 and m[0] in _NO_WORDS for m in markers)

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
                    words=self.text[first.start : last.end],
                    clauses=self._slice(first.clause, last.clause),
                    numbers=(self._clauses.index(first.clause) + 1, self._clauses.index(last.clause) + 1),
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
