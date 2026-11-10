"""What the call needs to understand of a customer turn while it is live. Not the extractor.

The state machine asks one thing of a turn: which `Intent` is it, and did it carry an amount (or,
at the second check, a year). `RuleInterpreter` answers from word lists and `samajh.amounts`;
it never sees the loan record. `samajh.dialogue.llm_fallback` adds an LLM for the turns the rules
cannot place.

Who is believed at the first-name question is decided here and only here: a reply is a yes only
when it claims to be the person asked for, in words from a short list, and says nothing else that
the list does not hold. Anything that speaks of the borrower as someone else ends the call.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.amounts import Ambiguous, AmountResult, Approximate, Parsed, parse_amount, parse_approx_amount
from samajh.dialogue._lexicon import (
    LANGUAGE_NAMES,
    LEXICONS,
    OWN_LANGUAGES,
    Lexicon,
    Phrase,
    phrase_at,
    tokens,
)
from samajh.types import Language


class Expecting(StrEnum):
    """What kind of reply the bot's last line calls for."""

    identity = "identity"  # "am I speaking with X?"
    go_ahead = "go_ahead"  # "may we go on?"
    birth_year = "birth_year"
    open = "open"  # an answer in the customer's own words; a bare "yes" says nothing
    told = "told"  # open, but "yes" or "no" alone is an answer ("were you told ...?")
    either_or = "either_or"  # "was it required, or your choice?": a bare yes or no is not an answer
    amount = "amount"  # a rupee figure, or "I don't know"
    confirmation = "confirmation"  # a read-back: yes, no, or another figure
    stop_check = "stop_check"  # "shall we go on?" / "do you want a person to call?": yes or no
    callback_time = "callback_time"  # "when should we call?": any reply is the answer


class Intent(StrEnum):
    yes = "yes"
    no = "no"
    wrong_person = "wrong_person"
    decline = "decline"  # said in so many words: the call ends
    wants_human = "wants_human"
    maybe_decline = "maybe_decline"  # a weak signal: the bot asks before it ends the call
    maybe_human = "maybe_human"
    call_later = "call_later"  # "call me later", "I am driving": the call ends with a call-back
    do_not_call = "do_not_call"  # "take my number off your list": the call ends, outcome do_not_call
    written_request = "written_request"  # "send it in writing": the call ends, outcome written_requested
    other_language = "other_language"  # "speak Tamil": the call ends, the language is recorded
    asks_who = "asks_who"  # "who is this?", "is this a fraud call?": answered, then the question again
    took_nothing = "took_nothing"  # "I took nothing with the loan"
    dont_know = "dont_know"
    said = "said"  # words the interpreter has no label for; an answer where one is open
    silence = "silence"
    asks_repeat = "asks_repeat"
    filler = "filler"
    off_topic = "off_topic"
    unclear = "unclear"  # the interpreter could not read the turn


# The amounts a read-back can carry: `spoken_amount` speaks 1 to 999,999,999, and a read-back line is
# only known to parse back to its amount from 100 up (W1 report section 3). A figure outside this
# range is treated as no figure, so the premium question is asked once more.
READ_BACK_MIN, READ_BACK_LIMIT = 100, 1_000_000_000

UNCLEAR: frozenset[Intent] = frozenset(
    {Intent.silence, Intent.asks_repeat, Intent.filler, Intent.off_topic, Intent.unclear}
)
# Readings the word lists are not sure of: the classifier is asked about these.
_UNSETTLED = frozenset(
    {Intent.said, Intent.maybe_decline, Intent.maybe_human, Intent.off_topic, Intent.unclear}
)


