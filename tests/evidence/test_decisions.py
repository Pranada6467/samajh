"""Reviewer decisions chained in dispositions.jsonl and bound to the case they were made on."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from samajh.evidence.decisions import case_digest, verify_dispositions
from samajh.evidence.digest import GENESIS, sha256_hex
from samajh.ops.__main__ import main
from samajh.ops.batch import load_batch
from samajh.ops.model import Decision, Disposition
from samajh.ops.store import OpsStore
from samajh.ops.views import CaseChanged, DispositionIn, case_view, queue_view, record_disposition

NOW = datetime(2027, 3, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def demo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    state = tmp_path_factory.mktemp("demo")
    assert main(["demo", "--state", str(state)]) == 0
    return state


@pytest.fixture
def store(demo: Path, tmp_path: Path) -> OpsStore:
    return OpsStore(Path(shutil.copytree(demo, tmp_path / "state")) / "ops")


def _cases(store: OpsStore) -> list[str]:
    return [i.case_id for i in queue_view(load_batch(store)).items]


def _decide(store: OpsStore, case_id: str, note: str = "seen", at: datetime = NOW) -> None:
    digest = case_view(load_batch(store), case_id).case_digest
    body = DispositionIn(decision=Decision.call_customer, note=note, case_digest=digest)
    record_disposition(store, case_id, body, at, reviewer="Token Name", reviewer_auth="token")


def _log(store: OpsStore) -> Path:
    return store.root / "dispositions.jsonl"


def _lines(store: OpsStore) -> list[bytes]:
    return _log(store).read_bytes().splitlines()


def _decided_three(store: OpsStore) -> list[bytes]:
    for n, case_id in enumerate(_cases(store)[:3]):
        _decide(store, case_id, note=f"note {n}")
    return _lines(store)


def test_each_decision_links_to_the_raw_bytes_of_the_line_before(store: OpsStore) -> None:
    lines = _decided_three(store)
    prevs = [json.loads(line)["prev_sha256"] for line in lines]
    assert prevs == [GENESIS, sha256_hex(lines[0]), sha256_hex(lines[1])]
    assert verify_dispositions(_log(store)) == (True, None, sha256_hex(lines[2]))


def test_a_decision_is_bound_to_the_case_and_names_the_token_reviewer(store: OpsStore) -> None:
    case_id = _cases(store)[0]
    _decide(store, case_id)
    stored = store.dispositions()[0]
    assert stored.case_digest == case_digest(store.root, None, case_id)
    assert stored.reviewer == "Token Name" and stored.reviewer_auth == "token"
    view = case_view(load_batch(store), case_id).history[0]
    assert view.case_digest == stored.case_digest and view.reviewer_auth == "token"


def test_the_digest_changes_when_the_call_file_changes(store: OpsStore) -> None:
    case_id = _cases(store)[0]
    before = case_digest(store.root, None, case_id)
    path = store.root / "calls" / f"{case_id}.json"
    path.write_bytes(path.read_bytes() + b" ")
    assert case_digest(store.root, None, case_id) != before


def test_a_stale_digest_is_refused_and_nothing_is_appended(store: OpsStore) -> None:
    case_id = _cases(store)[0]
    stale = case_view(load_batch(store), case_id).case_digest
    path = store.root / "calls" / f"{case_id}.json"
    path.write_bytes(path.read_bytes() + b"\n")
    body = DispositionIn(decision=Decision.call_customer, note="n", case_digest=stale)
    with pytest.raises(CaseChanged):
        record_disposition(store, case_id, body, NOW, reviewer="X", reviewer_auth="token")
    assert store.dispositions() == ()


def test_the_phone_case_seal_is_part_of_the_digest(tmp_path: Path) -> None:
    ops, sessions = tmp_path / "ops", tmp_path / "sessions"
    sid = "20261110T142233-9f2c4e1ab07d"
    (ops / "calls").mkdir(parents=True)
    (ops / "calls" / f"{sid}.json").write_text(
        json.dumps({"source": {"kind": "phone_session", "session_id": sid}})
    )
    unsealed = case_digest(ops, sessions, sid)
    (sessions / sid).mkdir(parents=True)
    (sessions / sid / "case.json").write_text(json.dumps({"seal": {"content_sha256": "a" * 64}}))
    sealed = case_digest(ops, sessions, sid)
    (sessions / sid / "case.json").write_text(json.dumps({"seal": {"content_sha256": "b" * 64}}))
    assert len({unsealed, sealed, case_digest(ops, sessions, sid)}) == 3
    assert unsealed == case_digest(ops, None, sid)


def test_old_lines_still_load_and_the_chain_starts_after_them(store: OpsStore) -> None:
    cases = _cases(store)
    old = Disposition(
        case_id=cases[0], decision=Decision.call_customer, note="old", reviewer="free",
        recorded_at=datetime(2026, 11, 10, tzinfo=UTC),  # before the evidence epoch
    )  # fmt: skip
    old_line = old.model_dump_json().encode()
    assert b"prev_sha256" not in old_line and b"case_digest" not in old_line
    _log(store).write_bytes(old_line + b"\n")
    _decide(store, cases[1])
    _decide(store, cases[2])
    lines = _lines(store)
    assert lines[0] == old_line
    assert json.loads(lines[1])["prev_sha256"] == sha256_hex(old_line)
    assert store.dispositions()[0] == old and store.dispositions()[0].reviewer_auth is None
    assert verify_dispositions(_log(store))[0] is True


def test_an_identical_decision_is_stored_once(store: OpsStore) -> None:
    case_id = _cases(store)[0]
    _decide(store, case_id)
    _decide(store, case_id)
    assert len(_lines(store)) == 1


def test_an_edited_middle_line_breaks_the_next_link(store: OpsStore) -> None:
    lines = _decided_three(store)
    lines[1] = lines[1].replace(b"note 1", b"note X")
    _log(store).write_bytes(b"\n".join(lines) + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and problem.startswith("line 3 ")


def test_a_deleted_middle_line_is_caught(store: OpsStore) -> None:
    lines = _decided_three(store)
    _log(store).write_bytes(lines[0] + b"\n" + lines[2] + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and problem.startswith("line 2 ")


def test_a_decision_moved_to_another_case_breaks_the_chain(store: OpsStore) -> None:
    lines = _decided_three(store)
    row = json.loads(lines[0])
    row["case_id"] = _cases(store)[5]
    lines[0] = json.dumps(row, separators=(",", ":")).encode()
    _log(store).write_bytes(b"\n".join(lines) + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and problem.startswith("line 2 ")


def test_two_swapped_lines_are_caught(store: OpsStore) -> None:
    lines = _decided_three(store)
    lines[1], lines[2] = lines[2], lines[1]
    _log(store).write_bytes(b"\n".join(lines) + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and problem.startswith("line 2 ")


def test_a_line_without_a_link_after_the_chain_began_is_caught(store: OpsStore) -> None:
    lines = _decided_three(store)
    row = json.loads(lines[2])
    del row["prev_sha256"]
    lines[2] = json.dumps(row).encode()
    _log(store).write_bytes(b"\n".join(lines) + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and "line 3" in problem


def test_an_empty_log_verifies_with_no_head(tmp_path: Path) -> None:
    assert verify_dispositions(tmp_path / "dispositions.jsonl") == (True, None, None)


def test_an_unchained_line_dated_after_the_epoch_is_a_mismatch(store: OpsStore) -> None:
    cases = _cases(store)
    line = Disposition(
        case_id=cases[0], decision=Decision.call_customer, note="x", reviewer="free", recorded_at=NOW
    ).model_dump_json()
    _log(store).write_text(line + "\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and "dated after the evidence epoch" in problem


def test_the_head_file_catches_a_deleted_or_edited_last_line(store: OpsStore) -> None:
    lines = _decided_three(store)
    head = json.loads((store.root / "dispositions.head.json").read_bytes())
    assert head == {"lines": 3, "head": sha256_hex(lines[-1])}
    _log(store).write_bytes(b"\n".join(lines[:2]) + b"\n")
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and "the last line differs from dispositions.head.json" in problem
    _log(store).write_bytes(b"\n".join([*lines[:2], lines[2].replace(b"note 2", b"note X")]) + b"\n")
    assert not verify_dispositions(_log(store))[0]
    _log(store).unlink()
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and "says 3 lines" in problem


def test_a_missing_head_file_with_chained_lines_is_a_mismatch(store: OpsStore) -> None:
    _decided_three(store)
    (store.root / "dispositions.head.json").unlink()
    ok, problem, _ = verify_dispositions(_log(store))
    assert not ok and "dispositions.head.json is missing" in problem
