"""One small function per rule. Pure: record and beliefs in, outcomes out.

Every rule commits to Passed, Flag or Gap. Silence is never a pass: a question that was
not asked or not answered usably is a Gap, and "I do not know" is a Flag. The one exception
is the payment-frequency question, which is judged only when the call asks it.

A flag's triage tier follows from its reason (`samajh.types.FLAG_TIER`), not from its severity.
"""

from collections.abc import Callable
from typing import NamedTuple, TypeVar

from samajh.amounts import too_wide
from samajh.rules.clauses import KIND_ON_RECORD
from samajh.types import (
    REFER_RULES,
    TOLD_REQUIRED_HEARD,
    Answer,
    Basis,
    Beliefs,
    ConsentMethod,
    DontKnow,
    Evidence,
    FeatureClaim,
    Flag,
    FlagReason,
    Gap,
    GapReason,
    KindClaim,
    LoanRecord,
    NotAsked,
    Outcome,
    Passed,
    PaymentFrequency,
    PaymentSource,
    Product,
    ProductBeliefs,
    ProductId,
    Question,
    RecallItem,
    RuleId,
    SaleConcern,
    Severity,
    Stated,
    Unclear,
)

T = TypeVar("T")
Outcomes = tuple[Outcome, ...]


class Rule(NamedTuple):
    """The rule a check runs as: its id and the paragraph it may engage for this lender type."""

    id: RuleId
    clause: str


Why = FlagReason  # the old name; rules use it as a short alias


# Review priority of every flag. Tune here and nowhere else.
SEVERITY: dict[Why, Severity] = {
    Why.kind_differs: Severity.high,
    Why.kind_dont_know: Severity.high,
    Why.premium_differs_confirmed: Severity.high,
    Why.premium_differs: Severity.medium,
    Why.premium_dont_know: Severity.medium,
    Why.cover_differs: Severity.low,
    Why.cover_differs_confirmed: Severity.high,
    Why.cover_differs_unconfirmed: Severity.medium,
    Why.cover_dont_know: Severity.low,
    Why.term_differs: Severity.low,
    Why.term_dont_know: Severity.low,
    Why.cancel_unaware: Severity.low,
    Why.cancel_dont_know: Severity.low,
    Why.cancel_window_differs: Severity.low,
    Why.cancel_window_dont_know: Severity.low,
    Why.cancel_not_on_record: Severity.low,
    Why.recall_not_named: Severity.low,
    Why.recall_off_record: Severity.medium,
    Why.consent_no_record: Severity.high,
    Why.consent_not_recognised: Severity.high,
    Why.consent_method_differs: Severity.medium,
    Why.consent_dont_know: Severity.medium,
    Why.funded_no_consent: Severity.high,
    Why.funded_says_separately: Severity.high,
    Why.funded_dont_know: Severity.high,
    Why.unfunded_says_deducted: Severity.medium,
    Why.bundled_not_mitigant: Severity.high,
    Why.bundled_described_as_deposit: Severity.high,
    Why.bundled_no_choice_on_record: Severity.high,
    Why.bundled_no_choice_told: Severity.high,
    Why.feature_contradicted: Severity.high,
    Why.feature_dont_know: Severity.low,
    Why.sale_concern: Severity.high,
    Why.premium_approximate: Severity.low,
    Why.premium_said_zero: Severity.high,
    Why.consent_product_not_named: Severity.low,
    Why.payment_says_not_charged: Severity.high,
    Why.recall_denied: Severity.high,
    Why.frequency_recurring_on_single: Severity.low,
    Why.frequency_dont_know: Severity.low,
}  # answers_conflict is not listed: its severity follows the rule it is raised under

AMOUNT_TOLERANCE_PERCENT = 1  # a stated amount may differ from the record by up to this much
# "About fifty thousand", or a range: the record may lie this far outside what was said.
APPROX_AMOUNT_TOLERANCE_PERCENT = 10
TERM_TOLERANCE_MONTHS = 0
CANCEL_TOLERANCE_DAYS = 1  # "one month" is read as 30 days and "two weeks" as 14

# Kinds that make an off-record recall item worth a reviewer's time.
OFF_RECORD_KINDS = frozenset({KindClaim.insurance, KindClaim.deposit, KindClaim.investment})

DONT_KNOW = "customer said they do not know"

CONCERN_LABEL: dict[SaleConcern, str] = {
    SaleConcern.coached_answers: "customer says they were told what to answer",
    SaleConcern.learned_after_sale: "customer says they learned of the product only after the sale",
    SaleConcern.signed_without_explanation: "customer says they signed without an explanation",
}

