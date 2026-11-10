from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from itertools import pairwise

import pytest

from samajh.ops import book as books
from samajh.ops.__main__ import DEMO_DRAWS
from samajh.ops.model import DrawnLoan
from samajh.ops.sampler import draw, eligible, size_for, verify_draw

AS_OF = date(2027, 2, 8)


@pytest.fixture(scope="module")
def book():
    meta, loans, _ = books.generate_book(85)
    return meta, loans


def _chain(meta, loans, days, rate=0.4, seed=85):
    draws, after = [], None
    for as_of in days:
        draws.append(draw(loans, meta, as_of, rate, seed, after))
        after = as_of
    return draws


def test_a_draw_is_reproducible_and_takes_only_loans_sold_in_the_last_30_days(book) -> None:
    meta, loans = book
    first = draw(loans, meta, AS_OF, 0.4, seed=85, after=None)
    assert first == draw(loans, meta, AS_OF, 0.4, seed=85, after=None)
    assert first.drawn != draw(loans, meta, AS_OF, 0.4, seed=86, after=None).drawn
    assert first.draw_id == "D-2027-02-08" and first.book_sha256 == meta.sha256
    sold = {loan.record.loan_id: loan.sold_on for loan in loans}
    in_window = sorted(i for i, day in sold.items() if 0 <= (AS_OF - day).days <= 30)
    assert list(first.eligible) == in_window == [loan.record.loan_id for loan in eligible(loans, AS_OF)]
    assert len(first.drawn) == size_for(0.4, len(in_window)) == round(0.4 * len(in_window))
    for d in first.drawn:
        assert d.sold_on == sold[d.loan_id] and d.day_since_sale == (AS_OF - d.sold_on).days
        assert 0 <= d.day_since_sale <= 30


def test_windows_do_not_overlap_so_each_sale_is_eligible_once_with_the_same_chance(book) -> None:
    meta, loans = book
    draws = _chain(meta, loans, DEMO_DRAWS)
    seen = Counter(loan_id for d in draws for loan_id in d.eligible)
    assert set(seen.values()) == {1}  # no sale is eligible in two draws
    assert len(seen) == len(loans)  # the demo draws cover every sale on the book
    for earlier, later in pairwise(draws):
        assert later.after == earlier.as_of
        assert all(
            later.as_of - timedelta(days=30) <= x.sold_on and x.sold_on > earlier.as_of for x in later.drawn
        )
    chances = [d.inclusion for d in draws]
    assert all(abs(c - 0.4) <= 0.5 / min(len(d.eligible) for d in draws) + 1e-9 for c in chances)


def test_a_sale_in_a_gap_longer_than_30_days_between_draws_is_never_eligible(book) -> None:
    meta, loans = book
    first, later = _chain(meta, loans, (date(2027, 1, 11), date(2027, 3, 1)))
    gap = {x.record.loan_id for x in loans if date(2027, 1, 11) < x.sold_on < date(2027, 1, 30)}
    assert gap and not gap & (set(first.eligible) | set(later.eligible))


def test_a_rate_of_one_takes_every_eligible_loan_and_a_draw_must_follow_the_previous_one(book) -> None:
    meta, loans = book
    everything = draw(loans, meta, AS_OF, 1.0, seed=85, after=None)
    assert sorted(d.loan_id for d in everything.drawn) == list(everything.eligible)
    with pytest.raises(ValueError):
        draw(loans, meta, AS_OF, 0.4, seed=85, after=AS_OF)


def test_verify_recomputes_the_draw_and_its_chain(book) -> None:
    meta, loans = book
    first, second = _chain(meta, loans, (AS_OF, AS_OF + timedelta(weeks=1)))
    assert verify_draw(first, loans, None) and verify_draw(second, loans, first)
    assert not verify_draw(second, loans, None)  # its window must start where the previous ended

    drawn_ids = {d.loan_id for d in first.drawn}
    outsider = next(loan for loan in eligible(loans, AS_OF) if loan.record.loan_id not in drawn_ids)
    swapped = DrawnLoan(
        loan_id=outsider.record.loan_id,
        sold_on=outsider.sold_on,
        day_since_sale=(AS_OF - outsider.sold_on).days,
    )
    forged = first.model_copy(update={"drawn": (swapped, *first.drawn[1:])})
    assert not verify_draw(forged, loans, None)


def test_the_store_refuses_a_draw_that_does_not_start_where_the_last_one_ended(book, tmp_path) -> None:
    """The store's own check, apart from `verify_draw`: a draw is written only when its `after` is
    the previous draw's day (None for the first), so no window overlaps or skips the one before."""
    from datetime import UTC, datetime

    from samajh.ops.store import OpsStore

    meta, loans = book
    store = OpsStore(tmp_path / "ops")
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
    later = AS_OF + timedelta(weeks=1)
    with pytest.raises(ValueError, match="does not start where the previous draw ended"):
        store.add_draw(draw(loans, meta, AS_OF, 0.4, 85, after=AS_OF - timedelta(days=3)))  # first: no after
    assert store.draws() == ()
    first = draw(loans, meta, AS_OF, 0.4, 85, after=None)
    store.add_draw(first)
    for after in (None, AS_OF - timedelta(days=1), AS_OF + timedelta(days=1)):  # overlaps, overlaps, skips
        with pytest.raises(ValueError, match="does not start where the previous draw ended"):
            store.add_draw(draw(loans, meta, later, 0.4, 85, after=after))
    assert store.draws() == (first,)
    store.add_draw(first)  # the same draw again: no change
    second = draw(loans, meta, later, 0.4, 85, after=AS_OF)
    store.add_draw(second)
    assert store.draws() == (first, second)
