"""Verifier probe for P6: regenerate amounts-v2 in memory and measure overlap with amounts-v1.

  uv run python references/reviews/iter2/probes/p6_heldout.py
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from samajh.evalkit.amounts import heldout
from samajh.evalkit.amounts.grammar import jsonl_bytes

REPO = Path(__file__).resolve().parents[4]
v2 = [json.loads(line) for line in (REPO / "data/amounts_v2/amounts-v2.jsonl").read_text().splitlines()]
v1 = [json.loads(line) for line in (REPO / "data/amounts/amounts-v1.jsonl").read_text().splitlines()]
print("regenerated sha256", hashlib.sha256(jsonl_bytes(heldout.generate())).hexdigest()[:16], "(frozen 1beea924ba961370)")

v1h = [r for r in v1 if r["language"] in ("hi", "hi-en")]
print("v1 hi/hi-en rows", len(v1h))
print("identical texts:", len({r["text"] for r in v2} & {r["text"] for r in v1h}))
same_amt = [(r["id"], r["gold"]["amount_inr"]) for r in v2
            if (r["language"], r["gold"]["amount_inr"]) in {(x["language"], x["gold"]["amount_inr"]) for x in v1h}]
print("v2 items whose (language, amount) is in v1:", len(same_amt), Counter(i.split("-")[-2] for i, _ in same_amt))
any_lang = [r for r in v2 if r["gold"]["amount_inr"] in {x["gold"]["amount_inr"] for x in v1h}]
print("v2 items whose amount is in v1 hi/hi-en in any language:", len(any_lang), Counter(r["tags"]["stratum"] for r in any_lang))


# carrier templates: replace the number phrase by masking the v1 amount wording is not available, so
# compare the non-number words: strip known number words/units by taking text outside the amount span.
def frame(r):
    t = r["text"]
    return t


def skeleton(text):
    # crude: drop tokens that are number-ish (Devanagari or Latin number words handled by the parser lexicon)
    from samajh.amounts._lexicon import WORDS  # working-copy lexicon; only used to mask
    toks = re.findall(r"\S+", text)
    out = []
    for tok in toks:
        key = tok.strip("।,.").lower()
        out.append("#" if key in WORDS or key.isdigit() else tok)
    return re.sub(r"(# ?)+", "# ", " ".join(out))


s1 = Counter(skeleton(r["text"]) for r in v1h)
s2 = Counter(skeleton(r["text"]) for r in v2)
shared = set(s1) & set(s2)
print("distinct skeletons v1", len(s1), "v2", len(s2), "shared", len(shared))
for s in list(shared)[:8]:
    print("  shared skeleton:", s)
# amount wording pattern overlap: number phrase shapes
print("v1 tags keys:", Counter(k for r in v1h for k in r.get("tags", {})).most_common(10))
print("v1 shape tags:", Counter(r["tags"].get("shape") for r in v1h).most_common(30))
