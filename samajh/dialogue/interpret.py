"""What the call needs to understand of a customer turn while it is live. Not the extractor.

The state machine asks one thing of a turn: which `Intent` is it, and did it carry an amount (or,
at the second check, a year). `RuleInterpreter` answers from word lists and `samajh.amounts`;
it never sees the loan record. `samajh.dialogue.llm_fallback` adds an LLM for the turns the rules
cannot place.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.amounts import Ambiguous, Parsed, parse_amount
from samajh.dialogue._lexicon import LEXICONS, Lexicon, Phrase, phrase_at, tokens
from samajh.types import Language


class Expecting(StrEnum):
    """What kind of reply the bot's last line calls for."""

    identity = "identity"  # "am I speaking with X?"
    go_ahead = "go_ahead"  # "may we go on?"
    birth_year = "birth_year"
    open = "open"  # an answer in the customer's own words; a bare "yes" says nothing
    told = "told"  # open, but "yes" or "no" alone is an answer ("were you told ...?")
    amount = "amount"  # a rupee figure, or "I don't know"
    confirmation = "confirmation"  # a read-back: yes, no, or another figure
    stop_check = "stop_check"  # "do you want to stop?" / "do you want a person to call?": yes or no


class Intent(StrEnum):
    yes = "yes"
    no = "no"
    wrong_person = "wrong_person"
    decline = "decline"  # said in so many words: the call ends
    wants_human = "wants_human"
    maybe_decline = "maybe_decline"  # a weak signal: the bot asks before it ends the call
    maybe_human = "maybe_human"
    dont_know = "dont_know"
    said = "said"  # words the interpreter has no label for; an answer where one is open
    silence = "silence"
    asks_repeat = "asks_repeat"
    filler = "filler"
    off_topic = "off_topic"


# The amounts a read-back can carry: `spoken_amount` speaks 1 to 999,999,999, and a read-back line is
# only known to parse back to its amount from 100 up (W1 report section 3). A figure outside this
# range is treated as no figure, so the premium question is asked once more.
READ_BACK_MIN, READ_BACK_LIMIT = 100, 1_000_000_000

UNCLEAR: frozenset[Intent] = frozenset({Intent.silence, Intent.asks_repeat, Intent.filler, Intent.off_topic})


class Interpretation(BaseModel):
    """One customer turn as the call understands it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Intent
    # The one unhedged amount in the turn, read by samajh.amounts, and only if the bot can read it back.
    amount_inr: int | None = Field(default=None, ge=READ_BACK_MIN, lt=READ_BACK_LIMIT)
    year: int | None = None  # set only when a birth year was expected; two digits when said that way


class TurnInterpreter(Protocol):
    def interpret(
        self, text: str, *, language: Language, expecting: Expecting, question: str
    ) -> Interpretation:
        """Read one customer turn. `question` is the bot line it replies to."""
        ...


# In words. A longer turn that holds "samajh nahin aaya" or "band karo" is an answer about the sale,
# not a request to repeat or an order to stop.
_REPEAT_TURN = 10
_STOP_TURN = 6
_DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯೦೧೨೩೪೫೬೭೮೯", "0123456789" * 3)
_FOUR_DIGITS = re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")


def _has(words: Phrase, phrases: frozenset[Phrase], *, at_start: bool = False) -> bool:
    places = range(min(1, len(words))) if at_start else range(len(words))
    return any(phrase_at(words, k, phrases) is not None for k in places)


def _only(words: Phrase, phrases: frozenset[Phrase]) -> bool:
    """Is the whole turn made of these phrases and nothing else?"""
    k = 0
    while k < len(words):
        phrase = phrase_at(words, k, phrases)
        if phrase is None:
            return False
        k += len(phrase)
    return bool(words)


def _amount(text: str) -> int | None:
    parsed = parse_amount(text)
    if isinstance(parsed, Parsed) and READ_BACK_MIN <= parsed.rupees < READ_BACK_LIMIT:
        return parsed.rupees
    return None


def _small_number(text: str) -> int | None:
    """A number said alone, such as "nineteen" or "नब्बे": `parse_amount` holds it back as a bare number."""
    parsed = parse_amount(text)
    if isinstance(parsed, Parsed):
        return parsed.rupees
    if isinstance(parsed, Ambiguous) and len(parsed.candidates) == 1:
        return parsed.candidates[0].rupees
    return None


def birth_year(text: str) -> int | None:
    """The year in a reply to "which year were you born?": four digits, or two when said that way."""
    digits = _FOUR_DIGITS.search(text.translate(_DIGITS))
    if digits:
        return int(digits.group())
    whole = _small_number(text)
    if whole is not None and (whole < 100 or 1900 <= whole <= 2099):
        return whole
    words = text.split()
    for cut in range(1, len(words)):  # "nineteen ninety": century, then the year within it
        century, rest = _small_number(" ".join(words[:cut])), _small_number(" ".join(words[cut:]))
        if century in (19, 20) and rest is not None and rest < 100:
            return century * 100 + rest
    return None


class RuleInterpreter:
    """Word lists and `samajh.amounts`. Deterministic; reads nothing but the turn."""

    def interpret(
        self, text: str, *, language: Language, expecting: Expecting, question: str = ""
    ) -> Interpretation:
        words = tokens(text)
        lexicon = LEXICONS[language]
        intent = self._intent(words, lexicon, expecting)
        year = birth_year(text) if expecting is Expecting.birth_year else None
        return Interpretation(intent=intent, amount_inr=_amount(text), year=year)

    def _intent(self, words: Phrase, lexicon: Lexicon, expecting: Expecting) -> Intent:
        if not words:
            return Intent.silence
        short = len(words) <= _REPEAT_TURN
        if _has(words, lexicon.wants_human):
            return Intent.wants_human
        if _has(words, lexicon.decline):
            return Intent.decline
        affirms = _has(words, lexicon.yes_despite_no)
        denies = not affirms and (_has(words, lexicon.no) or _has(words, lexicon.no_at_start, at_start=True))
        if len(words) <= _STOP_TURN and _has(words, lexicon.decline_short):
            # "नहीं, रहने दीजिए" to "may we go on?" is a plain no; elsewhere it is only a hint.
            return Intent.no if denies and expecting is Expecting.go_ahead else Intent.maybe_decline
        affirms = affirms or (not denies and _has(words, lexicon.yes))
        repeats = _only(words, lexicon.asks_repeat_whole) or (short and _has(words, lexicon.asks_repeat))
        if expecting is Expecting.identity:
            is_self = _has(words, lexicon.is_self) and not denies
            if _has(words, lexicon.wrong_person):
                return Intent.wrong_person
            if (repeats or _has(words, lexicon.who)) and not is_self:
                return Intent.asks_repeat
            if denies:
                return Intent.no
            if affirms or is_self:
                return Intent.yes
        if repeats:
            return Intent.asks_repeat
        if expecting in (Expecting.go_ahead, Expecting.confirmation, Expecting.stop_check):
            if denies:
                return Intent.no
            if affirms:
                return Intent.yes
        if _has(words, lexicon.dont_know):
            return Intent.dont_know
        if expecting is Expecting.told and (denies or affirms) and short:
            return Intent.no if denies else Intent.yes
        if _only(words, lexicon.filler):
            return Intent.filler
        return Intent.said
