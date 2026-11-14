"""Retention of phone session directories (`<state>/sessions/<id>/`: the log, the turn audio, call.wav).

Off unless a number of days is set (`--days`, else `SAMAJH_RETENTION_DAYS`). A candidate is an ended
session created more than that many days ago. Kept, with the reason: an active session, a session
whose case is a referral with no final decision (`samajh.ops.model.FINAL_DECISIONS`), and a directory whose session.json does not parse
(nothing unreadable is deleted). Each deletion appends one line to `<state>/ops/retention.jsonl`
with the session's chain head, seal and recording sha256, so the deletion leaves a record.

Not deleted by this: the ops store's analysed call (`ops/calls/<id>.json`, which holds the
transcript) and the decision log.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ENV = "SAMAJH_RETENTION_DAYS"
STAYS = (
    "Not deleted by this command: the ops store's analysed calls (ops/calls/<id>.json, which hold "
    "the transcript) and the decision log (ops/dispositions.jsonl)."
)


@dataclass(frozen=True)
class Row:
    session_id: str
    action: str  # "delete" | "keep"
    reason: str


def retention_days(days: int | None) -> int | None:
    if days is not None:
        return days
    raw = os.environ.get(ENV, "").strip()
    return int(raw) if raw else None


def _batch_state(ops_root: Path) -> tuple[set[str], set[str]]:
    """(case ids that are referrals with no final decision, case ids with a final decision).
    Case ids are session ids for phone cases."""
    from samajh.ops.batch import load_batch
    from samajh.ops.store import NoBatch, OpsStore

    try:
        batch = load_batch(OpsStore(ops_root))
    except (NoBatch, FileNotFoundError):
        return set(), set()
    referred = [s.call.call_id for s in batch.referrals]
    referred += [s.call.call_id for s in batch.late if s.referred]
    referred += [
        o.record.call_id for o in batch.outside if o.record and o.triage and o.triage.tier == "refer"
    ]
    open_cases = {c for c in referred if c is not None and not batch.decided(c)}
    decided = {c for c in referred if c is not None and batch.decided(c)}
    return open_cases, decided


def _own_case_open(session_dir: Path) -> str | None:
    """Why the session's own case.json keeps it (a referral, or a case that is not ready), or None.
    No case.json: None (nothing to review)."""
    try:
        case = json.loads((session_dir / "case.json").read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return "its case.json does not parse: nothing unreadable is deleted"
    if not isinstance(case, dict):
        return "its case.json does not parse: nothing unreadable is deleted"
    if case.get("status") != "ready":
        return f"its case file is not ready (status {case.get('status')!r})"
    if case.get("tier") == "refer":
        return "its case file is a referral with no final decision in the ops batch"
    return None


def plan(state: Path, days: int, now: datetime | None = None) -> list[Row]:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=days)
    sessions = state / "sessions"
    if not sessions.is_dir():
        return []
    if days < 1:
        raise ValueError("--days must be at least 1")
    open_cases, decided = _batch_state(state / "ops")
    rows: list[Row] = []
    for d in sorted(p for p in sessions.iterdir() if p.is_dir()):
        try:
            data = json.loads((d / "session.json").read_bytes())
            created = datetime.fromisoformat(data["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
        except (OSError, ValueError, KeyError, TypeError):
            rows.append(Row(d.name, "keep", "session.json does not parse: nothing unreadable is deleted"))
            continue
        if created >= cutoff:
            continue
        if data.get("status") != "ended":
            rows.append(Row(d.name, "keep", "the session is still active"))
        elif d.name in open_cases:
            rows.append(Row(d.name, "keep", "its case is a referral with no final decision"))
        elif d.name not in decided and (why := _own_case_open(d)) is not None:
            rows.append(Row(d.name, "keep", why))
        else:
            rows.append(Row(d.name, "delete", f"ended, created {created:%Y-%m-%d}, older than {days} days"))
    return rows


def delete(state: Path, rows: list[Row], now: datetime | None = None) -> list[str]:
    """Remove each "delete" row's directory and log it to `ops/retention.jsonl`."""
    log = state / "ops" / "retention.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    done = []
    for row in rows:
        if row.action != "delete":
            continue
        d = state / "sessions" / row.session_id
        data = json.loads((d / "session.json").read_bytes())
        chain = data.get("chain") or {}
        entry = {
            "session_id": row.session_id,
            "deleted_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
            "created_at": data.get("created_at"),
            "session_head": chain.get("head"),
            "session_seal": chain.get("seal"),
            "recording_sha256": (data.get("recording") or {}).get("sha256"),
        }
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        shutil.rmtree(d)
        done.append(row.session_id)
    return done


def run(state: Path, days: int | None, *, do_delete: bool) -> int:
    try:
        n = retention_days(days)
    except ValueError:
        print(f"{ENV} is not a whole number of days", file=sys.stderr)
        return 2
    if n is None:
        print("retention is off: nothing deleted")
        return 0
    if n < 1:
        print("--days must be at least 1", file=sys.stderr)
        return 2
    rows = plan(state, n)
    for row in rows:
        verb = ("deleting" if do_delete else "would delete") if row.action == "delete" else "keeping"
        print(f"{verb} {row.session_id}: {row.reason}")
    if not rows:
        print(f"no session is older than {n} days")
    if do_delete:
        print(f"deleted {len(delete(state, rows))} session directories (logged in ops/retention.jsonl)")
    elif any(r.action == "delete" for r in rows):
        print("nothing deleted: run again with --delete")
    print(STAYS)
    return 0
