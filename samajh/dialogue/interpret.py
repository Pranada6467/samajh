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
    ROMAN_NUMBERS,
    Lexicon,
    Phrase,
    found,
    phrase_at,
    roman_key,
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


def _year_reply_cleaned(text: str) -> str:
    """The birth-year reply without a leading yes-"ya", with numeric dates as their year and no "तारीख" day."""
    first = tokens(text)[:1]
    if first and first[0] in ("ya", "yaa", "yeah", "yah"):
        text = _LEADING_YES.sub("", text, count=1)
    text = _NUMERIC_DATE.sub(lambda m: m.group(1), text.translate(_DIGITS))
    if any(word in _TARIKH for word in tokens(text)):
        text = ", ".join(" ".join(_without_tarikh_day(tokens(part))) for part in _CLAUSE_MARKS.split(text))
    return text


def _devanagari_numbers(text: str) -> str:
    """Romanised Hindi number words in Devanagari ("unnees sau chaurasi" -> "उन्नीस सौ चौरासी"), so the year
    is read the same in either script (wave 4). Other words are left as they are."""
    return _LATIN_WORD.sub(lambda m: ROMAN_NUMBERS.get(roman_key(m.group()), m.group()), text)


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


def means_now(text: str, language: Language) -> bool:
    """At "when shall we call?": does the reply mean now ("अभी बोलिए", "now is fine"), naming no later time
    and holding no no-word ("अभी नहीं")?"""
    words, lexicon = tokens(text), LEXICONS[language]
    if not _has(words, lexicon.now_words):
        return False
    if _has(words, lexicon.go_on | lexicon.hurry | lexicon.do_now):
        return True  # "नहीं, अभी ठीक है, आगे बढ़िए": now and go on wins over any no-word or later time
    later = lexicon.time_words | lexicon.call_later | lexicon.no | lexicon.no_at_start | lexicon.decline
    return not _has(words, later)


def affirms_or_goes_on(text: str, language: Language) -> bool:
    """Does the reply hold a yes-word or a go-on word ("हाँ", "बोलिए", "pucho")?"""
    lexicon = LEXICONS[language]
    return _has(tokens(text), lexicon.yes | lexicon.identity_yes | lexicon.go_on | lexicon.hurry)


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
        mid_call = expecting not in _NO_ACCOUNT_OF_THE_SALE
        # Also "मम्मी, ये किसका फ़ोन है?": a who-question mid-call from someone who speaks of or to another.
        asks_for_another = _has(words, lexicon.who | lexicon.asks_who) and _has(
            words, lexicon.kin | lexicon.third_person | lexicon.absent_frame
        )
        takeover = mid_call and (self._takeover(words, lexicon) or asks_for_another)
        if takeover and intent is Intent.said:
            extra["settled"] = False
        year = loose = None
        two = False
        guessed = False
        if expecting is Expecting.birth_year and intent is not Intent.wrong_person:
            if lexicon.ack_ok:  # Hindi and Hinglish only; Tamil and Kannada read as before
                text = _year_reply_cleaned(text)
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
            if two or guessed or _has(words, lexicon.asks_repeat):
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
        return Interpretation(
            intent=intent,
            amount_inr=_amount(parsed),
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
        if _has(_without_own_office(words, lexicon), deny) or _has(words, lexicon.no_at_start, at_start=True):
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
        kin_words = _without_own_office(words, lexicon) if expecting is Expecting.birth_year else words
        if _has(kin_words, lexicon.kin) and not (RuleInterpreter._only_address(words, lexicon) or year_then_address):
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
    def _only_address(words: Phrase, lexicon: Lexicon) -> bool:
        """Is every relation word a form of address ("हाँ भाई बोलो", "yes sir")? Only beside a yes or go-on
        word, with no possessive and no relation word followed by "हूं" / "बोल रहा" / "am"."""
        if not lexicon.address or not _has(words, lexicon.yes | lexicon.go_on | lexicon.is_self):
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
        busy = _has(words, lexicon.occupied)
        goes_on = _has(words, lexicon.go_on | lexicon.hurry)
        if busy and expecting in _OPENING and not _has(words, lexicon.first_person) and not goes_on:
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
