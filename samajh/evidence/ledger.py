"""Heads kept outside the logs, and the ledger of analysed call files (format: `samajh.evidence`,
"Call ledger" and "Head files").

`write_head` is called under the ops store's lock after each append to `dispositions.jsonl` or
`calls.chain.jsonl`. `append_call` is called by `OpsStore.save_call` (and when a call file is
removed). `verify_call_ledger` re-checks the ledger, its head file and every call file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from samajh.evidence.digest import GENESIS, after_epoch, digest, file_sha256, sha256_hex

LEDGER = "calls.chain.jsonl"
LEDGER_HEAD = "calls.chain.head.json"
DISPOSITIONS_HEAD = "dispositions.head.json"


def _entry_hash(entry: dict[str, Any]) -> str:
    return digest({k: v for k, v in entry.items() if k != "hash"})


def write_head(path: Path, lines: int, head: str | None) -> None:
    """`{"lines": n, "head": sha}`, written to a temporary file and moved into place."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps({"lines": lines, "head": head}) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_head(path: Path) -> dict[str, Any] | None:
    """The head file, or None when absent. Raises ValueError when it is not `{"lines", "head"}`."""
    try:
        data = json.loads(path.read_bytes())
    except FileNotFoundError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("lines"), int):
        raise ValueError(f"{path.name} is not {{lines, head}}")  # noqa: TRY004  (callers catch ValueError)
    return data


def raw_lines(data: bytes) -> list[bytes]:
    return [line for line in data.split(b"\n") if line]


def compare_head(head_path: Path, lines: list[bytes], log_name: str) -> str | None:
    """The problem in words when the log's line count or last line differs from its head file."""
    try:
        recorded = read_head(head_path)
    except ValueError:
        return f"{head_path.name} is malformed"
    if recorded is None:
        return f"{head_path.name} is missing while {log_name} has lines" if lines else None
    last = sha256_hex(lines[-1]) if lines else None
    if recorded["lines"] != len(lines) or recorded.get("head") != last:
        if not lines:
            return f"{log_name} is missing or empty but {head_path.name} says {recorded['lines']} lines"
        return f"the last line differs from {head_path.name} (lines {len(lines)} against {recorded['lines']})"
    return None


# --- the call ledger -------------------------------------------------------------------


def ledger_entries(ops_root: Path) -> list[dict[str, Any]]:
    try:
        data = (ops_root / LEDGER).read_bytes()
    except FileNotFoundError:
        return []
    end = data.rfind(b"\n") + 1
    return [json.loads(line) for line in raw_lines(data[:end])]


def append_call(ops_root: Path, call_id: str, sha256: str | None, at: str) -> dict[str, Any]:
    """Append one line for a call file written (`sha256` of its bytes) or removed (None), then
    rewrite the head file. Caller holds the store's lock."""
    path = ops_root / LEDGER
    entries = ledger_entries(ops_root)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        data = b""
    if data and not data.endswith(b"\n"):  # a torn append: keep the fragment aside, cut it
        end = data.rfind(b"\n") + 1
        with path.with_name(LEDGER + ".torn").open("ab") as f:
            f.write(data[end:] + b"\n")
        os.truncate(path, end)
    entry: dict[str, Any] = {
        "i": len(entries),
        "prev": entries[-1]["hash"] if entries else GENESIS,
        "call_id": call_id,
        "sha256": sha256,
        "at": at,
    }
    entry["hash"] = _entry_hash(entry)
    line = json.dumps(entry, ensure_ascii=False).encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line + b"\n")
        os.fsync(fd)
    finally:
        os.close(fd)
    write_head(ops_root / LEDGER_HEAD, len(entries) + 1, sha256_hex(line))
    return entry


def ledger_head(ops_root: Path) -> tuple[str | None, int]:
    try:
        lines = raw_lines((ops_root / LEDGER).read_bytes())
    except FileNotFoundError:
        return None, 0
    return (sha256_hex(lines[-1]) if lines else None), len(lines)


def call_dated_after_epoch(call: Any, batch_created_at: str | None) -> bool:
    """A call file is new when its phone session id is dated at or after the epoch, or (a simulated
    call) its batch was created at or after it."""
    source = call.get("source") if isinstance(call, dict) else None
    if isinstance(source, dict) and source.get("kind") == "phone_session":
        return after_epoch(source.get("session_id"))
    return after_epoch(batch_created_at)


def batch_created_at(ops_root: Path) -> str | None:
    try:
        value = json.loads((ops_root / "batch.json").read_bytes()).get("created_at")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def verify_call_ledger(ops_root: Path) -> tuple[list[str], list[str], str | None]:
    """(mismatches, unverifiable, head): the ledger's links and hashes, its head file, and every
    call file's sha256 against the latest ledger line for it."""
    problems: list[str] = []
    unverifiable: list[str] = []
    path = ops_root / LEDGER
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        data = b""
    lines = raw_lines(data)
    head = sha256_hex(lines[-1]) if lines else None
    latest: dict[str, str | None] = {}
    prev = GENESIS
    for n, line in enumerate(lines):
        try:
            e = json.loads(line)
            if not isinstance(e, dict):
                raise ValueError  # noqa: TRY004
        except ValueError:
            return [f"{LEDGER} line {n} does not parse"], unverifiable, head
        if e.get("i") != n or e.get("prev") != prev or e.get("hash") != _entry_hash(e):
            return [f"{LEDGER} entry {n} (call {e.get('call_id')}): link or hash does not match"], [], head
        prev = e["hash"]
        latest[e.get("call_id")] = e.get("sha256")
    problem = compare_head(ops_root / LEDGER_HEAD, lines, LEDGER)
    if problem:
        problems.append(f"{LEDGER}: {problem}")
    created = batch_created_at(ops_root)
    folder = ops_root / "calls"
    files = {p.stem: p for p in folder.glob("*.json")} if folder.is_dir() else {}
    for call_id, p in sorted(files.items()):
        if call_id not in latest:
            try:
                call = json.loads(p.read_bytes())
            except ValueError:
                call = None
            if call_dated_after_epoch(call, created):
                problems.append(f"call {call_id}: dated after the evidence epoch but has no ledger line")
            else:
                unverifiable.append(f"call {call_id}: written before the call ledger")
            continue
        if latest[call_id] is None:
            problems.append(f"call {call_id}: the ledger says it was removed, but the file exists")
        elif file_sha256(p) != latest[call_id]:
            problems.append(f"call {call_id}: sha256 differs from its line in {LEDGER}")
    for call_id, sha in sorted(latest.items()):
        if sha is not None and call_id not in files:
            problems.append(f"call {call_id}: in {LEDGER} but its file is missing")
    return problems, unverifiable, head