KIND_LABEL: dict[KindClaim, str] = {
    KindClaim.insurance: "insurance",
    KindClaim.deposit: "a deposit (FD)",
    KindClaim.investment: "an investment",
    KindClaim.fee: "a fee or charge",
    KindClaim.other: "something else",
}

CONSENT_LABEL: dict[ConsentMethod, str] = {
    ConsentMethod.signed_form: "a signed form",
    ConsentMethod.otp: "an OTP",
    ConsentMethod.digital_click: "a click or tick on a screen",
    ConsentMethod.recorded_call: "a recorded call",
    ConsentMethod.verbal: "word of mouth only",
}

FEATURE_LABEL: dict[FeatureClaim, str] = {
    FeatureClaim.is_deposit: "it is a deposit",
    FeatureClaim.refundable_anytime: "the money can be taken back at any time",
    FeatureClaim.guaranteed_return: "it gives a guaranteed return",
    FeatureClaim.one_time_payment: "it is paid only once",
    FeatureClaim.withdrawable_after_period: "the money can be withdrawn after a period",
    FeatureClaim.money_back: "the money comes back",
}

# An untimed "the money comes back" is true of a product exactly when the record gives it a way for
# the money to come back. The one place this is derived; records never list `money_back` themselves.
MONEY_BACK_VIA = frozenset(
    {FeatureClaim.is_deposit, FeatureClaim.refundable_anytime, FeatureClaim.withdrawable_after_period}
)


def claim_holds(claim: FeatureClaim, features: frozenset[FeatureClaim]) -> bool:
    """Is the customer's belief true of a product with these features on record?"""
    if claim is FeatureClaim.money_back:
        return bool(features & MONEY_BACK_VIA)
    return claim in features


# The rule that answers a question, and so the rule its conflicting answers are flagged under.
QUESTION_RULE: dict[Question, RuleId] = {
    Question.kind: RuleId.kind,
    Question.premium: RuleId.premium,
    Question.payment_source: RuleId.loan_funded,
    Question.required_for_loan: RuleId.bundling,
    Question.provider_choice: RuleId.bundling,
    Question.cover: RuleId.cover,
    Question.term: RuleId.term,
    Question.cancel_window: RuleId.cancel_window,
    Question.features: RuleId.belief_mismatch,
    Question.payment_frequency: RuleId.belief_mismatch,
    Question.consent: RuleId.consent,
}


# --- building outcomes -------------------------------------------------------


def rupees(amount: int) -> str:
    """Format with Indian grouping: 5200000 -> '₹52,00,000'."""
    digits = str(amount)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while head:
        groups.append(head[-2:])
        head = head[:-2]
    return "₹" + ",".join([*reversed(groups), tail])


def _passed(rule: Rule, product_id: ProductId | None) -> Outcomes:
    return (Passed(rule_id=rule.id, product_id=product_id),)


def _flag(
    rule: Rule,
    product_id: ProductId | None,
    why: Why,
    expected: str,
    heard: str,
    evidence: Evidence | None = None,
    claim: FeatureClaim | None = None,
    rests_on: Basis | None = None,
) -> Flag:
    return Flag(
        rule_id=rule.id,
        reason=why,
        clause=rule.clause,
        product_id=product_id,
        severity=SEVERITY[why],
        expected=expected,
        heard=heard,
        quote=evidence.quote if evidence else None,
        turn_id=evidence.turn_id if evidence else None,
        claim=claim,
        rests_on=rests_on,
    )


def _gap(
    rule: Rule, product_id: ProductId | None, reason: GapReason, evidence: Evidence | None = None
) -> Gap:
    return Gap(
        rule_id=rule.id,
        clause=rule.clause,
        product_id=product_id,
        reason=reason,
        quote=evidence.quote if evidence else None,
        turn_id=evidence.turn_id if evidence else None,
    )


def _gap_for(rule: Rule, product_id: ProductId, answer: NotAsked | Unclear) -> Gap:
    if isinstance(answer, NotAsked):
        return _gap(rule, product_id, GapReason.not_asked)
    return _gap(rule, product_id, answer.reason, answer.evidence)


def _evidence_of(answer: Answer) -> Evidence | None:
    """The customer's words behind a usable answer. An unusable answer's quote may not be theirs."""
    return answer.evidence if isinstance(answer, (Stated, DontKnow)) else None


