"""Recompute every `k/n (p%, lo-hi)` cell printed in eval/amounts/REPORT.md with an independent Wilson
(solved by bisection on the score-test equation, not the closed form). Offline.

  uv run python references/reviews/iter1/probes/amounts_wilson_all.py
"""

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
Z = 1.959963984540054


def bound(k: int, n: int, upper: bool) -> float:
    """Root of (phat - p)^2 = z^2 p (1 - p) / n on the chosen side of phat."""
    phat = k / n

    def f(p: float) -> float:
        return (phat - p) ** 2 - Z * Z * p * (1 - p) / n

    lo, hi = (phat, 1.0) if upper else (0.0, phat)
    if (upper and k == n) or (not upper and k == 0):
        return phat
    for _ in range(200):
        mid = (lo + hi) / 2
        inside = f(mid) < 0
        if upper:
            lo, hi = (mid, hi) if inside else (lo, mid)
        else:
            lo, hi = (lo, mid) if inside else (mid, hi)
    return (lo + hi) / 2


text = (ROOT / "eval/amounts/REPORT.md").read_text(encoding="utf-8")
cells = re.findall(r"(\d+)/(\d+) \((\d+)%, (\d+)-(\d+)\)", text)
bad = []
for k, n, p, lo, hi in cells:
    k, n = int(k), int(n)
    want = (round(100 * k / n), round(100 * bound(k, n, False)), round(100 * bound(k, n, True)))
    got = (int(p), int(lo), int(hi))
    # Python formats with round-half-even on the binary value; allow that on exact .5 only
    if got != want:
        bad.append((k, n, got, want))
print(f"cells of the form k/n (p%, lo-hi) in REPORT.md: {len(cells)}; distinct (k, n): {len({(c[0], c[1]) for c in cells})}; differing from my Wilson: {len(bad)}")
for row in bad[:20]:
    print("  ", row)
prose = re.findall(r"(\d+) of (\d+) \((\d+)%, (\d+)-(\d+)\)", text)
for k, n, p, lo, hi in prose:
    k, n = int(k), int(n)
    want = (round(100 * k / n), round(100 * bound(k, n, False)), round(100 * bound(k, n, True)))
    print(f"  prose: {k} of {n} ({p}%, {lo}-{hi}) -> mine {want} {'OK' if want == (int(p), int(lo), int(hi)) else 'DIFFERS'}")
shown_100 = sorted({(int(k), int(n)) for k, n, p, lo, hi in cells if int(p) == 100 and int(k) != int(n)})
print("cells printed as 100% that are not k == n:", shown_100)
