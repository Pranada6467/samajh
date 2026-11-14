"""Shared paths, the seed, the per-field draw and the flag-to-field map for the ACQ customer set."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from samajh.types import FlagReason  # noqa: E402

DATA = ROOT / "data" / "acq"
RECORDS = DATA / "records"
SEED = "samajh-acq-2026-11-14"
FIELDS = ("kind", "premium", "source", "frequency", "required", "cover", "term", "cancel", "money_back", "consent")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records_digest(directory: Path = RECORDS) -> str:
    """sha256 of one line per `*.json` file, sorted by name: `<sha256 of the bytes>  <file name>\\n`
    (the same definition as `eval/p5/bank.py`)."""
    lines = "".join(f"{sha256(p)}  {p.name}\n" for p in sorted(directory.glob("*.json"), key=lambda p: p.name))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(dump_jsonl(rows), encoding="utf-8")


def u(customer_id: str, field: str, axis: str) -> float:
    """A draw in [0, 1) fixed by the seed, the customer, the field and the axis ("a" or "r")."""
    if axis not in ("a", "r"):
        raise ValueError(f"axis must be 'a' or 'r', got {axis!r}")
    digest = hashlib.sha256(f"{SEED}|{customer_id}|{field}|{axis}".encode()).hexdigest()
    return int(digest[:8], 16) / 2**32


_R = FlagReason
# The belief field each flag reason is about (from what each reason tests in samajh/rules/checks.py).
# Placed by hand where the prefix rule does not decide it:
#   bundled_described_as_deposit -> kind: raised because the customer calls the product a deposit.
#   recall_* -> kind: open recall is whether the customer names the product as what it is.
#   answers_conflict, sale_concern -> None: they follow a question or the sale, not one belief field.
FLAG_FIELD: dict[FlagReason, str | None] = {
    _R.kind_differs: "kind",
    _R.kind_dont_know: "kind",
    _R.premium_differs_confirmed: "premium",
    _R.premium_differs: "premium",
    _R.premium_dont_know: "premium",
    _R.premium_approximate: "premium",
    _R.premium_said_zero: "premium",
    _R.cover_differs: "cover",
    _R.cover_differs_confirmed: "cover",
    _R.cover_differs_unconfirmed: "cover",
    _R.cover_dont_know: "cover",
    _R.term_differs: "term",
    _R.term_dont_know: "term",
    _R.cancel_unaware: "cancel",
    _R.cancel_dont_know: "cancel",
    _R.cancel_window_differs: "cancel",
    _R.cancel_window_dont_know: "cancel",
    _R.cancel_not_on_record: "cancel",
    _R.recall_not_named: "kind",
    _R.recall_denied: "kind",
    _R.recall_off_record: "kind",
    _R.consent_no_record: "consent",
    _R.consent_not_recognised: "consent",
    _R.consent_method_differs: "consent",
    _R.consent_dont_know: "consent",
    _R.consent_product_not_named: "consent",
    _R.funded_no_consent: "source",
    _R.funded_says_separately: "source",
    _R.funded_dont_know: "source",
    _R.unfunded_says_deducted: "source",
    _R.payment_says_not_charged: "source",
    _R.bundled_not_mitigant: "required",
    _R.bundled_described_as_deposit: "kind",
    _R.bundled_no_choice_on_record: "required",
    _R.bundled_no_choice_told: "required",
    _R.feature_contradicted: "money_back",
    _R.feature_dont_know: "money_back",
    _R.frequency_recurring_on_single: "frequency",
    _R.frequency_dont_know: "frequency",
    _R.sale_concern: None,
    _R.answers_conflict: None,
}
if set(FLAG_FIELD) != set(FlagReason):
    raise RuntimeError(f"FLAG_FIELD misses {sorted(set(FlagReason) - set(FLAG_FIELD))}")
