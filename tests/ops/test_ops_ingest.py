"""Phone-session ingest on hand-built batches: the rules in samajh/ops/sessions.py's docstring."""

from __future__ import annotations

import itertools
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from opskit import (
    COMPLETED,
    DECLINED_AFTER_CHECKS,
    NO_ANSWER,
    SOLD,
    WALL,
    assert_each_call_named_once,
    coached,
    customer,
    loan,
    open_batch,
    phone_case,
    put_case,
    run_batch,
    snapshot,
)

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.chain import india_day
from samajh.ops.model import MAX_ATTEMPTS, AttemptOutcome, CallRecord, FinalStatus, OutsideCall
from samajh.ops.report import build_report
from samajh.ops.sessions import NO_BOOK_BLOCK, NOT_DRAWN, NOT_ON_BOOK, ingest
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, batch_view
from samajh.types import Tier

DRAWN_ON = SOLD + timedelta(days=3)


def nothing(record_id: str):
    """A packaged-record lookup that knows no record: the book's loans must not need it."""
    return


def _sampled(store: OpsStore, loan_id: str):
    return next(s for s in load_batch(store).sampled if s.drawn.loan_id == loan_id)


def _every_folder_once(found, sessions: Path) -> None:
    ids = found.linked + found.outside + [sid for sid, _ in found.skipped]
    assert sorted(ids) == sorted(p.name for p in sessions.iterdir() if p.is_dir())


def _reasons(found) -> dict[str, str]:
    return dict(found.skipped)


# --- 1. ingest never stops --------------------------------------------------------------------------


def test_no_session_folder_stops_ingest_and_each_ends_in_one_place_with_a_reason(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"

    def folder(name: str) -> Path:
        (sessions / name).mkdir(parents=True)
        return sessions / name

    folder("20261110T050000-000000000a01")  # nothing in it
    (folder("20261110T050000-000000000a02") / "session.json").write_text(
        json.dumps({"status": "active", "dialogue": "stub"})
    )
    (folder("20261110T050000-000000000a03") / "session.json").write_text(
        json.dumps({"status": "ended", "ended_reason": "hangup", "dialogue": "samajh"})
    )
    (folder("20261110T050000-000000000a04") / "case.json").write_text("{not json")
    (folder("20261110T050000-000000000a05") / "case.json").write_text(json.dumps({"session_id": "x"}))
    unknown = phone_case(store, a, None, DRAWN_ON, "hung_up_by_aliens", sid="20261110T050000-000000000a06")
    put_case(sessions, unknown)
    broken = phone_case(store, a, customer(a), DRAWN_ON, sid="20261110T050000-000000000a07")
    broken["transcript"] = {"call_id": broken["session_id"], "turns": "not a list"}
    put_case(sessions, broken)
    folder("not-a-session")
    (sessions / "stray-file.txt").write_text("x")  # a file, not a session folder: not looked at

    found = ingest(store, sessions, nothing)
    _every_folder_once(found, sessions)
    why = _reasons(found)
    assert (found.linked, found.outside) == ([], [])
    assert why["20261110T050000-000000000a01"].startswith("no case file (case.json)")
    assert (
        "still active" in why["20261110T050000-000000000a02"]
        and "stub" in why["20261110T050000-000000000a02"]
    )
    assert "ended (hangup) but no case was built" in why["20261110T050000-000000000a03"]
    assert why["20261110T050000-000000000a04"].startswith("case file could not be read")
    assert why["20261110T050000-000000000a05"].startswith("case file could not be read")
    assert "'hung_up_by_aliens' has no attempt outcome" in why["20261110T050000-000000000a06"]
    # A malformed transcript is caught where the case file is parsed, before any rule runs.
    assert why["20261110T050000-000000000a07"].startswith("case file could not be read: transcript")
    assert why["not-a-session"] == "not a session id"
    assert store.attempts() == () and store.outside() == ()
    assert_each_call_named_once(store)

    summary = store.ingest_summary()
    assert summary is not None and summary.sessions == 8 and len(summary.skipped) == 8
    log = attempt_log_view(load_batch(store))
    assert len(log.not_ingested) == 8 and "did not bring in 8" in log.ingest_note
    report = build_report(store)
    assert report.phone_sessions_not_ingested == 8 and "did not bring in 8" in report.ingest_note


# --- 2. do_not_call and written_requested ---------------------------------------------------------


@pytest.mark.parametrize("outcome", ["do_not_call", "written_requested"])
def test_a_do_not_call_or_written_request_ends_the_chain_and_has_its_own_count(
    tmp_path: Path, outcome: str
) -> None:
    a, b = loan(1), loan(2)
    store, draw = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    first = phone_case(store, a, None, DRAWN_ON, outcome)
    later = phone_case(store, a, customer(a), DRAWN_ON + timedelta(days=1), started=WALL + timedelta(hours=1))
    put_case(sessions, first)
    put_case(sessions, later)

    found = ingest(store, sessions, nothing)
    assert found.linked == [first["session_id"]]
    assert "attempts had already ended" in _reasons(found)[later["session_id"]]
    s = _sampled(store, a.record.loan_id)
    assert s.status is FinalStatus(outcome) and s.call is None
    exits = {row.key: row.value.count for row in build_report(store).funnel.exits}
    assert exits[outcome] == 1
    (row,) = (x for x in attempt_log_view(load_batch(store)).loans if x.loan_id == a.record.loan_id)
    assert row.status_label == wording.STATUS_LABEL[FinalStatus(outcome)]

    run_draw(
        store,
        draw,
        {a.record.loan_id: customer(a, COMPLETED), b.record.loan_id: customer(b, COMPLETED)},
        scripted_analysis,
    )
    assert [x.outcome for x in _sampled(store, a.record.loan_id).attempts] == [AttemptOutcome(outcome)]


# --- 3. a failed case file that is rebuilt ---------------------------------------------------------


def test_a_failed_case_rebuilt_to_ready_becomes_the_counted_call_with_an_explicit_supersede(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2), status="failed")
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    assert _sampled(store, a.record.loan_id).status is FinalStatus.completed_not_analysed
    assert_each_call_named_once(store)

    put_case(sessions, case | {"status": "ready"})
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    s = _sampled(store, a.record.loan_id)
    assert s.status is FinalStatus.completed and s.counted and s.triage.tier is Tier.refer
    (effective,) = store.attempts()
    assert effective.supersedes is AttemptOutcome.completed_not_analysed and effective.number == 1
    lines = (store.root / "attempts.jsonl").read_text().splitlines()
    assert [json.loads(line)["outcome"] for line in lines] == ["completed_not_analysed", "completed"]
    assert_each_call_named_once(store)

    before = snapshot(store.root)
    assert ingest(store, sessions, nothing).linked == [case["session_id"]]
    assert snapshot(store.root) == before  # idempotent after the supersede


