"""Transcript -> RawExtraction: small LLM calls per customer reply, then deterministic assembly.

The answer call records the answer to the question the bot asked. The screening call reads the
same reply for things said in passing: beliefs about the product and concerns about the sale.
The change check, on a reply to a checked question that has two or more clauses or holds a word
that may take an answer back (`Reply.has_change_marker`), asks separately
whether the customer gave an answer and then corrected or withdrew it (`Change`). It sees what
the answer call sees and not the answer call's reading, so it is a second, independent look. A
correction whose final answer stands keeps the earlier words (the clause runs code resolves from
the check's clause numbers) in `also`; otherwise the stated answer is taken away. It adds no
conflict and never creates or changes a value. A failed check makes the reply's stated answers
`Unclear(extraction_failed)`. On a reply of one clause a correction cannot be pointed at (the two
clause runs would overlap), so anything but `none` there makes its stated answers unusable. A
one-clause reply whose answer is followed by a who-knows, forgot or don't-know tail ("41300 kya
pata", "बीमा था भूल गया क्या था") is taken back by code whatever the check said
(`Reply.has_take_back_tail`): the check's prompt reads such doubt as leaning to the answer.

Code, not the model, decides which question a reply answers, which turn a quote comes from and
which product an answer belongs to. The model sees one question and one reply and returns enums,
clause numbers and spans (`samajh.extract._wire`). Each one is resolved against that reply
(`_ground`); a field whose clause number or span is not there becomes `Unclear(quote_not_grounded)`.

The model never chooses the words kept as evidence. An answer quotes the customer's whole reply,
and a recall item, a claim or a concern quotes the whole clauses around its span, so no quote can
stop short of a "not" that the model left out. The two identity checks are never sent to the
model: the right-party question names the borrower and the second check asks a birth year.

The calls for one transcript run in parallel threads and are assembled in call order. A call that
fails makes the fields of its reply `Unclear(extraction_failed)`, never the whole call a failure,
and that holds whichever asking of a question failed: a failure is never hidden by another reply.
A question asked more than once keeps its last stated answer (the other usable replies go in its
`also`); only stated answers that are incompatible are kept as an `AnswerConflict`: an "I don't
know" before or after an answer, a restatement, and amounts within tolerance of each other are not.
Every open-recall reply counts; the last reply that is a denial is kept (the rules judge its order
against what was named).

A premium the bot read back without asking it (the customer gave it in open recall) is carried
from the open-recall reply that `samajh.rules.normalise.carried_premiums` names, decided from the
transcript alone: the whole reply is its quote and the parser's amount span its value.
It is carried only when that reply's change check said `none`, or the reply got no check (one
clause and no marker word); after a correction, a withdrawal or a failed call nothing is carried.
"""

import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from itertools import groupby
from typing import Protocol, TypeVar

from pydantic import BaseModel

from samajh.amounts import has_doubt_word, is_loan_tenure
from samajh.clients.errors import BadResponse, LlmOutputInvalid, RateLimited, ServerError, TransportError
from samajh.clients.llm import LlmResult, Message
from samajh.extract._ground import Found, Reply, amount_reading, days, months
from samajh.extract._prompt import change_messages, messages, screen_messages
from samajh.extract._wire import (
    SCHEMA,
    CancelReply,
    Change,
    ChangeReply,
    ConsentReply,
    FeaturesReply,
    FrequencyReply,
    KindReply,
    PaymentReply,
    PremiumReply,
    ReadbackReply,
    RecallReply,
    ScreenReply,
    SlotKind,
    SpanReply,
    Status,
    WireReply,
    YesNoReply,
)
from samajh.rules.checks import (
    AMOUNT_TOLERANCE_PERCENT,
    APPROX_AMOUNT_TOLERANCE_PERCENT,
    CANCEL_TOLERANCE_DAYS,
)
from samajh.rules.clauses import KIND_ON_RECORD
from samajh.rules.normalise import ZERO_PREMIUM, CarriedPremium, carried_premiums
from samajh.types import (
    Answer,
    AnswerConflict,
    CallStep,
    ClaimEvidence,
    ConcernEvidence,
    DontKnow,
    Evidence,
    FeatureClaim,
    GapReason,
    KindClaim,
    LoanRecord,
    ProductId,
    Question,
    RawExtraction,
    RawOpenRecall,
    RawProductAnswers,
    RawRecallItem,
    Speaker,
    Stated,
    Transcript,
    Turn,
    TurnId,
    Unclear,
)

T = TypeVar("T", bound=BaseModel)

# Room for a reasoning model to think before it answers. At 800 a hard reply ("ज़रूरी था, ऐसा तो
# किसी ने नहीं कहा।") came back from openai/gpt-6-luna cut off and empty, which fails the whole call;
# the same request used 863 completion tokens when allowed 4000 (measured 2026-11-10).
_MAX_TOKENS = 4000
# A reply this short cannot state a belief or a concern, so it is not screened.
_SCREEN_MIN_WORDS = 3
# A customer who misdescribes the one product on record still named it: these kinds may be
# matched to a product that no recall item describes correctly.
_MISDESCRIBED = frozenset({KindClaim.deposit, KindClaim.investment, KindClaim.other})
_IDENTITY = frozenset({CallStep.right_party_check, CallStep.second_check})
# One reply's call failed in a way that says nothing about the next reply. Anything else (the
# spend cap, a bad key, a bad configuration) would fail every call, so it is raised.
_ONE_CALL_FAILED = (LlmOutputInvalid, BadResponse, TransportError, RateLimited, ServerError)


