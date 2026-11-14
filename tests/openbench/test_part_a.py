"""Behaviour of W7 Part A's outcome classification and acceptance schemes, on toy clips."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "openbench"))
sys.path.insert(0, str(ROOT / "eval" / "amounts_v2"))
_spec = importlib.util.spec_from_file_location("w7_part_a", ROOT / "eval" / "openbench" / "part_a.py")
part_a = importlib.util.module_from_spec(_spec)
sys.modules["w7_part_a"] = part_a
_spec.loader.exec_module(part_a)

O = "indicconformer-rnnt"


@pytest.fixture(scope="module")
def amounts():
    from frozen_parser import load

    return load()


def test_outcome_classification(amounts):
    assert part_a.read("तीन लाख चालीस हज़ार रुपये", 340000, amounts).outcome == "right"
    wrong = part_a.read("तीन लाख चालीस हज़ार रुपये", 300040, amounts)
    assert (wrong.outcome, wrong.amount) == ("wrong", 340000)
    assert part_a.read("मुझे नहीं पता", 340000, amounts).outcome == "no amount"
    assert part_a.read(None, 340000, amounts).outcome == "missing"


def clip(gold: int, **amounts_by_system: int | None) -> part_a.Clip:
    readings = {
        s: part_a.Reading("no amount" if v is None else ("right" if v == gold else "wrong"), v)
        for s, v in amounts_by_system.items()
    }
    return part_a.Clip("x", "phone", gold, {}, "sha", readings)


def run(c: part_a.Clip) -> list[int | None]:
    return [rule(c) for rule in part_a.schemes(O).values()]


def test_schemes_three_different_amounts_reask_everywhere():
    c = clip(100, **{part_a.T3: 1, part_a.T25: 2, O: 3})
    assert run(c) == [None, None, None, None]


def test_two_agree_third_none():
    c = clip(5)
    c.readings.update(
        {
            part_a.T3: part_a.Reading("right", 5),
            part_a.T25: part_a.Reading("right", 5),
            O: part_a.Reading("no amount", None),
        }
    )
    ref, unanimous, majority, swap = run(c)
    assert (ref, unanimous, majority, swap) == (5, None, 5, None)


def test_majority_outvotes_wrong_v3_and_swap_accepts():
    c = clip(300200)
    c.readings.update(
        {
            part_a.T3: part_a.Reading("wrong", 302000),
            part_a.T25: part_a.Reading("right", 300200),
            O: part_a.Reading("right", 300200),
        }
    )
    assert run(c) == [None, None, 300200, 300200]


def test_ambiguous_and_missing_never_accepted():
    c = clip(7)
    c.readings.update(
        {
            part_a.T3: part_a.Reading("right", 7),
            part_a.T25: part_a.Reading("ambiguous", None),
            O: part_a.Reading("missing", None),
        }
    )
    assert run(c) == [None, None, None, None]


def test_accept_counts_wrong_and_reasks():
    wrong_agree = clip(10)
    wrong_agree.readings.update(
        {part_a.T3: part_a.Reading("wrong", 9), part_a.T25: part_a.Reading("wrong", 9)}
    )
    right_agree = clip(10)
    right_agree.readings.update(
        {part_a.T3: part_a.Reading("right", 10), part_a.T25: part_a.Reading("right", 10)}
    )
    split = clip(10)
    split.readings.update({part_a.T3: part_a.Reading("right", 10), part_a.T25: part_a.Reading("wrong", 9)})
    ref = part_a.schemes(O)["1 reference: v3.0 T = v2.5 T"]
    a = part_a.accept([wrong_agree, right_agree, split], ref)
    assert (a.n, a.accepted, a.wrong, a.reasks) == (3, 2, 1, 1)
