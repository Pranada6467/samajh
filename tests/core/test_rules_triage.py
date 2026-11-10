"""Decision chain v2: approximate amounts, conflicting answers, denial in recall, payment
frequency, unscreened replies, and the triage tier. Expected results come from
references/pilots/P3a-contract.md, not from running the code.
"""

import pytest
from test_rules_engine import (
    CLAUSES,
    P1,
    P2,
    beliefs,
    dont_know,
    ev,
    flags,
    gaps,
    named,
    product,
    product_beliefs,
    recall_of,
    record,
    run,
    said,
    unclear,
)

from samajh.rules import evaluate
from samajh.rules.checks import APPROX_AMOUNT_TOLERANCE_PERCENT
from samajh.types import (
    REFER_RULES,
    AnswerConflict,
    ClaimEvidence,
    ConcernEvidence,
    ConsentMethod,
    FeatureClaim,
    FlagReason,
    GapReason,
    KindClaim,
    LenderType,
    NotAsked,
    OpenRecall,
    PaymentFrequency,
    PaymentSource,
    Question,
    RuleId,
    SaleConcern,
    Severity,
    Stated,
    Tier,
    Verdict,
)

HIGH, MEDIUM, LOW = Severity.high, Severity.medium, Severity.low
R = FlagReason


def about(value: int, low: int | None = None, hedged: bool = False) -> Stated:
    """An amount said as "about X", or as a range from `low` to `value`."""
    return Stated(value=value, evidence=ev(), approximate=True, low=low, hedged=hedged)


def one_flag(result, rule: RuleId):
    (flag,) = flags(result, rule)
    assert rule not in result.products[0].passed
    return flag


# --- premium: record 52,000 ----------------------------------------------------


def test_the_approximate_tolerance_is_ten_percent():
    assert APPROX_AMOUNT_TOLERANCE_PERCENT == 10


@pytest.mark.parametrize(
    "answer",
    [said(50_000), about(50_000), about(55_000, low=50_000), about(50_000, hedged=True)],
)
def test_a_confirmed_premium_near_the_record_is_a_low_approximate_flag(answer):
    result = run(belief_changes={"premium_inr": answer})
    flag = one_flag(result, RuleId.premium)
    assert (flag.reason, flag.severity, flag.tier) == (R.premium_approximate, LOW, Tier.understanding_gap)
    assert result.tier is Tier.understanding_gap


def test_a_confirmed_approximate_single_figure_within_one_percent_passes():
    result = run(belief_changes={"premium_inr": about(52_000)})
    assert RuleId.premium in result.products[0].passed
    assert result.tier is Tier.clear


@pytest.mark.parametrize("low, high", [(50_000, 52_000), (52_000, 55_000), (51_900, 52_100)])
def test_a_range_is_never_exact_even_when_an_end_is_the_record(low, high):
    flag = one_flag(run(belief_changes={"premium_inr": about(high, low=low)}), RuleId.premium)
    assert flag.reason is R.premium_approximate


# near means |record - stated| * 100 <= stated * 10, in integers: 47,273 to 57,777 for 52,000
@pytest.mark.parametrize(
    "heard, reason",
    [
        (47_273, R.premium_approximate),
        (47_272, R.premium_differs_confirmed),
        (57_777, R.premium_approximate),
        (57_778, R.premium_differs_confirmed),
    ],
)
def test_the_approximate_tolerance_uses_exact_integer_arithmetic(heard, reason):
    assert one_flag(run(belief_changes={"premium_inr": said(heard)}), RuleId.premium).reason is reason


# a range holds the record when low * 90 <= record * 100 <= high * 110
@pytest.mark.parametrize(
    "low, high, reason",
    [
        (40_000, 47_273, R.premium_approximate),
        (40_000, 47_272, R.premium_differs_confirmed),
        (57_777, 70_000, R.premium_approximate),
        (57_778, 70_000, R.premium_differs_confirmed),
        (30_000, 90_000, R.premium_approximate),
    ],
)
def test_a_range_is_near_when_the_record_lies_inside_it_widened_by_the_tolerance(low, high, reason):
    flag = one_flag(run(belief_changes={"premium_inr": about(high, low=low)}), RuleId.premium)
    assert flag.reason is reason


