"""The random selection of loans to call, built so that anyone can recompute it from the book.

Draw windows do not overlap: a draw takes the sales made since the previous draw that are still
within 30 days of the sale, and takes its `rate` of them. A sale's chance of being sampled is its
draw's drawn / eligible (`Draw.inclusion`): the same for draws at one rate up to rounding, and
different for draws at different rates, which the report states (`report.sampling`). A sale no draw
covers is "never eligible", which the report counts with the reason.
"""

import random
from collections.abc import Sequence
from datetime import date

from samajh.ops.model import WINDOW_DAYS, BookLoan, BookMeta, Draw, DrawnLoan

DEFAULT_RATE = 0.4


def eligible(
    book: Sequence[BookLoan],
    as_of: date,
    after: date | None = None,
    min_day: int = 0,
    max_day: int = WINDOW_DAYS,
) -> list[BookLoan]:
    """Loans sold after `after` and between `min_day` and `max_day` days before `as_of`, by loan id."""
    inside = (
        loan
        for loan in book
        if min_day <= (as_of - loan.sold_on).days <= max_day and (after is None or loan.sold_on > after)
    )
    return sorted(inside, key=lambda loan: loan.record.loan_id)


def size_for(rate: float, eligible_count: int) -> int:
    """`round(rate * eligible)`, at least one when any loan is eligible."""
    return min(eligible_count, max(1, round(rate * eligible_count))) if eligible_count else 0


def _select(
    book: Sequence[BookLoan],
    as_of: date,
    after: date | None,
    rate: float,
    seed: int,
    min_day: int,
    max_day: int,
) -> tuple[tuple[str, ...], tuple[DrawnLoan, ...]]:
    inside = eligible(book, as_of, after, min_day, max_day)
    chosen = random.Random(f"{seed}|{as_of}").sample(inside, size_for(rate, len(inside)))
    return (
        tuple(loan.record.loan_id for loan in inside),
        tuple(
            DrawnLoan(
                loan_id=loan.record.loan_id, sold_on=loan.sold_on, day_since_sale=(as_of - loan.sold_on).days
            )
            for loan in chosen
        ),
    )


def draw(
    book: Sequence[BookLoan],
    meta: BookMeta,
    as_of: date,
    rate: float,
    seed: int,
    after: date | None,
    min_day: int = 0,
    max_day: int = WINDOW_DAYS,
) -> Draw:
    """Draw `rate` of the loans sold after `after` (the previous draw's day) and in the last 30 days."""
    if after is not None and after >= as_of:
        raise ValueError(f"a draw on {as_of} cannot follow a draw on {after}")
    found, drawn = _select(book, as_of, after, rate, seed, min_day, max_day)
    return Draw(
        draw_id=f"D-{as_of.isoformat()}",
        as_of=as_of,
        after=after,
        min_day=min_day,
        max_day=max_day,
        rate=rate,
        seed=seed,
        book_sha256=meta.sha256,
        eligible=found,
        drawn=drawn,
    )


def verify_draw(draw: Draw, book: Sequence[BookLoan], previous: Draw | None) -> bool:
    """Recompute the selection from the book. True when it matches and the window starts where
    the previous draw's ended (so no sale is eligible twice and none is skipped between draws)."""
    chained = draw.after == (previous.as_of if previous else None)
    found = _select(book, draw.as_of, draw.after, draw.rate, draw.seed, draw.min_day, draw.max_day)
    return chained and found == (draw.eligible, draw.drawn)
