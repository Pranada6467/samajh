"""P3b round 3: the two-readings line beside an amount quote on a phone call's case page (claim 15),
on case files with reading shapes the builders did not write.

Usage: uv run python references/reviews/iter2/probes/p3b_r3_readings.py <state dir>
Writes only under <state dir>; leaves a state with referred phone calls for page rendering
(<state dir>/ops, <state dir>/sessions) and <state dir>/expected_lines.json.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.views import case_view  # noqa: E402
from samajh.types import SaleConcern  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
store, meta, loans, cust = new_batch(STATE, 31415, 40, [(date(2027, 2, 20), 1.0)], sold_from=date(2027, 1, 25), days=26)
drawn = [b for b in loans if any(x.loan_id == b.record.loan_id for d in store.draws() for x in d.drawn)]
sess = STATE / "sessions"

P = lambda text, model="prisma-v3.0", ok=True, error=None: {  # noqa: E731
    "role": "primary", "mode": "rest", "model": model, "params": {"format": "transcribe"}, "ok": ok, "error": error, "text": text,
}
S = lambda text, model="prisma-v2.5", ok=True, error=None: {  # noqa: E731
    "role": "second", "mode": "rest", "model": model, "params": {"format": "transcribe"}, "ok": ok, "error": error, "text": text,
}
ODD = "₹ 25,000 रुपये  <b>पच्चीस</b> · \"quote\" ​ end "
VARIANTS = {
    # name: (readings, readings_agreed (or "ABSENT"), followed_by (or "ABSENT"), expected closing, expected texts)
    "same_read_back": ([P("बारह हज़ार पाँच सौ"), S("12,500")], True, "read_back", "same amount, read back"),
    "differ_asked_again": ([P("बारह हज़ार"), S("12,500")], False, "asked_again", "differ, asked again"),
    "differ_read_back": ([P("1,20,500"), S("12,500")], False, "read_back", "differ, read back"),
    "same_asked_again": ([P("12500"), S("12,500")], True, "asked_again", "same amount, asked again"),
    "same_other": ([P("12500"), S("12500")], True, "other", "same amount"),
    "differ_missing_fb": ([P("12500"), S("15000")], False, "ABSENT", "differ"),
    "null_read_back": ([P("बारह"), S("twelve")], None, "read_back", None),
    "absent_agreed": ([P("बारह"), S("twelve")], "ABSENT", "read_back", None),
    "one_reading": ([P("12,500")], None, "read_back", "one reading"),
    "second_timeout": ([P("12,500"), S("", ok=False, error="timeout")], False, "asked_again", "differ, asked again"),
    "odd_text": ([P(ODD), S(ODD.strip())], True, "read_back", "same amount, read back"),
    "odd_followed_by": ([P("12500"), S("12500")], True, "banana", "same amount"),
    "other_models": ([P("12500", model="prisma-v2.5"), S("12500", model="custom-x")], True, "read_back", "same amount, read back"),
    "second_empty_ok": ([P("12500"), S("")], False, "asked_again", "differ, asked again"),
    "second_first": ([S("12,500"), P("12,500")], True, "read_back", "same amount, read back"),
}
expected = {}
for i, (name, (readings, agreed, fb, closing)) in enumerate(VARIANTS.items()):
    b = drawn[i]
    lid = b.record.loan_id
    c0 = cust[lid]
    (bel,) = c0.beliefs[:1]
    product = b.record.products[0]
    who = c0.model_copy(
        update={
            "beliefs": (bel.model_copy(update={"premium_inr": 3500 if product.premium_inr != 3500 else 7500, "cover_inr": 2000000 if product.cover_inr != 2000000 else 1000000}),) + c0.beliefs[1:],
            "concerns": (SaleConcern.coached_answers,),
        }
    )
    started = datetime(2026, 11, 10, 4, 0, tzinfo=UTC) + timedelta(minutes=i)
    c = case_file(store, b, who, date(2027, 2, 20), started)
    for t in c["turns"]:
        t["readings"] = readings
        if agreed != "ABSENT":
            t["readings_agreed"] = agreed
        if fb != "ABSENT":
            t["followed_by"] = fb
    put(sess, c)
    expected[c["session_id"]] = (name, readings, closing)
found = ingest(store, sess, packaged_records())
print("ingest:", found.describe())
batch = load_batch(store)
lines_out = {}
seen_amount_lines = 0
for sid, (name, readings, closing) in expected.items():
    try:
        cv = case_view(batch, sid, sess)
    except Exception as e:  # noqa: BLE001
        FAILS.append(f"{name}: no case page ({type(e).__name__}); tier not refer?")
        continue
    quotes = [ln.quote for ln in (*cv.refer_lines, *cv.other_lines) if ln.quote is not None]
    amount = [q for q in quotes if q.readings is not None]
    seen_amount_lines += len(amount)
    if not amount:
        FAILS.append(f"{name}: no amount quote with a readings line (quotes {len(quotes)})")
        continue
    for q in amount:
        r = q.readings
        prim = next((x for x in readings if x["role"] == "primary"), None)
        sec = next((x for x in readings if x["role"] == "second"), None)
        want_parts = []
        for x in (prim, sec):
            if x is None:
                continue
            label = "Prisma " + x["model"].removeprefix("prisma-") if x["model"].startswith("prisma-") else x["model"]
            if x["ok"] and x["text"]:
                want_parts.append((label, x["text"], True))
            else:
                want_parts.append((label, None, False))
        got_parts = [(p.model, p.text if p.as_written else None, p.as_written) for p in r.parts]
        if got_parts != want_parts:
            FAILS.append(f"{name}: parts {got_parts!r} != {want_parts!r}")
        for p, x in zip(r.parts, [x for x in (prim, sec) if x]):
            if p.as_written and p.text.encode() != x["text"].encode():
                FAILS.append(f"{name}: text not byte for byte")
        if closing is None:
            if any(w in r.closing for w in ("same", "differ")):
                FAILS.append(f"{name}: null agreement but closing '{r.closing}'")
        elif r.closing != closing:
            FAILS.append(f"{name}: closing '{r.closing}' != '{closing}'")
        line = " · ".join(f"{p.model}: {p.text}" for p in r.parts) + f" · {r.closing}"
        lines_out.setdefault(sid, []).append(line)
    print(f"  {name:20s} {len(amount)} amount quote(s): {lines_out.get(sid, ['-'])[0][:150]}")
(STATE / "expected_lines.json").write_text(json.dumps(lines_out, ensure_ascii=False, indent=1))
print(f"amount quote lines checked: {seen_amount_lines}")
for f in FAILS:
    print("FAIL", f)
print("FAILURES:", len(FAILS))
