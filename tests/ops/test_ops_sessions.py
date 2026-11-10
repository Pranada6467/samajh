"""Real phone sessions enter the batch through their case files (committed P1 artifacts)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, time, timedelta
from pathlib import Path

import pytest
from serverkit import FakeSpeech
from starlette.testclient import TestClient

from samajh.dialogue.machine import Outcome
from samajh.ops.batch import load_batch
from samajh.ops.model import FROM_DIALOGUE, AttemptOutcome, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import IST, PARTIAL_NOTE, ingest, packaged_records
from samajh.ops.store import OpsStore
from samajh.ops.views import AttemptLogView, CaseView, QueueView, case_view, queue_view
from samajh.server import create_app

P1 = Path(__file__).resolve().parents[2] / "references" / "pilots" / "p1-artifacts"
CALLS = ("hero", "informed", "informed-run1", "third-party")


def _case(name: str) -> dict:
    return json.loads((P1 / name / "case.json").read_text(encoding="utf-8"))


def _put(sessions: Path, case: dict) -> Path:
    folder = sessions / case["session_id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "case.json").write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return folder


def _counts(store: OpsStore) -> tuple:
    report = build_report(store)
    return (
        [(r.key, r.value.count) for r in (*report.funnel.stages, *report.funnel.exits)],
        [(r.tier, r.value.count) for r in report.tiers],
        [(f.rule_id, f.flagged.count) for f in report.findings],
    )


def test_every_dialogue_outcome_has_an_attempt_outcome() -> None:
    assert set(FROM_DIALOGUE) == {o.value for o in Outcome} | {"in_progress"}
    assert FROM_DIALOGUE["call_back_later"] is AttemptOutcome.call_back_later
    assert FROM_DIALOGUE["language_switch"] is AttemptOutcome.language_switch
    assert FROM_DIALOGUE["human_requested"] is AttemptOutcome.incomplete
    assert FROM_DIALOGUE["in_progress"] is AttemptOutcome.incomplete


def test_the_p1_calls_are_outside_the_sample_listed_and_never_counted(
    store: OpsStore, tmp_path: Path
) -> None:
    before = _counts(store)
    sessions = tmp_path / "sessions"
    for name in CALLS:
        _put(sessions, _case(name))

    found = ingest(store, sessions, packaged_records())
    assert (len(found.linked), len(found.outside), found.skipped) == (0, 4, [])
    assert ingest(store, sessions, packaged_records()).outside == found.outside  # rerun: no change
    assert len(store.outside()) == 4

    assert _counts(store) == before  # nothing outside the sample enters the statistics
    batch = load_batch(store)
    report = build_report(store)
    assert report.outside_calls == 4 and not report.batch.simulated
    by_record = {o.call.session_id: o for o in batch.outside}
    hero, informed, run1, third = (by_record[_case(n)["session_id"]] for n in CALLS)
    assert hero.call.reason == "the loan is not on the lender's book for this batch"
    assert (hero.triage.tier, informed.triage.tier, run1.triage.tier) == ("refer", "clear", "refer")
    # The third-party call's case file says "incomplete", but a wrong party is an attempt, not a finding.
    assert (third.call.outcome, third.call.call_id, third.triage) == (AttemptOutcome.wrong_party, None, None)
    assert all(o.call.source.kind == "phone_session" for o in batch.outside)

    items = {i.case_id: i for i in queue_view(batch).items}
    outside = [i for i in items.values() if not i.in_report]
    assert {i.case_id for i in outside} == {hero.call.session_id, run1.call.session_id}
    assert all(not i.simulated and i.not_counted_because == hero.call.reason for i in outside)
    case = case_view(batch, hero.call.session_id)
    assert not case.in_report and case.call.transcript_note == PARTIAL_NOTE
    assert case.loan.borrower and case.loan.branch is None
    quoted = [line.quote for line in case.refer_lines if line.quote]
    assert quoted and all(q.start_s is not None for q in quoted)  # audio offsets from the case file


def _linked_hero(store: OpsStore, **changes) -> tuple[dict, str]:
    """The hero case file, moved onto a sampled loan whose customer was never reached."""
    batch = load_batch(store)
    target = next(s for s in batch.sampled if s.status is FinalStatus.unreachable)
    case = _case("hero")
    day = target.loan.sold_on + timedelta(days=target.attempts[-1].day_since_sale + 1)
    case |= {
        "loan_id": target.loan.record.loan_id,
        "started_at": datetime.combine(day, time(11), IST).isoformat(),
    }
    return case | changes, target.loan.record.loan_id


def test_a_phone_call_on_a_sampled_loan_enters_the_funnel_queue_and_report_as_a_phone_call(
    state: Path, store: OpsStore
) -> None:
    case, loan_id = _linked_hero(store)
    folder = _put(state / "sessions", case)
    (folder / "call.wav").write_bytes(b"RIFF")  # the case page offers the recording when it exists
    before = build_report(store)

    found = ingest(store, state / "sessions", packaged_records())
    assert found.linked == [case["session_id"]]
    batch = load_batch(store)
    (linked,) = (s for s in batch.sampled if s.loan.record.loan_id == loan_id)
    assert linked.status is FinalStatus.completed and linked.attempts[-1].source.kind == "phone_session"
    assert linked.attempts[-1].dialogue_outcome == "completed"

    after = build_report(store)
    assert after.funnel.stages[-1].value.count == before.funnel.stages[-1].value.count + 1
    assert after.batch.referred == before.batch.referred + 1
    assert any(r.key.startswith("Phone call") for r in after.reading)

    client = TestClient(create_app(gnani=FakeSpeech(), state=state, web_dir=None, clips_dir=None))
    queue = QueueView.model_validate(client.get("/api/review/queue").json())
    item = next(i for i in queue.items if i.case_id == case["session_id"])
    assert item.in_report and not item.simulated
    page = CaseView.model_validate(client.get(f"/api/review/cases/{case['session_id']}").json())
    assert page.call.recording_url == f"/api/sessions/{case['session_id']}/recording.wav"
    assert not page.call.simulated and page.call.day_since_sale == linked.attempts[-1].day_since_sale
    log = AttemptLogView.model_validate(client.get("/api/review/attempts").json())
    logged = next(loan for loan in log.loans if loan.loan_id == loan_id)
    assert (logged.attempts[-1].session_id, logged.attempts[-1].simulated) == (case["session_id"], False)


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({"status": "failed", "failed": ["extract"]}, FinalStatus.completed_not_analysed),
        ({"call_outcome": "call_back_later"}, FinalStatus.call_back_later),
        ({"call_outcome": "language_switch"}, FinalStatus.language_switch),
        ({"call_outcome": "declined"}, FinalStatus.declined),
        ({"call_outcome": "human_requested"}, FinalStatus.incomplete),
        ({"call_outcome": "in_progress"}, FinalStatus.incomplete),
    ],
)
def test_a_session_that_did_not_yield_an_analysed_call_is_an_attempt_with_no_finding(
    state: Path, store: OpsStore, changes: dict, status: FinalStatus
) -> None:
    case, loan_id = _linked_hero(store, **changes)
    _put(state / "sessions", case)
    tiers_before = [(r.tier, r.value.count) for r in build_report(store).tiers]
    ingest(store, state / "sessions", packaged_records())
    (linked,) = (s for s in load_batch(store).sampled if s.loan.record.loan_id == loan_id)
    assert linked.status is status and linked.call is None
    assert [(r.tier, r.value.count) for r in build_report(store).tiers] == tiers_before


def test_a_running_case_or_an_unknown_record_is_skipped(store: OpsStore, tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    _put(sessions, _case("hero") | {"status": "running"})
    _put(sessions, _case("informed") | {"record_id": "nobody", "loan_id": "LN-NOBODY"})
    found = ingest(store, sessions, packaged_records())
    assert (found.linked, found.outside) == ([], [])
    assert sorted(why for _, why in found.skipped) == [
        "case file still running",
        "record 'nobody' is neither on the book nor a phone record",
    ]
    shutil.rmtree(sessions)
    assert ingest(store, sessions, packaged_records()).skipped == []
