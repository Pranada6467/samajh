"""Rule engine tests. Expected results are derived from the rule spec, not from running the code.

Every test starts from a compliant baseline (all rules pass, verdict `clear`) and changes one thing.
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

import samajh.rules
from samajh.rules import CLAUSES, RULES, evaluate, verdict_of
from samajh.types import (
    EVIDENCE_PACK_RULES,
    Beliefs,
    Borrower,
    CaseResult,
    ClaimEvidence,
    ConcernEvidence,
    Consent,
    ConsentMethod,
    DontKnow,
    Evidence,
    EvidencePack,
    FeatureClaim,
    Flag,
    Gap,
    GapReason,
    KindClaim,
    Language,
    LenderType,
    LoanKind,
    LoanRecord,
    NotAsked,
    OpenRecall,
    Passed,
    PaymentSource,
    Product,
    ProductBeliefs,
    ProductId,
    ProductResult,
    RecallItem,
    RuleId,
    SaleConcern,
    Severity,
    Stated,
    TurnId,
    Unclear,
    Verdict,
)

P1 = ProductId("P1")
P2 = ProductId("P2")
HIGH, MEDIUM, LOW = Severity.high, Severity.medium, Severity.low
CLEAR, FLAGGED, UNCLEAR = Verdict.clear, Verdict.flag_for_review, Verdict.unclear_needs_human
UNCLEAR_REASONS = [r for r in GapReason if r is not GapReason.not_asked]
BANK, NBFC = LenderType.bank, LenderType.nbfc

# --- builders ----------------------------------------------------------------

QUOTE = "customer words"
TURN = TurnId(41)


def ev(quote: str = QUOTE, turn: int = TURN) -> Evidence:
    return Evidence(quote=quote, turn_id=TurnId(turn))


def said(value, quote: str = QUOTE, turn: int = TURN) -> Stated:
    return Stated(value=value, evidence=ev(quote, turn))


def dont_know() -> DontKnow:
    return DontKnow(evidence=ev())


def unclear(reason: GapReason = GapReason.no_usable_answer) -> Unclear:
    return Unclear(reason=reason, evidence=ev())


def product(pid: ProductId = P1, **changes) -> Product:
    base = {
        "id": pid,
        "kind": "credit_life",
        "provider": "Namoona Life (synthetic)",
        "premium_inr": 52_000,
        "cover_inr": 500_000,
        "term_months": 36,
        "paid_from_loan": True,
        "required_for_loan": False,
        "risk_mitigant": True,
        "provider_choice_offered": True,
        "cancel_window_days": 30,
        "features": frozenset({FeatureClaim.one_time_payment}),
        "consent": Consent(method=ConsentMethod.otp, at=date(2027, 1, 5)),
    }
    return Product(**(base | changes))


def record(*products: Product, lender_type: LenderType = BANK) -> LoanRecord:
    return LoanRecord(
        loan_id="LN-TEST-0000",
        lender_type=lender_type,
        borrower=Borrower(name="Test Grahak", dob=date(1990, 1, 1), language=Language.hi),
        loan_kind=LoanKind.gold,
        sanctioned_inr=500_000,
        disbursed_inr=448_000,
        disbursed_on=date(2027, 1, 5),
        products=products or (product(),),
    )


def product_beliefs(pid: ProductId = P1, **changes) -> ProductBeliefs:
    base = {
        "product_id": pid,
        "kind": said(KindClaim.insurance),
        "payment_source": said(PaymentSource.from_loan),
        "required_for_loan": said(False),
        "provider_choice_offered": said(True),
        "cancel_allowed": said(True),
        "consent_given": said(True),
        "consent_method": said(ConsentMethod.otp),
        "feature_probe": said(()),
        "premium_inr": said(52_000),
        "premium_readback": said(True),
        "cover_inr": said(500_000),
        "term_months": said(36),
        "cancel_window_days": said(30),
    }
    return ProductBeliefs(**(base | changes))


def recall_of(*items: RecallItem, asked: bool = True) -> OpenRecall:
    return OpenRecall(asked=asked, answer=ev("recall answer", 3) if asked else None, items=items)


def named(pid: ProductId | None = P1, kind: KindClaim | None = None, quote: str = "ek policy") -> RecallItem:
    """A recall item. The baseline item names the product without saying what kind it is."""
    return RecallItem(evidence=ev(quote, 3), kind=kind, product_id=pid)


def beliefs(
    *products: ProductBeliefs, recall: OpenRecall | None = None, ungrounded=(), sale_concerns=()
) -> Beliefs:
    products = products or (product_beliefs(),)
    if recall is None:
        recall = recall_of(*(named(p.product_id) for p in products))
    return Beliefs(
        call_id="CALL-TEST-0000",
        loan_id="LN-TEST-0000",
        language=Language.hi,
        recall=recall,
        products=products,
        sale_concerns=sale_concerns,
        ungrounded=ungrounded,
    )


def run(
    product_changes: dict | None = None,
    belief_changes: dict | None = None,
    lender_type: LenderType = BANK,
    **beliefs_kw,
) -> CaseResult:
    """Evaluate the one-product baseline with changes to the record and/or the beliefs."""
    return evaluate(
        record(product(**(product_changes or {})), lender_type=lender_type),
        beliefs(product_beliefs(**(belief_changes or {})), **beliefs_kw),
    )


def flags(result: CaseResult, rule: RuleId) -> list[Flag]:
    return [f for f in result.products[0].flags if f.rule_id is rule]


def gaps(result: CaseResult, rule: RuleId) -> list[Gap]:
    return [g for g in result.products[0].gaps if g.rule_id is rule]


def assert_one_flag(result: CaseResult, rule: RuleId, severity: Severity, quoted: bool = True) -> Flag:
    (flag,) = flags(result, rule)
    assert flag.severity is severity
    assert flag.clause == CLAUSES[BANK][rule]
    assert flag.product_id == P1
    assert flag.expected and flag.heard
    if quoted:
        assert (flag.quote, flag.turn_id) == (QUOTE, TURN)
    assert rule not in result.products[0].passed
    assert result.products[0].verdict is FLAGGED
    assert result.verdict is FLAGGED
    return flag


def assert_passes(result: CaseResult, rule: RuleId) -> None:
    assert rule in result.products[0].passed
    assert not flags(result, rule) and not gaps(result, rule)


# --- baseline ----------------------------------------------------------------

CASE_LEVEL_RULES = {RuleId.recall_unmatched, RuleId.sale_conduct}
PER_PRODUCT_RULES = [r for r in RuleId if r not in CASE_LEVEL_RULES]


def test_baseline_is_clear_and_every_rule_passes():
    result = run()
    assert result.verdict is CLEAR
    (p,) = result.products
    assert p.verdict is CLEAR
    assert p.passed == tuple(PER_PRODUCT_RULES)
    assert not p.flags and not p.gaps
    assert not result.case_flags and not result.case_gaps and not result.unmatched_recall
    assert (result.loan_id, result.call_id, result.language) == (
        "LN-TEST-0000",
        "CALL-TEST-0000",
        Language.hi,
    )


# --- missing data, uniform across rules --------------------------------------

# answer field -> (rule that reads it, severity of a "do not know" answer on the baseline record).
# On the baseline record every one of these must be answered for its rule to pass.
ANSWER_FIELDS = {
    "kind": (RuleId.kind, HIGH),
    "premium_inr": (RuleId.premium, MEDIUM),
    "cover_inr": (RuleId.cover, LOW),
    "term_months": (RuleId.term, LOW),
    "cancel_allowed": (RuleId.cancel_window, LOW),
    "cancel_window_days": (RuleId.cancel_window, LOW),
    "consent_given": (RuleId.consent, MEDIUM),
    "payment_source": (RuleId.loan_funded, HIGH),  # baseline premium is deducted from the loan
    "required_for_loan": (RuleId.bundling, None),  # not knowing what happened is a gap, not a flag
    "feature_probe": (RuleId.belief_mismatch, LOW),
}
# Read only in some cases: the read-back with the premium, the choice of provider when the
# product was required, the way of agreeing when the customer says they agreed.
CONDITIONAL_FIELDS = {"premium_readback", "provider_choice_offered", "consent_method"}
RULES_NEEDING_AN_ANSWER = {rule for rule, _ in ANSWER_FIELDS.values()}
DONT_KNOW_FLAGS = [field for field, (_, severity) in ANSWER_FIELDS.items() if severity]


def test_answer_field_table_covers_every_answer_field():
    answer_fields = {
        name for name, value in product_beliefs() if isinstance(value, (NotAsked, Unclear, DontKnow, Stated))
    }
    assert answer_fields == set(ANSWER_FIELDS) | CONDITIONAL_FIELDS


@pytest.mark.parametrize("field", ANSWER_FIELDS)
def test_not_asked_is_a_gap_never_clear(field):
    rule, _ = ANSWER_FIELDS[field]
    result = run(belief_changes={field: NotAsked()})
    (gap,) = gaps(result, rule)
    assert gap.reason is GapReason.not_asked
    assert (gap.clause, gap.product_id, gap.quote, gap.turn_id) == (CLAUSES[BANK][rule], P1, None, None)
    assert rule not in result.products[0].passed
    assert result.products[0].verdict is UNCLEAR
    assert result.verdict is UNCLEAR


@pytest.mark.parametrize("reason", UNCLEAR_REASONS)
@pytest.mark.parametrize("field", ANSWER_FIELDS)
def test_unclear_is_a_gap_with_its_reason_and_quote(field, reason):
    rule, _ = ANSWER_FIELDS[field]
    result = run(belief_changes={field: unclear(reason)})
    (gap,) = gaps(result, rule)
    assert (gap.reason, gap.quote, gap.turn_id) == (reason, QUOTE, TURN)
    assert result.products[0].verdict is UNCLEAR
    assert result.verdict is UNCLEAR


def test_unclear_without_evidence_is_still_a_gap():
    result = run(belief_changes={"premium_inr": Unclear()})
    (gap,) = gaps(result, RuleId.premium)
    assert (gap.reason, gap.quote, gap.turn_id) == (GapReason.no_usable_answer, None, None)
    assert result.verdict is UNCLEAR


@pytest.mark.parametrize("field", DONT_KNOW_FLAGS)
def test_dont_know_is_a_flag(field):
    rule, severity = ANSWER_FIELDS[field]
    assert_one_flag(run(belief_changes={field: dont_know()}), rule, severity)


# --- kind --------------------------------------------------------------------


@pytest.mark.parametrize("claim", [k for k in KindClaim if k is not KindClaim.insurance])
def test_kind_stated_wrong_flags_high(claim):
    assert_one_flag(run(belief_changes={"kind": said(claim)}), RuleId.kind, HIGH)


def test_kind_wrong_in_recall_flags_even_when_the_prompted_answer_is_right():
    result = run(recall=recall_of(named(P1, KindClaim.deposit, "ek FD")))
    (flag,) = flags(result, RuleId.kind)
    assert (flag.severity, flag.quote, flag.turn_id) == (HIGH, "ek FD", 3)
    assert result.verdict is FLAGGED


def test_kind_one_flag_per_contradicting_source():
    result = run(
        belief_changes={"kind": said(KindClaim.investment, "investment hai", 9)},
        recall=recall_of(named(P1, KindClaim.deposit, "ek FD"), named(P1, KindClaim.insurance, "bima")),
    )
    assert [f.quote for f in flags(result, RuleId.kind)] == ["investment hai", "ek FD"]


def test_kind_dont_know_flags_even_when_recall_named_the_right_kind():
    result = run(belief_changes={"kind": dont_know()}, recall=recall_of(named(P1, KindClaim.insurance)))
    assert_one_flag(result, RuleId.kind, HIGH)


def test_kind_named_correctly_in_recall_stands_in_for_a_question_never_asked():
    result = run(belief_changes={"kind": NotAsked()}, recall=recall_of(named(P1, KindClaim.insurance)))
    assert_passes(result, RuleId.kind)
    assert result.verdict is CLEAR


@pytest.mark.parametrize("reason", UNCLEAR_REASONS)
def test_recall_does_not_rescue_a_kind_answer_that_was_asked_and_unusable(reason):
    result = run(belief_changes={"kind": unclear(reason)}, recall=recall_of(named(P1, KindClaim.insurance)))
    (gap,) = gaps(result, RuleId.kind)
    assert (gap.reason, gap.quote) == (reason, QUOTE)
    assert result.verdict is UNCLEAR


def test_kind_in_unmatched_or_other_products_recall_item_is_not_a_source():
    result = run(belief_changes={"kind": NotAsked()}, recall=recall_of(named(P1), named(None, KindClaim.fee)))
    (gap,) = gaps(result, RuleId.kind)
    assert gap.reason is GapReason.not_asked


# --- premium, cover, term ----------------------------------------------------


# record premium 52,000 -> 1% is exactly 520
@pytest.mark.parametrize("heard", [52_000, 52_520, 51_480, 52_001])
def test_premium_within_one_percent_passes(heard):
    result = run(belief_changes={"premium_inr": said(heard)})
    assert_passes(result, RuleId.premium)
    assert result.verdict is CLEAR


@pytest.mark.parametrize(
    "heard, heard_text", [(52_521, "₹52,521"), (51_479, "₹51,479"), (5_200_000, "₹52,00,000"), (520, "₹520")]
)
def test_premium_more_than_one_percent_off_flags(heard, heard_text):
    flag = assert_one_flag(run(belief_changes={"premium_inr": said(heard)}), RuleId.premium, HIGH)
    assert "₹52,000" in flag.expected
    assert heard_text in flag.heard


@pytest.mark.parametrize("readback", [NotAsked(), unclear(), dont_know()])
def test_premium_flag_is_medium_without_a_confirmed_readback(readback):
    changes = {"premium_inr": said(60_000), "premium_readback": readback}
    assert_one_flag(run(belief_changes=changes), RuleId.premium, MEDIUM)


# A matching amount is not enough: recognition can drop a word, so the customer must confirm it.
@pytest.mark.parametrize(
    "readback, reason, quoted",
    [
        (NotAsked(), GapReason.not_asked, False),
        (unclear(), GapReason.no_usable_answer, True),
        (unclear(GapReason.quote_not_grounded), GapReason.quote_not_grounded, True),
        (dont_know(), GapReason.no_usable_answer, True),
        (said(False), GapReason.readback_rejected, True),
    ],
)
def test_premium_matching_the_record_does_not_pass_without_a_confirmed_readback(readback, reason, quoted):
    result = run(belief_changes={"premium_readback": readback})
    (gap,) = gaps(result, RuleId.premium)
    assert gap.reason is reason
    assert (gap.quote, gap.turn_id) == ((QUOTE, TURN) if quoted else (None, None))
    assert RuleId.premium not in result.products[0].passed
    assert result.verdict is UNCLEAR


def test_an_amount_the_customer_rejected_at_readback_is_a_gap_not_a_flag():
    result = run(belief_changes={"premium_inr": said(200_000), "premium_readback": said(False)})
    (gap,) = gaps(result, RuleId.premium)
    assert gap.reason is GapReason.readback_rejected
    assert not flags(result, RuleId.premium)
    assert result.verdict is UNCLEAR


# record premium 12,345 -> 1% is 123.45: 123 rupees off is inside, 124 is outside
@pytest.mark.parametrize("heard, flagged", [(12_468, False), (12_222, False), (12_469, True), (12_221, True)])
def test_premium_tolerance_uses_exact_integer_arithmetic(heard, flagged):
    result = run({"premium_inr": 12_345}, {"premium_inr": said(heard)})
    assert bool(flags(result, RuleId.premium)) is flagged


# record cover 5,00,000 -> 1% is exactly 5,000
@pytest.mark.parametrize("heard", [500_000, 505_000, 495_000])
def test_cover_within_one_percent_passes(heard):
    result = run(belief_changes={"cover_inr": said(heard)})
    assert_passes(result, RuleId.cover)
    assert result.verdict is CLEAR


@pytest.mark.parametrize("heard, heard_text", [(505_001, "₹5,05,001"), (494_999, "₹4,94,999")])
def test_cover_more_than_one_percent_off_flags_low(heard, heard_text):
    flag = assert_one_flag(run(belief_changes={"cover_inr": said(heard)}), RuleId.cover, LOW)
    assert "₹5,00,000" in flag.expected
    assert heard_text in flag.heard


@pytest.mark.parametrize("heard", [35, 37, 3, 360])
def test_term_must_match_exactly(heard):
    flag = assert_one_flag(run(belief_changes={"term_months": said(heard)}), RuleId.term, LOW)
    assert "36" in flag.expected and str(heard) in flag.heard


# --- cancel window -----------------------------------------------------------


NO_WINDOW = {"cancel_window_days": None}


@pytest.mark.parametrize("days", [30, 29, 31])
def test_cancel_window_within_a_day_of_the_record_passes(days):
    result = run(belief_changes={"cancel_window_days": said(days)})
    assert_passes(result, RuleId.cancel_window)
    assert result.verdict is CLEAR


@pytest.mark.parametrize("days", [28, 32, 15, 365])
def test_cancel_window_stated_wrong_flags_low(days):
    flag = assert_one_flag(run(belief_changes={"cancel_window_days": said(days)}), RuleId.cancel_window, LOW)
    assert "30 days" in flag.expected and f"{days} days" in flag.heard


def test_customer_not_told_it_can_be_cancelled_flags_low():
    assert_one_flag(run(belief_changes={"cancel_allowed": said(False)}), RuleId.cancel_window, LOW)


def test_customer_not_told_it_can_be_cancelled_flags_whatever_the_window_answer():
    changes = {"cancel_allowed": said(False), "cancel_window_days": NotAsked()}
    assert_one_flag(run(belief_changes=changes), RuleId.cancel_window, LOW)


def test_knowing_it_can_be_cancelled_without_a_usable_by_when_is_a_gap_not_a_pass():
    result = run(belief_changes={"cancel_window_days": Unclear()})
    (gap,) = gaps(result, RuleId.cancel_window)
    assert gap.reason is GapReason.no_usable_answer
    assert result.verdict is UNCLEAR


def test_no_window_on_record_and_customer_was_told_none_passes():
    for answer in (said(False), dont_know()):
        result = run(NO_WINDOW, {"cancel_allowed": answer, "cancel_window_days": NotAsked()})
        assert_passes(result, RuleId.cancel_window)
        assert result.verdict is CLEAR


def test_no_window_on_record_but_customer_was_told_it_can_be_cancelled_flags_low():
    flag = assert_one_flag(run(NO_WINDOW), RuleId.cancel_window, LOW)
    assert "no cancellation window" in flag.expected


@pytest.mark.parametrize("answer", [NotAsked(), Unclear()])
def test_no_window_on_record_still_needs_the_question(answer):
    result = run(NO_WINDOW, {"cancel_allowed": answer})
    assert gaps(result, RuleId.cancel_window)
    assert result.verdict is UNCLEAR


# --- recall ------------------------------------------------------------------


def test_recall_not_asked_is_a_gap_for_the_product_and_the_case():
    result = run(recall=recall_of(asked=False))
    (gap,) = gaps(result, RuleId.recall)
    assert gap.reason is GapReason.not_asked
    (case_gap,) = result.case_gaps
    assert (case_gap.rule_id, case_gap.reason, case_gap.product_id) == (
        RuleId.recall_unmatched,
        GapReason.not_asked,
        None,
    )
    assert result.products[0].verdict is UNCLEAR
    assert result.verdict is UNCLEAR


def test_recall_without_the_product_flags_low_and_quotes_the_answer():
    result = run(recall=recall_of())
    flag = assert_one_flag(result, RuleId.recall, LOW, quoted=False)
    assert (flag.quote, flag.turn_id) == ("recall answer", 3)


def test_recall_without_any_answer_still_flags():
    result = run(recall=OpenRecall(asked=True))
    flag = assert_one_flag(result, RuleId.recall, LOW, quoted=False)
    assert flag.quote is None


@pytest.mark.parametrize("kind", [KindClaim.insurance, KindClaim.deposit, KindClaim.investment])
def test_unmatched_recall_of_a_financial_product_is_a_case_flag(kind):
    extra = named(None, kind, "aur ek alag cheez")
    result = run(recall=recall_of(named(P1), extra))
    (flag,) = result.case_flags
    assert (flag.rule_id, flag.severity, flag.product_id) == (RuleId.recall_unmatched, MEDIUM, None)
    assert (flag.clause, flag.quote, flag.turn_id) == (
        CLAUSES[BANK][RuleId.recall_unmatched],
        "aur ek alag cheez",
        3,
    )
    assert result.unmatched_recall == (extra,)
    assert result.products[0].verdict is CLEAR
    assert result.verdict is FLAGGED


def test_unmatched_recall_of_a_fee_is_listed_but_not_flagged():
    extra = named(None, KindClaim.fee, "processing fee")
    result = run(recall=recall_of(named(P1), extra))
    assert not result.case_flags and not result.case_gaps
    assert result.unmatched_recall == (extra,)
    assert result.verdict is CLEAR


@pytest.mark.parametrize("kind", [KindClaim.other, None])
def test_unmatched_recall_of_an_unclassified_thing_needs_a_human(kind):
    extra = named(None, kind, "aur bees hazaar kate, pata nahin kyon")
    result = run(recall=recall_of(named(P1), extra))
    (gap,) = result.case_gaps
    assert (gap.rule_id, gap.reason, gap.product_id) == (
        RuleId.recall_unmatched,
        GapReason.no_usable_answer,
        None,
    )
    assert (gap.quote, gap.turn_id) == ("aur bees hazaar kate, pata nahin kyon", 3)
    assert not result.case_flags
    assert result.products[0].verdict is CLEAR
    assert result.verdict is UNCLEAR


def test_each_unmatched_financial_item_gets_its_own_flag():
    result = run(
        recall=recall_of(named(P1), named(None, KindClaim.deposit), named(None, KindClaim.investment))
    )
    assert len(result.case_flags) == 2
    assert len(result.unmatched_recall) == 2


# --- consent -----------------------------------------------------------------


def test_no_consent_record_flags_high_from_the_record_alone():
    result = run(
        {"consent": None, "paid_from_loan": False}, {"payment_source": said(PaymentSource.separately)}
    )
    assert_one_flag(result, RuleId.consent, HIGH)  # quote comes from the consent answer


def test_no_consent_record_flags_even_when_nothing_was_asked():
    result = evaluate(record(product(consent=None)), beliefs(ProductBeliefs(product_id=P1)))
    flag = assert_one_flag(result, RuleId.consent, HIGH, quoted=False)
    assert flag.quote is None and flag.turn_id is None


def test_a_consent_record_the_customer_does_not_recognise_flags_high():
    flag = assert_one_flag(run(belief_changes={"consent_given": said(False)}), RuleId.consent, HIGH)
    assert "an OTP on 2027-01-05" in flag.expected


@pytest.mark.parametrize("answer", [NotAsked(), Unclear(), unclear(GapReason.quote_not_grounded)])
def test_a_consent_record_on_file_does_not_clear_the_check_by_itself(answer):
    result = run(belief_changes={"consent_given": answer, "consent_method": answer})
    assert gaps(result, RuleId.consent)
    assert RuleId.consent not in result.products[0].passed
    assert result.verdict is UNCLEAR


@pytest.mark.parametrize("method", [m for m in ConsentMethod if m is not ConsentMethod.otp])
def test_a_different_way_of_agreeing_than_the_record_flags_medium(method):
    changes = {"consent_method": said(method, "form par sign kiya tha", 30)}
    flag = assert_one_flag(run(belief_changes=changes), RuleId.consent, MEDIUM, quoted=False)
    assert (flag.quote, flag.turn_id) == ("form par sign kiya tha", 30)


@pytest.mark.parametrize(
    "method, reason",
    [
        (NotAsked(), GapReason.not_asked),
        (Unclear(), GapReason.no_usable_answer),
        (unclear(GapReason.quote_not_grounded), GapReason.quote_not_grounded),
        (dont_know(), GapReason.no_usable_answer),
    ],
)
def test_naming_the_product_without_a_usable_way_of_agreeing_is_a_gap_not_a_pass(method, reason):
    result = run(belief_changes={"consent_method": method})
    (gap,) = gaps(result, RuleId.consent)
    assert gap.reason is reason
    assert RuleId.consent not in result.products[0].passed
    assert result.verdict is UNCLEAR


# --- loan funded -------------------------------------------------------------

NOT_FROM_LOAN = {"paid_from_loan": False}


def test_deducted_from_loan_without_consent_flags_high_from_the_record_alone():
    result = run({"consent": None})
    assert_one_flag(result, RuleId.loan_funded, HIGH)
    assert_one_flag(result, RuleId.consent, HIGH)


def test_deducted_from_loan_but_customer_says_paid_separately_flags_high():
    result = run(belief_changes={"payment_source": said(PaymentSource.separately)})
    assert_one_flag(result, RuleId.loan_funded, HIGH)


def test_not_deducted_and_customer_agrees_passes():
    result = run(NOT_FROM_LOAN, {"payment_source": said(PaymentSource.separately)})
    assert_passes(result, RuleId.loan_funded)
    assert result.verdict is CLEAR


def test_not_deducted_but_customer_says_deducted_flags_medium():
    assert_one_flag(run(NOT_FROM_LOAN), RuleId.loan_funded, MEDIUM)


def test_not_deducted_and_customer_does_not_know_is_a_gap_and_engages_no_paragraph():
    result = run(NOT_FROM_LOAN, {"payment_source": dont_know()})
    (gap,) = gaps(result, RuleId.loan_funded)
    assert (gap.reason, gap.quote) == (GapReason.no_usable_answer, QUOTE)
    assert not flags(result, RuleId.loan_funded) and result.products[0].evidence_pack is None
    assert result.verdict is UNCLEAR


def test_a_flag_never_quotes_an_answer_that_was_not_usable():
    unusable = unclear(GapReason.quote_not_grounded)
    result = run(
        {"consent": None, "required_for_loan": True, "provider_choice_offered": False},
        {"consent_given": unusable, "payment_source": unusable, "required_for_loan": unusable},
    )
    found = [f for f in result.products[0].flags if f.rule_id in (RuleId.consent, RuleId.loan_funded, RuleId.bundling)]
    assert len(found) == 3 and all(f.quote is None and f.turn_id is None for f in found)
    assert result.products[0].evidence_pack.quotes() == ()


def test_a_record_must_state_the_product_features():
    data = product().model_dump()
    del data["features"]
    with pytest.raises(ValidationError):
        Product.model_validate(data)


def test_not_deducted_and_no_consent_still_needs_the_payment_answer():
    result = run(NOT_FROM_LOAN | {"consent": None}, {"payment_source": NotAsked()})
    (gap,) = gaps(result, RuleId.loan_funded)
    assert gap.reason is GapReason.not_asked
    assert result.verdict is FLAGGED  # the consent flag dominates


# --- bundling ----------------------------------------------------------------


REQUIRED = {"required_for_loan": True}
TOLD_REQUIRED = {"required_for_loan": said(True, "bola tha lena hi padega", 20)}
NO_CHOICE = {"provider_choice_offered": said(False, "nahin, kisi aur company ka nahin bataya", 22)}


@pytest.mark.parametrize("believed", [said(True), said(False), NotAsked(), dont_know()])
def test_required_as_a_risk_mitigant_with_a_choice_of_provider_passes(believed):
    result = run(REQUIRED, {"required_for_loan": believed})
    assert_passes(result, RuleId.bundling)
    assert result.verdict is CLEAR


def test_customer_told_it_was_required_passes_when_it_is_a_mitigant_with_a_choice():
    result = run(belief_changes=TOLD_REQUIRED)
    assert_passes(result, RuleId.bundling)
    assert result.verdict is CLEAR


def test_not_required_per_record_and_customer_passes_whatever_the_choice_of_provider():
    for choice in (said(False), NotAsked(), dont_know()):
        for record_choice in (True, False):
            result = run(
                {"provider_choice_offered": record_choice, "risk_mitigant": False},
                {"provider_choice_offered": choice},
            )
            assert_passes(result, RuleId.bundling)
            assert result.verdict is CLEAR


@pytest.mark.parametrize("required", [REQUIRED, {}])
def test_required_and_not_a_risk_mitigant_flags_high_even_with_a_choice_of_provider(required):
    result = run(required | {"risk_mitigant": False}, TOLD_REQUIRED)
    flag = assert_one_flag(result, RuleId.bundling, HIGH, quoted=False)
    assert "risk mitigant" in flag.heard
    assert (flag.quote, flag.turn_id) == ("bola tha lena hi padega", 20)


def test_required_and_not_a_risk_mitigant_flags_from_the_record_alone():
    result = evaluate(
        record(product(required_for_loan=True, risk_mitigant=False)),
        beliefs(ProductBeliefs(product_id=P1)),
    )
    (flag,) = flags(result, RuleId.bundling)
    assert (flag.severity, flag.quote) == (HIGH, None)


@pytest.mark.parametrize("required", [(REQUIRED, {}), ({}, TOLD_REQUIRED)])
def test_required_mitigant_without_a_choice_on_record_flags_high(required):
    on_record, believed = required
    result = run(on_record | {"provider_choice_offered": False}, believed)
    flag = assert_one_flag(result, RuleId.bundling, HIGH, quoted=False)
    assert "no choice of provider" in flag.heard


@pytest.mark.parametrize("required", [(REQUIRED, {}), ({}, TOLD_REQUIRED)])
def test_required_mitigant_and_customer_was_not_told_of_a_choice_flags_high(required):
    on_record, believed = required
    flag = assert_one_flag(run(on_record, believed | NO_CHOICE), RuleId.bundling, HIGH, quoted=False)
    assert (flag.quote, flag.turn_id) == ("nahin, kisi aur company ka nahin bataya", 22)


@pytest.mark.parametrize(
    "described",
    [
        {"kind": said(KindClaim.deposit, "security deposit hai", 9)},
        {"feature_probe": said((FeatureClaim.is_deposit,), "security deposit hai", 9)},
        {
            "volunteered_claims": (
                ClaimEvidence(claim=FeatureClaim.is_deposit, evidence=ev("security deposit hai", 9)),
            )
        },
    ],
)
def test_a_required_product_described_as_a_deposit_is_never_a_risk_mitigant(described):
    result = run(REQUIRED, described)  # the record says risk mitigant, with a choice of provider
    (flag,) = flags(result, RuleId.bundling)
    assert (flag.severity, flag.quote, flag.turn_id) == (HIGH, "security deposit hai", 9)
    assert "deposit" in flag.heard


def test_required_product_called_a_deposit_in_open_recall_flags_bundling():
    result = run(REQUIRED, recall=recall_of(named(P1, KindClaim.deposit, "ek FD")))
    (flag,) = flags(result, RuleId.bundling)
    assert flag.quote == "ek FD"


def test_each_bundling_reason_is_its_own_flag():
    result = run(REQUIRED | {"risk_mitigant": False, "provider_choice_offered": False}, NO_CHOICE)
    assert len(flags(result, RuleId.bundling)) == 3


@pytest.mark.parametrize(
    "choice, reason", [(NotAsked(), GapReason.not_asked), (dont_know(), GapReason.no_usable_answer)]
)
@pytest.mark.parametrize("required", [(REQUIRED, {}), ({}, TOLD_REQUIRED)])
def test_required_mitigant_needs_the_customers_answer_on_choice_of_provider(required, choice, reason):
    on_record, believed = required
    result = run(on_record, believed | {"provider_choice_offered": choice})
    (gap,) = gaps(result, RuleId.bundling)
    assert gap.reason is reason
    assert result.verdict is UNCLEAR


def test_not_knowing_whether_it_was_required_is_a_gap_not_a_flag():
    result = run(belief_changes={"required_for_loan": dont_know()})
    (gap,) = gaps(result, RuleId.bundling)
    assert (gap.reason, gap.quote) == (GapReason.no_usable_answer, QUOTE)
    assert not flags(result, RuleId.bundling)
    assert result.verdict is UNCLEAR


# --- feature belief ----------------------------------------------------------

NOT_A_FEATURE = [c for c in FeatureClaim if c is not FeatureClaim.one_time_payment]


@pytest.mark.parametrize("claim", NOT_A_FEATURE)
def test_volunteered_claim_the_product_does_not_have_flags_high(claim):
    volunteered = (ClaimEvidence(claim=claim, evidence=ev()),)
    assert_one_flag(run(belief_changes={"volunteered_claims": volunteered}), RuleId.belief_mismatch, HIGH)


@pytest.mark.parametrize("claim", NOT_A_FEATURE)
def test_probed_claim_the_product_does_not_have_flags_high(claim):
    assert_one_flag(run(belief_changes={"feature_probe": said((claim,))}), RuleId.belief_mismatch, HIGH)


def test_claims_the_product_does_have_pass():
    true_claim = FeatureClaim.one_time_payment
    changes = {
        "feature_probe": said((true_claim,)),
        "volunteered_claims": (ClaimEvidence(claim=true_claim, evidence=ev()),),
    }
    result = run(belief_changes=changes)
    assert_passes(result, RuleId.belief_mismatch)
    assert result.verdict is CLEAR


def test_claim_true_of_this_product_passes_when_the_record_lists_it():
    result = run(
        {"features": frozenset({FeatureClaim.refundable_anytime})},
        {"feature_probe": said((FeatureClaim.refundable_anytime,))},
    )
    assert_passes(result, RuleId.belief_mismatch)


def test_calling_it_a_deposit_is_also_a_feature_flag():
    result = run(belief_changes={"kind": said(KindClaim.deposit)})
    assert_one_flag(result, RuleId.belief_mismatch, HIGH)
    assert_one_flag(result, RuleId.kind, HIGH)


def test_same_claim_from_several_sources_is_one_flag_and_distinct_claims_are_separate():
    changes = {
        "kind": said(KindClaim.deposit, "FD hai", 9),
        "feature_probe": said((FeatureClaim.is_deposit, FeatureClaim.guaranteed_return), "probe", 15),
        "volunteered_claims": (
            ClaimEvidence(claim=FeatureClaim.guaranteed_return, evidence=ev("pakka return", 11)),
        ),
    }
    result = run(belief_changes=changes)
    assert [f.quote for f in flags(result, RuleId.belief_mismatch)] == ["pakka return", "probe"]


def test_volunteered_contradiction_flags_even_when_the_probe_was_never_asked():
    changes = {
        "feature_probe": NotAsked(),
        "volunteered_claims": (ClaimEvidence(claim=FeatureClaim.refundable_anytime, evidence=ev()),),
    }
    assert_one_flag(run(belief_changes=changes), RuleId.belief_mismatch, HIGH)


def test_true_volunteered_claim_does_not_stand_in_for_the_probe():
    changes = {
        "feature_probe": NotAsked(),
        "volunteered_claims": (ClaimEvidence(claim=FeatureClaim.one_time_payment, evidence=ev()),),
    }
    result = run(belief_changes=changes)
    assert gaps(result, RuleId.belief_mismatch)
    assert result.verdict is UNCLEAR


# --- evidence ----------------------------------------------------------------


def test_ungrounded_quote_on_a_product_is_a_gap_per_quote():
    result = run(belief_changes={"ungrounded": (ev("made up", 5), ev("also made up", 6))})
    found = gaps(result, RuleId.evidence)
    assert [(g.reason, g.quote, g.turn_id) for g in found] == [
        (GapReason.quote_not_grounded, "made up", 5),
        (GapReason.quote_not_grounded, "also made up", 6),
    ]
    assert RuleId.evidence not in result.products[0].passed
    assert result.verdict is UNCLEAR


def test_ungrounded_case_level_quote_is_a_case_gap():
    result = run(ungrounded=(ev("made up", 5),))
    (gap,) = result.case_gaps
    assert (gap.rule_id, gap.reason, gap.product_id, gap.quote) == (
        RuleId.evidence,
        GapReason.quote_not_grounded,
        None,
        "made up",
    )
    assert result.products[0].verdict is CLEAR
    assert result.verdict is UNCLEAR


# --- invariants --------------------------------------------------------------


def test_empty_product_beliefs_are_never_clear():
    # recall named the product -> gaps only; recall asked but product not named -> the recall flag
    cases = [(recall_of(named(P1)), UNCLEAR), (recall_of(asked=False), UNCLEAR), (recall_of(), FLAGGED)]
    for recall, expected in cases:
        result = evaluate(record(), beliefs(ProductBeliefs(product_id=P1), recall=recall))
        assert result.verdict is expected
        assert result.products[0].verdict is expected
        assert len(result.products[0].gaps) == len(RULES_NEEDING_AN_ANSWER) + (not recall.asked)


def test_product_on_record_with_no_beliefs_at_all_is_never_clear():
    empty = Beliefs(
        call_id="CALL-TEST-0000",
        loan_id="LN-TEST-0000",
        language=Language.hi,
        recall=OpenRecall(asked=False),
        products=(),
    )
    result = evaluate(record(), empty)
    assert result.verdict is UNCLEAR
    assert result.products[0].passed == (RuleId.evidence,)
    assert len(result.products[0].gaps) == len(PER_PRODUCT_RULES) - 1


def test_flags_dominate_gaps():
    result = run(belief_changes={"premium_inr": NotAsked(), "cancel_allowed": said(False)})
    assert gaps(result, RuleId.premium) and flags(result, RuleId.cancel_window)
    assert result.products[0].verdict is FLAGGED
    assert result.verdict is FLAGGED


def test_verdict_of():
    passed = Passed(rule_id=RuleId.kind, product_id=P1)
    gap = Gap(rule_id=RuleId.kind, clause="x", product_id=P1, reason=GapReason.not_asked)
    flag = Flag(rule_id=RuleId.kind, clause="x", product_id=P1, severity=LOW, expected="a", heard="b")
    assert verdict_of([]) is CLEAR
    assert verdict_of([passed]) is CLEAR
    assert verdict_of([passed, gap]) is UNCLEAR
    assert verdict_of([gap, passed, flag]) is FLAGGED
    assert verdict_of(iter([flag, gap])) is FLAGGED


@pytest.mark.parametrize(
    "second, second_verdict, case_verdict",
    [
        ({"kind": said(KindClaim.deposit)}, FLAGGED, FLAGGED),
        ({"term_months": NotAsked()}, UNCLEAR, UNCLEAR),
        ({}, CLEAR, CLEAR),
    ],
)
def test_products_are_judged_separately_and_the_case_takes_the_worst(second, second_verdict, case_verdict):
    rec = record(product(P1), product(P2))
    result = evaluate(rec, beliefs(product_beliefs(P1), product_beliefs(P2, **second)))
    first, other = result.products
    assert (first.product_id, first.verdict) == (P1, CLEAR)
    assert not first.flags and not first.gaps
    assert (other.product_id, other.verdict) == (P2, second_verdict)
    assert result.verdict is case_verdict


def test_recall_is_matched_per_product():
    rec = record(product(P1), product(P2))
    result = evaluate(rec, beliefs(product_beliefs(P1), product_beliefs(P2), recall=recall_of(named(P1))))
    first, other = result.products
    assert first.verdict is CLEAR
    assert [f.rule_id for f in other.flags] == [RuleId.recall]


def test_every_rule_id_has_exactly_one_spec_and_a_clause_for_each_lender_type():
    assert [spec.id for spec in RULES] == list(RuleId)
    assert set(CLAUSES) == set(LenderType)
    for lender_type in LenderType:
        assert set(CLAUSES[lender_type]) == set(RuleId)
        for spec in RULES:
            assert spec.clause(lender_type) == CLAUSES[lender_type][spec.id]
    for spec in RULES:
        assert spec.title.endswith(".") and callable(spec.check)


def test_rule_ids_are_the_neutral_names_in_the_design():
    assert [r.value for r in RuleId] == [r.name for r in RuleId]
    assert {"kind", "premium", "cover", "term", "cancel_window", "consent", "bundling", "loan_funded"} < {
        r.value for r in RuleId
    }
    assert RuleId.belief_mismatch == "belief_mismatch"


# DESIGN.md section 6; verified in references/claims/claims-ledger.md rows A5 and A19.
PARAGRAPHS = {
    BANK: {"feedback": "85Y", "consent": "85G", "bundling": "85V", "loan_funded": "85W", "belief": "4(20A)(ii)"},
    NBFC: {
        "feedback": "101Y",
        "consent": "101G",
        "bundling": "101V",
        "loan_funded": "101W",
        "belief": "6(9A)(ii)",
    },
}


@pytest.mark.parametrize("lender_type", list(LenderType))
def test_clauses_are_looked_up_by_lender_type(lender_type):
    want = PARAGRAPHS[lender_type]
    clauses = CLAUSES[lender_type]
    for rule in (RuleId.kind, RuleId.premium, RuleId.cover, RuleId.term, RuleId.cancel_window):
        assert clauses[rule] == want["feedback"]
    assert clauses[RuleId.consent] == want["consent"]
    assert clauses[RuleId.bundling] == want["bundling"]
    assert clauses[RuleId.loan_funded] == want["loan_funded"]
    assert clauses[RuleId.belief_mismatch] == want["belief"]


@pytest.mark.parametrize("lender_type", list(LenderType))
def test_flags_and_gaps_carry_the_paragraph_for_the_lender_on_the_record(lender_type):
    worst = {
        "kind": said(KindClaim.deposit),
        "consent_given": said(False),
        "payment_source": said(PaymentSource.separately),
        "provider_choice_offered": said(False),
        "term_months": NotAsked(),
    }
    result = run(REQUIRED, worst, lender_type=lender_type)
    found = {o.rule_id: o.clause for o in (*result.all_flags(), *result.all_gaps())}
    assert set(found) == {
        RuleId.kind,
        RuleId.consent,
        RuleId.loan_funded,
        RuleId.bundling,
        RuleId.belief_mismatch,
        RuleId.term,
    }
    assert found == {rule: CLAUSES[lender_type][rule] for rule in found}
    assert result.products[0].evidence_pack.lender_type is lender_type


def test_evaluate_is_deterministic_and_the_result_round_trips_through_json():
    for rec, bel in (demo_case(), (record(), beliefs()), (record(), beliefs(ProductBeliefs(product_id=P1)))):
        result = evaluate(rec, bel)
        assert evaluate(rec, bel) == result
        assert evaluate(rec.model_copy(deep=True), bel.model_copy(deep=True)) == result
        assert CaseResult.model_validate_json(result.model_dump_json()) == result


# --- bad input ---------------------------------------------------------------


def test_beliefs_about_a_product_not_on_record_are_rejected():
    with pytest.raises(ValueError, match="not on the record"):
        evaluate(record(), beliefs(product_beliefs(P1), product_beliefs(P2), recall=recall_of(named(P1))))


def test_two_beliefs_for_one_product_are_rejected():
    with pytest.raises(ValueError, match="more than once"):
        evaluate(record(), beliefs(product_beliefs(P1), product_beliefs(P1, kind=said(KindClaim.deposit))))


def test_recall_item_matched_to_a_product_not_on_record_is_rejected():
    with pytest.raises(ValueError, match="not on the record"):
        evaluate(record(), beliefs(recall=recall_of(named(P1), named(P2, KindClaim.deposit))))


def test_beliefs_from_another_loan_are_rejected():
    other_loan = record().model_copy(update={"loan_id": "LN-OTHER-9999"})
    with pytest.raises(ValueError, match="LN-OTHER-9999"):
        evaluate(other_loan, beliefs())


# --- conduct of the sale ------------------------------------------------------


@pytest.mark.parametrize("concern", list(SaleConcern))
def test_a_voiced_concern_about_the_sale_flags_high_even_when_every_answer_is_right(concern):
    said_it = ConcernEvidence(concern=concern, evidence=ev("sab mein haan bolne ko kaha tha", 24))
    result = evaluate(record(), beliefs(sale_concerns=(said_it,)))
    (flag,) = result.case_flags
    assert (flag.rule_id, flag.severity, flag.product_id) == (RuleId.sale_conduct, HIGH, None)
    assert (flag.quote, flag.turn_id) == ("sab mein haan bolne ko kaha tha", 24)
    assert result.products[0].verdict is CLEAR
    assert result.verdict is FLAGGED


# --- results must be self-consistent ------------------------------------------


def test_a_result_cannot_claim_a_verdict_its_flags_and_gaps_do_not_support():
    flagged = run(belief_changes={"kind": said(KindClaim.deposit)})
    for verdict in (CLEAR, UNCLEAR):
        with pytest.raises(ValidationError):
            CaseResult.model_validate(flagged.model_dump() | {"verdict": verdict})
        with pytest.raises(ValidationError):
            ProductResult.model_validate(flagged.products[0].model_dump() | {"verdict": verdict})
    with pytest.raises(ValidationError):
        CaseResult.model_validate(run().model_dump() | {"verdict": FLAGGED})


def test_flag_and_gap_keys_are_the_stable_part_of_a_result():
    result = run(belief_changes={"kind": said(KindClaim.deposit), "term_months": NotAsked()})
    assert result.flag_keys() == {(P1, RuleId.kind, HIGH), (P1, RuleId.belief_mismatch, HIGH)}
    assert result.gap_keys() == {(P1, RuleId.term, GapReason.not_asked)}


# --- evidence pack -------------------------------------------------------------

PACK_RULES = [RuleId.kind, RuleId.premium, RuleId.consent, RuleId.loan_funded, RuleId.bundling]
PACK_TRIGGERS = {
    RuleId.kind: ({}, {"kind": said(KindClaim.fee)}),
    RuleId.premium: ({}, {"premium_inr": said(60_000)}),
    RuleId.consent: ({}, {"consent_given": said(False)}),
    RuleId.loan_funded: ({}, {"payment_source": said(PaymentSource.separately)}),
    RuleId.bundling: ({"required_for_loan": True}, {"provider_choice_offered": said(False)}),
}
NO_PACK_TRIGGERS = {
    RuleId.cover: {"cover_inr": said(1)},
    RuleId.term: {"term_months": said(1)},
    RuleId.cancel_window: {"cancel_allowed": said(False)},
    RuleId.belief_mismatch: {"feature_probe": said((FeatureClaim.guaranteed_return,))},
}


def test_the_pack_rules_are_kind_premium_consent_bundling_and_loan_funded():
    assert set(PACK_TRIGGERS) == set(PACK_RULES) == set(EVIDENCE_PACK_RULES)


@pytest.mark.parametrize("rule", PACK_RULES)
def test_a_flag_under_a_pack_rule_yields_an_evidence_pack(rule):
    on_record, believed = PACK_TRIGGERS[rule]
    result = run(on_record, believed)
    (p,) = result.products
    pack = p.evidence_pack
    assert isinstance(pack, EvidencePack)
    assert pack.flags == tuple(flags(result, rule)) == p.flags
    assert (pack.loan_id, pack.call_id, pack.lender_type) == ("LN-TEST-0000", "CALL-TEST-0000", BANK)
    assert pack.product == product(**on_record)
    assert pack.quotes() == (ev(),)
    assert pack.clauses() == (CLAUSES[BANK][rule],)
    assert result.evidence_packs() == (pack,)


@pytest.mark.parametrize("rule", NO_PACK_TRIGGERS)
def test_a_flag_under_any_other_rule_yields_no_evidence_pack(rule):
    result = run(belief_changes=NO_PACK_TRIGGERS[rule])
    assert flags(result, rule) and result.verdict is FLAGGED
    assert result.products[0].evidence_pack is None
    assert result.evidence_packs() == ()


def test_case_level_flags_and_gaps_yield_no_evidence_pack():
    concern = ConcernEvidence(concern=SaleConcern.coached_answers, evidence=ev())
    result = evaluate(record(), beliefs(sale_concerns=(concern,), recall=recall_of(named(P1), named(None))))
    assert result.case_flags and result.case_gaps
    assert result.evidence_packs() == ()


def test_clear_and_unclear_products_have_no_evidence_pack():
    assert run().products[0].evidence_pack is None
    assert run(belief_changes={"kind": NotAsked()}, recall=recall_of(named(P1))).evidence_packs() == ()


def test_the_pack_leaves_out_flags_under_other_rules():
    result = run(belief_changes={"kind": said(KindClaim.deposit, "FD hai", 9), "term_months": said(1)})
    (p,) = result.products
    assert {f.rule_id for f in p.flags} == {RuleId.kind, RuleId.term, RuleId.belief_mismatch}
    assert [f.rule_id for f in p.evidence_pack.flags] == [RuleId.kind]
    assert p.evidence_pack.quotes() == (ev("FD hai", 9),)


def test_a_result_cannot_carry_a_pack_that_does_not_match_its_flags():
    flagged = run(belief_changes={"kind": said(KindClaim.deposit)}).products[0]
    with pytest.raises(ValidationError):
        ProductResult.model_validate(flagged.model_dump() | {"evidence_pack": None})
    with pytest.raises(ValidationError):
        ProductResult.model_validate(
            run().products[0].model_dump() | {"evidence_pack": flagged.evidence_pack.model_dump()}
        )
    with pytest.raises(ValidationError):
        EvidencePack.model_validate(flagged.evidence_pack.model_dump() | {"flags": []})
    other = run(belief_changes={"term_months": said(1)}).products[0].flags
    with pytest.raises(ValidationError):
        EvidencePack.model_validate(
            flagged.evidence_pack.model_dump() | {"flags": [f.model_dump() for f in other]}
        )


# --- the demo case (DESIGN.md section 10) ------------------------------------

DEMO_QUOTE = "bas ek FD, loan security ke liye, bavan hazaar"


def demo_case() -> tuple[LoanRecord, Beliefs]:
    """Gold loan, ₹52,000 deducted, no consent record; the customer calls it an FD in open recall."""
    answer = Evidence(quote=DEMO_QUOTE, turn_id=TurnId(6))
    item = RecallItem(evidence=answer, kind=KindClaim.deposit, amount_inr=52_000, product_id=P1)
    bel = Beliefs(
        call_id="CALL-DEMO-0000",
        loan_id="LN-TEST-0000",
        language=Language.hi_en,
        recall=OpenRecall(asked=True, answer=answer, items=(item,)),
        products=(ProductBeliefs(product_id=P1),),
    )
    return record(product(consent=None)), bel


def test_demo_case_flags_kind_feature_belief_loan_funded_and_consent():
    result = evaluate(*demo_case())
    assert result.verdict is FLAGGED
    (p,) = result.products
    assert p.verdict is FLAGGED
    by_rule = {f.rule_id: f for f in p.flags}
    assert set(by_rule) == {RuleId.kind, RuleId.belief_mismatch, RuleId.loan_funded, RuleId.consent}
    assert len(p.flags) == 4
    assert all(f.severity is HIGH for f in p.flags)
    for rule in (RuleId.kind, RuleId.belief_mismatch):
        assert (by_rule[rule].quote, by_rule[rule].turn_id) == (DEMO_QUOTE, 6)
    assert all(f.clause == CLAUSES[BANK][f.rule_id] for f in p.flags)
    assert set(p.passed) == {RuleId.recall, RuleId.evidence}
    assert not result.case_flags and not result.case_gaps
    pack = p.evidence_pack
    assert [f.rule_id for f in pack.flags] == [RuleId.kind, RuleId.consent, RuleId.loan_funded]
    assert pack.clauses() == ("85Y", "85G", "85W")
    assert by_rule[RuleId.belief_mismatch].clause == "4(20A)(ii)"
    assert pack.quotes() == (Evidence(quote=DEMO_QUOTE, turn_id=TurnId(6)),)
    assert pack.product.consent is None and pack.product.premium_inr == 52_000


# --- wording and imports -----------------------------------------------------

# "refundable" stays legal: it names a belief the customer may hold (FeatureClaim.refundable_anytime).
BANNED = re.compile(r"mis[-_ ]?s(?:ell|old)|violat|fraud|refund(?!able)", re.IGNORECASE)


def test_core_source_never_uses_banned_words():
    package = Path(samajh.rules.__file__).parent.parent
    sources = sorted(
        [*(package / "rules").glob("*.py"), *(package / "amounts").glob("*.py"), package / "types.py"]
    )
    assert {"checks.py", "clauses.py", "engine.py", "normalise.py", "types.py"} <= {s.name for s in sources}
    for source in sources:
        assert not BANNED.search(source.read_text(encoding="utf-8")), source.name


def everything_flagged() -> CaseResult:
    """A case that raises every flag and gap the engine can word."""
    worst = product_beliefs(
        P1,
        kind=said(KindClaim.deposit),
        payment_source=said(PaymentSource.separately),
        required_for_loan=said(True),
        provider_choice_offered=said(False),
        cancel_allowed=said(False),
        consent_given=said(False),
        feature_probe=said(tuple(FeatureClaim)),
        premium_inr=said(1),
        cover_inr=said(1),
        term_months=said(1),
        ungrounded=(ev(),),
    )
    unsure = {name: dont_know() for name in ANSWER_FIELDS}
    wrong = product_beliefs(
        ProductId("P3"), cancel_window_days=said(7), consent_method=said(ConsentMethod.signed_form)
    )
    rec = record(
        product(P1, provider_choice_offered=False),
        product(P2, paid_from_loan=False),
        product(ProductId("P3"), required_for_loan=True, risk_mitigant=False),
        product(ProductId("P4"), cancel_window_days=None),
    )
    off_record = [named(None, k) for k in KindClaim]
    concerns = tuple(ConcernEvidence(concern=c, evidence=ev()) for c in SaleConcern)
    bel = beliefs(
        worst,
        product_beliefs(P2, **unsure),
        wrong,
        product_beliefs(ProductId("P4")),
        recall=recall_of(*off_record),
        ungrounded=(ev(),),
        sale_concerns=concerns,
    )
    return evaluate(rec, bel)


def test_no_result_ever_contains_banned_words():
    results = [
        everything_flagged(),
        evaluate(*demo_case()),
        run(),
        run({"consent": None, "paid_from_loan": False}),
    ]
    results += [run(NOT_FROM_LOAN, {"payment_source": said(PaymentSource.from_loan)})]
    assert {f.rule_id for r in results for p in r.products for f in p.flags} | {
        f.rule_id for r in results for f in r.case_flags
    } == set(RuleId) - {RuleId.evidence}
    for result in results:
        assert not BANNED.search(result.model_dump_json())
    for spec in RULES:
        assert not BANNED.search(spec.title)


def test_rules_package_imports_no_network_llm_or_client_code():
    code = (
        "import sys, samajh.rules\n"
        "banned = ('httpx', 'httpcore', 'requests', 'urllib3', 'aiohttp', 'openai', 'anthropic',"
        " 'dotenv', 'fastapi', 'samajh.clients', 'samajh.extract')\n"
        "print(sorted(m for m in sys.modules if m.startswith(banned)))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
