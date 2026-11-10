"""Where one batch lives on disk: `<state>/ops/`.

    batch.json          the BatchMeta
    book.jsonl          a copy of the book, so the server needs only the state directory
    draws.jsonl         one Draw per line
    attempts.jsonl      one Attempt per line; the last line per attempt id is the one that stands
    calls/<call_id>.json    one CallRecord per analysed call
    dispositions.jsonl  one Disposition per line; append-only, the latest per case stands
    outside.jsonl       one OutsideCall per line: phone calls that are not attempts in the sample;
                        the last line per session id stands
    ingest.json         the IngestSummary of the last ingest of phone sessions

Every write is safe to repeat. A write takes the store's file lock, so threads and processes can
share the store; the lock is reentrant within one `OpsStore`, so a caller can hold it across
several writes (`OpsStore.locked`). A whole file is written to a temporary file and moved into place.

The logs are append-only, and each append is one write of a whole line. A crash in the middle of
an append can still leave a torn last line with no newline: readers skip it when it does not parse,
and the next append, under the lock, moves it to `<log>.torn` first, so the log stays readable and
nothing is deleted. A line that does not parse anywhere else is an error. The one change allowed to an entry is an explicit supersede (the new
line carries `supersedes`): a phone session's `completed_not_analysed` replaced by `completed`.
"""

import os
import re
from collections.abc import Callable, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

from filelock import FileLock
from pydantic import BaseModel

from samajh.ops import book as books
from samajh.ops.model import (
    DEFAULT_UNIT,
    SESSION_ID_PATTERN,
    Attempt,
    AttemptOutcome,
    BatchMeta,
    BookLoan,
    BookMeta,
    CallRecord,
    Disposition,
    Draw,
    IngestSummary,
    OutsideCall,
)

M = TypeVar("M", bound=BaseModel)
CALL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$")


class NoBatch(Exception):
    """The store holds no batch yet."""


def _split_tail(data: bytes) -> tuple[bytes, bytes]:
    """A log's bytes as (every whole line, the last line when it has no newline)."""
    end = data.rfind(b"\n") + 1
    return data[:end], data[end:]


def _parse_or_none(model: type[M], line: bytes) -> M | None:
    try:
        return model.model_validate_json(line)
    except ValueError:  # pydantic's ValidationError, or bytes that are not UTF-8
        return None


def may_supersede(existing: Attempt | OutsideCall, row: Attempt | OutsideCall) -> bool:
    """`row` may replace `existing`: the same entry, but `completed_not_analysed` became `completed`
    with its analysed call, and `row` says so."""
    return (
        existing.supersedes is None
        and existing.outcome is AttemptOutcome.completed_not_analysed
        and existing.call_id is None
        and row.outcome is AttemptOutcome.completed
        and row.call_id is not None
        and row.supersedes is AttemptOutcome.completed_not_analysed
        and existing
        == row.model_copy(update={"outcome": existing.outcome, "call_id": None, "supersedes": None})
    )


class OpsStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._filelock: FileLock | None = None

    def locked(self) -> FileLock:
        """The store's lock, to hold across several writes; reentrant within this `OpsStore`."""
        return self._lock()

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
        """One effective entry per attempt (the last line with its id), in the order first logged."""
        return self._read("attempts.jsonl", Attempt, key=lambda a: a.attempt_id)

    def add_attempt(self, attempt: Attempt) -> None:
        """Log an attempt. The same attempt again: no change. Another with its id: an error, unless
        it is an explicit supersede of `completed_not_analysed` by `completed` (`supersedes`)."""
        self._append("attempts.jsonl", attempt, Attempt, lambda a: a.attempt_id, may_supersede)

    def dispositions(self) -> tuple[Disposition, ...]:
        """Every recorded decision, oldest first."""
        return self._read("dispositions.jsonl", Disposition)

    def add_disposition(self, disposition: Disposition) -> None:
        """Append a decision. Nothing is ever changed or removed; an identical entry is stored once."""
        self._append("dispositions.jsonl", disposition, Disposition, lambda d: d)

    def outside(self) -> tuple[OutsideCall, ...]:
        """One effective entry per session (the last line with its id), in the order first logged."""
        return self._read("outside.jsonl", OutsideCall, key=lambda c: c.session_id)

    def add_outside(self, call: OutsideCall) -> None:
        """Log a phone call outside the sample. The same call again: no change. Another for the same
        session: an error, unless it is the explicit supersede that `add_attempt` allows."""
        self._append("outside.jsonl", call, OutsideCall, lambda c: c.session_id, may_supersede)

    # --- the last ingest ---

    def ingest_summary(self) -> IngestSummary | None:
        try:
            return IngestSummary.model_validate_json((self.root / "ingest.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def save_ingest_summary(self, summary: IngestSummary) -> None:
        """Keep the last ingest's summary. The same summary again: the file is not rewritten."""
        with self._lock():
            if self.ingest_summary() != summary:
                self._replace(self.root / "ingest.json", summary.model_dump_json(indent=2) + "\n")

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

    def drop_unreferenced_session_calls(self) -> tuple[str, ...]:
        """Remove each phone session's call file that no effective attempt or outside call names.
        Such a file is left only by a write interrupted between saving the call and logging its
        entry (the call is always saved first); the next ingest writes it again. Returns the ids."""
        session = re.compile(SESSION_ID_PATTERN)
        with self._lock():
            named = {a.call_id for a in self.attempts()} | {o.call_id for o in self.outside()}
            folder = self.root / "calls"
            dropped = tuple(
                sorted(
                    p.stem
                    for p in (folder.glob("*.json") if folder.is_dir() else ())
                    if session.fullmatch(p.stem) and p.stem not in named
                )
            )
            for call_id in dropped:
                self._call_path(call_id).unlink()
            return dropped

    # --- files ---

    def _call_path(self, call_id: str) -> Path:
        if not CALL_ID.fullmatch(call_id):
            raise ValueError(f"not a call id: {call_id!r}")
        return self.root / "calls" / f"{call_id}.json"

    def _lock(self) -> FileLock:
        if self._filelock is None:
            self.root.mkdir(parents=True, exist_ok=True)
            self._filelock = FileLock(self.root / ".lock")
        return self._filelock

    def _read(self, name: str, model: type[M], key: Callable[[M], object] | None = None) -> tuple[M, ...]:
        """Every line; with `key`, the last line per key, in the order each key first appears.

        A last line with no newline that does not parse is a torn append (a write cut short, or one
        still in progress in another process) and is not read; `_append` moves it aside. Any other
        line that does not parse is an error."""
        try:
            data = (self.root / name).read_bytes()
        except FileNotFoundError:
            return ()
        whole, tail = _split_tail(data)
        rows = [model.model_validate_json(line) for line in whole.decode("utf-8").splitlines() if line]
        if tail:
            parsed = _parse_or_none(model, tail)
            if parsed is not None:
                rows.append(parsed)
        if key is None:
            return tuple(rows)
        effective: dict[object, M] = {}
        for row in rows:
            effective[key(row)] = row
        return tuple(effective.values())

    def _append(
        self,
        name: str,
        row: M,
        model: type[M],
        key: Callable[[M], object],
        may_replace: Callable[[M, M], bool] | None = None,
    ) -> None:
        with self._lock():
            for existing in self._read(name, model, key if may_replace else None):
                if key(existing) == key(row):
                    if existing == row:
                        return
                    if may_replace is None or not may_replace(existing, row):
                        raise ValueError(f"{name} already holds a different entry for {key(row)}")
                    break
            path = self.root / name
            self._mend_tail(path, model)
            line = (row.model_dump_json() + "\n").encode("utf-8")
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                written = os.write(fd, line)  # one write of the whole line
                while written < len(line):  # a short write to a local file is rare; finish the line
                    written += os.write(fd, line[written:])
                os.fsync(fd)
            finally:
                os.close(fd)

    @staticmethod
    def _mend_tail(path: Path, model: type[M]) -> None:
        """Under the lock, before an append: a last line with no newline is ended with one when it
        parses, and otherwise (a torn append) moved to `<name>.torn` and cut from the log, so the
        next line never runs on from it. The fragment is kept, one per line, never deleted."""
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return
        whole, tail = _split_tail(data)
        if not tail:
            return
        if _parse_or_none(model, tail) is not None:
            fd = os.open(path, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, b"\n")
                os.fsync(fd)
            finally:
                os.close(fd)
            return
        side = path.with_name(f"{path.name}.torn")
        fd = os.open(side, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, tail + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
        os.truncate(path, len(whole))

    @staticmethod
    def _replace(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
