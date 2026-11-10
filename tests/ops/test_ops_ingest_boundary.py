"""Ingest at its boundary: hostile case files never stop it, a session is in exactly one place, a
case file that changed after it was brought in keeps the first version, booleans and counts are
taken only as JSON booleans and integers, and the `speaker_confirmed` rule."""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest
from opskit import (
    COMPLETED,
    SOLD,
    WALL,
    assert_each_call_named_once,
    coached,
    customer,
    loan,
    open_batch,
    phone_case,
    put_case,
    snapshot,
)

from samajh.ops import sessions as sessions_module
from samajh.ops import wording
from samajh.ops.__main__ import main
from samajh.ops.batch import load_batch
from samajh.ops.model import MAX_ATTEMPTS, AttemptOutcome, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, case_view, queue_view
from samajh.types import SaleConcern

DRAWN_ON = SOLD + timedelta(days=3)


def nothing(record_id: str):
    return


def _assert_one_place(found, sessions: Path) -> None:
    """linked, outside and skipped are disjoint and cover every folder; changed is within linked or outside."""
    linked, outside, skipped = set(found.linked), set(found.outside), {sid for sid, _ in found.skipped}
    assert len(found.linked) + len(found.outside) + len(found.skipped) == len(linked | outside | skipped)
    assert linked | outside | skipped == {p.name for p in sessions.iterdir() if p.is_dir()}
    assert {sid for sid, _ in found.changed} <= linked | outside


def _assert_skipped_in_no_count(store: OpsStore, found) -> None:
    """The page's sentence on skipped sessions is true: none of them is an attempt or an outside call."""
    in_store = {a.source.session_id for a in store.attempts() if a.source.kind == "phone_session"}
    in_store |= {o.session_id for o in store.outside()}
    assert not in_store & {sid for sid, _ in found.skipped}


# --- 1. hostile shapes ------------------------------------------------------------------------------


def _set(path: str, value):
    """A change to a case file at a dotted path ("book.call_date"); a missing parent is created."""

    def change(case: dict) -> None:
        *parents, last = path.split(".")
        node = case
        for part in parents:
            node = node.setdefault(part, {}) if isinstance(node.get(part), dict) or part not in node else node[part]
        node[last] = value

    return change


def _turns(value):
    return _set("turns", value)


