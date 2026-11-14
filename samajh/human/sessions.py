"""Loading session logs, case files, card gold and the call log as plain JSON dicts.

Read with `.get(...)`, never through the pydantic models, so logs written before a field existed
and logs written after both load.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from samajh.server.samajh_dialogue import answers_year_question

# Copied from eval/p5/score.py (LOAN_KEYS, MATTER_STEPS): a bot line that names the loan.
MATTER_STEPS = frozenset({"context", "open_recall", "teach_back", "consent_check", "read_back"})
LOAN_KEYS = frozenset({"context.loan", "verify.after_loan"})


@dataclass
class Session:
    dir: Path
    log: dict[str, Any]
    case: dict[str, Any] | None
    customer_id: str | None = None  # from a P5 run's calls/*.json
    gold: dict[str, Any] | None = field(default=None)
    card: str | None = None

    @property
    def id(self) -> str:
        return self.log.get("session_id") or self.dir.name

    @property
    def events(self) -> list[dict[str, Any]]:
        return self.log.get("events") or []

    def event(self, seq: Any) -> dict[str, Any] | None:
        if not isinstance(seq, int):
            return None
        for e in self.events:
            if e.get("seq") == seq:
                return e
        return None

    def customers(self, counted: bool = True) -> list[dict[str, Any]]:
        out = [e for e in self.events if e.get("type") == "customer"]
        return [e for e in out if not e.get("superseded")] if counted else out

    def bots(self, counted: bool = True) -> list[dict[str, Any]]:
        out = [e for e in self.events if e.get("type") == "bot"]
        return [e for e in out if not e.get("superseded")] if counted else out

    def asked(self, c: dict[str, Any]) -> dict[str, Any] | None:
        return self.event(c.get("reply_to"))

    def reply(self, c: dict[str, Any]) -> dict[str, Any] | None:
        e = self.event((c.get("seq") or 0) + 1)
        return e if e and e.get("type") == "bot" else None

    def source(self) -> str:
        kinds = sorted({c.get("source") for c in self.customers() if c.get("source") in ("mic", "file")})
        return "/".join(kinds) or "none"

    def void(self) -> bool:
        if any(c.get("degraded") for c in self.customers()):
            return True
        return bool((self.case or {}).get("degraded_turns"))

    def outcome(self) -> str | None:
        if self.case and self.case.get("call_outcome"):
            return self.case["call_outcome"]
        for b in reversed(self.bots()):
            if (b.get("tags") or {}).get("outcome"):
                return b["tags"]["outcome"]
        return None

    def tier(self) -> str:
        if self.case and self.case.get("status") == "ready":
            return self.case.get("tier") or "none"
        return "no case"

    def loan_named(self) -> bool:
        for b in self.bots():
            for ln in b.get("lines") or []:
                if ln.get("key") in LOAN_KEYS or (ln.get("tags") or {}).get("step") in MATTER_STEPS:
                    return True
        return False

    def is_year_answer(self, c: dict[str, Any]) -> bool:
        asked = self.asked(c)
        lines = [SimpleNamespace(tags=ln.get("tags") or {}) for ln in (asked or {}).get("lines") or []]
        return answers_year_question(lines)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _load_dir(d: Path, customer_id: str | None = None) -> Session | None:
    log = _read_json(d / "session.json")
    if log is None:
        return None
    return Session(d, log, _read_json(d / "case.json"), customer_id)


def _find_by_id(state: Path, sid: str) -> Path | None:
    for cand in [state / "sessions" / sid, *state.glob(f"*/sessions/{sid}")]:
        if (cand / "session.json").exists():
            return cand
    return None


def load_sessions(paths: list[Path], state: Path) -> list[Session]:
    """A session dir, a sessions root, or a P5 run dir (calls/*.json) per path."""
    out: list[Session] = []
    for p in paths:
        if (p / "session.json").exists():
            s = _load_dir(p)
            out += [s] if s else []
        elif (p / "calls").is_dir():
            for call_file in sorted((p / "calls").glob("*.json")):
                call = _read_json(call_file) or {}
                sid = call.get("session_id")
                found = _find_by_id(state, sid) if sid else None
                s = _load_dir(found, call.get("customer_id")) if found else None
                out += [s] if s else []
        else:
            for d in sorted(p.iterdir()) if p.is_dir() else []:
                s = _load_dir(d) if (d / "session.json").exists() else None
                out += [s] if s else []
    seen, unique = set(), []
    for s in out:
        if s.id not in seen:
            seen.add(s.id)
            unique.append(s)
    return unique


def load_gold(path: Path) -> dict[str, dict[str, Any]]:
    """Gold rows keyed by `id` and by `card_id`."""
    rows: list[dict[str, Any]] = []
    if path.is_file():
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    elif path.is_dir():
        files = sorted((path / "gold").glob("*.gold.json")) or sorted(path.glob("*.gold.json"))
        rows = [r for r in (_read_json(f) for f in files) if r]
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        for k in (r.get("id"), r.get("card_id")):
            if k:
                out[k] = r
    return out


def load_call_log(path: Path) -> dict[str, str]:
    """session_id -> card_id."""
    if not path.is_file():
        return {}
    with path.open(newline="") as f:
        return {r["session_id"]: r["card_id"] for r in csv.DictReader(f) if r.get("session_id")}


def attach_gold(sessions: list[Session], gold: dict[str, dict], log: dict[str, str]) -> None:
    for s in sessions:
        key = log.get(s.id) or s.customer_id
        s.card = key
        s.gold = gold.get(key) if key else None
