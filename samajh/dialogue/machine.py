"""The Samajh call as a state machine (DESIGN.md section 5). Pure: no audio, no network, no clock.

    start(record, language, lender_name=...) -> (CallState, BotUtterance)
    step(state, customer_text)                -> (CallState, BotUtterance | EndOfCall)

`CallState.position` says which reply the bot is waiting for; the interpreter turns the reply into
an `Intent` (the event); `step` maps (position, intent) to the next position and the next lines.

The state holds a `CallPlan`, not the loan record: the first name, the birth year for the second
check, and the product ids. Nothing else from the record survives `start`, so no line the bot
speaks can depend on a value the call is testing. Every branch depends on what the customer said.
The only figures the bot ever says are ones the customer said first.

Call v2 (iteration 2):
- The opening is four short lines after a first-person yes; the other disclosures are said where
  they are needed (no OTP with the birth-year question, the right to stop with the loan, how to
  check the call on request and at the close).
- A refusal, a request for a person or for a later call ends the call politely; a weak signal gets
  one "shall we go on?". "Who is this?" gets a short answer and the question again.
- A customer who took nothing gets one follow-up and the consent question.
- The premium is read back straight after it is said. With two readings that disagree, the bot asks
  for the amount once more before it reads anything back.

Every position allows one re-ask at most, read-backs per product are capped, silence twice ends the
call, and the whole call is capped at `Limits.max_bot_turns`, so a call always ends.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from samajh.amounts import spoken_amount
from samajh.dialogue._lexicon import OWN_LANGUAGES
from samajh.dialogue.halves import consent_halves, kind_is_half
from samajh.dialogue.interpret import (
    UNCLEAR,
    Expecting,
    Intent,
    Interpretation,
    RuleInterpreter,
    TurnContext,
    TurnInterpreter,
    affirms_or_goes_on,
    asks_something,
    claim_with_tail,
    claims_another_name,
    claims_self,
    doubts_claim,
    hedges_claim,
    hedges_or_asks,
    means_now,
    name_hints,
    names_another_speaker,
    only_asks_whom,
    points_elsewhere,
    short_delay_or_echo,
    speaks_of_borrower,
    starts_with_yes,
    third_party_sign,
    who_check_claim,
)
from samajh.dialogue.prompts import LINES, PRODUCT_QUESTIONS, load_prompts
from samajh.identity import CheckKind, IdentityPolicy, IdentityRecord, expected_answer, identity_sentence
from samajh.rules.halves import missing_half
from samajh.types import (
    CallStep,
    Frozen,
    Language,
    LoanRecord,
    ProductId,
    Question,
    Speaker,
    Transcript,
    Turn,
    TurnId,
)


class Outcome(StrEnum):
    """How a call ended."""

    completed = "completed"
    wrong_party = "wrong_party"  # the person who answered is not the borrower
    not_confirmed = "not_confirmed"  # nobody claimed to be the borrower
    no_go_ahead = "no_go_ahead"  # no clear yes after the disclosure
    second_check_failed = "second_check_failed"
    declined = "declined"
    human_requested = "human_requested"
    turn_limit = "turn_limit"
    call_back_later = "call_back_later"  # the customer asked to be called another time
    language_switch = "language_switch"  # the customer asked for another language; no live switch
    no_response = "no_response"  # nothing heard `Limits.max_silences` times in a row
    do_not_call = "do_not_call"  # the customer asked not to be called again / to remove the number
    written_requested = "written_requested"  # the customer asked for this in writing instead


class Limits(Frozen):
    max_bot_turns: int = Field(default=60, ge=1)  # utterances, including the closing one
    max_read_backs: int = Field(default=3, ge=1)  # read-backs of one product's premium
    max_stop_checks: int = Field(default=2, ge=0)  # times a call asks "shall we go on?"
    max_silences: int = Field(default=2, ge=1)  # consecutive silent turns before the call ends
    max_side_answers: int = Field(default=2, ge=0)  # "who is this?" answers before it counts as unclear
    # Round 4: "is it you speaking?" checks after a sign of another speaker. Its own count, not
    # `max_stop_checks`: a borrower who used the "shall I go on?" checks still gets one, and the reverse.
    max_who_checks: int = Field(default=2, ge=0)
    # W4: live switches to another prompt language; a request past this ends the call (`end.language`).
    max_language_switches: int = Field(default=2, ge=0)


class LanguageSwitch(Frozen):
    """W4: the call went on in another language from this customer turn on."""

    turn_id: TurnId
    from_language: Language
    to_language: Language
    requested: str  # the English lower-case name the customer asked for


class CallPlan(Frozen):
    """All the call keeps of the loan record."""

    loan_id: str
    first_name: str
    # The expected answer of the year-of-birth check (`samajh.identity.expected_answer`); None when the
    # policy has no second check, so the call keeps nothing of the record it does not use.
    birth_year: int | None = None
    product_ids: tuple[ProductId, ...]


class Line(Frozen):
    """One sentence group the bot speaks. `key` and `slots` identify the template, for pre-made audio."""

    key: str
    slots: dict[str, str]
    text: str
    step: CallStep
    asks: Question | None = None
    product_id: ProductId | None = None


class BotUtterance(Frozen):
    """What the bot says before it listens again. The last line is the one the customer answers."""

    language: Language
    lines: tuple[Line, ...]

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)


# --- positions: the reply the bot is waiting for -----------------------------


class AtIdentity(Frozen):
    """The name question (`right_party.ask`), or its re-ask (`right_party.reask`: "are you <name> yourself?").

    With no second check (P8) the re-ask is also the direct question asked after a yes to the name."""

    at: Literal["identity"] = "identity"
    reasked: bool = False


class AtGoAhead(Frozen):
    at: Literal["go_ahead"] = "go_ahead"
    reasked: bool = False
    # The right-party check has passed (round 3: the birth year; P8 with no second check: the direct
    # question), so a yes goes on to the loan. The name is kept for saved states.
    year_passed: bool = False


class AtBirthYear(Frozen):
    at: Literal["birth_year"] = "birth_year"
    reasked: bool = False
    # The ordinary path (round 3): asked straight after an acknowledgement, before the lender is named.
    # Until the year passes nothing may name the lender, the loan or a product.
    early: bool = False
    # P8, two attempts: a wrong year used the first attempt and the year is asked once more
    # (`second_check.reask`). Separate from `reasked`, the single re-ask for a reply with no year.
    retry: bool = False


class AtRecall(Frozen):
    at: Literal["recall"] = "recall"
    reasked: bool = False


class AtRecallFollowUp(Frozen):
    """The customer said they took nothing (or could not say): one neutral follow-up, never re-asked."""

    at: Literal["recall_follow_up"] = "recall_follow_up"


class AtTeachBack(Frozen):
    at: Literal["teach_back"] = "teach_back"
    product: int  # index into CallPlan.product_ids
    question: Question
    reasked: bool = False
    follow: bool = False  # W4: the one follow-up for a half answer to the kind question ("what is it called?")


class AtSayAgain(Frozen):
    """The two readings of an amount answer differed: the bot asked for the amount once more."""

    at: Literal["say_again"] = "say_again"
    product: int
    item: Literal["premium", "cover"] = "premium"


class AtConsent(Frozen):
    at: Literal["consent"] = "consent"
    reasked: bool = False
    follow: Literal["what", "how"] | None = None  # W4: the one follow-up asking only for the missing half


class AtReadBack(Frozen):
    """The bot read the customer's figure back and waits for yes, no, or another figure.

    `low` is set for an amount said as "about X" or "X to Y": the line said `low` to `amount_inr`.
    `item` is the figure read back: the premium, or the cover amount when the customer stated one.
    """

    at: Literal["read_back"] = "read_back"
    product: int
    amount_inr: int
    read_backs: int  # read-backs of this item so far, this one included
    low: int | None = None
    item: Literal["premium", "cover"] = "premium"


class AtRestate(Frozen):
    """The customer rejected a read-back without giving a figure; the bot asked for the right one."""

    at: Literal["restate"] = "restate"
    product: int
    read_backs: int
    rejected_inr: int | None = None  # the figure the customer said was wrong
    item: Literal["premium", "cover"] = "premium"


class AtCallbackTime(Frozen):
    """The customer asked for a later call without saying when; the bot asked when."""

    at: Literal["callback_time"] = "callback_time"
    # Wave 2: the question that was pending, so a reply meaning "now" goes back to it. None in states
    # saved before; such a call ends as a call-back, as before.
    resume: Annotated[_Waiting, Field(discriminator="at")] | None = None


class Ended(Frozen):
    at: Literal["ended"] = "ended"
    outcome: Outcome


_Question = AtRecall | AtTeachBack | AtConsent
_Waiting = (
    AtIdentity | AtGoAhead | AtBirthYear | AtRecall | AtRecallFollowUp | AtTeachBack | AtSayAgain | AtConsent
    | AtReadBack | AtRestate | AtCallbackTime
)  # fmt: skip
AtCallbackTime.model_rebuild()


class AtStopCheck(Frozen):
    """A reply may have meant "stop" or "get me a person"; the bot asked, and goes back to `resume`.

    Only a weak signal comes here (a short "leave it", a refusal the customer may be quoting, or an
    LLM's guess). A plain refusal or a plain request for a human ends the call at once.
    """

    at: Literal["stop_check"] = "stop_check"
    # "decline": "shall I go on?"; "human": "shall a person call you?"; "disengaged": "shall I ask on, or
    # stop here?", after two unusable replies or three "I don't know"s in a row.
    # "who" (wave 2): someone else may have the phone and nobody judged it; `right_party.reask` asks who
    # is speaking, naming neither the lender nor the loan.
    wish: Literal["decline", "human", "disengaged", "who"]
    resume: Annotated[_Waiting, Field(discriminator="at")]
    then: Intent = Intent.asks_repeat  # what the pending question is taken to have heard, on going on
    # Iteration 3 fix round: on going on, put `resume`'s question as new (the who-check came before a line that
    # would have named the lender, the loan or a figure, not after an answer to it). False in older states.
    fresh: bool = False


Position = Annotated[_Waiting | AtStopCheck | Ended, Field(discriminator="at")]


class StatedPremium(Frozen):
    product_id: ProductId
    amount_inr: int  # the customer's latest figure, never the record's; the top of a range
    low: int | None = None  # set when the customer said "about X" or "X to Y"


class Unresolved(Frozen):
    """A question the call moved past without a usable answer. The case needs a human."""

    step: CallStep
    asks: Question | None = None
    product_id: ProductId | None = None


class CarriedAnswer(Frozen):
    """An answer given in open recall that the call did not ask for again ("बावन हज़ार का" -> the premium)."""

    product_id: ProductId
    question: Question
    turn_id: TurnId  # the customer's recall turn that holds it


class SecondReading(Frozen):
    """The other transcript of a customer turn that was read twice. `Turn.text` is the one the call acted on."""

    turn_id: TurnId
    text: str
    agreed: bool  # both transcripts gave the same figure


class CallState(Frozen):
    """Everything needed to continue a call. Serialise with `model_dump_json`, restore with `model_validate_json`."""

    call_id: str
    language: Language
    lender_name: str
    plan: CallPlan
    limits: Limits
    position: Position
    turns: tuple[Turn, ...] = ()
    bot_turns: int = 0
    premiums: tuple[StatedPremium, ...] = ()
    unresolved: tuple[Unresolved, ...] = ()
    stop_checks: int = 0  # times the bot has asked "shall we go on?"
    second_readings: tuple[SecondReading, ...] = ()
    silences: int = 0  # silent turns in a row
    side_answers: int = 0  # times the bot answered "who is this?"
    said_again: tuple[ProductId, ...] = ()  # products whose premium the bot asked for a second time
    own_choice: tuple[ProductId, ...] = ()  # products the customer said were their own choice
    callback_time: str | None = None  # the customer's own words for when to call; never parsed
    requested_language: str | None = None  # English name in lower case, as asked for
    language_switches: tuple[LanguageSwitch, ...] = ()  # W4: live switches, in order
    follow_ups: tuple[str, ...] = ()  # W4: slots that had their one follow-up ("consent", "kind:P1")
    deferrals: tuple[str, ...] = ()  # W4: slots that had their one re-ask after a deferral ("आप records में देख लीजिए")
    puts: tuple[tuple[str, int], ...] = ()  # W4: times each question slot was put, for the loop cap
    degraded_turns: tuple[TurnId, ...] = ()  # customer turns the classifier failed on
    degraded_checked: bool = False  # the call has asked "shall I go on?" after a failed classifier
    unusable_run: int = 0  # unusable replies in a row
    dont_know_run: int = 0  # "I don't know" replies in a row
    disengage_checked: bool = False
    recall_figure: tuple[int, TurnId] | None = None  # a single figure the customer gave in open recall
    carried_forward: tuple[CarriedAnswer, ...] = ()
    said_again_cover: tuple[ProductId, ...] = ()
    speaker_confirmed: bool = False  # True once the birth year has passed (either path)
    who_checks: int = 0  # round 4: times the bot has asked who is speaking after the opening
    # Round 4: a turn showed a sign of another speaker that a classifier label let pass, and no who-check
    # has passed since: a later turn nobody can judge gets the who-check.
    speaker_doubt: bool = False
    # P8: the right-party check in force. A state saved before P8 has no such field and loads with the
    # check it ran then, the year of birth with one attempt; `start` always sets it (default: no check).
    identity: IdentityPolicy = Field(
        default_factory=lambda: IdentityPolicy(second_check=CheckKind.year_of_birth, attempts=1)
    )
    check_attempts: int = 0  # P8: answers the second check judged (a wrong year, a guess, the right year)
    # P8: True once the right-party check passed, False when the call ended at the opening because the
    # speaker was not accepted, None before either (and in states saved before P8).
    check_passed: bool | None = None
    # P8 (product review gain 8): the open-recall reply named something, so the kind question refers to it.
    recall_named: bool = False
    # Iteration 3, round 2: the go-ahead was asked again once because the reply only echoed the bot's time phrase
    # or named a short delay ("15 minute baad", "थोड़ी देर"); a second such reply is read as before.
    delay_reasked: bool = False

    def transcript(self) -> Transcript:
        """The call so far, in the shape the extractor and the rules consume."""
        return Transcript(
            call_id=self.call_id, loan_id=self.plan.loan_id, language=self.language, turns=self.turns
        )

    def premium_of(self, product: int) -> int | None:
        wanted = self.plan.product_ids[product]
        return next((p.amount_inr for p in self.premiums if p.product_id == wanted), None)


class EndOfCall(Frozen):
    """The bot's last words and the finished call."""

    utterance: BotUtterance
    outcome: Outcome
    transcript: Transcript
    unresolved: tuple[Unresolved, ...]
    callback_time: str | None = None
    requested_language: str | None = None
    language_switches: tuple[LanguageSwitch, ...] = ()
    degraded_turns: tuple[TurnId, ...] = ()
    carried_forward: tuple[CarriedAnswer, ...] = ()
    speaker_confirmed: bool = False  # the birth year passed before the call ended; never on `wrong_party`


log = logging.getLogger(__name__)

_RULES = RuleInterpreter()

_TOLD = frozenset({Question.provider_choice, Question.cancel_window})
_EITHER_OR = frozenset({Question.required_for_loan, Question.payment_frequency})
_FIGURE = frozenset({Expecting.amount, Expecting.confirmation})  # replies that may carry a rupee figure
_BEFORE_LOAN = (AtIdentity, AtGoAhead, AtBirthYear)
# P8: outcomes that mean the speaker was not accepted as the borrower.
_NOT_ACCEPTED = frozenset({Outcome.wrong_party, Outcome.not_confirmed, Outcome.second_check_failed})
_END_LINES: dict[Outcome, tuple[str, ...]] = {
    Outcome.wrong_party: ("end.third_party",),
    Outcome.not_confirmed: ("end.third_party",),
    Outcome.no_go_ahead: ("end.neutral",),
    Outcome.second_check_failed: ("end.check_failed",),
    Outcome.declined: ("end.declined",),
    Outcome.human_requested: ("end.human",),
    Outcome.turn_limit: ("close.thanks", "close.may_call_back", "close.bye"),
    Outcome.call_back_later: ("end.call_back",),
    Outcome.language_switch: ("end.language",),
    Outcome.no_response: ("end.no_response",),
    Outcome.do_not_call: ("end.do_not_call",),
    Outcome.written_requested: ("end.written",),
}


def expecting(position: Position) -> Expecting:
    """The kind of reply a position waits for."""
    match position:
        case AtIdentity():
            return Expecting.identity
        case AtGoAhead():
            return Expecting.go_ahead
        case AtBirthYear():
            return Expecting.birth_year
        case AtTeachBack(question=Question.premium | Question.cover) | AtSayAgain() | AtRestate():
            return Expecting.amount
        case AtTeachBack(question=question) if question in _EITHER_OR:
            return Expecting.either_or
        case AtTeachBack(question=question) if question in _TOLD:
            return Expecting.told
        case AtRecallFollowUp():
            return Expecting.told
        case AtRecall() | AtTeachBack() | AtConsent():
            return Expecting.open
        case AtReadBack():
            return Expecting.confirmation
        case AtStopCheck():
            return Expecting.stop_check
        case AtCallbackTime():
            return Expecting.callback_time
        case Ended():
            raise ValueError("the call has ended")


# --- building what the bot says ----------------------------------------------


def cover_read_back_question() -> Question:
    """The `Question` a cover read-back line is tagged with. [pending P3a] The core package is adding a
    value for it; until its name is in references/pilots/P3a-contract.md, the line is tagged `cover`
    and told apart from the cover question by `step=read_back`, as the premium read-back is."""
    return Question.cover


def _item_question(item: str) -> Question:
    return cover_read_back_question() if item == "cover" else Question.premium


def _line(
    state: CallState,
    key: str,
    *,
    product: int | None = None,
    step: CallStep | None = None,
    asks: Question | None = None,
    **slots: str,
) -> Line:
    spec = LINES[key]
    wanted = {"first_name": state.plan.first_name, "lender": state.lender_name} | slots
    filled = {name: wanted[name] for name in spec.slots}
    asks = asks or spec.asks
    asks_product = asks is not None and asks is not Question.consent
    return Line(
        key=key,
        slots=filled,
        text=load_prompts(state.language).render(key, **filled),
        step=step or spec.step,
        asks=asks,
        product_id=state.plan.product_ids[product] if asks_product and product is not None else None,
    )


def _read_back_line(state: CallState, position: AtReadBack, *, again: bool) -> Line:
    amount, low = position.amount_inr, position.low
    asks = _item_question(position.item)
    if low is None:
        said = {"amount_words": spoken_amount(amount, state.language)}
        first = "read_back.cover_confirm" if position.item == "cover" else "read_back.confirm"
        return _line(
            state, "read_back.reconfirm" if again else first, product=position.product, asks=asks, **said
        )
    pack = load_prompts(state.language)
    words = spoken_amount(amount, state.language)
    if low != amount:
        words = f"{spoken_amount(low, state.language)} {pack.range_word} {words}"
    return _line(state, "read_back.confirm_about", product=position.product, amount_words=words)


def _lines_for(state: CallState, position: Position, *, again: bool = False) -> tuple[Line, ...]:
    """The lines that put `position`'s question. `again` marks a read-back repeated after an unclear reply."""
    match position:
        case AtIdentity(reasked=reasked):
            return (_line(state, "right_party.reask" if reasked else "right_party.ask"),)
        case AtGoAhead(reasked=True):
            return (_line(state, "disclosure.reask"),)
        case AtGoAhead() if state.identity.second_check is None:
            # P8, no second check: the never-ask line (said with the year question when there is one) and the
            # call-back line come with the disclosure, after the right-party check has passed.
            keys = ("who", "not_sales", "recording", "never_ask", *_call_back_line(state), "go_ahead")
            return tuple(_line(state, key if "." in key else f"disclosure.{key}", step=CallStep.disclosure)
                         for key in keys)  # fmt: skip
        case AtGoAhead():
            return tuple(
                _line(state, f"disclosure.{key}") for key in ("who", "not_sales", "recording", "go_ahead")
            )
        case AtBirthYear(reasked=True) | AtBirthYear(retry=True):
            return (_line(state, "second_check.reask"),)
        case AtBirthYear(early=True):
            said = {turn.text for turn in state.turns if turn.speaker is Speaker.bot}
            purpose = () if said & {_line(state, k).text for k in ("purpose.before_confirm", "right_party.reask")} \
                else (_line(state, "purpose.before_confirm", step=CallStep.second_check),)  # fmt: skip
            return (
                *purpose,
                _line(state, "disclosure.never_ask", step=CallStep.second_check),
                _line(state, "second_check.ask"),
            )
        case AtBirthYear():
            return (
                _line(state, "disclosure.never_ask", step=CallStep.second_check),
                *(_line(state, key, step=CallStep.second_check) for key in _call_back_line(state)),
                _line(state, "second_check.ask"),
            )
        case AtRecall(reasked=True):
            return (_line(state, "open_recall.reask"),)
        case AtRecall():
            return (
                _line(state, "context.loan"),
                _line(state, "disclosure.rights", step=CallStep.context),
                _line(state, "open_recall.ask"),
            )
        case AtRecallFollowUp():
            return (_line(state, "open_recall.nothing"),)
        case AtTeachBack(product=product, follow=True):
            return (_line(state, "kind.follow_what", product=product),)
        case AtConsent(follow="what" | "how" as half):
            return (_line(state, f"consent.follow_{half}"),)
        case AtTeachBack(product=product, question=question, reasked=reasked):
            named = question is Question.kind and not reasked and product == 0 and state.recall_named
            key = "kind.ask_named" if named else f"{question.value}.{'reask' if reasked else 'ask'}"
            ask = _line(state, key, product=product)
            if question is not PRODUCT_QUESTIONS[0] or reasked:
                return (*_ack(state, position), ask)
            if product > 0:  # the first product is introduced as in a one-product record
                ordinal = load_prompts(state.language).ordinal(product)
                return (_line(state, "teach_back.intro_nth", ordinal=ordinal), ask)
            return (_line(state, "teach_back.intro"), ask)
        case AtSayAgain(product=product, item=item):
            return (_line(state, f"{item}.say_again", product=product),)
        case AtConsent(reasked=reasked):
            return (_line(state, "consent.reask" if reasked else "consent.ask"),)
        case AtReadBack():
            return (_read_back_line(state, position, again=again),)
        case AtRestate(product=product, item=item):
            return (_line(state, "read_back.restate", product=product, asks=_item_question(item)),)
        case AtCallbackTime():
            return (_line(state, "callback.when"),)
        case AtStopCheck(wish="who", resume=resume):
            # Iteration 3: a choice question ("you yourself, or someone else in their place?"), asked only after
            # a sign of another speaker; a bare yes does not answer it (`_on_who_check`).
            return (_line(state, "right_party.who_check", step=_unresolved_at(state, resume).step),)
        case AtStopCheck(wish=wish, resume=resume):
            return (_line(state, f"stop_check.{wish}", step=_unresolved_at(state, resume).step),)
        case Ended():
            raise ValueError("the call has ended")


def _call_back_line(state: CallState) -> tuple[str, ...]:
    """`verify.short` ("if in doubt, hang up and ask customer care yourself"), unless the lender turned it off."""
    return ("verify.short",) if state.identity.call_back_line else ()


# Languages with the neutral acknowledgement (product review gain 8): Hindi and Hinglish only.
_ACK_LANGUAGES = frozenset({Language.hi, Language.hi_en})


def _ack(state: CallState, position: AtTeachBack) -> tuple[Line, ...]:
    """`ack.neutral` ("जी।") before every second teach-back question: chosen by the question's place in
    `PRODUCT_QUESTIONS` alone, never by what the customer said. Never on a re-ask; `_say` drops it before a
    bridge or a verification answer, and it is never put before a stop check, a who-check, a read-back or
    an end, which are other positions."""
    odd = PRODUCT_QUESTIONS.index(position.question) % 2 == 1
    if state.language in _ACK_LANGUAGES and odd and not position.reasked:
        return (_line(state, "ack.neutral", product=position.product),)
    return ()


_MAX_PUTS = 2
_SIDE_ANSWERS = ("verify.", "purpose.")


def _capped_slot(position: Position) -> str | None:
    """W4: the slot a question position puts, for the loop cap; None for the opening, read-backs (bounded by
    `Limits.max_read_backs`) and the stop checks."""
    match position:
        case AtTeachBack(product=product, question=question):
            return f"{question.value}:{product}"
        case AtConsent():
            return "consent"
        case AtRecall():
            return "recall"
        case _:
            return None


def _say(
    state: CallState,
    position: Position,
    *,
    bridge: bool = False,
    again: bool = False,
    before: tuple[str, ...] = (),
    lead: tuple[str, ...] = (),
) -> tuple[CallState, BotUtterance | EndOfCall]:
    """Move to `position` and put its question, or end the call when the turn budget is spent.

    `before` names lines said first (a verification answer); then only the question line follows.
    """
    if state.bot_turns + 1 >= state.limits.max_bot_turns:
        return _end(state, Outcome.turn_limit)
    state, position = _carry_forward(state, position)
    slot = _capped_slot(position)
    if slot is not None and not any(key.startswith(_SIDE_ANSWERS) for key in before):
        # W4: a question is put at most `_MAX_PUTS` times by any path (re-ask, deferral, call-back-time or stop-check
        # return); past that the slot is left unresolved and the call moves on. "Who is this?" answers do not count.
        counts = dict(state.puts)
        counts[slot] = counts.get(slot, 0) + 1
        state = state.model_copy(update={"puts": tuple(counts.items())})
        if counts[slot] > _MAX_PUTS:
            return _go(_mark_unresolved(state, position), _after(state, position), bridge=True)
    lines = _lines_for(state, position, again=again)
    if before:
        lines = (*(_line(state, key, step=lines[-1].step) for key in before), lines[-1])
    if lead:  # W4: said before the position's own lines, all of them
        lines = (*(_line(state, key, step=lines[0].step) for key in lead), *lines)
    if bridge:
        lines = tuple(line for line in lines if line.key != "ack.neutral")
        lines = (_line(state, "bridge.moving_on", step=lines[0].step), *lines)
    if state.speaker_doubt and _watching(state, position) and any(_names_something(line) for line in lines):
        # Iteration 3 fix round: while a sign of another speaker is unsettled, no line that names the lender, the
        # loan or a figure plays; the who-check comes first and, once it passes, this question is put as new.
        return _who_check(state, position, fresh=True)
    return _speak(state.model_copy(update={"position": position}), lines)


def _speak(state: CallState, lines: tuple[Line, ...]) -> tuple[CallState, BotUtterance]:
    next_id = len(state.turns) + 1
    turns = tuple(
        Turn(id=TurnId(next_id + k), speaker=Speaker.bot, step=line.step, text=line.text, asks=line.asks,
             product_id=line.product_id)
        for k, line in enumerate(lines)
    )  # fmt: skip
    state = state.model_copy(update={"turns": state.turns + turns, "bot_turns": state.bot_turns + 1})
    return state, BotUtterance(language=state.language, lines=lines)


def _end(
    state: CallState, outcome: Outcome, *, keys: tuple[str, ...] | None = None
) -> tuple[CallState, EndOfCall]:
    if keys is None and outcome is Outcome.completed:
        middle = ("close.may_call_back",) if state.unresolved else ()
        keys = ("close.thanks", *middle, "close.verify", "close.bye")
    elif keys is None:
        keys = _END_LINES[outcome]
    update: dict = {"position": Ended(outcome=outcome)}
    if state.check_passed is None and outcome in _NOT_ACCEPTED:  # P8: ended at the opening, not accepted
        update["check_passed"] = False
    if outcome is Outcome.wrong_party:  # round 4: someone else had the phone, whatever passed before
        update["speaker_confirmed"] = False
    ended = state.model_copy(update=update)
    ended, utterance = _speak(ended, tuple(_line(state, key) for key in keys))
    return ended, EndOfCall(
        utterance=utterance,
        outcome=outcome,
        transcript=ended.transcript(),
        unresolved=ended.unresolved,
        callback_time=ended.callback_time,
        requested_language=ended.requested_language,
        language_switches=ended.language_switches,
        degraded_turns=ended.degraded_turns,
        speaker_confirmed=ended.speaker_confirmed,
    )


# --- order of the questions --------------------------------------------------


def _first_teach_back(state: CallState, product: int) -> Position:
    if product < len(state.plan.product_ids):
        return AtTeachBack(product=product, question=PRODUCT_QUESTIONS[0])
    return AtConsent()


def _next_question(state: CallState, product: int, question: Question) -> Position:
    """The question after `question` for this product, then the next product, then consent."""
    k = PRODUCT_QUESTIONS.index(question) + 1
    while k < len(PRODUCT_QUESTIONS):
        following = PRODUCT_QUESTIONS[k]
        own = state.plan.product_ids[product] in state.own_choice
        if not (following is Question.provider_choice and own):
            return AtTeachBack(product=product, question=following)
        k += 1
    return _first_teach_back(state, product + 1)


def _after(state: CallState, position: _Waiting) -> Position | None:
    """Where the call goes once `position` is answered or given up; None when it is ready to close."""
    match position:
        case AtRecall() | AtRecallFollowUp():
            return AtConsent()
        case AtTeachBack(product=product, question=question):
            return _next_question(state, product, question)
        case (
            AtReadBack(product=product, item="cover")
            | AtRestate(product=product, item="cover")
            | AtSayAgain(product=product, item="cover")
        ):
            return _next_question(state, product, Question.cover)
        case AtSayAgain(product=product) | AtReadBack(product=product) | AtRestate(product=product):
            return _next_question(state, product, Question.premium)
        case AtConsent():
            return None
        case _:
            raise ValueError(f"no question follows {position.at}")


def _go(
    state: CallState, position: Position | None, *, bridge: bool = False
) -> tuple[CallState, BotUtterance | EndOfCall]:
    return _end(state, Outcome.completed) if position is None else _say(state, position, bridge=bridge)


def _with_premium(state: CallState, product: int, amount_inr: int, low: int | None = None) -> CallState:
    product_id = state.plan.product_ids[product]
    kept = tuple(p for p in state.premiums if p.product_id != product_id)
    stated = StatedPremium(product_id=product_id, amount_inr=amount_inr, low=low)
    return state.model_copy(update={"premiums": (*kept, stated)})


def _unresolved_at(state: CallState, position: _Waiting) -> Unresolved:
    """The call step, question and product a position stands for."""
    match position:
        case AtIdentity():
            return Unresolved(step=CallStep.right_party_check)
        case AtGoAhead():
            return Unresolved(step=CallStep.disclosure)
        case AtBirthYear():
            return Unresolved(step=CallStep.second_check)
        case AtRecall() | AtRecallFollowUp():
            return Unresolved(step=CallStep.open_recall)
        case AtTeachBack(product=product, question=question):
            return Unresolved(
                step=CallStep.teach_back, asks=question, product_id=state.plan.product_ids[product]
            )
        case AtSayAgain(product=product, item=item):
            return Unresolved(
                step=CallStep.teach_back,
                asks=_item_question(item),
                product_id=state.plan.product_ids[product],
            )
        case AtConsent():
            return Unresolved(step=CallStep.consent_check, asks=Question.consent)
        case AtReadBack(product=product, item=item) | AtRestate(product=product, item=item):
            return Unresolved(
                step=CallStep.read_back, asks=_item_question(item), product_id=state.plan.product_ids[product]
            )
        case AtCallbackTime():
            return Unresolved(step=CallStep.close)


def _mark_unresolved(state: CallState, position: _Waiting) -> CallState:
    return state.model_copy(update={"unresolved": (*state.unresolved, _unresolved_at(state, position))})


# --- figures -----------------------------------------------------------------


class Figure(Frozen):
    """An amount heard in one reading: `low == high` for one figure; `about` when hedged or a range."""

    low: int
    high: int
    about: bool = False


def _figure(heard: Interpretation | None) -> Figure | None:
    if heard is None:
        return None
    if heard.approx is not None:
        return Figure(low=heard.approx[0], high=heard.approx[1], about=True)
    if heard.amount_inr is not None:
        return Figure(low=heard.amount_inr, high=heard.amount_inr)
    return None


def _same(a: Figure | None, b: Figure | None) -> bool:
    return a is not None and b is not None and (a.low, a.high) == (b.low, b.high)


def _read_back_at(product: int, figure: Figure, read_backs: int, item: str = "premium") -> AtReadBack:
    if item == "cover":  # a cover range is not read back as a range: only one plain figure is
        return AtReadBack(product=product, amount_inr=figure.high, read_backs=read_backs, item="cover")
    return AtReadBack(
        product=product,
        amount_inr=figure.high,
        read_backs=read_backs,
        low=figure.low if figure.about else None,
    )


def _keep(state: CallState, position: AtReadBack | AtRestate, figure: Figure) -> CallState:
    """Remember a premium the customer stated; a cover figure lives in the transcript only."""
    if position.item == "cover":
        return state
    return _with_premium(state, position.product, figure.high, figure.low if figure.about else None)


def _carry_forward(state: CallState, position: Position) -> tuple[CallState, Position]:
    """A figure the customer already gave in open recall is not asked for again: it is read back.

    Only for the first product, and only a single clean figure; the customer confirms or corrects it.
    """
    if not (
        isinstance(position, AtTeachBack)
        and position.question is Question.premium
        and position.product == 0
        and not position.reasked
        and state.recall_figure is not None
    ):
        return state, position
    amount, turn_id = state.recall_figure
    carried = CarriedAnswer(product_id=state.plan.product_ids[0], question=Question.premium, turn_id=turn_id)
    state = _with_premium(state, 0, amount).model_copy(
        update={"recall_figure": None, "carried_forward": (*state.carried_forward, carried)}
    )
    return state, AtReadBack(product=0, amount_inr=amount, read_backs=1)


# Classifier labels that say nothing about who is speaking ("हेलो? क्या बात चल रही थी?" read as a request to
# repeat): after a sign of another speaker they count as no label, so the who-check comes first (round 4).
_SILENT_ON_SPEAKER = frozenset({None, "asks_repeat", "who_or_why", "off_topic", "unclear"})

# Classifier labels that judge the speaker to be someone else (`llm_fallback`).
_SPEAKER_LABELS = frozenset({"wrong_person", "third_party_handoff"})


def _watching(state: CallState, position: Position) -> bool:
    """Is the call past the right-party pass, where every turn is read for signs of another speaker? Every position
    after the loan is named, and the go-ahead once the speaker is confirmed (iteration 3 fix round)."""
    return not isinstance(position, _BEFORE_LOAN) or state.speaker_confirmed


# Words of a line that name the loan (Hindi, Hinglish; Tamil and Kannada `not human-reviewed`).
_LOAN_WORDS = ("लोन", "loan", "கடன்", "ಸಾಲ")


def _names_something(line: Line) -> bool:
    """Does a line name the lender, the loan or a figure? Read from the line itself: its slots and its words."""
    return bool({"lender", "amount_words"} & line.slots.keys()) or any(w in line.text.casefold() for w in _LOAN_WORDS)


_DEFER_POSITIONS = (AtRecall, AtTeachBack, AtConsent)
_QUESTION_POSITIONS = (AtRecall, AtRecallFollowUp, AtTeachBack, AtSayAgain, AtConsent, AtReadBack, AtRestate)


# --- the two entry points ----------------------------------------------------


def start(
    record: LoanRecord,
    language: Language,
    *,
    lender_name: str,
    call_id: str | None = None,
    limits: Limits | None = None,
    identity: IdentityPolicy = IdentityPolicy(),  # noqa: B008 - frozen, so one shared default is safe
) -> tuple[CallState, BotUtterance]:
    """Open a call: the bot asks for the borrower by first name and says nothing else.

    `lender_name` is spoken in the disclosure; `LoanRecord` does not carry it. `identity` is the lender's
    right-party setting (P8); the default is no second check. Raises ValueError when the record cannot be
    called (no name, or more products than the language has ordinals).
    """
    names = record.borrower.name.split()
    if not names:
        raise ValueError("the borrower has no name to ask for")
    if not lender_name.strip():
        raise ValueError("lender_name is empty")
    limits = limits or Limits()
    if limits.max_bot_turns < 2:
        raise ValueError("Limits.max_bot_turns leaves no room for a question and a goodbye")
    if len(record.products) > len(load_prompts(language).ordinals):
        raise ValueError(f"the {language.value} prompts have no ordinal for product {len(record.products)}")
    plan = CallPlan(
        loan_id=record.loan_id,
        first_name=names[0],
        birth_year=expected_answer(identity.second_check, record) if identity.second_check else None,
        product_ids=tuple(p.id for p in record.products),
    )
    state = CallState(
        call_id=call_id or f"call-{record.loan_id}",
        language=language,
        lender_name=lender_name.strip(),
        plan=plan,
        limits=limits,
        position=AtIdentity(),
        identity=identity,
    )
    return _speak(state, _lines_for(state, state.position))


def step(
    state: CallState,
    customer_text: str,
    *,
    second_reading: str | None = None,
    interpreter: TurnInterpreter = _RULES,
) -> tuple[CallState, BotUtterance | EndOfCall]:
    """Take the customer's reply to the bot's last utterance and say what comes next.

    `second_reading` is another transcript of the same turn, from a second speech model. It counts
    only where the bot waits for a figure (the premium question, a read-back, a restated amount)
    and is ignored elsewhere. `""` means the second model was asked and heard nothing; `None` means
    no second reading was tried, and the call behaves as with one model.
    """
    position = state.position
    if position.at == "ended":
        raise ValueError("the call has ended")
    asked = state.turns[-1]
    expects = expecting(position)
    turn_id = TurnId(len(state.turns) + 1)

    def read(text: str) -> Interpretation:
        try:
            return interpreter.interpret(
                text, language=state.language, expecting=expects, question=asked.text,
                **_context_kwargs(interpreter, state, text),
            )
        except Exception:  # an interpreter's failure must never escape `step`
            log.warning("interpreter raised; turn read by the word lists", exc_info=True)
            heard = _RULES.interpret(text, language=state.language, expecting=expects, question=asked.text)
            unsure = not heard.settled and heard.intent is not Intent.acknowledges
            if expects in (Expecting.identity, Expecting.birth_year) and unsure:
                heard = heard.model_copy(update={"intent": Intent.said, "year": None})
            return heard.model_copy(update={"degraded": True})

    if second_reading is not None and expects in _FIGURE:  # both readings start before either is read
        _begin(interpreter, state, customer_text)
        _begin(interpreter, state, second_reading)
    heard = read(customer_text)
    other: Interpretation | None = None
    if second_reading is not None and expects in _FIGURE:
        other = read(second_reading)
        if _protects_more(other, heard):
            # A stop signal heard in only one reading wins over a figure or an answer in the other: the
            # call acts on it as if the turn had carried it alone (round 3).
            heard, other = other, heard
            customer_text, second_reading = second_reading, customer_text
        elif _protects(heard) is None and _figure(heard) is None and _figure(other) is not None \
                and heard.intent is not Intent.yes:  # fmt: skip
            # Only the second reading holds a figure: it is the one the call acts on, so `Turn.text`
            # holds the figure the bot will read back and the rules will compare.
            heard, other = other, heard
            customer_text, second_reading = second_reading, customer_text
        spare = SecondReading(
            turn_id=turn_id, text=second_reading, agreed=_same(_figure(heard), _figure(other))
        )
        state = state.model_copy(update={"second_readings": (*state.second_readings, spare)})
    reply = Turn(id=turn_id, speaker=Speaker.customer, step=asked.step, text=customer_text)
    update: dict = {"turns": (*state.turns, reply)}
    if heard.degraded or (other is not None and other.degraded):
        update["degraded_turns"] = (*state.degraded_turns, turn_id)
    silent = heard.intent is Intent.silence and (other is None or other.intent is Intent.silence)
    update["silences"] = state.silences + 1 if silent else 0
    state = state.model_copy(update=update)

    if silent and state.silences >= state.limits.max_silences:
        return _end(state, Outcome.no_response)
    if isinstance(position, AtStopCheck) and position.wish == "who":
        return _on_who_check(state, position, heard, customer_text)
    if heard.intent is Intent.other_language:
        own = heard.language_name in OWN_LANGUAGES[state.language]
        if not own:
            return _on_language_request(state, position, heard, turn_id)
        heard = heard.model_copy(update={"intent": Intent.asks_repeat, "language_name": None})
    if heard.intent is Intent.wants_human:
        return _end(state, Outcome.human_requested)
    if isinstance(position, _BEFORE_LOAN) and not state.speaker_confirmed \
            and heard.intent in (Intent.decline, Intent.do_not_call, Intent.call_later) \
            and speaks_of_borrower(customer_text, state.language, state.plan.first_name):  # fmt: skip
        return _end(state, Outcome.wrong_party)  # iteration 3: "रमेश जी नहीं हैं, ..." is not the borrower refusing
    if isinstance(position, AtIdentity) and not state.speaker_confirmed \
            and claims_another_name(customer_text, state.language, state.plan.first_name):  # fmt: skip
        # Iteration 4: "हाँ, मैं ही राजेश हूँ" on a record for Ramesh names someone else as the speaker. It ends here,
        # before any re-ask: a re-asked "are you Ramesh yourself?" would let a bare yes pass.
        return _end(state.model_copy(update={"speaker_confirmed": False}), Outcome.wrong_party)
    if heard.intent is Intent.decline:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.do_not_call:
        return _end(state, Outcome.do_not_call)
    if heard.intent is Intent.written_request:
        return _end(state, Outcome.written_requested)
    watching = _watching(state, position)
    if heard.intent is Intent.wrong_person and watching:
        if heard.classifier_label in _SPEAKER_LABELS and heard.other_speaker and not heard.possible_takeover:
            # Iteration 3 fix round: a weak sign ("मेरी वाइफ़ ने भरे थे पैसे") that a classifier read as someone else
            # gets the who-check, which names nothing, instead of the end. A strong sign keeps the end.
            return _who_check(state, position)
        return _end(state, Outcome.wrong_party)  # "talk to my son, he handles it"
    if watching:
        # Round 4: a sign of another speaker that no classifier label judged, or a turn nobody can judge
        # after such a sign, gets the who-check before anything else is said or taken as an answer. Iteration 3
        # fix round: also at the go-ahead after the pass, and a speaker naming themself as someone else.
        unjudged = heard.classifier_label in _SILENT_ON_SPEAKER
        doubt = state.speaker_doubt and unjudged and not heard.settled
        other_name = names_another_speaker(customer_text, state.language, state.plan.first_name)
        if heard.possible_takeover or other_name or (heard.other_speaker and unjudged) or doubt:
            return _who_check(state, position)
        if heard.other_speaker:
            state = state.model_copy(update={"speaker_doubt": True})
    if isinstance(position, AtGoAhead) and not state.delay_reasked and heard.intent in _DELAY_MAY_BE \
            and short_delay_or_echo(customer_text, state.language):  # fmt: skip
        # Iteration 3, round 2: "दो-तीन मिनट?", "15 minute baad" (speech heard the bot's own "दो-तीन मिनट" back), "थोड़ी
        # देर": no refusal and no clear later. The go-ahead is asked again once ("अभी … बात करें? बस हाँ या ना"),
        # even when a classifier read it as a call-back; a real later after that still ends as a call-back.
        state = state.model_copy(update={"delay_reasked": True})
        return _say(state, position.model_copy(update={"reasked": True}))
    if isinstance(position, AtCallbackTime):
        if position.resume is not None and means_now(customer_text, state.language):
            return _say(state, position.resume)  # "अभी बोलिए, अभी फ़्री हूँ": back to the pending question
        return _call_back(state, customer_text.strip() or None)
    if heard.intent is Intent.defers:
        if isinstance(position, _DEFER_POSITIONS):
            slot = _capped_slot(position) or position.at
            if slot not in state.deferrals and not getattr(position, "reasked", True):
                # W4: one re-ask, with a line that says the call wants the customer's own memory, not the record
                state = state.model_copy(update={"deferrals": (*state.deferrals, slot)})
                return _say(state, position.model_copy(update={"reasked": True}), before=("defer.reask",))
        heard = heard.model_copy(update={"intent": Intent.unclear})  # a second deferral: an unusable reply
    if heard.intent is Intent.call_later:
        if heard.callback == "ask":
            resume = None if isinstance(position, AtStopCheck) else position
            return _say(state, AtCallbackTime(resume=resume))
        return _call_back(state, customer_text if heard.callback == "time" else None)
    if isinstance(position, AtStopCheck):
        return _on_stop_check(state, position, heard)
    if heard.intent in (Intent.maybe_decline, Intent.maybe_human):
        wish = "decline" if heard.intent is Intent.maybe_decline else "human"
        if state.stop_checks >= state.limits.max_stop_checks:  # asked often enough: take it as meant
            return _end(state, Outcome.declined if wish == "decline" else Outcome.human_requested)
        state = state.model_copy(update={"stop_checks": state.stop_checks + 1})
        return _say(state, AtStopCheck(wish=wish, resume=position))
    if isinstance(position, AtIdentity) and state.identity.second_check is None \
            and heard.classifier_label not in _SPEAKER_LABELS \
            and not (heard.judged and heard.classifier_label != "confirms_self") \
            and claim_with_tail(customer_text, state.language, state.plan.first_name):  # fmt: skip
        # Iteration 3, round 2: an explicit claim passes whatever follows it ("मैं ही समीर हूँ, क्या issue है?"); the
        # question then gets the disclosure, which comes only after the pass. A classifier label that the speaker
        # is someone else still ends the call (`_on_identity_direct`).
        return _say(_passed(state), AtGoAhead(year_passed=True))
    if heard.intent is Intent.asks_who:
        if state.side_answers < state.limits.max_side_answers:
            state = state.model_copy(update={"side_answers": state.side_answers + 1})
            if isinstance(position, AtIdentity):  # no lender, no loan: only that it is a feedback call
                return _say(state, AtIdentity(reasked=True), before=("purpose.before_confirm",))
            if isinstance(position, AtBirthYear) and position.early:  # the lender is not named yet
                return _say(state, position, before=("purpose.before_confirm",))
            # Round 4: once the birth year has passed, identity is confirmed: the after-loan answer.
            confirmed = state.speaker_confirmed or (isinstance(position, AtGoAhead) and position.year_passed)
            before = isinstance(position, _BEFORE_LOAN) and not confirmed
            verify = "verify.before_loan" if before else "verify.after_loan"
            return _say(state, position, before=(verify,))
        heard = heard.model_copy(update={"intent": Intent.asks_repeat})
    # The classifier failed on a free reply: ask once whether to go on.
    failed = heard.degraded and heard.intent is Intent.said and isinstance(position, _QUESTION_POSITIONS)
    if failed and not state.degraded_checked:
        state = state.model_copy(update={"degraded_checked": True})
        return _say(state, AtStopCheck(wish="decline", resume=position))
    if isinstance(position, _QUESTION_POSITIONS):
        state, check = _disengaged(state, position, heard)
        if check is not None:
            return _say(state, check)
    if isinstance(position, AtIdentity) and position.reasked and heard.intent is Intent.said \
            and starts_with_yes(customer_text, state.language):  # fmt: skip
        heard = heard.model_copy(update={"intent": Intent.acknowledges})  # any length at the re-ask
    if isinstance(position, AtRecall) and heard.amount_inr is not None and heard.intent not in UNCLEAR:
        state = state.model_copy(update={"recall_figure": (heard.amount_inr, turn_id)})
    return _on_reply(state, position, heard, other)


# Readings at the go-ahead that a short delay or an echo of the bot's time phrase may carry: never a yes, a refusal
# or a third party (iteration 3, round 2).
_DELAY_MAY_BE = frozenset({
    Intent.call_later, Intent.said, Intent.unclear, Intent.asks_repeat, Intent.filler, Intent.off_topic,
    Intent.maybe_decline,
})  # fmt: skip


# Stop intents, most protective first: when two readings of one turn differ, the earlier one wins.
_PROTECTIVE = (
    Intent.wrong_person, Intent.do_not_call, Intent.decline, Intent.wants_human, Intent.written_request,
    Intent.call_later, Intent.other_language, Intent.maybe_decline, Intent.maybe_human,
)  # fmt: skip


def _protects(heard: Interpretation) -> int | None:
    """The rank of a reading's stop intent in `_PROTECTIVE` (lower is stronger); None when it has none.
    A possible takeover, or a sign of another speaker no classifier judged, ranks just after `wrong_person`."""
    if heard.intent in _PROTECTIVE:
        return 2 * _PROTECTIVE.index(heard.intent)
    unjudged_sign = heard.other_speaker and heard.classifier_label in _SILENT_ON_SPEAKER
    return 1 if heard.possible_takeover or unjudged_sign else None


def _protects_more(a: Interpretation, b: Interpretation) -> bool:
    """Does reading `a` carry a stop intent that is stronger than any in reading `b`?"""
    rank_a, rank_b = _protects(a), _protects(b)
    return rank_a is not None and (rank_b is None or rank_a < rank_b)


def turn_context(state: CallState, text: str) -> TurnContext:
    """The context classifier's view beyond the turn (W4): the record's first name, name hints from the reply, and
    the exchange before this one, unless that exchange was at the year of birth (never sent to any model)."""
    previous_question = previous_reply = None
    turns = state.turns
    for k in range(len(turns) - 1, -1, -1):
        if turns[k].speaker is Speaker.customer:
            bot = next((t for t in reversed(turns[:k]) if t.speaker is Speaker.bot), None)
            if turns[k].step is not CallStep.second_check and (bot is None or bot.step is not CallStep.second_check):
                previous_reply = turns[k].text
                previous_question = bot.text if bot is not None else None
            break
    name = state.plan.first_name
    hints = name_hints(text, name)
    return TurnContext(
        first_name=name, previous_question=previous_question, previous_reply=previous_reply, name_hints=hints
    )


def _context_kwargs(interpreter: TurnInterpreter, state: CallState, text: str) -> dict:
    """`context=` only for an interpreter that declares `wants_context`; others keep the old signature."""
    return {"context": turn_context(state, text)} if getattr(interpreter, "wants_context", False) else {}


def _begin(interpreter: TurnInterpreter, state: CallState, text: str) -> None:
    begin = getattr(interpreter, "begin", None)
    if begin is None:
        return
    try:
        begin(text, language=state.language, expecting=expecting(state.position), question=state.turns[-1].text,
              **_context_kwargs(interpreter, state, text))
    except Exception:
        log.warning("interpreter begin raised", exc_info=True)


def prefetch(state: CallState, customer_text: str, *, interpreter: TurnInterpreter) -> None:
    """Start the classifier for this turn as soon as a transcript exists. A no-op when the interpreter
    has no `begin` or the call has ended; never raises. `step` with the same text then waits less."""
    if state.position.at == "ended":
        return
    _begin(interpreter, state, customer_text)


def _disengaged(
    state: CallState, position: _Waiting, heard: Interpretation
) -> tuple[CallState, AtStopCheck | None]:
    """Two unusable replies or three "I don't know"s in a row get one "shall I ask on, or stop here?"."""
    unusable = heard.intent in UNCLEAR and heard.intent is not Intent.silence
    dont_know = heard.intent is Intent.dont_know
    runs = {
        "unusable_run": state.unusable_run + 1 if unusable else 0,
        "dont_know_run": state.dont_know_run + 1 if dont_know else 0,
    }
    state = state.model_copy(update=runs)
    if state.disengage_checked or (runs["unusable_run"] < 2 and runs["dont_know_run"] < 3):
        return state, None
    state = state.model_copy(update={"disengage_checked": True, "unusable_run": 0, "dont_know_run": 0})
    return state, AtStopCheck(wish="disengaged", resume=position, then=heard.intent)


def _call_back(state: CallState, when: str | None) -> tuple[CallState, EndOfCall]:
    return _end(state.model_copy(update={"callback_time": when}), Outcome.call_back_later)


def _on_reply(state: CallState, position: _Waiting, heard: Interpretation, other: Interpretation | None):
    match position:
        case AtIdentity() if state.identity.second_check is None:
            return _on_identity_direct(state, position, heard)
        case AtIdentity():
            return _on_identity(state, position, heard)
        case AtGoAhead():
            return _on_go_ahead(state, position, heard)
        case AtBirthYear():
            return _on_birth_year(state, position, heard)
        case AtRecall():
            return _on_recall(state, position, heard)
        case AtRecallFollowUp():
            return _on_follow_up(state, position, heard)
        case AtTeachBack() | AtConsent():
            return _on_question(state, position, heard, other)
        case AtSayAgain():
            return _on_amount(state, position, heard, other)
        case AtReadBack():
            return _on_read_back(state, position, heard, other)
        case AtRestate():
            return _on_restate(state, position, heard, other)
        case AtCallbackTime():  # back from a who-check asked at "when shall we call?": ask it again
            return _say(state, position)


def _who_check(
    state: CallState, position: Position, *, fresh: bool = False
) -> tuple[CallState, BotUtterance | EndOfCall]:
    """Ask who is speaking (`right_party.who_check`, which names neither the lender nor the loan), then go back to
    the pending question. Past `Limits.max_who_checks` the call ends as `wrong_party` instead.

    From the go-ahead the call goes back to the go-ahead's re-ask, put as new (iteration 3 fix round), so a
    go-ahead asked twice before does not end as `no_go_ahead` on the way back."""
    resume = position.resume if isinstance(position, AtStopCheck) else position
    if state.who_checks >= state.limits.max_who_checks:
        return _end(state, Outcome.wrong_party)
    if isinstance(resume, AtGoAhead):
        resume, fresh = resume.model_copy(update={"reasked": True}), True
    state = state.model_copy(update={"who_checks": state.who_checks + 1})
    return _say(state, AtStopCheck(wish="who", resume=resume, fresh=fresh))


_WHO_CHECK_ENDS = {
    Intent.decline: Outcome.declined, Intent.maybe_decline: Outcome.declined,
    Intent.wants_human: Outcome.human_requested, Intent.maybe_human: Outcome.human_requested,
    Intent.do_not_call: Outcome.do_not_call, Intent.written_request: Outcome.written_requested,
}  # fmt: skip


_WHO_CHECK_STOPS = frozenset({*_WHO_CHECK_ENDS, Intent.call_later, Intent.other_language})


# W4: the prompt file a requested language is served from. English goes to the Hinglish file, the closest one
# there is (its lines mix English words into Hindi); a request for a language with no file ends the call.
_SWITCH_TO: dict[str, Language] = {
    "hindi": Language.hi, "tamil": Language.ta, "kannada": Language.kn, "english": Language.hi_en,
}  # fmt: skip


def _on_language_request(state: CallState, position: Position, heard: Interpretation, turn_id: TurnId):
    """W4: switch live to a language that has a prompt file and put the pending question again, as new, in it;
    otherwise end with `end.language`. Never while a sign of another speaker is unsettled."""
    target = _SWITCH_TO.get(heard.language_name or "")
    room = len(state.language_switches) < state.limits.max_language_switches
    if target is None or target is state.language or not room or state.speaker_doubt:
        return _end(state.model_copy(update={"requested_language": heard.language_name}), Outcome.language_switch)
    switch = LanguageSwitch(
        turn_id=turn_id, from_language=state.language, to_language=target, requested=heard.language_name or ""
    )
    state = state.model_copy(update={"language": target, "language_switches": (*state.language_switches, switch)})
    return _say(state, position, lead=("language.switched",))


def _on_who_check(state: CallState, position: AtStopCheck, heard: Interpretation, text: str):
    """ "Is it you speaking?" (round 4), the same in every arm.

    A reply that points at someone else (a relation, a third person, a denial, a takeover sign) ends the call
    as `wrong_party`, whatever the classifier says. The call goes back to the question only on an
    affirmation: every word explained by the closed vocabulary (`affirms_self`), or the classifier's
    `confirms_self` on a reply with a first-person word. A stop request ends as asked; anything else ends as
    `wrong_party`.

    Iteration 3: the who-check is a choice question ("you yourself, or someone else?") asked only after a sign
    of another speaker, so it resumes only on an explicit first-person self-claim (`claims_self`: "मैं ही",
    "मैं ख़ुद", "मैं Ramesh", "Ramesh बोल रहा हूँ", "speaking"), in every arm; the classifier's `confirms_self`
    needs such a claim too. A bare yes ("हाँ", "जी", "ठीक है") does not answer a choice question and ends the
    call, with no re-ask (a re-ask gives a third party a second try with the answer in hand). Resuming wrongly
    names the loan to a third party; ending wrongly costs a genuine borrower one call that ops retries.
    Known and accepted: a third party who says outright "मैं ही रमेश हूँ" passes; no text rule can catch it.

    Fix round: a classifier label that the speaker is someone else ends the call; otherwise the claim is read by
    `who_check_claim` before any sign: interjections and fillers may stand beside
    it, and a clause explaining that a relative or a child had the phone is set aside. Anything else that points
    elsewhere ends the call as before.
    """
    language, name = state.language, state.plan.first_name
    if heard.classifier_label in _SPEAKER_LABELS:  # a label may end the call, never clear a sign
        return _end(state.model_copy(update={"speaker_confirmed": False}), Outcome.wrong_party)
    claimed = heard.classifier_label == "confirms_self" and who_check_claim(text, language, name, closed=False)
    # Iteration 3, round 2: an explicit claim with any tail that puts nobody else in the speaker's place
    # (`claim_with_tail`), unless the reply also asks to stop: a stop is read as before, with the speaker unconfirmed.
    tail = heard.intent not in _WHO_CHECK_STOPS and claim_with_tail(text, language, name)
    if (who_check_claim(text, language, name) or claimed or tail) and not doubts_claim(text, language, name):
        state = state.model_copy(update={"speaker_doubt": False})
        if position.fresh:
            return _say(state, position.resume)
        return _on_reply(state, position.resume, Interpretation(intent=position.then), None)
    someone_else = heard.possible_takeover or heard.other_speaker or heard.intent is Intent.wrong_person
    if someone_else or points_elsewhere(text, language, count_denial=False):
        return _end(state, Outcome.wrong_party)
    # Nobody claimed to be the borrower: whatever ends the call ends it with the speaker unconfirmed. A stop
    # request ends as asked (iteration 3: before a plain no-word is read as "not me"); anything else is a
    # wrong party, with no re-ask.
    state = state.model_copy(update={"speaker_confirmed": False})
    if heard.intent is Intent.other_language:
        state = state.model_copy(update={"requested_language": heard.language_name})
        return _end(state, Outcome.language_switch)
    if heard.intent is Intent.call_later:
        return _call_back(state, text if heard.callback == "time" else None)
    return _end(state, _WHO_CHECK_ENDS.get(heard.intent, Outcome.wrong_party))


def _on_stop_check(state: CallState, position: AtStopCheck, heard: Interpretation):
    """ "Shall we go on?": yes goes back to the question, no ends the call. "Shall a person call you?": the reverse.

    Anything else goes back to the question, as if its last reply had been unclear.
    """
    if heard.intent is Intent.maybe_decline:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.maybe_human:
        return _end(state, Outcome.human_requested)
    if position.wish in ("decline", "disengaged") and heard.intent is Intent.no:
        return _end(state, Outcome.declined)
    if position.wish == "human" and heard.intent is Intent.yes:
        return _end(state, Outcome.human_requested)
    return _on_reply(state, position.resume, Interpretation(intent=position.then), None)


def _on_identity(state: CallState, position: AtIdentity, heard: Interpretation):
    if heard.intent is Intent.yes:
        return _say(state, AtGoAhead())
    if heard.intent is Intent.acknowledges:  # not a claim: the year first, the lender after it
        return _say(state, AtBirthYear(early=True))
    if heard.intent in (Intent.no, Intent.wrong_person):
        return _end(state, Outcome.wrong_party)
    if position.reasked:
        return _end(state, Outcome.not_confirmed)
    return _say(state, AtIdentity(reasked=True))


# Classifier labels that confirm a yes at the direct question when the word lists alone are not sure.
_YES_LABELS = frozenset({"yes", "confirms_self"})


def _passed(state: CallState) -> CallState:
    return state.model_copy(update={"speaker_confirmed": True, "check_passed": True})


def _on_identity_direct(state: CallState, position: AtIdentity, heard: Interpretation):
    """No second check (P8). The name question, then the direct question "are you <name> yourself?"
    (`right_party.reask`); a yes to that passes. An explicit first-person claim at the name question already
    answers it. A relation, another name, a denial ends as `wrong_party` (read before this, as in round 4); a
    hedge or a question is never a pass. An ordinary yes the word lists are not sure of passes only on a
    classifier label that says yes: with the classifier failing nothing protects the loan after the pass."""
    if heard.intent in (Intent.no, Intent.wrong_person):
        return _end(state, Outcome.wrong_party)
    text = state.turns[-1].text if state.turns and state.turns[-1].speaker is Speaker.customer else ""
    if heard.judged:
        return _on_identity_judged(state, position, heard, text)
    # Iteration 3, round 2: a reply that puts someone else in the speaker's place, hedges, or asks whom the caller wants
    # is never plain, whatever a classifier labelled it ("हाँ मैं ही हूँ, मेरा बेटा बात करेगा").
    plain = not hedges_or_asks(text, state.language) and not doubts_claim(text, state.language, state.plan.first_name)
    if plain and heard.intent in (Intent.yes, Intent.acknowledges, Intent.said) \
            and claims_self(text, state.language, state.plan.first_name):  # fmt: skip
        # Iteration 3 fix round: an explicit first-person claim in the closed vocabulary ("जी, मैं ही रमेश हूँ",
        # "haan main Ramesh bol raha hoon") passes in every arm, at the name question and the direct question;
        # the interpreter cannot see the first name, so the call reads it here.
        return _say(_passed(state), AtGoAhead(year_passed=True))
    if heard.intent is Intent.yes and plain:
        return _say(_passed(state), AtGoAhead(year_passed=True))
    if not position.reasked:  # a yes, or anything not yet a yes: the direct question, once
        return _say(state, AtIdentity(reasked=True))
    sure = heard.settled or heard.classifier_label in _YES_LABELS
    if heard.intent is Intent.acknowledges and sure and plain:
        return _say(_passed(state), AtGoAhead(year_passed=True))
    if asks_something(text, state.language) and state.side_answers < state.limits.max_side_answers:
        # "हाँ, क्या बात है?": not a pass; the question is answered without the lender or the loan, and the
        # direct question is put again (within the "who is this?" answers allowed).
        state = state.model_copy(update={"side_answers": state.side_answers + 1})
        return _say(state, position, before=("purpose.before_confirm",))
    return _end(state, Outcome.not_confirmed)


def _on_identity_judged(state: CallState, position: AtIdentity, heard: Interpretation, text: str):
    """W4: the context classifier decided the reply. `confirms_self` passes; `yes` gets the direct question, and at
    the direct question passes (the yes-twice default). A third-party sign or another name is a veto."""
    name = state.plan.first_name
    if claims_another_name(text, state.language, name):
        return _end(state.model_copy(update={"speaker_confirmed": False}), Outcome.wrong_party)
    if only_asks_whom(text, state.language, name):
        # W4 fix round: the only sign is a question about whom the caller wants: the direct question once, not the end
        if not position.reasked:
            return _say(state, AtIdentity(reasked=True))
        return _end(state, Outcome.not_confirmed)
    if third_party_sign(text, state.language, name):
        return _end(state.model_copy(update={"speaker_confirmed": False}), Outcome.wrong_party)
    label = heard.classifier_label
    # A hedge on the claim itself ("शायद मैं ही हूँ", "मान लीजिए") never passes; a trailing question after a claim
    # does ("मैं ही समीर हूँ, क्या issue है?": the disclosure that follows the pass answers it). A plain yes passes at
    # the direct question only without a hedge or a question, as before.
    hedged = hedges_claim(text, state.language, name)
    plain = not hedged and not hedges_or_asks(text, state.language)
    # A `yes` label on a reply the word lists read as an explicit claim with the name ("Sunita here, go on") passes
    # as today: the label says it agrees, and a claim needs no "I" when it names the borrower.
    claim = label == "yes" and not hedged and claim_with_tail(text, state.language, name)
    if (label == "confirms_self" and not hedged) or claim or (label == "yes" and position.reasked and plain and heard.intent is not Intent.filler
                                                       and (starts_with_yes(text, state.language)
                                                            or affirms_or_goes_on(text, state.language))):
        return _say(_passed(state), AtGoAhead(year_passed=True))
    if not position.reasked:
        return _say(state, AtIdentity(reasked=True))
    if asks_something(text, state.language) and state.side_answers < state.limits.max_side_answers:
        state = state.model_copy(update={"side_answers": state.side_answers + 1})
        return _say(state, position, before=("purpose.before_confirm",))
    return _end(state, Outcome.not_confirmed)


def _on_go_ahead(state: CallState, position: AtGoAhead, heard: Interpretation):
    if heard.intent is Intent.yes:
        return _say(state, AtRecall() if position.year_passed else AtBirthYear())
    if heard.intent is Intent.no:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.wrong_person:
        return _end(state, Outcome.wrong_party)
    if position.reasked:
        return _end(state, Outcome.no_go_ahead)
    return _say(state, position.model_copy(update={"reasked": True}))


def _on_birth_year(state: CallState, position: AtBirthYear, heard: Interpretation):
    if heard.intent is Intent.wrong_person:  # "पापा 1984 में पैदा हुए थे" names the year too
        return _end(state, Outcome.wrong_party)
    known = state.plan.birth_year
    # Two digits ("84") pass from 10 up only: "एक" and "दो" turn up in replies that give no year at
    # all ("एक बार फिर बोलिए"), and nobody gives 2002 as "दो".
    short = known % 100

    def matches(year: int | None) -> bool:
        return year is not None and (year == known or (short >= 10 and year == short))

    if not heard.two_years and matches(heard.year):
        state = _passed(state).model_copy(update={"check_attempts": state.check_attempts + 1})
        return _say(state, AtGoAhead(year_passed=True) if position.early else AtRecall())
    # A year that does not match, or a guess or two years, uses an attempt (P8: one by default, two when the
    # lender sets it); past the last one the call ends. A reply with no year, or the right year said in a way
    # the call could not take as the speaker's own, is asked again once, whatever the attempts.
    heard_year = heard.year if heard.year is not None else heard.loose_year
    wrong = heard.two_years or (heard_year is not None and not matches(heard_year))
    failed = keys = None
    if wrong:
        state = state.model_copy(update={"check_attempts": state.check_attempts + 1})
        failed = state.check_attempts >= state.identity.attempts
    if failed or (not wrong and position.reasked):
        keys = ("end.third_party",) if position.early else None  # the ordinary path must not name the lender
        return _end(state, Outcome.second_check_failed, keys=keys)
    if wrong:
        return _say(state, position.model_copy(update={"retry": True}))
    return _say(state, position.model_copy(update={"reasked": True}))


def _start_products(state: CallState, heard: Interpretation | None = None):
    if heard is not None and heard.names_something:  # gain 8: the kind question refers to what was named
        state = state.model_copy(update={"recall_named": True})
    return _say(state, _first_teach_back(state, 0))


def _on_recall(state: CallState, position: AtRecall, heard: Interpretation):
    # Nothing branch only for a reply that names nothing: "पता नहीं, बावन हज़ार कटे थे" names something.
    if heard.names_nothing or (
        heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know) and not heard.names_something
    ):
        return _say(state, AtRecallFollowUp())
    if heard.intent in UNCLEAR and not heard.names_something:
        if not position.reasked:
            return _say(state, AtRecall(reasked=True))
        return _say(_mark_unresolved(state, position), AtRecallFollowUp())
    return _start_products(state, heard)