HOSTILE = {
    # the verifier's four
    "models.extraction a string": _set("models", {"extraction": "gpt-6"}),
    "models.extraction a list": _set("models", {"extraction": ["gpt-6"]}),
    "started_at year 9999": _set("started_at", "9999-12-31T23:59:59+00:00"),
    "started_at year 1 at +14:00": _set("started_at", "0001-01-01T00:00:00+14:00"),
    # more of the same kind
    "models a string": _set("models", "gpt-6"),
    "models a list": _set("models", ["gpt-6"]),
    "models null": _set("models", None),
    "models.extraction.model a number": _set("models", {"extraction": {"model": 5}}),
    "started_at year 1999": _set("started_at", "1999-12-31T23:59:59+00:00"),
    "started_at year 2101": _set("started_at", "2101-01-01T00:00:00+00:00"),
    "started_at not a time": _set("started_at", "yesterday"),
    "started_at a number": _set("started_at", 1731216600),
    "started_at null": _set("started_at", None),
    "started_at naive": _set("started_at", "2026-11-10T05:30:00"),
    "book a string": _set("book", "D-2027"),
    "book a list": _set("book", []),
    "book.batch_id a number": _set("book.batch_id", 5),
    "book.day_since_sale a string": _set("book.day_since_sale", "3"),
    "book.day_since_sale a float": _set("book.day_since_sale", 3.0),
    "book.day_since_sale true": _set("book.day_since_sale", True),
    "book.call_date year 9999": _set("book.call_date", "9999-12-31"),
    "book.call_date not a date": _set("book.call_date", "soon"),
    "book.sold_on year 1": _set("book.sold_on", "0001-01-01"),
    "turns a string": _turns("not a list"),
    "turns of numbers": _turns([5]),
    "turn_id a string": _turns([{"turn_id": "1", "text": "x"}]),
    "turn_id a float": _turns([{"turn_id": 1.0, "text": "x"}]),
    "turn readings a string": _turns([{"turn_id": 1, "text": "x", "readings": "abc"}]),
    "turn reading of another role": _turns([{"turn_id": 1, "readings": [{"role": "third", "model": "x"}]}]),
    "turn reading model a number": _turns([{"turn_id": 1, "readings": [{"role": "primary", "model": 3}]}]),
    "turn reading text a number": _turns(
        [{"turn_id": 1, "readings": [{"role": "primary", "model": "p", "text": 5}]}]
    ),
    "turn start_s a string": _turns([{"turn_id": 1, "text": "x", "start_s": "1.5"}]),
    "customer_audio counts as strings": _set("customer_audio", {"mic": "3", "file": 0, "none": 0}),
    "customer_audio counts true": _set("customer_audio", {"mic": True, "file": 0, "none": 0}),
    "customer_audio negative": _set("customer_audio", {"mic": -1, "file": 0, "none": 0}),
    "customer_audio a list": _set("customer_audio", [1, 2, 3]),
    "customer_audio a float": _set("customer_audio", {"mic": 1.5, "file": 0, "none": 0}),
    "recording a string": _set("recording", "call.wav"),
    "recording.sha256 a number": _set("recording", {"sha256": 5}),
    "transcript a string": _set("transcript", "x"),
    "transcript turns a string": _set("transcript", {"turns": "x"}),
    "result null on a ready call": _set("result", None),
    "result a string": _set("result", "refer"),
    "result products a number": _set("result", {"products": 5}),
    "call_outcome a number": _set("call_outcome", 5),
    "call_outcome null": _set("call_outcome", None),
    "language unknown": _set("language", "fr"),
    "status unknown": _set("status", "done"),
    "record_id null": _set("record_id", None),
    "loan_id a number": _set("loan_id", 7),
    "session_id a number": _set("session_id", 7),
    "speaker_confirmed a string": _set("speaker_confirmed", "no"),
    "speaker_confirmed 0": _set("speaker_confirmed", 0),
    "speaker_confirmed 1": _set("speaker_confirmed", 1),
    "readings_agreed yes": _turns(
        [{"turn_id": 1, "readings": [{"role": "primary", "model": "p", "text": "x"}], "readings_agreed": "yes"}]
    ),
    "reading ok yes": _turns([{"turn_id": 1, "readings": [{"role": "primary", "model": "p", "ok": "yes"}]}]),
}
# The ones that are not malformed in any way ingest relies on: brought in, with the odd field read as
# not recorded (or, for a naive time, as UTC).
LINKED = {
    "models.extraction a string",
    "models.extraction a list",
    "models a string",
    "models a list",
    "models null",
    "models.extraction.model a number",
    "started_at naive",
    "customer_audio counts as strings",
    "customer_audio counts true",
    "customer_audio negative",
    "customer_audio a list",
    "customer_audio a float",
    "recording a string",
    "recording.sha256 a number",
    "readings_agreed yes",
    "reading ok yes",
}


@pytest.mark.parametrize("name", sorted(HOSTILE))
def test_a_hostile_case_file_never_stops_ingest_and_ends_in_one_place(tmp_path: Path, name: str) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=1))
    HOSTILE[name](case)
    folder = sessions / phone_case(store, a, None, None)["session_id"]  # a fresh, valid folder name
    folder.mkdir(parents=True)
    case_sid = folder.name
    if not isinstance(case.get("session_id"), int):
        case["session_id"] = case_sid
    (folder / "case.json").write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    good = phone_case(store, b, customer(b), DRAWN_ON, started=WALL + timedelta(hours=2))
    put_case(sessions, good)  # a sound session after it in time: the run must reach it

    found = ingest(store, sessions, nothing)
    _assert_one_place(found, sessions)
    _assert_skipped_in_no_count(store, found)
    assert good["session_id"] in found.linked
    assert_each_call_named_once(store)
    build_report(store)  # the store still reads and reports
    attempt_log_view(load_batch(store))
    if name in LINKED:
        assert case_sid in found.linked, dict(found.skipped).get(case_sid)
    else:
        assert case_sid in dict(found.skipped), name
        assert dict(found.skipped)[case_sid]


def test_the_odd_fields_of_a_linked_session_are_read_as_not_recorded(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON, audio={"mic": "3", "file": 0, "none": 0})
    case |= {"models": {"extraction": "gpt-6"}, "recording": {"sha256": 5}}
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    (attempt,) = store.attempts()
    assert attempt.source.customer_audio is None and attempt.source.recording_sha256 is None
    assert store.call(case["session_id"]).analysis == "extraction model not named in the case file"
    note = load_batch(store).phone_sessions
    assert wording.phone_note(note).endswith(
        "1 where it is not recorded, or not readable, in the case file. None of them is a call with a real "
        "customer of a lender."
    )


