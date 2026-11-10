"""P3a re-verification (round 3): mutations in a scratch copy; never the checkout.

    uv run python references/reviews/iter2/probes/p3a_r3_mutate.py <scratch-copy-of-repo>

The scratch copy needs samajh/, tests/, data/ (without amounts_v2 and scenarios) and
references/pilots. Each mutation is applied, `pytest tests/core tests/extract` is run with the
copy first on PYTHONPATH, and the file is restored.
"""

import os
import subprocess
import sys
from pathlib import Path

M = [
    ("change check ignores 'corrected'", "samajh/extract/_extract.py",
     "        if wire.change is Change.none:\n            return\n        first = g.run(",
     "        if wire.change in (Change.none, Change.corrected):\n            return\n        first = g.run("),
    ("change check ignores 'withdrawn'", "samajh/extract/_extract.py",
     "        if wire.change is Change.none:\n            return\n        first = g.run(",
     "        if wire.change in (Change.none, Change.withdrawn):\n            return\n        first = g.run("),
    ("both readings agree dropped (stands = True)", "samajh/extract/_extract.py",
     "            stands = at is not None and first[1] < at[0] and final[0] <= at[1] <= final[1]",
     "            stands = True"),
    ("change check only on 3+ clauses", "samajh/extract/_extract.py",
     "            if len(reply.clauses()) >= 2:", "            if len(reply.clauses()) >= 3:"),
    ("denial order test removed", "samajh/rules/checks.py",
     "        later = tuple(ev for ev in named if ev.turn_id > denial.turn_id)", "        later = tuple(named)"),
    ("kind-on-record filter removed", "samajh/rules/checks.py",
     "        named = [i.evidence for i in _matched(p, beliefs) if i.kind is on_record]",
     "        named = [i.evidence for i in _matched(p, beliefs)]"),
    ("cover: exact figure with rejected read-back passes", "samajh/rules/checks.py",
     "            if _rejected(readback) and not corrected:\n                return (_gap(rule, p.id, GapReason.readback_rejected, readback.evidence),)\n",
     ""),
    ("cover: wrong figure with rejected/mismatched read-back -> understanding_gap (old)", "samajh/rules/checks.py",
     "        else:\n            why = Why.cover_differs_unconfirmed",
     "        elif _rejected(readback) or _mismatched(readback):\n            why = Why.cover_differs\n        else:\n            why = Why.cover_differs_unconfirmed"),
    ("carried premium even when the premium was asked", "samajh/rules/normalise.py",
     "        elif pid not in asked:", "        elif True:"),
    ("approximate tolerance ignored in the conflict rule", "samajh/extract/_extract.py",
     "        tol = max(x[2], y[2])", "        tol = AMOUNT_TOLERANCE_PERCENT"),
    ("self-correction 'also' dropped", "samajh/extract/_extract.py",
     "                        heard[k] = answer.model_copy(update={\"also\": (*answer.also, earlier)})",
     "                        heard[k] = answer"),
]


def main() -> int:
    root = Path(sys.argv[1])
    py = Path(__file__).resolve().parents[4] / ".venv/bin/python"
    env = {**os.environ, "PYTHONPATH": str(root)}
    for name, rel, old, new in M:
        f = root / rel
        src = f.read_text(encoding="utf-8")
        if src.count(old) != 1:
            print(f"SKIP (pattern count {src.count(old)}): {name}")
            continue
        f.write_text(src.replace(old, new), encoding="utf-8")
        try:
            r = subprocess.run([str(py), "-m", "pytest", "tests/core", "tests/extract", "-q", "-x",
                                "-p", "no:cacheprovider"], cwd=root, env=env, capture_output=True, text=True)
        finally:
            f.write_text(src, encoding="utf-8")
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
        print(f"{'caught  ' if r.returncode else 'SURVIVED'} {name} | {last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
