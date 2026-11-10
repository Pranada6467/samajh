"""RawExtraction -> Beliefs. Deterministic, and the last stop for LLM output.

What the rules can rely on afterwards:
1. An answer counts only when its quote is in a customer turn that replies to the bot turn
   tagged with that question for that product. Anything else is a gap, never a pass.
   The quote of an answer must be one or more WHOLE clauses of that reply (a clause ends at
   punctuation; quoting the whole reply always qualifies), so a quote cannot stop short of a
   "नहीं" in the same clause. Recall items, volunteered claims and concerns may quote any
   run of whole words. This code checks where a quote sits, not what it means: a wrong value
   on a complete, real clause is the extractor's error and is measured in its evaluation.
2. Amounts and terms are read by `samajh.amounts` from the customer's whole reply. The LLM's
   span only has to agree with that reading; a reply with two amounts is a gap.
3. A "yes" to a read-back confirms the premium only when the bot read back that same amount
   after the customer gave it. The premium may come from the reply to the premium question
   or from a correction made in reply to a read-back ("नहीं, पचपन हज़ार").
4. A question the bot asked cannot read as "not asked", and open recall counts only when the
   transcript has the open-recall question.
5. The consent question is open and names no product: a bot turn tagged `asks=consent` with
   no `product_id` counts as asked for every product on the record.
"""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from samajh.amounts import CLAUSE_END, Parsed, parse_amount, parse_duration_days, parse_duration_months
from samajh.types import (
    Answer,
    Beliefs,
    CallStep,
    ClaimEvidence,
    ConcernEvidence,
    DontKnow,
    Evidence,
    GapReason,
    LoanRecord,
    NotAsked,
    OpenRecall,
    ProductBeliefs,
    ProductId,
    Question,
    RawExtraction,
    RawProductAnswers,
    RecallItem,
    Speaker,
    Stated,
    Transcript,
    Turn,
    TurnId,
    Unclear,
)

_Asks = tuple[ProductId, Question, bool]  # product, question, is it the read-back
_Reader = Callable[[str, bool], int | None]  # (text, exact) -> number, or None when unsure


def _asked_by(turn: Turn, on_record: list[ProductId]) -> frozenset[_Asks]:
    """What one bot turn asks. Only the consent question may leave out the product."""
    if turn.asks is None:
        return frozenset()
    read_back = turn.step is CallStep.read_back
    if turn.product_id is not None:
        return frozenset({(turn.product_id, turn.asks, read_back)})
    if turn.asks is Question.consent:
        return frozenset((pid, turn.asks, read_back) for pid in on_record)
    return frozenset()


@dataclass(frozen=True)
class _Reply:
    """One customer turn, the bot turn it replies to, and what that bot turn asked."""

    text: str
    clauses: tuple[tuple[str, ...], ...]  # the comparison form of each clause, as words
    prompt: Turn | None
    asked: frozenset[_Asks]

    def says(self, quote: str, whole_clauses: bool) -> bool:
        """Is the quote in this turn, on word boundaries (and, if asked, on clause boundaries)?"""
        wanted = tuple(_norm(quote).split())
        if not wanted:
            return False
        if not whole_clauses:
            words = tuple(word for clause in self.clauses for word in clause)
            return any(words[k : k + len(wanted)] == wanted for k in range(len(words) - len(wanted) + 1))
        for first in range(len(self.clauses)):
            run: tuple[str, ...] = ()
            for clause in self.clauses[first:]:
                run += clause
                if len(run) >= len(wanted):
                    break
            if run == wanted:
                return True
        return False

    def is_open_recall(self) -> bool:
        return self.prompt is not None and self.prompt.step is CallStep.open_recall


def _norm(text: str) -> str:
    """Comparison form: NFC, casefolded, punctuation, symbols and format characters removed."""
    kept = []
    for ch in unicodedata.normalize("NFC", text).casefold():
        category = unicodedata.category(ch)
        if category[0] == "Z":
            kept.append(" ")
        elif category[0] not in "PS" and category != "Cf":
            kept.append(ch)
    return " ".join("".join(kept).split())


