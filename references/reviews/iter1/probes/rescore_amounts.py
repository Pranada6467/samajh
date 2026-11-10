"""Verifier probe: rescore the saved amounts transcripts with one version of the parser.

    PYTHONPATH=<tree holding samajh/amounts at some commit> \
        python references/reviews/iter1/probes/rescore_amounts.py <repo root>

Reads `eval/amounts/run/stt.jsonl` (the cached Prisma output, 2,640 rows) and
`data/amounts/amounts-v1.jsonl` (gold) and writes nothing. No Gnani call. Exact match on the
rupee amount. Prints which `samajh.amounts` it imported, so the caller can run it once per
parser version (trees made with `git archive <commit> samajh/amounts samajh/types.py`).
"""

import json
import sys
from collections import Counter
from pathlib import Path

import samajh.amounts as amounts
from samajh.amounts import Parsed, parse_amount


def main() -> int:
    root = Path(sys.argv[1])
    print("parser:", Path(amounts.__file__).parent)
    gold = {}
    for line in (root / "data/amounts/amounts-v1.jsonl").read_text().splitlines():
        row = json.loads(line)
        gold[row["id"]] = row["gold"]["amount_inr"]
    rows = [json.loads(line) for line in (root / "eval/amounts/run/stt.jsonl").read_text().splitlines()]

    def read(text: str | None) -> int | None:
        if not text:
            return None
        result = parse_amount(text)
        return result.rupees if isinstance(result, Parsed) else None

    def cell(model: str, condition: str, fmt: str = "transcribe", language: str = "item", field: str = "text"):
        return {
            r["item_id"]: read(r.get(field))
            for r in rows
            if r["stt"]["model"] == model and r["condition"] == condition
            and r["stt"]["format"] == fmt and r["stt"]["language"] == language
        }

    def tally(got: dict[str, int | None]) -> str:
        c = Counter("right" if v == gold[i] else ("none" if v is None else "wrong") for i, v in got.items())
        return f"right {c['right']} of {len(got)} (wrong amount {c['wrong']}, no amount {c['none']})"

    v25_phone = cell("prisma-v2.5", "phone")
    v30_phone = cell("prisma-v3.0", "phone")
    print("v2.5 transcribe, phone :", tally(v25_phone))
    print("v2.5 transcribe, clean :", tally(cell("prisma-v2.5", "clean16k")))
    print("v2.5 literal, phone    :", tally(cell("prisma-v2.5", "phone", field="literal")))
    print("v3.0 transcribe, phone :", tally(v30_phone))
    print("v3.0 transcribe, clean :", tally(cell("prisma-v3.0", "clean16k")))
    agree = [i for i in gold if v25_phone[i] is not None and v25_phone[i] == v30_phone[i]]
    right = [i for i in agree if v25_phone[i] == gold[i]]
    print(f"v2.5 and v3.0 agree on phone: right {len(right)} of {len(agree)} agreeing; "
          f"agreeing and wrong: {[(i, v25_phone[i], gold[i]) for i in agree if i not in right]}")
    rest = [i for i in gold if i not in agree]
    print(f"not agreeing {len(rest)}; at least one right in {sum(gold[i] in (v25_phone[i], v30_phone[i]) for i in rest)}")
    wrong_v25 = [(i, v25_phone[i], gold[i]) for i in gold if v25_phone[i] not in (None, gold[i])]
    print("v2.5 phone wrong amounts:", wrong_v25)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
