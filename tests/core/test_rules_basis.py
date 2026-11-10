"""What a referral rests on: `Basis`, `FLAG_BASIS`, `Flag.rests_on` / `Flag.basis`, `referral_basis`
and the summary's `referral_basis` and `first_line` (contract sections 1, 2 and 6). A tag beside
the tier: it never changes a tier, a verdict, a flag or a gap."""

import json
from pathlib import Path

import pytest
from test_rules_engine import (
    demo_case,
    everything_flagged,
    product,
    record,
    run,
    said,
)

from samajh.rules import evaluate, summarise
from samajh.rules.summary import RECORD_ONLY_FIRST_LINE
from samajh.types import (
    FLAG_BASIS,
    TOLD_REQUIRED_HEARD,
    Basis,
    CaseResult,
    Flag,
    FlagReason,
    KindClaim,
    RuleId,
    Severity,
    Tier,
    referral_basis,
)

R = FlagReason
RECORD_REASONS = {
    R.consent_no_record,
    R.funded_no_consent,
    R.bundled_not_mitigant,
    R.bundled_no_choice_on_record,
}


def flag(reason: FlagReason, rule: RuleId = RuleId.consent, **kw) -> Flag:
    return Flag(
        rule_id=rule,
        reason=reason,
        clause="85G",
        product_id=None,
        severity=Severity.high,
        expected="e",
        heard="h",
        **kw,
    )


def test_every_reason_has_a_basis_and_exactly_four_rest_on_the_record():
    assert set(FLAG_BASIS) == set(FlagReason)
    assert {r for r, b in FLAG_BASIS.items() if b is Basis.record_only} == RECORD_REASONS


@pytest.mark.parametrize("reason", sorted(RECORD_REASONS))
def test_the_override_marks_a_record_reason_as_resting_on_a_statement(reason):
    f = flag(reason, rests_on=Basis.customer_statement)
    assert f.basis is Basis.customer_statement
    assert flag(reason).basis is Basis.record_only


@pytest.mark.parametrize(
    ("reason", "rests_on"),
    [
        (R.consent_no_record, Basis.record_only),
        (R.kind_differs, Basis.customer_statement),
        (R.kind_differs, Basis.record_only),
    ],
)
def test_the_override_never_goes_the_other_way_or_repeats_the_table(reason, rests_on):
    with pytest.raises(ValueError, match="rests_on"):
        flag(reason, rests_on=rests_on)


def bundling_flags(result: CaseResult) -> list[Flag]:
    return [f for f in result.all_flags() if f.rule_id is RuleId.bundling]


def test_bundling_on_the_record_rests_on_the_record():
    result = run({"required_for_loan": True, "risk_mitigant": False, "provider_choice_offered": False})
    found = bundling_flags(result)
    assert {f.reason for f in found} == {R.bundled_not_mitigant, R.bundled_no_choice_on_record}
    assert all(f.rests_on is None and f.basis is Basis.record_only for f in found)
    assert result.referral_basis is Basis.record_only


def test_bundling_on_the_customers_word_that_it_was_required_rests_on_what_they_said():
    result = run(
        {"required_for_loan": False, "risk_mitigant": False, "provider_choice_offered": False},
        {"required_for_loan": said(True)},
    )
    found = bundling_flags(result)
    assert {f.reason for f in found} == {R.bundled_not_mitigant, R.bundled_no_choice_on_record}
    assert all(f.rests_on is Basis.customer_statement for f in found)
    assert result.referral_basis is Basis.customer_statement


def test_referral_basis_of_flags():
    assert referral_basis([]) is None
    assert referral_basis([flag(R.premium_dont_know, RuleId.premium)]) is None  # understanding gap only
    assert referral_basis([flag(R.consent_no_record)]) is Basis.record_only
    both = [flag(R.consent_no_record), flag(R.consent_not_recognised)]
    assert referral_basis(both) is Basis.customer_statement
    # a lower-tier flag on a statement does not make the referral one on a statement
    assert (
        referral_basis([flag(R.consent_no_record), flag(R.cover_differs, RuleId.cover)]) is Basis.record_only
    )


def cases() -> list[CaseResult]:
    return [
        run(),
        run({"consent": None}),
        run({"consent": None}, {"cover_inr": said(1)}),
        run({}, {"cover_inr": said(1)}),
        run({}, {"consent_given": said(False)}),
        everything_flagged(),
        evaluate(*demo_case()),
    ]


