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
from functools import cache
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.amounts import Ambiguous, AmountResult, Approximate, Parsed, parse_amount, parse_approx_amount
from samajh.amounts._lexicon import WORDS, norm_key
from samajh.dialogue._lexicon import (
    LANGUAGE_NAMES,
    LEXICONS,
    OWN_LANGUAGES,
    ROMAN_NUMBERS,
    Lexicon,
    Phrase,
    found,
    phrase_at,
    roman_key,
    tokens,
)
from samajh.dialogue._names import is_first_name
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
    yes = "yes"  # at the first-name question: an explicit first-person claim (the strong path)
    # At the first-name question only: an affirmative or go-on reply that is not a first-person claim
    # ("हाँ जी", "बोलिए", "हाँ, रमेश जी से हो रही है"). The call asks the birth year before it names the lender.
    acknowledges = "acknowledges"
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
# Round 3: a free answer (`said`) to a later question that holds a word of the sale's vocabulary
# (`Lexicon.substance`) is settled without the classifier. Set to False to switch this skip off.
SETTLE_ON_SUBSTANCE = True
# Words besides the affirmative and courtesy words that an ordinary confirmation may hold (a first and
# last name). With any such word the reply is not settled: the classifier judges it when there is one.
# Three or more could carry a short clause about someone else ("हाँ बाहर गए हैं"), so they are re-asked.
_ACK_EXTRA = 2
# Endings of a first-person future or intention ("करूंगा", "दूंगी", "lunga"): a plan, maybe a refusal.
_FUTURE = ("ूंगा", "ूंगी", "ेंगे", "unga", "ungi", "oonga", "enge")


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
    # The amount is a bound ("पचास हज़ार तक", "up to 40,000"; `samajh.amounts` marks it): a cover figure or a
    # read-back may carry it, the premium question asks again (iteration 3 fix round).
    bound: bool = False
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
    # Open recall and its follow-up (round 3): the customer's own words name something beyond the loan (a
    # figure, a thing, or something done, taken, deducted or required) in a clause they do not deny. Set by
    # the word lists; it survives a classifier that changes the intent, so the nothing branch needs both.
    names_something: bool = False
    # Open recall and its follow-up (wave 2): the reply holds a denial and names nothing, whatever the
    # intent reads as ("जो था लोन ही था, और कुछ नहीं", "Don't think so.").
    names_nothing: bool = False
    # Mid-call (wave 2): the word lists see a possible takeover (someone else has the phone). Unsettled;
    # a classifier that judges the turn clears it. Without a judgment the call asks who is speaking.
    possible_takeover: bool = False
    # Birth year (wave 2): the reply names more than one year ("1984 या 85"); it never passes.
    two_years: bool = False
    # Mid-call (round 4): any sign the word lists see that someone other than the borrower is speaking,
    # the strong `possible_takeover` ones and weaker ones ("मेरे पति का लोन है", "हेलो? क्या पूछ रहे थे?").
    # Without a classifier label for the turn the call asks who is speaking; a label decides a weak one.
    other_speaker: bool = False
    # The classifier label this reading follows (`LlmFallbackInterpreter`); None when no label was used
    # (no classifier, a failure, a timeout, `unclear`, or a turn the word lists settled).
    classifier_label: str | None = None


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
    """Is the turn the amount plus yes-words, fillers, "that is what I paid" words (`Lexicon.restates`)
    and the word for rupees, and nothing else?"""
    if not isinstance(parsed, Parsed):
        return False
    rest = _rest(
        tokens(text[: parsed.span.start] + " " + text[parsed.span.end :]),
        lexicon.yes | lexicon.filler | lexicon.restates,
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


_CLAUSE_MARKS = re.compile(r"[,.;:!?।|]+")
_QUESTION = re.compile(r"\?")


def _denials(lexicon: Lexicon) -> frozenset[Phrase]:
    return lexicon.no | lexicon.no_at_start | lexicon.nothing | lexicon.took_nothing | lexicon.denial


# Readings that end the call whatever else the turn says: a sign of another speaker does not unsettle them.
_ENDS_AT_ONCE = frozenset({
    Intent.decline, Intent.wants_human, Intent.do_not_call, Intent.written_request, Intent.other_language,
    Intent.wrong_person,
})  # fmt: skip
_GO_AHEAD_ENDS = frozenset({
    Intent.no, Intent.decline, Intent.wants_human, Intent.call_later, Intent.do_not_call, Intent.written_request,
    Intent.maybe_decline, Intent.maybe_human,
})  # fmt: skip
# Yes-words that also serve as an honorific or an intensifier ("नहीं जी", "बिल्कुल टाइम नहीं").
_NOT_COOPERATIVE = frozenset({tokens("जी"), tokens("बिल्कुल")})


def _cooperative(lexicon: Lexicon) -> frozenset[Phrase]:
    """Yes-words and go-on words, without "जी" and "बिल्कुल" ("नहीं जी, रहने दीजिए" is a no)."""
    words = lexicon.yes | lexicon.go_on | lexicon.hurry | lexicon.yes_despite_no
    return words - _NOT_COOPERATIVE


def starts_with_yes(text: str, language: Language) -> bool:
    """At the re-ask: a reply that starts with a yes-word and holds no third-person word or denial."""
    words, lexicon = tokens(text), LEXICONS[language]
    if not words or not lexicon.ack_ok or phrase_at(words, 0, lexicon.yes | lexicon.identity_yes) is None:
        return False
    return not _has(words, lexicon.third_person | lexicon.no | lexicon.kin | lexicon.wrong_person)


def _phrases_of(*texts: str) -> frozenset[Phrase]:
    return frozenset(tokens(text) for text in texts)


# Wave 5: with a year, "ये" points at someone ("हमारे ये तो चौरासी के हैं": my husband) and "क्यों" makes it
# a question, not an answer.
_NOT_OWN_YEAR = _phrases_of("ये", "यह", "क्यों", "क्यूं", "why", "kyon", "kyun", "kyu")


def _number_word(word: str) -> int | None:
    digits = word.translate(_DIGITS)
    return int(digits) if digits.isdigit() else _small_number(word)


def _without_day_and_month(words: Phrase, lexicon: Lexicon) -> Phrase:
    """Drop month names and a day number (1 to 31) next to one: "उन्नीस सौ चौरासी, पंद्रह जून" -> the year."""
    drop: set[int] = set()
    for k in range(len(words)):
        month = phrase_at(words, k, lexicon.months)
        if month is None:
            continue
        drop.update(range(k, k + len(month)))
        for j, beyond in ((k - 1, k - 2), (k + len(month), k + len(month) + 1)):
            if 0 <= j < len(words) and not (0 <= beyond < len(words) and _number_word(words[beyond])):
                day = _number_word(words[j])  # not part of a longer number ("eighty four June")
                if day is not None and 1 <= day <= 31:
                    drop.add(j)
    return tuple(word for k, word in enumerate(words) if k not in drop)


_LATIN_WORD = re.compile(r"[A-Za-z]+")

# Wave 5 fix 2 (Hindi and Hinglish only): a reply-initial "ya" / "yeah" is a yes, not "या" (or); a numeric
# date ("15-06-1984", "15/06/84") gives its year only; a day before "तारीख" is not a year.
_LEADING_YES = re.compile(r"^\s*(?:ya|yaa|yeah|yah)\b[\s,.!]*", re.IGNORECASE)
_NUMERIC_DATE = re.compile(r"(?<!\d)\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*(\d{4}|\d{2})(?!\d)")
_TARIKH = frozenset({"तारीख", "tarikh", "tareekh", "tarik", "tareek"})


def _without_tarikh_day(words: Phrase) -> Phrase:
    """Drop "तारीख" and a day number (1 to 31) just before it: "पंद्रह तारीख जून चौरासी" -> "जून चौरासी"."""
    drop: set[int] = set()
    for k, word in enumerate(words):
        if word in _TARIKH:
            drop.add(k)
            day = _number_word(words[k - 1]) if k else None
            if day is not None and 1 <= day <= 31:
                drop.add(k - 1)
    return tuple(word for k, word in enumerate(words) if k not in drop)


def _without_own_office(words: Phrase, lexicon: Lexicon) -> Phrase:
    """At the year (Hindi and Hinglish): "मैं ... ऑफिस में हूं" is the speaker's own whereabouts, so "ऑफिस"
    there is not a cue that the borrower is away. "वो ऑफिस में हैं" has no "मैं ... हूं" and keeps it."""
    if lexicon.ack_ok and "मैं" in words and "हूं" in words:
        return tuple(word for word in words if word != "ऑफिस")
    return words


def _without_year_vo(words: Phrase, lexicon: Lexicon) -> Phrase:
    """At the year (Hindi and Hinglish, round 4): "वो" before "तो", a year word or a number is "that", not a
    person ("साल? वो तो याद नहीं", "वो उन्नीस सौ चौरासी"). Any other sign stays: "वो तो बाहर हैं" keeps "बाहर हैं"."""
    if not lexicon.ack_ok:
        return words
    year_words = ("तो", "साल", "सन", "year", "ईयर")
    return tuple(
        word for k, word in enumerate(words)
        if not (word == "वो" and k + 1 < len(words) and (words[k + 1] in year_words or _number_word(words[k + 1])))
    )  # fmt: skip


def _year_reply_cleaned(text: str) -> str:
    """The birth-year reply without a leading yes-"ya", with numeric dates as their year and no "तारीख" day."""
    first = tokens(text)[:1]
    if first and first[0] in ("ya", "yaa", "yeah", "yah"):
        text = _LEADING_YES.sub("", text, count=1)
    text = _NUMERIC_DATE.sub(lambda m: m.group(1), text.translate(_DIGITS))
    if any(word in _TARIKH for word in tokens(text)):
        text = ", ".join(" ".join(_without_tarikh_day(tokens(part))) for part in _CLAUSE_MARKS.split(text))
    return text


_WORD = re.compile(r"[^\s,.;:!?।|]+")


def _without_leading_no_words(text: str, lexicon: Lexicon) -> str:
    """At the year (iteration 3 fix round): no-words before the first other word ("नहीं नहीं, चौरासी", "nahi, 1984")
    answer the earlier turn or the doubt in the question; they are dropped, so the reply holds one year, not a
    self-correction. A no-word after a number still marks a guess ("चौरासी, नहीं पचासी")."""
    no = lexicon.no | lexicon.no_at_start | _phrases_of("no", "nope", "जी नहीं", "नहीं जी")
    cut = 0
    for match in _WORD.finditer(text):
        word = tokens(match.group())
        if not word or (word not in no and word not in (("जी",),)):
            break
        cut = match.end()
    rest = text[cut:].lstrip(" ,.;:!?।|")
    return rest if tokens(rest) else text


def _devanagari_numbers(text: str) -> str:
    """Romanised Hindi number words in Devanagari ("unnees sau chaurasi" -> "उन्नीस सौ चौरासी"), so the year
    is read the same in either script (wave 4). Other words are left as they are."""
    return _LATIN_WORD.sub(lambda m: ROMAN_NUMBERS.get(roman_key(m.group()), m.group()), text)


def _distance(a: str, b: str, limit: int = 1) -> int:
    """Edit distance in code points (one vowel sign is one edit), counted up to `limit + 1`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


@cache
def _number_words() -> tuple[dict[str, tuple], dict[str, str]]:
    """The Devanagari number words `samajh.amounts` reads (lookup key -> value), and the romanised spellings
    of `ROMAN_NUMBERS` (folded key -> Devanagari word)."""
    devanagari = {key: word.atoms for key, word in WORDS.items()
                  if word.kind == "num" and re.search(r"[\u0900-\u097F]", key)}  # fmt: skip
    return devanagari, ROMAN_NUMBERS


@cache
def _known_words(language: Language) -> frozenset[str]:
    """Every single word of the language's lexicon and every word `samajh.amounts` knows: never corrected."""
    lexicon = LEXICONS[language]
    words = {word for name in lexicon.__dataclass_fields__ for phrase in getattr(lexicon, name) for word in phrase}
    return frozenset(words | set(WORDS))


def _near_numbers(text: str, language: Language) -> tuple[str, bool]:
    """At the year question (round 4): a word one edit from exactly one number word is read as that word.

    "चौरसी" (one vowel sign dropped) -> "चौरासी"; "chaurassee" -> "चौरासी". A word that is a number word or a
    known word is left alone, as is a Devanagari word under 4 code points or a romanised one under 5
    letters. A word one edit from two different numbers, or a word straight after "सौ" / "हज़ार" that is two
    edits from some number and not corrected, is number-like but unreadable: the reply is then read as
    holding no year (`True` in the result), so it gets the one re-ask instead of being read as "उन्नीस सौ"
    alone. The corrected year must still equal the
    record's.
    """
    devanagari, roman = _number_words()
    known = _known_words(language)
    unsure = False

    def fix(match: re.Match) -> str:
        nonlocal unsure
        word = match.group()
        if re.fullmatch(r"[A-Za-z]+", word):
            key = roman_key(word)
            if key in roman or len(key) < 5 or tokens(word)[0] in known or norm_key(word) in WORDS:
                return word
            spans = {other: roman[other] for other in roman}
        else:
            key = norm_key(word)
            if key in devanagari or len(key) < 4 or key in known or tokens(word)[0] in known:
                return word
            spans = {other: atoms for other, atoms in devanagari.items()}
        near, like = {}, False
        for other, value in spans.items():
            distance = _distance(key, other, limit=2)
            like = like or distance <= 2
            if distance <= 1:
                near.setdefault(value, other)
        if len(near) == 1:
            value, other = near.popitem()
            return value if isinstance(value, str) else other
        before = tokens(match.string[: match.start()])[-1:]
        unsure = unsure or len(near) > 1 or (like and before in (("सौ",), ("सो",), ("हजार",), ("sau",), ("sao",)))
        return word

    return re.sub(r"[A-Za-z]+|[\u0900-\u097F]+", fix, text), unsure


def _year_in(text: str, words: Phrase, lexicon: Lexicon) -> tuple[int | None, bool]:
    """The birth year in a reply, and whether it names two different years.

    Each clause is read alone, and again without the words a year reply may hold ("सन", "sir"), so
    "चौरासी, उन्नीस सौ चौरासी" is one year and "nineteen eighty-four, sir" is read at all.
    """
    found_years: list[int] = []
    for part in [*_CLAUSE_MARKS.split(text), text]:
        part_words = tokens(part)
        plain = " ".join(_rest(part_words, lexicon.year_ok | lexicon.filler | lexicon.yes))
        heard = (birth_year(plain) if plain else None) or birth_year(part)
        if heard is not None and heard >= 10:  # "एक", "दो" turn up in replies that give no year
            found_years.append(heard)
    digits = [int(m.group()) for m in re.finditer(r"(?<!\d)\d{2,4}(?!\d)", text.translate(_DIGITS))]
    found_years += [d for d in digits if 10 <= d < 100 or 1900 <= d <= 2099]
    if not found_years:
        return None, False
    full = [y for y in found_years if y >= 100]
    distinct = {y % 100 for y in found_years}
    best = full[0] if full else found_years[0]
    return best, len(distinct) > 1


def _names_something(text: str, lexicon: Lexicon) -> bool:
    """Does any clause the customer does not deny name a figure, a thing or something done?

    A clause ends at punctuation or a clause-break word ("पर", "बस", "but"). A clause holding a no-word
    ("नहीं", "not", "कुछ नहीं") is denied as a whole. In a clause that names the loan, "took" is the loan.
    """
    no = lexicon.no | lexicon.nothing | lexicon.dont_know
    for part in _CLAUSE_MARKS.split(text):
        clause: list[str] = []
        words = tokens(part)
        for k, word in enumerate((*words, "")):
            if word and phrase_at(words, k, lexicon.clause_break) is None:
                clause.append(word)
                continue
            said = tuple(clause)
            clause = []
            if not said or _has(said, no):
                continue
            figure = parse_amount(" ".join(said))
            if isinstance(figure, Parsed) or (isinstance(figure, Ambiguous) and figure.candidates):
                return True
            things = found(said, lexicon.names_thing)
            if _has(said, lexicon.the_loan):  # "सोना गिरवी रखा और पैसे लिए": the loan's money is the loan
                things = [t for t in things if t not in lexicon.loan_money]
            if things:
                return True
            if _has(said, lexicon.take) and not _has(said, lexicon.the_loan):
                return True
    return False


_NEGATORS = frozenset(tokens(w) for w in ("dont", "do not", "not", "never", "मत"))
_LATER = frozenset({"बाद", "later"})


def _refuses_to_talk(words: Phrase, lexicon: Lexicon) -> bool:
    """A refusal to talk, by structure (round 4): a no-word, a talk or listen word and a wanting or doing
    word within three words either side of the talk word ("नहीं करनी कोई बात", "mujhe baat nahi karni", "kuch nahi sunna"),
    or a hang-up word with a no-word in the turn ("नहीं चाहिए कुछ, रखिए"). "कोई बात नहीं" alone is not one."""
    words = _rest(words, lexicon.yes_despite_no)
    negators = lexicon.no | lexicon.no_at_start | _NEGATORS
    if _has(words, lexicon.hang_up) and _has(words, negators):
        return True
    for k in range(len(words)):
        window = words[max(0, k - 3) : k + 4]
        if phrase_at(words, k, lexicon.talk) is not None and _has(window, negators) and _has(window, lexicon.want_do):
            return True
    return False


# Iteration 3 (Hindi and Hinglish): first-person subjects, habitual and wanting verbs, "interested" words.
_I_SUBJECT = frozenset(tokens(w) for w in (
    "मैं", "मुझे", "मुझको", "हम", "हमें", "हमको", "hum", "hume", "humein", "humko", "mujhko", "i", "me", "im",
))  # fmt: skip
_HABITUAL = frozenset(tokens(w) for w in ("करता", "करती", "करते", "karta", "karti", "karte", "चाहता", "चाहती",
                                          "chahta", "chahti"))  # fmt: skip
_WANT = frozenset(tokens(w) for w in ("चाहिए", "chahiye", "chaiye", "chahie", "want", "need"))
_INTERESTED = frozenset(tokens(w) for w in ("इंटरेस्टेड", "इंटरेस्ट", "interested", "intrested", "दिलचस्पी", "रुचि",
                                            "ruchi", "dilchaspi"))  # fmt: skip
# "करना", "करो", "कीजिए": the verb of "don't call" ("मत करना फोन", "phone mat karo").
_DO = frozenset(tokens(w) for w in ("करना", "करो", "करिए", "कीजिए", "करें", "करे", "karna", "karo", "kariye",
                                    "kijiye", "karein", "kare"))  # fmt: skip
_CALL = frozenset(tokens(w) for w in ("कॉल", "फोन", "call", "phone"))
# "नहीं हैं" (honorific or plural "is/are not"): said of a person who is not there, not of the speaker.
_IS_NOT_THERE = frozenset(tokens(w) for w in ("नहीं हैं", "nahi hain", "nahin hain", "not here", "not available"))
_WE = frozenset(tokens(w) for w in ("हम", "hum", "we"))


def _near(words: Phrase, k: int, phrases: frozenset[Phrase], span: int = 3) -> bool:
    return _has(words[max(0, k - span) : k + span + 1], phrases)


def first_person_refusal(words: Phrase, lexicon: Lexicon) -> bool:
    """A first-person refusal, by structure (iteration 3; Hindi and Hinglish, read before the loan is named and
    at the stop checks only). Three shapes, each with a no-word near its head word:
    - "I (habitually) don't do/want talk": a first-person subject and a talk word with a habitual or wanting verb
      ("मैं ऐसी कॉल पे बात नहीं करता", "hum phone pe baat nahi karte");
    - "not wanted": "चाहिए" or "want" ("मुझे नहीं चाहिए", "kuch nahi chahiye", "I don't want");
    - "not interested": an interest word ("interested nahi hoon", "नहीं हूँ interested", "रुचि नहीं").
    After the loan is named the same words can be an account of the sale ("मुझे नहीं चाहिए था"), so the caller
    reads this only where there is no sale to recount."""
    if not lexicon.ack_ok:
        return False
    words = _rest(words, lexicon.yes_despite_no)
    negators = lexicon.no | lexicon.no_at_start | _NEGATORS
    first = _has(words, _I_SUBJECT)
    for k in range(len(words)):
        head = words[k : k + 1]
        if head in lexicon.talk and first and _near(words, k, negators) and _near(words, k, _HABITUAL | lexicon.want_do):
            return True
        if (head in _WANT or head in _INTERESTED) and _near(words, k, negators, span=2):
            return True
    return False


_FREE = frozenset(tokens(w) for w in ("फ्री", "free", "खाली", "khali", "फुर्सत", "fursat"))


def not_free(words: Phrase, lexicon: Lexicon) -> bool:
    """ "I am not free" ("abhi free nahi hoon", "फुर्सत नहीं है"): busy, by structure. Before the loan is named
    only: later "फ्री नहीं था" is about the product. Hindi and Hinglish only."""
    negators = lexicon.no | lexicon.no_at_start | _NEGATORS
    return bool(lexicon.ack_ok) and any(
        words[k : k + 1] in _FREE and _near(words, k, negators, span=2) for k in range(len(words))
    )


def asks_no_calls(words: Phrase, lexicon: Lexicon) -> bool:
    """ "Don't call", by structure (iteration 3): a call word with "मत" and a do-verb near it ("मत करना फोन",
    "phone mat karna dobara"), or "दोबारा/फिर/कभी" + "मत" + a do-verb. Hindi and Hinglish only."""
    if not lexicon.ack_ok:
        return False
    never = frozenset(tokens(w) for w in ("मत", "ना", "न"))
    again = frozenset(tokens(w) for w in ("दोबारा", "फिर", "कभी", "बाद में भी", "dobara", "kabhi"))
    for k in range(len(words)):
        if words[k : k + 1] in _CALL | again and _near(words, k, never) and _near(words, k, _DO):
            return True
    return False


# Iteration 3 fix round: "remove my number / take me off the list", by structure. A removal verb within four
# words of a number or list word ("mera number hata do", "मेरा नंबर लिस्ट से हटा दीजिए", "number delete kar do",
# "हटाओ मेरा नंबर"); "निकाल" ("take out") only with a list word ("list se nikaal do"), since "पैसे निकाल" is money.
_REMOVE = frozenset(tokens(w) for w in ("हटा*", "हटव*", "hata*", "hatwa*", "hataa*", "डिलीट*", "delete*", "रिमूव*",
                                        "remove*", "erase*", "मिटा*", "mita*"))  # fmt: skip
_TAKE_OUT = frozenset(tokens(w) for w in ("निकाल*", "निकल*", "nikal*", "nikaal*", "take off", "take me off"))
_NUMBER_WORDS = frozenset(tokens(w) for w in ("नंबर", "नम्बर", "number", "contact", "कॉन्टैक्ट", "डेटा", "data",
                                              "डिटेल*", "detail*", "नं", "num", "numbr", "nmbr", "मोबाइल",
                                              "mobile"))  # fmt: skip
# "mera no. hata do" (iteration 3, round 2): "no" is the number only straight after "my" ("मेरा", "mera", "my").
_MY_NUMBER_ABBR = frozenset(tokens(w) for w in ("मेरा no", "मेरा नो", "हमारा no", "हमारा नो", "my no"))
_LIST_WORDS = frozenset(tokens(w) for w in ("लिस्ट", "list", "सूची", "रिकॉर्ड", "record*", "database", "डेटाबेस"))


def asks_removal(words: Phrase) -> bool:
    """ "Remove my number" in any word order or script (iteration 3 fix round). Read at every stage."""
    numbers = _NUMBER_WORDS | _LIST_WORDS | _MY_NUMBER_ABBR
    for k in range(len(words)):
        if phrase_at(words, k, _REMOVE) is not None and _near(words, k, numbers, span=4):
            return True
        if phrase_at(words, k, _TAKE_OUT) is not None and _near(words, k, _LIST_WORDS, span=4):
            return True
    return False


# Iteration 3 fix round: signs of a speaker new to the call, read at every position after the right-party pass.
# (1) A question about whom the caller wants or was talking to ("किससे बात करनी है?", "aap kisse baat kar rahe the",
# "who do you want?"), not "who am I talking to?" (a first-person subject asks who the caller is).
_WHOM = frozenset(tokens(w) for w in ("किससे", "किस से", "किसको", "किस को", "किसे", "kisse", "kis se", "kisko", "kis ko",
                                      "kise", "kisase", "whom"))  # fmt: skip
_WHOM_WANT = frozenset(tokens(w) for w in ("बात", "बोल*", "talk*", "speak*", "चाहिए", "chahiye", "chaiye", "want*",
                                           "need*", "ढूंढ*", "ढूँढ*", "dhoondh*", "dhundh*", "dhund*", "मिलना", "milna",
                                           "looking", "calling for", "asking for", "काम"))  # fmt: skip
_WHO_WANTED = frozenset(tokens(w) for w in ("कौन चाहिए", "kaun chahiye", "कौन चाहिए था", "किसका काम", "kiska kaam"))
_ASKER_IS_ME = frozenset(tokens(w) for w in ("मैं", "i", "im", "i am", "हूं", "मुझे", "मैंने"))
# (2) The speaker says they just arrived ("मैं तो अभी आया", "abhi abhi aayi hoon", "just came in").
_JUST = frozenset(tokens(w) for w in ("अभी", "abhi", "just", "अभी अभी", "abhi abhi", "अभी तो", "abhi to", "अभी ही"))
_ARRIVED = frozenset(tokens(w) for w in (
    "आया", "आई", "आयी", "आए", "आये", "पहुंचा", "पहुंची", "पहुंचे", "aaya", "aya", "aayi", "ayi", "aai", "aaye", "aye",
    "pahuncha", "pahunchi", "pahunche", "came", "arrived", "got here", "got home", "got back", "walked in", "came in",
    "घर आया", "घर आई", "ghar aaya", "ghar aayi",
))  # fmt: skip
# (3) The speaker knows nothing of the matter ("मुझे इसका कुछ नहीं पता", "mujhe is baare mein kuch nahi maloom").
_KNOW_NOTHING = frozenset(tokens(w) for w in (
    "कुछ नहीं पता", "कुछ नहीं मालूम", "कुछ पता नहीं", "कुछ मालूम नहीं", "कोई जानकारी नहीं", "कुछ जानकारी नहीं",
    "कुछ नहीं जानता", "कुछ नहीं जानती", "पता ही नहीं", "kuch nahi pata", "kuch pata nahi", "kuch nahi maloom",
    "kuch nahi malum", "know nothing", "dont know anything", "no idea about", "nothing about this", "dont know about this",
    "no idea what", "idea नहीं", "आइडिया नहीं",
))  # fmt: skip
_THIS_MATTER = frozenset(tokens(w) for w in ("इसका", "इसके", "इसकी", "इस बारे", "इसके बारे", "iska", "iske", "iski",
                                             "is baare", "is bare", "iske baare", "about this", "about it", "ये सब",
                                             "yeh sab", "ye sab"))  # fmt: skip
# Where a question about the sale is pending, "I know nothing about it" is an answer; it is a sign only with a "what
# is this about?" question or an arrival. Elsewhere (the go-ahead, a read-back, a stop check, "when shall we call?")
# it answers nothing and is a sign by itself.
_SALE_QUESTIONS = frozenset({"open", "told", "either_or", "amount"})


def newcomer_sign(words: Phrase, lexicon: Lexicon, expecting: str) -> bool:
    """A speaker new to the call (iteration 3 fix round; Hindi and Hinglish, English words too): a question about
    whom the caller wants or was talking to, an arrival, or knowing nothing of the matter where that is no answer.
    A strong sign: it gets the who-check whatever a classifier says."""
    if not lexicon.ack_ok:
        return False
    asks_me = _has(words, _ASKER_IS_ME)
    for k in range(len(words)):
        if phrase_at(words, k, _WHOM) is not None and not asks_me and _near(words, k, _WHOM_WANT, span=4):
            return True
        if words[k] in ("who", "whom") and "you" in words[k + 1 : k + 4] and _has(words[k + 1 : k + 6], _WHOM_WANT):
            return True
    if _has(words, _WHO_WANTED):
        return True
    arrived = any(
        phrase_at(words, k, _JUST) is not None and _has(words[k + 1 : k + 4], _ARRIVED) for k in range(len(words))
    )
    if arrived:
        return True
    knows_nothing = _has(words, _KNOW_NOTHING) or (_has(words, _THIS_MATTER) and _has(words, lexicon.dont_know))
    if not knows_nothing:
        return False
    if expecting not in _SALE_QUESTIONS:
        return True
    return _has(words, lexicon.asks_who)


def speaks_of_someone_absent(words: Phrase, lexicon: Lexicon) -> bool:
    """Before the loan is named: does the reply speak of a person who is not the speaker, or who is away? A
    third-person pronoun, an absent cue, a pointer ("उनका"), "उनको", or "X नहीं हैं" without "हम"."""
    elsewhere = lexicon.third_person | lexicon.absent | lexicon.absent_frame | lexicon.pointer
    return _has(words, elsewhere) or (_has(words, _IS_NOT_THERE) and not _has(words, _WE))


# Iteration 3, no second check: words that make a yes at the right-party question not a pass.
_IDENTITY_HEDGE = frozenset(tokens(w) for w in (
    "शायद", "होगा", "होगी", "पक्का नहीं", "लगता है", "shayad", "hoga", "lagta है", "maybe", "probably", "i think",
    "not sure", "guess",
    # Iteration 3 fix round: "take it that way" ("वही समझ लीजिए", "maan lo") is not a claim but leave to assume one;
    # and "वही है" / "wahi hai" says "he is the one", in the third person. "वही हूँ" (I am) is not here.
    "समझ लीजिए", "समझ लो", "समझ लें", "समझिए", "समझो", "मान लीजिए", "मान लो", "मान लें", "मानिए", "मानो",
    "समझ lijiye", "समझ lo", "samjho", "samjhiye", "samajhiye", "maan lijiye", "maan lo", "man lo", "maan lijie",
    "maniye", "maano", "कह सकते हैं", "कह लीजिए", "keh sakte", "kah sakte", "you can say", "say so", "kind of", "sort of",
    "consider", "assume", "वही है", "वही हैं", "यही है", "यही हैं", "वो ही है", "वो ही हैं", "that is him", "thats him",
    "that is her", "thats her", "he is", "she is",
))  # fmt: skip


def asks_something(text: str, language: Language) -> bool:
    """Does the reply ask something ("क्या", "कौन", "किस बारे में", "what")?"""
    words, lexicon = tokens(text), LEXICONS[language]
    return _has(words, lexicon.who | lexicon.asks_who | lexicon.what_q)


def hedges_or_asks(text: str, language: Language) -> bool:
    """At the right-party question with no second check (P8): does the reply hedge ("शायद", "पता नहीं") or ask
    something (`asks_something`)? Such a reply is never a pass."""
    words, lexicon = tokens(text), LEXICONS[language]
    return asks_something(text, language) or _has(words, lexicon.dont_know | _IDENTITY_HEDGE)


def means_now(text: str, language: Language) -> bool:
    """At "when shall we call?": does the reply mean now ("अभी बोलिए", "now is fine"), naming no later time
    and holding no no-word ("अभी नहीं")?"""
    words, lexicon = tokens(text), LEXICONS[language]
    if not _has(words, lexicon.now_words):
        return False
    if _has(words, lexicon.go_on | lexicon.hurry | lexicon.do_now):
        return True  # "नहीं, अभी ठीक है, आगे बढ़िए": now and go on wins over any no-word or later time
    # Round 4: a no-word is the answer to "later?" ("नहीं नहीं, अभी कर लीजिए", "later nahi, abhi") unless it
    # negates the now ("अभी नहीं", "not now"), and a "later" counts only when nothing negates it.
    no = lexicon.no | lexicon.no_at_start | _NEGATORS
    for k, word in enumerate(words):
        if (word,) in lexicon.now_words and (
            (k + 1 < len(words) and phrase_at(words, k + 1, no) is not None) or (k and words[k - 1] == "not")
        ):
            return False
        if word in _LATER and not _has(words[k + 1 : k + 4], no):
            return False
    return not _has(words, lexicon.time_words | lexicon.call_later | lexicon.decline | lexicon.occupied)


# Iteration 3, round 2: at the go-ahead ("क्या दो-तीन मिनट बात करें?"), a reply that echoes the bot's time phrase or
# names a short delay. Speech heard "do-teen minute baat kar sakte hain" as "15 minute baad".
_MINUTE = _phrases_of("मिनट", "मिनिट", "minutes", "mins", "min", "minit", "सेकंड", "second", "seconds", "sec")
_SHORT_WAIT = _phrases_of("थोड़ी देर", "थोड़ा देर", "जरा देर", "कुछ देर", "thodi der", "thoda der", "thodi dair", "zara der",
                          "jara der", "kuch der", "एक सेकंड", "ek second", "one minute", "a minute")  # fmt: skip
_ECHO = _phrases_of("दो तीन", "do teen", "do tin", "दो चार", "do char", "two three")
_DO_LATER = _phrases_of("बाद करना", "बाद कर लेना", "बाद कीजिए", "बाद करिए", "बाद करो", "बाद कर दो", "बाद कर दीजिए",
                        "बाद में करना", "बाद में कीजिए", "बाद में करिए", "बाद में करो", "later")  # fmt: skip


def short_delay_or_echo(text: str, language: Language) -> bool:
    """At the go-ahead (iteration 3, round 2): does the reply only echo the bot's time phrase or name a short delay
    ("दो-तीन मिनट?", "15 minute baad", "थोड़ी देर"), with no refusal, no no-word and no clear later (a call or phone
    word, "बाद में करना", a day or hour or clock time, "busy", a call-back phrase)? Such a reply gets one re-ask, not
    an end. Hindi and Hinglish only."""
    words, lexicon = tokens(text), LEXICONS[language]
    if not lexicon.ack_ok or not _has(words, _MINUTE | _SHORT_WAIT | _ECHO):
        return False
    negators = lexicon.no | lexicon.no_at_start | _NEGATORS | lexicon.nothing
    stops = (
        lexicon.decline | lexicon.do_not_call | lexicon.call_later | lexicon.occupied | lexicon.wants_human
        | lexicon.written | _CALL | _DO_LATER
    )  # fmt: skip
    if _has(words, negators | stops):
        return False
    if _refuses_to_talk(words, lexicon) or first_person_refusal(words, lexicon) or not_free(words, lexicon) \
            or asks_no_calls(words, lexicon) or asks_removal(words):  # fmt: skip
        return False
    later_times = frozenset(p for p in lexicon.time_words if "मिनट" not in p and "देर" not in p)
    if _has(words, later_times | _phrases_of("tomorrow", "evening", "morning", "hour", "hours", "night")):
        return False
    return not _has(words, lexicon.kin | lexicon.relation | lexicon.third_person | lexicon.pointer | lexicon.absent)


def affirms_or_goes_on(text: str, language: Language) -> bool:
    """Does the reply hold a yes-word or a go-on word ("हाँ", "बोलिए", "pucho")?"""
    lexicon = LEXICONS[language]
    return _has(tokens(text), lexicon.yes | lexicon.identity_yes | lexicon.go_on | lexicon.hurry)


def _self_words(lexicon: Lexicon) -> frozenset[Phrase]:
    """The closed vocabulary of a reply that affirms being the borrower (round 4): yes-words, first-person
    claim words, courtesy, address forms, go-on words and fillers."""
    words = (
        lexicon.yes | lexicon.identity_yes | lexicon.is_self | lexicon.first_person | lexicon.self_ok
        | lexicon.go_on | lexicon.hurry | lexicon.address | lexicon.filler
    )  # fmt: skip
    return words | _INTERJECTIONS if lexicon.ack_ok else words


# Iteration 3 fix round (Hindi and Hinglish): interjections a self-claim may carry ("अरे मैं ही हूँ", "arre main hi").
_INTERJECTIONS = frozenset(tokens(w) for w in (
    "अरे", "अरी", "अजी", "ओह", "ओहो", "ओ", "अरे बाबा", "बाबा", "सुनिए", "सुनो", "देखिए", "बस", "भई", "arre", "are", "arey",
    "aray", "ajee", "aji", "oh", "oho", "suniye", "suno", "dekhiye", "bhai", "bhayi", "yaar", "haan haan", "ji ji",
))  # fmt: skip


def _is_name(word: str, first_name: str) -> bool:
    """Is this spoken word the record's first name, in Devanagari or Latin spelling (`_names.is_first_name`)?"""
    return is_first_name(word, first_name)


def _denies(words: Phrase, lexicon: Lexicon) -> bool:
    """A no-word or a denial, not counting "no problem" forms."""
    words = _rest(words, lexicon.yes_despite_no)
    return _has(words, lexicon.no | lexicon.nothing | lexicon.denial) or _has(
        words, lexicon.no_at_start, at_start=True
    )


def _without_leading_no(words: Phrase, lexicon: Lexicon) -> Phrase:
    """At the who-check: "नहीं भाई, मैं ही हूँ" is "no, it is me". A no-word at the start goes when the reply holds
    a first-person claim ("मैं ही", "बोल रहा हूं"); the rest is read as usual."""
    if not _has(words, lexicon.is_self):
        return words
    no = lexicon.no | lexicon.no_at_start
    while words and phrase_at(words, 0, no) is not None:
        words = words[len(phrase_at(words, 0, no)) :]
    return words


def points_elsewhere(text: str, language: Language, *, count_denial: bool = True) -> bool:
    """At the who-check (round 4): does the reply speak of another person or deny being the borrower? A
    relation word that is not a form of address, a third-person word or possessive, an absent or "not me"
    cue, a denial, or a takeover sign. Such a reply ends the call whatever the classifier says. With
    `count_denial` False a plain no-word is not counted (a refusal to talk holds one: "मुझे बात नहीं करनी")."""
    lexicon = LEXICONS[language]
    words = _without_leading_no(tokens(text), lexicon)
    if not words:
        return False
    relations = lexicon.kin | lexicon.relation
    address_only = RuleInterpreter._only_address(words, lexicon) and not _has(_rest(words, lexicon.address), relations)
    related = _has(words, relations) and not address_only
    elsewhere = lexicon.third_person | lexicon.wrong_person | lexicon.absent | lexicon.absent_frame | lexicon.pointer
    possessive_s = any(m.group().casefold().replace("’", "'") not in _CONTRACTIONS
                       for m in _POSSESSIVE_S.finditer(text))  # fmt: skip
    return (
        related or possessive_s or _has(words, elsewhere | lexicon.not_me) or (count_denial and _denies(words, lexicon))
        or any(_signs(words, lexicon))
    )  # fmt: skip


def affirms_self(text: str, language: Language, first_name: str) -> bool:
    """At the who-check (round 4): an affirmation of being the borrower by the word lists alone.

    Every word must be explained by the closed vocabulary (`_self_words`) or be the borrower's own first
    name, the reply must hold a yes-word or a first-person claim, and nothing may point elsewhere
    (`points_elsewhere`). "हाँ", "हाँ जी बोलिए", "मैं Ramesh बोल रहा हूँ" pass; "हाँ, मैं उनका बेटा, बोलो" does not.
    """
    lexicon = LEXICONS[language]
    words = _without_leading_no(tokens(text), lexicon)
    if not words or points_elsewhere(text, language):
        return False
    rest = [word for word in _rest(words, _self_words(lexicon)) if not _is_name(word, first_name)]
    claims = lexicon.yes | lexicon.identity_yes | lexicon.is_self | lexicon.first_person | lexicon.go_on
    return not rest and _has(words, claims)


_SELF_ALONE = frozenset(tokens(w) for w in ("खुद", "myself", "ख़ुद"))
_I_WORD = frozenset(tokens(w) for w in ("मैं", "i", "im", "i am"))
_I_COMPLETES = frozenset(tokens(w) for w in ("ही", "हूं", "am", "here"))


def _another_name(words: Phrase, lexicon: Lexicon, first_name: str) -> bool:
    """ "सुरेश बोल रहा हूँ", "मैं सुरेश": a word that is not the borrower's first name and not in the closed
    vocabulary, straight before a speaking word or straight after "मैं"."""
    closed = _self_words(lexicon)

    def other(word: str) -> bool:
        return phrase_at((word,), 0, closed) is None and not _is_name(word, first_name)

    for k, word in enumerate(words):
        if k and phrase_at(words, k, lexicon.speak) is not None and other(words[k - 1]):
            return True
        if (word,) in _I_WORD and k + 1 < len(words) and other(words[k + 1]):
            return True
    return False


def _explicit_self_claim(words: Phrase, lexicon: Lexicon, first_name: str) -> bool:
    """An explicit first-person self-claim: "मैं ही", "बोल रहा हूँ", "speaking", "it's me" (`Lexicon.is_self`),
    "ख़ुद", "myself", "मैं" with the first name or with "ही"/"हूँ", or the first name with a speaking word; and
    no other name in the place of the speaker (`_another_name`)."""
    if _another_name(words, lexicon, first_name):
        return False
    if _has(words, lexicon.is_self | _SELF_ALONE):
        return True
    named = any(_is_name(word, first_name) for word in words)
    if _has(words, _I_WORD) and (named or _has(words, _I_COMPLETES)):
        return True
    return named and _has(words, lexicon.speak | frozenset(tokens(w) for w in ("here", "this is")))


_POSSESSED = frozenset(tokens(w) for w in ("का", "की", "के", "ka", "ki", "ke", "s"))


def _name_possessed(words: Phrase, lexicon: Lexicon, first_name: str) -> bool:
    """ "मैं रमेश का भाई": the first name followed by a possessive is someone else's relation, never a claim."""
    return any(
        _is_name(word, first_name) and k + 1 < len(words) and phrase_at(words, k + 1, lexicon.possessive | _POSSESSED)
        for k, word in enumerate(words)
    )


# An explanation that a relative or a child had the phone (iteration 3 fix round): past tense, no speaking now.
_CHILD = frozenset(tokens(w) for w in ("बच्चे", "बच्चा", "बच्ची", "बच्चों", "बच्चो", "bachche", "bachcha", "bacche",
                                       "baccha", "bachhe", "bachi", "bachchi", "kid", "kids", "child", "children"))  # fmt: skip
_PHONE = frozenset(tokens(w) for w in ("फोन", "मोबाइल", "mobile", "कॉल", "line", "लाइन"))
_PAST = frozenset(tokens(w) for w in ("था", "थी", "थे", "लिया", "ली", "लिए", "उठाया", "उठाई", "उठा लिया", "दिया", "दे दिया",
                                      "had", "took", "picked", "was", "were", "tha", "thi", "the", "liya", "uthaya",
                                      "utha liya", "le liya", "diya"))  # fmt: skip
_NOW_SPEAKING = frozenset(tokens(w) for w in ("बोल रह*", "बात कर रह*", "speaking", "is talking", "अब", "ab", "now"))


def _explains_phone(words: Phrase, lexicon: Lexicon) -> bool:
    """ "बच्चे ने फ़ोन ले लिया था", "meri beti ne phone utha liya tha": a relative or a child had the phone, in the past,
    and nobody else is said to be speaking now. It points at no third person ("उनके बेटे ने" names the borrower)."""
    if not lexicon.ack_ok or not _has(words, _PHONE) or not _has(words, _PAST):
        return False
    if not (_has(words, lexicon.relation | lexicon.kin | _CHILD)):
        return False
    if _has(words, _NOW_SPEAKING | lexicon.pointer | lexicon.third_person | lexicon.absent_frame | lexicon.not_me):
        return False
    return not _has(words, _I_WORD)


def who_check_claim(text: str, language: Language, first_name: str, *, closed: bool = True) -> bool:
    """At the who-check (iteration 3 fix round): an explicit first-person claim to be the borrower.

    The claim needs a first-person word and "ही" / "ख़ुद" / "बोल रहा हूँ" / the first name as the subject complement
    ("अरे मैं ही हूँ, रमेश", "haan main Ramesh bol raha hoon"); interjections and fillers may stand beside it. The first
    name followed by a possessive ("मैं रमेश का भाई") is no claim. A clause that explains a relative or a child had the
    phone ("बच्चे ने फ़ोन ले लिया था, मैं रमेश बोल रहा हूँ") is set aside, punctuated or not. Everything else must not
    point at someone else (`points_elsewhere`) and, with `closed` (the word lists alone), must be explained by the
    closed vocabulary. A bare yes is never a claim. With `closed=False` (the classifier read `confirms_self`) other
    words may stand in the claim's clauses; the explicit claim is still required."""
    lexicon = LEXICONS[language]
    kept: list[str] = []
    for part in _CLAUSE_MARKS.split(text):
        words = tokens(part)
        if not words or _explains_phone(words, lexicon):
            continue
        for j in range(len(words) - 1, 1, -1):  # unpunctuated: an explanation, then the claim
            if _explains_phone(words[:j], lexicon) and not _explains_phone(words[j:], lexicon):
                words = words[j:]
                break
        kept.extend(words)
    words = tuple(kept)
    no = lexicon.no | lexicon.no_at_start
    while words and phrase_at(words, 0, no) is not None:  # "नहीं नहीं, मैं ख़ुद हूँ": "no, it is me"
        words = words[len(phrase_at(words, 0, no)) :]
    if not words or _name_possessed(words, lexicon, first_name) or points_elsewhere(" ".join(words), language):
        return False
    if closed and [word for word in _rest(words, _self_words(lexicon)) if not _is_name(word, first_name)]:
        return False
    return _explicit_self_claim(words, lexicon, first_name)


_SPEAKING_NOW = frozenset(tokens(w) for w in ("बोल रहा हूं", "बोल रही हूं", "बोल रहा", "बोल रही", "speaking"))
_NOT_A_NAME = frozenset(tokens(w) for w in ("सच", "झूठ", "सही", "गलत", "ठीक", "साफ", "सीधा", "क्या", "कुछ", "ये", "यह",
                                           "वो", "जो", "सब", "बस", "तो", "भी", "ही", "मैं", "हम", "आप", "sach", "jhooth",
                                           "jhoot", "sahi", "galat", "kya", "kuch", "sab", "bhi", "i", "im", "who", "is", "am", "are", "was",
                                           "not", "still", "you", "he", "she", "this", "it"))  # fmt: skip


def names_another_speaker(text: str, language: Language, first_name: str) -> bool:
    """After the pass (iteration 3 fix round): someone names themself as the speaker, and the name is not the
    borrower's ("मैं सुरेश बोल रहा हूँ", "Suresh here", "मेरा नाम सुरेश है", "myself Suresh"). Never an answer."""
    lexicon = LEXICONS[language]
    if not lexicon.ack_ok:
        return False
    words = tokens(text)
    closed = _self_words(lexicon) | _NOT_A_NAME

    def other(word: str) -> bool:
        return phrase_at((word,), 0, closed) is None and not _is_name(word, first_name) and not _number_word(word)

    for k, word in enumerate(words):
        if k and phrase_at(words, k, _SPEAKING_NOW) is not None and other(words[k - 1]):
            return True
        if words[k : k + 2] in (("मेरा", "नाम"), ("my", "name")) and k + 2 < len(words):
            following = words[k + 2 : k + 4]
            name = following[1] if following[:1] in (("is",),) and len(following) > 1 else following[0]
            if other(name):
                return True
        if word == "myself" and k + 1 < len(words) and other(words[k + 1]):
            return True
    return False


def speaks_of_borrower(text: str, language: Language, first_name: str) -> bool:
    """Before the loan is named (iteration 3): does the reply name the borrower with no first-person word
    ("रमेश जी नहीं हैं, फोन मत करना")? Then the speaker is talking about the borrower, not as the borrower."""
    words = tokens(text)
    return any(_is_name(word, first_name) for word in words) and not speaks_in_first_person(text, language)


def claims_self(text: str, language: Language, first_name: str, *, closed: bool = True) -> bool:
    """At the who-check after a sign of another speaker (iteration 3): an explicit first-person claim to be the
    borrower ("मैं ही बोल रहा हूँ", "हाँ, मैं ख़ुद", "मैं Ramesh", "Ramesh बोल रहा हूँ", "main hi", "speaking").

    A bare yes ("हाँ", "जी", "हाँ जी", "ठीक है") is not one: the who-check is a choice question ("you yourself, or
    someone else?"). Nothing may point elsewhere (`points_elsewhere`). With `closed` (the word lists alone)
    every word must also be explained by the closed vocabulary of `affirms_self`; `closed=False` is for a
    reply the classifier read as `confirms_self`, which still needs the explicit claim.
    """
    lexicon = LEXICONS[language]
    words = _without_leading_no(tokens(text), lexicon)
    if not words or points_elsewhere(text, language):
        return False
    if closed and [word for word in _rest(words, _self_words(lexicon)) if not _is_name(word, first_name)]:
        return False
    return _explicit_self_claim(words, lexicon, first_name)


# Iteration 3, round 2: an explicit claim with a tail. The claim is read by structure; whatever follows it (a
# question, "बताइए", "aage poochiye", a past-tense account that a relative had the phone) is open, and only a
# word that puts someone else in the speaker's place (or a hedge, or a question that reopens doubt) stops it.
_CLAIM_PARTICLES = frozenset(tokens("ही तो खुद"))
_I_FIRST = (("मैं",), ("i",), ("im",), ("i", "am"), ("this", "is"), ("its",), ("it", "is"))
# First-person frames after the borrower's name: "समीर हूँ", "रमेश ही बोल रहा हूँ", "Ramesh speaking", "Sunita here".
_NAME_FRAMES = _phrases_of("बोल रहा हूं", "बोल रही हूं", "बात कर रहा हूं", "बात कर रही हूं", "बोल रहा", "बोल रही",
                           "बात कर रहा", "बात कर रही", "हूं", "speaking", "here")  # fmt: skip
# After "बोल रहा" (no "हूँ"): a third-person or past ending ("रमेश बोल रहा है", "Ramesh bol raha tha") is no claim.
_THIRD_ENDING = frozenset(tokens("है हैं था थी थे"))
# A relation word in an account of the past ("बेटे के हाथ में फ़ोन था", "बीवी ने उठा लिया था"): these words in the
# words after it, before any first-person word, make it an account and not the speaker's own place.
_PAST_MARK = _PAST | frozenset(tokens(w) for w in ("उठा", "उठाया", "पकड़ा", "पकड़ाया", "दे दिया", "ले लिया", "ले ली"))
_PRESENT_SPEAKING = frozenset(tokens(w) for w in ("बोल रह*", "बात कर रह*", "बात करेगा", "बात करेगी", "बात करेंगे",
                                                  "है", "हैं", "हूं", "speaking", "is", "will"))  # fmt: skip
# Hand-over phrases of `Lexicon.absent` that are past ("बेटे ने फ़ोन उठाया"): allowed only inside such an account.
_PAST_HAND_OVER = _phrases_of("ने फोन", "फोन दिया", "फोन पकड़ा")
_SPOUSE = _phrases_of("बीवी", "बीबी", "biwi", "bivi", "beevi", "missus")


def _claim_form(words: Phrase, lexicon: Lexicon, first_name: str) -> bool:
    """Is there an explicit first-person claim in the words? "मैं (ही) समीर", "I am Ramesh", "मैं ही", "मैं ख़ुद", "मैं
    हूँ", "समीर (ही) बोल रहा हूँ", "Sameer hoon", "Ramesh speaking", "बोल रही हूँ", "speaking", "it's me"."""
    n = len(words)
    for k, word in enumerate(words):
        start = next((len(p) for p in sorted(_I_FIRST, key=len, reverse=True) if words[k : k + len(p)] == p), 0)
        if start:
            j = k + start
            if word == "मैं" and j < n and words[j] in ("ही", "खुद", "हूं"):
                return True
            while j < n and words[j] in _CLAIM_PARTICLES:
                j += 1
            if j < n and _is_name(words[j], first_name):
                return True
        if _is_name(word, first_name):
            j = k + 1
            while j < n and words[j] in _CLAIM_PARTICLES:
                j += 1
            frame = phrase_at(words, j, _NAME_FRAMES) if j < n else None
            if frame is not None:
                after = j + len(frame)
                if frame[-1] in ("हूं", "speaking", "here") or after >= n or words[after] not in _THIRD_ENDING:
                    return True
    return _has(words, lexicon.is_self | _phrases_of("its me", "it is me", "thats me", "मैं खुद"))


def _in_past_account(words: Phrase, after: int) -> bool:
    """Do the words from `after` on, up to the next first-person word (at most six), tell of the past and name no
    one speaking now? ("बेटे" + "के हाथ में फ़ोन था")"""
    window: list[str] = []
    for word in words[after : after + 6]:
        if word in ("मैं", "i", "im"):
            break
        window.append(word)
    part = tuple(window)
    return _has(part, _PAST_MARK) and not _has(part, _PRESENT_SPEAKING)


def _address_at(words: Phrase, k: int, phrase: Phrase, lexicon: Lexicon) -> bool:
    """Is the relation word at `k` a form of address ("हाँ भाई", "जी madam")? It is one of the address forms, with no
    possessive or "my" before it and no "हूँ" / "बोल रहा" / possessive after it."""
    if phrase not in lexicon.address:
        return False
    before = words[k - 1 : k] if k else ()
    after = k + len(phrase)
    pointing = lexicon.possessive | lexicon.my | lexicon.pointer | _POSSESSED
    if before and phrase_at(before, 0, pointing) is not None:
        return False
    return after >= len(words) or phrase_at(words, after, lexicon.relation_frame | lexicon.possessive) is None


def _someone_else_speaks(words: Phrase, lexicon: Lexicon, first_name: str) -> bool:
    """Does a reply that holds a claim also put someone else in the speaker's place, or speak of the borrower as
    another? A pointer or third-person word ("उनका", "वो", "his"), "not me", a relation or role word that is
    neither a form of address nor part of an account of the past, the first name followed by a possessive or a
    third-person ending ("रमेश का भाई", "रमेश बाहर हैं"), another name as the speaker ("मैं सुरेश हूँ"), an
    absent or wrong-number cue other than a past hand-over inside such an account."""
    if _has(words, lexicon.pointer | lexicon.third_person | lexicon.absent_frame | lexicon.not_me):
        return True
    if _name_possessed(words, lexicon, first_name):
        return True
    n = len(words)
    account = False
    relations = lexicon.kin | lexicon.relation | _CHILD | _SPOUSE | lexicon.wrong_person
    k = 0
    while k < n:
        phrase = phrase_at(words, k, relations)
        if phrase is None:
            k += 1
            continue
        nouns = lexicon.relation | _CHILD | _SPOUSE
        # "मेरी पत्नी" (a `wrong_person` phrase) is "my" + a relation: an account when the rest tells of the past.
        noun = phrase_at(phrase, 0, nouns) is not None or (
            len(phrase) > 1 and phrase_at(phrase, 0, lexicon.my) is not None and phrase_at(phrase, 1, nouns) is not None
        )
        if _address_at(words, k, phrase, lexicon):
            pass
        elif noun and _in_past_account(words, k + len(phrase)):
            account = True
        else:
            return True
        k += len(phrase)
    for k in range(n):
        cue = phrase_at(words, k, lexicon.absent)
        if cue is not None and not (account and cue in _PAST_HAND_OVER):
            return True
    for k, word in enumerate(words):
        if not _is_name(word, first_name):
            continue
        for later in words[k + 1 : k + 4]:  # "रमेश बाहर हैं", "Ramesh nahi hai": the borrower in the third person
            if later in ("हूं", "मैं", "ही", "बोल", "speaking", "here"):
                break
            if later in ("हैं", "गए", "गई", "रहे", "थे", "नहीं", "is", "isnt", "not"):
                return True
    closed = _self_words(lexicon) | _NOT_A_NAME | lexicon.address
    for k, word in enumerate(words):  # "मैं सुरेश हूँ", "main Suresh": another name straight after "I"
        if word != "मैं":
            continue
        j = k + 1
        while j < n and words[j] in _CLAIM_PARTICLES:
            j += 1
        if j >= n:
            continue
        other = words[j]
        known = phrase_at((other,), 0, closed) is not None or _is_name(other, first_name) or _number_word(other)
        if not known and (j + 1 >= n or words[j + 1] in ("हूं", "बोल", "here")):
            return True
    return False


def claim_with_tail(text: str, language: Language, first_name: str) -> bool:
    """An explicit first-person claim to be the borrower, whatever follows it (iteration 3, round 2).

    The claim ("मैं समीर हूँ", "समीर बोल रही हूँ", "main hi hoon", "मैं ख़ुद", "मैं ही बात कर रहा हूँ", "speaking")
    passes beside a question ("क्या issue है?"), a go-on word ("aage poochiye"), an address form ("भाई", "जी",
    "madam") or a past-tense account that someone else had the phone ("बीवी ने उठा लिया था"), unless the reply
    also puts someone else in the speaker's place (`_someone_else_speaks`: "मैं उनका भाई", "मैं रमेश का भाई",
    "मैं सुरेश बोल रहा हूँ", "अब मैं बोल रही हूँ, उनकी बेटी"), hedges ("शायद", "मान लीजिए", "पता नहीं"), says no
    straight after the name ("समीर नहीं"), or asks a question that reopens doubt ("आप किससे बात करना चाहते हैं?").
    Hindi and Hinglish only. A bare yes is never a claim."""
    lexicon = LEXICONS[language]
    if not lexicon.ack_ok:
        return False
    words = tokens(text)
    return bool(words) and _claim_form(words, lexicon, first_name) and not doubts_claim(text, language, first_name)


def doubts_claim(text: str, language: Language, first_name: str) -> bool:
    """Does the reply hold anything that stops a claim (`claim_with_tail`): another name as the speaker, a hedge, a
    possessive of the borrower, a no after the claim, a question about whom the caller wants or a newcomer, or
    someone else in the speaker's place? Hindi and Hinglish; elsewhere False."""
    lexicon = LEXICONS[language]
    if not lexicon.ack_ok:
        return False
    words = tokens(text)
    if names_another_speaker(text, language, first_name):
        return True
    if _has(words, _IDENTITY_HEDGE | lexicon.dont_know):
        return True
    if _POSSESSIVE_S.search(text) and any(m.group().casefold().replace("’", "'") not in _CONTRACTIONS
                                          for m in _POSSESSIVE_S.finditer(text)):  # fmt: skip
        return True
    no = lexicon.no | lexicon.no_at_start
    for k, word in enumerate(words):  # "समीर नहीं", "मैं ही नहीं": a no straight after the claim
        if (_is_name(word, first_name) or word == "मैं") and _has(words[k + 1 : k + 3], no):
            return True
    asks_for_another = _has(words, lexicon.who | lexicon.asks_who) and _has(
        words, lexicon.kin | lexicon.third_person | lexicon.absent_frame
    )
    # "आप किससे बात करना चाहते हैं?" after "मैं ही हूँ": whom the caller wants, not "who am I talking to?" ("हूँ" after it).
    asks_whom = any(
        phrase_at(words, k, _WHOM) is not None and _near(words, k, _WHOM_WANT, span=4) and "हूं" not in words[k:]
        for k in range(len(words))
    )
    if asks_for_another or asks_whom or newcomer_sign(words, lexicon, Expecting.stop_check.value):
        return True
    return _someone_else_speaks(words, lexicon, first_name)


def _signs(words: Phrase, lexicon: Lexicon) -> tuple[bool, bool]:
    """Mid-call signs that someone other than the borrower is speaking (round 4): (strong, any).

    Strong: the round 3 takeover frames (`RuleInterpreter._takeover`), and "I" beside a relation of
    someone else ("मैं उनका भाई", "main unka driver"). Weak (Hindi and Hinglish only, empty lists
    elsewhere): a relation of someone else without "I" ("unka bhai"), the speaker's own relative owning or
    doing something ("मेरे पति का लोन", "मेरे बेटे ने भरा"), "talk to me" or "now I am speaking" ("मुझसे बात
    करो", "ab main bol raha hoon"), and a restart: a greeting with a question word ("हेलो? क्या पूछ रहे थे").
    """
    strong = RuleInterpreter._takeover(words, lexicon)
    first = _has(words, lexicon.first_person)
    weak = False
    for k in range(len(words)):
        if phrase_at(words, k, lexicon.pointer) is not None and any(
            phrase_at(words, j, lexicon.relation) is not None for j in range(k + 1, min(k + 3, len(words)))
        ):
            strong, weak = strong or first, True
        relative = phrase_at(words, k + 1, lexicon.relation) if k + 1 < len(words) else None
        if relative is not None and phrase_at(words, k, lexicon.my) is not None:
            after = k + 1 + len(relative)
            after += after < len(words) and words[after] == "जी"
            weak = weak or (after < len(words) and phrase_at(words, after, lexicon.possessive | lexicon.agent) is not None)
        if words[k] in ("अब", "ab", "now") and _has(words[k + 1 : k + 3], lexicon.first_person) \
                and _has(words[k + 1 : k + 5], lexicon.speak):  # fmt: skip
            weak = True
    if _has(words, lexicon.talk_to_me) or (_has(words, lexicon.greeting) and _has(words, lexicon.what_q)):
        weak = True
    return strong, strong or weak


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
        if (expecting is Expecting.go_ahead and _has(words, _cooperative(lexicon), at_start=True)
                and _has(words, lexicon.keep_short)):  # fmt: skip
            # Wave 5: "हाँ, पर ज़्यादा लंबा मत करना": a yes whose only negative asks to keep it short. Read
            # the reply without the request; any other negative ("अभी नहीं") still reads as it did.
            short = _rest(words, lexicon.keep_short)
            intent, extra = self._intent(" ".join(short), short, lexicon, expecting, language)
        if expecting is Expecting.go_ahead and intent in _GO_AHEAD_ENDS and _has(words, _cooperative(lexicon)):
            # At the go-ahead the word lists end the call only on a reply with no yes-word and no go-on
            # word ("रुकिए मत, बोलते रहिए"): a conflicted reply is asked again, never ended.
            intent, extra = Intent.unclear, {"settled": False}
        recall = expecting in (Expecting.open, Expecting.told)
        named = recall and _names_something(text, lexicon)
        # Round 4: the stop checks and the call-back question are answered mid-call too. Iteration 3 fix round:
        # the go-ahead too, which comes after the right-party pass with no second check (the call decides
        # whether the pass happened; before it, a sign at the go-ahead changes nothing).
        mid_call = expecting not in (Expecting.identity, Expecting.birth_year)
        # Also "मम्मी, ये किसका फ़ोन है?": a who-question mid-call from someone who speaks of or to another.
        asks_for_another = _has(words, lexicon.who | lexicon.asks_who) and _has(
            words, lexicon.kin | lexicon.third_person | lexicon.absent_frame
        )
        strong, sign = _signs(words, lexicon) if mid_call else (False, False)
        newcomer = mid_call and newcomer_sign(words, lexicon, expecting.value)
        takeover = mid_call and (strong or asks_for_another or newcomer)
        sign = sign or takeover
        if takeover and intent is Intent.said:
            extra["settled"] = False
        year = loose = None
        two = False
        guessed = False
        if expecting is Expecting.birth_year and intent is not Intent.wrong_person:
            unsure = False
            if lexicon.ack_ok:  # Hindi and Hinglish only; Tamil and Kannada read as before
                text = _without_leading_no_words(_year_reply_cleaned(text), lexicon)
                text, unsure = _near_numbers(text, language)
            text = _devanagari_numbers(text)
            words = tokens(text)
            if _has(words, lexicon.months):  # a date of birth: the month and the day beside it are not years
                text = ", ".join(" ".join(_without_day_and_month(tokens(part), lexicon))
                                 for part in _CLAUSE_MARKS.split(text))  # fmt: skip
                words = tokens(text)
            heard, two = _year_in(text, words, lexicon)
            numbers = heard is not None or two or any(ch.isdigit() for ch in text) or any(
                (n := _small_number(word)) is not None and n >= 10 for word in words
            )
            # A guess uses the one attempt: a year with a hedge, a tag, an "or" or a self-correction.
            guessed = numbers and _has(words, lexicon.hedge)
            if two or guessed or unsure or _has(words, lexicon.asks_repeat):
                heard = None
            if heard is not None and self._tight_year(words, lexicon):
                year = heard
            else:
                loose = heard
        parsed = parse_amount(text)
        figure = expecting in _FIGURE
        settled = extra.pop("settled", None)
        if guessed:
            settled = True  # the guess ends the check; nothing for the classifier to judge
        elif settled is None:
            settled = self._settled(intent, expecting, year)
            if not settled and self._substance(intent, expecting, words, lexicon):
                settled = True
        approx = _approximate(text) if figure else None
        if figure and (_amount(parsed) is not None or approx is not None):
            settled = True  # a figure the bot can read back: the read-back settles the rest
        if sign and intent not in _ENDS_AT_ONCE:
            settled = False  # round 4: someone else may be speaking; only a classifier can judge a weak sign
        if expecting is Expecting.stop_check and intent is Intent.yes and _rest(words, _self_words(lexicon)):
            settled = False  # round 4: a yes with other words ("हाँ, मैं उनका बेटा, बोलो") goes to the classifier
        return Interpretation(
            intent=intent,
            amount_inr=_amount(parsed),
            bound=_amount(parsed) is not None and bool(getattr(parsed, "bound", False)),
            figures=_figures(parsed),
            approx=approx,
            only_amount=figure and _only_amount(text, parsed, lexicon),
            year=year,
            loose_year=loose,
            own_choice=expecting is Expecting.either_or and self._own_choice(words, lexicon),
            names_something=recall and named,
            names_nothing=recall and not named and _has(words, _denials(lexicon)),
            two_years=two or guessed,
            possible_takeover=takeover,
            other_speaker=sign,
            settled=settled,
            **extra,
        )

    @staticmethod
    def _settled(intent: Intent, expecting: Expecting, year: int | None) -> bool:
        if intent is Intent.silence or expecting is Expecting.callback_time:
            return True
        if expecting is Expecting.go_ahead:
            # Every reply at the go-ahead is put to the classifier when there is one, except a third party the
            # word lists found: no label may turn that into a yes (iteration 3 fix round).
            return intent is Intent.wrong_person
        if expecting is Expecting.birth_year:
            return year is not None or intent is Intent.wrong_person
        return intent not in _UNSETTLED

    @staticmethod
    def _substance(intent: Intent, expecting: Expecting, words: Phrase, lexicon: Lexicon) -> bool:
        """A free answer to a later question that speaks of the sale (round 3; `SETTLE_ON_SUBSTANCE`)."""
        later = expecting not in _NO_ACCOUNT_OF_THE_SALE and expecting is not Expecting.callback_time
        if not (SETTLE_ON_SUBSTANCE and later and intent is Intent.said and _has(words, lexicon.substance)):
            return False
        # Wave 2: no risk cue (a refusal or hand-off can mention the product too): no negation, no talk /
        # call / phone / branch / manager word, no command to the caller, no relation or third person, no
        # who/why question, no first-person future ("करूंगा", "dekh lunga").
        cues = (
            lexicon.no | lexicon.no_at_start | lexicon.nothing | lexicon.risk_cue | lexicon.kin
            | lexicon.third_person | lexicon.who | lexicon.asks_who | lexicon.wants_human | lexicon.narrative
        )  # fmt: skip
        return not (_has(words, cues) or any(word.endswith(_FUTURE) for word in words))

    @staticmethod
    def _acknowledgement(words: Phrase, lexicon: Lexicon, denies: bool) -> bool | None:
        """An ordinary confirmation: True when settled, False when not settled, None when it is not one.

        It holds an affirmative or go-on word, no denial and no third-person pronoun (the third-party,
        stop and who/repeat readings are taken before this), and at most `_ACK_EXTRA` other words. A
        language with no `ack_ok` list (Tamil, Kannada) has no ordinary confirmation.
        """
        if denies or not lexicon.ack_ok or _has(words, lexicon.third_person):
            return None
        if not _has(words, lexicon.yes | lexicon.identity_yes | lexicon.go_on):
            return None
        courtesy = (
            lexicon.yes | lexicon.identity_yes | lexicon.go_on | lexicon.self_ok | lexicon.is_self
            | lexicon.first_person | lexicon.ack_ok | lexicon.filler
        )  # fmt: skip
        extra = len(_rest(words, courtesy))
        return None if extra > _ACK_EXTRA else extra == 0

    @staticmethod
    def _tight_year(words: Phrase, lexicon: Lexicon) -> bool:
        """May the year in the reply be taken as the speaker's own?

        Hindi and Hinglish (wave 5): yes unless a word gives a reason to think the year is someone
        else's or the reply is not an answer: a third person, a relation, a wrong-person or absent cue, a
        possessive after a word that is not a number ("रमेश का 1984"), a negation, a who-question, an
        ask-to-repeat or a hedge. A deny rule, so a harmless extra word ("अरे", "और क्या") does not cost
        the attempt. Tamil and Kannada (no `ack_ok` list) keep the allow rule: the year and nothing else
        but "my", "born", "in" and the like.
        """
        if not lexicon.ack_ok:
            rest = _rest(words, lexicon.year_ok | lexicon.filler)
            return all(any(ch.isdigit() for ch in word) or _small_number(word) is not None for word in rest)
        deny = (
            lexicon.third_person | lexicon.kin | lexicon.wrong_person | lexicon.absent | lexicon.absent_frame
            | lexicon.not_me | lexicon.no | lexicon.nothing | lexicon.dont_know | lexicon.who | lexicon.asks_who
            | lexicon.asks_repeat | lexicon.hedge | lexicon.denial | _NOT_OWN_YEAR
        )  # fmt: skip
        if len(words) >= 2 and (words[-1],) in lexicon.address and _number_word(words[-2]) is not None:
            words = words[:-1]  # "उन्नीस सौ चौरासी भाई": a form of address after the year
        if _has(_without_year_vo(_without_own_office(words, lexicon), lexicon), deny) \
                or _has(words, lexicon.no_at_start, at_start=True):  # fmt: skip
            return False
        for k in range(1, len(words)):  # "रमेश का", "भैया का": a possessive after a name or relation
            if phrase_at(words, k, lexicon.possessive) is not None and _number_word(words[k - 1]) is None:
                return False
        return True

    @staticmethod
    def _own_choice(words: Phrase, lexicon: Lexicon) -> bool:
        return _has(words, lexicon.own_choice) and not _has(words, lexicon.forced)

    @staticmethod
    def _third_party(text: str, words: Phrase, lexicon: Lexicon, expecting: Expecting) -> bool:
        """Does the speaker speak of the borrower as someone else? Read before the loan is named."""
        if _has(words, lexicon.wrong_person):
            return True
        # Wave 5: at the year, a form of address straight after the year ("उन्नीस सौ चौरासी भाई") is not a
        # relation, if no other relation word or possessive is in the reply.
        year_then_address = (
            expecting is Expecting.birth_year and len(words) >= 2 and (words[-1],) in lexicon.address
            and _number_word(words[-2]) is not None and not _has(words[:-1], lexicon.kin | lexicon.possessive)
        )  # fmt: skip
        kin_words = words
        if expecting is Expecting.birth_year:
            kin_words = _without_year_vo(_without_own_office(words, lexicon), lexicon)
        # Round 4, widened in iteration 3: in a refusal, a "busy", a "later" or a "don't call" at the opening
        # ("नहीं भाई, बात नहीं करनी", "nahi bhai, interested nahi hoon", "sir abhi busy hoon"), an address form with
        # no possessive, no third-person word and no "हूं / बोल रहा / am" straight after it is address, not a
        # relation: a "हूं" later in the reply belongs to the predicate ("interested नहीं हूं").
        stops = (
            _has(words, lexicon.decline | lexicon.occupied | lexicon.call_later | lexicon.do_not_call)
            or _refuses_to_talk(words, lexicon) or first_person_refusal(words, lexicon) or asks_no_calls(words, lexicon)
            or not_free(words, lexicon) or (bool(lexicon.ack_ok) and asks_removal(words))
        )  # fmt: skip
        refusal_address = (
            stops and not speaks_of_someone_absent(words, lexicon)
            and RuleInterpreter._only_address(words, lexicon, beside_yes=False)
        )  # fmt: skip
        address = RuleInterpreter._only_address(words, lexicon) or year_then_address or refusal_address
        if _has(kin_words, lexicon.kin) and not address:
            return True
        if expecting is not Expecting.identity:
            return False
        possessive_s = any(m.group().casefold().replace("’", "'") not in _CONTRACTIONS
                           for m in _POSSESSIVE_S.finditer(text))  # fmt: skip
        return possessive_s or _has(words, lexicon.possessive)

    @staticmethod
    def _takeover(words: Phrase, lexicon: Lexicon) -> bool:
        """Someone else may have the phone: a wrong number, the borrower away or the phone theirs,
        "मैं ... नहीं हूं", or a relation word followed by "हूं" / "बोल रही" ("main unki wife hoon").
        An account that only mentions a relative or staff ("नॉमिनी मेरी पत्नी है") is none of these."""
        if _has(words, lexicon.absent):  # not `wrong_person`: mid-call "मेरी पत्नी" is an account
            return True
        first = _has(words, lexicon.first_person)
        if first and _has(words, lexicon.not_me):
            return True
        # "मैं उनका बेटा हूँ", "main dukan ka ladka hoon", "this is his brother": a possessive that points at
        # someone else, one word, then "हूं"/"am"; or "this is" / "I am" straight before his/her.
        pointing = lexicon.possessive | lexicon.kin | _phrases_of("his", "her", "their")
        for k in range(len(words)):
            if phrase_at(words, k, pointing) is None:
                continue
            if first and k + 2 < len(words) and phrase_at(words, k + 2, lexicon.relation_frame) is not None:
                return True
            if words[k] in ("his", "her") and (words[max(0, k - 2) : k] == ("this", "is") or
                                                 (k and words[k - 1] in ("am", "im"))):  # fmt: skip
                return True
        # "Unko chakkar aa gaya, main padosi hoon": "I am ..." beside the borrower as "उनको / unko".
        if first and _has(words, lexicon.relation_frame) and _has(words, lexicon.absent_frame):
            return True
        for k in range(len(words)):
            kin = phrase_at(words, k, lexicon.kin)
            after = k + len(kin) if kin else 0
            if kin and after < len(words) and phrase_at(words, after, lexicon.relation_frame) is not None:
                return True
        return False

    @staticmethod
    def _only_address(words: Phrase, lexicon: Lexicon, *, beside_yes: bool = True) -> bool:
        """Is every relation word a form of address ("हाँ भाई बोलो", "yes sir")? Beside a yes or go-on word
        (or, round 4, inside a refusal: `beside_yes=False`), with no possessive and no relation word followed
        by "हूं" / "बोल रहा" / "am"."""
        if not lexicon.address or (beside_yes and not _has(words, lexicon.yes | lexicon.go_on | lexicon.is_self)):
            return False
        if _has(words, lexicon.possessive) or _POSSESSIVE_S.search(" ".join(words)):
            return False
        for k in range(len(words)):
            kin = phrase_at(words, k, lexicon.kin)
            if kin is None:
                continue
            if phrase_at(words, k, lexicon.address) != kin:
                return False
            after = k + len(kin)
            if after < len(words) and phrase_at(words, after, lexicon.relation_frame) is not None:
                return False
        return True

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
        busy = _has(words, lexicon.occupied) or (expecting in _NO_ACCOUNT_OF_THE_SALE and not_free(words, lexicon))
        goes_on = _has(words, lexicon.go_on | lexicon.hurry)
        if busy and expecting in _OPENING and not _has(words, lexicon.first_person) and not goes_on:
            return Intent.wrong_person, {}  # "साहब मीटिंग में हैं": busy, but someone else is
        refuses = _has(words, lexicon.decline) or _refuses_to_talk(words, lexicon) or (
            expecting in _NO_ACCOUNT_OF_THE_SALE and first_person_refusal(words, lexicon)
        )
        if busy and _has(words, lexicon.hurry) and not (later or refuses):
            busy = False  # "थोड़ा बिज़ी हूँ, जल्दी बोलिए": busy, and still says go on
        human = _has(words, lexicon.wants_human)
        short = len(words) <= _STOP_TURN and _has(words, lexicon.decline_short)
        dnc = _has(words, lexicon.do_not_call) or asks_no_calls(words, lexicon) or (
            bool(lexicon.ack_ok) and asks_removal(words)
        )
        written = _has(words, lexicon.written)
        if not (human or refuses or later or busy or short or dnc or written):
            return None
        if narrated:
            return Intent.said, {"settled": False}
        if _has(words, lexicon.go_on | lexicon.hurry) and (human or refuses or later or busy or dnc or written):
            # "बंद मत कीजिए, बोलिए", "अभी बिज़ी था, अब बोलो": a stop word beside a go-on word. Conflicted: the
            # classifier judges; without one the call asks once and never ends on it.
            if expecting in _NO_ACCOUNT_OF_THE_SALE:
                return Intent.unclear, {"settled": False}
            return (Intent.maybe_human if human else Intent.maybe_decline), {"settled": False}
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
        ends = (Intent.decline, Intent.do_not_call, Intent.call_later)
        if stop is not None and expecting in _OPENING and stop[0] in ends and speaks_of_someone_absent(words, lexicon):
            # Round 4, widened in iteration 3: "वो नहीं हैं, बात नहीं हो सकती", "रमेश जी नहीं हैं, बाद में भी मत करना
            # फोन": about someone who is away. Never logged as the borrower refusing.
            return Intent.wrong_person, {}
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
            asking = _rest(words, lexicon.who | lexicon.asks_who)
            if asking != words and asking and not denies:
                # "हाँ, मैं ही रमेश हूँ। आप कौन?": the confirmation wins; the next lines answer the question
                if self._claims_to_be_the_borrower(asking, lexicon):
                    return Intent.yes, {"settled": True}
                ack = self._acknowledgement(asking, lexicon, denies)
                if ack is not None:
                    return Intent.acknowledges, {"settled": ack}
            if _has(words, lexicon.who) or _has(words, lexicon.asks_who):
                return Intent.asks_who, {"settled": len(words) <= 4}
            if repeats and (short and _has(words, lexicon.asks_repeat) or not _has(words, lexicon.yes | lexicon.identity_yes | lexicon.go_on)):
                return Intent.asks_repeat, {"settled": len(words) <= 4}
            ack = self._acknowledgement(words, lexicon, denies)
            if ack is not None:
                return Intent.acknowledges, {"settled": ack}
            if _only(words, lexicon.identity_yes | lexicon.self_ok | lexicon.filler):
                # "हेलो", "नमस्ते": a greeting, not a confirmation
                return Intent.said, {"settled": True}
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
        if expecting is Expecting.go_ahead:  # only yes-words or only no-words: no classifier needed
            if denies and _has(words, lexicon.go_on | lexicon.hurry):
                return Intent.unclear, {"settled": False}  # "नहीं नहीं, बोलिए": conflicted, asked once
            if denies:
                return Intent.no, {"settled": _only(words, lexicon.no | lexicon.no_at_start | lexicon.filler)}
            if affirms:
                return Intent.yes, {"settled": _only(words, lexicon.yes | lexicon.filler)}
        if expecting in (Expecting.confirmation, Expecting.stop_check):
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