def _on_follow_up(state: CallState, position: AtRecallFollowUp, heard: Interpretation):
    """One follow-up only: whatever the reply, the call does not ask it again."""
    if heard.names_nothing or (
        heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know) and not heard.names_something
    ):
        return _say(state, AtConsent())
    if heard.intent in UNCLEAR and not heard.names_something:
        return _say(_mark_unresolved(state, position), AtConsent())
    return _start_products(state, heard)


def _follow_up(state: CallState, position: AtTeachBack | AtConsent, heard: Interpretation):
    """W4: the one follow-up for a half answer, chosen only by what the customer said (never by the record)."""
    if heard.intent is not Intent.said or heard.names_nothing:
        return None
    reply = state.turns[-1]
    # Only a figure the call could read back counts (W4 fix round: "एक फॉर्म", "ek baar" hold the figure 1)
    figure = heard.amount_inr is not None or any(f >= 100 for f in heard.figures)
    if isinstance(position, AtConsent):
        slot = "consent"
        halves = consent_halves(reply.text, state.language, reply.id, figure=figure)
        missing = missing_half(*halves) if halves is not None else None
        follow: AtTeachBack | AtConsent | None = None if missing is None else AtConsent(follow=missing)
    elif position.question is Question.kind:
        slot = f"kind:{state.plan.product_ids[position.product]}"
        half = kind_is_half(reply.text, state.language, figure=figure)
        follow = position.model_copy(update={"follow": True}) if half else None
    else:
        return None
    if follow is None or slot in state.follow_ups:
        return None
    return _say(state.model_copy(update={"follow_ups": (*state.follow_ups, slot)}), follow)


