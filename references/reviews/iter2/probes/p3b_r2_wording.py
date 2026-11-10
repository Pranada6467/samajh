"""P3b re-verification (round 2): every reviewer-facing string, read for wording that implies a finding,
a refund, mis-selling, a statistical interval on reviewer decisions, or a claim about a real lender.

Usage: uv run python references/reviews/iter2/probes/p3b_r2_wording.py <views dir> [<views dir> ...]

Reads every string value in the JSON views (batch, queue, every case page, attempt log, report) that
p3b_r2_ingest.py dumped, plus the string literals of web/review/*.js and *.html. Prints, per pattern,
the number of distinct strings that match and up to three examples. Also checks that no reviewer
decision count in a report carries an interval.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from samajh.ops.wording import banned_in

ROOT = Path(__file__).resolve().parents[4]
EXTRA = {
    "finding": r"\bfinding",
    "establish": r"\bestablish",
    "interval": r"\binterval",
    "confidence": r"\bconfiden",
    "penalty/liable": r"\bpenalt|\bliab",
    "wrongdoing/fault": r"wrongdo|\bfault",
    "complaint": r"complain",
    "compensation/money back": r"compensat|money back|get .* back",
    "prove/proof": r"\bprove|\bproof",
    "real lender/customer": r"\breal (lender|customer|borrower|call)",
    "rate": r"\brate\b",
}


def strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


found_banned = defaultdict(set)
found_extra = defaultdict(set)
SKIP_KEYS = (".text", ".quote", ".note", ".reviewer")  # customer speech and reviewer free text
for d in sys.argv[1:]:
    for f in sorted(Path(d).glob("*.json")):
        data = json.loads(f.read_text())
        for path, s in strings(data):
            if path.endswith(SKIP_KEYS) or path.endswith("_id") or path.endswith("sha256"):
                continue
            for p in banned_in(s):
                found_banned[p].add((f.name, path.split("[")[0], s[:140]))
            for name, p in EXTRA.items():
                if re.search(p, s, re.IGNORECASE):
                    found_extra[name].add(s[:160])
        if f.name == "report.json":
            for key in ("referrals",):
                for row in data[key]:
                    if set(row["value"]) - {"count", "n"}:
                        print("INTERVAL ON A DECISION ROW", row)
            for key in ("open_referrals", "supported_of_decided"):
                if set(data[key]) - {"count", "n"}:
                    print("INTERVAL ON", key, data[key])

lit = re.compile(r"`([^`]*)`|\"((?:[^\"\\]|\\.)*)\"")
for f in sorted((ROOT / "web" / "review").glob("*.*")):
    if f.suffix not in (".js", ".html"):
        continue
    for m in lit.finditer(f.read_text()):
        s = m.group(1) or m.group(2) or ""
        if len(s) < 12 or " " not in s:
            continue
        for p in banned_in(s):
            found_banned[p].add((f.name, "literal", s[:140]))
        for name, p in EXTRA.items():
            if re.search(p, s, re.IGNORECASE):
                found_extra[name].add(f"[{f.name}] " + s[:160])

print("BANNED (samajh.ops.wording.BANNED) hits:", {k: len(v) for k, v in found_banned.items()} or "none")
for k, v in found_banned.items():
    for e in sorted(v)[:5]:
        print("  ", k, e)
print("EXTRA patterns (distinct strings):")
for name in EXTRA:
    v = sorted(found_extra.get(name, ()))
    print(f"  {name}: {len(v)}")
    for e in v[:4]:
        print("     -", e)
