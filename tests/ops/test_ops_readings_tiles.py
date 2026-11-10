"""The case page's speech readings beside an amount quote, and the report's number tiles."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from opskit import (
    COMPLETED,
    SOLD,
    WALL,
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
from samajh.ops.model import CallRecord
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest
from samajh.ops.store import OpsStore
from samajh.ops.views import ReadingsView, case_view
from samajh.types import RuleId, SaleConcern, Tier

DRAWN_ON = SOLD + timedelta(days=3)
# Texts as a model might write them, with characters a normaliser would change: kept byte for byte.
V3 = "52,000 रुपये।"
V25 = "52 हज़ार  रुपए"


def nothing(record_id: str):
    return


def _primary(text: str | None = V3, ok: bool = True, error: str | None = None) -> dict:
    return {
        "role": "primary",
        "mode": "rest",
        "model": "prisma-v3.0",
        "params": {},
        "ok": ok,
        "error": error,
        "text": text,
    }


def _second(text: str | None = V25, ok: bool = True, error: str | None = None) -> dict:
    return {
        "role": "second",
        "mode": "rest",
        "model": "prisma-v2.5",
        "params": {},
        "ok": ok,
        "error": error,
        "text": text,
    }


def _referred_premium(store: OpsStore, a, turns=None) -> tuple[dict, int]:
    """A completed phone call referred for coached answers and for a premium of 52,000 against the
    record's 12,500. `turns(premium_turn_id)` gives the case file's `turns`."""
    who = customer(a, COMPLETED, concerns=(SaleConcern.coached_answers,), premium_inr=52_000)
    case = phone_case(store, a, who, DRAWN_ON)
    (premium,) = [f for f in case["result"]["products"][0]["flags"] if f["rule_id"] == "premium"]
    if turns is not None:
        case["turns"] = turns(premium["turn_id"])
    return case, premium["turn_id"]


def _readings(tmp_path: Path, turns) -> tuple[ReadingsView, dict]:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case, turn_id = _referred_premium(store, a, turns)
    put_case(tmp_path / "sessions", case)
    found = ingest(store, tmp_path / "sessions", nothing)
    assert found.linked == [case["session_id"]], found.skipped
    view = case_view(load_batch(store), case["session_id"])
    (line,) = [x for x in view.refer_lines if RuleId.premium in x.rule_ids]
    assert line.quote is not None and line.quote.turn_id == turn_id
    # Only the amount quote carries a readings line.
    others = [x for x in (*view.refer_lines, *view.other_lines) if x is not line and x.quote]
    assert others and all(x.quote.readings is None for x in others)
    assert line.quote.readings is not None
    return line.quote.readings, case


def _line(r: ReadingsView) -> str:
    """The line as review.js renders it."""
    if not r.parts:
        return r.closing
    return " · ".join(f"{p.model}: {p.text}" for p in r.parts) + f" · {r.closing}"


_MISSING = object()


def _turn(readings: list[dict], agreed: bool | None, followed_by=_MISSING):
    """The case file's turns: one turn with these readings; `followed_by` left out unless given."""

    def turns(tid: int) -> list[dict]:
        turn = {"turn_id": tid, "text": V3, "readings": readings, "readings_agreed": agreed}
        if followed_by is not _MISSING:
            turn["followed_by"] = followed_by
        return [turn]

    return turns


TWO = f"Prisma v3.0: {V3} · Prisma v2.5: {V25}"


