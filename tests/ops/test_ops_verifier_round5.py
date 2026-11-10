"""Ingest and report edges an independent verifier found: a session folder deleted after it was
brought in, the limits with no simulated attempt, the length of a reason, a result that does not
read, a call at the same time as the loan's last attempt, and the sold tile with uncovered sales."""

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

from opskit import SOLD, WALL, coached, loan, open_batch, phone_case, put_case, snapshot

from samajh.ops import sessions as sessions_module
from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import PhoneSession
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view

DRAWN_ON = SOLD + timedelta(days=3)


def nothing(record_id: str):
    return


def _assert_one_place_in_store(found, store: OpsStore) -> None:
    """linked and outside agree with the store, skipped holds nothing the store holds, and changed
    is within linked or outside."""
    attempts = {a.source.session_id for a in store.attempts() if isinstance(a.source, PhoneSession)}
    outside = {o.session_id for o in store.outside()}
    assert set(found.linked) == attempts and len(found.linked) == len(attempts)
    assert set(found.outside) == outside and len(found.outside) == len(outside)
    assert not {sid for sid, _ in found.skipped} & (attempts | outside)
    assert {sid for sid, _ in found.changed} <= attempts | outside


def test_a_linked_session_whose_folder_is_deleted_stays_linked_and_is_listed_as_changed(
    tmp_path: Path,
) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    first = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2))
    other = phone_case(store, b, coached(b), DRAWN_ON + timedelta(days=2), started=WALL + timedelta(hours=1))
    folder = put_case(sessions, first)
    put_case(sessions, other)
    assert len(ingest(store, sessions, nothing).linked) == 2
    kept = tmp_path / "kept"
    shutil.copytree(folder, kept)
    before = {k: v for k, v in snapshot(store.root).items() if k != "ingest.json"}

    shutil.rmtree(folder)
    found = ingest(store, sessions, nothing)
    sid = first["session_id"]
    assert sid in found.linked and found.skipped == []
    assert dict(found.changed) == {sid: sessions_module.FOLDER_GONE}
    assert "no longer in the sessions directory" in sessions_module.FOLDER_GONE
    _assert_one_place_in_store(found, store)
    assert {k: v for k, v in snapshot(store.root).items() if k != "ingest.json"} == before
    note = attempt_log_view(load_batch(store)).ingest_note
    assert "saw 2 phone session(s)" in note and "2 as attempts" in note, note

    snap = snapshot(store.root)
    assert ingest(store, sessions, nothing).changed == found.changed
    assert snapshot(store.root) == snap  # a second ingest changes no store file

    shutil.copytree(kept, folder)
    back = ingest(store, sessions, nothing)
    assert back.changed == [] and sid in back.linked


def test_an_outside_call_whose_folder_is_deleted_stays_outside_and_is_listed_as_changed(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), None)
    folder = put_case(sessions, case)
    assert ingest(store, sessions, nothing).outside == [case["session_id"]]
    shutil.rmtree(folder)
    found = ingest(store, sessions, nothing)
    assert found.outside == [case["session_id"]] and found.skipped == []
    assert dict(found.changed) == {case["session_id"]: sessions_module.FOLDER_GONE}
    _assert_one_place_in_store(found, store)


def _limits_without_simulation(store: OpsStore) -> None:
    limits = build_report(store).limits
    assert not [line for line in limits if "the simulation" in line.lower()], limits
    assert any("not a sample of any lender's customers" in line for line in limits), limits
    assert [line for line in limits if wording.banned_in(line)] == []


def test_the_limits_with_only_phone_attempts_do_not_speak_of_the_simulation(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2)))
    assert len(ingest(store, sessions, nothing).linked) == 1
    _limits_without_simulation(store)


def test_the_limits_with_only_an_outside_call_do_not_speak_of_the_simulation(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, coached(a), None))
    assert len(ingest(store, sessions, nothing).outside) == 1
    _limits_without_simulation(store)


def test_the_limits_with_simulated_attempts_keep_the_simulation_sentence() -> None:
    lines = wording.limits(True, simulated=2, phone_attempts=1)
    assert any("the mix of customers the simulation assumes" in line for line in lines)


def test_a_long_skip_reason_is_cut_to_the_limit_with_a_visible_cut(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2))
    put_case(sessions, case | {"loan_id": "L" * 100_000})
    found = ingest(store, sessions, nothing)
    [(_, reason)] = found.skipped
    assert len(reason) == sessions_module.REASON_LIMIT and reason.endswith("…")
    assert all(len(s.reason) <= sessions_module.REASON_LIMIT for s in store.ingest_summary().skipped)
    assert (store.root / "ingest.json").stat().st_size < 10_000


def test_a_long_changed_reason_is_cut_to_the_limit(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2))
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    put_case(sessions, case | {"book": case["book"] | {"batch_id": "B" * 100_000}})
    found = ingest(store, sessions, nothing)
    [(_, what)] = found.changed
    assert len(what) == sessions_module.REASON_LIMIT and what.endswith("…")


def test_an_empty_result_names_the_field_inside_the_result(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2)) | {"result": {}})
    [(_, reason)] = ingest(store, sessions, nothing).skipped
    assert "result.loan_id" in reason, reason


def test_a_second_session_at_the_same_time_as_the_last_attempt_is_skipped(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    day = DRAWN_ON + timedelta(days=2)
    first = phone_case(store, a, None, day, outcome="no_response")
    second = phone_case(store, a, coached(a), day, started=WALL + timedelta(days=1))  # same India time
    put_case(sessions, first)
    put_case(sessions, second)
    found = ingest(store, sessions, nothing)
    assert found.linked == [first["session_id"]]
    assert [sid for sid, _ in found.skipped] == [second["session_id"]] and found.skipped[0][1]
    assert len([x for x in store.attempts() if x.loan_id == a.record.loan_id]) == 1


def test_the_sold_tile_counts_sales_no_draw_covers(tmp_path: Path) -> None:
    a, b, late = loan(1), loan(2), loan(3, sold_on=SOLD + timedelta(days=40))
    store, _ = open_batch(tmp_path / "ops", [a, b, late], DRAWN_ON)
    report = build_report(store)
    assert report.sampling.eligible == 2
    assert report.tiles.sold == 3 == report.sampling.sales_in_period