def test_a_run_interrupted_between_saving_the_call_and_logging_it_converges(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2), status="failed")
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    put_case(sessions, case | {"status": "ready"})

    real = store.add_attempt

    def crash(attempt) -> None:
        raise KeyboardInterrupt  # the process dies after the call file is written

    store.add_attempt = crash
    with pytest.raises(KeyboardInterrupt):
        ingest(store, sessions, nothing)
    store.add_attempt = real
    assert (store.root / "calls" / f"{case['session_id']}.json").exists()  # orphan for now

    # The case file changes again before the next run: the orphan must not survive a skip either.
    put_case(sessions, case | {"status": "ready", "language": "hi-en"})
    found = ingest(OpsStore(store.root), sessions, nothing)
    assert found.skipped == [] and "differs" in found.changed[0][1]
    assert_each_call_named_once(store)

    put_case(sessions, case | {"status": "ready"})
    ingest(OpsStore(store.root), sessions, nothing)
    assert _sampled(store, a.record.loan_id).counted
    assert_each_call_named_once(store)


@pytest.mark.parametrize(
    "change",
    [{"language": "hi-en"}, {"call_outcome": "declined"}, {"status": "failed"}],
    ids=["language", "outcome", "ready-to-failed"],
)
def test_any_other_change_to_an_ingested_case_file_is_listed_as_changed_and_changes_nothing(
    tmp_path: Path, change: dict
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2))
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    before, report = snapshot(store.root), build_report(store)

    put_case(sessions, case | change)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    assert "differs from what was brought in" in found.changed[0][1]
    assert {k: v for k, v in snapshot(store.root).items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }
    assert build_report(store).tiers == report.tiers
    assert_each_call_named_once(store)


def test_an_outside_call_rebuilt_to_ready_is_superseded_too(tmp_path: Path) -> None:
    a, late = loan(1), loan(2, SOLD + timedelta(days=20))  # sold after the draw: not drawn
    store, _ = open_batch(tmp_path / "ops", [a, late], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, late, coached(late), None, status="failed")
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    assert store.outside()[0].outcome is AttemptOutcome.completed_not_analysed
    put_case(sessions, case | {"status": "ready"})
    ingest(store, sessions, nothing)
    (o,) = load_batch(store).outside
    assert o.call.outcome is AttemptOutcome.completed and o.triage.tier is Tier.refer
    assert o.call.supersedes is AttemptOutcome.completed_not_analysed
    assert_each_call_named_once(store)