@pytest.mark.parametrize(
    ("readings", "agreed", "followed_by", "expected"),
    [
        # The closing is built from readings_agreed and followed_by only.
        ([_primary(), _second()], True, "read_back", f"{TWO} · same amount, read back"),
        ([_primary(), _second()], False, "asked_again", f"{TWO} · differ, asked again"),
        ([_primary(), _second()], False, "read_back", f"{TWO} · {wording.READINGS_DIFFER_READ_BACK}"),
        ([_primary(), _second()], True, "asked_again", f"{TWO} · same amount, asked again"),
        # "other", a case file written before followed_by, or a value ops does not know: nothing is
        # said about what followed.
        ([_primary(), _second()], True, "other", f"{TWO} · same amount"),
        ([_primary(), _second()], False, "other", f"{TWO} · differ"),
        ([_primary(), _second()], True, _MISSING, f"{TWO} · same amount"),
        ([_primary(), _second()], False, _MISSING, f"{TWO} · differ"),
        ([_primary(), _second()], True, None, f"{TWO} · same amount"),
        ([_primary(), _second()], False, "repeated", f"{TWO} · differ"),
        ([_primary(), _second()], True, 7, f"{TWO} · same amount"),
        # One reading, or two not compared: what followed is never added.
        ([_primary()], None, "read_back", f"Prisma v3.0: {V3} · one reading"),
        ([_primary()], None, _MISSING, f"Prisma v3.0: {V3} · one reading"),
        # A second reading that failed: said so in words, and the closing still comes only from the
        # case file's readings_agreed (the dialogue takes a missing reading as a disagreement).
        (
            [_primary(), _second(text="", ok=False, error="timeout")],
            False,
            "asked_again",
            f"Prisma v3.0: {V3} · Prisma v2.5: no text (timeout) · differ, asked again",
        ),
        (
            [_primary(), _second(text=None)],
            False,
            "asked_again",
            f"Prisma v3.0: {V3} · Prisma v2.5: no text · differ, asked again",
        ),
        # Read twice with no agreement recorded: neither "same" nor "differ", whatever followed.
        (
            [_primary(), _second()],
            None,
            "read_back",
            f"{TWO} · two readings, not compared as amounts in the case file",
        ),
        (
            [_primary(), _second()],
            None,
            "asked_again",
            f"{TWO} · two readings, not compared as amounts in the case file",
        ),
    ],
    ids=[
        "same_read_back",
        "differ_asked_again",
        "differ_read_back",
        "same_asked_again",
        "same_other",
        "differ_other",
        "same_field_missing",
        "differ_field_missing",
        "same_field_null",
        "differ_unknown_value",
        "same_not_a_string",
        "one_reading_read_back",
        "one_reading",
        "second_failed",
        "second_null_text",
        "agreement_null_read_back",
        "agreement_null_asked_again",
    ],
)
def test_the_readings_line_beside_an_amount_quote(
    tmp_path: Path, readings, agreed, followed_by, expected
) -> None:
    view, _ = _readings(tmp_path, _turn(readings, agreed, followed_by))
    assert _line(view) == expected
    assert wording.banned_in(_line(view)) == []


def test_the_texts_are_the_case_files_byte_for_byte(tmp_path: Path) -> None:
    view, case = _readings(
        tmp_path, _turn([_second(), _primary()], True)
    )  # order in the file does not matter
    (turn,) = case["turns"]
    by_role = {r["role"]: r["text"] for r in turn["readings"]}
    assert [p.text.encode() for p in view.parts] == [by_role["primary"].encode(), by_role["second"].encode()]
    assert all(p.as_written for p in view.parts)
    assert [p.model for p in view.parts] == ["Prisma v3.0", "Prisma v2.5"]


def test_a_turn_the_case_file_does_not_list_and_a_case_file_without_readings_say_less(tmp_path: Path) -> None:
    other = _readings(
        tmp_path / "a", lambda tid: [{"turn_id": tid + 1000, "text": "x", "readings": [_primary()]}]
    )
    assert other[0] == ReadingsView(parts=(), closing=wording.READINGS_NONE_FOR_TURN)
    empty = _readings(tmp_path / "b", _turn([], None))
    assert empty[0] == ReadingsView(parts=(), closing=wording.READINGS_NONE_FOR_TURN)
    old = _readings(tmp_path / "c", lambda tid: [{"turn_id": tid, "text": V3}])  # written before readings
    assert old[0] == ReadingsView(parts=(), closing=wording.READINGS_NOT_KEPT)
    none = _readings(tmp_path / "d", None)  # no turns at all
    assert none[0] == ReadingsView(parts=(), closing=wording.READINGS_NOT_KEPT)


