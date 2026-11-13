"""The frozen-hash gate and the disposition draw."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from bank import FrozenMismatch, check_frozen, draw, gives_way, records_digest


def test_the_frozen_p5_set_matches_its_digests() -> None:
    check_frozen()  # raises on any mismatch


def _fake_set(tmp_path: Path) -> Path:
    p5 = tmp_path / "data" / "p5"
    (p5 / "records").mkdir(parents=True)
    (p5 / "records" / "r1.json").write_text("{}")
    (p5 / "replies.jsonl").write_text('{"id": "x"}\n')
    (p5 / "build.py").write_text("print(1)\n")
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / "rules.md").write_text("rules\n")

    def h(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    frozen = {
        "inputs": {"records": records_digest(p5 / "records")},
        "words": {"replies.jsonl": h(p5 / "replies.jsonl")},
        "other": {"build.py": h(p5 / "build.py"), "eval/rules.md": h(tmp_path / "eval" / "rules.md")},
    }
    (p5 / "FROZEN.json").write_text(json.dumps(frozen))
    return p5


@pytest.mark.parametrize("change", ["data/p5/replies.jsonl", "data/p5/records/r1.json", "eval/rules.md"])
def test_any_changed_file_stops_the_run(tmp_path: Path, change: str) -> None:
    p5 = _fake_set(tmp_path)
    check_frozen(p5, tmp_path)
    (tmp_path / change).write_text("edited\n")
    with pytest.raises(FrozenMismatch, match="records" if "records" in change else Path(change).name):
        check_frozen(p5, tmp_path)


def test_a_missing_file_stops_the_run(tmp_path: Path) -> None:
    p5 = _fake_set(tmp_path)
    (p5 / "build.py").unlink()
    with pytest.raises(FrozenMismatch):
        check_frozen(p5, tmp_path)


def test_the_draw_is_fixed_and_shared_by_level() -> None:
    u = draw("seed", "P5-C001", "premium")
    assert u == draw("seed", "P5-C001", "premium") and 0 <= u < 1
    assert not gives_way("seed", "P5-C001", "premium", 0.0)
    assert gives_way("seed", "P5-C001", "premium", 1.0)
    assert not gives_way("seed", "P5-C001", None, 1.0)  # an ungrouped topic never gives way
    assert gives_way("seed", "P5-C001", "premium", 0.5) == (u < 0.5)