# --- 4. idempotent ------------------------------------------------------------------------------


def test_a_second_ingest_changes_no_file_and_no_number(tmp_path: Path) -> None:
    a, b, c = loan(1), loan(2), loan(3, SOLD + timedelta(days=20))
    store, _ = open_batch(tmp_path / "ops", [a, b, c], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, coached(a), DRAWN_ON))
    put_case(
        sessions, phone_case(store, b, None, DRAWN_ON, "no_response", started=WALL + timedelta(minutes=5))
    )
    put_case(sessions, phone_case(store, c, customer(c), None))
    put_case(sessions, phone_case(store, a, None, DRAWN_ON, "running", status="running"))
    (sessions / "20261110T000000-00000000dead").mkdir()
    first = ingest(store, sessions, nothing)
    before, report = snapshot(store.root), build_report(store)
    second = ingest(store, sessions, nothing)
    assert (second.linked, second.outside, second.skipped) == (first.linked, first.outside, first.skipped)
    assert snapshot(store.root) == before and build_report(store) == report


# --- 5. not drawn is outside, from the book's record ---------------------------------------------


@pytest.mark.parametrize("with_book_block", [False, True])
def test_a_loan_on_the_book_that_was_not_drawn_is_outside_with_the_books_record(
    tmp_path: Path, with_book_block: bool
) -> None:
    a, late = loan(1), loan(2, SOLD + timedelta(days=20))
    store, _ = open_batch(tmp_path / "ops", [a, late], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(
        store, late, coached(late), late.sold_on + timedelta(days=2) if with_book_block else None
    )
    put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.outside == [case["session_id"]] and found.skipped == []
    (o,) = load_batch(store).outside
    assert o.call.reason == NOT_DRAWN == "the loan was not drawn in this batch"
    assert o.call.record == late.record and o.triage is not None
    assert build_report(store).tiers[0].value.n == 0  # never counted


def test_a_drawn_loan_called_without_a_book_block_is_outside_and_a_packaged_record_is_outside(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    drawn = phone_case(store, a, coached(a), None)
    packaged = phone_case(store, a, None, None, "wrong_party", record_id="hero", loan_id="LN-DEMO-0001")
    stranger = phone_case(store, a, None, None, "wrong_party", record_id="nobody", loan_id="LN-NOBODY")
    for case in (drawn, packaged, stranger):
        put_case(sessions, case)
    found = ingest(store, sessions, lambda rid: a.record if rid == "hero" else None)
    reasons = {o.session_id: o.reason for o in store.outside()}
    assert reasons == {drawn["session_id"]: NO_BOOK_BLOCK, packaged["session_id"]: NOT_ON_BOOK}
    assert _reasons(found) == {
        stranger["session_id"]: "record 'nobody' is neither on the book nor a phone record"
    }
    assert store.attempts() == () and _sampled(store, a.record.loan_id).status is FinalStatus.not_attempted


# --- 6. order and numbering ------------------------------------------------------------------------


def test_sessions_are_taken_in_wall_clock_order_whatever_the_folder_names(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    # Created before either was ingested, on the same call date; the earlier one has the later name.
    early = phone_case(
        store, a, None, DRAWN_ON, "no_response", started=WALL, sid="20261110T090000-000000000b02"
    )
    late = phone_case(
        store,
        a,
        coached(a),
        DRAWN_ON,
        started=WALL + timedelta(minutes=7),
        sid="20261110T010000-000000000b01",
    )
    put_case(sessions, early)
    put_case(sessions, late)
    found = ingest(store, sessions, nothing)
    assert found.linked == [early["session_id"], late["session_id"]]
    attempts = _sampled(store, a.record.loan_id).attempts
    assert [(x.number, x.outcome) for x in attempts] == [
        (1, AttemptOutcome.no_answer),
        (2, AttemptOutcome.completed),
    ]
    assert attempts[0].at < attempts[1].at


def test_a_phone_call_after_a_simulated_completion_is_skipped_and_the_call_stays_counted(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [coached(a, NO_ANSWER, COMPLETED)], DRAWN_ON)
    sessions = tmp_path / "sessions"
    after = phone_case(store, a, None, DRAWN_ON + timedelta(days=5), "no_response")
    put_case(sessions, after)
    found = ingest(store, sessions, nothing)
    assert "attempts had already ended" in _reasons(found)[after["session_id"]]
    s = _sampled(store, a.record.loan_id)
    assert s.status is FinalStatus.completed and s.counted and len(s.attempts) == 2


def test_a_phone_call_dated_before_the_last_logged_attempt_is_skipped(tmp_path: Path) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [customer(a, NO_ANSWER, NO_ANSWER)], DRAWN_ON)
    sessions = tmp_path / "sessions"
    # The simulated attempts are on DRAWN_ON and the day after, at 11:00 India time.
    before_last = phone_case(store, a, None, DRAWN_ON, "no_response")
    put_case(sessions, before_last)
    found = ingest(store, sessions, nothing)
    assert "not after the loan's last logged attempt" in _reasons(found)[before_last["session_id"]]
    assert [x.number for x in _sampled(store, a.record.loan_id).attempts] == [1, 2]


def test_the_simulator_continues_a_chain_that_a_phone_attempt_started(tmp_path: Path) -> None:
    a, b, c, d = loan(1), loan(2), loan(3), loan(4, SOLD - timedelta(days=24))
    store, draw = open_batch(tmp_path / "ops", [a, b, c, d], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, None, DRAWN_ON + timedelta(days=4), "no_response"))
    put_case(sessions, phone_case(store, b, None, DRAWN_ON, "declined"))
    put_case(sessions, phone_case(store, c, None, DRAWN_ON, "no_response"))
    put_case(sessions, phone_case(store, d, None, DRAWN_ON, "no_response"))  # day 27 from the sale
    assert len(ingest(store, sessions, nothing).linked) == 4

    script = (NO_ANSWER, NO_ANSWER, COMPLETED)
    customers = {x.record.loan_id: customer(x, *script) for x in (a, b, c, d)}
    run_draw(store, draw, customers, scripted_analysis, max_attempts=3)
    first = snapshot(store.root)
    run_draw(store, draw, customers, scripted_analysis, max_attempts=3)
    assert snapshot(store.root) == first  # a second run changes nothing

    for x in (a, b, c, d):
        attempts = _sampled(store, x.record.loan_id).attempts
        assert [y.number for y in attempts] == list(range(1, len(attempts) + 1))
        assert all(p.at < q.at for p, q in itertools.pairwise(attempts))
        assert all(y.day_since_sale <= 30 for y in attempts)
    days = lambda x: [(y.day_since_sale, y.source.kind) for y in _sampled(store, x.record.loan_id).attempts]
    # a: the phone attempt on day 7 comes first; the simulated ones follow on the next days, and the
    # limit of 3 counts the phone attempt, so the script's third step is never played.
    assert days(a) == [(7, "phone_session"), (8, "simulated"), (9, "simulated")]
    assert _sampled(store, a.record.loan_id).status is FinalStatus.unreachable
    assert days(b) == [(3, "phone_session")]  # declined ends the chain
    assert days(c) == [(3, "phone_session"), (4, "simulated"), (5, "simulated")]
    assert days(d) == [(27, "phone_session"), (28, "simulated"), (29, "simulated")]


def test_the_simulator_stops_at_day_30_counting_a_phone_attempt(tmp_path: Path) -> None:
    d = loan(1, SOLD - timedelta(days=26))
    store, draw = open_batch(tmp_path / "ops", [d], DRAWN_ON)  # day 29 at the draw
    put_case(
        tmp_path / "s", phone_case(store, d, None, DRAWN_ON + timedelta(days=1), "no_response")
    )  # day 30
    ingest(store, tmp_path / "s", nothing)
    run_draw(store, draw, {d.record.loan_id: customer(d, COMPLETED)}, scripted_analysis)
    s = _sampled(store, d.record.loan_id)
    assert [y.day_since_sale for y in s.attempts] == [30] and s.status is FinalStatus.not_reached_in_time


# --- 7. dates and the book block ----------------------------------------------------------------


def test_a_call_dated_before_the_sale_or_the_draw_or_with_a_book_block_that_does_not_match_is_skipped(
    tmp_path: Path,
) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    cases = {
        "before the sale": phone_case(store, a, coached(a), SOLD - timedelta(days=3)),
        "before the loan's draw": phone_case(store, a, coached(a), DRAWN_ON - timedelta(days=1)),
        "day since the sale": phone_case(store, a, coached(a), DRAWN_ON)
        | {"book": {**phone_case(store, a, None, DRAWN_ON)["book"], "day_since_sale": 9}},
        "sale date": phone_case(store, a, coached(a), DRAWN_ON)
        | {"book": {**phone_case(store, a, None, DRAWN_ON)["book"], "sold_on": "2027-01-01"}},
        "names batch": phone_case(store, a, coached(a), DRAWN_ON)
        | {"book": {**phone_case(store, a, None, DRAWN_ON)["book"], "batch_id": "B-2027H1-otherbook"}},
        "names draw": phone_case(store, a, coached(a), DRAWN_ON)
        | {"book": {**phone_case(store, a, None, DRAWN_ON)["book"], "draw_id": "D-2027-01-01"}},
        "not on this batch's book": phone_case(store, b, None, DRAWN_ON, "no_response")
        | {"loan_id": "SYN-GL-270111-9999", "record_id": "SYN-GL-270111-9999"},
        "record id": phone_case(store, b, None, DRAWN_ON, "no_response") | {"record_id": "hero"},
    }
    for case in cases.values():
        put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [] and found.outside == []
    why = _reasons(found)
    for words, case in cases.items():
        assert words in why[case["session_id"]], (words, why[case["session_id"]])
    assert store.attempts() == ()
    report = build_report(store)
    assert report.timing.first_attempt_days is None


def test_no_negative_day_appears_in_the_report(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    put_case(tmp_path / "s", phone_case(store, a, coached(a), SOLD - timedelta(days=3)))
    ingest(store, tmp_path / "s", nothing)
    text = build_report(store).model_dump_json() + attempt_log_view(load_batch(store)).model_dump_json()
    assert '"day_since_sale":-' not in text and 'first_attempt_days":[-' not in text


# --- 8. the 30-day window binds a phone attempt in the counting ----------------------------------


def test_a_phone_call_after_day_30_is_logged_shown_and_not_counted_and_the_report_says_so(
    tmp_path: Path,
) -> None:
    a, b = loan(1), loan(2)
    store = run_batch(tmp_path / "ops", [a, b], [customer(a, NO_ANSWER), coached(b, COMPLETED)], DRAWN_ON)
    assert build_report(store).timing.note == "No attempt was made after day 30 from the sale."
    sessions = tmp_path / "sessions"
    late = phone_case(store, a, coached(a), SOLD + timedelta(days=31))
    put_case(sessions, late)
    assert ingest(store, sessions, nothing).linked == [late["session_id"]]
    s = _sampled(store, a.record.loan_id)
    assert s.status is FinalStatus.completed_late and not s.counted and s.attempts[-1].day_since_sale == 31
    report = build_report(store)
    assert {r.tier: r.value.n for r in report.tiers}[Tier.refer] == 1  # only b
    assert report.timing.attempts_after_window.count == 1 and report.timing.phone_attempts_after_window == 1
    assert "1 of 3 attempts were made after day 30" in report.timing.note
    assert "phone call" in report.timing.note and "none" not in report.timing.note.lower().split(",")[0]
    assert report.timing.note == attempt_log_view(load_batch(store)).window_note


def test_the_attempt_day_is_the_call_date_at_the_india_time_of_day_of_the_session(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    call_date = DRAWN_ON + timedelta(days=2)
    # 20:00 UTC on the wall clock is 01:30 the next day in India; the book's day is the call date.
    case = phone_case(
        store, a, None, call_date, "no_response", started=datetime(2026, 11, 10, 20, 0, tzinfo=UTC)
    )
    put_case(tmp_path / "s", case)
    ingest(store, tmp_path / "s", nothing)
    (attempt,) = store.attempts()
    assert india_day(attempt.at) == call_date and attempt.day_since_sale == (call_date - a.sold_on).days
    assert (attempt.at.hour, attempt.at.minute) == (1, 30)


# --- 9. the funnel counts a phone attempt as a simulated one -------------------------------------


@pytest.mark.parametrize(
    ("step", "outcome"),
    [(NO_ANSWER, "no_response"), (COMPLETED, "completed"), (DECLINED_AFTER_CHECKS, "declined")],
)
def test_a_phone_attempt_counts_in_the_funnel_as_the_same_simulated_attempt(
    tmp_path: Path, step, outcome
) -> None:
    a = loan(1)
    simulated = run_batch(tmp_path / "sim", [a], [coached(a, step)], DRAWN_ON)
    phone, _ = open_batch(tmp_path / "phone", [a], DRAWN_ON)
    case = phone_case(phone, a, coached(a), DRAWN_ON, outcome)
    if outcome == "declined":  # the transcript shows the identity checks passed
        case["transcript"] = phone_case(phone, a, coached(a), DRAWN_ON)["transcript"]
    put_case(tmp_path / "s", case)
    ingest(phone, tmp_path / "s", nothing)
    funnel = lambda store: [
        (r.key, r.value.count)
        for r in (*build_report(store).funnel.stages, *build_report(store).funnel.exits)
    ]
    assert funnel(phone) == funnel(simulated)


# --- 10. the phone-call note is read from the case files ------------------------------------------


def test_the_phone_note_counts_where_the_customer_audio_came_from(tmp_path: Path) -> None:
    loans = [loan(n) for n in range(1, 7)]
    store, _ = open_batch(tmp_path / "ops", loans, DRAWN_ON)
    sessions = tmp_path / "sessions"
    audios = [
        {"mic": 5, "file": 0, "none": 0},
        {"mic": 0, "file": 4, "none": 1},
        {"mic": 2, "file": 3, "none": 0},
        {"mic": 0, "file": 0, "none": 2},
        None,  # a case file written before customer_audio existed
    ]
    for x, audio in zip(loans, audios, strict=False):
        put_case(sessions, phone_case(store, x, None, DRAWN_ON, "no_response", audio=audio))
    put_case(sessions, phone_case(store, loans[5], None, None, "no_response", audio=audios[0]))  # outside
    ingest(store, sessions, nothing)
    report, batch = build_report(store), batch_view(load_batch(store))
    note = batch.phone_note
    assert note in report.limits
    assert (
        "6 phone session(s), 2 with customer audio from the microphone only, 1 from prepared audio files only, "
        "1 from both, 1 with no customer audio, 1 where it is not recorded, or not readable, in the case file"
    ) in note
    assert "synthetic voices" not in " ".join(report.limits)
    assert "real customer of a lender" in note  # and never that microphone audio is one
    assert store.attempts()[0].source.customer_audio.mic == 5
    assert store.outside()[0].source.customer_audio.mic == 5


def test_a_batch_with_no_phone_call_has_no_phone_note(tmp_path: Path) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [customer(a, COMPLETED)], DRAWN_ON)
    assert batch_view(load_batch(store)).phone_note is None and build_report(store).limits == wording.LIMITS


# --- 11 and 12. the summary is kept, and the new words are clean ---------------------------------


def test_the_last_ingest_is_kept_and_the_pages_say_how_many_sessions_were_left_out(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    assert store.ingest_summary() is None and build_report(store).phone_sessions_not_ingested is None
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, None, DRAWN_ON, "no_response"))
    (sessions / "20261110T000000-00000000beef").mkdir()
    ingest(store, sessions, nothing)
    summary = store.ingest_summary()
    assert (len(summary.linked), len(summary.outside), len(summary.skipped)) == (1, 0, 1)
    assert summary.skipped[0].reason.startswith("no case file")
    log = attempt_log_view(load_batch(store))
    assert [v.session_id for v in log.not_ingested] == ["20261110T000000-00000000beef"]
    assert "not even the reach figures" in log.ingest_note


def test_the_new_words_hold_no_banned_term_and_never_say_finding() -> None:
    from samajh.ops.model import IngestSummary, PhoneSession, SkippedSession

    texts = [
        wording.phone_note([PhoneSession(session_id="20261110T000000-000000000001")]),
        wording.window_note(2, 2, 10),
        wording.window_note(0, 0, 10),
        wording.ingest_note(None),
        wording.ingest_note(
            IngestSummary(linked=("a",), outside=(), skipped=(SkippedSession(session_id="b", reason="x"),))
        ),
        NOT_DRAWN,
        NOT_ON_BOOK,
        NO_BOOK_BLOCK,
        *(wording.OUTCOME_LABEL[o] for o in (AttemptOutcome.do_not_call, AttemptOutcome.written_requested)),
        *(wording.STATUS_LABEL[s] for s in (FinalStatus.do_not_call, FinalStatus.written_requested)),
    ]
    for text in texts:
        assert not wording.banned_in(text) and "finding" not in text.lower(), text


def test_models_used_by_the_phone_server_keep_their_names() -> None:
    """samajh/server/loanbook.py reads these; keep them."""
    from samajh.ops.model import RETRY_AFTER, WINDOW_DAYS, Attempt, BookLoan, Draw  # noqa: F401

    assert {"number", "at", "outcome", "loan_id"} <= set(Attempt.model_fields)
    assert {"as_of", "draw_id", "drawn"} <= set(Draw.model_fields)
    assert CallRecord and OutsideCall and date


def test_a_phone_attempt_ingested_while_the_simulator_analyses_is_not_overwritten(tmp_path: Path) -> None:
    a = loan(1)
    store, draw = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, phone_case(store, a, None, DRAWN_ON + timedelta(days=5), "declined"))

    def analyse_while_a_session_arrives(call, record):
        ingest(store, sessions, nothing)
        return scripted_analysis(call, record)

    with pytest.raises(RuntimeError, match="gained an attempt meanwhile"):
        run_draw(store, draw, {a.record.loan_id: customer(a, COMPLETED)}, analyse_while_a_session_arrives)
    assert [(x.number, x.source.kind) for x in store.attempts()] == [(1, "phone_session")]
    run_draw(
        store, draw, {a.record.loan_id: customer(a, COMPLETED)}, scripted_analysis
    )  # declined: nothing more
    assert len(store.attempts()) == 1


