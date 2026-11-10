"""P3b round 3: read the rendered review pages (text dumped from headless Chrome) for the readings
line, the tiles, junk values and banned words (claims 12, 15, 16, 18).

Usage: uv run python references/reviews/iter2/probes/p3b_r3_pages.py <state dir> <dir of page .txt dumps>
The dumps come from a review-only server over <state dir> (see the report for the commands).
Reads only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.wording import banned_in  # noqa: E402

state, pages = Path(sys.argv[1]), Path(sys.argv[2])
FAILS = []
texts = {p.stem: p.read_text() for p in sorted(pages.glob("*.txt"))}
for name, t in texts.items():
    if banned_in(t):
        FAILS.append(f"{name}: banned {banned_in(t)}")
    for m in re.finditer(r"\b(undefined|NaN|null)\b|\(\s*\)|\[\s*\]", t):
        FAILS.append(f"{name}: junk {m.group(0)!r} near {t[max(0, m.start() - 40):m.end() + 20]!r}")
    for m in re.finditer(r"(?i)\bfinding", t):
        FAILS.append(f"{name}: 'finding' near {t[max(0, m.start() - 40):m.end() + 20]!r}")
for p in sorted(pages.glob("*.html")):
    h = p.read_text()
    # visible attributes too (title, aria-label, alt)
    for m in re.finditer(r'(?:title|aria-label|alt|placeholder)="([^"]*)"', h):
        if banned_in(m.group(1)):
            FAILS.append(f"{p.name}: banned in attribute {m.group(1)[:80]!r}")

exp_path = state / "expected_lines.json"
checked = 0
if exp_path.exists():
    for sid, lines in json.loads(exp_path.read_text()).items():
        t = texts.get(f"case-{sid}")
        if t is None:
            FAILS.append(f"no rendered case page for {sid}")
            continue
        for line in lines:
            checked += 1
            # innerText collapses runs of white space inside inline text only when CSS says so; compare both
            if line not in t and re.sub(r"\s+", " ", line) not in re.sub(r"\s+", " ", t):
                FAILS.append(f"case {sid}: readings line not rendered as the view gives it: {line[:120]!r}")
            elif line not in t:
                print(f"  note: {sid} line matches only with white space collapsed: {line[:90]!r}")
print(f"readings lines compared on rendered pages: {checked}")

rep = build_report(OpsStore(state / "ops"))
t = texts.get("report", "")
tiles = rep.tiles
head = t[: t.find("Sampling")] if "Sampling" in t else t[:3000]
want = [
    ("Sold in the period", tiles.sold),
    ("Sampled", tiles.sampled),
    ("Completed within 30 days", tiles.completed),
    ("Referred", tiles.referred),
    ("Understanding gap", tiles.understanding_gap),
]
for label, value in want:
    m = re.search(re.escape(label) + r"\s*\n\s*([\d,]+)", head)
    if not m or int(m.group(1).replace(",", "")) != value:
        FAILS.append(f"tile {label}: page {m.group(1) if m else None} vs report {value}")
if tiles.synthetic not in t:
    FAILS.append("synthetic label missing from the tile strip")
if tiles.most_common_gap.label not in head:
    FAILS.append(f"most common gap label {tiles.most_common_gap.label!r} missing")
print(f"tiles: sold {tiles.sold}, sampled {tiles.sampled}, completed {tiles.completed}, referred {tiles.referred}, "
      f"gap {tiles.understanding_gap}, most common {tiles.most_common_gap.label!r} ({tiles.most_common_gap_count})")
if not rep.sampling.intervals_shown and re.search(r"95% interval \d", t):
    FAILS.append("report page shows an interval while the report withholds them")
for f in FAILS:
    print("FAIL", f)
print(f"pages read: {len(texts)}; FAILURES: {len(FAILS)}")
