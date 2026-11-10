"""An LLM second opinion for customer turns the word lists cannot place.

Kept apart from `interpret` so the call core imports no network client.

The model is named here, not taken from the client's default: that default is chosen for extraction
after the call and can change, and this call sits inside a live turn where every second is silence
on the line. The call is cut off after `timeout_s` of wall-clock time. A failed or late call is never
passed over in silence: the turn keeps the word lists' reading, is marked `degraded` (the machine
lists it in `CallState.degraded_turns`), and the reason is logged.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from samajh.clients.errors import ClientError
from samajh.clients.llm import LlmClient, Message
from samajh.dialogue.interpret import Expecting, Intent, Interpretation, RuleInterpreter, TurnInterpreter
from samajh.types import Language

log = logging.getLogger(__name__)

# Chosen by measurement on the labelled turn set: references/pilots/W9-dialogue-report.md section 4.
FALLBACK_MODEL = "mistralai/mistral-small-3.2-24b-instruct"
# The reply is one short JSON object. The room above that is for models that spend output tokens
# on reasoning first: with 30, openai/gpt-6-luna came back cut off and empty.
MAX_TOKENS = 512
# Wall-clock limit on one LLM call inside a live turn (W9 report §6: the client's own default is 60 s
# with retries). Past it the turn is read by the word lists alone.
TIMEOUT_S = 2.5
# Calls that outlive their turn finish here in the background; their answer is dropped.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="samajh-llm-fallback")


class _Label(StrEnum):
    yes = "yes"
    no = "no"
    wrong_person = "wrong_person"
    decline = "decline"
    wants_human = "wants_human"
    dont_know = "dont_know"
    asks_repeat = "asks_repeat"
    asks_who = "asks_who"
    off_topic = "off_topic"
    answer = "answer"


class _Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: _Label


_SYSTEM = """You label one customer reply in a phone call. A lender's automated assistant asked a \
question about a loan and something bought with it; you see the question and the reply (Hindi, \
Hinglish, Tamil or Kannada, as transcribed speech).

Choose exactly one label:
- answer: the reply says anything at all about the loan, the lender, its staff, the thing bought, \
money, papers, or how the customer feels about them. Complaints are answers: "I never wanted it", \
"they forced it on me", "nobody explained", "I got no time to read", "I spoke to the manager then", \
"I refused but they added it". Vague, angry or wrong answers are still answers.
- decline: the customer wants to end or stop THIS CALL now (busy now, call later, don't call me, \
won't talk). Not wanting the product, or having refused it in the past, is NOT a decline.
- wants_human: the customer asks, now, to be put through to a person or staff member instead of \
the assistant. Having spoken to a manager or agent in the past is NOT this.
- wrong_person: the speaker says they are not the person asked for, or it is a wrong number.
- yes / no: a plain yes or no to a yes-or-no question.
- dont_know: the customer says they do not know or do not remember.
- asks_repeat: the customer did not hear or understand the question and wants it said again.
- asks_who: the customer asks who is calling, from where, or whether this call is genuine or a fraud.
- off_topic: the reply is plainly about something else altogether (the weather, chores, shopping, \
words spoken to someone else in the room) and says nothing about the loan or the thing bought.

When unsure, choose answer."""

# What the LLM's label may do, by the kind of reply expected; any other label leaves the rule reading.
# No entry ends a call on the LLM's word alone. Its "decline" and "wants_human" (and its "no" to
# "may we go on?") become a question to the customer, and it cannot say "wrong person" at all:
# on the held-out replies it took "I spoke to the branch manager about it" for a request for a
# human and "what is this about?" for a wrong number. It is never asked at the first-name question.
_OPEN = {
    _Label.dont_know: Intent.dont_know,
    _Label.asks_repeat: Intent.asks_repeat,
    _Label.asks_who: Intent.asks_who,
    _Label.off_topic: Intent.off_topic,
}
_STOP = {_Label.decline: Intent.maybe_decline, _Label.wants_human: Intent.maybe_human}
_READS_AS: dict[Expecting, dict[_Label, Intent]] = {
    Expecting.go_ahead: {
        _Label.yes: Intent.yes,
        _Label.no: Intent.maybe_decline,
        _Label.asks_repeat: Intent.asks_repeat,
        _Label.asks_who: Intent.asks_who,
    }
    | _STOP,
    Expecting.stop_check: {_Label.yes: Intent.yes, _Label.no: Intent.no} | _STOP,
    Expecting.confirmation: {
        _Label.yes: Intent.yes,
        _Label.no: Intent.no,
        _Label.asks_repeat: Intent.asks_repeat,
        _Label.dont_know: Intent.dont_know,
    }
    | _STOP,
    Expecting.birth_year: {_Label.asks_repeat: Intent.asks_repeat} | _STOP,
    Expecting.open: _OPEN | _STOP,
    Expecting.told: _OPEN | _STOP,
    Expecting.either_or: _OPEN | _STOP,
    Expecting.amount: _OPEN | _STOP,
}
# A weak stop signal from the word lists (a short "leave it", a refusal inside a first-person account)
# is put to the LLM too: "answer" clears it, a stop label keeps the one question to the customer.
_WEAK = frozenset({Intent.maybe_decline, Intent.maybe_human})


class LlmFallbackInterpreter:
    """The rules first; an LLM only for a turn the rules left as plain `said` or as a weak stop signal.

    The LLM picks a label and nothing else: amounts and years always come from the rules, and no
    label ends a call by itself (see `_READS_AS`). If the LLM call fails or takes longer than
    `timeout_s`, the turn keeps the rules' reading, marked `degraded`, and the reason is logged as a
    warning. The log line names the error and the model, never the customer's words.
    """

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

    def interpret(
        self, text: str, *, language: Language, expecting: Expecting, question: str
    ) -> Interpretation:
        first = self._rules.interpret(text, language=language, expecting=expecting, question=question)
        table = _READS_AS.get(expecting)
        settled = first.amount_inr is not None and expecting in (Expecting.amount, Expecting.confirmation)
        if table is None or settled or first.year is not None:
            return first
        if first.intent is not Intent.said and first.intent not in _WEAK:
            return first
        messages = [
            Message(role="system", content=_SYSTEM),
            Message(role="user", content=f"Question: {question}\nReply: {text}"),
        ]
        try:
            label = self._label(messages)
        except (ClientError, FutureTimeout) as error:
            log.warning(
                "LLM fallback failed, turn read by the word lists: %s from %s: %s",
                type(error).__name__,
                self._model,
                error,
            )
            return first.model_copy(update={"degraded": True})
        if first.intent in _WEAK:
            if label is _Label.answer:
                return first.model_copy(update={"intent": Intent.said})
            return first
        intent = table.get(label)
        return first if intent is None else first.model_copy(update={"intent": intent})

    def _label(self, messages: list[Message]) -> _Label:
        def ask() -> _Label:
            reply = self._llm.complete(_Verdict, messages, model=self._model, max_tokens=self._max_tokens)
            return reply.value.label

        if self._timeout_s is None:
            return ask()
        return _POOL.submit(ask).result(timeout=self._timeout_s)
