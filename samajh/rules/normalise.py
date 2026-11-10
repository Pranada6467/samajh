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
   span only has to agree with that reading, and must itself read exactly: a span is never
   trimmed, so a word next to the number that may change it ("सारे तीन लाख") makes it a gap.
   An amount said with a word of doubt or as a narrow range is read by `parse_approx_amount`
   and marked `approximate` (a range keeps its lower end in `low`). A term said as the loan's
   own ("जब तक लोन चलेगा") is the record's loan tenure, or a `not_comparable` gap without one.
3. A "yes" to a read-back confirms the premium only when the bot read back that same amount
   after the customer gave it: for a range, the same two ends. The premium may come from the
   reply to the premium question or from a correction made in reply to a read-back.
4. A question the bot asked cannot read as "not asked", and open recall counts only when the
   transcript has the open-recall question.
5. The consent question is open and names no product: a bot turn tagged `asks=consent` with
   no `product_id` counts as asked for every product on the record.
6. Conflicting answers, a denial in open recall and unscreened replies are kept only where
   their quotes are in the call; a quote that is not becomes an evidence gap.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from samajh.amounts import (
    CLAUSE_END,
    Approximate,
    Parsed,
    is_loan_tenure,
    parse_amount,
    parse_approx_amount,
    parse_duration_days,
    parse_duration_months,
)
from samajh.types import (
    Answer,
    AnswerConflict,
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
            clauses = tuple(
                words for part in CLAUSE_END.split(turn.text) if (words := tuple(_norm(part).split()))
            )
            replies[turn.id] = _Reply(turn.text, clauses, prompt, asked)
    return replies


def _said(evidence: Evidence, replies: dict[TurnId, _Reply], whole_clauses: bool = False) -> _Reply | None:
    """The customer turn that contains the quote, if the quote is really there."""
    reply = replies.get(evidence.turn_id)
    return reply if reply and reply.says(evidence.quote, whole_clauses) else None


_TOKEN = re.compile(r"\S+")


def widen(reply: str, span: str) -> str:
    """The span as it stands in the reply, with one more word on each side within its clause.

    What the amount and duration parsers read: a fraction word ("सारहे") or a unit word the model
    left out of its span is still seen, and makes the parse refuse instead of being dropped. A span
    that is not a run of whole words of the reply is returned as it is.
    """
    ends = [m.start() for m in CLAUSE_END.finditer(reply)]
    words = [
        (m.start(), m.end(), w, sum(e < m.start() for e in ends))
        for m in _TOKEN.finditer(reply)
        for w in _norm(m.group()).split()
    ]
    wanted = _norm(span).split()
    forms = [w for _, _, w, _ in words]
    for k in range(len(forms) - len(wanted) + 1):
        if wanted and forms[k : k + len(wanted)] == wanted:
            first, last = k, k + len(wanted) - 1
            if first > 0 and words[first - 1][3] == words[first][3]:
                first -= 1
            if last + 1 < len(words) and words[last + 1][3] == words[last][3]:
                last += 1
            return reply[words[first][0] : words[last][1]]
    return span


def _rupees(text: str, exact: bool) -> int | None:
    result = parse_amount(text, exact=exact)
    return result.rupees if isinstance(result, Parsed) else None


def _ends(text: str, exact: bool) -> tuple[int, int, bool] | None:
    """(low, high, approximate) of the amount in `text`; low == high for one figure."""
    result = parse_approx_amount(text, exact=exact)
    if isinstance(result, Parsed):
        return result.rupees, result.rupees, False
    if isinstance(result, Approximate):
        return result.low, result.high, True
    return None


def _read_amount(answer: Answer[str], replies: dict[TurnId, _Reply]) -> Answer[int]:
    """An amount from the customer's whole reply, exact or approximate; the span must agree.

    "करीब पचास हज़ार" is 50,000 marked approximate; "पचास बावन हज़ार" is 52,000 with `low`
    50,000. Hedged and approximate are markers: the rules decide what they may change.
    """
    match answer:
        case Stated(value=span, evidence=ev, hedged=hedged, also=also):
            reply = replies[ev.turn_id].text
            heard = _ends(reply, False)
            # The span, the span with its neighbours, and the whole reply must all read the same.
            said = [_ends(text, False) for text in (span, widen(reply, span))]
            if heard is None or any(r is None or r[:2] != heard[:2] for r in said):
                return Unclear(reason=GapReason.value_not_parsed, evidence=ev)
            low, high, approximate = heard
            return Stated[int](
                value=high,
                evidence=ev,
                hedged=hedged,
                approximate=approximate,
                low=low if low < high else None,
                also=also,
            )
        case _:
            return answer


def _read_term(answer: Answer[str], tenure: int | None, replies: dict[TurnId, _Reply]) -> Answer[int]:
    """A term in months; "as long as the loan runs" is the loan's tenure on the record."""
    if isinstance(answer, Stated) and is_loan_tenure(answer.value):
        ev = answer.evidence
        if not is_loan_tenure(replies[ev.turn_id].text):
            return Unclear(reason=GapReason.value_not_parsed, evidence=ev)
        if tenure is None:
            return Unclear(reason=GapReason.not_comparable, evidence=ev)
        return Stated[int](value=tenure, evidence=ev, hedged=answer.hedged, also=answer.also)
    return _read(answer, _months, replies)


def _months(text: str, exact: bool) -> int | None:
    return parse_duration_months(text, exact=exact)


def _days(text: str, exact: bool) -> int | None:
    return parse_duration_days(text, exact=exact)


def _ground(
    answer: Answer,
    accepted: frozenset[_Asks],
    was_asked: bool,
    replies: dict[TurnId, _Reply],
    ungrounded: list[Evidence],
) -> Answer:
    """Keep an answer only when it quotes whole clauses of a reply to one of the `accepted` questions.

    The other replies a stated answer stands over (`also`) are held to the same test; one that
    fails is dropped from `also` and listed as ungrounded.
    """

    def grounded(ev: Evidence) -> bool:
        reply = _said(ev, replies, whole_clauses=True)
        return bool(reply and reply.asked & accepted)

    match answer:
        case NotAsked():
            return Unclear() if was_asked else answer
        case Unclear():
            return answer
        case DontKnow(evidence=ev) | Stated(evidence=ev):
            if not grounded(ev):
                return Unclear(reason=GapReason.quote_not_grounded, evidence=ev)
            if isinstance(answer, Stated) and answer.also:
                ungrounded += [e for e in answer.also if not grounded(e)]
                return answer.model_copy(update={"also": tuple(e for e in answer.also if grounded(e))})
            return answer
    raise TypeError(f"not an Answer: {answer!r}")


def _read(answer: Answer[str], read: _Reader, replies: dict[TurnId, _Reply]) -> Answer[int]:
    """Read the number from the customer's whole reply; the LLM's span must agree with it."""
    match answer:
        case Stated(value=span, evidence=ev):
            reply = replies[ev.turn_id].text
            heard = read(reply, False)
            if heard is None or heard != read(span, False) or heard != read(widen(reply, span), False):
                return Unclear(reason=GapReason.value_not_parsed, evidence=ev)
            return Stated[int](value=heard, evidence=ev, hedged=answer.hedged, also=answer.also)
        case _:
            return answer


def _confirm(figure: Answer, readback: Answer, replies: dict[TurnId, _Reply]) -> tuple[Answer, Answer]:
    """A "yes" confirms an amount only when the bot read back that same amount (for a range, the
    same two ends) after the customer gave it. A "no" leaves the amount unusable."""
    if not (isinstance(figure, Stated) and isinstance(readback, Stated)):
        return figure, readback
    if not readback.value:
        return Unclear(reason=GapReason.readback_rejected, evidence=readback.evidence), readback
    read_back_turn = replies[readback.evidence.turn_id].prompt
    read = _ends(read_back_turn.text, False) if read_back_turn is not None else None
    if (
        readback.evidence.turn_id <= figure.evidence.turn_id
        or read is None
        or read[:2] != (figure.low or figure.value, figure.value)
    ):
        # The customer confirmed some other amount, or confirmed before giving this one:
        # neither the amount nor the "yes" can be relied on.
        mismatch = Unclear(reason=GapReason.readback_mismatch, evidence=readback.evidence)
        return mismatch, mismatch
    return figure, readback


def _conflicts(
    raw: RawProductAnswers, ungrounded: list[Evidence], replies: dict[TurnId, _Reply]
) -> tuple[AnswerConflict, ...]:
    """Keep each answer of a conflict that is a whole reply to that question; the rest are ungrounded."""
    kept = []
    for conflict in raw.conflicts:
        accepted = (raw.product_id, conflict.question, False)
        answers = []
        for ev in conflict.answers:
            reply = _said(ev, replies, whole_clauses=True)
            (answers if reply and accepted in reply.asked else ungrounded).append(ev)
        if len(answers) >= 2:
            kept.append(conflict.model_copy(update={"answers": tuple(answers)}))
    return tuple(kept)


def _product_beliefs(
    raw: RawProductAnswers,
    ungrounded: list[Evidence],
    replies: dict[TurnId, _Reply],
    asked: frozenset[_Asks],
    tenure: int | None,
) -> ProductBeliefs:
    def ground(answer: Answer, question: Question, read_back: bool = False) -> Answer:
        asks = (raw.product_id, question, read_back)
        return _ground(answer, frozenset({asks}), asks in asked, replies, ungrounded)

    def amount(answer: Answer[str], readback: Answer[bool], question: Question) -> tuple[Answer, Answer]:
        """An amount and the reply to its read-back: the premium, or the cover. The amount may also
        come from a correction made in reply to the read-back."""
        own, again = (raw.product_id, question, False), (raw.product_id, question, True)
        figure = _read_amount(_ground(answer, frozenset({own, again}), own in asked, replies, ungrounded), replies)
        readback = ground(readback, question, read_back=True)
        return _confirm(figure, readback, replies)

    premium, readback = amount(raw.premium, raw.premium_readback, Question.premium)
    cover, cover_readback = amount(raw.cover, raw.cover_readback, Question.cover)

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
        payment_frequency=ground(raw.payment_frequency, Question.payment_frequency),
        volunteered_claims=tuple(claims),
        conflicts=_conflicts(raw, ungrounded, replies),
        premium_inr=premium,
        cover_readback=cover_readback,
        cover_inr=cover,
        term_months=_read_term(ground(raw.term, Question.term), tenure, replies),
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
    denial = raw.recall.denial
    if denial is not None and not (in_recall(denial) and replies[denial.turn_id].says(denial.quote, True)):
        case_ungrounded.append(denial)
        denial = None

    unscreened: list[Evidence] = []
    for ev in raw.unscreened:
        (unscreened if _said(ev, replies) else case_ungrounded).append(ev)

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
        recall=OpenRecall(asked=recall_asked, answer=answer, items=tuple(items), denial=denial),
        products=tuple(
            _product_beliefs(
                raw_by_id.get(pid, RawProductAnswers(product_id=pid)),
                product_ungrounded[pid],
                replies,
                asked,
                record.tenure_months,
            )
            for pid in on_record
        ),
        sale_concerns=tuple(concerns),
        ungrounded=tuple(case_ungrounded),
        unscreened=tuple(unscreened),
    )