def test_a_phone_call_at_20_utc_on_day_30_is_on_the_call_date_in_india_and_ends_the_window(
    tmp_path: Path,
) -> None:
    """Every place that turns a time into a day uses India time. A session started at 20:00 UTC is
    01:30 the next day in India: the attempt is dated the call date (day 30) at 01:30 India time,
    the report's clock is that date, and the simulator's next attempt would be day 31, so none is
    made. In UTC the attempt would sit on day 29 and the simulator would call again on day 30."""
    a = loan(1)
    store, draw = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    day_30 = a.sold_on + timedelta(days=30)
    late_evening_utc = datetime(2026, 11, 10, 20, 0, tzinfo=UTC)
    put_case(tmp_path / "s", phone_case(store, a, None, day_30, "no_response", started=late_evening_utc))
    ingest(store, tmp_path / "s", nothing)
    (phone,) = store.attempts()
    assert phone.day_since_sale == 30 and phone.outcome is AttemptOutcome.no_answer
    assert phone.at.astimezone(UTC).date() == day_30 - timedelta(days=1)  # the UTC date is day 29
    assert india_day(phone.at) == day_30
    assert build_report(store).as_of == day_30

    run_draw(store, draw, {a.record.loan_id: customer(a, NO_ANSWER, COMPLETED, COMPLETED)}, scripted_analysis)
    assert [x.source.kind for x in store.attempts()] == [
        "phone_session"
    ]  # nothing on day 31, or day 30 again
    assert _sampled(store, a.record.loan_id).status is FinalStatus.not_reached_in_time