class Llm(Protocol):
    """The part of `samajh.clients.llm.LlmClient` the extractor uses."""

    def complete(
        self,
        schema: type[T],
        messages: Sequence[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LlmResult[T]: ...


class ExtractionFailed(Exception):
    """No longer raised: a failed call now makes its fields `Unclear(extraction_failed)`.

    Kept only until `eval/text_path/run.py` stops importing it.
    """

    def __init__(self, call_id: str, turn_id: TurnId, kind: SlotKind, reason: str) -> None:
        self.call_id, self.turn_id, self.kind = call_id, turn_id, kind
        super().__init__(f"call {call_id}, turn {turn_id} ({kind}): {reason}")


@dataclass(frozen=True)
class Slot:
    """One customer reply and what the bot turn before it asked."""

    turn: Turn
    question: str
    kind: SlotKind
    products: tuple[ProductId, ...]  # the product asked about; every product when none was named
    step: CallStep | None = None  # the step of the bot turn; None when the customer spoke first


@dataclass
class SlotTrace:
    """What one LLM call cost and how its spans fared. `fields` name wire fields of that call."""

    turn_id: TurnId
    kind: SlotKind
    screen: bool  # the screening call for this reply, not the answer call
    model: str
    usd: float
    seconds: float
    cache_hit: bool
    generation_id: str | None
    prompt_tokens: int
    completion_tokens: int
    spans: int = 0  # spans the model returned
    not_in_reply: list[str] = field(default_factory=list)  # fields whose span was not in the reply
    pointers: int = 0  # answers the model backed with clause numbers
    bad_pointers: list[str] = field(default_factory=list)  # fields with no clause number, or one out of range
    inconsistent: list[str] = field(default_factory=list)  # "stated" without a value or a span
    # The error type when the call gave no output; `model` is then the one asked for ("" for the
    # client's default) and `usd` is 0.0 although failed attempts may have been paid for.
    failed: str | None = None
    check: bool = False  # the change check for this reply (then `screen` is False)
    change: str | None = None  # the check's label ("none", "corrected", "withdrawn") when it gave one


@dataclass(frozen=True)
class Extraction:
    raw: RawExtraction
    slots: tuple[SlotTrace, ...]


def _slot_kind(prompt: Turn | None, on_record: Sequence[ProductId]) -> SlotKind:
    if prompt is None:
        return SlotKind.other
    if prompt.step is CallStep.open_recall:
        return SlotKind.recall
    if prompt.asks is None:
        return SlotKind.other
    if prompt.product_id is None:
        return SlotKind.consent if prompt.asks is Question.consent else SlotKind.other
    if prompt.product_id not in on_record:
        raise ValueError(f"turn {prompt.id} asks about {prompt.product_id}, which is not on the record")
    if prompt.step is CallStep.read_back:
        read_back = {Question.premium: SlotKind.readback, Question.cover: SlotKind.cover_readback}
        return read_back.get(prompt.asks, SlotKind.other)
    return SlotKind(prompt.asks.value)


def slots(transcript: Transcript, record: LoanRecord) -> tuple[Slot, ...]:
    """Every customer turn, paired with the bot turn it replies to, as the rule engine pairs them."""
    on_record = tuple(p.id for p in record.products)
    found: list[Slot] = []
    prompt: Turn | None = None
    for turn in transcript.turns:
        if turn.speaker is Speaker.bot:
            prompt = turn
            continue
        kind = _slot_kind(prompt, on_record)
        asked_about = prompt.product_id if prompt and prompt.product_id else None
        products = (asked_about,) if asked_about and kind is not SlotKind.other else on_record
        step = prompt.step if prompt else None
        found.append(Slot(turn, prompt.text if prompt else "", kind, products, step))
    return tuple(found)


class _Grounder:
    """Turns the wire fields of one call into answers, counting every span and clause pointer."""

    def __init__(self, slot: Slot, trace: SlotTrace) -> None:
        self.reply = Reply(slot.turn.text)
        self.turn_id = slot.turn.id
        self.trace = trace
        # Code decides the marker, not the model. A doubt about exactness ("ठीक से याद नहीं") is a hedge
        # too, except for a cover figure: `checks.cover` reads `hedged` as a tier input, so that
        # marker stays as it was there (P5 fix round 2: marker only, no tier change).
        exactness = slot.kind not in (SlotKind.cover, SlotKind.cover_readback)
        self.hedged = has_doubt_word(slot.turn.text, exactness=exactness)
        # Wire field -> (first, last) clause the stated answer came from: the clauses the model
        # pointed at, or for a span the clauses the grounded span sits in. Read by the change check.
        self.where: dict[str, tuple[int, int]] = {}

    def whole(self) -> Evidence:
        return self.evidence(self.reply.whole())

    def find(self, name: str, span: str | None) -> Found | None:
        if span is None or not span.strip():
            return None
        self.trace.spans += 1
        found = self.reply.find(span)
        if found is None:
            self.trace.not_in_reply.append(name)
        return found

    def evidence(self, quote: str) -> Evidence:
        return Evidence(quote=quote, turn_id=self.turn_id)

    def pointed(self, name: str, status: Status, value: object, clauses: tuple[int, ...]) -> Answer:
        """An enum or yes/no answer, or an "I do not know".

        The model must point at a clause of the reply that carries the answer. The evidence kept
        is the whole reply, not the clause the model picked.
        """
        whole = self.whole()
        if status is Status.unclear:
            return Unclear(evidence=whole)
        if status is Status.stated and value is None:
            self.trace.inconsistent.append(name)
            return Unclear(evidence=whole)
        self.trace.pointers += 1
        if self.reply.cover(clauses) is None:
            self.trace.bad_pointers.append(name)
            return Unclear(reason=GapReason.quote_not_grounded)
        if status is Status.dont_know:
            return DontKnow(evidence=whole)
        self.where[name] = (min(clauses), max(clauses))
        return Stated(value=value, evidence=whole, hedged=self.hedged)

    def run(self, name: str, clauses: tuple[int, ...]) -> tuple[int, int] | None:
        """(first, last) clause of a run the model pointed at; None, counted, when it is not in the reply."""
        self.trace.pointers += 1
        if self.reply.cover(clauses) is None:
            self.trace.bad_pointers.append(name)
            return None
        return min(clauses), max(clauses)

    def spoken(self, name: str, status: Status, span: str | None, clauses: tuple[int, ...]) -> Answer:
        """An amount or a duration: the value is the span, as it stands in the reply."""
        if status is not Status.stated:
            return self.pointed(name, status, None, clauses)
        if not (span and span.strip()):
            self.trace.inconsistent.append(name)
            return Unclear(evidence=self.whole())
        found = self.find(name, span)
        if found is None:
            return Unclear(reason=GapReason.quote_not_grounded)
        self.where[name] = found.numbers
        return Stated(value=found.words, evidence=self.whole(), hedged=self.hedged)


Usable = Stated | DontKnow
_FAILED = GapReason.extraction_failed


def _amount(text: str) -> tuple[int, int, int] | None:
    """(low, high, tolerance percent) of a spoken amount: the approximate tolerance for a hedge or range."""
    if text == ZERO_PREMIUM:
        return 0, 0, AMOUNT_TOLERANCE_PERCENT
    reading = amount_reading(text)
    if reading is None:
        return None
    low, high, approximate = reading
    return low, high, APPROX_AMOUNT_TOLERANCE_PERCENT if approximate else AMOUNT_TOLERANCE_PERCENT


def _term(text: str) -> object:
    return "loan" if is_loan_tenure(text) else months(text)


def _compatible(name: str, a: Stated, b: Stated) -> bool:
    """Two stated answers to one question that a reviewer would not call contradictory.

    Amounts: within tolerance of each other (10% when either is hedged or a range, else 1%).
    Durations: the same number of months, or of days within a day. An amount or duration that
    cannot be read is never a conflict: the rules refuse it on its own. Anything else: equal.
    """
    if name in ("premium", "cover"):
        x, y = _amount(a.value), _amount(b.value)
        if x is None or y is None:
            return True
        tol = max(x[2], y[2])
        return x[0] * (100 - tol) <= y[1] * 100 and y[0] * (100 - tol) <= x[1] * 100
    if name == "term":
        x, y = _term(a.value), _term(b.value)
        return x is None or y is None or "loan" in (x, y) or x == y
    if name == "cancel_window":
        x, y = days(a.value), days(b.value)
        return x is None or y is None or abs(x - y) <= CANCEL_TOLERANCE_DAYS
    if isinstance(a.value, tuple):
        return frozenset(a.value) == frozenset(b.value)
    return a.value == b.value


def _changes(name: str, heard: Sequence[Answer]) -> list[Evidence]:
    """Stated answers incompatible with the one before them, the first included. One entry: no conflict."""
    kept: list[Stated] = []
    for answer in heard:
        if isinstance(answer, Stated) and (not kept or not _compatible(name, answer, kept[-1])):
            kept.append(answer)
    return [answer.evidence for answer in kept]


def _resolve(heard: Sequence[Answer]) -> Answer:
    """The field's answer from every reply to every asking, in call order.

    A failed model call on any asking -> `Unclear(extraction_failed)`: never dropped. Else the
    last stated answer, holding the other usable replies in `also`; else the last "I don't know";
    else the last unusable reply.
    """
    failed = next((a for a in heard if isinstance(a, Unclear) and a.reason is _FAILED), None)
    if failed is not None:
        return failed
    stated = [a for a in heard if isinstance(a, Stated)]
    if stated:
        last = stated[-1]
        also = tuple(a.evidence for a in heard if isinstance(a, Usable) and a is not last)
        return last.model_copy(update={"also": also}) if also else last
    dont_know = [a for a in heard if isinstance(a, DontKnow)]
    return dont_know[-1] if dont_know else heard[-1]


class _Assembly:
    """Collects grounded answers for the whole call."""

    def __init__(self, on_record: Sequence[ProductId]) -> None:
        # Every reply to each field, in call order, since a read-back last replaced it.
        self.heard: dict[ProductId, dict[str, list[Answer]]] = {pid: {} for pid in on_record}
        self.claims: dict[ProductId, list[ClaimEvidence]] = {pid: [] for pid in on_record}
        self.concerns: list[ConcernEvidence] = []
        self.recall_answer: Evidence | None = None
        self.recall_denial: Evidence | None = None
        self.recall_items: list[tuple[RawRecallItem, bool]] = []  # item, was its span in the reply
        self.unscreened: list[Evidence] = []

    def put(self, slot: Slot, name: str, answer: Answer, replace: bool = False) -> None:
        """Remember a reply to a field. `replace` is the read-back: the new reply is taken whatever
        it is and the earlier ones are forgotten, so a premium corrected at the read-back is not a
        conflict and the last read-back reply stands alone."""
        for pid in slot.products:
            heard = self.heard[pid].setdefault(name, [])
            if replace:
                heard.clear()
            heard.append(answer)

    def answers(self, pid: ProductId) -> dict[str, Answer]:
        return {name: _kept_correction(_resolve(heard), heard) for name, heard in self.heard[pid].items()}

    def conflicts(self, pid: ProductId) -> tuple[AnswerConflict, ...]:
        """Per question: stated answers that differ across askings, in call order.

        A correction inside one reply is never a conflict (see `check`).
        """
        found = []
        for kind, names in _FIELDS.items():
            if kind in _READ_BACK or not names:
                continue  # the last read-back reply stands alone; recall and other fill no field
            differing: set[Evidence] = set()
            for name in names:
                changes = _changes(name, self.heard[pid].get(name, ()))
                if len(changes) > 1:
                    differing.update(changes)
            if differing:
                answers = tuple(sorted(differing, key=lambda e: e.turn_id))
                found.append(AnswerConflict(question=Question(kind.value), answers=answers))
        return tuple(found)

    def take(self, slot: Slot, wire: WireReply, g: _Grounder) -> None:
        _TAKE[slot.kind](self, slot, wire, g)

    def screen(self, slot: Slot, wire: ScreenReply, g: _Grounder) -> None:
        """Claims and concerns voiced in passing.

        A span that is in the reply is kept as the whole clauses around it. A span that is not
        in the reply stays as the model wrote it: the rule engine then records an evidence gap,
        so a concern the model garbled can never end in `clear`.
        """
        for concern in wire.concerns:
            found = g.find("concerns", concern.span)
            quote = found.clauses if found else concern.span
            self._add(self.concerns, ConcernEvidence(concern=concern.concern, evidence=g.evidence(quote)))
        if slot.kind is SlotKind.features:
            return  # the money-back probe already has the customer's beliefs as its answer
        for claim in wire.claims:
            found = g.find("claims", claim.span)
            quote = found.clauses if found else claim.span
            for pid in slot.products:
                said = ClaimEvidence(claim=FeatureClaim(claim.claim.value), evidence=g.evidence(quote))
                self._add(self.claims[pid], said)

    @staticmethod
    def _add(items: list, item: object) -> None:
        if item not in items:
            items.append(item)

    def check(
        self,
        slot: Slot,
        wire: ChangeReply | None,
        g: _Grounder,
        where: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        """Apply the change check to what the answer call took from this reply. `wire` None: the check failed.

        `where` is the answer call's record of the clauses each stated answer came from. Only a
        stated answer is touched: `DontKnow` and `Unclear` stand whatever the check says, and so
        does a rejected read-back. The check never gives a value.
        - withdrawn, or a failed check: every stated answer of the reply is unusable.
        - corrected: an answer stands only when both readings agree on the clause that holds it:
          the answer call's clauses start after the check's `first_clauses` and end inside its
          `final_clauses` (the two runs resolve and do not overlap); clauses between the two runs
          hold only the correction words. The earlier words (the `first_clauses`
          run, whole clauses) go into its `also` for the reviewer; no conflict is added. Any other
          answer of the reply is unusable. A read-back "yes" taken back is always unusable.
        """
        if slot.kind is SlotKind.recall:
            self._recall_check(slot, wire, g)
            return
        if wire is None:
            self._unstate(slot, Unclear(reason=_FAILED, evidence=g.whole()))
            return
        g.trace.change = wire.change.value
        if wire.change is Change.none:
            return
        if (
            wire.change is Change.withdrawn
            and slot.kind is SlotKind.provider_choice
            and self._told_no(slot)
            and g.reply.ends_in_dont_know_tail()
        ):
            # "नहीं बताया पता नहीं": not knowing follows from not being told, and keeping the "no"
            # errs toward a referral (P5 fix round 2). A "yes" and every other question: as below.
            return
        first = g.run("first_clauses", wire.first_clauses)
        final = g.run("final_clauses", wire.final_clauses) if wire.change is Change.corrected else None
        if first and final and first[1] >= final[0] and final[1] >= first[0]:
            g.trace.bad_pointers.append("final_clauses")  # the two runs overlap
            final = None
        if final is None or first is None or slot.kind in _READ_BACK:
            self._unstate(slot, Unclear(evidence=g.whole()))
            return
        earlier = g.evidence(g.reply.cover(first))
        for name in _FIELDS[slot.kind]:
            at = (where or {}).get(_WIRE_FIELD[name])
            # The answer call may also point at the correction words between the two runs ("अरे
            # नहीं"): its prompt asks for the clause with any "not" that belongs to the answer.
            stands = at is not None and first[1] < at[0] and final[0] <= at[1] <= final[1]
            for pid in slot.products:
                heard = self.heard[pid].get(name, [])
                for k, answer in enumerate(heard):
                    if not (isinstance(answer, Stated) and answer.evidence.turn_id == slot.turn.id):
                        continue
                    if stands:
                        heard[k] = answer.model_copy(update={"also": (*answer.also, earlier)})
                    else:
                        heard[k] = Unclear(evidence=g.whole())

    def _unstate(self, slot: Slot, instead: Unclear) -> bool:
        """Replace each stated answer taken from this reply by `instead`. True when there was one.

        For a read-back only a "yes" is replaced: a rejection stands as the first reading gave it.
        """
        taken = False
        for name in _FIELDS[slot.kind]:
            for pid in slot.products:
                heard = self.heard[pid].get(name, [])
                for k, answer in enumerate(heard):
                    if not (isinstance(answer, Stated) and answer.evidence.turn_id == slot.turn.id):
                        continue
                    if slot.kind in _READ_BACK and answer.value is not True:
                        continue
                    heard[k] = instead
                    taken = True
        return taken

    def _recall_check(self, slot: Slot, wire: ChangeReply | None, g: _Grounder) -> None:
        """A recall reply that named something and then took it back or named another thing.

        The items said first are dropped and the reply is listed as unscreened, so the case cannot
        end `clear` on it; when the first clauses do not resolve, every item of the reply is dropped.
        A change whose first answer named no item (a denial, then a thing named) drops nothing and
        is left alone. A failed check lists the reply as unscreened and keeps the items. A reply
        that named nothing is left alone.
        """
        here = [k for k, (item, _) in enumerate(self.recall_items) if item.evidence.turn_id == slot.turn.id]
        if not here:
            return
        if wire is not None:
            g.trace.change = wire.change.value
            if wire.change is Change.none:
                return
            first = g.run("first_clauses", wire.first_clauses)
            if wire.change is Change.corrected:
                g.run("final_clauses", wire.final_clauses)  # counted only: code keeps no answer from it
            dropped = {k for k in here if first is None or self._within(g.reply, k, first)}
            if not dropped:
                return  # what was taken back named nothing ("nothing", then a thing): the items stand
            self.recall_items = [x for k, x in enumerate(self.recall_items) if k not in dropped]
        self._add(self.unscreened, g.whole())

    def tail(self, slot: Slot, g: _Grounder) -> None:
        """A one-clause reply whose answer is followed by a who-knows, forgot or don't-know tail
        (`_tail_takes_back`): taken back, whatever the change check said. Stated answers become
        unusable; open recall drops the reply's items and lists it as unscreened.

        Except "nobody told me" on the provider-choice question (P5 fix round): "किसी ने नहीं बताया,
        पता नहीं" is one answer, since not knowing follows from not being told, and keeping the "no"
        errs toward a referral (`bundled_no_choice_told`), never toward `clear`."""
        if slot.kind is SlotKind.provider_choice and self._told_no(slot):
            return
        if slot.kind is SlotKind.recall:
            here = {
                k for k, (item, _) in enumerate(self.recall_items) if item.evidence.turn_id == slot.turn.id
            }
            if here:
                self.recall_items = [x for k, x in enumerate(self.recall_items) if k not in here]
                self._add(self.unscreened, g.whole())
            return
        self._unstate(slot, Unclear(evidence=g.whole()))

    def _told_no(self, slot: Slot) -> bool:
        """This reply's provider-choice answer is a stated "no, nobody told me"."""
        return any(
            isinstance(a, Stated) and a.value is False and a.evidence.turn_id == slot.turn.id
            for pid in slot.products
            for a in self.heard[pid].get("provider_choice_offered", [])
        )

    def _within(self, reply: Reply, k: int, run: tuple[int, int]) -> bool:
        """Does recall item `k` (or its span, if not found in the reply) lie inside the clause run?"""
        item, grounded = self.recall_items[k]
        found = reply.find(item.evidence.quote) if grounded else None
        return found is None or (run[0] <= found.numbers[0] and found.numbers[1] <= run[1])

    def blank(self, slot: Slot) -> None:
        """Silence: asked, and nothing was said."""
        self._no_answer(slot, Unclear())

    def failed(self, slot: Slot, screen: bool) -> None:
        """The call for this reply gave no output.

        Open recall has no field that can say "not read", so its reply is listed with the
        unscreened ones: the rules then cannot take the missing items for "named nothing".
        """
        whole = Evidence(quote=Reply(slot.turn.text).whole(), turn_id=slot.turn.id)
        if screen or slot.kind is SlotKind.recall:
            self._add(self.unscreened, whole)
        else:
            self._no_answer(slot, Unclear(reason=GapReason.extraction_failed, evidence=whole))

    def _no_answer(self, slot: Slot, answer: Unclear) -> None:
        for name in _FIELDS[slot.kind]:
            self.put(slot, name, answer, replace=name.endswith("_readback"))

    def _kind(self, slot: Slot, wire: KindReply, g: _Grounder) -> None:
        self.put(slot, "kind", g.pointed("kind", wire.status, wire.kind, wire.clauses))

    def _payment(self, slot: Slot, wire: PaymentReply, g: _Grounder) -> None:
        self.put(slot, "payment_source", g.pointed("source", wire.status, wire.source, wire.clauses))

    def _frequency(self, slot: Slot, wire: FrequencyReply, g: _Grounder) -> None:
        answer = g.pointed("frequency", wire.status, wire.frequency, wire.clauses)
        self.put(slot, "payment_frequency", answer)

    def _yes_no(self, slot: Slot, wire: YesNoReply, g: _Grounder) -> None:
        (name,) = _FIELDS[slot.kind]
        self.put(slot, name, g.pointed("yes", wire.status, wire.yes, wire.clauses))

    def _span(self, slot: Slot, wire: SpanReply, g: _Grounder) -> None:
        (name,) = _FIELDS[slot.kind]
        self.put(slot, name, g.spoken("span", wire.status, wire.span, wire.clauses))

    def _premium(self, slot: Slot, wire: PremiumReply, g: _Grounder) -> None:
        """An amount, or "it cost nothing" (`free`), recorded as `ZERO_PREMIUM` with the whole reply
        as its evidence. The words the model gives for it must be in the reply. Whether 0 stands
        (no other amount, nothing said about the loan or another payer) is decided in
        `samajh.rules.normalise`, from the reply alone."""
        if not (wire.free and wire.status is Status.stated):
            self.put(slot, "premium", g.spoken("span", wire.status, wire.span, wire.clauses))
            return
        if not (wire.span and wire.span.strip()):
            g.trace.inconsistent.append("free")
            self.put(slot, "premium", Unclear(evidence=g.whole()))
            return
        found = g.find("span", wire.span)
        if found is None:
            self.put(slot, "premium", Unclear(reason=GapReason.quote_not_grounded))
            return
        g.where["span"] = found.numbers
        self.put(slot, "premium", Stated(value=ZERO_PREMIUM, evidence=g.whole(), hedged=g.hedged))

    def _readback(self, slot: Slot, wire: ReadbackReply, g: _Grounder) -> None:
        self._read_back(slot, wire, g, "premium")

    def _cover_readback(self, slot: Slot, wire: ReadbackReply, g: _Grounder) -> None:
        self._read_back(slot, wire, g, "cover")

    def _read_back(self, slot: Slot, wire: ReadbackReply, g: _Grounder, field: str) -> None:
        answer = g.pointed("confirms", wire.status, wire.confirms, wire.clauses)
        self.put(slot, f"{field}_readback", answer, replace=True)
        rejected = isinstance(answer, Stated) and answer.value is False
        if rejected and wire.corrected_amount_span:
            corrected = g.spoken("corrected_amount_span", Status.stated, wire.corrected_amount_span, ())
            self.put(slot, field, corrected, replace=True)

    def _cancel(self, slot: Slot, wire: CancelReply, g: _Grounder) -> None:
        allowed = g.pointed("allowed", wire.allowed_status, wire.allowed, wire.allowed_clauses)
        self.put(slot, "cancel_allowed", allowed)
        window = g.spoken("window_span", wire.window_status, wire.window_span, wire.window_clauses)
        self.put(slot, "cancel_window", window)

    def _consent(self, slot: Slot, wire: ConsentReply, g: _Grounder) -> None:
        given = g.pointed("given", wire.given_status, wire.given, wire.given_clauses)
        self.put(slot, "consent_given", given)
        method = g.pointed("method", wire.method_status, wire.method, wire.method_clauses)
        self.put(slot, "consent_method", method)

    def _features(self, slot: Slot, wire: FeaturesReply, g: _Grounder) -> None:
        claims = tuple(dict.fromkeys(wire.claims))
        if wire.status is not Status.stated and claims:
            # "I do not know" together with a belief is two answers: neither is kept.
            g.trace.inconsistent.append("claims")
            self.put(slot, "feature_probe", Unclear(evidence=g.whole()))
            return
        self.put(slot, "feature_probe", g.pointed("claims", wire.status, claims, wire.clauses))

    def carry(self, turn: Turn, carried: CarriedPremium, pid: ProductId) -> None:
        """The premium the customer gave in this open-recall reply, read back later and never asked.

        Put in call order, so a correction at the read-back replaces it like any premium.
        """
        evidence = Evidence(quote=Reply(turn.text).whole(), turn_id=turn.id)
        heard = self.heard[pid].setdefault("premium", [])
        heard.append(
            Stated(value=carried.span, evidence=evidence, hedged=has_doubt_word(turn.text, exactness=True))
        )

    def _recall(self, slot: Slot, wire: RecallReply, g: _Grounder) -> None:
        """Every recall reply counts: the first answer is kept, and the last reply that denies."""
        self.recall_answer = self.recall_answer or g.whole()
        if wire.took_nothing and not wire.items:
            self.recall_denial = g.whole()
        for item in wire.items:
            found = g.find("items", item.span)
            amount = g.find("items.amount_span", item.amount_span) if found else None
            raw = RawRecallItem(
                evidence=g.evidence(found.clauses if found else item.span),
                kind=item.kind,
                amount_text=amount.words if amount else None,
            )
            self.recall_items.append((raw, found is not None))


_TAKE: dict[SlotKind, Callable] = {
    SlotKind.recall: _Assembly._recall,
    SlotKind.kind: _Assembly._kind,
    SlotKind.premium: _Assembly._premium,
    SlotKind.readback: _Assembly._readback,
    SlotKind.cover_readback: _Assembly._cover_readback,
    SlotKind.payment_source: _Assembly._payment,
    SlotKind.payment_frequency: _Assembly._frequency,
    SlotKind.required_for_loan: _Assembly._yes_no,
    SlotKind.provider_choice: _Assembly._yes_no,
    SlotKind.cover: _Assembly._span,
    SlotKind.term: _Assembly._span,
    SlotKind.cancel_window: _Assembly._cancel,
    SlotKind.features: _Assembly._features,
    SlotKind.consent: _Assembly._consent,
}

_READ_BACK = frozenset({SlotKind.readback, SlotKind.cover_readback})

# The wire field of the answer call that each RawProductAnswers field is read from.
_WIRE_FIELD: dict[str, str] = {
    "kind": "kind",
    "premium": "span",
    "premium_readback": "confirms",
    "cover_readback": "confirms",
    "payment_source": "source",
    "payment_frequency": "frequency",
    "required_for_loan": "yes",
    "provider_choice_offered": "yes",
    "cover": "span",
    "term": "span",
    "cancel_allowed": "allowed",
    "cancel_window": "window_span",
    "feature_probe": "claims",
    "consent_given": "given",
    "consent_method": "method",
}


def _kept_correction(resolved: Answer, heard: Sequence[Answer]) -> Answer:
    """The resolved answer with the earlier words of a correction inside its own reply kept in `also`.

    `_resolve` rebuilds `also` from the other askings; the self-correction quote (an `also` entry
    from the answer's own turn, put there by `_Assembly.check`) must survive that.
    """
    if not isinstance(resolved, Stated):
        return resolved
    own = [
        e for a in heard if isinstance(a, Stated) and a.evidence == resolved.evidence
        for e in a.also if e.turn_id == resolved.evidence.turn_id
    ]  # fmt: skip
    missing = tuple(e for e in own if e not in resolved.also)
    return resolved.model_copy(update={"also": (*missing, *resolved.also)}) if missing else resolved


# The RawProductAnswers fields each question fills.
_FIELDS: dict[SlotKind, tuple[str, ...]] = {
    SlotKind.recall: (),
    SlotKind.kind: ("kind",),
    SlotKind.premium: ("premium",),
    SlotKind.readback: ("premium_readback",),
    SlotKind.cover_readback: ("cover_readback",),
    SlotKind.payment_source: ("payment_source",),
    SlotKind.payment_frequency: ("payment_frequency",),
    SlotKind.required_for_loan: ("required_for_loan",),
    SlotKind.provider_choice: ("provider_choice_offered",),
    SlotKind.cover: ("cover",),
    SlotKind.term: ("term",),
    SlotKind.cancel_window: ("cancel_allowed", "cancel_window"),
    SlotKind.features: ("feature_probe",),
    SlotKind.consent: ("consent_given", "consent_method"),
    SlotKind.other: (),
}


def attribute(items: Sequence[tuple[RawRecallItem, bool]], record: LoanRecord) -> tuple[RawRecallItem, ...]:
    """Decide which product on record each thing named in open recall is. Deterministic.

    The model never sees the record, so it cannot do this. An item the customer describes as the
    kind on record takes the first product not yet named, one item per product. After that, if
    exactly one product is still unnamed and exactly one remaining item is a misdescription
    (deposit, investment, other), they are paired: the customer named the product under another
    name. Everything else stays unmatched, and the rules treat it as off the record. An item
    whose span was not in the reply is never matched.
    """
    unnamed = list(record.products)
    matched: dict[int, ProductId] = {}
    for k, (item, grounded) in enumerate(items):
        product = next((p for p in unnamed if grounded and item.kind is KIND_ON_RECORD[p.kind]), None)
        if product is not None:
            matched[k] = product.id
            unnamed.remove(product)
    misdescribed = [
        k
        for k, (item, grounded) in enumerate(items)
        if grounded and k not in matched and item.kind in _MISDESCRIBED
    ]
    if len(misdescribed) == 1 and len(unnamed) == 1:
        matched[misdescribed[0]] = unnamed[0].id
    return tuple(item.model_copy(update={"product_id": matched.get(k)}) for k, (item, _) in enumerate(items))


class _Call(Enum):
    """The LLM calls made about one reply."""

    answer = "answer"
    screen = "screen"
    check = "check"


def _ask(
    llm: Llm, slot: Slot, transcript: Transcript, model: str | None, call: _Call
) -> tuple[WireReply | ScreenReply | ChangeReply | None, SlotTrace]:
    """One LLM call about one reply. No output when it failed."""
    language, question, reply = transcript.language, slot.question, slot.turn.text
    schema: type[BaseModel]
    if call is _Call.screen:
        schema, request = ScreenReply, screen_messages(language, question, reply)
    elif call is _Call.check:
        schema, request = ChangeReply, change_messages(slot.kind, language, question, reply)
    else:
        schema, request = SCHEMA[slot.kind], messages(slot.kind, language, question, reply)
    trace = SlotTrace(
        turn_id=slot.turn.id, kind=slot.kind, screen=call is _Call.screen, model=model or "", usd=0.0,
        seconds=0.0, cache_hit=False, generation_id=None, prompt_tokens=0, completion_tokens=0,
        check=call is _Call.check,
    )  # fmt: skip
    started = time.monotonic()
    try:
        result = llm.complete(schema, request, model=model, max_tokens=_MAX_TOKENS)
    except _ONE_CALL_FAILED as exc:
        trace.failed = type(exc).__name__  # the name only: the message may quote the reply
        trace.seconds = time.monotonic() - started
        return None, trace
    trace.model, trace.usd, trace.seconds = result.model, result.usd, time.monotonic() - started
    trace.cache_hit, trace.generation_id = result.cache_hit, result.generation_id
    trace.prompt_tokens, trace.completion_tokens = result.prompt_tokens, result.completion_tokens
    return result.value, trace


def _plan(transcript: Transcript, record: LoanRecord) -> Iterator[tuple[Slot, _Call | None]]:
    """Each reply's calls in call order (None: silence, no call).

    The change check goes with every answer call on a reply of two or more clauses, and on a reply
    of one clause that holds a marker word (`Reply.has_change_marker`), open recall included (its
    result is used only when the reply named something). Speech-to-text can leave a withdrawal
    unpunctuated, so the clause count alone would let it through. A one-clause reply with no marker
    gets no check.
    """
    for slot in slots(transcript, record):
        if slot.step in _IDENTITY:
            continue
        reply = Reply(slot.turn.text)
        if reply.blank:
            yield slot, None
            continue
        if slot.kind is not SlotKind.other:
            yield slot, _Call.answer
            if _needs_check(reply):
                yield slot, _Call.check
        if reply.word_count >= _SCREEN_MIN_WORDS:
            yield slot, _Call.screen


def _needs_check(reply: Reply) -> bool:
    """Two or more clauses, or a word that may take an answer back."""
    return len(reply.clauses()) >= 2 or reply.has_change_marker()


# Questions whose answer is itself an amount, a duration or a date: a word such as "कितना" or "कब"
# in the reply is about the answer, so it never exempts a tail.
_ASKS_A_QUANTITY = frozenset(
    {SlotKind.recall, SlotKind.premium, SlotKind.readback, SlotKind.cover, SlotKind.cover_readback,
     SlotKind.term, SlotKind.cancel_window}
)  # fmt: skip


def _tail_takes_back(reply: Reply, kind: SlotKind) -> bool:
    """One clause, and a who-knows, forgot or don't-know tail after the answer ("41300 kya pata").

    On a question that does not ask for a quantity, a reply that names another detail ("बीमा है रकम
    याद नहीं") is not taken back: the tail is about that detail.
    """
    exempt = kind not in _ASKS_A_QUANTITY
    return len(reply.clauses()) == 1 and reply.has_take_back_tail(other_detail_exempts=exempt)


def _carries(slot: Slot, got: dict[_Call, tuple[object, SlotTrace]]) -> bool:
    """May this reply's premium be carried forward? Only when its answer call gave output and its
    change check said `none`, or the reply needed no check (one clause, no marker word). After a
    correction, a withdrawal or a failed call nothing is carried, and the read-back then leaves the
    premium a gap. A reply that needed a check and has none is never carried, nor is a one-clause
    reply with a take-back tail (`_tail_takes_back`), whatever its check said.
    """
    answer = got.get(_Call.answer)
    if answer is None or answer[0] is None or _tail_takes_back(Reply(slot.turn.text), slot.kind):
        return False
    if _Call.check not in got:
        return not _needs_check(Reply(slot.turn.text))
    check = got[_Call.check][0]
    return isinstance(check, ChangeReply) and check.change is Change.none


def extract_traced(
    transcript: Transcript,
    record: LoanRecord,
    llm: Llm,
    *,
    model: str | None = None,
    max_workers: int = 8,
) -> Extraction:
    """`extract`, plus what each LLM call cost, which spans were not in the reply and which calls failed.

    Raises ValueError when the transcript is not a call about this loan, and the client's error
    when no call can succeed (`CapExceeded`, `AuthError`, `ConfigError`).
    """
    if transcript.loan_id != record.loan_id:
        raise ValueError(f"transcript is for loan {transcript.loan_id}, record is {record.loan_id}")
    on_record = tuple(p.id for p in record.products)
    plan = list(_plan(transcript, record))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(_ask, llm, slot, transcript, model, call) for slot, call in plan if call is not None
        ]
        try:
            asked = iter([future.result() for future in futures])
        except BaseException:
            pool.shutdown(cancel_futures=True)
            raise

    assembly = _Assembly(on_record)
    carried = {pid: c for pid, c in carried_premiums(transcript).items() if c.reply is not None}
    traces: list[SlotTrace] = []
    for _, group in groupby(plan, key=lambda planned: planned[0].turn.id):
        calls = list(group)
        slot = calls[0][0]
        if calls[0][1] is None:
            assembly.blank(slot)
            continue
        got: dict[_Call, tuple[object, SlotTrace]] = {}
        for _, call in calls:
            got[call] = next(asked)
            traces.append(got[call][1])
        if _carries(slot, got):
            for pid, c in carried.items():
                if c.reply == slot.turn.id:
                    assembly.carry(slot.turn, c, pid)
        if _Call.answer in got:
            wire, trace = got[_Call.answer]
            if wire is None:
                assembly.failed(slot, screen=False)
            else:
                grounder = _Grounder(slot, trace)
                assembly.take(slot, wire, grounder)
                if _Call.check in got:
                    check, check_trace = got[_Call.check]
                    assembly.check(slot, check, _Grounder(slot, check_trace), grounder.where)
                if _tail_takes_back(grounder.reply, slot.kind):
                    assembly.tail(slot, grounder)
        if _Call.screen in got:
            wire, trace = got[_Call.screen]
            if wire is None:
                assembly.failed(slot, screen=True)
            else:
                assembly.screen(slot, wire, _Grounder(slot, trace))

    recall_asked = any(t.speaker is Speaker.bot and t.step is CallStep.open_recall for t in transcript.turns)
    raw = RawExtraction(
        call_id=transcript.call_id,
        recall=RawOpenRecall(
            asked=recall_asked,
            answer=assembly.recall_answer,
            items=attribute(assembly.recall_items, record),
            denial=assembly.recall_denial,
        ),
        products=tuple(
            RawProductAnswers(
                product_id=pid,
                volunteered_claims=tuple(assembly.claims[pid]),
                conflicts=assembly.conflicts(pid),
                **assembly.answers(pid),
            )
            for pid in on_record
        ),
        sale_concerns=tuple(assembly.concerns),
        unscreened=tuple(assembly.unscreened),
    )
    return Extraction(raw=raw, slots=tuple(traces))


def extract(
    transcript: Transcript,
    record: LoanRecord,
    llm: Llm,
    *,
    model: str | None = None,
    max_workers: int = 8,
) -> RawExtraction:
    """What the customer said on the call, as enums and their own words. The one LLM step.

    The model is shown one bot question and one customer reply at a time, and nothing from the
    lender's record. A quote that is not in the reply never becomes an answer.
    """
    return extract_traced(transcript, record, llm, model=model, max_workers=max_workers).raw
