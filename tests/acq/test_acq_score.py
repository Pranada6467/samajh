"""The ACQ scorer on hand-made call files, against hand-computed counts."""

from __future__ import annotations

import json

from acq_common import FIELDS
from acq_score import markdown, score


def _open(cid, kind, status="ok", tier=None, outcome="completed", flags=(), variant="own", reason="x_differs"):
    """Each flag (tier, field) quotes a reply played as `variant`."""
    turns = [{"reply": {"text": f"मैंने कहा  {f} बात", "variant": variant}, "variant": variant} for _, f in flags]
    return {"customer_id": cid, "arm": "open", "a": 0.0, "kind": kind, "status": status, "tier": tier,
            "outcome": outcome, "turns": turns,
            "flags": [{"tier": t, "field": f, "reason": reason, "quote": f"कहा {f} बात"} for t, f in flags]}


def _closed(cid, kind, answers: dict[str, str]):
    ans = [{"field": f, "answer": answers.get(f, "yes")} for f in FIELDS]
    strict = [x["field"] for x in ans if x["answer"] != "yes"]
    lenient = [x["field"] for x in ans if x["answer"] == "no"]
    return {"customer_id": cid, "arm": "closed", "r": 0.0, "a": 0.0, "kind": kind, "status": "ok", "answers": ans,
            "outcome_strict": "caught" if strict else "confirmed", "caught_fields_strict": strict,
            "outcome_lenient": "caught" if lenient else "confirmed", "caught_fields_lenient": lenient}


def _run(tmp_path):
    calls = tmp_path / "calls"
    calls.mkdir()
    rows = [
        _open("ACQ-C007", "misled", tier="refer", flags=[("refer", "required")]),
        _closed("ACQ-C007", "misled", {"required": "no"}),
        _open("ACQ-C016", "misled", tier="clear"),
        _closed("ACQ-C016", "misled", {"kind": "no"}),
        _open("ACQ-C030", "misled", status="entry_failed"),
        _closed("ACQ-C030", "misled", {}),
        _open("ACQ-C006", "knowledge_gap", tier="understanding_gap", flags=[("understanding_gap", "premium")]),
        _closed("ACQ-C006", "knowledge_gap", {"premium": "dont_know"}),
        _open("ACQ-C001", "informed", tier="incomplete"),
        _closed("ACQ-C001", "informed", {}),
    ]
    for i, row in enumerate(rows):
        (calls / f"{i}.json").write_text(json.dumps(row))
    return score(tmp_path)


def test_counts_and_mcnemar(tmp_path):
    s = _run(tmp_path)
    cell = s["cells"]["r=0,a=0"]
    m = cell["kind=misled"]
    assert m["n"] == 2 and m["excluded"]["entry_failed"] == 1
    k = {name: v["k"] for name, v in m["metrics"].items()}
    assert k["open.refer"] == 1 and k["open.refer_ground"] == 1 and k["open.clear"] == 1
    assert k["open.miss"] == 1 and k["open.silent_miss"] == 1
    assert k["closed.strict_caught"] == 2 and k["closed.strict_caught_ground"] == 2  # C016 ground holds kind
    assert k["closed.strict_confirmed"] == 0 and k["closed.lenient_caught"] == 2
    p2a = m["mcnemar"]["P2a:refer_ground~strict_caught_ground"]
    assert (p2a["b_open_only"], p2a["c_closed_only"], p2a["both"], p2a["neither"]) == (0, 1, 1, 0)
    p3 = m["mcnemar"]["P3:not_clear~strict_caught"]
    assert (p3["b_open_only"], p3["c_closed_only"], p3["both"], p3["p"]) == (0, 1, 1, 1.0)
    assert m["metrics"]["open.refer"]["per100"] == 50.0

    kg = cell["kind=knowledge_gap"]
    assert kg["metrics"]["open.gap_found"]["k"] == 1 and kg["metrics"]["closed.strict_gap_found"]["k"] == 1
    assert kg["metrics"]["closed.lenient_gap_found"]["k"] == 0
    assert kg["mcnemar"]["P1:gap_found~strict_gap_found"]["both"] == 1

    inf = cell["kind=informed"]
    assert inf["metrics"]["open.incomplete"]["k"] == 1 and inf["metrics"]["closed.strict_caught"]["k"] == 0
    assert inf["metrics"]["open.not_clear"]["k"] == 1 and inf["mcnemar"] == {}

    assert cell["class=problem"]["n"] == 2 and cell["class=problem"]["excluded"]["missing_open"] == 77


def test_markdown_has_no_difference_line(tmp_path):
    md = markdown(_run(tmp_path))
    assert "entry_failed 1" in md and "per 100" in md
    assert "minus" not in md.lower() and "difference" not in md.lower()


def _score_rows(tmp_path, rows):
    calls = tmp_path / "calls"
    calls.mkdir()
    for i, row in enumerate(rows):
        (calls / f"{i}.json").write_text(json.dumps(row))
    return score(tmp_path)["cells"]["r=0,a=0"]


def test_flag_from_a_defer_reply_does_not_count(tmp_path):
    cell = _score_rows(tmp_path, [
        _open("ACQ-C007", "misled", tier="refer", flags=[("refer", "required")], variant="defer"),
        _closed("ACQ-C007", "misled", {"required": "no"}),
        _open("ACQ-C006", "knowledge_gap", tier="incomplete", flags=[("understanding_gap", "premium")]),
        _closed("ACQ-C006", "knowledge_gap", {}),
    ])
    m = cell["kind=misled"]["metrics"]
    assert m["open.refer_ground"]["k"] == 0 and m["open.refer_ground_any_source"]["k"] == 1
    kg = cell["kind=knowledge_gap"]["metrics"]
    assert kg["open.gap_found"]["k"] == 0 and kg["open.gap_flag_any_tier"]["k"] == 1


def test_dont_know_on_a_false_field_does_not_count(tmp_path):
    cell = _score_rows(tmp_path, [
        _open("ACQ-C007", "misled", tier="refer", flags=[("refer", "required")], reason="bundled_dont_know"),
        _closed("ACQ-C007", "misled", {}),
    ])
    assert cell["kind=misled"]["metrics"]["open.refer_ground"]["k"] == 0


def test_ended_early_split_and_incomplete_refusal(tmp_path):
    cell = _score_rows(tmp_path, [_open("ACQ-C001", "informed", tier="incomplete", outcome="declined"),
                                  _closed("ACQ-C001", "informed", {})])
    m = cell["kind=informed"]["metrics"]
    assert m["open.ended_early.declined"]["k"] == 1 and m["open.not_clear"]["k"] == 1
    assert cell["kind=informed"]["mcnemar"] == {}
    (tmp_path / "manifest.json").write_text(json.dumps([{"plan": [["ACQ-C001", 0.0], ["ACQ-C005", 0.0]]}]))
    from acq_score import main
    assert main([str(tmp_path)]) == 1
    assert main([str(tmp_path), "--allow-incomplete", "--out", str(tmp_path / "t.md")]) == 0
    md = (tmp_path / "t.md").read_text()
    assert "INCOMPLETE RUN" in md and "cell over the exclusion limit" not in md


def test_primary_marking(tmp_path):
    s = _run(tmp_path)
    assert s["cells"]["r=0,a=0"]["kind=misled"]["mcnemar"]["P2a:refer_ground~strict_caught_ground"]["primary"]
    assert not s["cells"]["r=0,a=0"]["kind=knowledge_gap"]["mcnemar"]["P1:gap_found~strict_gap_found"]["primary"]
    assert "descriptive, not a test" in markdown(s)