def test_many_hostile_case_files_together_in_one_run(tmp_path: Path) -> None:
    loans = [loan(n) for n in range(1, 4)]
    store, _ = open_batch(tmp_path / "ops", loans, DRAWN_ON)
    sessions = tmp_path / "sessions"
    for k, (name, change) in enumerate(sorted(HOSTILE.items())):
        of = loans[k % 3]
        case = phone_case(store, of, coached(of), DRAWN_ON + timedelta(days=k % 20), started=WALL + timedelta(minutes=k))
        change(case)
        sid = case["session_id"] if isinstance(case.get("session_id"), str) else f"20261110T0{k:05d}-00000000beef"
        folder = sessions / sid
        folder.mkdir(parents=True)
        (folder / "case.json").write_text(json.dumps(case), encoding="utf-8")
    (sessions / "20261110T000000-00000000aaaa").mkdir()
    (sessions / "20261110T000000-00000000aaaa" / "case.json").write_text("[1, 2]")
    (sessions / "20261110T000000-00000000aaab").mkdir()
    (sessions / "20261110T000000-00000000aaab" / "case.json").write_bytes(b"\xff\xfe not utf-8")
    found = ingest(store, sessions, nothing)
    _assert_one_place(found, sessions)
    _assert_skipped_in_no_count(store, found)
    assert_each_call_named_once(store)
    before = snapshot(store.root)
    again = ingest(store, sessions, nothing)
    assert (again.linked, again.outside, again.skipped, again.changed) == (
        found.linked,
        found.outside,
        found.skipped,
        found.changed,
    )
    assert snapshot(store.root) == before  # a second ingest changes no store file


@pytest.mark.parametrize("error", [ZeroDivisionError, AttributeError, OverflowError, RecursionError, LookupError])
def test_any_exception_while_bringing_in_one_session_is_a_skip_naming_it_with_no_partial_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: type[Exception]
) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    bad = phone_case(store, a, coached(a), DRAWN_ON)
    good = phone_case(store, b, coached(b), DRAWN_ON, started=WALL + timedelta(hours=1))
    put_case(sessions, bad)
    put_case(sessions, good)
    real = store.add_attempt

    def add_attempt(attempt) -> None:  # the call file is already saved when this runs
        if attempt.loan_id == a.record.loan_id:
            raise error("boom")
        real(attempt)

    monkeypatch.setattr(store, "add_attempt", add_attempt)
    found = ingest(store, sessions, nothing)
    why = dict(found.skipped)[bad["session_id"]]
    assert error.__name__ in why
    assert found.linked == [good["session_id"]]
    assert not (store.root / "calls" / f"{bad['session_id']}.json").exists()  # no call without its entry
    assert_each_call_named_once(store)
    _assert_one_place(found, sessions)


def test_an_exception_while_reading_one_folder_is_a_skip_naming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON)
    put_case(sessions, case)
    monkeypatch.setattr(sessions_module, "_read_case", lambda folder: (_ for _ in ()).throw(MemoryError()))
    found = ingest(store, sessions, nothing)
    assert "MemoryError" in dict(found.skipped)[case["session_id"]]


# --- 2. a session is in exactly one place; changed after it was brought in ----------------------------


