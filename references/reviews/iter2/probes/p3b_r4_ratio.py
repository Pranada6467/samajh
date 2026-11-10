"""P3b round 4, claim 4: the 1.25 boundary on inclusion chances, against an exact Fraction oracle.

usage: uv run python references/reviews/iter2/probes/p3b_r4_ratio.py <state dir>
Writes only under <state dir>. No network.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tests" / "ops"))
from p3b_r3_kit import custom_batch  # noqa: E402
from opskit import loan  # noqa: E402

from samajh.ops.report import build_report  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []

# pairs (drawn, eligible) whose exact ratio is 5/4 but whose float division is not exactly 1.25
found = []
for e1 in range(3, 60):
    for d1 in range(1, e1 + 1):
        for e2 in range(3, 60):
            for d2 in range(1, e2 + 1):
                hi, lo = Fraction(d1, e1), Fraction(d2, e2)
                if hi == Fraction(5, 4) * lo and (d1 / e1) / (d2 / e2) != 1.25:
                    if hi.denominator == e1 and lo.denominator == e2:  # irreducible, new shapes
                        found.append(((d1, e1), (d2, e2)))
print(f"{len(found)} irreducible exact-5/4 pairs with float ratio != 1.25; using a spread of them")
picks = found[:: max(1, len(found) // 6)][:6]

schedules: list[tuple[str, list[tuple[int, int]]]] = []
for (a, b) in picks:
    schedules.append((f"exact {a[0]}/{a[1]} vs {b[0]}/{b[1]}", [a, b]))
# just above / just below, non-exact floats
schedules += [
    ("above 41/110 vs 7/15", [(7, 15), (41, 110)]),
    ("below 57/152 vs 7/15", [(7, 15), (57, 152)]),
    ("above 13/35 vs 7/15 (ratio 49/39)", [(7, 15), (13, 35)]),
    ("below 3/8 vs 7/15 (ratio 56/45)", [(7, 15), (3, 8)]),
    ("three draws, extremes exact 5/4 (5/12, 2/5... no: 5/12 1/3 3/8)", [(5, 12), (1, 3), (3, 8)]),
    ("three draws, 11/30 22/75 1/3", [(11, 30), (22, 75), (1, 3)]),
    ("exact 1.25 + one just above 1/3 5/12 31/74", [(1, 3), (5, 12), (31, 74)]),
]


def build(tag: str, sched: list[tuple[int, int]]):
    loans_ = []
    draws = []
    serial = 1
    day0 = date(2027, 1, 20)
    for k, (dr, el) in enumerate(sched):
        as_of = day0 + timedelta(days=20 * k)
        sold = as_of - timedelta(days=4)
        for _ in range(el):
            loans_.append(loan(serial, sold_on=sold))
            serial += 1
        draws.append((as_of, dr / el))
    store, meta = custom_batch(STATE / tag.replace(" ", "_").replace("/", "-")[:60], loans_, draws, seed=99)
    return store


for tag, sched in schedules:
    store = build(tag, sched)
    rates = [Fraction(len(d.drawn), len(d.eligible)) for d in store.draws() if d.eligible]
    got = [(len(d.drawn), len(d.eligible)) for d in store.draws()]
    if got != sched:
        FAILS.append(f"[{tag}] draws came out {got}, wanted {sched}")
    lo, hi = min(rates), max(rates)
    want = "narrow" if hi <= Fraction(5, 4) * lo else "wide"
    rep = build_report(store)
    s = rep.sampling
    js = rep.model_dump(mode="json")
    intervals = []

    def walk(x, path=""):
        if isinstance(x, dict):
            if {"count", "n", "share", "low", "high"} <= set(x) and (x["low"] is not None or x["high"] is not None):
                intervals.append(path)
            for k, v in x.items():
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")

    walk(js)
    same = "about the same chance" in s.statement
    ok = (s.chances == want and s.intervals_shown == (want == "narrow") and same == (want == "narrow")
          and (want == "narrow" or not intervals) and (want == "wide" or intervals))
    print(f"[{tag}] exact {hi}/{lo} = {hi / lo} -> want {want}; got chances={s.chances} shown={s.intervals_shown} "
          f"same-chance-words={same} intervals={len(intervals)} ratio_float={s.inclusion_ratio!r}")
    if not ok:
        FAILS.append(f"[{tag}] wrong: {s.chances}, shown {s.intervals_shown}, words {same}, intervals {len(intervals)}; "
                     f"statement: {s.statement[:300]}")
    if want == "wide" and "interval" in json.dumps(js["limits"]).lower() and "No interval is given" not in " ".join(js["limits"]):
        FAILS.append(f"[{tag}] wide report limits speak of intervals: {js['limits']}")
    if want == "narrow" and "1.25 times" in s.statement and "differed" in s.statement:
        FAILS.append(f"[{tag}] narrow but statement says differed")

print(f"schedules: {len(schedules)}")
print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x)
