"""Retention of phone session directories: off by default, lists before it deletes, leaves a record."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_bundle import demo, phone_base  # noqa: F401  (fixtures)

from samajh.ops.__main__ import main as ops
from samajh.ops.retention import plan

OLD = (datetime.now(UTC) - timedelta(days=40)).isoformat()


def _session(state: Path, sid: str, created_at: str = OLD, status: str = "ended") -> Path:
    d = state / "sessions" / sid
    d.mkdir(parents=True)
    body = {"session_id": sid, "created_at": created_at, "status": status,
            "chain": {"version": 1, "entries": 3, "head": "h" * 64, "seal": "s" * 64},
            "recording": {"sha256": "r" * 64}}  # fmt: skip
    (d / "session.json").write_text(json.dumps(body))
    return d


def test_off_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("SAMAJH_RETENTION_DAYS", raising=False)
    d = _session(tmp_path, "old")
    assert ops(["retention", "--state", str(tmp_path), "--delete"]) == 0
    assert "retention is off: nothing deleted" in capsys.readouterr().out and d.exists()


def test_lists_without_deleting(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("SAMAJH_RETENTION_DAYS", "30")
    d = _session(tmp_path, "old")
    _session(tmp_path, "new", created_at=datetime.now(UTC).isoformat())
    assert ops(["retention", "--state", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "would delete old" in out and "new" not in out.replace("nothing", "")
    assert d.exists() and not (tmp_path / "ops" / "retention.jsonl").exists()
    assert "ops/calls" in out  # says plainly what stays


def test_deletes_an_old_ended_session_and_logs_it(tmp_path: Path) -> None:
    d = _session(tmp_path, "old")
    keep_new = _session(tmp_path, "new", created_at=datetime.now(UTC).isoformat())
    assert ops(["retention", "--state", str(tmp_path), "--days", "30", "--delete"]) == 0
    assert not d.exists() and keep_new.exists()
    (row,) = [json.loads(x) for x in (tmp_path / "ops" / "retention.jsonl").read_text().splitlines()]
    assert row["session_id"] == "old" and row["created_at"] == OLD
    assert (row["session_head"], row["session_seal"], row["recording_sha256"]) == (
        "h" * 64,
        "s" * 64,
        "r" * 64,
    )
    assert row["deleted_at"]


def test_keeps_an_active_session_and_an_unreadable_one(tmp_path: Path, capsys) -> None:
    active = _session(tmp_path, "live", status="active")
    broken = tmp_path / "sessions" / "broken"
    broken.mkdir(parents=True)
    (broken / "session.json").write_text("{not json")
    assert ops(["retention", "--state", str(tmp_path), "--days", "1", "--delete"]) == 0
    out = capsys.readouterr().out
    assert active.exists() and broken.exists()
    assert "keeping live: the session is still active" in out and "keeping broken" in out


def test_keeps_the_session_of_an_undecided_referral(phone_base, tmp_path: Path) -> None:  # noqa: F811
    state, sid = phone_base
    state = Path(shutil.copytree(state, tmp_path / "state"))
    later = datetime.now(UTC) + timedelta(days=400)
    rows = {r.session_id: r for r in plan(state, 30, now=later)}
    assert rows[sid].action == "keep" and "referral" in rows[sid].reason


@pytest.mark.parametrize("final", ["concern_supported"])
def test_a_finally_decided_referral_session_may_go(phone_base, tmp_path: Path, final: str) -> None:  # noqa: F811
    from samajh.evidence.decisions import case_digest
    from samajh.ops.model import Decision, Disposition
    from samajh.ops.store import OpsStore

    state, sid = phone_base
    state = Path(shutil.copytree(state, tmp_path / "state"))
    store = OpsStore(state / "ops")
    store.add_disposition(Disposition(
        case_id=sid, decision=Decision(final), note="n", reviewer="R", recorded_at=datetime.now(UTC),
        case_digest=case_digest(store.root, state / "sessions", sid), reviewer_auth="token",
    ))  # fmt: skip
    rows = {r.session_id: r for r in plan(state, 30, now=datetime.now(UTC) + timedelta(days=400))}
    assert rows[sid].action == "delete"


def test_keeps_a_referral_that_is_not_yet_ingested(tmp_path: Path) -> None:
    d = _session(tmp_path, "pending")
    (d / "case.json").write_text(json.dumps({"status": "ready", "tier": "refer"}))
    failed = _session(tmp_path, "failed")
    (failed / "case.json").write_text(json.dumps({"status": "failed", "tier": None}))
    clear = _session(tmp_path, "clear")
    (clear / "case.json").write_text(json.dumps({"status": "ready", "tier": "clear"}))
    rows = {r.session_id: r for r in plan(tmp_path, 30)}
    assert rows["pending"].action == "keep" and "referral" in rows["pending"].reason
    assert rows["failed"].action == "keep" and "not ready" in rows["failed"].reason
    assert rows["clear"].action == "delete"


@pytest.mark.parametrize("days", ["0", "-3"])
def test_refuses_fewer_than_one_day(tmp_path: Path, days: str, capsys) -> None:
    d = _session(tmp_path, "old")
    assert ops(["retention", "--state", str(tmp_path), "--days", days, "--delete"]) == 2
    assert d.exists() and "at least 1" in capsys.readouterr().err


def test_export_of_a_session_deleted_by_retention_says_so(phone_base, tmp_path: Path, capsys) -> None:  # noqa: F811
    from samajh.evidence.__main__ import main as evidence
    from samajh.ops.retention import Row, delete

    state, sid = phone_base
    state = Path(shutil.copytree(state, tmp_path / "state"))
    delete(state, [Row(sid, "delete", "test")])
    capsys.readouterr()
    assert evidence(["export", "--case", sid, "--out", str(tmp_path / "b"), "--state", str(state)]) == 2
    assert "the session was deleted by retention on" in capsys.readouterr().err