def _replies(transcript: Transcript, on_record: list[ProductId]) -> dict[TurnId, _Reply]:
    replies: dict[TurnId, _Reply] = {}
    prompt, asked = None, frozenset()
    for turn in transcript.turns:
        if turn.speaker is Speaker.bot:
            prompt, asked = turn, _asked_by(turn, on_record)
        else:
            clauses = tuple(words for part in CLAUSE_END.split(turn.text) if (words := tuple(_norm(part).split())))
            replies[turn.id] = _Reply(turn.text, clauses, prompt, asked)
    return replies


def _said(evidence: Evidence, replies: dict[TurnId, _Reply], whole_clauses: bool = False) -> _Reply | None:
    """The customer turn that contains the quote, if the quote is really there."""
    reply = replies.get(evidence.turn_id)
    return reply if reply and reply.says(evidence.quote, whole_clauses) else None


def _rupees(text: str, exact: bool) -> int | None:
    result = parse_amount(text, exact=exact)
    return result.rupees if isinstance(result, Parsed) else None


def _months(text: str, exact: bool) -> int | None:
    return parse_duration_months(text, exact=exact)


def _days(text: str, exact: bool) -> int | None:
    return parse_duration_days(text, exact=exact)


def _ground(
    answer: Answer, accepted: frozenset[_Asks], was_asked: bool, replies: dict[TurnId, _Reply]
) -> Answer:
    """Keep an answer only when it quotes whole clauses of a reply to one of the `accepted` questions."""
    match answer:
        case NotAsked():
            return Unclear() if was_asked else answer
        case Unclear():
            return answer
        case DontKnow(evidence=ev) | Stated(evidence=ev):
            reply = _said(ev, replies, whole_clauses=True)
            if reply and reply.asked & accepted:
                return answer
            return Unclear(reason=GapReason.quote_not_grounded, evidence=ev)
    raise TypeError(f"not an Answer: {answer!r}")


def _read(answer: Answer[str], read: _Reader, replies: dict[TurnId, _Reply]) -> Answer[int]:
    """Read the number from the customer's whole reply; the LLM's span must agree with it."""
    match answer:
        case Stated(value=span, evidence=ev):
            heard = read(replies[ev.turn_id].text, False)
            if heard is None or heard != read(span, True):
                return Unclear(reason=GapReason.value_not_parsed, evidence=ev)
            return Stated[int](value=heard, evidence=ev)
        case _:
            return answer


def _product_beliefs(
    raw: RawProductAnswers,
    ungrounded: list[Evidence],
    replies: dict[TurnId, _Reply],
    asked: frozenset[_Asks],
) -> ProductBeliefs:
    def ground(answer: Answer, question: Question, read_back: bool = False) -> Answer:
        asks = (raw.product_id, question, read_back)
        return _ground(answer, frozenset({asks}), asks in asked, replies)

    premium_asked = (raw.product_id, Question.premium, False)
    premium_read_back = (raw.product_id, Question.premium, True)
    premium = _ground(
        raw.premium, frozenset({premium_asked, premium_read_back}), premium_asked in asked, replies
    )
    premium = _read(premium, _rupees, replies)
    readback = ground(raw.premium_readback, Question.premium, read_back=True)
    if isinstance(premium, Stated) and isinstance(readback, Stated):
        read_back_turn = replies[readback.evidence.turn_id].prompt
        if not readback.value:
            premium = Unclear(reason=GapReason.readback_rejected, evidence=readback.evidence)
        elif (
            readback.evidence.turn_id <= premium.evidence.turn_id
            or read_back_turn is None
            or _rupees(read_back_turn.text, False) != premium.value
        ):
            # The customer confirmed some other amount, or confirmed before giving this one:
            # neither the amount nor the "yes" can be relied on.
            premium = readback = Unclear(reason=GapReason.readback_mismatch, evidence=readback.evidence)

    claims: list[ClaimEvidence] = []
    for claim in raw.volunteered_claims:
        if _said(claim.evidence, replies):
            claims.append(claim)
        else:
            ungrounded.append(claim.evidence)

    return ProductBeliefs(
        product_id=raw.product_id,
        kind=ground(raw.kind, Question.kind),
        premium_readback=readback,
        payment_source=ground(raw.payment_source, Question.payment_source),
        required_for_loan=ground(raw.required_for_loan, Question.required_for_loan),
        provider_choice_offered=ground(raw.provider_choice_offered, Question.provider_choice),
        cancel_allowed=ground(raw.cancel_allowed, Question.cancel_window),
        consent_given=ground(raw.consent_given, Question.consent),
        consent_method=ground(raw.consent_method, Question.consent),
        feature_probe=ground(raw.feature_probe, Question.features),
        volunteered_claims=tuple(claims),
        premium_inr=premium,
        cover_inr=_read(ground(raw.cover, Question.cover), _rupees, replies),
        term_months=_read(ground(raw.term, Question.term), _months, replies),
        cancel_window_days=_read(ground(raw.cancel_window, Question.cancel_window), _days, replies),
        ungrounded=tuple(ungrounded),
    )