class Interpretation(BaseModel):
    """One customer turn as the call understands it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Intent
    # The one unhedged amount in the turn, read by samajh.amounts, and only if the bot can read it back.
    amount_inr: int | None = Field(default=None, ge=READ_BACK_MIN, lt=READ_BACK_LIMIT)
    # Numbers heard that did not settle into one amount ("शायद पचपन हज़ार", "बावन नहीं पचपन", "पचपन").
    # The bot never says them; at a read-back they show that the customer named some other figure.
    figures: tuple[int, ...] = ()
    # An amount said as "about X" or "X to Y" (`samajh.amounts.parse_approx_amount`), as (low, high).
    approx: tuple[int, int] | None = None
    # The turn is the amount and nothing more than yes-words and fillers ("हाँ, बावन हज़ार").
    only_amount: bool = False
    year: int | None = None  # set only when a birth year was expected; two digits when said that way
    # With `call_later`: "time" when the turn names a time, "busy" when the customer cannot talk now and
    # names none, "ask" when they want a later call and name no time.
    callback: Literal["time", "busy", "ask"] | None = None
    language_name: str | None = None  # with `other_language`: English name in lower case, if said
    own_choice: bool = False  # "it was my choice": the bot then skips the provider-choice question
    # The word lists are sure of this reading (an exact, tight match). An unsettled reading is what the
    # classifier is asked about; with no classifier it stands, and at the first-name and birth-year
    # questions it never confirms anyone.
    settled: bool = True
    # A year heard in a reply that held other words ("इनका जन्म 1984 में हुआ था"). It never passes the
    # second check by itself: only a classifier that reads the reply as first person can promote it.
    loose_year: int | None = None
    degraded: bool = False  # the classifier was asked and failed; this reading is the word lists' alone


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
_OPENING = frozenset({Expecting.identity, Expecting.go_ahead, Expecting.birth_year})
# Before the loan is named there is no sale to recount, so a refusal there is a refusal.
_NO_ACCOUNT_OF_THE_SALE = _OPENING | {Expecting.stop_check, Expecting.callback_time}
_FIGURE = frozenset({Expecting.amount, Expecting.confirmation})
_DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯೦೧೨೩೪೫೬೭೮೯", "0123456789" * 3)
_FOUR_DIGITS = re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")
# "Ramesh's wife": the English possessive, read before `tokens` drops the apostrophe.
_POSSESSIVE_S = re.compile(r"[A-Za-z]+['’]s\b")
_CONTRACTIONS = frozenset(
    {"it's", "that's", "what's", "who's", "let's", "there's", "here's", "where's", "how's"}
)
_CURRENCY = frozenset(tokens("रुपये रुपए रुपया रुपैया rupees rupee rs inr"))


def _has(words: Phrase, phrases: frozenset[Phrase], *, at_start: bool = False) -> bool:
    places = range(min(1, len(words))) if at_start else range(len(words))
    return any(phrase_at(words, k, phrases) is not None for k in places)


def _only(words: Phrase, phrases: frozenset[Phrase]) -> bool:
    """Is the whole turn made of these phrases and nothing else?"""
    return bool(words) and not _rest(words, phrases)


def _rest(words: Phrase, phrases: frozenset[Phrase]) -> Phrase:
    """The words of a turn that none of these phrases covers."""
    left, k = [], 0
    while k < len(words):
        phrase = phrase_at(words, k, phrases)
        if phrase is None:
            left.append(words[k])
            k += 1
        else:
            k += len(phrase)
    return tuple(left)


def _amount(parsed: AmountResult) -> int | None:
    if isinstance(parsed, Parsed) and READ_BACK_MIN <= parsed.rupees < READ_BACK_LIMIT:
        return parsed.rupees
    return None


def _figures(parsed: AmountResult) -> tuple[int, ...]:
    return tuple(c.rupees for c in parsed.candidates) if isinstance(parsed, Ambiguous) else ()


def _approximate(text: str) -> tuple[int, int] | None:
    """An amount said as "about X" or "X to Y" that a read-back can carry (P3a's `parse_approx_amount`)."""
    parsed = parse_approx_amount(text)
    if isinstance(parsed, Approximate) and READ_BACK_MIN <= parsed.low <= parsed.high < READ_BACK_LIMIT:
        return parsed.low, parsed.high
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


def _only_amount(text: str, parsed: AmountResult, lexicon: Lexicon) -> bool:
    """Is the turn the amount plus yes-words, fillers and the word for rupees, and nothing else?"""
    if not isinstance(parsed, Parsed):
        return False
    rest = _rest(
        tokens(text[: parsed.span.start] + " " + text[parsed.span.end :]), lexicon.yes | lexicon.filler
    )
    return all(word in _CURRENCY for word in rest)


def _language_request(words: Phrase, lexicon: Lexicon, language: Language) -> tuple[bool, str | None]:
    """Did the customer ask for another language, and which one?"""
    names = {LANGUAGE_NAMES[word] for word in words if word in LANGUAGE_NAMES}
    other = names - OWN_LANGUAGES[language]
    if other and (_has(words, lexicon.language_cue) or len(words) <= 3):
        return True, min(other)
    if names & OWN_LANGUAGES[language] and _has(words, lexicon.cannot_follow):
        return True, None
    return False, None


def speaks_in_first_person(text: str, language: Language) -> bool:
    """Does the reply hold a first-person word ("मैं", "main", "I", "speaking")? A claim to be the
    borrower needs one, whoever judges it: "haan batao kya baat hai" is not a claim."""
    words, lexicon = tokens(text), LEXICONS[language]
    return _has(words, lexicon.first_person) or _has(words, lexicon.is_self)


class RuleInterpreter:
    """Word lists and `samajh.amounts`. Deterministic; reads nothing but the turn."""

    def interpret(
        self, text: str, *, language: Language, expecting: Expecting, question: str = ""
    ) -> Interpretation:
        words = tokens(text)
        lexicon = LEXICONS[language]
        intent, extra = self._intent(text, words, lexicon, expecting, language)
        year = loose = None
        if expecting is Expecting.birth_year and intent is not Intent.wrong_person:
            heard = birth_year(text)
            if heard is not None and self._tight_year(words, lexicon):
                year = heard
            else:
                loose = heard
        parsed = parse_amount(text)
        figure = expecting in _FIGURE
        settled = extra.pop("settled", None)
        if settled is None:
            settled = self._settled(intent, expecting, year)
        approx = _approximate(text) if figure else None
        if figure and (_amount(parsed) is not None or approx is not None):
            settled = True  # a figure the bot can read back: the read-back settles the rest
        return Interpretation(
            intent=intent,
            amount_inr=_amount(parsed),
            figures=_figures(parsed),
            approx=approx,
            only_amount=figure and _only_amount(text, parsed, lexicon),
            year=year,
            loose_year=loose,
            own_choice=expecting is Expecting.either_or and self._own_choice(words, lexicon),
            settled=settled,
            **extra,
        )

    @staticmethod
    def _settled(intent: Intent, expecting: Expecting, year: int | None) -> bool:
        if intent is Intent.silence or expecting is Expecting.callback_time:
            return True
        if expecting is Expecting.go_ahead:
            return False  # every reply at the go-ahead is put to the classifier when there is one
        if expecting is Expecting.birth_year:
            return year is not None or intent is Intent.wrong_person
        return intent not in _UNSETTLED

    @staticmethod
    def _tight_year(words: Phrase, lexicon: Lexicon) -> bool:
        """Is the reply the year and nothing else but "my", "born", "in" and the like?"""
        rest = _rest(words, lexicon.year_ok | lexicon.filler)
        return all(any(ch.isdigit() for ch in word) or _small_number(word) is not None for word in rest)

    @staticmethod
    def _own_choice(words: Phrase, lexicon: Lexicon) -> bool:
        return _has(words, lexicon.own_choice) and not _has(words, lexicon.forced)

    @staticmethod
    def _third_party(text: str, words: Phrase, lexicon: Lexicon, expecting: Expecting) -> bool:
        """Does the speaker speak of the borrower as someone else? Read before the loan is named."""
        if _has(words, lexicon.wrong_person) or _has(words, lexicon.kin):
            return True
        if expecting is not Expecting.identity:
            return False
        possessive_s = any(m.group().casefold().replace("’", "'") not in _CONTRACTIONS
                           for m in _POSSESSIVE_S.finditer(text))  # fmt: skip
        return possessive_s or _has(words, lexicon.possessive)

    @staticmethod
    def _claims_to_be_the_borrower(words: Phrase, lexicon: Lexicon) -> bool:
        """An explicit first-person claim ("हाँ, मैं ही बोल रहा हूँ", "speaking") with nothing else in it.

        A name, a title or any word outside the short courtesy list makes the reply not tight: the
        classifier judges it, and without one it does not confirm.
        """
        return _has(words, lexicon.is_self) and not _rest(
            words, lexicon.identity_yes | lexicon.is_self | lexicon.self_ok | lexicon.filler
        )

    def _stop_signal(
        self, words: Phrase, lexicon: Lexicon, expecting: Expecting
    ) -> tuple[Intent, dict] | None:
        """A refusal, a request for a person or for a later call; None when the turn holds none."""
        after_loan = expecting not in _NO_ACCOUNT_OF_THE_SALE
        # Third-person or habitual narration: the refusal words belong to the sale, not to this call.
        narrated = after_loan and _has(words, lexicon.narrative)
        # A first-person past ("मैंने कहा था ..."): maybe a quote, maybe meant now; the bot asks.
        recounted = after_loan and _has(words, lexicon.recounts)
        timed = _has(words, lexicon.time_words) and _has(words, lexicon.call_words)
        later = _has(words, lexicon.call_later) or timed
        busy = _has(words, lexicon.occupied)
        if busy and expecting in _OPENING and not _has(words, lexicon.first_person):
            return Intent.wrong_person, {}  # "साहब मीटिंग में हैं": busy, but someone else is
        refuses = _has(words, lexicon.decline)
        if busy and _has(words, lexicon.hurry) and not (later or refuses):
            busy = False  # "थोड़ा बिज़ी हूँ, जल्दी बोलिए": busy, and still says go on
        human = _has(words, lexicon.wants_human)
        short = len(words) <= _STOP_TURN and _has(words, lexicon.decline_short)
        dnc, written = _has(words, lexicon.do_not_call), _has(words, lexicon.written)
        if not (human or refuses or later or busy or short or dnc or written):
            return None
        if narrated:
            return Intent.said, {"settled": False}
        if human:
            return (Intent.maybe_human if recounted else Intent.wants_human), {}
        if recounted:
            return Intent.maybe_decline, {}
        if dnc:
            return Intent.do_not_call, {}
        if written:
            return Intent.written_request, {}
        if later or busy:
            when = "time" if _has(words, lexicon.time_words) else ("ask" if later and not busy else "busy")
            return Intent.call_later, {"callback": when}
        if refuses:
            return Intent.decline, {}
        return None  # a short weak signal: decided by the caller, which knows the yes/no context

    def _intent(
        self, text: str, words: Phrase, lexicon: Lexicon, expecting: Expecting, language: Language
    ) -> tuple[Intent, dict]:
        if not words:
            return Intent.silence, {}
        switch, name = _language_request(words, lexicon, language)
        if switch:
            return Intent.other_language, {"language_name": name}
        if expecting in _OPENING and self._third_party(text, words, lexicon, expecting):
            return Intent.wrong_person, {}
        stop = self._stop_signal(words, lexicon, expecting)
        if stop is not None:
            return stop
        if expecting is Expecting.callback_time:
            return Intent.said, {}
        affirms = _has(words, lexicon.yes_despite_no)
        denies = not affirms and (_has(words, lexicon.no) or _has(words, lexicon.no_at_start, at_start=True))
        if len(words) <= _STOP_TURN and _has(words, lexicon.decline_short):
            # "नहीं, रहने दीजिए" to "may we go on?" is a plain no; elsewhere it is only a hint.
            return (Intent.no if denies and expecting is Expecting.go_ahead else Intent.maybe_decline), {}
        affirms = affirms or (not denies and _has(words, lexicon.yes))
        short = len(words) <= _REPEAT_TURN
        repeats = _only(words, lexicon.asks_repeat_whole) or (short and _has(words, lexicon.asks_repeat))
        if expecting is Expecting.identity:
            if self._claims_to_be_the_borrower(words, lexicon) and not denies:
                return Intent.yes, {"settled": True}
            if _only(words, lexicon.identity_yes | lexicon.self_ok | lexicon.filler):
                # "हाँ जी", "बोलिए", "हेलो": an acknowledgement, not a claim
                return Intent.said, {"settled": True}
            if _has(words, lexicon.who) or _has(words, lexicon.asks_who):
                return Intent.asks_who, {"settled": len(words) <= 4}
            if repeats:
                return Intent.asks_repeat, {"settled": len(words) <= 4}
            return (Intent.no if denies else Intent.said), {"settled": False}
        after_loan = expecting not in _NO_ACCOUNT_OF_THE_SALE
        if _has(words, lexicon.asks_who) and not (after_loan and _has(words, lexicon.narrative)):
            return Intent.asks_who, {}
        if expecting in (Expecting.open, Expecting.told, Expecting.either_or) and _has(
            words, lexicon.took_nothing
        ):
            return Intent.took_nothing, {}
        if repeats:
            return Intent.asks_repeat, {}
        if expecting in (Expecting.confirmation, Expecting.stop_check) and _has(words, lexicon.dont_know):
            return Intent.dont_know, {}  # "पता नहीं" holds a no-word and is not a no to the read-back
        if expecting in (Expecting.go_ahead, Expecting.confirmation, Expecting.stop_check):
            if denies:
                return Intent.no, {}
            if affirms:
                return Intent.yes, {}
        if _has(words, lexicon.dont_know):
            return Intent.dont_know, {}
        if expecting is Expecting.amount and _has(words, lexicon.paid_nothing):
            return Intent.no, {}  # "कुछ नहीं दिया", "फ्री था": an answer, with no figure to read back
        if expecting is Expecting.either_or and _only(words, lexicon.yes | lexicon.no | lexicon.filler):
            return Intent.filler, {}  # "हाँ जी" to "required, or your choice?" says neither
        nothing = _has(words, lexicon.nothing) and _only(words, lexicon.nothing | lexicon.filler)
        if expecting in (Expecting.open, Expecting.told) and nothing:
            return Intent.no, {}  # "कुछ नहीं", "नहीं जी"
        if expecting is Expecting.told and (denies or affirms) and short:
            return (Intent.no if denies else Intent.yes), {}
        if _only(words, lexicon.filler):
            return Intent.filler, {}
        return Intent.said, {}