@pytest.mark.parametrize("readback", [NotAsked(), unclear(), dont_know()])
@pytest.mark.parametrize("answer", [about(50_000), about(55_000, low=50_000), about(52_000)])
def test_an_unconfirmed_approximate_premium_near_the_record_is_a_gap_like_an_exact_one(answer, readback):
    result = run(belief_changes={"premium_inr": answer, "premium_readback": readback})
    exact = run(belief_changes={"premium_readback": readback})
    assert not flags(result, RuleId.premium)
    assert [g.reason for g in gaps(result, RuleId.premium)] == [g.reason for g in gaps(exact, RuleId.premium)]
    assert result.tier is Tier.incomplete


@pytest.mark.parametrize("answer", [said(50_000), Stated(value=50_000, evidence=ev(), hedged=True)])
def test_an_unconfirmed_plain_figure_near_the_record_still_flags_as_differing(answer):
    result = run(belief_changes={"premium_inr": answer, "premium_readback": NotAsked()})
    flag = one_flag(result, RuleId.premium)
    assert (flag.reason, flag.severity, flag.tier) == (R.premium_differs, MEDIUM, Tier.incomplete)


@pytest.mark.parametrize(
    "answer",
    [
        Stated(value=70_000, evidence=ev(), hedged=True),
        about(70_000),
        about(70_000, hedged=True),
        about(70_000, low=65_000),
        about(40_000, low=30_000, hedged=True),
    ],
)
@pytest.mark.parametrize(
    "readback, reason, severity",
    [(said(True), R.premium_differs_confirmed, HIGH), (NotAsked(), R.premium_differs, MEDIUM)],
)
def test_a_hedge_or_an_approximation_never_upgrades_a_wrong_premium(answer, readback, reason, severity):
    plain = run(belief_changes={"premium_inr": said(answer.value), "premium_readback": readback})
    hedged = run(belief_changes={"premium_inr": answer, "premium_readback": readback})
    for result in (plain, hedged):
        flag = one_flag(result, RuleId.premium)
        assert (flag.reason, flag.severity) == (reason, severity)
    assert hedged.tier is plain.tier


def test_a_rejected_read_back_is_a_gap_whatever_the_amount():
    result = run(belief_changes={"premium_inr": about(55_000, low=50_000), "premium_readback": said(False)})
    (gap,) = gaps(result, RuleId.premium)
    assert gap.reason is GapReason.readback_rejected
    assert not flags(result, RuleId.premium)


# --- cover: record 5,00,000 ------------------------------------------------------


@pytest.mark.parametrize("answer", [about(480_000), about(500_000, low=400_000), about(460_000, low=400_000)])
def test_an_approximate_cover_near_the_record_passes(answer):
    result = run(belief_changes={"cover_inr": answer})
    assert RuleId.cover in result.products[0].passed and not flags(result, RuleId.cover)


@pytest.mark.parametrize(
    "answer",
    [
        said(480_000),
        Stated(value=480_000, evidence=ev(), hedged=True),
        about(400_000),
        about(440_000, low=400_000),
        about(700_000, low=600_000, hedged=True),
    ],
)
def test_a_plain_cover_keeps_the_one_percent_rule_and_a_far_approximate_one_flags(answer):
    flag = one_flag(run(belief_changes={"cover_inr": answer}), RuleId.cover)
    assert (flag.reason, flag.severity) == (R.cover_differs, LOW)


# --- conflicting answers ---------------------------------------------------------

FIRST, SECOND = ev("FD hai, jama kiya hai", 9), ev("achha, bima", 11)