@pytest.mark.parametrize(
    "change",
    [
        {"models": {"extraction": {"model": "another-model"}}},
        {"language": "hi-en"},
        {"call_outcome": "declined"},
        {"status": "failed"},
        {"started_at": "not a time"},
        {"book": {"batch_id": "B-other"}},
        "unreadable",
    ],
    ids=["another-analysis", "language", "outcome", "ready-to-failed", "malformed", "book", "unreadable"],
)
def test_a_linked_session_whose_case_file_changes_stays_linked_and_counted_and_is_listed_as_changed(
    tmp_path: Path, change, capsys: pytest.CaptureFixture[str]
) -> None:
    a = loan(1)
    state = tmp_path / "state"
    store, _ = open_batch(state / "ops", [a], DRAWN_ON)
    sessions = state / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=2))
    folder = put_case(sessions, case)
    ingest(store, sessions, nothing)
    report = build_report(store)
    before = snapshot(store.root)

    if change == "unreadable":
        (folder / "case.json").write_text("{not json")
    elif "book" in change:
        put_case(sessions, case | {"book": case["book"] | change["book"]})
    else:
        put_case(sessions, case | change)
    found = ingest(store, sessions, nothing)
    sid = case["session_id"]
    assert found.linked == [sid] and found.skipped == [] and [s for s, _ in found.changed] == [sid]
    _assert_one_place(found, sessions)
    assert {k: v for k, v in snapshot(store.root).items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }
    after = build_report(store)
    assert (after.funnel, after.tiers, after.rules) == (report.funnel, report.tiers, report.rules)

    summary = store.ingest_summary()
    assert [c.session_id for c in summary.changed] == [sid] and summary.skipped == ()
    log = attempt_log_view(load_batch(store))
    assert log.not_ingested == () and [c.session_id for c in log.changed] == [sid]
    assert log.changed_label == wording.CHANGED_LABEL and log.changed[0].differs
    assert "did not bring in" not in log.ingest_note and "1 of the sessions brought in" in log.ingest_note
    assert after.phone_sessions_not_ingested == 0 and after.phone_sessions_changed == 1
    snap = snapshot(store.root)
    assert main(["ingest", "--state", str(state)]) == 0
    capsys.readouterr()
    assert {k: v for k, v in snapshot(store.root).items() if k != "ingest.json"} == {
        k: v for k, v in snap.items() if k != "ingest.json"
    }

    snap = snapshot(store.root)
    assert ingest(store, sessions, nothing).changed == found.changed
    assert snapshot(store.root) == snap  # a second ingest changes no store file, ingest.json included


def test_an_outside_call_whose_case_file_changes_stays_outside_and_is_listed_as_changed(tmp_path: Path) -> None:
    a, late = loan(1), loan(2, SOLD + timedelta(days=20))
    store, _ = open_batch(tmp_path / "ops", [a, late], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, late, coached(late), None)
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    put_case(sessions, case | {"language": "hi-en"})
    found = ingest(store, sessions, nothing)
    assert found.outside == [case["session_id"]] and found.skipped == []
    assert "language" in dict(found.changed)[case["session_id"]]
    _assert_one_place(found, sessions)


def test_a_linked_session_whose_case_file_now_says_outside_stays_linked(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON)
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    put_case(sessions, {k: v for k, v in case.items() if k != "book"})
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.outside == [] and found.skipped == []
    assert "outside the sample" in dict(found.changed)[case["session_id"]]


