"""The synthetic loan records a call can start from.

One JSON file per record, named `<id>.json`, holding a `CallRecord`. The packaged demo records
are in `records/` beside this module; `SAMAJH_RECORDS_DIR` names one more directory (the
evaluation writes its records there).
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from pydantic import StringConstraints, ValidationError

from samajh.types import Frozen, LoanRecord

PACKAGED_DIR = Path(__file__).with_name("records")
RECORD_ID = r"^[a-z0-9][a-z0-9-]{0,40}$"
_Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CallRecord(Frozen):
    id: Annotated[str, StringConstraints(pattern=RECORD_ID)]
    # For the operator who picks a record on the phone. Never spoken, never shown to the LLM.
    label: _Text
    description: _Text
    lender_name: _Text  # spoken in the disclosure; `LoanRecord` does not carry it
    record: LoanRecord


class RecordBook:
    def __init__(self, records: Iterable[CallRecord]) -> None:
        self._records: dict[str, CallRecord] = {}
        for record in records:
            if record.id in self._records:
                raise ValueError(f"duplicate record id {record.id!r}")
            self._records[record.id] = record

    def get(self, record_id: str) -> CallRecord:
        """Raises KeyError for an unknown id."""
        return self._records[record_id]

    def ids(self) -> list[str]:
        return sorted(self._records)

    def listing(self) -> list[dict[str, str]]:
        """What the phone's picker may show. Never a value the call tests."""
        return [
            {
                "id": r.id,
                "label": r.label,
                "description": r.description,
                "first_name": r.record.borrower.name.split()[0],
                "language": r.record.borrower.language.value,
            }
            for _, r in sorted(self._records.items())
        ]


def _load(path: Path) -> CallRecord:
    try:
        record = CallRecord.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise ValueError(f"{path}: not a call record: {error}") from None
    if record.id != path.stem:
        raise ValueError(f"{path}: the id {record.id!r} is not the file's name")
    if not record.record.borrower.name.split():
        raise ValueError(f"{path}: the borrower has no name")
    return record


def load_book(*directories: Path) -> RecordBook:
    """Every `*.json` in each directory. Raises ValueError on a file that is not exactly a
    `CallRecord` named after its id, on a directory that does not exist, and on a duplicate id."""
    records: list[CallRecord] = []
    for directory in directories:
        if not directory.is_dir():
            raise ValueError(f"{directory}: not a directory")
        records += [_load(path) for path in sorted(directory.glob("*.json"))]
    return RecordBook(records)


def default_book() -> RecordBook:
    """The packaged demo records, plus the records in the directory `SAMAJH_RECORDS_DIR` names."""
    extra = os.environ.get("SAMAJH_RECORDS_DIR", "").strip()
    return load_book(PACKAGED_DIR, *([Path(extra)] if extra else []))
