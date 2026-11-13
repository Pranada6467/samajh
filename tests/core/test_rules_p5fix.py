"""P5 fix round: answers a customer clearly gave are used. Expected results come from the decisions in
references/pilots/P3a-contract.md (the P5 fix round), not from running the code.

A consent reply that gives only the way of agreeing, a phone yes against a recorded call, a premium
of nothing, a premium paid by nobody, each in an informed and a misled version.
"""

import pytest
from test_rules_engine import QUOTE, ev, flags, gaps, named, recall_of, run, said

from samajh.rules import summarise
from samajh.types import (
    ClaimEvidence,
    Consent,
    ConsentMethod,
    DontKnow,
    FeatureClaim,
    FlagReason,
    GapReason,
    KindClaim,
    NotAsked,
    PaymentSource,
    RuleId,
    Stated,
    Tier,
    Unclear,
)

R = FlagReason
CONSENT_TURN = 50
OTP, SIGNED, RECORDED, VERBAL = (
    ConsentMethod.otp,
    ConsentMethod.signed_form,
    ConsentMethod.recorded_call,
    ConsentMethod.verbal,
)


def consent_reply(method: ConsentMethod, **extra) -> dict:
    """A reply to the consent question that gives a way of agreeing and names nothing agreed to."""
    whole = ev("ओटीपी दिया था।", CONSENT_TURN)
    return {
        "consent_given": Unclear(evidence=whole),
        "consent_method": Stated(value=method, evidence=whole, **extra),
    }


def nowhere() -> dict:
    """The customer named this product nowhere: no kind answer, nothing in open recall."""
    return {"recall": recall_of()}


def consent_tier(result) -> Tier:
    from samajh.types import tier_of

    return tier_of(flags(result, RuleId.consent), gaps(result, RuleId.consent))


# --- (A) a way of agreeing with nothing named in the same reply --------------------------------


def test_method_only_matching_the_record_passes_when_the_kind_question_named_the_product():
    result = run(
        belief_changes=consent_reply(OTP) | {"kind": said(KindClaim.insurance, turn=20)}, **nowhere()
    )
    assert RuleId.consent in result.products[0].passed


def test_method_only_matching_the_record_passes_when_open_recall_named_the_product():
    changes = consent_reply(OTP) | {"kind": NotAsked()}
    result = run(belief_changes=changes, recall=recall_of(named(kind=KindClaim.insurance)))
    assert RuleId.consent in result.products[0].passed


def test_a_recall_item_matched_by_misdescription_names_the_product():
    changes = consent_reply(OTP) | {"kind": NotAsked()}
    result = run(belief_changes=changes, recall=recall_of(named(kind=KindClaim.deposit)))
    assert RuleId.consent in result.products[0].passed


def test_a_misdescription_still_counts_as_naming_the_product_and_the_kind_rule_refers():
    result = run(belief_changes=consent_reply(OTP) | {"kind": said(KindClaim.deposit, turn=20)}, **nowhere())
    assert RuleId.consent in result.products[0].passed
    assert result.tier is Tier.refer  # through the kind rule


def test_method_only_differing_from_the_record_refers_when_the_product_was_named():
    result = run(belief_changes=consent_reply(SIGNED) | {"kind": said(KindClaim.insurance, turn=20)})
    (flag,) = flags(result, RuleId.consent)
    assert (flag.reason, flag.tier) == (R.consent_method_differs, Tier.refer)


def test_method_only_with_the_product_named_nowhere_is_an_understanding_gap():
    result = run(belief_changes=consent_reply(OTP) | {"kind": NotAsked()}, **nowhere())
    (flag,) = flags(result, RuleId.consent)
    assert (flag.reason, flag.tier, flag.severity.value) == (
        R.consent_product_not_named,
        Tier.understanding_gap,
        "low",
    )
    assert not gaps(result, RuleId.consent)
    assert consent_tier(result) is Tier.understanding_gap


def test_a_kind_answered_dont_know_is_not_a_naming():
    result = run(belief_changes=consent_reply(OTP) | {"kind": DontKnow(evidence=ev(turn=20))}, **nowhere())
    assert [f.reason for f in flags(result, RuleId.consent)] == [R.consent_product_not_named]


def test_method_only_differing_from_the_record_refers_even_when_the_product_was_named_nowhere():
    result = run(belief_changes=consent_reply(SIGNED) | {"kind": NotAsked()}, **nowhere())
    (flag,) = flags(result, RuleId.consent)
    assert (flag.reason, flag.tier) == (R.consent_method_differs, Tier.refer)