def to_beliefs(raw: RawExtraction, record: LoanRecord, transcript: Transcript) -> Beliefs:
    """Ground every quote in the transcript and read amounts and terms.

    The transcript must tag each bot question with `asks` and `product_id`; without tags no
    answer can be tied to its question and every answer becomes a gap.

    Raises ValueError when the three inputs do not describe the same call, or when the
    extraction names a product that is not on the record. The caller re-runs the extraction.
    """
    if raw.call_id != transcript.call_id or transcript.loan_id != record.loan_id:
        raise ValueError("extraction, transcript and record are not the same call")
    on_record = [p.id for p in record.products]
    raw_by_id = {p.product_id: p for p in raw.products}
    named = [p.product_id for p in raw.products] + [i.product_id for i in raw.recall.items if i.product_id]
    if len(raw_by_id) != len(raw.products) or not set(named) <= set(on_record):
        raise ValueError("extraction names a duplicate product or one that is not on the record")

    replies = _replies(transcript, on_record)
    bot_turns = [t for t in transcript.turns if t.speaker is Speaker.bot]
    asked = frozenset().union(*(_asked_by(t, on_record) for t in bot_turns))
    recall_asked = raw.recall.asked and any(t.step is CallStep.open_recall for t in bot_turns)

    def in_recall(evidence: Evidence) -> bool:
        reply = _said(evidence, replies)
        return recall_asked and reply is not None and reply.is_open_recall()

    items: list[RecallItem] = []
    case_ungrounded: list[Evidence] = []
    product_ungrounded: dict[ProductId, list[Evidence]] = {pid: [] for pid in on_record}
    for item in raw.recall.items:
        if in_recall(item.evidence):
            said_amount = item.amount_text and replies[item.evidence.turn_id].says(item.amount_text, False)
            amount = _rupees(item.amount_text, True) if said_amount else None
            items.append(
                RecallItem(
                    evidence=item.evidence, kind=item.kind, amount_inr=amount, product_id=item.product_id
                )
            )
        elif item.product_id is None:
            case_ungrounded.append(item.evidence)
        else:
            product_ungrounded[item.product_id].append(item.evidence)

    answer = raw.recall.answer
    if answer is not None and not in_recall(answer):
        case_ungrounded.append(answer)
        answer = None

    concerns: list[ConcernEvidence] = []
    for concern in raw.sale_concerns:
        if _said(concern.evidence, replies):
            concerns.append(concern)
        else:
            case_ungrounded.append(concern.evidence)

    return Beliefs(
        call_id=raw.call_id,
        loan_id=record.loan_id,
        language=transcript.language,
        recall=OpenRecall(asked=recall_asked, answer=answer, items=tuple(items)),
        products=tuple(
            _product_beliefs(
                raw_by_id.get(pid, RawProductAnswers(product_id=pid)), product_ungrounded[pid], replies, asked
            )
            for pid in on_record
        ),
        sale_concerns=tuple(concerns),
        ungrounded=tuple(case_ungrounded),
    )