def test_the_cli_prints_the_changed_list_apart_from_the_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = loan(1)
    state = tmp_path / "state"
    store, _ = open_batch(state / "ops", [a], DRAWN_ON)
    sessions = state / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON)
    put_case(sessions, case)
    (sessions / "20261110T000000-00000000dead").mkdir()
    assert main(["ingest", "--state", str(state)]) == 0
    put_case(sessions, case | {"models": {"extraction": {"model": "another-model"}}})
    capsys.readouterr()
    assert main(["ingest", "--state", str(state)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("1 session(s) on drawn loans, 0 outside the sample, 1 skipped; 1 of those brought in")
    assert f"  changed after it was brought in {case['session_id']}: " in out
    assert "skipped 20261110T000000-00000000dead" in out and f"skipped {case['session_id']}" not in out


# --- 6. booleans and counts --------------------------------------------------------------------------


def _with_readings(tmp_path: Path, agreed, ok=True) -> tuple[OpsStore, dict]:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    who = customer(a, COMPLETED, concerns=(SaleConcern.coached_answers,), premium_inr=52_000)
    case = phone_case(store, a, who, DRAWN_ON)
    (turn_id,) = [f["turn_id"] for f in case["result"]["products"][0]["flags"] if f["rule_id"] == "premium"]
    case["turns"] = [
        {
            "turn_id": turn_id,
            "text": "x",
            "readings": [
                {"role": "primary", "model": "prisma-v3.0", "ok": ok, "text": "52,000 रुपये।"},
                {"role": "second", "model": "prisma-v2.5", "ok": True, "text": "52 हज़ार रुपए"},
            ],
            "readings_agreed": agreed,
        }
    ]
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert found.linked == [case["session_id"]], found.skipped
    return store, case


def _premium_line(store: OpsStore, case: dict):
    view = case_view(load_batch(store), case["session_id"])
    lines = [x for x in (*view.refer_lines, *view.other_lines) if x.quote and x.quote.readings]
    return lines[0].quote.readings


@pytest.mark.parametrize("agreed", ["yes", "on", "true", 1, 0, "no", [], {}])
def test_readings_agreed_that_is_not_a_json_boolean_makes_no_claim_of_same_or_differ(
    tmp_path: Path, agreed
) -> None:
    store, case = _with_readings(tmp_path, agreed)
    assert store.call(case["session_id"]).readings[0].agreed is None
    assert _premium_line(store, case).closing == wording.READINGS_NOT_COMPARED


@pytest.mark.parametrize(("agreed", "closing"), [(True, wording.READINGS_SAME), (False, wording.READINGS_DIFFER)])
def test_readings_agreed_true_or_false_is_kept(tmp_path: Path, agreed: bool, closing: str) -> None:
    store, case = _with_readings(tmp_path, agreed)
    assert _premium_line(store, case).closing == closing


@pytest.mark.parametrize("ok", ["yes", 1, "true", None])
def test_a_reading_whose_ok_is_not_a_json_boolean_never_shows_its_text_as_the_models_words(
    tmp_path: Path, ok
) -> None:
    store, case = _with_readings(tmp_path, True, ok=ok)
    primary = _premium_line(store, case).parts[0]
    assert not primary.as_written and primary.text == wording.READINGS_NO_TEXT


# --- the speaker_confirmed rule ----------------------------------------------------------------------


def _speaker(store: OpsStore, of, outcome: str, confirmed, day: int = 3, hour: int = 0, **kw) -> dict:
    case = phone_case(
        store, of, None, of.sold_on + timedelta(days=day), outcome, started=WALL + timedelta(hours=hour), **kw
    )
    if confirmed != "absent":
        case["speaker_confirmed"] = confirmed
    return case


@pytest.mark.parametrize("outcome", ["do_not_call", "human_requested", "call_back_later", "written_requested"])
def test_a_request_from_an_unconfirmed_speaker_is_its_own_outcome_and_the_loan_is_called_again(
    tmp_path: Path, outcome: str
) -> None:
    a, b = loan(1), loan(2)
    store, draw = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = _speaker(store, a, outcome, False)
    put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]]
    (attempt,) = store.attempts()
    assert attempt.outcome is AttemptOutcome.request_unconfirmed
    assert attempt.right_party_confirmed is False and attempt.dialogue_outcome == outcome

    batch = load_batch(store)
    s = next(x for x in batch.sampled if x.loan.record.loan_id == a.record.loan_id)
    assert s.status is FinalStatus.request_unconfirmed
    report = build_report(store)
    exits = {row.key: row.value.count for row in report.funnel.exits}
    assert exits["request_unconfirmed"] == 1
    assert exits["do_not_call"] == exits["call_back_later"] == exits["incomplete"] == exits["written_requested"] == 0
    stages = {row.key: row.value.count for row in report.funnel.stages}
    assert stages["reached"] == 1 and stages["right_party_confirmed"] == 0
    label = next(row.label for row in report.funnel.exits if row.key == "request_unconfirmed")
    assert label == wording.STATUS_LABEL[FinalStatus.request_unconfirmed]
    assert "not confirmed as the borrower" in label and not wording.banned_in(label)

    log = attempt_log_view(batch)
    row = next(x for x in log.loans if x.loan_id == a.record.loan_id)
    (shown,) = row.attempts
    assert shown.outcome_label == "Request from a speaker not confirmed as the borrower"
    assert (shown.dialogue_outcome, shown.request) == (outcome, wording.UNCONFIRMED_REQUEST_LABEL[outcome])
    assert queue_view(batch).items == ()  # no analysed call: never in the queue

    # The loan stays retryable: the simulator calls again, and so may the phone.
    run_draw(store, draw, {a.record.loan_id: customer(a, COMPLETED), b.record.loan_id: customer(b, COMPLETED)}, scripted_analysis)
    chain = next(x for x in load_batch(store).sampled if x.loan.record.loan_id == a.record.loan_id)
    assert [x.outcome for x in chain.attempts] == [AttemptOutcome.request_unconfirmed, AttemptOutcome.completed]