@pytest.mark.parametrize("result", cases())
def test_referral_basis_is_none_exactly_when_the_tier_is_not_refer(result):
    assert (result.referral_basis is None) == (result.tier is not Tier.refer)
    for p in result.products:
        assert (p.referral_basis is None) == (p.tier is not Tier.refer)


def test_a_record_flag_beside_a_refer_tier_statement_is_a_referral_on_the_statement():
    result = run({"consent": None}, {"kind": said(KindClaim.deposit)})
    assert {f.basis for f in result.all_flags() if f.tier is Tier.refer} == {
        Basis.record_only,
        Basis.customer_statement,
    }
    assert result.referral_basis is Basis.customer_statement
    assert result.products[0].referral_basis is Basis.customer_statement
    summary = summarise(record(product(consent=None)), result)
    assert summary.referral_basis is Basis.customer_statement and summary.first_line is None


def test_a_referral_on_the_record_alone_gets_the_first_line():
    rec = record(product(consent=None))
    result = run({"consent": None})
    assert result.tier is Tier.refer
    summary = summarise(rec, result)
    assert summary.referral_basis is Basis.record_only
    assert summary.first_line == RECORD_ONLY_FIRST_LINE
    refer = [line for line in summary.lines if line.tier is Tier.refer]
    assert refer and all(line.basis is Basis.record_only for line in refer)
    assert all(line.basis is None for line in summary.lines if line.tier is not Tier.refer)


def test_a_record_only_referral_with_a_lower_tier_statement_gets_the_same_first_line():
    rec = record(product(consent=None))
    result = run({"consent": None}, {"cover_inr": said(1)})
    assert result.referral_basis is Basis.record_only
    assert any(f.basis is Basis.customer_statement and f.tier is not Tier.refer for f in result.all_flags())
    assert summarise(rec, result).first_line == RECORD_ONLY_FIRST_LINE


def test_a_case_with_no_referral_has_no_basis_and_no_first_line():
    summary = summarise(record(), run({}, {"cover_inr": said(1)}))
    assert summary.tier is not Tier.refer
    assert summary.referral_basis is None and summary.first_line is None


def test_the_new_fields_are_left_out_of_a_dump_while_they_hold_their_default():
    """Stored results and summaries keep their bytes: `added_later`."""
    result = run({"consent": None}, {"cover_inr": said(1)})
    dumped = result.model_dump_json()
    assert "rests_on" not in dumped and "referral_basis" not in dumped
    assert CaseResult.model_validate_json(dumped) == result
    plain = summarise(record(), run())
    assert set(plain.model_dump()) == {"loan_id", "call_id", "tier", "lines"}
    told = run(
        {"required_for_loan": False, "risk_mitigant": False, "provider_choice_offered": False},
        {"required_for_loan": said(True)},
    )
    assert '"rests_on":"customer_statement"' in told.model_dump_json()
    assert CaseResult.model_validate_json(told.model_dump_json()) == told


@pytest.mark.parametrize("result", cases())
def test_every_refer_tier_flag_on_a_statement_carries_a_quote(result):
    for f in result.all_flags():
        if f.tier is Tier.refer and f.basis is Basis.customer_statement:
            assert f.quote is not None, f.reason


HERO = Path(__file__).resolve().parents[2] / "references" / "pilots" / "p1-artifacts" / "hero" / "case.json"


def test_a_result_stored_before_rests_on_reads_told_required_bundling_as_a_statement():
    """Backfill on load: the hero case file was written before `Flag.rests_on` existed."""
    result = CaseResult.model_validate(json.loads(HERO.read_text(encoding="utf-8"))["result"])
    told = [
        f
        for f in result.all_flags()
        if f.rule_id is RuleId.bundling and f.heard.startswith(TOLD_REQUIRED_HEARD)
    ]
    assert any(f.reason is R.bundled_no_choice_on_record for f in told)
    assert all(f.basis is Basis.customer_statement for f in told)


def test_the_backfill_leaves_a_flag_on_the_record_and_an_explicit_field_alone():
    on_record = flag(R.bundled_no_choice_on_record, RuleId.bundling)
    assert on_record.rests_on is None and on_record.basis is Basis.record_only
    told = run(
        {"required_for_loan": False, "risk_mitigant": False, "provider_choice_offered": False},
        {"required_for_loan": said(True)},
    )
    assert CaseResult.model_validate_json(told.model_dump_json()) == told
    built = [f for f in told.all_flags() if f.rule_id is RuleId.bundling]
    assert all(
        f.heard.startswith(TOLD_REQUIRED_HEARD) and f.rests_on is Basis.customer_statement for f in built
    )
