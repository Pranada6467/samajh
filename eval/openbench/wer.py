"""WER and CER for Part B (FLEURS). Standard library only.

`normalise` is the only text treatment besides `raw`: NFC, lower-case, every Unicode punctuation (P*) or
symbol (S*) character, danda included, to a space, whitespace collapsed. Numbers are not converted and
nukta is not folded.
"""

from __future__ import annotations

import random
import unicodedata
from collections.abc import Sequence

TREATMENTS = ("raw", "norm")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in text)
    return " ".join(text.split())


def edit_distance(ref: Sequence, hyp: Sequence) -> int:
    """Levenshtein distance (unit costs) between two sequences."""
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def _prepare(text: str, treatment: str) -> str:
    if treatment == "raw":
        return text
    if treatment == "norm":
        return normalise(text)
    raise ValueError(f"unknown treatment {treatment!r}")


def word_counts(ref: str, hyp: str, treatment: str) -> tuple[int, int]:
    """(word edits, reference words)."""
    r, h = _prepare(ref, treatment).split(), _prepare(hyp, treatment).split()
    return edit_distance(r, h), len(r)


def char_counts(ref: str, hyp: str, treatment: str) -> tuple[int, int]:
    """(character edits, reference characters), all whitespace removed first."""
    r = "".join(_prepare(ref, treatment).split())
    h = "".join(_prepare(hyp, treatment).split())
    return edit_distance(r, h), len(r)


def corpus_rate(edits: Sequence[int], ref_lens: Sequence[int]) -> float:
    total = sum(ref_lens)
    return sum(edits) / total if total else float("nan")


def bootstrap(
    edits: Sequence[int], ref_lens: Sequence[int], reps: int = 2000, seed: int = 20261114
) -> tuple[float, float, float]:
    """(corpus rate, 2.5th, 97.5th percentile) over utterance resamples."""
    if len(edits) != len(ref_lens):
        raise ValueError("edits and ref_lens differ in length")
    point = corpus_rate(edits, ref_lens)
    n = len(edits)
    if n == 0:
        return point, point, point
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        e = sum(edits[i] for i in idx)
        t = sum(ref_lens[i] for i in idx)
        stats.append(e / t if t else 0.0)
    stats.sort()
    lo = stats[int(0.025 * (reps - 1))]
    hi = stats[round(0.975 * (reps - 1))]
    return point, lo, hi
