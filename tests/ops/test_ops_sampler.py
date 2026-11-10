from __future__ import annotations

from datetime import date

import pytest

from samajh.ops import book as books
from samajh.ops.model import DrawnLoan
from samajh.ops.sampler import draw, eligible, verify_draw

AS_OF = date(2027, 2, 8)


@pytest.fixture(scope="module")
def book():
    meta, loans, _ = books.generate_book(85)
    return meta, loans


def test_a_draw_is_reproducible_and_takes_only_loans_sold_in_the_last_30_days(book) -> None:
    meta, loans = book
    first = draw(loans, meta, AS_OF, 20, seed=85, already_drawn=())
    assert first == draw(loans, meta, AS_OF, 20, seed=85, already_drawn=())
    assert first.drawn != draw(loans, meta, AS_OF, 20, seed=86, already_drawn=()).drawn
    assert first.draw_id == "D-2027-02-08" and first.book_sha256 == meta.sha256
    assert len(first.drawn) == 20 == len({d.loan_id for d in first.drawn})
    sold = {loan.record.loan_id: loan.sold_on for loan in loans}
    for d in first.drawn:
        assert d.sold_on == sold[d.loan_id]
        assert d.day_since_sale == (AS_OF - d.sold_on).days
        assert 0 <= d.day_since_sale <= 30
    in_window = sorted(i for i, day in sold.items() if 0 <= (AS_OF - day).days <= 30)
    assert list(first.eligible) == in_window == [loan.record.loan_id for loan in eligible(loans, AS_OF)]


def test_a_later_draw_never_takes_a_loan_again_and_records_what_it_left_out(book) -> None:
    meta, loans = book
    first = draw(loans, meta, AS_OF, 20, seed=85, already_drawn=())
    taken = {d.loan_id for d in first.drawn}
    second = draw(loans, meta, date(2027, 2, 15), 20, seed=85, already_drawn=taken)
    assert not taken & {d.loan_id for d in second.drawn}
    assert not taken & set(second.eligible)
    assert second.already_drawn and set(second.already_drawn) <= taken


def test_a_draw_larger_than_the_window_takes_every_eligible_loan(book) -> None:
    meta, loans = book
    everything = draw(loans, meta, AS_OF, 10_000, seed=85, already_drawn=())
    assert sorted(d.loan_id for d in everything.drawn) == list(everything.eligible)


def test_verify_recomputes_the_draw_and_fails_when_a_drawn_loan_is_swapped(book) -> None:
    meta, loans = book
    first = draw(loans, meta, AS_OF, 20, seed=85, already_drawn=())
    second = draw(loans, meta, date(2027, 2, 15), 20, seed=85, already_drawn={d.loan_id for d in first.drawn})
    assert verify_draw(first, loans, ()) and verify_draw(second, loans, (first,))
    assert not verify_draw(second, loans, ())  # the earlier draw is part of what is recomputed

    drawn_ids = {d.loan_id for d in first.drawn}
    outsider = next(loan for loan in eligible(loans, AS_OF) if loan.record.loan_id not in drawn_ids)
    swapped = DrawnLoan(
        loan_id=outsider.record.loan_id,
        sold_on=outsider.sold_on,
        day_since_sale=(AS_OF - outsider.sold_on).days,
    )
    forged = first.model_copy(update={"drawn": (swapped, *first.drawn[1:])})
    assert not verify_draw(forged, loans, ())
