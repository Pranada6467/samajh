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

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from samajh.amounts import format_inr, spoken_amount
from samajh.dialogue.interpret import (
    UNCLEAR,
    Expecting,
    Intent,
    Interpretation,
    RuleInterpreter,
    TurnInterpreter,
)
from samajh.dialogue.prompts import LINES, PRODUCT_QUESTIONS, load_prompts
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


class Limits(Frozen):
    max_bot_turns: int = Field(default=60, ge=1)  # utterances, including the closing one
    max_read_backs: int = Field(default=3, ge=1)  # read-backs of one product's premium
    max_stop_checks: int = Field(default=2, ge=0)  # times a call asks "shall we go on?"
    max_silences: int = Field(default=2, ge=1)  # consecutive silent turns before the call ends
    max_side_answers: int = Field(default=2, ge=0)  # "who is this?" answers before it counts as unclear


class CallPlan(Frozen):
    """All the call keeps of the loan record."""

    loan_id: str
    first_name: str
    birth_year: int
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
    at: Literal["identity"] = "identity"
    reasked: bool = False


class AtGoAhead(Frozen):
    at: Literal["go_ahead"] = "go_ahead"
    reasked: bool = False


class AtBirthYear(Frozen):
    at: Literal["birth_year"] = "birth_year"
    reasked: bool = False


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


class AtSayAgain(Frozen):
    """The two readings of the premium answer differed: the bot asked for the amount once more."""

    at: Literal["say_again"] = "say_again"
    product: int


class AtConsent(Frozen):
    at: Literal["consent"] = "consent"
    reasked: bool = False


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


class Ended(Frozen):
    at: Literal["ended"] = "ended"
    outcome: Outcome


_Question = AtRecall | AtTeachBack | AtConsent
_Waiting = (
    AtIdentity | AtGoAhead | AtBirthYear | AtRecall | AtRecallFollowUp | AtTeachBack | AtSayAgain | AtConsent
    | AtReadBack | AtRestate | AtCallbackTime
)  # fmt: skip


class AtStopCheck(Frozen):
    """A reply may have meant "stop" or "get me a person"; the bot asked, and goes back to `resume`.

    Only a weak signal comes here (a short "leave it", a refusal the customer may be quoting, or an
    LLM's guess). A plain refusal or a plain request for a human ends the call at once.
    """

    at: Literal["stop_check"] = "stop_check"
    wish: Literal["decline", "human"]
    resume: Annotated[_Waiting, Field(discriminator="at")]


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
    degraded_turns: tuple[TurnId, ...] = ()  # customer turns the LLM fallback failed on

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
    degraded_turns: tuple[TurnId, ...] = ()


_RULES = RuleInterpreter()

