"""What each referral rests on, beside every referral count the review pages give (P3c).

A referral on the record alone (for example no consent on record) is counted apart from one on
what the customer said. Each split sums to the count it sits beside; the tier never changes."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from opskit import COMPLETED, NOW, SOLD, coached, customer, loan, other_consent_method, run_batch
from pydantic import ValidationError

from samajh.ops import wording
from samajh.ops.__main__ import _summary
from samajh.ops.batch import load_batch
from samajh.ops.model import Decision
from samajh.ops.report import build_report
from samajh.ops.store import OpsStore
from samajh.ops.views import (
    DispositionIn,
    ReferralSplit,
    batch_view,
    case_view,
    queue_view,
    record_disposition,
)
from samajh.rules.summary import RECORD_ONLY_FIRST_LINE
from samajh.types import Basis, Tier

STATEMENT, RECORD = Basis.customer_statement, Basis.record_only


def no_consent(of):
    """The loan with no consent on record for its product: a referral on the record alone."""
    (product,) = of.record.products
    record = of.record.model_copy(update={"products": (product.model_copy(update={"consent": None}),)})
    return of.model_copy(update={"record": record})


@pytest.fixture
def mixed(tmp_path: Path) -> OpsStore:
    """Two referrals on the record alone, two on what the customer said, one clear call."""
    with_a, with_b = loan(1), loan(2, branch="SYN-BR-02")
    record_a, record_b = no_consent(with_a), no_consent(with_b)
    said_a, said_b, fine = loan(3), loan(4, branch="SYN-BR-02"), loan(5)
    customers = [  # the customers of the first two say they agreed by OTP, as on the original record
        customer(with_a, COMPLETED),
        customer(with_b, COMPLETED),
        coached(said_a, COMPLETED),
        other_consent_method(said_b, COMPLETED),
        customer(fine, COMPLETED),
    ]
    store = run_batch(
        tmp_path / "ops", [record_a, record_b, said_a, said_b, fine], customers, SOLD + timedelta(days=14)
    )
    items = queue_view(load_batch(store)).items
    first_record = next(i for i in items if i.loan_id == record_a.record.loan_id)
    record_disposition(
        store,
        first_record.case_id,
        DispositionIn(decision=Decision.concern_not_supported, note="seen", reviewer="R1"),
        NOW,
    )
    return store


def _sum(split: ReferralSplit) -> int:
    return split.customer_statement + split.record_only


def assert_every_split_sums(store: OpsStore) -> None:
    batch = load_batch(store)
    header = batch_view(batch)
    assert _sum(header.referred_split) == header.referred
    assert _sum(header.open_split) == header.open_cases
    assert _sum(header.other_referrals_split) == header.other_referrals
    report = build_report(store)
    assert _sum(report.tiles.referred_split) == report.tiles.referred
    for row in report.tiers:
        assert (row.referred_split is not None) == (row.tier is Tier.refer)
        if row.referred_split is not None:
            assert _sum(row.referred_split) == row.value.count == report.tiles.referred
    for b in report.breakdowns:
        for row in b.rows:
            assert _sum(row.referred_split) == row.referred.count
            assert _sum(row.rest_referred_split) == row.rest_referred.count
    for row in report.referrals:
        assert _sum(row.split) == row.value.count
    assert _sum(report.open_referrals_split) == report.open_referrals.count
    assert _sum(report.other_referrals_split) == report.other_referrals
    assert _sum(report.decided_split) == report.supported_of_decided.n
    assert _sum(report.supported_split) == report.supported_of_decided.count
    for row in report.rules:
        assert _sum(row.referred_split) == row.referred


def test_every_split_sums_to_its_count_on_a_mixed_batch(mixed: OpsStore) -> None:
    assert_every_split_sums(mixed)
    header = batch_view(load_batch(mixed))
    assert (header.referred, header.referred_split) == (4, ReferralSplit(customer_statement=2, record_only=2))
    assert header.open_split == ReferralSplit(customer_statement=2, record_only=1)
    report = build_report(mixed)
    decided = next(r for r in report.referrals if r.key == Decision.concern_not_supported.value)
    assert decided.split == ReferralSplit(customer_statement=0, record_only=1)
    consent = next(r for r in report.rules if r.rule_id.value == "consent")
    assert consent.referred_split.record_only == 2
    assert report.basis_note == wording.BASIS_NOTE
    assert report.rule_split_note == wording.RULE_SPLIT_NOTE
    assert report.decided_split == ReferralSplit(customer_statement=0, record_only=1)
    assert report.supported_split == ReferralSplit(customer_statement=0, record_only=0)


def test_every_split_sums_on_the_demo_batch(store: OpsStore) -> None:
    assert_every_split_sums(store)
    report = build_report(store)
    refer = next(r for r in report.tiers if r.tier is Tier.refer)
    assert (refer.value.count, refer.value.n) == (7, 64)
    assert refer.referred_split == ReferralSplit(customer_statement=7, record_only=0)
    text = _summary(store)
    assert "  referred on what the customer said: 7 of 64" in text
    assert "  referred on the record alone: 0 of 64" in text


def test_the_mixed_batch_report_sums_when_intervals_are_withheld(mixed_state: Path) -> None:
    assert_every_split_sums(OpsStore(mixed_state / "ops"))


def test_queue_rows_and_the_case_view_carry_the_basis(mixed: OpsStore) -> None:
    batch = load_batch(mixed)
    items = queue_view(batch).items
    assert sorted(i.basis for i in items) == sorted([STATEMENT, STATEMENT, RECORD, RECORD])
    for item in items:
        assert item.basis_label == wording.BASIS_LABEL[item.basis]
        view = case_view(batch, item.case_id)
        assert view.referral_basis is item.basis and view.basis_label == item.basis_label
        assert view.first_line == (RECORD_ONLY_FIRST_LINE if item.basis is RECORD else None)


def test_a_split_that_does_not_sum_is_refused() -> None:
    from samajh.ops.views import Count, DispositionRow

    with pytest.raises(ValidationError, match="does not sum"):
        DispositionRow(
            key="none",
            label="x",
            value=Count(count=2, n=3),
            split=ReferralSplit(customer_statement=1, record_only=0),
        )


def test_the_new_words_hold_no_banned_word_and_never_say_the_customer_misunderstood() -> None:
    new = [
        *wording.BASIS_LABEL.values(),
        wording.REFERRED_ON_STATEMENT,
        wording.REFERRED_ON_RECORD,
        wording.BASIS_NOTE,
        wording.RULE_SPLIT_NOTE,
    ]
    assert [s for s in new if wording.banned_in(s)] == []
    assert not any("misunderst" in s.lower() or "—" in s for s in new)