def _decide(
    rule: Rule,
    product_id: ProductId,
    answer: Answer[T],
    *,
    stated: Callable[[Stated[T]], Outcomes],
    dont_know: Why,
    expected: str,
) -> Outcomes:
    """The one place the four answer states are handled. Only `Stated` is rule-specific."""
    if isinstance(answer, Stated):
        return stated(answer)
    if isinstance(answer, DontKnow):
        return (_flag(rule, product_id, dont_know, expected, DONT_KNOW, answer.evidence),)
    return (_gap_for(rule, product_id, answer),)


def _matched(p: Product, beliefs: Beliefs) -> tuple[RecallItem, ...]:
    return tuple(i for i in beliefs.recall.items if i.product_id == p.id)


def _kind_sources(p: Product, beliefs: Beliefs) -> list[tuple[KindClaim, Evidence]]:
    """Every place the customer said what this product is: the kind question and open recall."""
    answer = beliefs.for_product(p.id).kind
    sources = [(answer.value, answer.evidence)] if isinstance(answer, Stated) else []
    sources += [(i.kind, i.evidence) for i in _matched(p, beliefs) if i.kind is not None]
    return sources


def _claims(b: ProductBeliefs) -> list[tuple[FeatureClaim, Evidence]]:
    """Every feature claim the customer made about this product: volunteered, probed, or "paid once"."""
    claims = [(c.claim, c.evidence) for c in b.volunteered_claims]
    if isinstance(b.feature_probe, Stated):
        claims += [(claim, b.feature_probe.evidence) for claim in b.feature_probe.value]
    frequency = b.payment_frequency
    if isinstance(frequency, Stated) and frequency.value is PaymentFrequency.one_time:
        claims.append((FeatureClaim.one_time_payment, frequency.evidence))
    return claims


# --- understanding -----------------------------------------------------------


