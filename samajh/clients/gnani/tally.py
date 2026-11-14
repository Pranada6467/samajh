"""An incremental reader of the shared ledger for the credit cap and the streaming budget.

`Ledger.total_credits()` parses the whole file, which on a large shared ledger costs most of a
second inside the one-slot lock. A `LedgerTally` remembers how far it has read and its running
sums, and on each call parses only the complete lines appended since. Lines are parsed exactly as
`Ledger.entries()` parses them (invalid lines skipped) and summed in file order, so the totals equal
`Ledger.total_credits()`. A file that shrank, was replaced, or no longer matches the bytes before
the old offset is rescanned from the start.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from samajh.clients._runtime import LedgerEntry

_ANCHOR = 64  # bytes before the offset re-read to check the file is the one we read


@dataclass(frozen=True)
class Totals:
    gnani_credits: float
    stream_seconds: float  # sum of audio_seconds over gnani `stt.stream` rows


class LedgerTally:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._reset()
        self.bytes_read = 0  # cumulative bytes read from the file, for tests and diagnostics

    def _reset(self) -> None:
        self._offset = 0
        self._inode: tuple[int, int] | None = None
        self._anchor = b""
        self._credits: float = 0
        self._stream: float = 0

    def totals(self) -> Totals:
        with self._lock:
            self._advance()
            return Totals(float(self._credits), float(self._stream))

    def gnani_credits(self) -> float:
        return self.totals().gnani_credits

    def stream_seconds(self) -> float:
        return self.totals().stream_seconds

    def _advance(self) -> None:
        try:
            f = open(self.path, "rb")  # noqa: SIM115
        except FileNotFoundError:
            self._reset()
            return
        with f:
            st = os.fstat(f.fileno())
            ident = (st.st_dev, st.st_ino)
            if self._inode != ident or st.st_size < self._offset or not self._anchor_matches(f):
                self._reset()
                self._inode = ident
            f.seek(self._offset)
            data = f.read()
            self.bytes_read += len(data)
            end = data.rfind(b"\n")
            if end < 0:
                return
            chunk = data[: end + 1]
            for raw in chunk.split(b"\n"):
                for line in raw.splitlines():  # the same splitting as Ledger.entries()
                    self._add(line)
            self._offset += end + 1
            self._anchor = chunk[-_ANCHOR:] if len(chunk) >= _ANCHOR else (self._anchor + chunk)[-_ANCHOR:]

    def _anchor_matches(self, f: object) -> bool:
        if not self._anchor:
            return True
        start = self._offset - len(self._anchor)
        f.seek(start)  # type: ignore[attr-defined]
        got = f.read(len(self._anchor))  # type: ignore[attr-defined]
        self.bytes_read += len(got)
        return got == self._anchor

    def _add(self, line: bytes) -> None:
        try:
            e = LedgerEntry.model_validate_json(line)
        except ValidationError:
            return
        if e.provider != "gnani":
            return
        self._credits += e.est_credits
        if e.kind == "stt.stream":
            self._stream += e.audio_seconds or 0.0


_TALLIES: dict[Path, LedgerTally] = {}
_TALLIES_LOCK = threading.Lock()


def tally_for(path: Path) -> LedgerTally:
    """The one tally for this ledger path in this process."""
    key = Path(os.path.abspath(path))
    with _TALLIES_LOCK:
        t = _TALLIES.get(key)
        if t is None:
            t = _TALLIES[key] = LedgerTally(key)
        return t