@pytest.mark.parametrize("outcome", ["do_not_call", "human_requested", "call_back_later", "written_requested"])
@pytest.mark.parametrize("confirmed", [True, None, "absent"])
def test_with_speaker_confirmed_true_or_unknown_the_request_maps_as_before(
    tmp_path: Path, outcome: str, confirmed
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    put_case(tmp_path / "sessions", _speaker(store, a, outcome, confirmed))
    ingest(store, tmp_path / "sessions", nothing)
    (attempt,) = store.attempts()
    expected = {
        "do_not_call": AttemptOutcome.do_not_call,
        "human_requested": AttemptOutcome.incomplete,
        "call_back_later": AttemptOutcome.call_back_later,
        "written_requested": AttemptOutcome.written_requested,
    }[outcome]
    assert attempt.outcome is expected
    # present: it decides; unknown: derived as before (no transcript, so not claimed)
    assert attempt.right_party_confirmed is (confirmed is True)


def test_speaker_confirmed_decides_right_party_confirmed_when_present(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    put_case(tmp_path / "sessions", _speaker(store, a, "declined", False))
    ingest(store, tmp_path / "sessions", nothing)
    assert store.attempts()[0].right_party_confirmed is False


@pytest.mark.parametrize(
    ("outcome", "confirmed", "status"),
    [
        ("completed", False, "ready"),
        ("completed", False, "failed"),
        ("wrong_party", True, "ready"),
        ("not_confirmed", True, "ready"),
        ("second_check_failed", True, "ready"),
        ("no_response", True, "ready"),
    ],
)
def test_a_case_file_whose_speaker_confirmed_contradicts_its_outcome_is_skipped(
    tmp_path: Path, outcome: str, confirmed: bool, status: str
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case = phone_case(store, a, coached(a), DRAWN_ON, outcome, status=status) | {"speaker_confirmed": confirmed}
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert "contradicts itself" in dict(found.skipped)[case["session_id"]]
    assert store.attempts() == ()


def test_an_unconfirmed_request_on_day_30_or_later_is_not_reached_in_time(tmp_path: Path) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, _speaker(store, a, "do_not_call", False, day=30))
    put_case(sessions, _speaker(store, b, "do_not_call", False, day=29, hour=1))
    ingest(store, sessions, nothing)
    status = {s.loan.record.loan_id: s.status for s in load_batch(store).sampled}
    assert status[a.record.loan_id] is FinalStatus.not_reached_in_time
    assert status[b.record.loan_id] is FinalStatus.request_unconfirmed


def test_unconfirmed_requests_count_towards_the_attempt_limit(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    cases = [_speaker(store, a, "call_back_later", False, day=3 + k, hour=k) for k in range(MAX_ATTEMPTS + 1)]
    for case in cases:
        put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [c["session_id"] for c in cases[:MAX_ATTEMPTS]]
    assert "the most a loan gets" in dict(found.skipped)[cases[-1]["session_id"]]
    (s,) = load_batch(store).sampled
    # the label promises no further call: at the limit there is none
    assert s.status is FinalStatus.request_unconfirmed and "no call after it" in wording.STATUS_LABEL[s.status]


def test_an_unconfirmed_request_outside_the_sample_says_what_was_asked(tmp_path: Path) -> None:
    a, late = loan(1), loan(2, SOLD + timedelta(days=20))
    store, _ = open_batch(tmp_path / "ops", [a, late], DRAWN_ON)
    case = phone_case(store, late, None, None, "do_not_call") | {"speaker_confirmed": False}
    put_case(tmp_path / "sessions", case)
    ingest(store, tmp_path / "sessions", nothing)
    (o,) = attempt_log_view(load_batch(store)).outside
    assert o.outcome is AttemptOutcome.request_unconfirmed and o.dialogue_outcome == "do_not_call"
    assert o.request == "asked not to be called again"


def test_a_written_request_from_an_unconfirmed_speaker_is_shown_in_words_and_never_ends_the_chain(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    first = _speaker(store, a, "written_requested", False)
    later = _speaker(store, a, "written_requested", True, day=4, hour=1)
    put_case(sessions, first)
    put_case(sessions, later)
    found = ingest(store, sessions, nothing)
    assert found.linked == [first["session_id"], later["session_id"]]  # the first ended nothing
    log = attempt_log_view(load_batch(store))
    (row,) = log.loans
    unconfirmed, confirmed = row.attempts
    assert unconfirmed.outcome is AttemptOutcome.request_unconfirmed
    assert unconfirmed.request == "asked for this in writing instead" and not wording.banned_in(unconfirmed.request)
    # From the confirmed borrower it is their own request and ends the chain, as before.
    assert (confirmed.outcome, confirmed.request) == (AttemptOutcome.written_requested, None)
    assert row.status is FinalStatus.written_requested


def test_hostile_table_is_not_shared_state() -> None:
    """Each hostile change works on its own copy of a case file (guards the table above)."""
    base = {"models": {"extraction": {"model": "m"}}, "book": {"batch_id": "B"}}
    for change in HOSTILE.values():
        change(copy.deepcopy(base))
    assert base == {"models": {"extraction": {"model": "m"}}, "book": {"batch_id": "B"}}