def _on_question(state: CallState, position: AtTeachBack | AtConsent, heard: Interpretation, other):
    if position.follow:  # W4: after the follow-up the call goes on as if the question had been answered
        return _go(state, _after(state, position))
    followed = _follow_up(state, position, heard)
    if followed is not None:
        return followed
    if isinstance(position, AtTeachBack):
        first_of_later = position.product > 0 and position.question is PRODUCT_QUESTIONS[0]
        denies = heard.intent in (Intent.took_nothing, Intent.no) and not heard.names_something
        if first_of_later and not position.reasked and (heard.names_nothing or denies):
            # Wave 2: nothing more was taken: the remaining products are left unresolved, then consent.
            rest = state.plan.product_ids[position.product :]
            left = tuple(Unresolved(step=CallStep.teach_back, asks=PRODUCT_QUESTIONS[0], product_id=p) for p in rest)
            return _say(state.model_copy(update={"unresolved": (*state.unresolved, *left)}), AtConsent())
        if heard.intent is Intent.took_nothing:  # "कौन सी चीज़? मैंने तो कुछ नहीं लिया": no more product questions
            return _say(state, AtConsent())
        if position.question in (Question.premium, Question.cover):
            return _on_amount(state, position, heard, other)
        if position.question is Question.required_for_loan and heard.own_choice:
            product_id = state.plan.product_ids[position.product]
            state = state.model_copy(update={"own_choice": (*state.own_choice, product_id)})
    if heard.intent not in UNCLEAR:
        return _go(state, _after(state, position))
    if not position.reasked:
        return _say(state, position.model_copy(update={"reasked": True}))
    state = _mark_unresolved(state, position)
    return _go(state, _after(state, position), bridge=True)