def test_the_simulator_calls_again_the_india_day_after_a_late_evening_phone_attempt(tmp_path: Path) -> None:
    a = loan(1)
    store, draw = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    call_date = DRAWN_ON + timedelta(days=5)
    put_case(
        tmp_path / "s",
        phone_case(
            store, a, None, call_date, "no_response", started=datetime(2026, 11, 10, 20, 0, tzinfo=UTC)
        ),
    )
    ingest(store, tmp_path / "s", nothing)
    run_draw(store, draw, {a.record.loan_id: customer(a, COMPLETED)}, scripted_analysis)
    phone, simulated = store.attempts()
    assert india_day(simulated.at) == call_date + timedelta(days=1)
    assert simulated.day_since_sale == phone.day_since_sale + 1


# --- the attempt limit, shared with the simulator and the phone server ------------------------------


def _unanswered(store: OpsStore, of, day: int, hour: int, outcome: str = "no_response", **kw) -> dict:
    """A phone session on `of` dated `day` days after the draw, started `hour` hours after WALL."""
    return phone_case(
        store,
        of,
        kw.pop("who", None),
        DRAWN_ON + timedelta(days=day),
        outcome,
        started=WALL + timedelta(hours=hour),
        **kw,
    )


def test_the_simulators_default_limit_is_the_named_constant() -> None:
    import inspect

    assert MAX_ATTEMPTS == 3
    assert inspect.signature(run_draw).parameters["max_attempts"].default == MAX_ATTEMPTS


