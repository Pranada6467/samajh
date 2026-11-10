"""P3b re-verification (round 2): phone-session ingestion on inputs the builder never used.
Offline: no Gnani, no OpenRouter, no server on 8085. Writes only under <scratch dir>.

Usage: uv run python references/reviews/iter2/probes/p3b_r2_ingest.py <scratch dir> <copied real sessions dir>

Builds a seed-85 batch with nine weekly draws, simulates the first six only (so the last three draws'
loans are untouched), then ingests: copies of today's real case files, plus synthetic case files on
drawn loans covering a referral, a failed case file, a running one, a late call, a call before the
sale, an IST-midnight call, a record on neither book, a folder with no case.json, a session on a
loan the simulation already completed, a re-ingest after a case file changed, and an outcome the
P2 fix round added. Then records decisions through the review routes in process (TestClient on a
bare FastAPI app with only the review router) and dumps every view as JSON for the wording probe.
"""

import json
import shutil
import sys
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from starlette.testclient import TestClient

from samajh.ops import book as books
from samajh.ops import sampler
from samajh.ops.batch import load_batch
from samajh.ops.model import FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest, packaged_records
from samajh.ops.simulate import run_draw, script_call, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, batch_view, case_view, queue_view
from samajh.server.review_routes import review_router

IST = timezone(timedelta(hours=5, minutes=30))
SCRATCH, REAL = Path(sys.argv[1]), Path(sys.argv[2])
if SCRATCH.exists():
    shutil.rmtree(SCRATCH)
STATE = SCRATCH / "state"
SESS = STATE / "sessions"
store = OpsStore(STATE / "ops")
meta, loans, customers = books.generate_book(85)
cust = {c.loan_id: c for c in customers}
store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
prev = None
for k in range(9):
    d = sampler.draw(loans, meta, date(2027, 1, 11) + timedelta(weeks=k), 0.4, 85, after=prev.as_of if prev else None)
    store.add_draw(d)
    prev = d
draws = store.draws()
for d in draws[:6]:
    run_draw(store, d, cust, scripted_analysis)
by_id = {l.record.loan_id: l for l in loans}
untouched = [x.loan_id for d in draws[6:] for x in d.drawn]  # drawn, no attempt yet
print("loans of draws 7-9 (no attempts):", untouched)

# pick, among all book loans, the archetype of each untouched loan
for lid in untouched:
    print("  ", lid, cust[lid].archetype, by_id[lid].sold_on)

sid_n = 0


def sid(ts: datetime) -> str:
    global sid_n
    sid_n += 1
    return f"{ts.astimezone(UTC):%Y%m%dT%H%M%S}-{sid_n:012x}"


def case_for(lid: str, started: datetime, outcome: str, status: str, result: bool = True, record_id=None) -> dict:
    loan = by_id.get(lid)
    s = sid(started)
    case = {
        "version": 1,
        "session_id": s,
        "record_id": record_id or lid,
        "loan_id": lid,
        "language": "hi",
        "status": status,
        "started_at": started.isoformat(),
        "call_outcome": outcome,
        "ended_reason": "hangup",
        "models": {"extraction": {"model": "probe/scripted"}},
        "turns": [],
    }
    if result and loan is not None:
        script = script_call(loan, cust[lid])
        res, _ = scripted_analysis(script, loan.record)
        t = script.transcript.model_dump(mode="json")
        t["call_id"] = s
        case["transcript"] = t
        case["result"] = res.model_dump(mode="json")
    return case


def put(case: dict, folder_name: str | None = None) -> str:
    f = SESS / (folder_name or case["session_id"])
    f.mkdir(parents=True, exist_ok=True)
    (f / "case.json").write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return case["session_id"]


def at(lid: str, day: int, hh: int = 11, mm: int = 0, tz=IST) -> datetime:
    return datetime.combine(by_id[lid].sold_on + timedelta(days=day), time(hh, mm), tz)


# 1. today's real case files, copied (never the originals)
real = sorted(REAL.glob("*/case.json"))
for p in real:
    (SESS / p.parent.name).mkdir(parents=True, exist_ok=True)
    shutil.copy(p, SESS / p.parent.name / "case.json")
real_no_case = [p.name for p in REAL.iterdir() if p.is_dir() and not (p / "case.json").exists()]
print(f"real session folders: {len(list(REAL.iterdir()))}, with case.json {len(real)}, without {len(real_no_case)}")