def _on_amount(state: CallState, position: AtTeachBack | AtSayAgain, heard: Interpretation, other):
    """An answer to "how much did you pay?" or "what do you get from it?": the same two-reading rule.

    The readings differ, or only one holds a figure: the amount is asked for once more per product and
    item. Then the figure is read back. A figure the parser marks ambiguous is never read back.
    """
    product = position.product
    item = position.item if isinstance(position, AtSayAgain) else position.question.value
    cover = item == "cover"
    first, second = _figure(heard), _figure(other)
    if cover:  # a cover range is not read back; only one plain figure is
        first = first if first is not None and not first.about else None
        second = second if second is not None and not second.about else None
    else:  # a premium said as a bound ("पचास हज़ार तक") is no figure: the premium is asked again
        first = None if heard.bound else first
        second = None if other is not None and other.bound else second
    done = state.said_again_cover if cover else state.said_again
    product_id = state.plan.product_ids[product]
    differ = other is not None and (first is not None or second is not None) and not _same(first, second)
    if differ and product_id not in done:  # never read back a figure on one model's word the first time
        key = "said_again_cover" if cover else "said_again"
        state = state.model_copy(update={key: (*done, product_id)})
        return _say(state, AtSayAgain(product=product, item=item))
    figure = first or second
    if figure is not None:
        if not cover:
            state = _with_premium(state, product, figure.high, figure.low if figure.about else None)
        return _say(state, _read_back_at(product, figure, 1, item=item))
    answered = heard.intent in (Intent.dont_know, Intent.no, Intent.took_nothing)
    if cover:  # "पैसा सुरक्षित रहेगा" answers the cover question without a figure
        answered = heard.intent not in UNCLEAR and not heard.figures
    if answered:
        return _go(state, _after(state, position))
    if isinstance(position, AtTeachBack) and not position.reasked:
        return _say(state, position.model_copy(update={"reasked": True}))
    state = _mark_unresolved(state, position)
    return _go(state, _after(state, position), bridge=True)


