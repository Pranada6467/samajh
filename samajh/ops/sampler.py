"""The random selection of loans to call, built so that anyone can recompute it from the book."""

import random
from collections.abc import Collection, Sequence
from datetime import date

from samajh.ops.model import WINDOW_DAYS, BookLoan, BookMeta, Draw, DrawnLoan


def eligible(
    book: Sequence[BookLoan], as_of: date, min_day: int = 0, max_day: int = WINDOW_DAYS
) -> list[BookLoan]:
    """The loans sold between `min_day` and `max_day` days before `as_of` (inclusive), sorted by loan id."""
    inside = (loan for loan in book if min_day <= (as_of - loan.sold_on).days <= max_day)
    return sorted(inside, key=lambda loan: loan.record.loan_id)


def _select(
    book: Sequence[BookLoan],
    as_of: date,
    size: int,
    seed: int,
    taken: Collection[str],
    min_day: int,
    max_day: int,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[DrawnLoan, ...]]:
    """(eligible ids, ids in the window that an earlier draw took, the loans drawn in draw order)."""
    inside = eligible(book, as_of, min_day, max_day)
    free = [loan for loan in inside if loan.record.loan_id not in taken]
    chosen = random.Random(f"{seed}|{as_of}").sample(free, min(size, len(free)))
    return (
        tuple(loan.record.loan_id for loan in free),
        tuple(loan.record.loan_id for loan in inside if loan.record.loan_id in taken),
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
    size: int,
    seed: int,
    already_drawn: Collection[str],
    min_day: int = 0,
    max_day: int = WINDOW_DAYS,
) -> Draw:
    """Draw up to `size` loans, as the `Draw` docstring says. `already_drawn`: ids earlier draws took."""
    free, taken, drawn = _select(book, as_of, size, seed, already_drawn, min_day, max_day)
    return Draw(
        draw_id=f"D-{as_of.isoformat()}",
        as_of=as_of,
        min_day=min_day,
        max_day=max_day,
        size=size,
        seed=seed,
        book_sha256=meta.sha256,
        eligible=free,
        already_drawn=taken,
        drawn=drawn,
    )


def verify_draw(draw: Draw, book: Sequence[BookLoan], earlier_draws: Sequence[Draw]) -> bool:
    """Recompute the selection from the book and the draws before it. True when nothing differs."""
    taken = {d.loan_id for earlier in earlier_draws for d in earlier.drawn}
    recomputed = _select(book, draw.as_of, draw.size, draw.seed, taken, draw.min_day, draw.max_day)
    return recomputed == (draw.eligible, draw.already_drawn, draw.drawn)
