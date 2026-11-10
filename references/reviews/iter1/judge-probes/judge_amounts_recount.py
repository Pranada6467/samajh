"""Judge probe: recount the amounts headline from eval/amounts/run/scores.jsonl (no API calls).

Usage: uv run python references/reviews/iter1/judge-probes/judge_amounts_recount.py
Scores in that file are from the parser as evaluated on 2026-11-10 (before the later parser fix).
"""
import json
from collections import defaultdict

rows = [json.loads(line) for line in open("eval/amounts/run/scores.jsonl")]
def pick(cond, model, method, output="text", fmt="transcribe"):
    return {r["item_id"]: r for r in rows if r["condition"] == cond and r["stt"]["model"] == model
            and r["stt"]["format"] == fmt and r["output"] == output and r["method"] == method
            and r["stt"]["language"] == "item"}  # the language set per item; indic-auto rows are a separate arm

for model in ("prisma-v2.5", "prisma-v3.0"):
    for method in ("naive", "parser"):
        d = pick("phone", model, method)
        print(model, method, "phone:", sum(r["correct"] for r in d.values()), "of", len(d))

a, b = pick("phone", "prisma-v2.5", "parser"), pick("phone", "prisma-v3.0", "parser")
agree = [i for i in a if a[i]["predicted"] == b[i]["predicted"] and isinstance(a[i]["predicted"], int)]
print("both models give the same amount:", len(agree), "right:", sum(a[i]["correct"] for i in agree))
rest = [i for i in a if i not in agree]
print("others:", len(rest), "at least one right:", sum(a[i]["correct"] or b[i]["correct"] for i in rest))

# v3.0 confident wrong amounts (an integer that is not the gold) on phone
wrong = [i for i in b if not b[i]["correct"] and isinstance(b[i]["predicted"], int)]
print("v3.0 phone: wrong amount with no warning:", len(wrong), "| no answer:", sum(1 for i in b if not b[i]["correct"]) - len(wrong))

# By size of the gold amount: how much of the set is in a retail premium range?
bands = [("under 1,000", 0, 999), ("1,000 to 2,00,000", 1000, 200000), ("above 2,00,000 to 1 crore", 200001, 10**7), ("above 1 crore", 10**7 + 1, 10**12)]
for name, lo, hi in bands:
    ids = [i for i in b if lo <= b[i]["gold"] <= hi]
    print(f"{name}: n={len(ids)} | v3.0 right {sum(b[i]['correct'] for i in ids)} | v2.5 right {sum(a[i]['correct'] for i in ids)} | "
          f"v3.0 silent wrong {sum(1 for i in ids if i in wrong)} | agree {sum(1 for i in ids if i in agree)} agree-right {sum(a[i]['correct'] for i in ids if i in agree)}")
by_lang = defaultdict(lambda: [0, 0, 0])
for i in b:
    L = b[i]["language"]; by_lang[L][0] += 1; by_lang[L][1] += b[i]["correct"]; by_lang[L][2] += a[i]["correct"]
print({k: v for k, v in by_lang.items()}, "(n, v3.0 right, v2.5 right)")
voices = {(r["voice"]["model"], r["voice"]["voice"]) for r in rows}
print("distinct TTS voices:", len(voices))
