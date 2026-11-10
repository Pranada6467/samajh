"""Calls on loans that `samajh.ops` drew from the synthetic loan book.

The batch is read from `<state>/ops` through `samajh.ops.store.OpsStore` on every request (the
files are small), so a new draw shows up without a restart. Two questions are kept apart:

* `LoanBook.open_call`: may a call be placed on this loan on this day? Asked once, when the
  session is created. A refusal is a `LoanRefused` with a stable code; nothing is spoken.
* `LoanBook.resolve`: which record does an existing session use? Asked on every later request
  (a turn after a restart, the case build, a case read). It never re-checks eligibility: once the
  call is ingested the loan has a completed attempt, and the finished session must stay readable.

The link a session is created with (batch, draw, sale date, call date) is stored in its params,
so every later step sees the same link. The call date is in the book's calendar (January to March
2027), not the wall clock's: `samajh.ops.sessions.ingest` dates the attempt from it.

Every logged attempt counts towards the limit (`attempt_limit`), simulated or from the phone.
Known limit: two sessions for the same loan created before either is ingested are both allowed.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta, timezone
from pathlib import Path
from typing import Any

from samajh.ops import model as ops_model
from samajh.ops.model import RETRY_AFTER, WINDOW_DAYS, Attempt, BookLoan, Draw
from samajh.ops.store import NoBatch, OpsStore
from samajh.server.records import LOAN_ID, CallRecord, RecordBook

IST = timezone(timedelta(hours=5, minutes=30))
SYNTHETIC = " (synthetic)"
# Session params the server writes at creation. A client that sends one is refused.
LINK_PARAMS = ("batch_id", "draw_id", "sold_on", "call_date")
# ASCII digits only: `\d` would take Devanagari digits, and `date.fromisoformat` alone takes
# forms such as `20270120`.
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def attempt_limit() -> int:
    """The most attempts a loan gets, as `samajh.ops` sets it: `samajh.ops.model.MAX_ATTEMPTS`
    when it exists, else the default of `samajh.ops.simulate.run_draw(..., max_attempts=...)`.
    Read, never copied, so a change in ops is followed here."""
    named = getattr(ops_model, "MAX_ATTEMPTS", None)
    if isinstance(named, int):
        return named
    from samajh.ops.simulate import run_draw

    default = inspect.signature(run_draw).parameters["max_attempts"].default
    if not isinstance(default, int):
        raise TypeError("samajh.ops names no attempt limit")
    return default


class LoanRefused(Exception):
    """A call may not be placed. `code` is stable; `message` never repeats client input."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


@dataclass(frozen=True)
class BookLink:
    """The loan-book attempt a session is: fixed when the session is created."""

    batch_id: str
    draw_id: str
    loan_id: str
    sold_on: date
    call_date: date  # in the book's calendar

    @property
    def day_since_sale(self) -> int:
        return (self.call_date - self.sold_on).days

    def params(self) -> dict[str, str]:
        return {
            "loan": self.loan_id,
            "batch_id": self.batch_id,
            "draw_id": self.draw_id,
            "sold_on": self.sold_on.isoformat(),
            "call_date": self.call_date.isoformat(),
        }

    @classmethod
    def from_params(cls, params: Mapping[str, str]) -> BookLink:
        """The link stored in a session's params. ValueError if any part is missing or malformed."""
        missing = [k for k in ("loan", *LINK_PARAMS) if not params.get(k)]
        if missing:
            raise ValueError(f"a loan-book session lacks {missing}")
        if not re.fullmatch(LOAN_ID, params["loan"]):
            raise ValueError("malformed loan id")
        return cls(
            batch_id=params["batch_id"],
            draw_id=params["draw_id"],
            loan_id=params["loan"],
            sold_on=date.fromisoformat(params["sold_on"]),
            call_date=date.fromisoformat(params["call_date"]),
        )

    def evidence(self) -> dict[str, Any]:
        """The case file's `book` block: the attempt in the book's calendar (the case file's
        `started_at` stays wall-clock time)."""
        return {
            "batch_id": self.batch_id,
            "draw_id": self.draw_id,
            "sold_on": self.sold_on.isoformat(),
            "call_date": self.call_date.isoformat(),
            "day_since_sale": self.day_since_sale,
        }


def _refuse(status: int, code: str, message: str) -> LoanRefused:
    return LoanRefused(status, code, message)


def _day(attempt: Attempt) -> date:
    at = attempt.at if attempt.at.tzinfo else attempt.at.replace(tzinfo=IST)
    return at.astimezone(IST).date()


@dataclass(frozen=True)
class _Snapshot:
    batch_id: str
    lender_name: str
    loans: dict[str, BookLoan]
    draws: tuple[Draw, ...]
    attempts: tuple[Attempt, ...]

    def draw_of(self, loan_id: str) -> Draw | None:
        return next((d for d in self.draws if any(x.loan_id == loan_id for x in d.drawn)), None)

    def attempts_of(self, loan_id: str) -> list[Attempt]:
        return sorted((a for a in self.attempts if a.loan_id == loan_id), key=lambda a: a.number)


