"""The sampling statement and the intervals: "about the same chance" and intervals only when the
chances of being drawn are narrow (`report.NARROW_RATIO`); otherwise the range, a plain warning and
no interval on any share."""

from __future__ import annotations

import math
import random
import re
from collections.abc import Iterator
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

import pytest
from opskit import NOW, SOLD, loan, open_batch
from pydantic import BaseModel

from samajh.ops import sampler, wording
from samajh.ops.batch import load_batch
from samajh.ops.book import book_sha256
from samajh.ops.model import BookMeta
from samajh.ops.report import NARROW_RATIO, build_report, sampling
from samajh.ops.store import OpsStore
from samajh.ops.views import Proportion
from samajh.types import LenderType

SAME = re.compile(r"about the same chance|\bequal", re.IGNORECASE)


def _proportions(value) -> Iterator[Proportion]:
    if isinstance(value, Proportion):
        yield value
    elif isinstance(value, BaseModel):  # any other model: walk its fields
        for name in type(value).model_fields:
            yield from _proportions(getattr(value, name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _proportions(item)


def test_the_narrow_ratio_is_the_stated_arithmetic() -> None:
    r = NARROW_RATIO
    assert r == 1.25
    bias = (math.sqrt(r) - 1) / (math.sqrt(r) + 1)
    assert round(bias, 3) == 0.056  # of the difference between two groups
    # The worst two-group mix really is that far off (checked on a grid, not only by the formula).
    worst = max(abs(w - w / (w + r * (1 - w))) for w in (i / 10_000 for i in range(1, 10_000)))
    assert worst == pytest.approx(bias, abs=1e-6)
    design_effect = (1 + r) ** 2 / (4 * r)
    assert design_effect == pytest.approx(1.0125)
    assert 1 - 1 / math.sqrt(design_effect) < 0.01  # an unweighted interval is under 1% too narrow


def test_the_demo_has_about_the_same_chance_with_its_range_and_keeps_every_interval(store: OpsStore) -> None:
    report = build_report(store)
    s = report.sampling
    assert (s.chances, s.intervals_shown) == ("narrow", True)
    assert s.inclusion_low == pytest.approx(0.375) and s.inclusion_high == pytest.approx(5 / 12)
    assert s.inclusion_ratio == pytest.approx((5 / 12) / 0.375) and s.inclusion_ratio <= NARROW_RATIO
    assert "about the same chance" in s.statement and "between 37.5% and 41.7%" in s.statement
    shares = [p for p in _proportions(report) if p.n]
    assert len(shares) > 40 and all(p.low is not None and p.high is not None for p in shares)
    assert wording.INTERVAL_LIMIT in report.limits and wording.NO_INTERVAL_LIMIT not in report.limits


def test_mixed_rates_state_the_range_say_the_shares_are_unweighted_and_withhold_every_interval(
    mixed_state: Path,
) -> None:
    store = OpsStore(mixed_state / "ops")
    report = build_report(store)
    s = report.sampling
    assert (s.chances, s.intervals_shown) == ("wide", False)
    assert s.inclusion_low < 0.1 and s.inclusion_high == 1.0 and s.inclusion_ratio > NARROW_RATIO
    text = s.statement
    assert not SAME.search(text), text
    assert f"between {s.inclusion_low:.1%} and {s.inclusion_high:.1%}" in text
    for needed in (
        "differed",
        "unweighted counts of the calls analysed",
        "over-represented",
        "do not estimate the share among all sales in the period",
        "no interval is shown on any share",
    ):
        assert needed in text, needed
    # No share the report computes from sampled loans or calls carries an interval: funnel, tiers,
    # rules, breakdowns and their comparisons, the policy items.
    shares = list(_proportions(report))
    assert len(shares) > 40 and all(p.low is None and p.high is None for p in shares)
    assert all(p.share == p.count / p.n for p in shares if p.n)
    assert all("interval" not in (item.highest or "") for item in report.policy_review)
    assert any(item.highest for item in report.policy_review)
    # The reach funnel keeps its counts.
    batch = load_batch(store)
    assert report.funnel.sampled == len(batch.sampled)
    assert sum(r.value.count for r in report.funnel.exits) + report.funnel.stages[-1].value.count == len(
        batch.sampled
    )
    assert wording.NO_INTERVAL_LIMIT in report.limits and wording.INTERVAL_LIMIT not in report.limits
    assert not any(SAME.search(line) for line in report.limits)


def test_no_draw_one_draw_and_a_draw_that_took_nobody(tmp_path: Path) -> None:
    a, b, c = loan(1), loan(2), loan(3, sold_on=SOLD + timedelta(days=40))
    store, first = open_batch(tmp_path / "ops", [a, b, c], SOLD + timedelta(days=3))

    # One draw: one chance, the same for every eligible sale.
    one = sampling(load_batch(store))
    assert (one.chances, one.intervals_shown, one.inclusion_ratio) == ("narrow", True, 1.0)
    assert "about the same chance of being sampled: 100.0%" in one.statement

    # A later draw whose eligible sale was not drawn (lowest chance 0): wide, and said so.
    later = first.as_of + timedelta(days=45)
    nobody = first.model_copy(
        update={
            "draw_id": f"D-{later}",
            "as_of": later,
            "after": first.as_of,
            "eligible": (c.record.loan_id,),
            "drawn": (),
        }
    )
    store.add_draw(nobody)
    zero = sampling(load_batch(store))
    assert (zero.chances, zero.intervals_shown, zero.inclusion_low, zero.inclusion_ratio) == (
        "wide",
        False,
        0.0,
        None,
    )
    assert not SAME.search(zero.statement) and "between 0.0% and 100.0%" in zero.statement
    assert "some eligible sales could not be drawn" in zero.statement
    report = build_report(store)
    assert all(p.low is None for p in _proportions(report))

    # No draw at all, and draws with nobody drawn: nothing to state a chance for.
    empty = OpsStore(tmp_path / "empty")
    empty.init(
        store.meta().book,
        store.book(),
        store.meta().period_start,
        store.meta().period_end,
        store.meta().created_at,
    )
    none = sampling(load_batch(empty))
    assert (none.chances, none.inclusion_low, none.inclusion_high, none.inclusion_ratio) == (
        "none",
        None,
        None,
        None,
    )
    assert none.statement.startswith("No draw has been made yet") and not SAME.search(none.statement)
    only_nobody = OpsStore(tmp_path / "nobody")
    only_nobody.init(
        store.meta().book,
        store.book(),
        store.meta().period_start,
        store.meta().period_end,
        store.meta().created_at,
    )
    only_nobody.add_draw(first.model_copy(update={"drawn": ()}))
    took_none = sampling(load_batch(only_nobody))
    assert took_none.chances == "none" and "No eligible sale was drawn" in took_none.statement
    assert not SAME.search(took_none.statement)
    for edge in (none, took_none):
        assert "nan" not in edge.statement.lower() and "none%" not in edge.statement.lower()


@pytest.mark.parametrize(
    ("low", "high", "chances"),
    [
        (Fraction(2, 5), Fraction(1, 2), "narrow"),  # exactly 1.25
        (Fraction(2, 5), Fraction(5004, 10000), "wide"),
        (Fraction(1, 3), Fraction(5, 12), "narrow"),  # exactly 1.25; floats give 1.2500000000000002
        (Fraction(1, 3), Fraction(5, 12) + Fraction(1, 10**9), "wide"),  # the mirror, just above
        (Fraction(0), Fraction(1, 2), "wide"),
        (Fraction(0), Fraction(0), "none"),
    ],
)
def test_the_line_between_narrow_and_wide_is_the_named_ratio_exactly(
    low: Fraction, high: Fraction, chances: str
) -> None:
    from samajh.ops.report import _chances

    assert _chances(low, high) == chances


def _three_draws(root: Path, counts: list[tuple[int, int]]) -> OpsStore:
    """A batch whose draws took `drawn` of `eligible` sales each, in that order, a week apart."""
    loans, serial, start = [], 0, SOLD
    for k, (_, eligible) in enumerate(counts):
        sold = start + timedelta(days=7 * k)
        for _ in range(eligible):
            serial += 1
            loans.append(loan(serial, sold))
    store = OpsStore(root)
    meta = BookMeta(
        lender_name="Namoona Bank (synthetic)",
        lender_type=LenderType.bank,
        seed=1,
        loans=len(loans),
        sold_from=loans[0].sold_on,
        sold_to=loans[-1].sold_on,
        sha256=book_sha256(loans),
    )
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), NOW)
    after = None
    for k, (drawn, eligible) in enumerate(counts):
        as_of = start + timedelta(days=7 * k + 1)
        d = sampler.draw(loans, meta, as_of, rate=1.0, seed=1, after=after)
        assert len(d.eligible) == eligible
        store.add_draw(d.model_copy(update={"drawn": d.drawn[:drawn]}))
        after = as_of
    return store


