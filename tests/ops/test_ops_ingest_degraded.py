"""A phone session with a turn the dialogue's classifier failed on (the case file's `degraded_turns`)
is void: skipped with its own reason, in no count, and the loan can be called again. A void session
that ended in a request (stop, a person, later, in writing) is logged as that request, not counted:
a confirmed borrower's "do not call me" stops the loan for ingest and for the phone server alike."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from opskit import (
    COMPLETED,
    SOLD,
    WALL,
    coached,
    customer,
    loan,
    open_batch,
    phone_case,
    put_case,
    snapshot,
)
from serverkit import FakeSpeech
from starlette.testclient import TestClient

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import MAX_ATTEMPTS, RETRY_AFTER, AttemptOutcome, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import CLASSIFIER_FAILED, ingest
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import AttemptLogView, attempt_log_view, queue_view
from samajh.server import create_app
from samajh.server.loanbook import LoanBook, LoanRefused

DRAWN_ON = SOLD + timedelta(days=3)


def nothing(record_id: str):
    return


def _counts(store: OpsStore) -> tuple:
    report = build_report(store)
    return (
        [(r.key, r.value.count) for r in (*report.funnel.stages, *report.funnel.exits)],
        [(r.tier, r.value.count) for r in report.tiers],
        [(f.rule_id, f.flagged.count) for f in report.rules],
        report.batch.referred,
    )


@pytest.mark.parametrize(
    ("turns", "reason"),
    [
        ([4], "not counted: the classifier failed on 1 turn (turn ids 4)"),
        ([2, 6], "not counted: the classifier failed on 2 turns (turn ids 2, 6)"),
    ],
)
def test_a_session_with_a_degraded_turn_is_listed_not_counted_and_the_loan_is_called_again(
    tmp_path: Path, turns: list[int], reason: str
) -> None:
    a, b = loan(1), loan(2)
    store, draw = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    # A completed call that would be referred (a coached customer), so a tier would show if it counted.
    case = phone_case(store, a, coached(a), DRAWN_ON) | {"degraded_turns": turns, "speaker_confirmed": True}
    put_case(sessions, case)
    before = _counts(store)

    found = ingest(store, sessions, nothing)
    assert (found.linked, found.outside, found.skipped) == ([], [], [(case["session_id"], reason)])
    assert reason.startswith(CLASSIFIER_FAILED)
    assert store.attempts() == () and store.outside() == ()
    assert _counts(store) == before  # no tier, outcome, funnel stage or rule count moved
    batch = load_batch(store)
    assert queue_view(batch).items == ()
    s = next(x for x in batch.sampled if x.loan.record.loan_id == a.record.loan_id)
    assert s.status is FinalStatus.not_attempted and s.call is None and s.triage is None

    log = attempt_log_view(batch)
    assert [(x.session_id, x.reason) for x in log.not_ingested] == [(case["session_id"], reason)]
    assert "1 of those left out had a turn the classifier failed on" in log.ingest_note
    assert "is to be repeated" in log.ingest_note and not wording.banned_in(log.ingest_note)
    report = build_report(store)
    assert report.phone_sessions_not_ingested == 1 and report.ingest_note == log.ingest_note

    # Rerun: the same. The loan is still callable: the simulator's call is its first attempt.
    assert ingest(store, sessions, nothing).skipped == found.skipped
    run_draw(
        store,
        draw,
        {a.record.loan_id: customer(a, COMPLETED), b.record.loan_id: customer(b, COMPLETED)},
        scripted_analysis,
    )
    (only,) = next(x for x in load_batch(store).sampled if x.loan.record.loan_id == a.record.loan_id).attempts
    assert (only.number, only.outcome) == (1, AttemptOutcome.completed)


@pytest.mark.parametrize("field", [{"degraded_turns": []}, {}])
def test_a_clean_session_or_one_without_the_field_is_brought_in_as_before(
    tmp_path: Path, field: dict
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case = phone_case(store, a, coached(a), DRAWN_ON) | field
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    assert "classifier" not in attempt_log_view(load_batch(store)).ingest_note


@pytest.mark.parametrize("bad", ["4", [1.5], ["4"], [True], {"4": 1}])
def test_a_degraded_turns_field_that_is_not_a_list_of_whole_numbers_is_unreadable(
    tmp_path: Path, bad
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case = phone_case(store, a, coached(a), DRAWN_ON) | {"degraded_turns": bad}
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert dict(found.skipped)[case["session_id"]].startswith("case file could not be read: degraded_turns")
    assert store.attempts() == ()


# --- which reason wins --------------------------------------------------------------------------


def test_a_case_file_that_contradicts_itself_is_skipped_for_that_even_when_degraded(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case = phone_case(store, a, coached(a), DRAWN_ON) | {"degraded_turns": [3], "speaker_confirmed": False}
    put_case(tmp_path / "sessions", case)
    (why,) = dict(ingest(store, tmp_path / "sessions", nothing).skipped).values()
    assert "contradicts itself" in why


def test_the_classifier_reason_wins_over_every_book_loan_and_chain_rule(tmp_path: Path) -> None:
    a, b, stranger = loan(1), loan(2), loan(9)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    ended = phone_case(store, b, None, DRAWN_ON, "do_not_call")  # b's chain ends here
    put_case(sessions, ended)
    cases = {
        "unknown loan": phone_case(
            store, stranger, None, DRAWN_ON, "declined", started=WALL + timedelta(hours=1)
        ),
        "other batch": phone_case(store, a, None, DRAWN_ON, "declined", started=WALL + timedelta(hours=2)),
        "chain ended": phone_case(
            store, b, None, DRAWN_ON + timedelta(days=1), "declined", started=WALL + timedelta(hours=3)
        ),
        "no book block": phone_case(store, a, None, None, "declined", started=WALL + timedelta(hours=4)),
    }
    cases["other batch"]["book"]["batch_id"] = "B-other"
    for case in cases.values():
        put_case(sessions, case | {"degraded_turns": [2]})
    found = ingest(store, sessions, nothing)
    why = dict(found.skipped)
    assert found.linked == [ended["session_id"]] and found.outside == []
    for name, case in cases.items():
        assert why[case["session_id"]] == "not counted: the classifier failed on 1 turn (turn ids 2)", name


def test_a_session_brought_in_before_it_was_degraded_stays_and_is_listed_as_changed(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, coached(a), DRAWN_ON)
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    counted = _counts(store)

    put_case(sessions, case | {"degraded_turns": [5]})
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    ((sid, differs),) = found.changed
    assert sid == case["session_id"] and "the classifier failed on 1 turn (turn ids 5)" in differs
    assert differs.endswith("still counted") and not differs.startswith(CLASSIFIER_FAILED)
    assert _counts(store) == counted  # nothing already logged is dropped


# --- a void session that ended in a request -------------------------------------------------------

VOID = "not counted: the classifier failed on 1 turn (turn ids 1)"


def _counted(store: OpsStore) -> tuple:
    """Tiers, rule counts and referrals: what a void request must never move."""
    report = build_report(store)
    return (
        [(r.tier, r.value.count) for r in report.tiers],
        [(f.rule_id, f.flagged.count) for f in report.rules],
        report.batch.referred,
    )


def _server_refusal(state: Path, loan_id: str) -> str | None:
    """The phone server's code for refusing a new call on the loan; None when it would place one."""
    try:
        LoanBook(state).open_call(loan_id)
    except LoanRefused as refused:
        return refused.code
    return None


