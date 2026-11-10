"""P3b round 4, claim 7: regression sweep on a new book; phone and simulated interleaved.

usage: uv run python references/reviews/iter2/probes/p3b_r4_sweep.py <state dir>
Writes only under <state dir>. No network. Then run p3b_r3_recount.py on <state dir>/w (read only).
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, invariants, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.simulate import run_draw, scripted_analysis  # noqa: E402
from samajh.ops.views import attempt_log_view, batch_view, case_view, queue_view  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
rng = random.Random(4242)
store, meta, loans, cust = new_batch(STATE / "w", seed=4242, n=140,
                                     draws=[(date(2027, 3, 1), 0.5), (date(2027, 3, 15), 0.5), (date(2027, 3, 29), 0.5)],
                                     sold_from=date(2027, 2, 5), days=50)
by = {b.record.loan_id: b for b in loans}
SESS = STATE / "w" / "sessions"
SESS.mkdir()
T = datetime(2026, 11, 10, 0, 0, tzinfo=UTC)
k = iter(range(10**6))
expect_refused: dict[str, str] = {}
late: list[str] = []
OUTS = ["completed", "no_response", "call_back_later", "do_not_call", "human_requested", "language_switch", "declined", "wrong_party"]


def phone_round(draw, n, tag):
    for x in draw.drawn[:n]:
        b = by[x.loan_id]
        kind = rng.random()
        started = T + timedelta(minutes=13 * next(k))
        if kind < 0.08:  # before the sale
            c = case_file(store, b, cust[b.record.loan_id], b.sold_on - timedelta(days=1), started)
            expect_refused[c["session_id"]] = "before the sale"
        elif kind < 0.16:  # before the draw (but after the sale)
            if draw.as_of > b.sold_on:
                c = case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=0), started)
                if b.sold_on < draw.as_of:
                    expect_refused[c["session_id"]] = "before the loan's draw"
            else:
                continue
        elif kind < 0.24:  # after day 30
            c = case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=31 + rng.randrange(10)), started)
            late.append(c["session_id"])
        else:
            o = rng.choice(OUTS)
            day = max((draw.as_of - b.sold_on).days, 0) + rng.randrange(0, 6)
            # 20:00-23:59 UTC is the next day in India: the attempt's day must still be the call date
            started = datetime(2026, 11, 10, rng.randrange(18, 24), rng.randrange(60), tzinfo=UTC) + timedelta(days=next(k))
            c = case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=min(day, 30)), started, outcome=o,
                          **({"speaker_confirmed": rng.choice([True, False])} if o in ("do_not_call", "call_back_later", "human_requested") else {}))
        put(SESS, c)


d1, d2, d3 = store.draws()
phone_round(d1, 18, "r1")
f = ingest(store, SESS, packaged_records())
run_draw(store, d1, cust, scripted_analysis)
phone_round(d1, 30, "r2")  # more sessions on d1 loans after the simulated run
phone_round(d2, 20, "r2")
f = ingest(store, SESS, packaged_records())
run_draw(store, d2, cust, scripted_analysis)
run_draw(store, d3, cust, scripted_analysis)
phone_round(d3, 25, "r3")
f = ingest(store, SESS, packaged_records())
f2 = ingest(store, SESS, packaged_records())
skipped = dict(f.skipped)
for sid, why in expect_refused.items():
    if sid in f.linked or sid in f.outside:
        FAILS.append(f"{sid} ({why}) was brought in")
    elif sid in skipped and not skipped[sid].strip():
        FAILS.append(f"{sid} refused without a reason")
    elif sid in skipped:
        print(f"  refused ({why}): {skipped[sid][:110]}")
for x in invariants(store, SESS):
    FAILS.append(f"invariant: {x}")
eff = {}
for l in (store.root / "attempts.jsonl").read_text().splitlines():
    if l:
        r = json.loads(l)
        eff[r["attempt_id"]] = r
late_logged = [a for a in eff.values() if a["source"]["kind"] == "phone_session" and a["source"]["session_id"] in late]
late_out = [s for s in late if s in skipped]
print(f"  late sessions: {len(late)}; logged as attempts: {len(late_logged)}; skipped: {[skipped[s][:60] for s in late_out]}")
b = load_batch(store)
counted_late = [s for s in b.sampled if s.counted and s.attempts and s.attempts[-1].day_since_sale > 30]
if counted_late:
    FAILS.append(f"late calls counted: {[s.loan.record.loan_id for s in counted_late]}")
rep = build_report(store)
if late_logged and rep.timing.attempts_after_window.count != len([a for a in eff.values() if a["day_since_sale"] > 30]):
    FAILS.append(f"timing after-window count {rep.timing.attempts_after_window.count}")
# India-day check from started_at vs at
for a in eff.values():
    if a["source"]["kind"] == "phone_session":
        case = json.loads((SESS / a["source"]["session_id"] / "case.json").read_text())
        if datetime.fromisoformat(a["at"]).date().isoformat() != case["book"]["call_date"]:
            FAILS.append(f"{a['attempt_id']}: at {a['at']} not on call date {case['book']['call_date']}")
phone = sum(a["source"]["kind"] == "phone_session" for a in eff.values())
print(f"  attempts {len(eff)} (phone {phone}), outside {len(store.outside())}, skipped {len(f.skipped)}")
# "finding" in every view string and key
blobs = [rep.model_dump_json(), batch_view(b).model_dump_json(), queue_view(b).model_dump_json(), attempt_log_view(b).model_dump_json()]
for cid in sorted({s.call.call_id for s in b.referrals if s.call}):
    try:
        blobs.append(case_view(b, cid).model_dump_json())
    except Exception as e:  # noqa: BLE001
        FAILS.append(f"case_view {cid}: {type(e).__name__}: {e}"[:200])
n_find = sum(x.lower().count("finding") for x in blobs)
print(f"  views scanned: {len(blobs)}; 'finding' occurrences: {n_find}")
if n_find:
    FAILS.append(f"'finding' appears {n_find} times in views")
print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x)