_TOLD = frozenset({Question.provider_choice, Question.cancel_window})
_EITHER_OR = frozenset({Question.required_for_loan, Question.payment_frequency})
_FIGURE = frozenset({Expecting.amount, Expecting.confirmation})  # replies that may carry a rupee figure
_BEFORE_LOAN = (AtIdentity, AtGoAhead, AtBirthYear)
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
        case AtTeachBack(question=Question.premium) | AtSayAgain() | AtRestate():
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
        said = {"amount_words": spoken_amount(amount, state.language), "amount_digits": format_inr(amount)}
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
        case AtGoAhead():
            return tuple(
                _line(state, f"disclosure.{key}") for key in ("who", "not_sales", "recording", "go_ahead")
            )
        case AtBirthYear(reasked=True):
            return (_line(state, "second_check.reask"),)
        case AtBirthYear():
            return (
                _line(state, "disclosure.never_ask", step=CallStep.second_check),
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
        case AtTeachBack(product=product, question=question, reasked=reasked):
            ask = _line(state, f"{question.value}.{'reask' if reasked else 'ask'}", product=product)
            if question is not PRODUCT_QUESTIONS[0] or reasked:
                return (ask,)
            if len(state.plan.product_ids) > 1:
                ordinal = load_prompts(state.language).ordinal(product)
                return (_line(state, "teach_back.intro_nth", ordinal=ordinal), ask)
            return (_line(state, "teach_back.intro"), ask)
        case AtSayAgain(product=product):
            return (_line(state, "premium.say_again", product=product),)
        case AtConsent(reasked=reasked):
            return (_line(state, "consent.reask" if reasked else "consent.ask"),)
        case AtReadBack():
            return (_read_back_line(state, position, again=again),)
        case AtRestate(product=product, item=item):
            return (_line(state, "read_back.restate", product=product, asks=_item_question(item)),)
        case AtCallbackTime():
            return (_line(state, "callback.when"),)
        case AtStopCheck(wish=wish, resume=resume):
            return (_line(state, f"stop_check.{wish}", step=_unresolved_at(state, resume).step),)
        case Ended():
            raise ValueError("the call has ended")


def _say(
    state: CallState,
    position: Position,
    *,
    bridge: bool = False,
    again: bool = False,
    before: tuple[str, ...] = (),
) -> tuple[CallState, BotUtterance | EndOfCall]:
    """Move to `position` and put its question, or end the call when the turn budget is spent.

    `before` names lines said first (a verification answer); then only the question line follows.
    """
    if state.bot_turns + 1 >= state.limits.max_bot_turns:
        return _end(state, Outcome.turn_limit)
    lines = _lines_for(state, position, again=again)
    if before:
        lines = (*(_line(state, key, step=lines[-1].step) for key in before), lines[-1])
    if bridge:
        lines = (_line(state, "bridge.moving_on", step=lines[0].step), *lines)
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


def _end(state: CallState, outcome: Outcome) -> tuple[CallState, EndOfCall]:
    if outcome is Outcome.completed:
        middle = ("close.may_call_back",) if state.unresolved else ()
        keys = ("close.thanks", *middle, "close.verify", "close.bye")
    else:
        keys = _END_LINES[outcome]
    ended = state.model_copy(update={"position": Ended(outcome=outcome)})
    ended, utterance = _speak(ended, tuple(_line(state, key) for key in keys))
    return ended, EndOfCall(
        utterance=utterance,
        outcome=outcome,
        transcript=ended.transcript(),
        unresolved=ended.unresolved,
        callback_time=ended.callback_time,
        requested_language=ended.requested_language,
        degraded_turns=ended.degraded_turns,
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
        case AtReadBack(product=product, item="cover") | AtRestate(product=product, item="cover"):
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
        case AtSayAgain(product=product):
            return Unresolved(
                step=CallStep.teach_back, asks=Question.premium, product_id=state.plan.product_ids[product]
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


# --- the two entry points ----------------------------------------------------


def start(
    record: LoanRecord,
    language: Language,
    *,
    lender_name: str,
    call_id: str | None = None,
    limits: Limits | None = None,
) -> tuple[CallState, BotUtterance]:
    """Open a call: the bot asks for the borrower by first name and says nothing else.

    `lender_name` is spoken in the disclosure; `LoanRecord` does not carry it. Raises ValueError
    when the record cannot be called (no name, or more products than the language has ordinals).
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
        birth_year=record.borrower.dob.year,
        product_ids=tuple(p.id for p in record.products),
    )
    state = CallState(
        call_id=call_id or f"call-{record.loan_id}",
        language=language,
        lender_name=lender_name.strip(),
        plan=plan,
        limits=limits,
        position=AtIdentity(),
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
        return interpreter.interpret(text, language=state.language, expecting=expects, question=asked.text)

    heard = read(customer_text)
    other: Interpretation | None = None
    if second_reading is not None and expects in _FIGURE:
        other = read(second_reading)
        if _figure(heard) is None and _figure(other) is not None and heard.intent is not Intent.yes:
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
    if heard.intent is Intent.other_language:
        return _end(
            state.model_copy(update={"requested_language": heard.language_name}), Outcome.language_switch
        )
    if heard.intent is Intent.wants_human:
        return _end(state, Outcome.human_requested)
    if heard.intent is Intent.decline:
        return _end(state, Outcome.declined)
    if isinstance(position, AtCallbackTime):
        return _call_back(state, customer_text.strip() or None)
    if heard.intent is Intent.call_later:
        if heard.callback == "ask":
            return _say(state, AtCallbackTime())
        return _call_back(state, customer_text if heard.callback == "time" else None)
    if isinstance(position, AtStopCheck):
        return _on_stop_check(state, position, heard)
    if heard.intent in (Intent.maybe_decline, Intent.maybe_human):
        wish = "decline" if heard.intent is Intent.maybe_decline else "human"
        if state.stop_checks >= state.limits.max_stop_checks:  # asked often enough: take it as meant
            return _end(state, Outcome.declined if wish == "decline" else Outcome.human_requested)
        state = state.model_copy(update={"stop_checks": state.stop_checks + 1})
        return _say(state, AtStopCheck(wish=wish, resume=position))
    if heard.intent is Intent.asks_who and not isinstance(position, AtIdentity):
        if state.side_answers < state.limits.max_side_answers:
            state = state.model_copy(update={"side_answers": state.side_answers + 1})
            verify = "verify.before_loan" if isinstance(position, _BEFORE_LOAN) else "verify.after_loan"
            return _say(state, position, before=(verify,))
        heard = heard.model_copy(update={"intent": Intent.asks_repeat})
    return _on_reply(state, position, heard, other)


def _call_back(state: CallState, when: str | None) -> tuple[CallState, EndOfCall]:
    return _end(state.model_copy(update={"callback_time": when}), Outcome.call_back_later)


def _on_reply(state: CallState, position: _Waiting, heard: Interpretation, other: Interpretation | None):
    match position:
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
            return _on_premium(state, position, heard, other)
        case AtReadBack():
            return _on_read_back(state, position, heard, other)
        case AtRestate():
            return _on_restate(state, position, heard, other)


def _on_stop_check(state: CallState, position: AtStopCheck, heard: Interpretation):
    """ "Shall we go on?": yes goes back to the question, no ends the call. "Shall a person call you?": the reverse.

    Anything else goes back to the question, as if its last reply had been unclear.
    """
    if heard.intent is Intent.maybe_decline:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.maybe_human:
        return _end(state, Outcome.human_requested)
    if position.wish == "decline" and heard.intent is Intent.no:
        return _end(state, Outcome.declined)
    if position.wish == "human" and heard.intent is Intent.yes:
        return _end(state, Outcome.human_requested)
    return _on_reply(state, position.resume, Interpretation(intent=Intent.asks_repeat), None)


def _on_identity(state: CallState, position: AtIdentity, heard: Interpretation):
    if heard.intent is Intent.yes:
        return _say(state, AtGoAhead())
    if heard.intent in (Intent.no, Intent.wrong_person):
        return _end(state, Outcome.wrong_party)
    if position.reasked:
        return _end(state, Outcome.not_confirmed)
    return _say(state, AtIdentity(reasked=True))


def _on_go_ahead(state: CallState, position: AtGoAhead, heard: Interpretation):
    if heard.intent is Intent.yes:
        return _say(state, AtBirthYear())
    if heard.intent is Intent.no:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.wrong_person:
        return _end(state, Outcome.wrong_party)
    if position.reasked:
        return _end(state, Outcome.no_go_ahead)
    return _say(state, AtGoAhead(reasked=True))


def _on_birth_year(state: CallState, position: AtBirthYear, heard: Interpretation):
    if heard.intent is Intent.wrong_person:  # "पापा 1984 में पैदा हुए थे" names the year too
        return _end(state, Outcome.wrong_party)
    known = state.plan.birth_year
    # Two digits ("84") pass from 10 up only: "एक" and "दो" turn up in replies that give no year at
    # all ("एक बार फिर बोलिए"), and nobody gives 2002 as "दो".
    short = known % 100
    if heard.year is not None and (heard.year == known or (short >= 10 and heard.year == short)):
        return _say(state, AtRecall())
    if position.reasked:
        return _end(state, Outcome.second_check_failed)
    return _say(state, AtBirthYear(reasked=True))


def _start_products(state: CallState):
    return _say(state, _first_teach_back(state, 0))


def _on_recall(state: CallState, position: AtRecall, heard: Interpretation):
    if heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know):
        return _say(state, AtRecallFollowUp())
    if heard.intent in UNCLEAR:
        if not position.reasked:
            return _say(state, AtRecall(reasked=True))
        return _say(_mark_unresolved(state, position), AtRecallFollowUp())
    return _start_products(state)


def _on_follow_up(state: CallState, position: AtRecallFollowUp, heard: Interpretation):
    """One follow-up only: whatever the reply, the call does not ask it again."""
    if heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know):
        return _say(state, AtConsent())
    if heard.intent in UNCLEAR:
        return _say(_mark_unresolved(state, position), AtConsent())
    return _start_products(state)


def _on_question(state: CallState, position: AtTeachBack | AtConsent, heard: Interpretation, other):
    if isinstance(position, AtTeachBack):
        if heard.intent is Intent.took_nothing:  # "कौन सी चीज़? मैंने तो कुछ नहीं लिया": no more product questions
            return _say(state, AtConsent())
        if position.question is Question.premium:
            return _on_premium(state, position, heard, other)
        if (
            position.question is Question.cover
            and heard.amount_inr is not None
            and heard.intent not in UNCLEAR
        ):
            # A stated cover figure is read back and confirmed, like the premium (coordinator decision).
            return _say(state, _read_back_at(position.product, _figure(heard), 1, item="cover"))
        if position.question is Question.required_for_loan and heard.own_choice:
            product_id = state.plan.product_ids[position.product]
            state = state.model_copy(update={"own_choice": (*state.own_choice, product_id)})
    if heard.intent not in UNCLEAR:
        return _go(state, _after(state, position))
    if not position.reasked:
        return _say(state, position.model_copy(update={"reasked": True}))
    state = _mark_unresolved(state, position)
    return _go(state, _after(state, position), bridge=True)


def _on_premium(state: CallState, position: AtTeachBack | AtSayAgain, heard: Interpretation, other):
    """An answer to "how much did you pay?": read the figure back, or ask for it once more."""
    product = position.product
    first, second = _figure(heard), _figure(other)
    may_say_again = state.plan.product_ids[product] not in state.said_again
    differ = other is not None and (first is not None or second is not None) and not _same(first, second)
    if differ and may_say_again:  # never read back a figure on one model's word the first time
        update = {"said_again": (*state.said_again, state.plan.product_ids[product])}
        return _say(state.model_copy(update=update), AtSayAgain(product=product))
    figure = first or second
    if figure is not None:
        state = _with_premium(state, product, figure.high, figure.low if figure.about else None)
        return _say(state, _read_back_at(product, figure, read_backs=1))
    if heard.intent in (Intent.dont_know, Intent.no, Intent.took_nothing):
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
    if heard.intent is Intent.yes or (figure is not None and heard.only_amount):
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