def _void(store: OpsStore, of, outcome: str, confirmed, day: int = 0, hours: int = 0) -> dict:
    case = phone_case(
        store, of, None, DRAWN_ON + timedelta(days=day), outcome, started=WALL + timedelta(hours=hours)
    ) | {"degraded_turns": [1]}
    if confirmed is not None:
        case["speaker_confirmed"] = confirmed
    return case


def test_a_confirmed_do_not_call_in_a_void_session_stops_the_loan_and_is_not_counted(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    before = _counted(store)
    void = _void(store, a, "do_not_call", True)
    put_case(sessions, void)
    assert _server_refusal(tmp_path, a.record.loan_id) is None  # callable before

    found = ingest(store, sessions, nothing)
    assert found.linked == [void["session_id"]] and found.skipped == []
    (attempt,) = store.attempts()
    assert (attempt.number, attempt.outcome, attempt.right_party_confirmed) == (
        1,
        AttemptOutcome.do_not_call,
        True,
    )
    assert attempt.not_counted == VOID and attempt.call_id is None
    assert _counted(store) == before and queue_view(load_batch(store)).items == ()

    # Both the phone server and ingest's chain see it: no further call on the loan.
    assert _server_refusal(tmp_path, a.record.loan_id) == "attempts_ended"
    again = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=1), started=WALL + timedelta(hours=1))
    put_case(sessions, again)
    found = ingest(store, sessions, nothing)
    assert found.linked == [void["session_id"]]
    assert "attempts had already ended" in dict(found.skipped)[again["session_id"]]
    assert store.attempts() == (attempt,)