def test_the_earlier_naming_is_taken_in_preference_to_a_later_one():
    result = run(
        belief_changes=consent_reply(OTP) | {"kind": said(KindClaim.insurance, turn=60)},
        recall=recall_of(named(kind=KindClaim.insurance)),
    )
    assert RuleId.consent in result.products[0].passed


def test_a_method_that_stood_over_a_correction_in_its_own_reply_is_not_a_method_only_answer():
    earlier = ev("फॉर्म पर साइन", CONSENT_TURN)
    changes = consent_reply(OTP, also=(earlier,)) | {"kind": said(KindClaim.insurance, turn=20)}
    result = run(belief_changes=changes)
    (gap,) = gaps(result, RuleId.consent)
    assert gap.reason is GapReason.no_usable_answer
    assert consent_tier(result) is Tier.incomplete


@pytest.mark.parametrize("reason", [GapReason.extraction_failed, GapReason.quote_not_grounded])
def test_an_unusable_what_half_for_any_other_reason_stays_a_gap(reason):
    same_turn = Unclear(reason=reason, evidence=ev(turn=CONSENT_TURN))
    changes = consent_reply(OTP) | {"consent_given": same_turn, "kind": said(KindClaim.insurance, turn=20)}
    result = run(belief_changes=changes)
    (gap,) = gaps(result, RuleId.consent)
    assert gap.reason is reason


@pytest.mark.parametrize("turn", [CONSENT_TURN - 2, CONSENT_TURN + 2])
def test_a_what_half_from_another_reply_is_not_paired_with_this_method(turn):
    changes = consent_reply(OTP) | {
        "consent_given": Unclear(evidence=ev(turn=turn)),
        "kind": said(KindClaim.insurance, turn=20),
    }
    (gap,) = gaps(run(belief_changes=changes), RuleId.consent)
    assert gap.reason is GapReason.no_usable_answer


def test_a_method_the_customer_does_not_remember_is_still_a_gap():
    changes = {
        "consent_given": Unclear(evidence=ev(turn=CONSENT_TURN)),
        "consent_method": DontKnow(evidence=ev(turn=CONSENT_TURN)),
        "kind": said(KindClaim.insurance, turn=20),
    }
    assert gaps(run(belief_changes=changes), RuleId.consent)


def test_not_knowing_what_they_agreed_to_still_refers():
    changes = consent_reply(OTP) | {"consent_given": DontKnow(evidence=ev(turn=CONSENT_TURN))}
    (flag,) = flags(run(belief_changes=changes), RuleId.consent)
    assert flag.reason is R.consent_dont_know


def test_no_consent_on_record_still_refers_on_the_record():
    result = run(
        {"consent": None, "paid_from_loan": False},
        consent_reply(OTP) | {"payment_source": said(PaymentSource.separately)},
    )
    (flag,) = flags(result, RuleId.consent)
    assert flag.reason is R.consent_no_record


# --- (F) a phone yes: the extractor classes it recorded_call; the comparison is equality ---------


def _record_consent(method: ConsentMethod) -> dict:
    from datetime import date

    return {"consent": Consent(method=method, at=date(2027, 1, 5))}


def test_a_phone_yes_classed_recorded_call_matches_a_recorded_call_record():
    result = run(_record_consent(RECORDED), {"consent_method": said(RECORDED)})
    assert RuleId.consent in result.products[0].passed


@pytest.mark.parametrize(
    ("on_record", "said_by_customer"), [(RECORDED, VERBAL), (SIGNED, RECORDED), (OTP, RECORDED)]
)
def test_a_call_not_recorded_or_a_phone_yes_against_another_method_refers(on_record, said_by_customer):
    result = run(_record_consent(on_record), {"consent_method": said(said_by_customer)})
    (flag,) = flags(result, RuleId.consent)
    assert (flag.reason, flag.tier) == (R.consent_method_differs, Tier.refer)


def test_a_method_only_phone_yes_against_a_recorded_call_passes_with_the_product_named():
    changes = consent_reply(RECORDED) | {"kind": said(KindClaim.insurance, turn=20)}
    assert RuleId.consent in run(_record_consent(RECORDED), changes).products[0].passed


# --- (C) a premium of nothing -----------------------------------------------------------------


