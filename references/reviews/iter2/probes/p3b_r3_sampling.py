"""P3b round 3: the sampling statement and intervals near the 1.25 boundary (claim 13), on books built
window by window so each draw's drawn / eligible is known in advance.

Usage: uv run python references/reviews/iter2/probes/p3b_r3_sampling.py <state dir>
Writes only under <state dir>.
"""

from __future__ import annotations

import math
import shutil
import sys
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import custom_batch  # noqa: E402
from p3b_r3_recount import recount  # noqa: E402

from samajh.ops import book as books  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS = []


def windows(spec: list[tuple[int, float]], gap: int = 9):
    """spec: (sales in the window, rate). Window k's sales are all on one day; its draw is 2 days later."""
    loans, draws = [], []
    day = date(2027, 1, 12)
    for k, (count, rate) in enumerate(spec):
        if count:
            _, made, _ = books.generate_book(500 + k, count, sold_from=day, days=1)
            loans += list(made)
        draws.append((day + timedelta(days=2), rate))
        day += timedelta(days=gap)
    return loans, draws


CASES = {
    "exactly 1.25 (4/5 vs 4/4)": [(5, 0.8), (4, 1.0)],
    "just over (7/9 vs 4/4 = 1.286)": [(9, 0.78), (4, 1.0)],
    "just under (9/11 vs 4/4 = 1.222)": [(11, 0.82), (4, 1.0)],
    "rate 1.0 alone, one draw": [(6, 1.0)],
    "one draw at 5% of 30": [(30, 0.05)],
    "a draw with nobody eligible between": [(5, 0.4), (0, 0.4), (4, 0.5)],
    "same rate 0.4, windows of 1 and 5": [(1, 0.4), (5, 0.4)],
    "same rate 0.4, windows of 2 and 5": [(2, 0.4), (5, 0.4)],
    "float edge 16/25 vs 4/5 (exactly 1.25)": [(25, 0.64), (5, 0.8)],
    "float edge 12/15 vs 16/20... 0.8 vs 0.64 reversed": [(5, 0.8), (25, 0.64)],
    "three draws 1/3, 2/5, 5/12": [(3, 0.4), (5, 0.4), (12, 0.4)],
}
for i, (name, spec) in enumerate(CASES.items()):
    loans, draws = windows(spec)
    st = STATE / f"c{i}"
    store, _ = custom_batch(st, loans, draws)
    rep = build_report(store)
    s = rep.sampling
    exact = [Fraction(len(d.drawn), len(d.eligible)) for d in store.draws() if d.eligible]
    true_ratio = max(exact) / min(exact) if exact else None
    narrow_true = true_ratio is not None and true_ratio <= Fraction(5, 4)
    print(f"{name}: inclusion {[str(x) for x in exact]} exact ratio {true_ratio} -> chances {s.chances}, intervals {s.intervals_shown}")
    print(f"    {s.statement[s.statement.find('overlap.') + 9:][:230]}")
    if exact and (s.chances == "narrow") != narrow_true:
        FAILS.append(f"{name}: exact ratio {true_ratio} but chances {s.chances} (float ratio {s.inclusion_ratio!r})")
    rows, bad = recount(st)
    for b in bad:
        FAILS.append(f"{name}: {b}")

# the comment's arithmetic behind 1.25
r = 1.25
bias = max(a - a / (a + r * (1 - a)) for a in (k / 100000 for k in range(1, 100000)))
kish = max((a + (1 - a) * r * r) * 1 / (a + (1 - a) * r) ** 2 for a in (k / 100000 for k in range(1, 100000)))
print(f"max unweighted bias factor at r=1.25: {bias:.5f} (comment: {(math.sqrt(r) - 1) / (math.sqrt(r) + 1):.5f}); "
      f"max Kish deff: {kish:.5f} (comment: {(1 + r) ** 2 / (4 * r):.5f}); interval widening {math.sqrt(kish) - 1:.4%}")
for f in FAILS:
    print("FAIL", f)
print("FAILURES:", len(FAILS))