def kind(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    on_record = KIND_ON_RECORD[p.kind]
    expected = f"customer describes it as {KIND_LABEL[on_record]}"
    sources = _kind_sources(p, beliefs)
    differing = [(k, ev) for k, ev in sources if k is not on_record]
    if differing:
        return tuple(
            _flag(rule, p.id, Why.kind_differs, expected, f"customer described it as {KIND_LABEL[k]}", ev)
            for k, ev in differing
        )
    answer = beliefs.for_product(p.id).kind
    if isinstance(answer, DontKnow):
        return (_flag(rule, p.id, Why.kind_dont_know, expected, DONT_KNOW, answer.evidence),)
    # An unprompted, correct naming in recall stands in for a kind question that was never
    # asked. It does not rescue an answer that was asked and came back unusable.
    if isinstance(answer, Unclear) or not sources:
        return (_gap_for(rule, p.id, answer),)
    return _passed(rule, p.id)


def _differs(heard: int, on_record: int) -> bool:
    """Strictly more than the tolerance away. Integer arithmetic only."""
    return abs(heard - on_record) * 100 > on_record * AMOUNT_TOLERANCE_PERCENT


def _exact(a: Stated[int], on_record: int) -> bool:
    """One figure within the exact tolerance of the record. A range is never exact."""
    return a.low is None and not _differs(a.value, on_record)


def _near(a: Stated[int], on_record: int) -> bool:
    """The record lies within the approximate tolerance of the figure, or of the range, said.

    The tolerance is taken on what the customer said: "about 50,000" reaches from 45,000 to
    55,000, and "50 to 55 thousand" from 45,000 to 60,500. Integer arithmetic only.
    """
    low = a.value if a.low is None else a.low
    return (
        low * (100 - APPROX_AMOUNT_TOLERANCE_PERCENT)
        <= on_record * 100
        <= a.value * (100 + APPROX_AMOUNT_TOLERANCE_PERCENT)
    )


def _too_wide(a: Stated[int]) -> bool:
    """A range too wide to compare with the record: never a pass, never a flag. Same bound as the parser."""
    return a.low is not None and too_wide(a.low, a.value)


def _heard_amount(a: Stated[int]) -> str:
    if a.low is not None:
        return f"customer said {rupees(a.low)} to {rupees(a.value)}"
    return f"customer said {'about ' if a.approximate else ''}{rupees(a.value)}"


def premium(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """The premium passes only when the customer confirmed the read-back of an exact figure.

    Speech recognition can drop a word ("paune do lakh" heard as "do lakh"), so an amount that
    matches the record but was never confirmed may not be what the customer said.

    Confirmed: exact passes, near is a low flag (the customer knows roughly what it cost),
    anything else is a high flag. Not confirmed: exact is a gap, and so is an answer the
    customer gave as approximate that is near; any other differing amount is a medium flag.
    A hedge or an approximation never moves an answer that is not near.
    """
    b = beliefs.for_product(p.id)
    readback = b.premium_readback
    expected = f"premium of {rupees(p.premium_inr)}"

    def stated(a: Stated[int]) -> Outcomes:
        # A rejected or mismatched read-back leaves the premium undecided, whatever the figure.
        if _rejected(readback):
            return (_gap(rule, p.id, GapReason.readback_rejected, readback.evidence),)
        if _mismatched(readback):
            return (_gap(rule, p.id, GapReason.readback_mismatch, readback.evidence),)
        if _too_wide(a):
            return (_gap(rule, p.id, GapReason.not_comparable, a.evidence),)
        if a.value == 0:
            # "It was free": no figure that speech recognition could have changed, so no read-back
            # is needed. `samajh.rules.normalise` reads 0 only when the reply does not also say the
            # money came from the loan or from someone else.
            heard = "customer said it cost them nothing"
            return (_flag(rule, p.id, Why.premium_said_zero, expected, heard, a.evidence),)
        confirmed = isinstance(readback, Stated)
        exact, near = _exact(a, p.premium_inr), _near(a, p.premium_inr)
        if confirmed and exact:
            return _passed(rule, p.id)
        if confirmed:
            why = Why.premium_approximate if near else Why.premium_differs_confirmed
            return (_flag(rule, p.id, why, expected, _heard_amount(a), a.evidence),)
        if not (exact or (near and a.approximate)):
            return (_flag(rule, p.id, Why.premium_differs, expected, _heard_amount(a), a.evidence),)
        if isinstance(readback, DontKnow):
            return (_gap(rule, p.id, GapReason.no_usable_answer, readback.evidence),)
        if isinstance(readback, NotAsked):
            # No read-back: the reviewer still sees the amount the customer said.
            return (_gap(rule, p.id, GapReason.not_asked, a.evidence),)
        return (_gap_for(rule, p.id, readback),)

    return _decide(
        rule, p.id, b.premium_inr, stated=stated, dont_know=Why.premium_dont_know, expected=expected
    )


def _rejected(readback: Answer[bool]) -> bool:
    return isinstance(readback, Stated) and not readback.value


def _mismatched(readback: Answer[bool]) -> bool:
    """The customer said yes to another figure, or before giving theirs (`samajh.rules.normalise`)."""
    return isinstance(readback, Unclear) and readback.reason is GapReason.readback_mismatch


def cover(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """One figure within the exact tolerance passes; an answer given as approximate may be near.

    Off the record (coordinator decision 2026-11-10): a hedged or approximate answer is an
    understanding gap. A plain figure is a referral once the customer confirmed a read-back of it,
    and incomplete until then: speech recognition may have changed it. A range too wide to compare
    is a gap.

    Asking a read-back never lowers the tier against not asking it: a plain differing figure whose
    read-back was rejected without a correction, or mismatched, is still incomplete. A figure that
    matches the record is a gap when its read-back was rejected or mismatched. A figure the customer
    gave as a correction at the read-back has had no read-back of its own: it is judged as if none
    was asked (the bot read back the customer's earlier figure, never the record's).
    """
    b = beliefs.for_product(p.id)
    readback = b.cover_readback
    expected = f"cover of {rupees(p.cover_inr)}"

    def stated(a: Stated[int]) -> Outcomes:
        if _too_wide(a):
            return (_gap(rule, p.id, GapReason.not_comparable, a.evidence),)
        corrected = _rejected(readback) and readback.evidence.turn_id == a.evidence.turn_id
        if _exact(a, p.cover_inr) or (a.approximate and _near(a, p.cover_inr)):
            if _rejected(readback) and not corrected:
                return (_gap(rule, p.id, GapReason.readback_rejected, readback.evidence),)
            if _mismatched(readback):
                return (_gap(rule, p.id, GapReason.readback_mismatch, readback.evidence),)
            return _passed(rule, p.id)
        if a.hedged or a.approximate:
            why = Why.cover_differs
        elif isinstance(readback, Stated) and readback.value:
            why = Why.cover_differs_confirmed
        else:
            why = Why.cover_differs_unconfirmed
        return (_flag(rule, p.id, why, expected, _heard_amount(a), a.evidence),)

    return _decide(rule, p.id, b.cover_inr, stated=stated, dont_know=Why.cover_dont_know, expected=expected)


def term(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    expected = f"term of {p.term_months} months"

    def stated(a: Stated[int]) -> Outcomes:
        if abs(a.value - p.term_months) > TERM_TOLERANCE_MONTHS:
            heard = f"customer said {a.value} months"
            return (_flag(rule, p.id, Why.term_differs, expected, heard, a.evidence),)
        return _passed(rule, p.id)

    answer = beliefs.for_product(p.id).term_months
    return _decide(rule, p.id, answer, stated=stated, dont_know=Why.term_dont_know, expected=expected)


def cancel_window(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """What the customer says they were told about cancelling, against the window on the record."""
    b = beliefs.for_product(p.id)
    on_record = p.cancel_window_days
    if on_record is None:
        expected = "the record shows no cancellation window for this product"

        def stated(a: Stated[bool]) -> Outcomes:
            if not a.value:
                return _passed(rule, p.id)
            heard = "customer was told it can be cancelled"
            return (_flag(rule, p.id, Why.cancel_not_on_record, expected, heard, a.evidence),)

        if isinstance(b.cancel_allowed, DontKnow):
            return _passed(rule, p.id)  # nothing on record that the customer should have been told
        return _decide(
            rule, p.id, b.cancel_allowed, stated=stated, dont_know=Why.cancel_dont_know, expected=expected
        )

    expected = f"customer was told it can be cancelled within {on_record} days"

    def window(a: Stated[int]) -> Outcomes:
        if abs(a.value - on_record) <= CANCEL_TOLERANCE_DAYS:
            return _passed(rule, p.id)
        heard = f"customer said it can be cancelled within {a.value} days"
        return (_flag(rule, p.id, Why.cancel_window_differs, expected, heard, a.evidence),)

    def stated(a: Stated[bool]) -> Outcomes:
        if not a.value:
            heard = "customer was not told it can be cancelled"
            return (_flag(rule, p.id, Why.cancel_unaware, expected, heard, a.evidence),)
        if isinstance(b.cancel_window_days, DontKnow):
            heard = "customer knows it can be cancelled but not by when"
            why = Why.cancel_window_dont_know
            return (_flag(rule, p.id, why, expected, heard, b.cancel_window_days.evidence),)
        if isinstance(b.cancel_window_days, Stated):
            return window(b.cancel_window_days)
        return (_gap_for(rule, p.id, b.cancel_window_days),)

    return _decide(
        rule, p.id, b.cancel_allowed, stated=stated, dont_know=Why.cancel_dont_know, expected=expected
    )


# --- open recall -------------------------------------------------------------


def recall(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """A customer who said they took nothing, while the record holds this product, is a referral
    while the denial stands (coordinator decision 2026-11-10). It is retracted only when the
    customer names this product as the kind on record in a turn AFTER the denial: a later recall
    item of that kind matched to this product, or the kind question answered as that kind. Then
    the finding is `recall_not_named`, with the denial as the quote and those namings in `also`.
    A naming before the denial, a misdescription ("an FD" for insurance), "I don't know", or
    nothing asked: the denial stands. The extractor keeps the last denial."""
    if not beliefs.recall.asked:
        return (_gap(rule, p.id, GapReason.not_asked),)
    expected = "customer names this product when asked what they took with the loan"
    denial = beliefs.recall.denial
    if denial is not None:
        on_record = KIND_ON_RECORD[p.kind]
        named = [i.evidence for i in _matched(p, beliefs) if i.kind is on_record]
        answer = beliefs.for_product(p.id).kind
        if isinstance(answer, Stated) and answer.value is on_record:
            named.append(answer.evidence)
        later = tuple(ev for ev in named if ev.turn_id > denial.turn_id)
        if not later:
            heard = "customer said they took nothing with the loan"
            return (_flag(rule, p.id, Why.recall_denied, expected, heard, denial),)
        heard = "customer first said they took nothing with the loan, then named this product"
        flag = _flag(rule, p.id, Why.recall_not_named, expected, heard, denial)
        return (flag.model_copy(update={"also": later}),)
    if _matched(p, beliefs):
        return _passed(rule, p.id)
    heard = "customer did not name this product unprompted"
    return (_flag(rule, p.id, Why.recall_not_named, expected, heard, beliefs.recall.answer),)


def recall_unmatched(rule: Rule, record: LoanRecord, beliefs: Beliefs) -> Outcomes:
    """Case-level: the customer names something that is not on the lender's record.

    A financial product is a flag. A fee is expected and ignored. Anything the extraction
    could not classify is a gap: a person has to hear what it was.
    """
    if not beliefs.recall.asked:
        return (_gap(rule, None, GapReason.not_asked),)
    outcomes: list[Outcome] = []
    for i in beliefs.recall.items:
        if i.product_id is not None or i.kind is KindClaim.fee:
            continue
        if i.kind in OFF_RECORD_KINDS:
            expected = "every product the customer names is on the lender's record"
            heard = f"customer named {KIND_LABEL[i.kind]} that is not on the record"
            outcomes.append(_flag(rule, None, Why.recall_off_record, expected, heard, i.evidence))
        else:
            outcomes.append(_gap(rule, None, GapReason.no_usable_answer, i.evidence))
    return tuple(outcomes) or _passed(rule, None)


# --- consent, payment, bundling ----------------------------------------------


def _method_only(given: Answer[bool], method: Answer[ConsentMethod]) -> bool:
    """The consent reply gave a way of agreeing and named nothing agreed to.

    The "what" half is the extractor's plain no-answer reading (of the same reply as the method,
    when it carries a quote), and the method stood without a correction inside that reply (no earlier words of its own turn
    in `also`). A failed call, an ungrounded quote, a withdrawal or a correction never qualify:
    the change check and the take-back tail leave the method `Unclear` or mark it.
    """
    return (
        isinstance(method, Stated)
        and isinstance(given, Unclear)
        and given.reason is GapReason.no_usable_answer
        and (given.evidence is None or given.evidence.turn_id == method.evidence.turn_id)
        and all(e.turn_id != method.evidence.turn_id for e in method.also)
    )


def _naming(p: Product, beliefs: Beliefs, consent_turn: int) -> Evidence | None:
    """Where the customer named this product in the call: a recall item matched to it, or the kind
    question answered (any kind: a misdescription is judged by the kind rule). The last naming
    before the consent reply, else the first after it; None when the customer named it nowhere."""
    namings = [i.evidence for i in _matched(p, beliefs)]
    kind = beliefs.for_product(p.id).kind
    if isinstance(kind, Stated):
        namings.append(kind.evidence)
    namings.sort(key=lambda ev: ev.turn_id)
    before = [ev for ev in namings if ev.turn_id < consent_turn]
    return before[-1] if before else (namings[0] if namings else None)


def consent(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """A consent record clears nothing by itself: the customer's own account must match it.

    No record -> flag from the record alone. A record -> the customer, asked openly what they
    agreed to buy and how, must name this product and the way of agreeing that is on record. A
    different way of agreeing is a flag. (A phone yes is classed as `recorded_call` by the extractor
    unless the customer says the call was not recorded; the comparison here is equality.)

    A reply that gives only the way of agreeing (P5 fix round): the "what" half is taken by code
    from the customer's own naming of this product elsewhere in the call (open recall or the kind
    question; `_naming`). If they named it nowhere, a matching way of agreeing is an understanding
    gap (`consent_product_not_named`); a differing way still refers. Any other unusable answer to
    either half is a gap, never a pass.
    """
    b = beliefs.for_product(p.id)
    if p.consent is None:
        return (
            _flag(
                rule,
                p.id,
                Why.consent_no_record,
                "a recorded consent for this product",
                "the lender's record has no consent for this product",
                _evidence_of(b.consent_given),
            ),
        )
    on_record = p.consent.method
    expected = (
        f"customer's account matches the consent on record: {CONSENT_LABEL[on_record]} "
        f"on {p.consent.at.isoformat()}"
    )

    method = b.consent_method

    def differs(m: Stated[ConsentMethod]) -> Flag:
        heard = f"customer said they agreed by {CONSENT_LABEL[m.value]}"
        return _flag(rule, p.id, Why.consent_method_differs, expected, heard, m.evidence)

    def stated(a: Stated[bool]) -> Outcomes:
        if not a.value:
            heard = "customer's account of what they agreed to buy does not include this product"
            return (_flag(rule, p.id, Why.consent_not_recognised, expected, heard, a.evidence),)
        if isinstance(method, Stated):
            if method.value == on_record:
                return _passed(rule, p.id)
            return (differs(method),)
        # The customer names the product but not how they agreed: the record cannot be compared.
        if isinstance(method, DontKnow):
            return (_gap(rule, p.id, GapReason.no_usable_answer, method.evidence),)
        return (_gap_for(rule, p.id, method),)

    given = b.consent_given
    if _method_only(given, method):
        assert isinstance(method, Stated)
        named = _naming(p, beliefs, method.evidence.turn_id)
        if named is not None:
            given = Stated[bool](value=True, evidence=named)
        elif method.value != on_record:
            return (differs(method),)
        else:
            heard = (
                "customer said how they agreed but did not name this product, here or anywhere in the call"
            )
            return (_flag(rule, p.id, Why.consent_product_not_named, expected, heard, method.evidence),)
    return _decide(rule, p.id, given, stated=stated, dont_know=Why.consent_dont_know, expected=expected)


def loan_funded(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    answer = beliefs.for_product(p.id).payment_source
    if p.paid_from_loan and p.consent is None:
        return (
            _flag(
                rule,
                p.id,
                Why.funded_no_consent,
                "a recorded consent for a premium deducted from the loan",
                "the record shows the premium deducted from the loan and no consent",
                _evidence_of(answer),
            ),
        )
    if p.paid_from_loan:
        on_record, other = PaymentSource.from_loan, Why.funded_says_separately
        expected = "customer knows the premium was deducted from the loan amount"
        heard = "customer said it was paid separately"
    else:
        on_record, other = PaymentSource.separately, Why.unfunded_says_deducted
        expected = "customer says the premium was paid separately, as on the record"
        heard = "customer said it was deducted from the loan amount"
        if isinstance(answer, DontKnow):
            # Nothing was funded from the loan per the record, so not knowing engages no paragraph.
            return (_gap(rule, p.id, GapReason.no_usable_answer, answer.evidence),)

    def stated(a: Stated[PaymentSource]) -> Outcomes:
        if a.value is on_record:
            return _passed(rule, p.id)
        if a.value is PaymentSource.not_charged:
            said = "customer said they paid nothing for it (free, or paid by the bank or someone else)"
            return (_flag(rule, p.id, Why.payment_says_not_charged, expected, said, a.evidence),)
        return (_flag(rule, p.id, other, expected, heard, a.evidence),)

    return _decide(rule, p.id, answer, stated=stated, dont_know=Why.funded_dont_know, expected=expected)


def _described_as_deposit(p: Product, beliefs: Beliefs) -> Evidence | None:
    """The customer's words, if they describe the product as a deposit (FD, security deposit)."""
    sources = [ev for k, ev in _kind_sources(p, beliefs) if k is KindClaim.deposit]
    sources += [ev for claim, ev in _claims(beliefs.for_product(p.id)) if claim is FeatureClaim.is_deposit]
    return sources[0] if sources else None


def bundling(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """Required for the loan AND (not a risk mitigant OR no choice of provider) -> flag.

    "Required" and "no choice" each hold when the record or the customer says so. A product the
    customer describes as a deposit is not a risk mitigant, whatever the record says. Required
    as a risk mitigant with a choice of provider, or not required at all, passes.
    """
    b = beliefs.for_product(p.id)
    required, choice = b.required_for_loan, b.provider_choice_offered
    told_required = isinstance(required, Stated) and required.value
    if not (p.required_for_loan or told_required):
        if isinstance(required, Stated):
            return _passed(rule, p.id)
        if isinstance(required, DontKnow):
            return (_gap(rule, p.id, GapReason.no_usable_answer, required.evidence),)
        return (_gap_for(rule, p.id, required),)

    expected = "a product required for the loan is a risk mitigant the customer may buy from any provider"
    how = "the record marks this product as required for the loan"
    # Required only on the customer's word: the flags below then rest on what the customer said.
    rests_on = None
    if not p.required_for_loan:
        how = TOLD_REQUIRED_HEARD
        rests_on = Basis.customer_statement
    required_ev = _evidence_of(required)
    flags: list[Outcome] = []
    deposit = _described_as_deposit(p, beliefs)
    if not p.risk_mitigant:
        heard = f"{how}; the record does not mark it as a risk mitigant"
        flags.append(
            _flag(rule, p.id, Why.bundled_not_mitigant, expected, heard, required_ev, rests_on=rests_on)
        )
    elif deposit is not None:
        heard = f"{how}; customer describes it as a deposit, which is not a risk mitigant"
        flags.append(_flag(rule, p.id, Why.bundled_described_as_deposit, expected, heard, deposit))
    if not p.provider_choice_offered:
        heard = f"{how}; the record shows no choice of provider was offered"
        flags.append(
            _flag(
                rule, p.id, Why.bundled_no_choice_on_record, expected, heard, required_ev, rests_on=rests_on
            )
        )
    if isinstance(choice, Stated) and not choice.value:
        heard = f"{how}; customer says they were not told they could buy it from another provider"
        flags.append(_flag(rule, p.id, Why.bundled_no_choice_told, expected, heard, choice.evidence))
    if flags:
        return tuple(flags)
    if isinstance(choice, Stated):
        return _passed(rule, p.id)
    if isinstance(choice, DontKnow):
        return (_gap(rule, p.id, GapReason.no_usable_answer, choice.evidence),)
    return (_gap_for(rule, p.id, choice),)


# --- features ----------------------------------------------------------------


def _frequency(rule: Rule, p: Product, b: ProductBeliefs) -> Outcomes:
    """What the payment-frequency answer adds. Never asked adds nothing: most calls do not ask it.

    "Paid once" is a feature claim and is judged with the others (`_claims`).
    """
    answer = b.payment_frequency
    expected = "customer knows whether the product is paid for once or again and again"
    if isinstance(answer, Unclear):
        return (_gap_for(rule, p.id, answer),)
    if isinstance(answer, DontKnow):
        return (_flag(rule, p.id, Why.frequency_dont_know, expected, DONT_KNOW, answer.evidence),)
    paid_once = FeatureClaim.one_time_payment in p.features
    if isinstance(answer, Stated) and answer.value is PaymentFrequency.recurring and paid_once:
        heard = "customer said it is paid again and again; the record shows a single payment"
        why = Why.frequency_recurring_on_single
        return (_flag(rule, p.id, why, expected, heard, answer.evidence),)
    return ()


def belief_mismatch(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """Contradicted beliefs, else the money-back probe; the payment-frequency answer is added to either."""
    b = beliefs.for_product(p.id)
    claims = _claims(b)
    claims += [(FeatureClaim.is_deposit, ev) for k, ev in _kind_sources(p, beliefs) if k is KindClaim.deposit]
    contradicted: dict[FeatureClaim, Evidence] = {}
    for claim, ev in claims:
        if not claim_holds(claim, p.features):
            contradicted.setdefault(claim, ev)
    expected = "what the customer believes matches the product's features"
    frequency = _frequency(rule, p, b)
    if contradicted:
        return (
            *(
                _flag(
                    rule,
                    p.id,
                    Why.feature_contradicted,
                    expected,
                    f"customer believes {FEATURE_LABEL[claim]}; the product does not have this feature",
                    ev,
                    claim,
                )
                for claim, ev in contradicted.items()
            ),
            *frequency,
        )
    probe = _decide(
        rule,
        p.id,
        b.feature_probe,
        stated=lambda _: _passed(rule, p.id),
        dont_know=Why.feature_dont_know,
        expected=expected,
    )
    if frequency and isinstance(probe[0], Passed):
        return frequency
    return (*probe, *frequency)


# --- conduct of the sale -----------------------------------------------------


def sale_conduct(rule: Rule, record: LoanRecord, beliefs: Beliefs) -> Outcomes:
    """Case-level: the customer voiced a concern about how the sale or the confirmation went."""
    expected = "no concern about how the product was sold"
    flags = tuple(
        _flag(rule, None, Why.sale_concern, expected, CONCERN_LABEL[c.concern], c.evidence)
        for c in beliefs.sale_concerns
    )
    return flags or _passed(rule, None)


# --- evidence ----------------------------------------------------------------


def evidence(rule: Rule, p: Product, beliefs: Beliefs) -> Outcomes:
    """A quote that is not in the transcript cannot support a verdict on this product."""
    gaps = tuple(
        _gap(rule, p.id, GapReason.quote_not_grounded, ev) for ev in beliefs.for_product(p.id).ungrounded
    )
    return gaps or _passed(rule, p.id)


def evidence_case(rule: Rule, record: LoanRecord, beliefs: Beliefs) -> Outcomes:
    """Case-level: quotes that belong to no product and are not in the transcript, and replies
    that no screening call read for claims and concerns."""
    return (
        *(_gap(rule, None, GapReason.quote_not_grounded, ev) for ev in beliefs.ungrounded),
        *(_gap(rule, None, GapReason.extraction_failed, ev) for ev in beliefs.unscreened),
    )


# --- conflicting answers -----------------------------------------------------


def conflicts(rules: dict[RuleId, Rule], p: Product, beliefs: Beliefs) -> tuple[Flag, ...]:
    """One flag per question whose answers differed, under the rule that question belongs to.

    The answers may come from separate askings or from one reply the customer corrected. The field
    holds only the last answer, so without this an earlier "FD" followed by "insurance" would leave
    no trace. The reviewer gets every answer, in call order.
    """
    found = []
    for conflict in beliefs.for_product(p.id).conflicts:
        rule = rules[QUESTION_RULE[conflict.question]]
        first, *others = conflict.answers
        found.append(
            Flag(
                rule_id=rule.id,
                reason=Why.answers_conflict,
                clause=rule.clause,
                product_id=p.id,
                severity=Severity.high if rule.id in REFER_RULES else Severity.low,
                expected="one consistent answer to the question",
                heard=f"customer gave {len(conflict.answers)} differing answers to this question",
                quote=first.quote,
                turn_id=first.turn_id,
                also=tuple(others),
            )
        )
    return tuple(found)
