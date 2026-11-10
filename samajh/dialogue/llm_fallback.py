"""The turn classifier: an LLM that judges every customer turn the word lists are not sure of.

Kept apart from `interpret` so the call core imports no network client.

Call v2, round 2. The word lists are a fast path only. The classifier is asked:
- at the first-name and birth-year questions, about every reply that is not an exact tight match;
- at the go-ahead question, about every reply;
- later, whenever the word lists find no settled reading (`Interpretation.settled` is False).

Every label it returns is honoured (`_READS_AS`). When it fails, times out (`timeout_s`, wall clock)
or says `unclear`, the defaults are asymmetric: at the first-name and birth-year questions nobody is
confirmed; later, the turn keeps the word lists' reading marked `degraded`, and the call asks once
whether to go on. No exception from the client leaves `interpret`.

The model is named here, not taken from the client's default: that default is chosen for extraction
after the call, and this call sits inside a live turn.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from samajh.clients.llm import LlmClient, Message
from samajh.dialogue.interpret import (
    Expecting,
    Intent,
    Interpretation,
    RuleInterpreter,
    TurnInterpreter,
    affirms_or_goes_on,
    speaks_in_first_person,
)
from samajh.types import Language

log = logging.getLogger(__name__)

# Chosen by measurement on the labelled turn set: references/pilots/W9-dialogue-report.md section 4.
FALLBACK_MODEL = "mistralai/mistral-small-3.2-24b-instruct"
# The reply is one short JSON object. The room above that is for models that spend output tokens
# on reasoning first: with 30, openai/gpt-6-luna came back cut off and empty.
MAX_TOKENS = 512
# Wall-clock limit on one classifier call inside a live turn (W9 report §6).
TIMEOUT_S = 2.5
# Each classifier request runs on its own daemon thread, started at once, so no call waits in a queue
# behind another call's request, and a request whose turn gave up finishes in the background (its
# answer is dropped) without holding up later ones. How long it can live is bounded by the client
# (the server's: one send per output attempt, three output attempts, `[fallback] timeout_s` each).
# At most this many run at once in the process; past it a turn is not asked and reads as a failed
# classifier (degraded), at once, instead of waiting for a slot it would not get in time.
_MAX_LIVE = 64
_LIVE = threading.BoundedSemaphore(_MAX_LIVE)
# Calls started by `begin` and not yet read. The oldest is forgotten past this many (it still finishes
# in the background and its answer is dropped), so a begun call that is never read cannot pile up.
# The server shares one interpreter across all its calls, so this is per process too.
_PENDING_LIMIT = _MAX_LIVE


class _Saturated(RuntimeError):
    """`_MAX_LIVE` classifier requests are already running in this process."""


def _start(ask: Callable[[list[Message]], _Label], messages: list[Message]) -> Future[_Label]:
    """Run `ask(messages)` on a new daemon thread now; its outcome lands in the returned future."""
    future: Future[_Label] = Future()
    live = _LIVE  # released to the semaphore that was acquired, whatever the global is by then
    if not live.acquire(blocking=False):
        future.set_exception(_Saturated(f"{_MAX_LIVE} classifier requests already running"))
        return future

    def run() -> None:
        try:
            future.set_result(ask(messages))
        except BaseException as error:  # noqa: BLE001 - the waiter reads every failure from the future
            future.set_exception(error)
        finally:
            live.release()

    try:
        threading.Thread(target=run, name="samajh-turn-classifier", daemon=True).start()
    except BaseException:
        live.release()
        raise
    return future


class _Label(StrEnum):
    confirms_self = "confirms_self"
    wrong_person = "wrong_person"
    third_party_handoff = "third_party_handoff"
    yes = "yes"
    no = "no"
    answer = "answer"
    dont_know = "dont_know"
    asks_repeat = "asks_repeat"
    who_or_why = "who_or_why"
    refuse = "refuse"
    stop = "stop"
    human_request = "human_request"
    call_back = "call_back"
    remove_number = "remove_number"
    written_request = "written_request"
    off_topic = "off_topic"
    unclear = "unclear"


class _Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: _Label


_STAGE = {
    Expecting.identity: "first_name: the assistant asked whether it is speaking with the person it named",
    Expecting.go_ahead: "go_ahead: the assistant asked whether it may ask a few questions now",
    Expecting.birth_year: "birth_year: the assistant asked the person for their own year of birth",
    Expecting.stop_check: (
        "stop_check: the assistant asked whether to go on with the call, or whether it is speaking with the "
        "named person"
    ),
}

_SYSTEM = """You label one customer reply in a phone call. An automated customer-care assistant of a \
lender is calling a named borrower about a recent loan and anything bought with it. You see the stage, \
the assistant's question and the reply (Hindi, Hinglish, English, Tamil or Kannada, transcribed speech).

