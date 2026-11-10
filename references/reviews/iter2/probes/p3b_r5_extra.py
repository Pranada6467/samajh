"""P3b round 5 extras: missing sessions dir counts, folder-gone words, claim 5 with identical started_at.

usage: uv run python references/reviews/iter2/probes/p3b_r5_extra.py <state dir of p3b_r5_all.py> <new dir>
"""
import json, shutil, sys
from datetime import date, datetime, UTC
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import at_ist, case_file, new_batch, put  # noqa: E402
from samajh.ops.batch import load_batch
from samajh.ops.report import build_report
from samajh.ops.sessions import FOLDER_GONE, ingest, packaged_records
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, batch_view

print("FOLDER_GONE:", FOLDER_GONE)
st = OpsStore(Path(sys.argv[1]) / "c1" / "ops")
b = load_batch(st)
log = attempt_log_view(b)
print("1f missing dir: log note:", log.ingest_note)
print("1f changed:", log.changed, "not_ingested:", log.not_ingested)
rep = build_report(st, datetime(2027, 7, 1, tzinfo=UTC)).model_dump(mode="json")
print("1f report phone_sessions_changed:", rep.get("phone_sessions_changed"))
print("1f report limits mention:", [l[:160] for l in rep["limits"] if "phone" in l.lower()][:2])
print("1f batch phone counts:", {k: v for k, v in batch_view(b).model_dump(mode="json").items() if "phone" in k or "outside" in k})
# claim 1: rerun on the c1_base copy with all folders gone; check log.changed words
st2 = OpsStore(Path(sys.argv[1]) / "c1_base" / "ops"); sess2 = Path(sys.argv[1]) / "c1_base" / "sessions"
for p in list(sess2.iterdir()): shutil.rmtree(p)
f = ingest(st2, sess2, packaged_records())
log2 = attempt_log_view(load_batch(st2))
print("all gone: log.changed:", [(c.session_id[-6:], c.differs[:70]) for c in log2.changed])
# claim 5 identical started_at
OUT = Path(sys.argv[2]); shutil.rmtree(OUT, ignore_errors=True)
for first in ("completed", "no_response"):
    s3, meta, loans, cust = new_batch(OUT / first, seed=8080, n=20, draws=[(date(2027, 2, 2), 1.0)], sold_from=date(2027, 1, 28), days=3)
    loan = {x.record.loan_id: x for x in loans}[s3.draws()[0].drawn[1].loan_id]
    S = OUT / first / "sessions"
    t = at_ist(date(2026, 11, 10), 9, 5)
    other = "no_response" if first == "completed" else "completed"
    a = case_file(s3, loan, cust[loan.record.loan_id], date(2027, 2, 5), t, outcome=first, sid="20261110T033500-000000000002")
    c = case_file(s3, loan, cust[loan.record.loan_id], date(2027, 2, 5), t, outcome=other, sid="20261110T033500-000000000001")
    put(S, a); put(S, c)
    f = ingest(s3, S, packaged_records())
    n = sum(1 for x in s3.attempts() if x.loan_id == loan.record.loan_id)
    print(f"5 identical started_at, {first} in sid ...002: attempts={n} linked={f.linked} skipped={[(s[-3:], w[:80]) for s, w in f.skipped]}")
