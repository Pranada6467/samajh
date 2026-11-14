"""Reviewer decisions bound to the case they were made on, and the chain over the decision log.

The formats are in `samajh.evidence` ("Decisions"). Everything here reads raw files: no server or
ops import, so the verifier needs only the state directory.
"""

from __future__ import annotations

import json
from pathlib import Path

from samajh.evidence.digest import GENESIS, after_epoch, sha256_hex, tagged
from samajh.evidence.ledger import DISPOSITIONS_HEAD, compare_head

CASE_TAG = "samajh-case-v1"


def case_digest(ops_root: Path, sessions: Path | None, case_id: str) -> str:
    """`tagged("samajh-case-v1", sha256(ops/calls/<case_id>.json), <phone case seal or "none">)`.

    The phone part is the phone session's `case.json` `seal.content_sha256` when the call's source is
    a phone session and that file has one; otherwise "none"."""
    path = ops_root / "calls" / f"{case_id}.json"
    raw = path.read_bytes()
    return tagged(CASE_TAG, sha256_hex(raw), _phone_seal(raw, sessions))


def _phone_seal(call_raw: bytes, sessions: Path | None) -> str:
    if sessions is None:
        return "none"
    try:
        source = json.loads(call_raw).get("source") or {}
    except (ValueError, AttributeError):
        return "none"
    session_id = source.get("session_id") if source.get("kind") == "phone_session" else None
    if not isinstance(session_id, str) or "/" in session_id or session_id in ("", ".", ".."):
        return "none"
    try:
        case = json.loads((sessions / session_id / "case.json").read_bytes())
        content = case["seal"]["content_sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        return "none"
    return content if isinstance(content, str) and content else "none"


def _lines(data: bytes) -> list[bytes]:
    """Every non-empty line of a log, without its newline (a last line with no newline included)."""
    return [line for line in data.split(b"\n") if line]


def last_line_sha256(path: Path) -> str:
    """sha256 of the raw bytes of the log's last line, or GENESIS when the log is empty or absent:
    the `prev_sha256` of the next line."""
    try:
        lines = _lines(path.read_bytes())
    except FileNotFoundError:
        return GENESIS
    return sha256_hex(lines[-1]) if lines else GENESIS


def verify_dispositions(path: Path) -> tuple[bool, str | None, str | None]:
    """Check the chain of `dispositions.jsonl`: (ok, the first problem in words, head).

    Every line from the first that carries `prev_sha256` on must name the sha256 of the previous
    line's raw bytes (GENESIS for line 1); older lines before it are covered as the bytes it chains
    to. A line that carries `case_digest` or `reviewer_auth` was written by the new code and so must
    carry `prev_sha256`: stripping it cannot pass a new line off as an old one. `head` is the sha256 of the last line's raw bytes (None for an empty or absent log): it is
    what an outside copy is compared with, since an edit to the last line breaks no link: the copy
    kept beside the log is `dispositions.head.json` (line count and head), and a log that differs
    from it is a mismatch. A line dated at or after the evidence epoch must carry `prev_sha256`."""
    try:
        lines = _lines(path.read_bytes())
    except FileNotFoundError:
        lines = []
    head = sha256_hex(lines[-1]) if lines else None
    chained = False
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except ValueError:
            return False, f"line {number} is not JSON", head
        prev = row.get("prev_sha256") if isinstance(row, dict) else None
        if prev is None and isinstance(row, dict):
            if row.get("case_digest") is not None:
                return False, f"line {number} has a case digest but no prev_sha256", head
            if row.get("reviewer_auth") is not None:
                return False, f"line {number} has reviewer_auth but no prev_sha256", head
            if isinstance(row.get("recorded_at"), str) and after_epoch(row["recorded_at"]):
                return (
                    False,
                    f"line {number} is dated after the evidence epoch but has no chain (prev_sha256)",
                    head,
                )
        if prev is None:
            if chained:
                return False, f"line {number} has no prev_sha256 after the chain began", head
            continue
        chained = True
        expected = sha256_hex(lines[number - 2]) if number > 1 else GENESIS
        if prev != expected:
            return False, f"line {number} does not link to the line before it", head
    if chained or (path.parent / DISPOSITIONS_HEAD).exists():
        problem = compare_head(path.parent / DISPOSITIONS_HEAD, lines, path.name)
        if problem:
            return False, problem, head
    return True, None, head