@pytest.mark.parametrize(
    ("confirmed", "exit_status", "confirmed_stage"),
    [(True, FinalStatus.do_not_call, 1), (False, FinalStatus.request_unconfirmed, 0)],
)
def test_a_void_request_is_an_attempt_in_the_funnel_marked_not_counted_and_in_no_tier(
    tmp_path: Path, confirmed: bool, exit_status: FinalStatus, confirmed_stage: int
) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    before = _counted(store)
    put_case(tmp_path / "sessions", _void(store, a, "do_not_call", confirmed))
    ingest(store, tmp_path / "sessions", nothing)

    funnel = build_report(store).funnel
    stages = {r.key: r.value.count for r in funnel.stages}
    exits = {r.key: (r.value.count, r.not_counted) for r in funnel.exits}
    assert (funnel.sampled, funnel.attempts) == (2, 1)
    assert stages == {"attempted": 1, "reached": 1, "right_party_confirmed": confirmed_stage, "completed": 0}
    assert exits[exit_status.value][0] == 1 and exits[FinalStatus.not_attempted.value][0] == 1
    assert stages["completed"] + sum(count for count, _ in exits.values()) == funnel.sampled
    assert _counted(store) == before  # no tier, rule count or referral

    batch = load_batch(store)
    s = next(x for x in batch.sampled if x.loan.record.loan_id == a.record.loan_id)
    assert s.status is exit_status and s.ended_by_uncounted_call
    assert s.call is None and s.triage is None and not s.counted and queue_view(batch).items == ()
    other = next(x for x in batch.sampled if x.loan.record.loan_id == b.record.loan_id)
    assert not other.ended_by_uncounted_call

    (view,) = next(x for x in attempt_log_view(batch).loans if x.loan_id == a.record.loan_id).attempts
    assert view.not_counted == VOID and view.outcome.value == exit_status.value


def test_a_counted_attempt_has_no_not_counted_reason_and_its_dump_leaves_the_field_out(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    put_case(tmp_path / "sessions", phone_case(store, a, None, DRAWN_ON, "do_not_call"))
    ingest(store, tmp_path / "sessions", nothing)
    batch = load_batch(store)
    (view,) = attempt_log_view(batch).loans[0].attempts
    assert view.not_counted is None and "not_counted" not in view.model_dump()
    assert not batch.sampled[0].ended_by_uncounted_call
    assert all("not_counted" not in r.model_dump() for r in build_report(store).funnel.exits)
    assert "not_counted" not in (store.root / "attempts.jsonl").read_text()


@pytest.mark.parametrize("confirmed", [False, None])
@pytest.mark.parametrize(
    "outcome", ["do_not_call", "human_requested", "call_back_later", "written_requested"]
)
def test_an_unconfirmed_request_in_a_void_session_is_logged_and_the_loan_stays_retryable(
    tmp_path: Path, outcome: str, confirmed
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    before = _counted(store)
    void = _void(store, a, outcome, confirmed)
    put_case(sessions, void)
    found = ingest(store, sessions, nothing)
    assert found.linked == [void["session_id"]]
    (attempt,) = store.attempts()
    assert (attempt.outcome, attempt.right_party_confirmed, attempt.not_counted) == (
        AttemptOutcome.request_unconfirmed,
        False,
        VOID,
    )
    assert attempt.dialogue_outcome == outcome and _counted(store) == before
    assert _server_refusal(tmp_path, a.record.loan_id) is None

    again = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=1), started=WALL + timedelta(hours=1))
    put_case(sessions, again)
    assert ingest(store, sessions, nothing).linked == [void["session_id"], again["session_id"]]
    assert [(x.number, x.outcome) for x in store.attempts()] == [
        (1, AttemptOutcome.request_unconfirmed),
        (2, AttemptOutcome.completed),
    ]