class LoanBook:
    def __init__(self, state: Path) -> None:
        self.store = OpsStore(state / "ops")

    def _snapshot(self) -> _Snapshot:
        try:
            meta = self.store.meta()
            loans = {loan.record.loan_id: loan for loan in self.store.book()}
        except NoBatch:
            raise _refuse(
                409, "no_batch", "no review batch: run `python -m samajh.ops init` and `draw`"
            ) from None
        return _Snapshot(
            meta.batch_id, meta.book.lender_name, loans, self.store.draws(), self.store.attempts()
        )

    # --- may a call be placed? -------------------------------------------------

    def open_call(self, loan_id: str, call_date: str | None = None) -> BookLink:
        """The link for a new call on `loan_id`, or `LoanRefused`.

        The call date defaults to the later of the draw's day plus the number of attempts already
        logged for the loan (the simulator's rule) and the day after the last logged attempt. A
        date given on or before that attempt's day is refused: ingest puts the call after it."""
        if not isinstance(loan_id, str) or not re.fullmatch(LOAN_ID, loan_id):
            raise _refuse(422, "invalid_loan_id", "a loan id looks like SYN-PL-270104-0001")
        wanted: date | None = None
        if call_date is not None:
            try:
                if not _DATE.fullmatch(call_date):
                    raise ValueError
                wanted = date.fromisoformat(call_date)
            except ValueError:
                raise _refuse(422, "invalid_call_date", "call_date is a day as YYYY-MM-DD") from None
        return self._open(self._snapshot(), loan_id, wanted)

    @staticmethod
    def _open(book: _Snapshot, loan_id: str, wanted: date | None) -> BookLink:
        loan = book.loans.get(loan_id)
        if loan is None:
            raise _refuse(404, "loan_not_on_book", "no loan with that id is on the batch's book")
        draw = book.draw_of(loan_id)
        if draw is None:
            raise _refuse(409, "loan_not_drawn", "that loan was not drawn in this batch")
        attempts = book.attempts_of(loan_id)
        if attempts and attempts[-1].outcome not in RETRY_AFTER:
            raise _refuse(409, "attempts_ended", "that loan's attempts have ended")
        limit = attempt_limit()
        if len(attempts) >= limit:
            raise _refuse(409, "attempt_limit", f"that loan has had its {limit} attempts")
        last_day = _day(attempts[-1]) if attempts else None
        if wanted is None:
            wanted = draw.as_of + timedelta(days=len(attempts))
            if last_day is not None:
                wanted = max(wanted, last_day + timedelta(days=1))
        if wanted < draw.as_of:
            raise _refuse(409, "before_draw", "the call date is before the loan was drawn")
        if (wanted - loan.sold_on).days > WINDOW_DAYS:
            raise _refuse(
                409, "outside_window", f"the call date is more than {WINDOW_DAYS} days after the sale"
            )
        if last_day is not None and wanted <= last_day:
            raise _refuse(
                409, "before_last_attempt", "the call date is not after the day of the loan's last attempt"
            )
        return BookLink(book.batch_id, draw.draw_id, loan_id, loan.sold_on, wanted)

    def callable(self) -> list[dict[str, Any]]:
        """The drawn loans a call may be placed on now (on each one's default call date), for the
        phone's picker, from one read of the store. Never a value the call tests. [] when there is
        no batch."""
        try:
            book = self._snapshot()
        except LoanRefused:
            return []
        rows: list[dict[str, Any]] = []
        for draw in book.draws:
            for drawn in draw.drawn:
                try:
                    link = self._open(book, drawn.loan_id, None)
                except LoanRefused:
                    continue
                borrower = book.loans[drawn.loan_id].record.borrower
                rows.append(
                    {
                        "loan_id": drawn.loan_id,
                        "first_name": borrower.name.split()[0],
                        "language": borrower.language.value,
                        "birth_year": borrower.dob.year,  # for the person who plays the customer
                        "lender_name": book.lender_name,
                        "batch_id": link.batch_id,
                        "draw_id": link.draw_id,
                        "sold_on": link.sold_on.isoformat(),
                        "call_date": link.call_date.isoformat(),
                        "day_since_sale": link.day_since_sale,
                    }
                )
        return rows

    # --- which record does a session use? --------------------------------------

    def resolve(self, params: Mapping[str, str]) -> tuple[CallRecord, BookLink]:
        """The record of a session created on a loan. ValueError when the session's link no longer
        names a drawn loan of the batch in the store (another batch, a lost draw). No eligibility."""
        link = BookLink.from_params(params)
        try:
            book = self._snapshot()
        except LoanRefused as refused:
            raise ValueError(refused.message) from None
        if book.batch_id != link.batch_id:
            raise ValueError("the session was made on another batch")
        loan = book.loans.get(link.loan_id)
        draw = next((d for d in book.draws if d.draw_id == link.draw_id), None)
        if loan is None or draw is None or not any(x.loan_id == link.loan_id for x in draw.drawn):
            raise ValueError("the session's loan is no longer a drawn loan of the batch")
        if loan.sold_on != link.sold_on:
            raise ValueError("the session's sale date is not the book's")
        lender = book.lender_name.removesuffix(SYNTHETIC)  # spoken; the marker stays on screen and in files
        record = CallRecord(
            id=link.loan_id,
            label=f"{link.loan_id} (synthetic loan book)",
            description=f"Drawn in {link.draw_id}; call date {link.call_date.isoformat()} in the book's calendar.",
            lender_name=lender,
            record=loan.record,
        )
        return record, link


def resolve_record(
    params: Mapping[str, str], book: RecordBook | None, loans: LoanBook | None
) -> tuple[CallRecord, BookLink | None]:
    """A session's record: `record` names a packaged record, `loan` a loan-book loan, never both.
    Raises ValueError (KeyError never escapes)."""
    if "record" in params and "loan" in params:
        raise ValueError("a session names a record or a loan, not both")
    if "loan" in params:
        if loans is None:
            raise ValueError("this server has no loan book")
        return loans.resolve(params)
    if book is None:
        raise ValueError("this server has no record book")
    try:
        return book.get(params.get("record", "")), None
    except KeyError:
        raise ValueError(f"unknown record {params.get('record')!r}") from None