before = build_report(store)
L = untouched
expect = {}
# a. completed, ready, in window (a problem archetype if there is one)
problem = [l for l in L if cust[l].archetype not in ("informed_full", "informed_ordinary", "forgot_premium")]
la = problem[0] if problem else L[0]
expect["a_ready"] = put(case_for(la, at(la, 5), "completed", "ready"))
# b. completed, case file failed
lb = [l for l in L if l != la][0]
expect["b_failed"] = put(case_for(lb, at(lb, 5), "completed", "failed"))
# c. still running
lc = [l for l in L if l not in (la, lb)][0]
expect["c_running"] = put(case_for(lc, at(lc, 5), "completed", "running", result=False))
# d. no answer on day 29, then completed on day 31 (late) on the same loan
ld = [l for l in L if l not in (la, lb, lc)][0]
expect["d_noans29"] = put(case_for(ld, at(ld, 29), "no_response", "ready", result=False))
expect["d_done31"] = put(case_for(ld, at(ld, 31), "completed", "ready"))
# e. IST midnight: 20:00 UTC on day 30 is day 31 in IST; a retry outcome
le = [l for l in L if l not in (la, lb, lc, ld)][0]
expect["e_midnight"] = put(case_for(le, at(le, 30, 20, 0, UTC), "call_back_later", "ready", result=False))
# f. completed before the sale (day -3)
lf = [l for l in L if l not in (la, lb, lc, ld, le)][0]
expect["f_before_sale"] = put(case_for(lf, at(lf, -3), "completed", "ready"))
# g. record on neither book
g = case_for(la, at(la, 3), "completed", "ready")
g["record_id"], g["loan_id"] = "nobody", "SYN-XX-000000-0000"
expect["g_unknown"] = put(g)
# h. a folder with no case.json, and a folder whose name is not a session id
(SESS / "20270201T000000-00000000dead").mkdir(parents=True)
(SESS / "20270201T000000-00000000dead" / "session.json").write_text("{}")
put(case_for(la, at(la, 4), "declined", "ready", result=False), folder_name="not-a-session")
# i. a phone call on a loan the simulation already completed: no answer, two days later
done = next(s for s in load_batch(store).sampled if s.status is FinalStatus.completed)
li = done.drawn.loan_id
expect["i_after_sim_done"] = put(
    case_for(li, at(li, done.attempts[-1].day_since_sale + 2), "no_response", "ready", result=False)
)
# j. a book loan that was never drawn
drawn_ids = {x.loan_id for d in draws for x in d.drawn}
lj = next(l.record.loan_id for l in loans if l.record.loan_id not in drawn_ids)
expect["j_not_drawn"] = put(case_for(lj, at(lj, 5), "completed", "ready"))

r1 = ingest(store, SESS, packaged_records())
print("ingest 1:", r1.describe().replace("\n", " | "))
b1 = build_report(store)
r2 = ingest(store, SESS, packaged_records())
b2 = build_report(store)
print("ingest 2 (duplicate): linked", len(r2.linked), "outside", len(r2.outside),
      "report unchanged:", b1.model_dump() == b2.model_dump())
print("attempts:", len(store.attempts()), "outside rows:", len(store.outside()))

batch = load_batch(store)
st = {s.drawn.loan_id: s for s in batch.sampled}
for key, lid in (("a", la), ("b", lb), ("c", lc), ("d", ld), ("e", le), ("f", lf), ("i", li)):
    s = st[lid]
    print(f"  {key} {lid}: status {s.status.value}; attempts "
          f"{[(a.number, a.day_since_sale, a.outcome.value, a.source.kind) for a in s.attempts]}; "
          f"counted {s.counted}; tier {s.triage.tier.value if s.triage else None}")
print("  i: was completed by simulation, call", done.call.call_id, "-> now counted:", st[li].counted)
print("outside:", [(o.call.session_id, o.call.reason, o.call.outcome.value, o.triage.tier.value if o.triage else None)
                   for o in batch.outside])