def _verdict(position: AtReadBack, heard: Interpretation) -> str:
    """What one reading says to a read-back: confirm, reject, another figure, or nothing clear."""
    read = Figure(
        low=position.low or position.amount_inr, high=position.amount_inr, about=position.low is not None
    )
    figure = _figure(heard)
    if figure is not None and not _same(figure, read):
        return "unclear" if heard.intent is Intent.yes else "figure"
    if heard.intent is Intent.no:
        return "reject"
    # A repeat of the figure read back confirms it when the rest of the reply is only yes-words, fillers
    # or "that is what I paid" words (`Interpretation.only_amount`; round 3 widened it: "52,000 दिए थे").
    if heard.intent is Intent.yes or (figure is not None and heard.only_amount and figure.about == read.about):
        return "confirm"
    return "unclear"


def _names_another(position: AtReadBack, heard: Interpretation) -> bool:
    """ "शायद पचपन हज़ार", "not fifty two, fifty five thousand": no one figure, but not the one read back."""
    return _figure(heard) is None and any(figure != position.amount_inr for figure in heard.figures)


def _on_read_back(state: CallState, position: AtReadBack, heard: Interpretation, other):
    more = position.read_backs < state.limits.max_read_backs
    verdict = _verdict(position, heard)
    if other is not None:
        second = _verdict(position, other)
        if "confirm" in (verdict, second) and {verdict, second} & {"reject", "figure"}:
            verdict = "unclear"  # one model heard yes, the other no: say it again
    if verdict == "figure":
        figure = _figure(heard)
        state = _keep(state, position, figure)
        if more:
            return _say(
                state, _read_back_at(position.product, figure, position.read_backs + 1, position.item)
            )
    elif verdict == "reject" or (_names_another(position, heard) and heard.intent is not Intent.yes):
        if more:
            restate = AtRestate(
                product=position.product,
                read_backs=position.read_backs,
                rejected_inr=position.amount_inr,
                item=position.item,
            )
            return _say(state, restate)
    elif verdict == "confirm":
        return _go(state, _after(state, position))
    elif more and heard.intent is not Intent.dont_know:  # "I don't know" is recorded, not pressed
        return _say(state, position.model_copy(update={"read_backs": position.read_backs + 1}), again=True)
    state = _mark_unresolved(state, position)
    return _go(state, _after(state, position), bridge=True)


