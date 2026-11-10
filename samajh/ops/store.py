"""Where one batch lives on disk: `<state>/ops/`.

    batch.json          the BatchMeta
    book.jsonl          a copy of the book, so the server needs only the state directory
    draws.jsonl         one Draw per line
    attempts.jsonl      one Attempt per line
    calls/<call_id>.json    one CallRecord per analysed call
    dispositions.jsonl  one Disposition per line; append-only, the latest per case stands
    outside.jsonl       one OutsideCall per line: phone calls whose loan was not drawn

Every write is safe to repeat. An append takes a file lock, so threads and processes can share
the store; a whole file is written to a temporary file and moved into place.
"""

import os
import re
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

from filelock import FileLock
from pydantic import BaseModel

from samajh.ops import book as books
from samajh.ops.model import (
    DEFAULT_UNIT,
    Attempt,
    BatchMeta,
    BookLoan,
    BookMeta,
    CallRecord,
    Disposition,
    Draw,
    OutsideCall,
)

M = TypeVar("M", bound=BaseModel)
CALL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$")


class NoBatch(Exception):
    """The store holds no batch yet."""


class OpsStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    # --- the batch and its book ---

    def init(
        self,
        book: BookMeta,
        loans: Sequence[BookLoan],
        period_start: date,
        period_end: date,
        now: datetime,
        unit: str = DEFAULT_UNIT,
    ) -> BatchMeta:
        """Start the batch. Again with the same book and period: no change. With another: an error."""
        if books.book_sha256(loans) != book.sha256:
            raise ValueError("the loans are not the book that the metadata describes")
        with self._lock():
            if (self.root / "batch.json").exists():
                existing = self.meta()
                same = (existing.book, existing.period_start, existing.period_end) == (
                    book,
                    period_start,
                    period_end,
                )
                if not same:
                    raise ValueError(
                        f"{self.root} already holds batch {existing.batch_id} for another book or period"
                    )
                return existing
            half = 1 if period_start.month <= 6 else 2
            meta = BatchMeta(
                batch_id=f"B-{period_start.year}H{half}-{book.sha256[:8]}",
                book=book,
                period_start=period_start,
                period_end=period_end,
                simulated=True,
                created_at=now,
                unit=unit,
            )
            self._replace(self.root / "book.jsonl", books.jsonl(loans))
            self._replace(self.root / "batch.json", meta.model_dump_json(indent=2) + "\n")
            return meta

    def meta(self) -> BatchMeta:
        try:
            return BatchMeta.model_validate_json((self.root / "batch.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise NoBatch(f"no batch in {self.root}: run `python -m samajh.ops init` first") from None

    def book(self) -> tuple[BookLoan, ...]:
        self.meta()
        return books.parse_loans((self.root / "book.jsonl").read_text(encoding="utf-8"))

    # --- the logs ---

    def draws(self) -> tuple[Draw, ...]:
        return self._read("draws.jsonl", Draw)

    def add_draw(self, draw: Draw) -> None:
        """Log a draw. The same draw again: no change. Another draw with its id: an error. A new draw
        must start where the last one ended, so that no two windows overlap."""
        if draw.book_sha256 != self.meta().book.sha256:
            raise ValueError(f"draw {draw.draw_id} was made from another book")
        earlier = self.draws()
        if draw not in earlier and draw.after != (earlier[-1].as_of if earlier else None):
            raise ValueError(f"draw {draw.draw_id} does not start where the previous draw ended")
        self._append("draws.jsonl", draw, Draw, lambda d: d.draw_id)

    def attempts(self) -> tuple[Attempt, ...]:
        return self._read("attempts.jsonl", Attempt)

    def add_attempt(self, attempt: Attempt) -> None:
        """Log an attempt. The same attempt again: no change. Another with its id: an error."""
        self._append("attempts.jsonl", attempt, Attempt, lambda a: a.attempt_id)

    def dispositions(self) -> tuple[Disposition, ...]:
        """Every recorded decision, oldest first."""
        return self._read("dispositions.jsonl", Disposition)

    def add_disposition(self, disposition: Disposition) -> None:
        """Append a decision. Nothing is ever changed or removed; an identical entry is stored once."""
        self._append("dispositions.jsonl", disposition, Disposition, lambda d: d)

    def outside(self) -> tuple[OutsideCall, ...]:
        return self._read("outside.jsonl", OutsideCall)

    def add_outside(self, call: OutsideCall) -> None:
        """Log a phone call outside the sample. The same call again: no change."""
        self._append("outside.jsonl", call, OutsideCall, lambda c: c.session_id)

    # --- analysed calls ---

    def call(self, call_id: str) -> CallRecord | None:
        try:
            return CallRecord.model_validate_json(self._call_path(call_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def save_call(self, call: CallRecord) -> None:
        """Save an analysed call. A call that is already saved is left as it is."""
        path = self._call_path(call.call_id)
        with self._lock():
            if not path.exists():
                self._replace(path, call.model_dump_json(indent=2) + "\n")

    # --- files ---

    def _call_path(self, call_id: str) -> Path:
        if not CALL_ID.fullmatch(call_id):
            raise ValueError(f"not a call id: {call_id!r}")
        return self.root / "calls" / f"{call_id}.json"

    def _lock(self) -> FileLock:
        self.root.mkdir(parents=True, exist_ok=True)
        return FileLock(self.root / ".lock")

    def _read(self, name: str, model: type[M]) -> tuple[M, ...]:
        try:
            text = (self.root / name).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ()
        whole = text[: text.rfind("\n") + 1]  # a line still being appended by another process is not read
        return tuple(model.model_validate_json(line) for line in whole.splitlines() if line)

    def _append(self, name: str, row: M, model: type[M], key) -> None:
        with self._lock():
            for existing in self._read(name, model):
                if key(existing) == key(row):
                    if existing != row:
                        raise ValueError(f"{name} already holds a different entry for {key(row)}")
                    return
            with (self.root / name).open("a", encoding="utf-8") as f:
                f.write(row.model_dump_json() + "\n")
                f.flush()
                os.fsync(f.fileno())

    @staticmethod
    def _replace(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
