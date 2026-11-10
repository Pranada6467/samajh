"""P3b round 4, claim 6: strict booleans on readings, and speaker_confirmed on requests.

usage: uv run python references/reviews/iter2/probes/p3b_r4_speaker.py <state dir>
Writes only under <state dir>. No network.
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
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.views import readings_view  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
store, meta, loans, cust = new_batch(STATE / "b", seed=2718, n=80, draws=[(date(2027, 5, 4), 0.9)],
                                     sold_from=date(2027, 4, 20), days=12)
by = {b.record.loan_id: b for b in loans}
d0 = store.draws()[0]
pool = iter([by[x.loan_id] for x in d0.drawn])
SESS = STATE / "b" / "sessions"
T = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
minute = iter(range(10**6))


def at(k=None):
    return T + timedelta(minutes=5 * next(minute))


# --- A. readings -----------------------------------------------------------------
SECRET = "MODEL-WORDS-{}"
variants = [
    ("agreed 'yes'", {"readings_agreed": "yes"}, None),
    ("agreed 1", {"readings_agreed": 1}, None),
    ("agreed 'true'", {"readings_agreed": "true"}, None),
    ("agreed 0", {"readings_agreed": 0}, None),
    ("agreed [true]", {"readings_agreed": [True]}, None),
    ("agreed true", {"readings_agreed": True}, True),
    ("agreed false", {"readings_agreed": False}, False),
    ("agreed null", {"readings_agreed": None}, None),
]
ok_variants = [("ok 'false'", "false", False), ("ok 1", 1, False), ("ok 'yes'", "yes", False), ("ok null", None, False),
               ("ok absent", "ABSENT", True), ("ok true", True, True), ("ok false", False, False), ("ok {}", {}, False)]
checks = []
for i, (name, agreed, want_agreed) in enumerate(variants):
    okname, okval, want_shown = ok_variants[i % len(ok_variants)]
    b = next(pool)
    c = case_file(store, b, cust[b.record.loan_id], d0.as_of + timedelta(days=1), at())
    t0 = c["turns"][0]["turn_id"]
    r1 = {"role": "primary", "model": "prisma-v3.0", "text": SECRET.format(f"{i}a")}
    if okval != "ABSENT":
        r1["ok"] = okval
    r2 = {"role": "second", "model": "prisma-v2.5", "ok": True, "text": SECRET.format(f"{i}b")}
    c["turns"][0] |= {"readings": [r1, r2], **agreed, "followed_by": "read_back"}
    put(SESS, c)
    checks.append((f"{name} / {okname}", c["session_id"], t0, want_agreed, want_shown, i))
found = ingest(store, SESS, packaged_records())
for tag, sid, t0, want_agreed, want_shown, i in checks:
    if sid not in found.linked:
        FAILS.append(f"[{tag}] not linked: {[w for s, w in found.skipped if s == sid]}")
        continue
    call = store.call(sid)
    rv = readings_view(call, t0)
    text = json.dumps(rv.model_dump(mode="json"), ensure_ascii=False)
    shown = SECRET.format(f"{i}a") in text
    closing = rv.closing
    exp_closing = {None: "two readings, not compared as amounts in the case file", True: "same amount, read back", False: "differ, read back"}[want_agreed]
    print(f"  {tag:28s} closing={closing!r} primary text shown={shown}")
    if closing != exp_closing:
        FAILS.append(f"[{tag}] closing {closing!r}, expected {exp_closing!r}")
    if shown != want_shown:
        FAILS.append(f"[{tag}] primary text shown={shown}, expected {want_shown}")

# --- B. speaker_confirmed ----------------------------------------------------------
CD = d0.as_of
plan = {}


def sess(b, outcome, day, sc="ABSENT", **kw):
    over = {} if sc == "ABSENT" else {"speaker_confirmed": sc}
    c = case_file(store, b, cust[b.record.loan_id], CD + timedelta(days=day), at(), outcome=outcome, **over, **kw)
    put(SESS, c)
    return c["session_id"]


L = [next(pool) for _ in range(10)]
seq = {
    "L0 dnc unconfirmed then completed": [(L[0], "do_not_call", 1, False), (L[0], "completed", 2, "ABSENT")],
    "L1 three unconfirmed requests then a 4th": [(L[1], "human_requested", 1, False), (L[1], "call_back_later", 2, False),
                                                 (L[1], "do_not_call", 3, False), (L[1], "completed", 4, "ABSENT")],
    "L2 dnc confirmed then completed": [(L[2], "do_not_call", 1, True), (L[2], "completed", 2, "ABSENT")],
    "L3 dnc absent": [(L[3], "do_not_call", 1, "ABSENT")],
    "L4 cbl true": [(L[4], "call_back_later", 1, True)],
    "L5 human false": [(L[5], "human_requested", 1, False)],
    "L6 human true": [(L[6], "human_requested", 1, True)],
    "L7 no_response then dnc false then no_response": [(L[7], "no_response", 1, "ABSENT"), (L[7], "do_not_call", 2, False), (L[7], "no_response", 3, "ABSENT")],
    "L8 written_requested false": [(L[8], "written_requested", 1, False)],
    "L9 completed with speaker false (contradiction)": [(L[9], "completed", 1, False)],
}
sids = {}
for name, steps in seq.items():
    sids[name] = [sess(b, o, d, sc) for b, o, d, sc in steps]
found = ingest(store, SESS, packaged_records())
skipped = dict(found.skipped)
for name, ss in sids.items():
    lid = seq[name][0][0].record.loan_id
    chain = sorted((a for a in store.attempts() if a.loan_id == lid), key=lambda a: a.number)
    print(f"  {name:48s} -> {[(a.number, a.outcome.value, a.right_party_confirmed) for a in chain]} skipped={[skipped[s][:70] for s in ss if s in skipped]}")
expect = {
    "L0 dnc unconfirmed then completed": ["request_unconfirmed", "completed"],
    "L1 three unconfirmed requests then a 4th": ["request_unconfirmed"] * 3,
    "L2 dnc confirmed then completed": ["do_not_call"],
    "L3 dnc absent": ["do_not_call"],
    "L4 cbl true": ["call_back_later"],
    "L5 human false": ["request_unconfirmed"],
    "L6 human true": ["incomplete"],
    "L7 no_response then dnc false then no_response": ["no_answer", "request_unconfirmed", "no_answer"],
    "L8 written_requested false": ["written_requested"],
    "L9 completed with speaker false (contradiction)": [],
}
for name, want in expect.items():
    lid = seq[name][0][0].record.loan_id
    got = [a.outcome.value for a in sorted((a for a in store.attempts() if a.loan_id == lid), key=lambda a: a.number)]
    if got != want:
        FAILS.append(f"[{name}] chain {got}, expected {want}")

# funnel recount from raw files
rows = [json.loads(l) for l in (store.root / "attempts.jsonl").read_text().splitlines() if l]
eff = {}
for r in rows:
    eff[r["attempt_id"]] = r
chains = {}
for a in eff.values():
    chains.setdefault(a["loan_id"], []).append(a)
retry = {"no_answer", "call_back_later", "language_switch", "request_unconfirmed"}
status = {}
for x in d0.drawn:
    ch = sorted(chains.get(x.loan_id, []), key=lambda a: a["number"])
    if not ch:
        status[x.loan_id] = "not_attempted"
        continue
    last = ch[-1]
    if last["outcome"] == "completed":
        status[x.loan_id] = "completed" if 0 <= last["day_since_sale"] <= 30 else "completed_late"
    elif last["outcome"] in retry and last["day_since_sale"] >= 30:
        status[x.loan_id] = "not_reached_in_time"
    elif last["outcome"] == "no_answer":
        status[x.loan_id] = "unreachable"
    else:
        status[x.loan_id] = last["outcome"]
rep = build_report(store)
exits = {r.key: r.value.count for r in rep.funnel.exits}
stages = {r.key: r.value.count for r in rep.funnel.stages}
mine = {}
for s in status.values():
    mine[s] = mine.get(s, 0) + 1
for k, v in exits.items():
    if mine.get(k, 0) != v:
        FAILS.append(f"funnel exit {k}: report {v}, recount {mine.get(k, 0)}")
if stages["completed"] != mine.get("completed", 0):
    FAILS.append(f"funnel completed {stages['completed']} vs {mine.get('completed', 0)}")
rp = sum(any(a["right_party_confirmed"] for a in chains.get(x.loan_id, [])) for x in d0.drawn)
if stages["right_party_confirmed"] != rp:
    FAILS.append(f"right party {stages['right_party_confirmed']} vs {rp}")
print("  exits:", exits)
print("  recount:", mine)
if exits.get("do_not_call") != 2:
    FAILS.append(f"do_not_call count {exits.get('do_not_call')}, expected 2 (L2, L3)")
if "request_unconfirmed" not in exits:
    FAILS.append("no request_unconfirmed funnel row")
labels = {r.key: r.label for r in rep.funnel.exits}
print("  request_unconfirmed label:", labels.get("request_unconfirmed"))
print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x)