def test_a_simulated_call_says_it_is_a_text_call(tmp_path: Path) -> None:
    a = loan(1)
    who = customer(a, COMPLETED, concerns=(SaleConcern.coached_answers,), premium_inr=52_000)
    store = run_batch(tmp_path / "ops", [a], [who], DRAWN_ON)
    batch = load_batch(store)
    (s,) = batch.referrals
    view = case_view(batch, s.call.call_id)
    (line,) = [x for x in view.refer_lines if RuleId.premium in x.rule_ids]
    assert line.quote.readings == ReadingsView(parts=(), closing=wording.READINGS_TEXT_CALL)
    # A simulated call's saved file has no readings field: its bytes are as before.
    assert "readings" not in json.loads((store.root / "calls" / f"{s.call.call_id}.json").read_text())


def test_every_readings_string_passes_the_lint() -> None:
    strings = [v for k, v in vars(wording).items() if k.startswith("READINGS_")] + [wording.NO_GAP]
    assert len(strings) > 8 and [s for s in strings if wording.banned_in(s)] == []


# --- ingesting again ------------------------------------------------------------------------------


def _ingested(tmp_path: Path, followed_by=_MISSING) -> tuple[OpsStore, dict, Path]:
    a = loan(1)
    store, _ = open_batch(tmp_path / "ops", [a], DRAWN_ON)
    case, _ = _referred_premium(store, a, _turn([_primary(), _second()], True, followed_by))
    sessions = tmp_path / "sessions"
    put_case(sessions, case)
    assert ingest(store, sessions, nothing).linked == [case["session_id"]]
    return store, case, sessions


def test_a_second_ingest_changes_nothing(tmp_path: Path) -> None:
    store, case, sessions = _ingested(tmp_path)
    before = snapshot(store.root)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }


def test_a_call_brought_in_before_readings_were_kept_stays_as_it_is(tmp_path: Path) -> None:
    store, case, sessions = _ingested(tmp_path)
    path = store.root / "calls" / f"{case['session_id']}.json"
    saved = CallRecord.model_validate_json(path.read_text())
    path.write_text(saved.model_copy(update={"readings": None}).model_dump_json(indent=2) + "\n")
    before = snapshot(store.root)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    assert (
        snapshot(store.root)[str(path.relative_to(store.root))] == before[str(path.relative_to(store.root))]
    )
    view = case_view(load_batch(store), case["session_id"])
    (line,) = [x for x in view.refer_lines if RuleId.premium in x.rule_ids]
    assert line.quote.readings == ReadingsView(parts=(), closing=wording.READINGS_NOT_KEPT)


def _premium_readings(store: OpsStore, case: dict) -> ReadingsView:
    view = case_view(load_batch(store), case["session_id"])
    (line,) = [x for x in view.refer_lines if RuleId.premium in x.rule_ids]
    return line.quote.readings


def test_followed_by_is_kept_as_data_and_left_out_of_the_saved_call_when_missing(tmp_path: Path) -> None:
    store, case, _ = _ingested(tmp_path / "a", "read_back")
    saved = json.loads((store.root / "calls" / f"{case['session_id']}.json").read_text())
    assert [t["followed_by"] for t in saved["readings"]] == ["read_back"]
    for value in (_MISSING, "repeated"):  # missing, or a value ops does not know: stored as missing
        store, case, _ = _ingested(tmp_path / str(value is _MISSING), value)
        saved = json.loads((store.root / "calls" / f"{case['session_id']}.json").read_text())
        assert all("followed_by" not in t for t in saved["readings"])
        assert _premium_readings(store, case).closing == wording.READINGS_SAME


def test_a_second_ingest_with_followed_by_changes_nothing(tmp_path: Path) -> None:
    store, case, sessions = _ingested(tmp_path, "read_back")
    before = snapshot(store.root)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }


def test_a_call_brought_in_before_followed_by_existed_stays_as_it_is(tmp_path: Path) -> None:
    """The call was saved by the ingest of before (no followed_by on its turns); the case file now
    carries the field. The saved call counts as the same and is left byte for byte, and its line
    says only "same amount"."""
    store, case, sessions = _ingested(tmp_path, "read_back")
    path = store.root / "calls" / f"{case['session_id']}.json"
    raw = json.loads(path.read_text())
    for turn in raw["readings"]:
        del turn["followed_by"]
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    before = snapshot(store.root)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }
    assert _premium_readings(store, case).closing == wording.READINGS_SAME


