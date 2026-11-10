"""Failure-label counts quoted in REPORT.md, recomputed from scores.jsonl + failure_labels.tsv. Offline.

  uv run python references/reviews/iter1/probes/amounts_labels.py
"""

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
scores = [json.loads(x) for x in (ROOT / "eval/amounts/run/scores.jsonl").read_text(encoding="utf-8").splitlines()]
with (ROOT / "eval/amounts/failure_labels.tsv").open(encoding="utf-8", newline="") as f:
    labels = {(r["item_id"], r["transcript"]): r["label"] for r in csv.DictReader(f, delimiter="\t")}


def lab(s):
    return f"{s['stt']['model'][7:]} {s['stt']['format']} {s['stt']['language']}"


failed = [s for s in scores if s["method"] == "parser" and not s["correct"]]
pairs = {(s["item_id"], s["transcript"]) for s in failed}
print(f"failed parser cells {len(failed)}; distinct (sentence, transcript) pairs {len(pairs)}; sentences {len({s['item_id'] for s in failed})}")
print("label rows in tsv:", len(labels), "| failed pairs with no label:", len(pairs - set(labels)), "| labels for pairs that are not failures:", len(set(labels) - pairs))
for stt in ("v2.5 transcribe item", "v3.0 transcribe item"):
    for cond in ("clean16k", "phone"):
        c = Counter(labels.get((s["item_id"], s["transcript"]), "UNLABELLED") for s in failed
                    if lab(s) == stt and s["condition"] == cond and s["output"] == "text")
        print(f"  {stt} {cond}: {dict(c)}")
rec = [s for s in failed if labels.get((s["item_id"], s["transcript"])) == "recognition"]
print("recognition-labelled failed cells:", len(rec), dict(Counter(s["condition"] for s in rec)))

# "8 of the 19 are proven formatting errors (v3.0's own verbatim output of the same sentence has the right words)"
ok = {(s["item_id"], lab(s)): s["correct"] for s in scores
      if s["method"] == "parser" and s["condition"] == "phone" and s["output"] == "text"}
proven = [s for s in failed if lab(s) == "v3.0 transcribe item" and s["condition"] == "phone" and s["output"] == "text"
          and labels.get((s["item_id"], s["transcript"])) == "prisma_formatting"]
for s in proven:
    v, c = ok.get((s["item_id"], "v3.0 verbatim item")), ok.get((s["item_id"], "v3.0 codemix item"))
    print(f"  prisma_formatting {s['item_id']}: gold {s['gold']} transcribe said {s['predicted']}; parser on v3.0 verbatim right={v}, codemix right={c}")
unres = [s["item_id"] for s in failed if lab(s) == "v3.0 transcribe item" and s["condition"] == "phone" and s["output"] == "text"
         and labels.get((s["item_id"], s["transcript"])) == "unresolved"]
manifest = {r["id"]: r for r in map(json.loads, (ROOT / "data/amounts/amounts-v1.jsonl").read_text(encoding="utf-8").splitlines())}
print("unresolved items and their fold:", [(i, manifest[i]["tags"]["fold"]) for i in unres])

from samajh.amounts import Parsed, parse_amount  # noqa: E402

today = Counter()
for r in manifest.values():
    res = parse_amount(r["text"])
    today[r["language"], isinstance(res, Parsed) and res.rupees == r["gold"]["amount_inr"]] += 1
print("today's parser on the written sentences (text control):", {k[0]: v for k, v in today.items() if k[1]}, "wrong:", {k[0]: v for k, v in today.items() if not k[1]})
