"""Small statistics: nearest-rank percentiles and counts per 100 with a Wilson interval."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from samajh.evalkit.score import wilson

NOT_LOGGED = "n/a (not logged)"


def p90(values: Sequence[float]) -> float:
    """Nearest-rank 90th percentile."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]


def spread(values: Sequence[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {"median": statistics.median(values), "p90": p90(values), "max": max(values), "n": len(values)}


def spread_cell(values: Sequence[float]) -> str:
    s = spread(values)
    if s is None:
        return f"{NOT_LOGGED} | | | 0"
    return f"{s['median']:.0f} | {s['p90']:.0f} | {s['max']:.0f} | {s['n']}"


def per100(k: int, n: int) -> str:
    if n == 0:
        return "n/a (n = 0)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f} per 100 ({k}/{n}; 95% CI {100 * lo:.0f}-{100 * hi:.0f})"