def _on_restate(state: CallState, position: AtRestate, heard: Interpretation, other):
    figure = _figure(heard) or _figure(other)
    if figure is not None:
        state = _keep(state, position, figure)
        return _say(state, _read_back_at(position.product, figure, position.read_backs + 1, position.item))
    state = _mark_unresolved(state, position)
    return _go(state, _after(state, position), bridge=True)


def identity_record(state: CallState) -> IdentityRecord:
    """What the case file keeps of the right-party check (P8). Pure. It holds the policy, the check used, the
    attempts, whether it passed and one fixed sentence; nothing of the expected answer or of any reply."""
    policy = state.identity
    passed = state.check_passed
    if passed is None and state.speaker_confirmed:  # a state saved before P8 that passed the year
        passed = True
    used = min(state.check_attempts, policy.attempts) if policy.second_check else 0
    # Fix round: the check passed, and later in the call someone else had the phone (a who-check or a takeover).
    later = passed is True and state.position == Ended(outcome=Outcome.wrong_party)
    return IdentityRecord(
        policy=policy,
        check_used=policy.second_check,
        attempts_allowed=policy.attempts if policy.second_check else 0,
        attempts_used=used,
        passed=passed,
        prior_notice_shown=policy.prior_notice,
        sentence=identity_sentence(policy, attempts_used=used, passed=passed, later_wrong_party=later),
    )


def call_seconds(transcript: Transcript, *, words_per_second: float = 2.5) -> float:
    """Speech time of a call, bot and customer: audio times where a turn has them, else its word count.

    The word-count rate is an assumption, not a measurement; pass the rate you assume.
    """
    total = 0.0
    for turn in transcript.turns:
        if turn.start_s is not None and turn.end_s is not None:
            total += turn.end_s - turn.start_s
        else:
            total += len(turn.text.split()) / words_per_second
    return total