def test_three_phone_attempts_are_taken_in_and_a_fourth_is_skipped_with_the_reason(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    cases = [_unanswered(store, a, k, k) for k in range(MAX_ATTEMPTS + 1)]
    for case in cases:
        put_case(sessions, case)

    found = ingest(store, sessions, nothing)
    assert found.linked == [c["session_id"] for c in cases[:MAX_ATTEMPTS]]
    why = _reasons(found)[cases[-1]["session_id"]]
    assert f"already has {MAX_ATTEMPTS} logged attempts" in why and wording.banned_in(why) == []
    assert [x.number for x in _sampled(store, a.record.loan_id).attempts] == [1, 2, 3]

    # Running it again: the third attempt is still recognised as brought in, nothing changes.
    before = snapshot(store.root)
    again = ingest(store, sessions, nothing)
    assert again.linked == found.linked and again.skipped == found.skipped
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }


def test_simulated_and_phone_attempts_count_together(tmp_path: Path) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [customer(a, NO_ANSWER, NO_ANSWER)], DRAWN_ON)
    assert [x.source.kind for x in _sampled(store, a.record.loan_id).attempts] == ["simulated"] * 2
    sessions = tmp_path / "sessions"
    third, fourth = _unanswered(store, a, 3, 0), _unanswered(store, a, 4, 1)
    put_case(sessions, third)
    put_case(sessions, fourth)

    found = ingest(store, sessions, nothing)
    assert found.linked == [third["session_id"]]
    assert f"already has {MAX_ATTEMPTS} logged attempts" in _reasons(found)[fourth["session_id"]]
    attempts = _sampled(store, a.record.loan_id).attempts
    assert [(x.number, x.source.kind) for x in attempts] == [
        (1, "simulated"),
        (2, "simulated"),
        (3, "phone_session"),
    ]


