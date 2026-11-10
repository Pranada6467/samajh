"""The Samajh call as a state machine (DESIGN.md section 5). Pure: no audio, no network, no clock.

    start(record, language, lender_name=...) -> (CallState, BotUtterance)
    step(state, customer_text)                -> (CallState, BotUtterance | EndOfCall)

`CallState.position` says which reply the bot is waiting for; the interpreter turns the reply into
an `Intent` (the event); `step` maps (position, intent) to the next position and the next lines.

The state holds a `CallPlan`, not the loan record: the first name, the birth year for the second
check, and the product ids. Nothing else from the record survives `start`, so no line the bot
speaks can depend on a value the call is testing (kind, premium, payment source, cover, term,
cancel window, consent). The only figures the bot ever says are ones the customer said first.

A plain refusal or request for a human ends the call at once. A weak signal of either (a short
"leave it", a refusal the customer may be quoting from the sale, or an LLM's guess) is checked with
one question and never argued with. That question is asked `Limits.max_stop_checks` times a call
at most; a further signal ends the call.

An amount turn may come with a second transcript of the same audio (DESIGN.md section 15, item 16).
`samajh.amounts.cross_check` says whether the two agree. Either way the figure is read back before
the call closes; where they differ the call acts on the reading that brings a figure the customer
has not just heard or rejected, and keeps the other in `CallState.second_readings`.

Every position allows one re-ask at most, read-backs per product are capped, and the whole call
is capped at `Limits.max_bot_turns`, so a call always ends.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from samajh.amounts import Agreed, cross_check, format_inr, parse_amount, spoken_amount
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
    not_confirmed = "not_confirmed"  # nobody confirmed the first name
    no_go_ahead = "no_go_ahead"  # no clear yes after the disclosure
    second_check_failed = "second_check_failed"
    declined = "declined"
    human_requested = "human_requested"
    turn_limit = "turn_limit"


class Limits(Frozen):
    max_bot_turns: int = Field(default=60, ge=1)  # utterances, including the closing one
    max_read_backs: int = Field(default=3, ge=1)  # read-backs of one product's premium
    max_stop_checks: int = Field(default=2, ge=0)  # times a call asks "do you want to stop?"


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


class AtTeachBack(Frozen):
    at: Literal["teach_back"] = "teach_back"
    product: int  # index into CallPlan.product_ids
    question: Question
    reasked: bool = False


class AtConsent(Frozen):
    at: Literal["consent"] = "consent"
    reasked: bool = False


class AtReadBack(Frozen):
    """The bot read `amount_inr` back and waits for yes, no, or another figure."""

    at: Literal["read_back"] = "read_back"
    product: int
    amount_inr: int
    read_backs: int  # read-backs of this product so far, this one included


class AtRestate(Frozen):
    """The customer rejected a read-back without giving a figure; the bot asked for the right one."""

    at: Literal["restate"] = "restate"
    product: int
    read_backs: int
    rejected_inr: int | None = None  # the figure the customer said was wrong


class Ended(Frozen):
    at: Literal["ended"] = "ended"
    outcome: Outcome


_Question = AtRecall | AtTeachBack | AtConsent
_Waiting = AtIdentity | AtGoAhead | AtBirthYear | _Question | AtReadBack | AtRestate


class AtStopCheck(Frozen):
    """A reply may have meant "stop" or "get me a person"; the bot asked, and will go back to `resume` on a no.

    Only a weak signal comes here (a short "leave it", or an LLM's guess). A plain refusal or a plain
    request for a human ends the call at once, with no question.
    """

    at: Literal["stop_check"] = "stop_check"
    wish: Literal["decline", "human"]
    resume: Annotated[_Waiting, Field(discriminator="at")]


Position = Annotated[_Waiting | AtStopCheck | Ended, Field(discriminator="at")]


class StatedPremium(Frozen):
    product_id: ProductId
    amount_inr: int  # the customer's latest figure, never the record's


class Unresolved(Frozen):
    """A question the call moved past without a usable answer. The case needs a human."""

    step: CallStep
    asks: Question | None = None
    product_id: ProductId | None = None


class SecondReading(Frozen):
    """The other transcript of a customer turn that was read twice. `Turn.text` is the one the call acted on."""

    turn_id: TurnId
    text: str
    agreed: bool  # `samajh.amounts.cross_check`: both transcripts gave the same single amount


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
    stop_checks: int = 0  # times the bot has asked "do you want to stop?"
    second_readings: tuple[SecondReading, ...] = ()

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


_RULES = RuleInterpreter()

_TOLD = frozenset({Question.required_for_loan, Question.provider_choice, Question.cancel_window})
_FIGURE = frozenset({Expecting.amount, Expecting.confirmation})  # replies that may carry a rupee figure
_END_LINES: dict[Outcome, tuple[str, ...]] = {
    Outcome.wrong_party: ("end.neutral",),
    Outcome.not_confirmed: ("end.neutral",),
    Outcome.no_go_ahead: ("end.neutral",),
    Outcome.second_check_failed: ("end.check_failed",),
    Outcome.declined: ("end.declined",),
    Outcome.human_requested: ("end.human",),
    Outcome.turn_limit: ("close.thanks", "close.may_call_back", "close.bye"),
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
        case AtTeachBack(question=Question.premium) | AtRestate():
            return Expecting.amount
        case AtTeachBack(question=question) if question in _TOLD:
            return Expecting.told
        case AtRecall() | AtTeachBack() | AtConsent():
            return Expecting.open
        case AtReadBack():
            return Expecting.confirmation
        case AtStopCheck():
            return Expecting.stop_check
        case Ended():
            raise ValueError("the call has ended")


# --- building what the bot says ----------------------------------------------


def _line(
    state: CallState, key: str, *, product: int | None = None, step: CallStep | None = None, **slots: str
) -> Line:
    spec = LINES[key]
    wanted = {"first_name": state.plan.first_name, "lender": state.lender_name} | slots
    filled = {name: wanted[name] for name in spec.slots}
    asks_product = spec.asks is not None and spec.asks is not Question.consent
    return Line(
        key=key,
        slots=filled,
        text=load_prompts(state.language).render(key, **filled),
        step=step or spec.step,
        asks=spec.asks,
        product_id=state.plan.product_ids[product] if asks_product and product is not None else None,
    )


def _ordinal(state: CallState, product: int) -> str:
    return load_prompts(state.language).ordinal(product)


def _lines_for(state: CallState, position: Position, *, again: bool = False) -> tuple[Line, ...]:
    """The lines that put `position`'s question. `again` marks a read-back repeated after an unclear reply."""
    several = len(state.plan.product_ids) > 1
    match position:
        case AtIdentity(reasked=reasked):
            return (_line(state, "right_party.reask" if reasked else "right_party.ask"),)
        case AtGoAhead(reasked=True):
            return (_line(state, "disclosure.reask"),)
        case AtGoAhead():
            keys = ("who", "not_sales", "recording", "rights", "verify", "never_ask", "go_ahead")
            return tuple(_line(state, f"disclosure.{key}") for key in keys)
        case AtBirthYear(reasked=reasked):
            return (_line(state, "second_check.reask" if reasked else "second_check.ask"),)
        case AtRecall(reasked=True):
            return (_line(state, "open_recall.reask"),)
        case AtRecall():
            return (_line(state, "context.loan"), _line(state, "open_recall.ask"))
        case AtTeachBack(product=product, question=question, reasked=reasked):
            ask = _line(state, f"{question.value}.{'reask' if reasked else 'ask'}", product=product)
            if question is not PRODUCT_QUESTIONS[0] or reasked:
                return (ask,)
            if several:
                return (_line(state, "teach_back.intro_nth", ordinal=_ordinal(state, product)), ask)
            return (_line(state, "teach_back.intro"), ask)
        case AtConsent(reasked=reasked):
            return (_line(state, "consent.reask" if reasked else "consent.ask"),)
        case AtReadBack(product=product, amount_inr=amount, read_backs=read_backs):
            said = {
                "amount_words": spoken_amount(amount, state.language),
                "amount_digits": format_inr(amount),
            }
            ask = _line(
                state, "read_back.reconfirm" if again else "read_back.confirm", product=product, **said
            )
            if several and read_backs == 1 and not again:
                return (_line(state, "read_back.intro_nth", ordinal=_ordinal(state, product)), ask)
            return (ask,)
        case AtRestate(product=product):
            return (_line(state, "read_back.restate", product=product),)
        case AtStopCheck(wish=wish, resume=resume):
            return (_line(state, f"stop_check.{wish}", step=_unresolved_at(state, resume).step),)
        case Ended():
            raise ValueError("the call has ended")


def _say(
    state: CallState, position: Position, *, bridge: bool = False, again: bool = False
) -> tuple[CallState, BotUtterance | EndOfCall]:
    """Move to `position` and put its question, or end the call when the turn budget is spent."""
    if state.bot_turns + 1 >= state.limits.max_bot_turns:
        return _end(state, Outcome.turn_limit)
    lines = _lines_for(state, position, again=again)
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
        keys = (
            ("close.thanks", "close.may_call_back", "close.bye")
            if state.unresolved
            else ("close.thanks", "close.bye")
        )
    else:
        keys = _END_LINES[outcome]
    ended = state.model_copy(update={"position": Ended(outcome=outcome)})
    ended, utterance = _speak(ended, tuple(_line(state, key) for key in keys))
    return ended, EndOfCall(
        utterance=utterance, outcome=outcome, transcript=ended.transcript(), unresolved=ended.unresolved
    )


# --- order of the questions --------------------------------------------------


def _first_teach_back(state: CallState, product: int) -> Position:
    if product < len(state.plan.product_ids):
        return AtTeachBack(product=product, question=PRODUCT_QUESTIONS[0])
    return AtConsent()


def _after_question(state: CallState, position: _Question) -> Position | None:
    """The position that follows a question, or None when the call is ready to close."""
    match position:
        case AtRecall():
            return _first_teach_back(state, 0)
        case AtTeachBack(product=product, question=question):
            k = PRODUCT_QUESTIONS.index(question) + 1
            if k < len(PRODUCT_QUESTIONS):
                return AtTeachBack(product=product, question=PRODUCT_QUESTIONS[k])
            return _first_teach_back(state, product + 1)
        case AtConsent():
            return _read_back_from(state, 0)


def _read_back_from(state: CallState, product: int) -> Position | None:
    """The first read-back at or after `product`: only products whose premium the customer stated."""
    for k in range(product, len(state.plan.product_ids)):
        amount = state.premium_of(k)
        if amount is not None:
            return AtReadBack(product=k, amount_inr=amount, read_backs=1)
    return None


def _go(
    state: CallState, position: Position | None, *, bridge: bool = False
) -> tuple[CallState, BotUtterance | EndOfCall]:
    return _end(state, Outcome.completed) if position is None else _say(state, position, bridge=bridge)


def _with_premium(state: CallState, product: int, amount_inr: int) -> CallState:
    product_id = state.plan.product_ids[product]
    kept = tuple(p for p in state.premiums if p.product_id != product_id)
    return state.model_copy(
        update={"premiums": (*kept, StatedPremium(product_id=product_id, amount_inr=amount_inr))}
    )


def _unresolved_at(state: CallState, position: _Waiting) -> Unresolved:
    """The call step, question and product a position stands for."""
    match position:
        case AtIdentity():
            return Unresolved(step=CallStep.right_party_check)
        case AtGoAhead():
            return Unresolved(step=CallStep.disclosure)
        case AtBirthYear():
            return Unresolved(step=CallStep.second_check)
        case AtRecall():
            return Unresolved(step=CallStep.open_recall)
        case AtTeachBack(product=product, question=question):
            return Unresolved(
                step=CallStep.teach_back, asks=question, product_id=state.plan.product_ids[product]
            )
        case AtConsent():
            return Unresolved(step=CallStep.consent_check, asks=Question.consent)
        case AtReadBack(product=product) | AtRestate(product=product):
            return Unresolved(
                step=CallStep.read_back, asks=Question.premium, product_id=state.plan.product_ids[product]
            )


def _mark_unresolved(state: CallState, position: _Waiting) -> CallState:
    return state.model_copy(update={"unresolved": (*state.unresolved, _unresolved_at(state, position))})


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
    and is ignored elsewhere.
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
    if second_reading is not None and expects in _FIGURE:
        agreed = isinstance(cross_check(parse_amount(customer_text), parse_amount(second_reading)), Agreed)
        if not agreed and _brings_no_figure(position, heard):
            other = read(second_reading)
            if not _brings_no_figure(position, other):
                heard, customer_text, second_reading = other, second_reading, customer_text
        spare = SecondReading(turn_id=turn_id, text=second_reading, agreed=agreed)
        state = state.model_copy(update={"second_readings": (*state.second_readings, spare)})
    reply = Turn(id=turn_id, speaker=Speaker.customer, step=asked.step, text=customer_text)
    state = state.model_copy(update={"turns": (*state.turns, reply)})

    if heard.intent is Intent.wants_human:
        return _end(state, Outcome.human_requested)
    if heard.intent is Intent.decline:
        return _end(state, Outcome.declined)
    if isinstance(position, AtStopCheck):
        return _on_stop_check(state, position, heard)
    if heard.intent in (Intent.maybe_decline, Intent.maybe_human):
        wish = "decline" if heard.intent is Intent.maybe_decline else "human"
        if state.stop_checks >= state.limits.max_stop_checks:  # asked often enough: take it as meant
            return _end(state, Outcome.declined if wish == "decline" else Outcome.human_requested)
        state = state.model_copy(update={"stop_checks": state.stop_checks + 1})
        return _say(state, AtStopCheck(wish=wish, resume=position))
    return _on_reply(state, position, heard)


def _brings_no_figure(position: Position, heard: Interpretation) -> bool:
    """Does this reading leave the bot with nothing new to read back?

    A plain yes to a read-back stands. Otherwise a reading counts only if it holds a figure, and not
    the one the customer has just been read (`AtReadBack`) or has just rejected (`AtRestate`).
    """
    match position:
        case AtReadBack(amount_inr=stale):
            if heard.intent is Intent.yes:
                return False
        case AtRestate(rejected_inr=stale):
            pass
        case _:
            stale = None
    return heard.amount_inr is None or heard.amount_inr == stale


def _on_reply(state: CallState, position: _Waiting, heard: Interpretation):
    match position:
        case AtIdentity():
            return _on_identity(state, position, heard)
        case AtGoAhead():
            return _on_go_ahead(state, position, heard)
        case AtBirthYear():
            return _on_birth_year(state, position, heard)
        case AtRecall() | AtTeachBack() | AtConsent():
            return _on_question(state, position, heard)
        case AtReadBack():
            return _on_read_back(state, position, heard)
        case AtRestate():
            return _on_restate(state, position, heard)


def _on_stop_check(state: CallState, position: AtStopCheck, heard: Interpretation):
    """Yes ends the call. Anything else goes back to the question, as if its last reply had been unclear."""
    if heard.intent is Intent.maybe_decline:
        return _end(state, Outcome.declined)
    if heard.intent is Intent.maybe_human:
        return _end(state, Outcome.human_requested)
    if heard.intent is Intent.yes:
        return _end(state, Outcome.declined if position.wish == "decline" else Outcome.human_requested)
    return _on_reply(state, position.resume, Interpretation(intent=Intent.asks_repeat))


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
    if heard.intent is Intent.wrong_person:  # "I am his wife, he was born in 1984" names the year too
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


def _on_question(state: CallState, position: _Question, heard: Interpretation):
    wants_amount = isinstance(position, AtTeachBack) and position.question is Question.premium
    if wants_amount and heard.amount_inr is not None:
        state = _with_premium(state, position.product, heard.amount_inr)
        answered = True
    elif wants_amount:
        answered = heard.intent is Intent.dont_know
    else:
        answered = heard.intent not in UNCLEAR
    if answered:
        return _go(state, _after_question(state, position))
    if not position.reasked:
        return _say(state, position.model_copy(update={"reasked": True}))
    state = _mark_unresolved(state, position)
    return _go(state, _after_question(state, position), bridge=True)


def _on_read_back(state: CallState, position: AtReadBack, heard: Interpretation):
    more = position.read_backs < state.limits.max_read_backs
    after = position.product + 1
    read = position.amount_inr
    # "शायद पचपन हज़ार", "not fifty two, fifty five thousand": no one figure, but not the one read back.
    names_another = heard.amount_inr is None and any(figure != read for figure in heard.figures)
    if heard.amount_inr is not None and heard.amount_inr != read:
        state = _with_premium(state, position.product, heard.amount_inr)
        if more:
            return _say(
                state,
                position.model_copy(
                    update={"amount_inr": heard.amount_inr, "read_backs": position.read_backs + 1}
                ),
            )
    elif heard.intent is Intent.no or (names_another and heard.intent is not Intent.yes):
        if more:
            restate = AtRestate(product=position.product, read_backs=position.read_backs, rejected_inr=read)
            return _say(state, restate)
    elif heard.intent is Intent.yes or heard.amount_inr == read:
        return _go(state, _read_back_from(state, after))
    elif more and heard.intent is not Intent.dont_know:  # "I don't know" is recorded, not pressed
        return _say(state, position.model_copy(update={"read_backs": position.read_backs + 1}), again=True)
    state = _mark_unresolved(state, position)
    return _go(state, _read_back_from(state, after), bridge=True)


def _on_restate(state: CallState, position: AtRestate, heard: Interpretation):
    if heard.amount_inr is not None:
        state = _with_premium(state, position.product, heard.amount_inr)
        return _say(
            state,
            AtReadBack(
                product=position.product, amount_inr=heard.amount_inr, read_backs=position.read_backs + 1
            ),
        )
    state = _mark_unresolved(state, position)
    return _go(state, _read_back_from(state, position.product + 1), bridge=True)
