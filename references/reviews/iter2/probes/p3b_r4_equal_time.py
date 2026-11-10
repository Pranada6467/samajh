"""P3b round 4: a phone session at exactly the time of the loan's last attempt (the M7 boundary).

usage: uv run python references/reviews/iter2/probes/p3b_r4_equal_time.py <state dir>
"""
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import IST, case_file, invariants, new_batch, put  # noqa: E402

from samajh.ops.sessions import ingest, packaged_records  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
store, meta, loans, cust = new_batch(STATE, seed=1618, n=30, draws=[(date(2027, 4, 1), 1.0)], sold_from=date(2027, 3, 20), days=10)
by = {b.record.loan_id: b for b in loans}
b = by[store.draws()[0].drawn[0].loan_id]
cd = date(2027, 4, 3)
t = datetime(2026, 11, 10, 11, 0, 0, tzinfo=IST)
s1 = case_file(store, b, cust[b.record.loan_id], cd, t, outcome="no_response")
s2 = case_file(store, b, cust[b.record.loan_id], cd, t + timedelta(days=1))  # wall clock a day later, same India time, same call date
put(STATE / "sessions", s1)
put(STATE / "sessions", s2)
f = ingest(store, STATE / "sessions", packaged_records())
print("linked", f.linked, "skipped", f.skipped)
print([(a.number, a.at.isoformat(), a.outcome.value) for a in store.attempts()])
print("invariants:", invariants(store, STATE / "sessions"))
