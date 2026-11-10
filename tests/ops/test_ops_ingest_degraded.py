"""A phone session with a turn the dialogue's classifier failed on (the case file's `degraded_turns`)
is void: skipped with its own reason, in no count, and the loan can be called again."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from opskit import COMPLETED, SOLD, WALL, coached, customer, loan, open_batch, phone_case, put_case

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import AttemptOutcome, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import CLASSIFIER_FAILED, ingest
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, queue_view

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


def test_a_repeated_clean_call_on_the_same_loan_is_its_first_attempt(tmp_path: Path) -> None:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    sessions = tmp_path / "sessions"
    void = phone_case(store, a, None, DRAWN_ON, "do_not_call") | {
        "degraded_turns": [1],
        "speaker_confirmed": True,
    }
    again = phone_case(store, a, coached(a), DRAWN_ON + timedelta(days=1), started=WALL + timedelta(hours=1))
    put_case(sessions, void)
    put_case(sessions, again)
    found = ingest(store, sessions, nothing)
    # The void session's "do not call" ended nothing: the repeated call is brought in as attempt 1.
    assert found.linked == [again["session_id"]] and [sid for sid, _ in found.skipped] == [void["session_id"]]
    (attempt,) = store.attempts()
    assert (attempt.number, attempt.outcome) == (1, AttemptOutcome.completed)


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