@pytest.mark.parametrize("readback", [NotAsked(), said(True)])
def test_a_premium_of_nothing_refers_with_or_without_a_read_back(readback):
    result = run(belief_changes={"premium_inr": said(0), "premium_readback": readback})
    (flag,) = flags(result, RuleId.premium)
    assert (flag.reason, flag.tier, flag.quote) == (R.premium_said_zero, Tier.refer, QUOTE)
    assert result.tier is Tier.refer


def test_a_premium_of_nothing_whose_read_back_was_rejected_stays_undecided():
    result = run(belief_changes={"premium_inr": said(0), "premium_readback": said(False)})
    (gap,) = gaps(result, RuleId.premium)
    assert gap.reason is GapReason.readback_rejected


def test_the_record_premium_confirmed_still_passes():
    assert RuleId.premium in run().products[0].passed


def test_the_summary_line_for_a_premium_of_nothing_names_the_record_premium():
    from test_rules_engine import product, record

    result = run(belief_changes={"premium_inr": said(0), "premium_readback": NotAsked()})
    line = next(x for x in summarise(record(product()), result).lines if RuleId.premium in x.rule_ids)
    assert line.tier is Tier.refer
    assert line.title == "Customer said it cost them nothing; the record shows a premium of ₹52,000."


# --- (D) a premium paid by nobody -------------------------------------------------------------


@pytest.mark.parametrize("from_loan", [True, False])
def test_not_charged_refers_against_either_record(from_loan):
    result = run({"paid_from_loan": from_loan}, {"payment_source": said(PaymentSource.not_charged)})
    (flag,) = flags(result, RuleId.loan_funded)
    assert (flag.reason, flag.tier, flag.quote) == (R.payment_says_not_charged, Tier.refer, QUOTE)


@pytest.mark.parametrize(
    ("from_loan", "source"), [(True, PaymentSource.from_loan), (False, PaymentSource.separately)]
)
def test_the_source_on_record_still_passes(from_loan, source):
    result = run({"paid_from_loan": from_loan}, {"payment_source": said(source)})
    assert RuleId.loan_funded in result.products[0].passed


def test_the_summary_line_for_not_charged_is_a_payment_line():
    from test_rules_engine import product, record

    result = run(belief_changes={"payment_source": said(PaymentSource.not_charged)})
    line = next(x for x in summarise(record(product()), result).lines if RuleId.loan_funded in x.rule_ids)
    assert line.tier is Tier.refer
    assert line.title.startswith("Customer said they paid nothing for it")
    assert "deducted from the loan" in line.record_value


# --- an untimed "the money comes back" (round 2) ------------------------------------------------

MONEY_BACK = FeatureClaim.money_back


@pytest.mark.parametrize("features", [frozenset(), frozenset({FeatureClaim.one_time_payment})])
def test_believing_the_money_comes_back_refers_on_a_product_that_gives_nothing_back(features):
    result = run({"features": features}, {"feature_probe": said((MONEY_BACK,))})
    (flag,) = flags(result, RuleId.belief_mismatch)
    assert (flag.reason, flag.claim, flag.tier) == (R.feature_contradicted, MONEY_BACK, Tier.refer)


@pytest.mark.parametrize(
    "way", [FeatureClaim.is_deposit, FeatureClaim.refundable_anytime, FeatureClaim.withdrawable_after_period]
)
def test_believing_the_money_comes_back_is_true_of_a_product_whose_record_gives_a_way_back(way):
    result = run({"features": frozenset({way})}, {"feature_probe": said((MONEY_BACK,))})
    assert RuleId.belief_mismatch in result.products[0].passed


def test_a_guaranteed_return_alone_is_not_a_way_for_the_money_to_come_back():
    result = run(
        {"features": frozenset({FeatureClaim.guaranteed_return})}, {"feature_probe": said((MONEY_BACK,))}
    )
    assert [f.claim for f in flags(result, RuleId.belief_mismatch)] == [MONEY_BACK]


def test_money_back_said_in_passing_is_judged_the_same_way():
    claim = (ClaimEvidence(claim=MONEY_BACK, evidence=ev()),)
    assert flags(run(belief_changes={"volunteered_claims": claim}), RuleId.belief_mismatch)
    passed = run({"features": frozenset({FeatureClaim.is_deposit})}, {"volunteered_claims": claim})
    assert not [f for f in flags(passed, RuleId.belief_mismatch) if f.claim is MONEY_BACK]
