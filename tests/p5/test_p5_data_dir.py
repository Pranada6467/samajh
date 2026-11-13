"""`--data DIR`: the harness reads a second frozen set from its own directory; the default stays data/p5."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from bank import (
    P5,
    FrozenMismatch,
    check_frozen,
    harness_hashes,
    load_customers,
    load_record,
    load_topics,
    records_digest,
    resolve_data,
)

SOURCE = "P5-C029"  # a completed-call customer whose rows seed the fixture
NEW_ID, NEW_NAME = "P5B-T001", "Fixturelal Udaharan"


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def data(tmp_path: Path) -> Path:
    """A one-customer set in the data/p5 layout, with its own id, record name and disposition seed."""
    d = tmp_path / "p5b"
    (d / "records").mkdir(parents=True)
    for name in ("customers.jsonl", "gold.jsonl", "replies.jsonl", "closed_statements.jsonl"):
        rows = [dict(r, id=NEW_ID) for r in _rows(P5 / name) if r["id"] == SOURCE]
        _write(d / name, rows)
    record_id = _rows(d / "customers.jsonl")[0]["record_id"]
    record = json.loads((P5 / "records" / f"{record_id}.json").read_text(encoding="utf-8"))
    record["record"]["borrower"]["name"] = NEW_NAME
    (d / "records" / f"{record_id}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    topics = json.loads((P5 / "topics.json").read_text(encoding="utf-8"))
    topics["disposition"]["seed"] = "fixture-seed"
    (d / "topics.json").write_text(json.dumps(topics, ensure_ascii=False), encoding="utf-8")
    (d / "closed_script.json").write_text("{}", encoding="utf-8")

    def h(name: str) -> str:
        return hashlib.sha256((d / name).read_bytes()).hexdigest()

    frozen = {
        "inputs": {n: h(n) for n in ("customers.jsonl", "gold.jsonl", "topics.json", "closed_script.json")}
        | {"records": records_digest(d / "records")},
        "words": {n: h(n) for n in ("replies.jsonl", "closed_statements.jsonl")},
        "other": {},
    }
    (d / "FROZEN.json").write_text(json.dumps(frozen), encoding="utf-8")
    return d


def test_the_default_is_data_p5() -> None:
    assert resolve_data(None) == resolve_data("data/p5") == P5
    customers = load_customers()
    assert len(customers) == 60 and {c.data_dir for c in customers.values()} == {P5}
    assert load_topics().seed == "samajh-p5-2026-11-10"


def test_every_loader_reads_the_given_directory(data: Path) -> None:
    check_frozen(data)
    customers = load_customers(data)
    assert list(customers) == [NEW_ID] and customers[NEW_ID].data_dir == data
    assert load_topics(data).seed == "fixture-seed"
    record = load_record(customers[NEW_ID].record_id, customers[NEW_ID].data_dir)
    assert record.record.borrower.name == NEW_NAME


def test_the_frozen_check_uses_the_directorys_own_digests(data: Path) -> None:
    (data / "replies.jsonl").write_text("edited\n", encoding="utf-8")
    with pytest.raises(FrozenMismatch, match="replies.jsonl"):
        check_frozen(data)


def test_a_text_call_uses_the_directorys_record(data: Path) -> None:
    from text_run import run_open

    from samajh.dialogue import RuleInterpreter

    def no_extraction(*_args, **_kwargs):
        raise RuntimeError("not in this test")

    customer = load_customers(data)[NEW_ID]
    call = run_open(customer, load_topics(data), 0.0, "disposition", RuleInterpreter(), None, no_extraction)
    first_line = call["turns"][0]["bot"][0]
    assert first_line["key"] == "right_party.ask" and "Fixturelal" in first_line["text"]


def test_run_refuses_on_the_given_directorys_frozen_file(data: Path, tmp_path: Path) -> None:
    # eval/text_path/run.py is also importable as `run` (tests/extract puts it on sys.path), so load ours
    # by path under its own name.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p5_run", Path(__file__).resolve().parents[2] / "eval" / "p5" / "run.py"
    )
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)

    (data / "gold.jsonl").write_text("edited\n", encoding="utf-8")
    with pytest.raises(FrozenMismatch, match="gold.jsonl"):
        run.main(["--out", str(tmp_path / "out"), "--data", str(data), "--usd-budget", "0"])


def test_score_takes_gold_from_the_given_directory(data: Path, tmp_path: Path) -> None:
    import score

    run_dir = tmp_path / "run"
    (run_dir / "calls").mkdir(parents=True)
    call = {"customer_id": NEW_ID, "arm": "open", "condition": "disposition", "level": 0.0, "status": "ok",
            "tier": "refer", "outcome": "completed", "referral_basis": "customer_statement", "writer_model": "w",
            "turns": [], "final_bot": [], "unmapped": [], "degraded_turns": 0, "errors": []}  # fmt: skip
    (run_dir / "calls" / "c.json").write_text(json.dumps(call), encoding="utf-8")
    score.main([str(run_dir), "--data", str(data)])
    result = json.loads((run_dir / "score.json").read_text(encoding="utf-8"))
    assert result["inputs"]["gold"] == str(data / "gold.jsonl")
    assert result["inputs"]["harness_sha256"] == harness_hashes()
    assert result["referrals"][0]["referred"] == 1  # the fixture's gold (no_problem) was used


def test_voice_rule_and_records_follow_the_directory(data: Path) -> None:
    import serve
    from voices import assign_voices

    assert set(assign_voices(load_customers(data))) == {NEW_ID}
    record_id = load_customers(data)[NEW_ID].record_id
    assert serve.p5_records(data / "records").get(record_id).record.borrower.name == NEW_NAME