def test_a_changed_followed_by_in_an_ingested_case_file_is_listed_as_changed_and_kept(tmp_path: Path) -> None:
    store, case, sessions = _ingested(tmp_path, "read_back")
    before = snapshot(store.root)
    case["turns"][0]["followed_by"] = "asked_again"
    put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    assert "analysed call differs" in dict(found.changed)[case["session_id"]]
    assert "readings" in dict(found.changed)[case["session_id"]]
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }


def test_a_changed_reading_in_an_ingested_case_file_is_listed_as_changed_and_kept(tmp_path: Path) -> None:
    store, case, sessions = _ingested(tmp_path)
    before = snapshot(store.root)
    case["turns"][0]["readings"][1]["text"] = "53 हज़ार"
    put_case(sessions, case)
    found = ingest(store, sessions, nothing)
    assert found.linked == [case["session_id"]] and found.skipped == []
    assert "analysed call differs" in dict(found.changed)[case["session_id"]]
    after = snapshot(store.root)
    assert {k: v for k, v in after.items() if k != "ingest.json"} == {
        k: v for k, v in before.items() if k != "ingest.json"
    }


# --- the report's tiles ---------------------------------------------------------------------------


def _assert_tiles_match_tables(store: OpsStore) -> None:
    r = build_report(store)
    t = r.tiles
    tier = {row.tier: row.value.count for row in r.tiers}
    stage = {row.key: row.value.count for row in r.funnel.stages}
    assert t.synthetic == r.batch.simulated_notice
    assert t.sold == r.sampling.sales_in_period
    assert t.sampled == r.sampling.sampled == r.funnel.sampled == r.batch.sampled
    assert t.completed == stage["completed"] == r.batch.completed
    assert t.referred == tier[Tier.refer] == r.batch.referred
    assert t.understanding_gap == tier[Tier.understanding_gap]
    most = max((row.understanding_gap for row in r.rules), default=0)
    assert t.most_common_gap_count == most
    if most:
        first = next(row for row in r.rules if row.understanding_gap == most)  # ties: higher in the table
        assert (t.most_common_gap.key, t.most_common_gap.label) == (first.rule_id.value, first.rule_label)
        assert most <= t.understanding_gap
    else:
        assert (t.most_common_gap.key, t.most_common_gap.label) == ("none", "none")
    assert wording.banned_in(t.model_dump_json()) == []


def test_the_tiles_equal_the_tables_on_the_demo_batch(store: OpsStore) -> None:
    _assert_tiles_match_tables(store)
    assert build_report(store).tiles.most_common_gap.key != "none"


def test_the_tiles_equal_the_tables_with_phone_attempts(tmp_path: Path) -> None:
    a, b, c = loan(1), loan(2), loan(3)
    store, _ = open_batch(tmp_path / "ops", [a, b, c], DRAWN_ON)
    sessions = tmp_path / "sessions"
    case, _ = _referred_premium(store, a, _turn([_primary(), _second()], True))
    put_case(sessions, case)
    gap = phone_case(
        store, b, customer(b, COMPLETED, term_months=36), DRAWN_ON, started=WALL + timedelta(hours=1)
    )
    put_case(sessions, gap)
    found = ingest(store, sessions, nothing)
    assert len(found.linked) == 2, found.skipped
    _assert_tiles_match_tables(store)
    t = build_report(store).tiles
    assert (t.sold, t.sampled, t.completed, t.referred) == (3, 3, 2, 1)


def test_the_most_common_gap_says_none_when_there_is_no_gap(tmp_path: Path) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [customer(a, COMPLETED)], DRAWN_ON)
    t = build_report(store).tiles
    assert (t.understanding_gap, t.most_common_gap.key, t.most_common_gap.label, t.most_common_gap_count) == (
        0,
        "none",
        "none",
        0,
    )
    _assert_tiles_match_tables(store)