QUESTION_RULE = {
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


def test_every_question_has_a_rule_for_its_conflicts():
    assert set(QUESTION_RULE) == set(Question)


@pytest.mark.parametrize("question", list(Question))
def test_conflicting_answers_flag_under_the_rule_of_the_question(question):
    rule = QUESTION_RULE[question]
    conflict = AnswerConflict(question=question, answers=(FIRST, SECOND, ev("third", 13)))
    result = run(belief_changes={"conflicts": (conflict,)})
    flag = one_flag(result, rule)
    refer = rule in REFER_RULES
    assert flag.reason is R.answers_conflict
    assert flag.severity is (HIGH if refer else LOW)
    assert flag.tier is (Tier.refer if refer else Tier.understanding_gap)
    assert (flag.quote, flag.turn_id) == (FIRST.quote, FIRST.turn_id)
    assert flag.also == (SECOND, ev("third", 13))
    assert flag.clause == CLAUSES[LenderType.bank][rule]
    assert flag.expected and flag.heard
    assert result.verdict is Verdict.flag_for_review
    assert result.tier is flag.tier


def test_fd_then_bima_on_the_kind_question_ends_refer_with_both_quotes():
    conflict = AnswerConflict(question=Question.kind, answers=(FIRST, SECOND))
    result = run(belief_changes={"kind": said(KindClaim.insurance, SECOND.quote, 11), "conflicts": (conflict,)})
    assert result.tier is Tier.refer
    flag = one_flag(result, RuleId.kind)
    assert [flag.quote, *(e.quote for e in flag.also)] == [FIRST.quote, SECOND.quote]
    assert flag in result.products[0].evidence_pack.flags


def test_a_conflict_keeps_the_rules_own_flags_and_gaps():
    conflict = AnswerConflict(question=Question.kind, answers=(FIRST, SECOND))
    wrong = run(belief_changes={"kind": said(KindClaim.deposit), "conflicts": (conflict,)})
    assert [f.reason for f in flags(wrong, RuleId.kind)] == [R.kind_differs, R.answers_conflict]
    unasked = run(belief_changes={"cover_inr": NotAsked(), "conflicts": (conflict.model_copy(update={"question": Question.cover}),)})
    assert [g.reason for g in gaps(unasked, RuleId.cover)] == [GapReason.not_asked]
    assert [f.reason for f in flags(unasked, RuleId.cover)] == [R.answers_conflict]


def test_a_conflict_belongs_to_its_own_product_only():
    conflict = AnswerConflict(question=Question.kind, answers=(FIRST, SECOND))
    result = evaluate(
        record(product(P1), product(P2)),
        beliefs(product_beliefs(P1), product_beliefs(P2, conflicts=(conflict,))),
    )
    first, second = result.products
    assert first.tier is Tier.clear
    assert [f.reason for f in second.flags] == [R.answers_conflict]
    assert RuleId.kind in first.passed and RuleId.kind not in second.passed


# --- recall: a customer who says they took nothing --------------------------------

DENIAL = ev("kuch nahin liya, bas loan liya tha", 3)


def denied() -> OpenRecall:
    return OpenRecall(asked=True, answer=ev("recall answer", 3), denial=DENIAL)


@pytest.mark.parametrize("kind", [dont_know(), said(KindClaim.deposit), unclear(), NotAsked()])
def test_denying_any_product_in_recall_is_a_high_flag_quoting_the_denial(kind):
    result = run(belief_changes={"kind": kind}, recall=denied())
    flag = one_flag(result, RuleId.recall)
    assert (flag.reason, flag.severity, flag.tier) == (R.recall_denied, HIGH, Tier.refer)
    assert (flag.quote, flag.turn_id) == (DENIAL.quote, DENIAL.turn_id)
    assert result.tier is Tier.refer


def test_a_denial_followed_by_the_kind_on_record_is_only_not_named():
    result = run(recall=denied())
    flag = one_flag(result, RuleId.recall)
    assert (flag.reason, flag.severity, flag.tier) == (R.recall_not_named, LOW, Tier.understanding_gap)


def test_a_denial_does_not_touch_a_product_the_customer_named():
    result = run(recall=OpenRecall(asked=True, items=(named(P1),), denial=DENIAL), belief_changes={"kind": dont_know()})
    assert RuleId.recall in result.products[0].passed


# --- payment frequency ------------------------------------------------------------

REGULAR = {"features": frozenset()}  # a regular-premium product: not paid once
ONCE = said(PaymentFrequency.one_time, "ek hi baar dena tha", 31)
AGAIN = said(PaymentFrequency.recurring, "har saal dena hai", 31)


def test_a_call_that_never_asks_the_frequency_gets_nothing_from_it():
    for on_record in ({}, REGULAR):
        result = run(on_record)
        assert result.tier is Tier.clear
        assert RuleId.belief_mismatch in result.products[0].passed


def test_paid_once_on_a_regular_premium_product_is_a_contradicted_belief():
    result = run(REGULAR, {"payment_frequency": ONCE})
    flag = one_flag(result, RuleId.belief_mismatch)
    assert (flag.reason, flag.severity, flag.tier) == (R.feature_contradicted, HIGH, Tier.refer)
    assert flag.claim is FeatureClaim.one_time_payment
    assert (flag.quote, flag.turn_id) == ("ek hi baar dena tha", 31)


@pytest.mark.parametrize("on_record, answer", [({}, ONCE), (REGULAR, AGAIN)])
def test_a_frequency_that_matches_the_record_passes(on_record, answer):
    result = run(on_record, {"payment_frequency": answer})
    assert RuleId.belief_mismatch in result.products[0].passed
    assert result.tier is Tier.clear


def test_paying_again_and_again_on_a_single_premium_product_is_a_low_flag():
    flag = one_flag(run(belief_changes={"payment_frequency": AGAIN}), RuleId.belief_mismatch)
    assert (flag.reason, flag.severity, flag.tier) == (R.frequency_recurring_on_single, LOW, Tier.understanding_gap)
    assert flag.quote == "har saal dena hai"


def test_not_knowing_the_frequency_is_a_low_flag():
    flag = one_flag(run(belief_changes={"payment_frequency": dont_know()}), RuleId.belief_mismatch)
    assert (flag.reason, flag.severity, flag.tier) == (R.frequency_dont_know, LOW, Tier.understanding_gap)


def test_an_unusable_frequency_answer_is_a_gap_under_belief_mismatch():
    result = run(belief_changes={"payment_frequency": unclear(GapReason.extraction_failed)})
    (gap,) = gaps(result, RuleId.belief_mismatch)
    assert gap.reason is GapReason.extraction_failed
    assert RuleId.belief_mismatch not in result.products[0].passed
    assert result.tier is Tier.incomplete


def test_a_frequency_finding_is_added_to_the_other_belief_outcomes():
    changes = {"payment_frequency": dont_know(), "feature_probe": said((FeatureClaim.guaranteed_return,))}
    reasons = [f.reason for f in flags(run(belief_changes=changes), RuleId.belief_mismatch)]
    assert reasons == [R.feature_contradicted, R.frequency_dont_know]
    unprobed = run(belief_changes={"payment_frequency": AGAIN, "feature_probe": NotAsked()})
    assert [g.reason for g in gaps(unprobed, RuleId.belief_mismatch)] == [GapReason.not_asked]
    assert [f.reason for f in flags(unprobed, RuleId.belief_mismatch)] == [R.frequency_recurring_on_single]


def test_every_contradicted_belief_flag_names_its_claim():
    changes = {
        "kind": said(KindClaim.deposit),
        "feature_probe": said((FeatureClaim.guaranteed_return,)),
        "volunteered_claims": (ClaimEvidence(claim=FeatureClaim.refundable_anytime, evidence=ev()),),
    }
    found = flags(run(belief_changes=changes), RuleId.belief_mismatch)
    assert {f.claim for f in found} == {
        FeatureClaim.is_deposit,
        FeatureClaim.guaranteed_return,
        FeatureClaim.refundable_anytime,
    }
    assert all(f.reason is R.feature_contradicted for f in found)


# --- unscreened replies -----------------------------------------------------------


def test_each_unscreened_reply_is_a_case_level_gap():
    bel = beliefs().model_copy(update={"unscreened": (ev("first reply", 4), ev("second reply", 8))})
    result = evaluate(record(), bel)
    assert [(g.rule_id, g.reason, g.product_id, g.quote, g.turn_id) for g in result.case_gaps] == [
        (RuleId.evidence, GapReason.extraction_failed, None, "first reply", 4),
        (RuleId.evidence, GapReason.extraction_failed, None, "second reply", 8),
    ]
    assert result.products[0].tier is Tier.clear
    assert result.tier is Tier.incomplete
    assert result.verdict is Verdict.unclear_needs_human


# --- the triage tier (contract section 1) -----------------------------------------

NO_CHOICE_ON_RECORD = {"required_for_loan": True, "provider_choice_offered": False}
CONCERN = (ConcernEvidence(concern=SaleConcern.coached_answers, evidence=ev()),)

# reason -> (record changes, belief changes, other `run` arguments)
FLAG_CASES: dict[FlagReason, tuple[dict, dict, dict]] = {
    R.kind_differs: ({}, {"kind": said(KindClaim.deposit)}, {}),
    R.kind_dont_know: ({}, {"kind": dont_know()}, {}),
    R.premium_differs_confirmed: ({}, {"premium_inr": said(70_000)}, {}),
    R.premium_differs: ({}, {"premium_inr": said(70_000), "premium_readback": NotAsked()}, {}),
    R.premium_dont_know: ({}, {"premium_inr": dont_know()}, {}),
    R.premium_approximate: ({}, {"premium_inr": about(50_000)}, {}),
    R.cover_differs: ({}, {"cover_inr": said(1)}, {}),
    R.cover_dont_know: ({}, {"cover_inr": dont_know()}, {}),
    R.term_differs: ({}, {"term_months": said(1)}, {}),
    R.term_dont_know: ({}, {"term_months": dont_know()}, {}),
    R.cancel_unaware: ({}, {"cancel_allowed": said(False)}, {}),
    R.cancel_dont_know: ({}, {"cancel_allowed": dont_know()}, {}),
    R.cancel_window_differs: ({}, {"cancel_window_days": said(7)}, {}),
    R.cancel_window_dont_know: ({}, {"cancel_window_days": dont_know()}, {}),
    R.cancel_not_on_record: ({"cancel_window_days": None}, {}, {}),
    R.recall_not_named: ({}, {}, {"recall": recall_of()}),
    R.recall_denied: ({}, {"kind": dont_know()}, {"recall": denied()}),
    R.recall_off_record: ({}, {}, {"recall": recall_of(named(P1), named(None, KindClaim.deposit))}),
    R.consent_no_record: ({"consent": None, "paid_from_loan": False}, {"payment_source": said(PaymentSource.separately)}, {}),
    R.consent_not_recognised: ({}, {"consent_given": said(False)}, {}),
    R.consent_method_differs: ({}, {"consent_method": said(ConsentMethod.verbal)}, {}),
    R.consent_dont_know: ({}, {"consent_given": dont_know()}, {}),
    R.funded_no_consent: ({"consent": None}, {}, {}),
    R.funded_says_separately: ({}, {"payment_source": said(PaymentSource.separately)}, {}),
    R.funded_dont_know: ({}, {"payment_source": dont_know()}, {}),
    R.unfunded_says_deducted: ({"paid_from_loan": False}, {}, {}),
    R.bundled_not_mitigant: ({"required_for_loan": True, "risk_mitigant": False}, {}, {}),
    R.bundled_described_as_deposit: ({"required_for_loan": True}, {"kind": said(KindClaim.deposit)}, {}),
    R.bundled_no_choice_on_record: (NO_CHOICE_ON_RECORD, {}, {}),
    R.bundled_no_choice_told: ({"required_for_loan": True}, {"provider_choice_offered": said(False)}, {}),
    R.feature_contradicted: ({}, {"feature_probe": said((FeatureClaim.guaranteed_return,))}, {}),
    R.feature_dont_know: ({}, {"feature_probe": dont_know()}, {}),
    R.frequency_recurring_on_single: ({}, {"payment_frequency": AGAIN}, {}),
    R.frequency_dont_know: ({}, {"payment_frequency": dont_know()}, {}),
    R.sale_concern: ({}, {}, {"sale_concerns": CONCERN}),
}

REFER_REASONS = {
    R.kind_differs, R.kind_dont_know, R.premium_differs_confirmed, R.recall_denied, R.recall_off_record,
    R.consent_no_record, R.consent_not_recognised, R.consent_method_differs, R.consent_dont_know,
    R.funded_no_consent, R.funded_says_separately, R.funded_dont_know, R.unfunded_says_deducted,
    R.bundled_not_mitigant, R.bundled_described_as_deposit, R.bundled_no_choice_on_record,
    R.bundled_no_choice_told, R.feature_contradicted, R.sale_concern,
}  # fmt: skip
INCOMPLETE_REASONS = {R.premium_differs}


def test_the_tier_table_covers_every_flag_reason():
    assert set(FLAG_CASES) == set(FlagReason) - {R.answers_conflict}


@pytest.mark.parametrize("reason", list(FLAG_CASES))
def test_each_flag_reason_gives_the_tier_in_the_contract(reason):
    on_record, believed, other = FLAG_CASES[reason]
    result = run(on_record, believed, **other)
    found = [f for f in result.all_flags() if f.reason is reason]
    assert found, [f.reason for f in result.all_flags()]
    expected = (
        Tier.refer
        if reason in REFER_REASONS
        else Tier.incomplete
        if reason in INCOMPLETE_REASONS
        else Tier.understanding_gap
    )
    assert {f.tier for f in found} == {expected}
    if all(f.tier is expected for f in result.all_flags()) and not result.all_gaps():
        assert result.tier is expected


# rule -> the answer whose absence leaves that rule undecided on the baseline
GAP_CASES = {
    RuleId.kind: ({"kind": NotAsked()}, {"recall": recall_of(named(P1))}),
    RuleId.premium: ({"premium_inr": NotAsked()}, {}),
    RuleId.consent: ({"consent_given": NotAsked()}, {}),
    RuleId.loan_funded: ({"payment_source": NotAsked()}, {}),
    RuleId.bundling: ({"required_for_loan": NotAsked()}, {}),
    RuleId.belief_mismatch: ({"feature_probe": NotAsked()}, {}),
    RuleId.recall_unmatched: ({}, {"recall": recall_of(named(P1), named(None))}),
    RuleId.evidence: ({"ungrounded": (ev(),)}, {}),
    RuleId.cover: ({"cover_inr": NotAsked()}, {}),
    RuleId.term: ({"term_months": NotAsked()}, {}),
    RuleId.cancel_window: ({"cancel_allowed": NotAsked()}, {}),
}
UNDERSTANDING_RULES = {RuleId.cover, RuleId.term, RuleId.cancel_window, RuleId.recall}


@pytest.mark.parametrize("rule", list(GAP_CASES))
def test_a_question_with_no_usable_answer_is_never_clear(rule):
    believed, other = GAP_CASES[rule]
    result = run(belief_changes=believed, **other)
    assert {g.rule_id for g in result.all_gaps()} == {rule} and not result.all_flags()
    expected = Tier.understanding_gap if rule in UNDERSTANDING_RULES else Tier.incomplete
    assert result.tier is expected
    assert result.tier is not Tier.clear


def test_recall_never_asked_is_incomplete_for_the_case_and_an_understanding_gap_for_the_product():
    result = run(recall=recall_of(asked=False))
    assert result.products[0].tier is Tier.understanding_gap  # the product's own recall gap
    assert result.tier is Tier.incomplete  # the case-level recall_unmatched gap


def test_a_clear_case_has_no_flag_and_no_gap():
    result = run()
    assert (result.tier, result.products[0].tier) == (Tier.clear, Tier.clear)


def test_tier_precedence_is_refer_then_incomplete_then_understanding_gap():
    understanding = {"cover_inr": dont_know()}
    incomplete = {"payment_source": NotAsked()}
    refer = {"kind": said(KindClaim.deposit)}
    assert run(belief_changes=understanding).tier is Tier.understanding_gap
    assert run(belief_changes=understanding | incomplete).tier is Tier.incomplete
    assert run(belief_changes=understanding | incomplete | refer).tier is Tier.refer
    assert run(belief_changes=incomplete | refer).tier is Tier.refer


def test_the_case_tier_is_the_worst_of_the_products_and_the_case_level():
    rec = record(product(P1), product(P2))
    result = evaluate(rec, beliefs(product_beliefs(P1, cover_inr=dont_know()), product_beliefs(P2, kind=NotAsked())))
    assert [p.tier for p in result.products] == [Tier.understanding_gap, Tier.incomplete]
    assert result.tier is Tier.incomplete
    concerned = evaluate(rec, beliefs(product_beliefs(P1), product_beliefs(P2), sale_concerns=CONCERN))
    assert [p.tier for p in concerned.products] == [Tier.clear, Tier.clear]
    assert concerned.tier is Tier.refer


def test_an_informed_customer_who_gives_a_range_and_forgets_the_window_is_an_understanding_gap():
    changes = {"premium_inr": about(55_000, low=50_000), "cancel_window_days": dont_know()}
    result = run(belief_changes=changes)
    assert {f.reason for f in result.all_flags()} == {R.premium_approximate, R.cancel_window_dont_know}
    assert not result.all_gaps()
    assert result.tier is Tier.understanding_gap
    assert result.verdict is Verdict.flag_for_review  # the strict verdict keeps its meaning