def test_draws_at_one_third_two_fifths_and_five_twelfths_are_narrow(tmp_path: Path) -> None:
    """The verifier's case: the highest is exactly 5/4 of the lowest; floats called it wide."""
    assert (5 / 12) / (1 / 3) > 1.25  # the float error this guards against
    s = sampling(load_batch(_three_draws(tmp_path / "ops", [(1, 3), (2, 5), (5, 12)])))
    assert (s.chances, s.intervals_shown) == ("narrow", True)
    assert "1.25 times the lowest, within the 1.25 this report allows" in s.statement
    mirror = sampling(load_batch(_three_draws(tmp_path / "ops2", [(1, 3), (2, 5), (6, 14)])))
    assert (mirror.chances, mirror.intervals_shown) == ("wide", False)  # 3/7 over 1/3 is 9/7


def test_narrow_or_wide_matches_a_fraction_oracle_on_random_rational_pairs() -> None:
    from samajh.ops.report import _chances

    rng = random.Random(1225)
    seen = set()
    for _ in range(3000):
        e1, e2 = rng.randint(1, 60), rng.randint(1, 60)
        low, high = sorted((Fraction(rng.randint(0, e1), e1), Fraction(rng.randint(0, e2), e2)))
        if high == 0:
            expected = "none"
        else:
            expected = "narrow" if low > 0 and high * 4 <= low * 5 else "wide"
        assert _chances(low, high) == expected, (low, high)
        seen.add(expected)
        if low and high * 4 == low * 5:
            seen.add("boundary")
    assert seen == {"none", "narrow", "wide", "boundary"}