def test_a_superseded_attempt_and_its_replacement_count_once(tmp_path: Path) -> None:
    """Two unanswered calls, then a third whose case file failed and was rebuilt: the rebuilt one
    supersedes the third attempt (four log lines, three attempts) and is not refused as a fourth."""
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    first, second = _unanswered(store, a, 0, 0), _unanswered(store, a, 1, 1)
    third = _unanswered(store, a, 2, 2, "completed", who=coached(a), status="failed")
    for case in (first, second, third):
        put_case(sessions, case)
    assert len(ingest(store, sessions, nothing).linked) == 3

    put_case(sessions, third | {"status": "ready"})
    found = ingest(store, sessions, nothing)
    assert found.skipped == [] and len(found.linked) == 3
    attempts = store.attempts()
    assert [x.number for x in attempts] == [1, 2, 3]
    assert attempts[-1].supersedes is AttemptOutcome.completed_not_analysed
    assert len((store.root / "attempts.jsonl").read_text().splitlines()) == 4
    assert _sampled(store, a.record.loan_id).status is FinalStatus.completed

    before = snapshot(store.root)
    assert ingest(store, sessions, nothing).skipped == []
    assert snapshot(store.root) == before


# --- the limits of a batch with phone calls say which calls are which ----------------------------


def _assert_limits_count_the_calls(
    store: OpsStore, simulated: int, phone_attempts: int, outside: int
) -> None:
    report = build_report(store)
    limits = " ".join(report.limits)
    notice = batch_view(load_batch(store)).simulated_notice
    for text in (limits, notice):
        assert "no speech was recorded or transcribed" not in text
        assert "the calls are synthetic and simulated" not in text
        assert "every call are synthetic" not in text
    assert notice == wording.MIXED_NOTICE
    assert f"{simulated} attempt(s) in this batch were simulated" in limits
    assert (
        f"{phone_attempts + outside} call(s) were phone sessions on the browser phone ({phone_attempts} "
        f"attempt(s) in the sample and {outside} call(s) outside it)"
    ) in limits


def test_the_limits_of_a_batch_with_a_phone_attempt_count_simulated_and_phone_calls(tmp_path: Path) -> None:
    a, b = loan(1), loan(2)
    store = run_batch(tmp_path / "ops", [a, b], [coached(a, COMPLETED), customer(b, NO_ANSWER)], DRAWN_ON)
    put_case(tmp_path / "s", phone_case(store, b, customer(b, COMPLETED), DRAWN_ON + timedelta(days=1)))
    assert len(ingest(store, tmp_path / "s", nothing).linked) == 1
    _assert_limits_count_the_calls(store, simulated=2, phone_attempts=1, outside=0)


def test_the_limits_of_a_batch_with_only_an_outside_phone_call_count_it(tmp_path: Path) -> None:
    a, late = loan(1), loan(2, SOLD + timedelta(days=20))
    store = run_batch(tmp_path / "ops", [a, late], [customer(a, COMPLETED)], DRAWN_ON)
    put_case(tmp_path / "s", phone_case(store, late, coached(late), None))
    assert len(ingest(store, tmp_path / "s", nothing).outside) == 1
    _assert_limits_count_the_calls(store, simulated=1, phone_attempts=0, outside=1)