@pytest.mark.parametrize(
    ("outcome", "logged"),
    [
        ("human_requested", AttemptOutcome.incomplete),
        ("call_back_later", AttemptOutcome.call_back_later),
        ("written_requested", AttemptOutcome.written_requested),
    ],
)
def test_the_other_confirmed_requests_in_a_void_session_are_mapped_as_today(
    tmp_path: Path, outcome: str, logged: AttemptOutcome
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    before = _counted(store)
    void = _void(store, a, outcome, True)
    put_case(tmp_path / "sessions", void)
    assert ingest(store, tmp_path / "sessions", nothing).linked == [void["session_id"]]
    (attempt,) = store.attempts()
    assert (attempt.number, attempt.outcome, attempt.not_counted) == (1, logged, VOID)
    assert _counted(store) == before
    refused = _server_refusal(tmp_path, a.record.loan_id)
    assert refused == (None if logged in RETRY_AFTER else "attempts_ended")


def test_void_requests_take_attempt_numbers_so_a_loan_never_passes_the_limit(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    voids = [_void(store, a, "call_back_later", True, day=i, hours=i) for i in range(MAX_ATTEMPTS + 1)]
    for case in voids:
        put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [c["session_id"] for c in voids[:MAX_ATTEMPTS]]
    (why,) = dict(found.skipped).values()
    assert why.startswith(f"{VOID}; its request was not logged: the loan already has {MAX_ATTEMPTS}")
    assert [x.number for x in store.attempts()] == list(range(1, MAX_ATTEMPTS + 1))
    assert _server_refusal(tmp_path, a.record.loan_id) == "attempt_limit"


def test_ingesting_void_requests_again_changes_nothing(tmp_path: Path) -> None:
    a, b = loan(1), loan(2)
    store, _ = open_batch(tmp_path / "ops", [a, b], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, _void(store, a, "do_not_call", True))
    put_case(sessions, _void(store, b, "call_back_later", False, hours=1))
    put_case(sessions, _void(store, b, "declined", False, day=1, hours=2))  # not the borrower's: skipped
    first = ingest(store, sessions, nothing)
    files = snapshot(store.root)
    again = ingest(store, sessions, nothing)
    assert (again.linked, again.skipped, again.changed) == (first.linked, first.skipped, [])
    assert snapshot(store.root) == files
    assert len(first.linked) == 2 and [why for _, why in first.skipped] == [VOID]


def test_a_void_completed_call_and_a_void_request_off_the_book_are_still_skipped(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    completed = phone_case(store, a, coached(a), DRAWN_ON) | {
        "degraded_turns": [1],
        "speaker_confirmed": True,
    }
    off_book = phone_case(store, a, None, None, "do_not_call", started=WALL + timedelta(hours=1)) | {
        "degraded_turns": [1],
        "speaker_confirmed": True,
    }
    put_case(sessions, completed)
    put_case(sessions, off_book)
    found = ingest(store, sessions, nothing)
    why = dict(found.skipped)
    assert found.linked == [] and found.outside == [] and store.attempts() == () and store.outside() == ()
    assert why[completed["session_id"]] == VOID
    assert why[off_book["session_id"]].startswith(f"{VOID}; its request was not logged: ")


def test_a_request_brought_in_before_it_was_degraded_stays_counted_and_is_listed_as_changed(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case = phone_case(store, a, None, DRAWN_ON, "do_not_call") | {"speaker_confirmed": True}
    put_case(sessions, case)
    ingest(store, sessions, nothing)
    logged = store.attempts()

    put_case(sessions, case | {"degraded_turns": [1]})
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    ((_, differs),) = found.changed
    assert differs.startswith("the classifier failed on 1 turn") and differs.endswith("still counted")
    assert store.attempts() == logged


# --- a confirmed decline in a void session; the funnel and the attempt page -----------------------


def test_a_confirmed_decline_in_a_void_session_is_logged_not_counted_and_ends_the_loan(
    tmp_path: Path,
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    before = _counted(store)
    void = _void(store, a, "declined", True)
    put_case(sessions, void)

    found = ingest(store, sessions, nothing)
    assert found.linked == [void["session_id"]] and found.skipped == []
    (attempt,) = store.attempts()
    assert (attempt.number, attempt.outcome, attempt.right_party_confirmed, attempt.not_counted) == (
        1,
        AttemptOutcome.declined,
        True,
        VOID,
    )
    assert attempt.call_id is None and _counted(store) == before
    batch = load_batch(store)
    assert batch.sampled[0].status is FinalStatus.declined and batch.sampled[0].ended_by_uncounted_call
    assert queue_view(batch).items == ()
    # The borrower is not called again, by the phone server or through ingest.
    assert _server_refusal(tmp_path, a.record.loan_id) == "attempts_ended"
    again = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=1), started=WALL + timedelta(hours=1))
    put_case(sessions, again)
    assert "attempts had already ended" in dict(ingest(store, sessions, nothing).skipped)[again["session_id"]]
    assert ingest(store, sessions, nothing).changed == [] and store.attempts() == (attempt,)


@pytest.mark.parametrize("confirmed", [False, None])
def test_a_decline_in_a_void_session_from_a_speaker_not_confirmed_is_skipped(
    tmp_path: Path, confirmed
) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    void = _void(store, a, "declined", confirmed)
    put_case(tmp_path / "sessions", void)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert found.linked == [] and found.skipped == [(void["session_id"], VOID)]
    assert store.attempts() == () and _server_refusal(tmp_path, a.record.loan_id) is None


def test_a_funnel_exit_row_counts_its_loans_that_ended_on_a_request_in_a_call_not_counted(
    tmp_path: Path,
) -> None:
    a, b, c = loan(1), loan(2), loan(3)
    store, _ = open_batch(tmp_path / "ops", [a, b, c], DRAWN_ON)
    sessions = tmp_path / "sessions"
    put_case(sessions, _void(store, a, "do_not_call", True))
    put_case(sessions, phone_case(store, b, None, DRAWN_ON, "do_not_call", started=WALL + timedelta(hours=1)))
    put_case(sessions, _void(store, c, "declined", True, hours=2))
    assert len(ingest(store, sessions, nothing).linked) == 3

    exits = {r.key: (r.value.count, r.not_counted) for r in build_report(store).funnel.exits}
    assert exits[FinalStatus.do_not_call.value] == (2, 1)  # one counted request, one from a void call
    assert exits[FinalStatus.declined.value] == (1, 1)
    assert all(
        not_counted == 0 for key, (_, not_counted) in exits.items() if key not in {"do_not_call", "declined"}
    )


def test_the_attempt_page_gets_why_a_logged_request_was_not_counted_in_neutral_words(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    put_case(tmp_path / "sessions", _void(store, a, "do_not_call", True))
    ingest(store, tmp_path / "sessions", nothing)
    client = TestClient(create_app(gnani=FakeSpeech(), state=tmp_path, web_dir=None, clips_dir=None))
    log = AttemptLogView.model_validate(client.get("/api/review/attempts").json())
    (view,) = next(x for x in log.loans if x.loan_id == a.record.loan_id).attempts
    assert view.not_counted == VOID
    # The chip line as review.js renders it beside the attempt.
    line = f"Request kept on the log; the call is {view.not_counted}"
    assert not wording.banned_in(line)
