"""Verifier probe for P6: skipped-group stratum detail (clean vs phone concordance, by shape, by voice,
and the 'X lakh Y' pattern where v3.0 writes X lakh Y thousand). Synthetic TTS set only.

  uv run python references/reviews/iter2/probes/p6_skipped_detail.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
items = {r["id"]: r for r in map(json.loads, (REPO / "data/amounts_v2/amounts-v2.jsonl").read_text().splitlines())}
rows = [json.loads(line) for line in (REPO / "eval/amounts_v2/run/stt.jsonl").read_text().splitlines()]
t3 = {}
voice = {}
for r in rows:
    if r["stt"]["model"] == "prisma-v3.0" and r["stt"]["format"] == "transcribe":
        nums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\d|\d", r["text"])]
        t3[(r["item_id"], r["condition"])] = nums
        voice[r["item_id"]] = r["voice"]["voice"]
skipped = [i for i, it in items.items() if it["tags"]["stratum"] == "skipped"]
state = {}
for i in skipped:
    g = items[i]["gold"]["amount_inr"]
    for c in ("clean16k", "phone"):
        n = t3[(i, c)]
        state[(i, c)] = "right" if n == [g] else ("wrong" if len(n) == 1 else "other")
pairs = Counter((state[(i, "clean16k")], state[(i, "phone")]) for i in skipped)
print("skipped items, (clean, phone) state by digit runs:", dict(pairs))
print("by shape (phone wrong / n):", {s: f"{sum(state[(i,'phone')]=='wrong' for i in skipped if items[i]['tags']['shape']==s)}/{sum(items[i]['tags']['shape']==s for i in skipped)}" for s in ("lakh_units", "lakh_hundreds", "thousand_units", "crore_thousands")})
by_lang = defaultdict(lambda: [0, 0])
for i in skipped:
    by_lang[items[i]["language"]][0] += state[(i, "phone")] == "wrong"
    by_lang[items[i]["language"]][1] += 1
print("by language:", dict(by_lang))
byv = defaultdict(lambda: [0, 0])
for i in skipped:
    byv[voice[i]][0] += state[(i, "phone")] == "wrong"
    byv[voice[i]][1] += 1
print("by voice (phone wrong, n):", dict(byv))
# 'X lakh Y' (Y < 100) written as X lakh Y thousand: the colloquial elliptical reading
coll = []
for i in skipped:
    it = items[i]
    g = it["gold"]["amount_inr"]
    if it["tags"]["shape"] != "lakh_units":
        continue
    lakh, rest = divmod(g, 100000)
    n = t3[(i, "phone")]
    if n == [lakh * 100000 + rest * 1000]:
        coll.append((i, it["tags"]["band"]))
print("phone: lakh_units written as X lakh Y thousand:", len(coll), Counter(b for _, b in coll))
wrong_phone = [i for i in skipped if state[(i, "phone")] == "wrong"]
print("phone wrong total", len(wrong_phone), "retail", sum(items[i]["tags"]["band"] == "retail" for i in wrong_phone),
      "by shape", Counter(items[i]["tags"]["shape"] for i in wrong_phone))
print("phone wrong retail by shape", Counter(items[i]["tags"]["shape"] for i in wrong_phone if items[i]["tags"]["band"] == "retail"))