print("funnel before/after:", before.funnel.sampled, before.funnel.attempts, "->", b1.funnel.sampled, b1.funnel.attempts)
print("completed before/after:", before.funnel.stages[-1].value.count, "->", b1.funnel.stages[-1].value.count)
print("timing after:", b1.timing)
print("simulated flag:", b1.batch.simulated, "| notice:", b1.batch.simulated_notice)
print("limits end:", b1.limits[-1])

# k. the case file of b is rebuilt and is now ready: ingest again
case_b = json.loads((SESS / expect["b_failed"] / "case.json").read_text())
case_b["status"] = "ready"
(SESS / expect["b_failed"] / "case.json").write_text(json.dumps(case_b, ensure_ascii=False))
try:
    r3 = ingest(store, SESS, packaged_records())
    print("re-ingest after failed->ready:", r3.describe().replace("\n", " | "),
          "| b status now", load_batch(store).sampled and {s.drawn.loan_id: s for s in load_batch(store).sampled}[lb].status.value)
except Exception as e:
    print("re-ingest after failed->ready RAISES:", type(e).__name__, str(e)[:160])
case_b["status"] = "failed"
(SESS / expect["b_failed"] / "case.json").write_text(json.dumps(case_b, ensure_ascii=False))

# l. outcomes the P2 fix round added
for outcome in ("do_not_call", "written_requested"):
    sub = SCRATCH / f"newoutcome-{outcome}"
    shutil.copytree(STATE / "ops", sub / "ops")
    one = sub / "sessions"
    c = case_for(lc, at(lc, 6), outcome, "ready", result=False)
    f = one / c["session_id"]
    f.mkdir(parents=True)
    (f / "case.json").write_text(json.dumps(c))
    try:
        r = ingest(OpsStore(sub / "ops"), one, packaged_records())
        print(f"outcome {outcome}:", r.describe().replace("\n", " | "))
    except Exception as e:
        print(f"outcome {outcome}: ingest RAISES {type(e).__name__}: {e}")

# m. decisions through the routes, in process
app = FastAPI()
app.include_router(review_router(STATE))
client = TestClient(app)
q = client.get("/api/review/queue").json()["items"]
print("queue:", [(i["case_id"], i["in_report"], i["not_counted_because"], i["simulated"]) for i in q])
counted = [i["case_id"] for i in q if i["in_report"]]
choices = ["concern_supported", "concern_not_supported", "call_customer", "needs_information"]
for k, cid in enumerate(counted[:6]):
    r = client.post(f"/api/review/cases/{cid}/disposition",
                    json={"decision": choices[k % 4], "note": "probe", "reviewer": "verifier"})
    assert r.status_code == 200, r.text
if counted:  # a later decision replaces the first
    client.post(f"/api/review/cases/{counted[0]}/disposition",
                json={"decision": "needs_information", "note": "second look", "reviewer": "verifier"})
nonref = next(s.call.call_id for s in load_batch(store).completed if not s.referred)
print("POST on a non-referral:", client.post(f"/api/review/cases/{nonref}/disposition",
      json={"decision": "call_customer", "note": "x", "reviewer": "v"}).status_code)
print("POST bad decision:", client.post(f"/api/review/cases/{counted[0]}/disposition",
      json={"decision": "established", "note": "x", "reviewer": "v"}).status_code)
print("GET path traversal:", client.get("/api/review/cases/..%2F..%2Fbatch").status_code)
outside_ref = [i["case_id"] for i in q if not i["in_report"]]
if outside_ref:
    print("POST on an outside referral:", client.post(f"/api/review/cases/{outside_ref[0]}/disposition",
          json={"decision": "call_customer", "note": "x", "reviewer": "v"}).status_code)

# dump every view
out = SCRATCH / "views"
out.mkdir()
batch = load_batch(store)
(out / "batch.json").write_text(batch_view(batch).model_dump_json(indent=1))
(out / "queue.json").write_text(queue_view(batch).model_dump_json(indent=1))
(out / "attempts.json").write_text(attempt_log_view(batch).model_dump_json(indent=1))
(out / "report.json").write_text(build_report(store).model_dump_json(indent=1))
for i in queue_view(batch).items:
    (out / f"case-{i.case_id}.json").write_text(case_view(batch, i.case_id, SESS).model_dump_json(indent=1))
for name in ("batch", "queue", "attempts", "report"):
    r = client.get(f"/api/review/{name}")
    assert r.status_code == 200, (name, r.status_code)
print("views written to", out)
