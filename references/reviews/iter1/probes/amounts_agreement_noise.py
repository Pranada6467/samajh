"""Does "two readings agree => right" hold under the noise conditions too? The report gives it for phone only.
BEFORE = saved scores.jsonl; AFTER = today's parser on the saved transcripts. Offline.

  uv run python references/reviews/iter1/probes/amounts_agreement_noise.py
"""

import json
import math
from pathlib import Path

from samajh.amounts import Parsed, parse_amount

ROOT = Path(__file__).resolve().parents[4]
scores = [json.loads(x) for x in (ROOT / "eval/amounts/run/scores.jsonl").read_text(encoding="utf-8").splitlines()]


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


rows = [s for s in scores if s["method"] == "parser" and s["output"] == "text" and s["stt"]["format"] == "transcribe" and s["stt"]["language"] == "item"]
for name in ("BEFORE", "AFTER"):
    print(name)
    pred = {}
    for s in rows:
        value = s["predicted"]
        if name == "AFTER":
            res = parse_amount(s["transcript"])
            value = res.rupees if isinstance(res, Parsed) else None
        pred[s["item_id"], s["condition"], s["stt"]["model"]] = (value, s["gold"])
    tot_agree = tot_wrong = 0
    for cond in ("clean16k", "phone", "narrowband", "street10", "street5", "babble10", "babble5"):
        ids = sorted({k[0] for k in pred if k[1] == cond})
        agree = [i for i in ids if pred[i, cond, "prisma-v2.5"][0] is not None and pred[i, cond, "prisma-v2.5"][0] == pred[i, cond, "prisma-v3.0"][0]]
        wrong = [i for i in agree if pred[i, cond, "prisma-v2.5"][0] != pred[i, cond, "prisma-v2.5"][1]]
        v3wrong = [i for i in ids if pred[i, cond, "prisma-v3.0"][0] is not None and pred[i, cond, "prisma-v3.0"][0] != pred[i, cond, "prisma-v3.0"][1]]
        caught = [i for i in v3wrong if i not in agree]
        lo, hi = wilson(len(agree) - len(wrong), len(agree))
        if cond not in ("clean16k", "phone"):
            tot_agree += len(agree)
            tot_wrong += len(wrong)
        print(f"  {cond:10s} n={len(ids):3d} agree {len(agree):3d}, agreeing but wrong {len(wrong)} {wrong} (right {100 * lo:.0f}-{100 * hi:.0f}%); "
              f"v3.0 wrong amounts {len(v3wrong)}, of them not agreed by v2.5 (caught) {len(caught)}")
    lo, hi = wilson(tot_agree - tot_wrong, tot_agree)
    print(f"  five degraded cells pooled (sentences repeat across cells): agree {tot_agree}, agreeing but wrong {tot_wrong} ({100 * lo:.1f}-{100 * hi:.1f}% right)")
