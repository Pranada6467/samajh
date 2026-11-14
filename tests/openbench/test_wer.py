"""Behaviour of eval/openbench/wer.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "eval" / "openbench" / "wer.py"
_spec = importlib.util.spec_from_file_location("openbench_wer", _PATH)
wer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wer)


def test_normalise_removes_danda_and_punctuation():
    assert wer.normalise("राम घर गया। फिर, वह  आया॥ Hello!") == "राम घर गया फिर वह आया hello"
    assert wer.normalise("₹500 + 2") == "500 2"


def test_identical_strings_score_zero():
    for t in wer.TREATMENTS:
        assert wer.word_counts("एक दो तीन", "एक दो तीन", t) == (0, 3)
        assert wer.char_counts("एक दो", "एक दो", t)[0] == 0


def test_single_edits():
    assert wer.word_counts("a b c", "a x c", "raw") == (1, 3)
    assert wer.word_counts("a b c", "a b c d", "raw") == (1, 3)
    assert wer.word_counts("a b c", "a c", "raw") == (1, 3)
    assert wer.word_counts("a b c", "", "raw") == (3, 3)


def test_raw_keeps_punctuation_norm_drops_it():
    assert wer.word_counts("गया।", "गया", "raw") == (1, 1)
    assert wer.word_counts("गया।", "गया", "norm") == (0, 1)


def test_cer_ignores_spaces():
    assert wer.char_counts("ab cd", "abcd", "raw") == (0, 4)
    assert wer.char_counts("ab cd", "ab  xd", "norm") == (1, 4)


def test_bootstrap_contains_point_and_is_deterministic():
    edits = [0, 1, 3, 2, 0, 5, 1, 0, 2, 1]
    lens = [5, 6, 7, 4, 8, 9, 5, 6, 7, 5]
    a = wer.bootstrap(edits, lens)
    assert a == wer.bootstrap(edits, lens)
    point, lo, hi = a
    assert point == sum(edits) / sum(lens)
    assert lo <= point <= hi and lo < hi
    assert wer.bootstrap(edits, lens, seed=1) != a