Choose exactly one label:
- confirms_self: the speaker says, in the first person, that they ARE the person named in the question \
("haan main hi bol raha hoon", "ji main Ramesh", "speaking"). At the first_name stage an acknowledgement \
("haan ji", "yes, tell me", "boliye"), or the named person's name without "I", is NOT this; use yes. A \
greeting alone ("hello", "namaste") is unclear.
- wrong_person: the speaker is someone else, or speaks of the named person in the third person ("he is \
out", "unki wife", "sahab meeting mein hain", "hamare ye", "mrs Ramesh", "ghar se bol rahi hoon"), gives \
a different name, gives SOMEONE ELSE'S year of birth, or says it is a wrong number.
- third_party_handoff: the speaker wants the call to go to someone else ("talk to my son, he handles it").
- yes / no: a plain yes or no to a yes-or-no question.
- answer: the reply answers the question in substance, including complaints and accounts of what the \
lender's staff said or did ("I refused but they added it", "the agent said call later"). At the \
birth_year stage, a year the speaker gives as THEIR OWN is an answer.
- dont_know: the speaker does not know or does not remember.
- asks_repeat: the speaker did not hear or understand and wants the question again.
- who_or_why: the speaker asks who is calling, from where, whether the call is genuine, or what it is \
about. Asking for a real person is NOT this.
- refuse: the speaker does not want to take part or answer (now or at all).
- stop: the speaker wants to end the call now, or is leaving.
- human_request: the speaker asks to talk to a human, a real person, staff or a manager now.
- call_back: the speaker asks to be called at another time, or cannot talk now (driving, busy).
- remove_number: the speaker asks not to be called again or to remove their number.
- written_request: the speaker wants this in writing (a letter, an email) instead of a call.
- off_topic: the reply is about something else altogether.
- unclear: none of the above fits, or you are not sure."""

# What each label does, by the kind of reply expected. A label missing from a stage's table leaves the
# word lists' reading; at the first-name and birth-year questions that reading never confirms.
_ENDS = {
    _Label.refuse: Intent.decline,
    _Label.stop: Intent.decline,
    _Label.human_request: Intent.wants_human,
    _Label.call_back: Intent.call_later,
    _Label.remove_number: Intent.do_not_call,
    _Label.written_request: Intent.written_request,
    _Label.wrong_person: Intent.wrong_person,
    _Label.third_party_handoff: Intent.wrong_person,
    _Label.who_or_why: Intent.asks_who,
}
_LATER = _ENDS | {
    _Label.answer: Intent.said,
    _Label.confirms_self: Intent.said,
    _Label.dont_know: Intent.dont_know,
    _Label.asks_repeat: Intent.asks_repeat,
    _Label.off_topic: Intent.off_topic,
    _Label.unclear: Intent.unclear,
}
_READS_AS: dict[Expecting, dict[_Label, Intent]] = {
    Expecting.identity: _ENDS
    | {_Label.confirms_self: Intent.yes, _Label.yes: Intent.acknowledges, _Label.asks_repeat: Intent.asks_repeat},
    Expecting.go_ahead: _ENDS
    | {_Label.yes: Intent.yes, _Label.confirms_self: Intent.yes, _Label.no: Intent.no,
       _Label.asks_repeat: Intent.asks_repeat},
    Expecting.birth_year: _ENDS | {_Label.asks_repeat: Intent.asks_repeat},
    Expecting.stop_check: {
        _Label.yes: Intent.yes,
        _Label.no: Intent.no,
        _Label.refuse: Intent.maybe_decline,
        _Label.stop: Intent.maybe_decline,
        _Label.human_request: Intent.maybe_human,
        # Round 4: the who-check ("is it you speaking?") is a stop check too.
        _Label.confirms_self: Intent.yes,
        _Label.wrong_person: Intent.wrong_person,
        _Label.third_party_handoff: Intent.wrong_person,
        _Label.remove_number: Intent.do_not_call,
        _Label.written_request: Intent.written_request,
        _Label.call_back: Intent.call_later,
    },
    Expecting.open: _LATER,
    Expecting.told: _LATER | {_Label.yes: Intent.yes, _Label.no: Intent.no},
    Expecting.either_or: _LATER,
    Expecting.amount: _LATER,
    Expecting.confirmation: _LATER | {_Label.yes: Intent.yes, _Label.no: Intent.no},
}  # fmt: skip
_WEAK = frozenset({Intent.maybe_decline, Intent.maybe_human})
_KEEPS_WEAK = frozenset(_ENDS.values()) | {Intent.said}
# At these questions a failed, late or unsure classifier confirms nobody.
_CONFIRMING = frozenset({Expecting.identity, Expecting.birth_year})


class LlmFallbackInterpreter:
    """The word lists first, as a fast path; the classifier for every reading they are not sure of."""

    def __init__(
        self,
        llm: LlmClient,
        rules: TurnInterpreter | None = None,
        *,
        model: str = FALLBACK_MODEL,
        max_tokens: int = MAX_TOKENS,
        timeout_s: float | None = TIMEOUT_S,
    ) -> None:
        self._llm = llm
        self._rules = rules if rules is not None else RuleInterpreter()
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s
        self._lock = threading.Lock()
        self._pending: OrderedDict[tuple, tuple[Future[_Label], float]] = OrderedDict()

    def begin(self, text: str, *, language: Language, expecting: Expecting, question: str) -> None:
        """Start the classifier call for this turn now, if `interpret` would ask it. Never raises.

        A later `interpret` with the same arguments uses this call and waits only for what is left of
        `timeout_s`, counted from here.
        """
        try:
            first = self._rules.interpret(text, language=language, expecting=expecting, question=question)
            if _READS_AS.get(expecting) is None or first.settled:
                return
            key = (text, language, expecting, question)
            with self._lock:
                if key in self._pending:
                    return
                future = _start(self._ask, self._messages(text, expecting, question))
                self._pending[key] = (future, time.monotonic())
                while len(self._pending) > _PENDING_LIMIT:
                    self._pending.popitem(last=False)
        except Exception:
            log.warning("turn classifier prefetch failed", exc_info=True)

    @staticmethod
    def _messages(text: str, expecting: Expecting, question: str) -> list[Message]:
        stage = _STAGE.get(
            expecting, "question: the assistant asked about the loan or what was bought with it"
        )
        return [
            Message(role="system", content=_SYSTEM),
            Message(role="user", content=f"Stage: {stage}\nQuestion: {question}\nReply: {text}"),
        ]

    def interpret(
        self, text: str, *, language: Language, expecting: Expecting, question: str
    ) -> Interpretation:
        first = self._rules.interpret(text, language=language, expecting=expecting, question=question)
        table = _READS_AS.get(expecting)
        if table is None or first.settled:
            return first
        try:
            label = self._label(text, language, expecting, question)
        except Exception as error:  # noqa: BLE001 - any client failure must leave the turn readable
            log.warning(
                "turn classifier failed, turn read by the word lists: %s from %s: %s",
                type(error).__name__,
                self._model,
                error,
            )
            return self._unjudged(first, expecting)
        if expecting is Expecting.go_ahead and label in (_Label.answer, _Label.yes, _Label.confirms_self):
            # Never falls through to a word-list end: a yes or go-on word makes it yes, else ask again.
            intent = Intent.yes if affirms_or_goes_on(text, language) else Intent.asks_repeat
            return first.model_copy(update={"intent": intent, "settled": True, "classifier_label": label.value})
        if expecting is Expecting.birth_year and label in (_Label.answer, _Label.confirms_self):
            # Read as the speaker's own year: the loose year counts. No year at all: asked again.
            return first.model_copy(update={"year": first.loose_year, "settled": True, "classifier_label": label.value})
        if label is _Label.confirms_self and not speaks_in_first_person(text, language):
            # a claim needs an "I": at the first-name question the reply is an ordinary confirmation
            label = _Label.yes if expecting is Expecting.identity else _Label.unclear
        intent = table.get(label)
        if intent is None or (expecting in _CONFIRMING and label is _Label.unclear):
            return self._unjudged(first, expecting) if expecting in _CONFIRMING else first
        if first.intent in _WEAK and intent not in _KEEPS_WEAK:
            return first  # a weak stop signal stays one question to the customer unless clearly an answer or an end
        if first.intent is Intent.yes and intent in (Intent.decline, Intent.call_later):
            intent = Intent.maybe_decline  # "busy, but ask quickly": the two readings disagree, so ask once
        # The classifier can confirm a possible takeover (an end label ends the call) but never clears it.
        update: dict = {"intent": intent, "settled": True}
        if label is not _Label.unclear:  # round 4: `unclear` is no usable label
            update["classifier_label"] = label.value
        if intent is Intent.call_later and first.callback is None:
            update["callback"] = "ask"
        return first.model_copy(update=update)

    @staticmethod
    def _unjudged(first: Interpretation, expecting: Expecting) -> Interpretation:
        """No judgment: at the confirming questions nobody is confirmed; later, the call asks once."""
        if expecting is Expecting.identity and first.intent is Intent.yes:
            first = first.model_copy(update={"intent": Intent.said})
        # An ordinary confirmation stands: that path discloses nothing before the birth year.
        return first.model_copy(update={"degraded": True, "year": None})

    def _ask(self, messages: list[Message]) -> _Label:
        reply = self._llm.complete(_Verdict, messages, model=self._model, max_tokens=self._max_tokens)
        return reply.value.label

    def _label(self, text: str, language: Language, expecting: Expecting, question: str) -> _Label:
        with self._lock:
            begun = self._pending.pop((text, language, expecting, question), None)
        if begun is None:
            messages = self._messages(text, expecting, question)
            if self._timeout_s is None:
                return self._ask(messages)
            return _start(self._ask, messages).result(timeout=self._timeout_s)
        future, started = begun
        if self._timeout_s is None:
            return future.result()
        return future.result(timeout=max(0.0, self._timeout_s - (time.monotonic() - started)))
