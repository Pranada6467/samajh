"""A log whose last line has no newline: a torn append is set aside, a whole one is kept."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from opskit import COMPLETED, NO_ANSWER, SOLD, coached, customer, loan, phone_case, put_case, run_batch

from samajh.ops.batch import load_batch
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest

TORN = b'{"attempt_id": "D-2027-02-10/x/half", "draw_'
AS_OF = SOLD + timedelta(days=10)


def nothing(record_id: str):
    return


def _batch(tmp_path: Path):
    a, b = loan(1), loan(2)
    store = run_batch(tmp_path / "ops", [a, b], [coached(a, COMPLETED), customer(b, NO_ANSWER)], AS_OF)
    return store, b


def test_a_torn_last_attempt_line_is_set_aside_and_no_attempt_is_lost(tmp_path: Path) -> None:
    store, b = _batch(tmp_path)
    log = store.root / "attempts.jsonl"
    earlier = store.attempts()
    assert earlier
    with log.open("ab") as f:
        f.write(TORN)

    # Before the next append: the store still reads and reports.
    assert store.attempts() == earlier
    load_batch(store)
    build_report(store)

    case = phone_case(store, b, customer(b, COMPLETED), AS_OF + timedelta(days=1))
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert found.linked == [case["session_id"]], found.skipped

    # After it: every earlier attempt is still there, the new one is kept, the fragment is aside.
    after = store.attempts()
    assert after[: len(earlier)] == earlier and len(after) == len(earlier) + 1
    assert after[-1].call_id == case["session_id"]
    assert (store.root / "attempts.jsonl.torn").read_bytes() == TORN + b"\n"
    assert TORN not in log.read_bytes() and log.read_bytes().endswith(b"\n")
    load_batch(store)
    build_report(store)


def test_a_whole_last_line_with_no_newline_is_kept_and_the_next_append_starts_a_new_line(
    tmp_path: Path,
) -> None:
    store, b = _batch(tmp_path)
    log = store.root / "attempts.jsonl"
    earlier = store.attempts()
    log.write_bytes(log.read_bytes().rstrip(b"\n"))  # the last whole entry lost only its newline

    assert store.attempts() == earlier
    case = phone_case(store, b, customer(b, COMPLETED), AS_OF + timedelta(days=1))
    put_case(tmp_path / "sessions", case)
    assert ingest(store, tmp_path / "sessions", nothing).linked == [case["session_id"]]

    after = store.attempts()
    assert after[: len(earlier)] == earlier and len(after) == len(earlier) + 1
    assert not (store.root / "attempts.jsonl.torn").exists()
    assert len(log.read_bytes().splitlines()) == len(after)
    build_report(store)
