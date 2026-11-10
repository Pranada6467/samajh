"""P3b round 3: ingest on inputs the builders never saw (claims 1, 3, 4, 5, 7, 10, 11).

Usage: uv run python references/reviews/iter2/probes/p3b_r3_ingest.py <state dir> [<copied real sessions dir>]
Writes only under <state dir>. Prints one line per check and FAIL lines; exits 0 always.
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import at_ist, case_file, hashes, invariants, new_batch, put  # noqa: E402

from samajh.dialogue.machine import Outcome  # noqa: E402
from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.model import FROM_DIALOGUE  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.views import attempt_log_view  # noqa: E402

STATE = Path(sys.argv[1])
REAL = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
WALL = date(2026, 11, 10)


def fail(msg: str) -> None:
    FAILS.append(msg)
    print("FAIL", msg)


def run_ingest(store: OpsStore, sessions: Path):
    try:
        return ingest(store, sessions, packaged_records()), None
    except BaseException as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}".splitlines()[0][:240] + " @ " + traceback.extract_tb(e.__traceback__)[-1].name


store, meta, loans, cust = new_batch(
    STATE / "A",
    seed=4711,
    n=110,
    draws=[(date(2027, 2, 10), 0.7), (date(2027, 2, 20), 0.7), (date(2027, 3, 2), 0.7), (date(2027, 3, 12), 0.7)],
    sold_from=date(2027, 2, 1),
    days=40,
)
by_id = {b.record.loan_id: b for b in loans}
drawn = [(d, x.loan_id) for d in store.draws() for x in d.drawn]
undrawn = [b for b in loans if not any(b.record.loan_id == lid for _, lid in drawn)]
print(f"batch A: {len(loans)} loans, {len(store.draws())} draws, {len(drawn)} drawn, {len(undrawn)} never drawn")
pool = iter(drawn)


def next_loan():
    d, lid = next(pool)
    return d, by_id[lid]


SESS = STATE / "A" / "sessions"
SESS.mkdir(parents=True)
hour = iter(range(0, 10**6))


def started() -> datetime:
    # distinct wall-clock times on 10 November 2026, a minute apart
    return datetime(2026, 11, 10, 0, 0, tzinfo=UTC) + timedelta(minutes=next(hour))


expect: dict[str, str] = {}  # folder -> "linked" | "outside" | "skipped"

# ---- 1. hostile folders, each also tried alone ----------------------------------------------
d0, base_loan = next_loan()
valid = case_file(store, base_loan, cust[base_loan.record.loan_id], d0.as_of, started())
hostile: dict[str, object] = {}
hostile["no-case-no-log"] = None
hostile["no-case-active-log"] = ("session.json", json.dumps({"status": "active", "dialogue": "samajh"}))
hostile["no-case-garbage-log"] = ("session.json", "{{{{")
hostile["no-case-list-log"] = ("session.json", "[1,2]")
hostile["empty"] = b""
hostile["truncated"] = json.dumps(valid)[:400]
hostile["binary"] = bytes(range(256)) * 4
hostile["array"] = "[1, 2, 3]"
hostile["wrong-types"] = {**valid, "status": 5, "started_at": "yesterday", "loan_id": None}
hostile["sid-mismatch"] = {**valid, "session_id": "20261110T000000-0000000000ff"}
hostile["running"] = {**valid, "status": "running"}
hostile["bogus-outcome"] = {**valid, "call_outcome": "exploded"}
hostile["bad-transcript"] = {**valid, "transcript": {"call_id": "x", "turns": [{"id": "a"}]}}
hostile["bad-result"] = {**valid, "result": {"products": "nope"}}
hostile["extraction-is-string"] = {**valid, "models": {"extraction": "gpt-6"}}
hostile["extraction-is-list"] = {**valid, "models": {"extraction": ["gpt-6"]}}
hostile["year-9999"] = {**valid, "started_at": "9999-12-31T23:59:59+00:00"}
hostile["year-1-plus14"] = {**valid, "started_at": "0001-01-01T00:00:00+14:00"}
hostile["deep-nesting"] = "[" * 200000 + "]" * 200000
hostile["agreed-maybe"] = {**valid, "turns": [{**t, "readings": [], "readings_agreed": "maybe"} for t in valid["turns"]]}
hostile["agreed-yes-string"] = {
    **valid,
    "turns": [
        {**t, "readings": [{"role": "primary", "model": "prisma-v3.0", "text": "x"}], "readings_agreed": "yes"}
        for t in valid["turns"]
    ],
}
hostile["readings-dict"] = {**valid, "turns": [{**t, "readings": {"role": "primary"}} for t in valid["turns"]]}
hostile["role-third"] = {
    **valid,
    "turns": [{**t, "readings": [{"role": "third", "model": "m", "text": "x"}]} for t in valid["turns"]],
}
hostile["turn-no-id"] = {**valid, "turns": [{"text": "x", "readings": []}]}
hostile["turns-strings"] = {**valid, "turns": ["a", "b"]}
hostile["models-string"] = {**valid, "models": "x"}
hostile["language-xx"] = {**valid, "language": "xx"}
hostile["audio-negative"] = {**valid, "customer_audio": {"mic": -1, "file": 0, "none": 0}}
hostile["audio-string"] = {**valid, "customer_audio": "mic"}
hostile["book-bad-date"] = {**valid, "book": {**valid["book"], "call_date": "2027-02-30"}}
hostile["book-string"] = {**valid, "book": "yes"}
hostile["recording-list"] = {**valid, "recording": [1]}
hostile["recording-sha-int"] = {**valid, "recording": {"sha256": 5}}
hostile["case-is-dir"] = "DIR"
hostile["null-json"] = "null"

alone: dict[str, str] = {}
for i, (name, content) in enumerate(hostile.items()):
    sid = f"20261110T0{i // 60:01d}{i % 60:02d}00-{0xbad000 + i:012x}"
    one = STATE / "alone" / name
    if one.exists():
        shutil.rmtree(one)
    shutil.copytree(STATE / "A" / "ops", one / "ops")
    s = OpsStore(one / "ops")
    folder = one / "sessions" / sid
    folder.mkdir(parents=True)
    if content is None:
        pass
    elif isinstance(content, tuple):
        (folder / content[0]).write_text(content[1])
    elif content == "DIR":
        (folder / "case.json").mkdir()
    elif isinstance(content, dict):
        c = dict(content)
        if c.get("session_id") == valid["session_id"]:
            c["session_id"] = sid
            if isinstance(c.get("transcript"), dict) and "call_id" in c["transcript"] and c["transcript"]["call_id"] == valid["session_id"]:
                c["transcript"] = {**c["transcript"], "call_id": sid}
        put(one / "sessions", c, name=sid)
    else:
        put(one / "sessions", content, name=sid)  # type: ignore[arg-type]
    found, err = run_ingest(s, one / "sessions")
    if err:
        alone[name] = "RAISED " + err
        fail(f"hostile '{name}': ingest raised {err}")
    else:
        where = "linked" if found.linked else "outside" if found.outside else "skipped"
        why = found.skipped[0][1] if found.skipped else ""
        alone[name] = f"{where}{': ' + why[:110] if why else ''}"
        if (len(found.linked) + len(found.outside) + len(found.skipped)) != 1:
            fail(f"hostile '{name}': not exactly one list")
        bad = invariants(s, one / "sessions")
        if bad:
            fail(f"hostile '{name}': invariants {bad[:3]}")
for name, res in alone.items():
    print(f"  hostile {name:22s} -> {res}")

# ---- 2. every dialogue outcome, on its own drawn loan --------------------------------------
outcome_loans: dict[str, str] = {}
for value in [o.value for o in Outcome] + ["in_progress"]:
    d, b = next_loan()
    lid = b.record.loan_id
    c = case_file(store, b, cust[lid], d.as_of, started(), outcome=value)
    put(SESS, c)
    expect[c["session_id"]] = "linked"
    outcome_loans[value] = lid

# ---- 3. loans not drawn, no book block, packaged records, unknown record ------------------
nd1, nd2 = undrawn[0], undrawn[1]
c = case_file(store, nd1, cust[nd1.record.loan_id], nd1.sold_on + timedelta(days=3), started(), book_over={"draw_id": "D-2027-02-20"})
put(SESS, c)
expect[c["session_id"]] = "outside"
undrawn_with_book = c["session_id"]
c = case_file(store, nd2, cust[nd2.record.loan_id], None, started(), outcome="no_response")
put(SESS, c)
expect[c["session_id"]] = "outside"
undrawn_no_book = c["session_id"]
d, b = next_loan()
c = case_file(store, b, cust[b.record.loan_id], None, started())
put(SESS, c)
expect[c["session_id"]] = "outside"
drawn_no_book = c["session_id"]
hero = case_file(store, b, None, None, started(), outcome="wrong_party", record_id="hero", loan_id="SYN-HERO-0001")
put(SESS, hero)
expect[hero["session_id"]] = "outside"
ghost = case_file(store, b, None, None, started(), outcome="declined", record_id="ghost", loan_id="SYN-GHOST")
put(SESS, ghost)
expect[ghost["session_id"]] = "skipped"

# ---- 4. dates and book-block disagreements (each on a fresh drawn loan) --------------------
date_cases = {}
d, b = next_loan()
c = case_file(store, b, cust[b.record.loan_id], b.sold_on - timedelta(days=2), started(), outcome="no_response")
date_cases["before-sale"] = c
d, b = next_loan()
if (d.as_of - b.sold_on).days >= 1:
    c = case_file(store, b, cust[b.record.loan_id], d.as_of - timedelta(days=1), started(), outcome="no_response")
    date_cases["before-draw"] = c
d, b = next_loan()
date_cases["sold-on-wrong"] = case_file(store, b, None, d.as_of, started(), outcome="declined",
                                        book_over={"sold_on": (b.sold_on - timedelta(days=1)).isoformat()})
d, b = next_loan()
date_cases["day-count-wrong"] = case_file(store, b, None, d.as_of, started(), outcome="declined",
                                          book_over={"day_since_sale": (d.as_of - b.sold_on).days + 1})
d, b = next_loan()
date_cases["batch-wrong"] = case_file(store, b, None, d.as_of, started(), outcome="declined",
                                      book_over={"batch_id": "B-2027H1-deadbeef"})
d, b = next_loan()
other = next(x for x in store.draws() if x.draw_id != d.draw_id)
date_cases["draw-wrong"] = case_file(store, b, None, d.as_of, started(), outcome="declined", book_over={"draw_id": other.draw_id})
d, b = next_loan()
date_cases["record-id-wrong"] = case_file(store, b, None, d.as_of, started(), outcome="declined", record_id="hero")
d, b = next_loan()
date_cases["loan-not-on-book"] = case_file(store, b, None, d.as_of, started(), outcome="declined",
                                           loan_id="SYN-PL-990101-0001", record_id="SYN-PL-990101-0001")
for c in date_cases.values():
    put(SESS, c)
    expect[c["session_id"]] = "skipped"

# ---- 5. late calls (day 31, day 45) and the India-time boundary (20:00 UTC on day 30) -------
late = {}
d, b = next_loan()
late["day31-completed"] = case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=31), started())
d, b = next_loan()
late["day45-no-answer"] = case_file(store, b, None, b.sold_on + timedelta(days=45), started(), outcome="no_response")
d, b = next_loan()
# wall clock 20:00 UTC = 01:30 IST next day; call_date is day 30
late["day30-2000utc"] = case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=30),
                                  datetime(2026, 11, 10, 20, 0, tzinfo=UTC))
for c in late.values():
    put(SESS, c)
    expect[c["session_id"]] = "linked"

# ---- 6. customer audio note --------------------------------------------------------------
audio_kinds = {
    "mic": {"mic": 5, "file": 0, "none": 1},
    "file": {"mic": 0, "file": 7, "none": 0},
    "both": {"mic": 2, "file": 3, "none": 0},
    "silent": {"mic": 0, "file": 0, "none": 4},
    "absent": None,
}
for kind, audio in audio_kinds.items():
    d, b = next_loan()
    c = case_file(store, b, None, d.as_of, started(), outcome="declined", audio=audio)
    put(SESS, c)
    expect[c["session_id"]] = "linked"

# ---- 7. rebuild: failed then ready (attempt, outside, third attempt) -----------------------
d, rb = next_loan()
rebuild = case_file(store, rb, cust[rb.record.loan_id], d.as_of, started(), status="failed")
put(SESS, rebuild)
expect[rebuild["session_id"]] = "linked"
nd3 = undrawn[2]  # outside variant: a never-drawn book loan, no book block, failed then ready
rebuild_out = case_file(store, nd3, cust[nd3.record.loan_id], None, started(), outcome="completed", status="failed")
put(SESS, rebuild_out)
expect[rebuild_out["session_id"]] = "outside"
d, r3 = next_loan()
third = []
for k in range(3):
    c = case_file(store, r3, cust[r3.record.loan_id], d.as_of + timedelta(days=k), started(),
                  outcome="no_response" if k < 2 else "completed", status="ready" if k < 2 else "failed")
    put(SESS, c)
    expect[c["session_id"]] = "linked"
    third.append(c)

# ---- run 1 -------------------------------------------------------------------------------
ops = STATE / "A" / "ops"
found, err = run_ingest(store, SESS)
if err:
    fail(f"ingest 1 raised {err}")
    print("FAILURES:", len(FAILS))
    sys.exit(0)
print("ingest 1:", found.describe().splitlines()[0])
got = {s: "linked" for s in found.linked} | {s: "outside" for s in found.outside} | {s: "skipped" for s, _ in found.skipped}
reasons = dict(found.skipped)
for sid, want in expect.items():
    if got.get(sid) != want:
        fail(f"{sid}: expected {want}, got {got.get(sid)} {reasons.get(sid, '')}")
for name, c in date_cases.items():
    print(f"  date case {name:18s} -> {got.get(c['session_id'])}: {reasons.get(c['session_id'], '')[:120]}")
bad = invariants(store, SESS)
for x in bad:
    fail(f"invariant after ingest 1: {x}")

batch = load_batch(store)
att_by_sid = {a.source.session_id: (s, a) for s in batch.sampled for a in s.attempts if a.source.kind == "phone_session"}
for value, lid in outcome_loans.items():
    s = next(x for x in batch.sampled if x.drawn.loan_id == lid)
    a = s.attempts[-1]
    want = FROM_DIALOGUE.get(value)
    if a.outcome is not want:
        fail(f"outcome {value}: attempt outcome {a.outcome} (want {want})")
print("  outcomes:", {v: next(x for x in batch.sampled if x.drawn.loan_id == lid).status.value for v, lid in outcome_loans.items()})
for name, c in late.items():
    s, a = att_by_sid[c["session_id"]]
    print(f"  late {name}: day {a.day_since_sale}, at {a.at.isoformat()}, status {s.status.value}, counted {s.counted}")
s, a = att_by_sid[late["day30-2000utc"]["session_id"]]
if not (a.day_since_sale == 30 and s.counted):
    fail(f"day30 at 20:00 UTC: day {a.day_since_sale} counted {s.counted}")
s, a = att_by_sid[late["day31-completed"]["session_id"]]
if s.counted or s.status.value != "completed_late":
    fail(f"day31 completed counted={s.counted} status={s.status}")
outside_by = {o.call.session_id: o.call for o in batch.outside}
for sid in (undrawn_with_book, undrawn_no_book):
    print(f"  never drawn {sid}: reason '{outside_by[sid].reason}'")
    if outside_by[sid].reason != "the loan was not drawn in this batch":
        fail(f"never-drawn loan reason: {outside_by[sid].reason}")
print(f"  drawn, no book block: '{outside_by[drawn_no_book].reason}'")
rep = build_report(store)
print("  timing:", rep.timing.attempts_after_window, rep.timing.phone_attempts_after_window, "|", rep.timing.note)
if "by design" in rep.timing.note:
    fail("timing note says 'by design' with late phone attempts")
if rep.timing.first_attempt_days and rep.timing.first_attempt_days[0] < 0:
    fail(f"negative first-attempt day {rep.timing.first_attempt_days}")
phone_line = next((x for x in rep.limits if x.startswith("Calls marked Phone call")), None)
print("  phone note:", phone_line)
# expected audio counts: over all phone sessions in the store
srcs = batch.phone_sessions
known = [x.customer_audio for x in srcs if x.customer_audio is not None]
exp = (
    sum(a.mic > 0 and a.file == 0 for a in known),
    sum(a.file > 0 and a.mic == 0 for a in known),
    sum(a.mic > 0 and a.file > 0 for a in known),
    sum(a.mic == 0 and a.file == 0 for a in known),
    len(srcs) - len(known),
)
want_line = (
    f"{len(srcs)} phone session(s), {exp[0]} with customer audio from the microphone only, {exp[1]} from prepared audio "
    f"files only, {exp[2]} from both, {exp[3]} with no customer audio"
)
if phone_line is None or want_line not in phone_line or (exp[4] and f"{exp[4]} where it is not recorded" not in phone_line):
    fail(f"phone note: want '{want_line}' + {exp[4]} unknown")
# raw recount of audio from the case files I wrote
raw = {"mic": 0, "file": 0, "both": 0, "silent": 0, "absent": 0}
in_store = set(att_by_sid) | set(outside_by)
for f in SESS.glob("*/case.json"):
    try:
        j = json.loads(f.read_text())
    except Exception:
        continue
    if not isinstance(j, dict) or j.get("session_id") not in in_store:
        continue
    au = j.get("customer_audio")
    if au is None:
        raw["absent"] += 1
    elif au["mic"] and au["file"]:
        raw["both"] += 1
    elif au["mic"]:
        raw["mic"] += 1
    elif au["file"]:
        raw["file"] += 1
    else:
        raw["silent"] += 1
print("  audio recount from case files:", raw, "| from note:", exp)
if (raw["mic"], raw["file"], raw["both"], raw["silent"], raw["absent"]) != exp:
    fail(f"audio recount {raw} != note {exp}")
# limits that contradict phone calls
for line in rep.limits:
    if "no speech was recorded or transcribed" in line or "the calls are synthetic and simulated" in line:
        fail(f"limit contradicts the phone calls in this batch: '{line[:110]}'")
# skipped visible
log = attempt_log_view(batch)
if len(log.not_ingested) != len(found.skipped) or rep.phone_sessions_not_ingested != len(found.skipped):
    fail(f"skipped visible: log {len(log.not_ingested)}, report {rep.phone_sessions_not_ingested}, ingest {len(found.skipped)}")
print("  ingest note:", rep.ingest_note)

# ---- idempotent ----------------------------------------------------------------------------
h1, r1 = hashes(ops), build_report(store).model_dump_json()
for k in (2, 3):
    f2, err = run_ingest(store, SESS)
    if err:
        fail(f"ingest {k} raised {err}")
        continue
    if hashes(ops) != h1:
        changed = [p for p in set(h1) | set(hashes(ops)) if h1.get(p) != hashes(ops).get(p)]
        fail(f"ingest {k} changed files {changed}")
    if build_report(store).model_dump_json() != r1:
        fail(f"ingest {k} changed the report")
print("  ingest 2 and 3: store hashes equal:", hashes(ops) == h1)

# ---- rebuild: failed -> ready --------------------------------------------------------------
for c in (rebuild, rebuild_out, third[2]):
    c2 = {**c, "status": "ready"}
    put(SESS, c2)
f3, err = run_ingest(store, SESS)
if err:
    fail(f"ingest after rebuild raised {err}")
else:
    batch = load_batch(store)
    for c in (rebuild, third[2]):
        s = next(x for x in batch.sampled if any(getattr(a.source, "session_id", None) == c["session_id"] for a in x.attempts))
        print(f"  rebuilt {c['session_id']}: status {s.status.value}, counted {s.counted}, n attempts {len(s.attempts)}")
        if s.status.value != "completed" or s.call is None:
            fail(f"rebuilt {c['session_id']} not completed: {s.status}")
    o = next(x for x in batch.outside if x.call.session_id == rebuild_out["session_id"])
    print(f"  rebuilt outside: outcome {o.call.outcome.value}, call {'yes' if o.record else 'no'}; skipped as: {dict(f3.skipped).get(rebuild_out['session_id'])}")
    if o.call.outcome.value != "completed" or o.record is None:
        fail("rebuilt outside call not completed")
    for x in invariants(store, SESS):
        fail(f"invariant after rebuild: {x}")
    h2 = hashes(ops)
    run_ingest(store, SESS)
    if hashes(ops) != h2:
        fail("ingest after rebuild not idempotent")
# ready -> failed again, and ready with another result: skipped, nothing changes
h2, r2 = hashes(ops), build_report(store).model_dump_json()
put(SESS, {**rebuild, "status": "failed"})
f4, err = run_ingest(store, SESS)
why = dict(f4.skipped).get(rebuild["session_id"]) if f4 else err
print("  ready->failed again:", why)
if hashes(ops) != {**h2, "ingest.json": hashes(ops).get("ingest.json")} or build_report(store).model_dump_json().replace(
    '"phone_sessions_not_ingested"', ""
) == "":
    pass
changed = [p for p in h2 if p != "ingest.json" and h2[p] != hashes(ops).get(p)]
if changed:
    fail(f"ready->failed changed {changed}")
altered = {**rebuild, "status": "ready", "result": {**rebuild["result"]}}
altered["result"] = json.loads(json.dumps(altered["result"]).replace('"clear"', '"refer"', 1)) if '"clear"' in json.dumps(altered["result"]) else altered["result"]
altered["models"] = {"extraction": {"model": "another-model"}}
put(SESS, altered)
f5, err = run_ingest(store, SESS)
print("  ready with another analysis:", dict(f5.skipped).get(rebuild["session_id"]) if f5 else err)
changed = [p for p in h2 if p != "ingest.json" and h2[p] != hashes(ops).get(p)]
if changed:
    fail(f"altered ready changed {changed}")
for x in invariants(store, SESS):
    fail(f"invariant after altered case file: {x}")
rep = build_report(store)
print("  ingest note now:", rep.ingest_note)
put(SESS, {**rebuild, "status": "ready"})  # put back

# ---- interrupted supersede: crash between saving the call and logging the line ------------
d, ib = next_loan()
ic = case_file(store, ib, cust[ib.record.loan_id], d.as_of, started(), status="failed")
put(SESS, ic)
run_ingest(store, SESS)
put(SESS, {**ic, "status": "ready"})
orig = OpsStore.add_attempt


def crash(self, attempt):
    if attempt.supersedes is not None:
        raise KeyboardInterrupt("simulated crash")
    return orig(self, attempt)


OpsStore.add_attempt = crash
_, err = run_ingest(store, SESS)
OpsStore.add_attempt = orig
orphan = (ops / "calls" / f"{ic['session_id']}.json").exists()
print(f"  crash during supersede: {err}; call file left: {orphan}")
f6, err = run_ingest(store, SESS)
print("  ingest after crash:", err or f6.describe().splitlines()[0])
for x in invariants(store, SESS):
    fail(f"invariant after crash recovery: {x}")
s = next(x for x in load_batch(store).sampled if x.drawn.loan_id == ib.record.loan_id)
if s.status.value != "completed":
    fail(f"after crash recovery status {s.status}")

# ---- a half-written line in attempts.jsonl (a crash mid-append) -----------------------------
half = STATE / "half"
shutil.copytree(STATE / "A", half)
hs = OpsStore(half / "ops")
with (half / "ops" / "attempts.jsonl").open("a") as fh:
    fh.write('{"attempt_id": "D-2027-02-10/x/half", "draw_')
d, hb = next_loan()
put(half / "sessions", case_file(hs, hb, None, d.as_of, started(), outcome="no_response"))
fh_res, err = run_ingest(hs, half / "sessions")
print("  half line then ingest:", err or fh_res.describe().splitlines()[0])
try:
    load_batch(hs)
    print("  half line: store still loads")
except Exception as e:  # noqa: BLE001
    fail(f"a half-written line followed by an ingest leaves the store unreadable: {type(e).__name__}: {str(e).splitlines()[0][:120]}")

# ---- the real sessions, copied without audio ----------------------------------------------
if REAL is not None:
    rs = STATE / "real"
    shutil.copytree(STATE / "A" / "ops", rs / "ops")
    shutil.copytree(REAL, rs / "sessions")
    st = OpsStore(rs / "ops")
    fr, err = run_ingest(st, rs / "sessions")
    if err:
        fail(f"real copies: ingest raised {err}")
    else:
        print(f"  real copies: {len(fr.linked)} linked, {len(fr.outside)} outside, {len(fr.skipped)} skipped")
        kinds = {}
        for sid, why in fr.skipped:
            kinds[why.split(":")[0][:90]] = kinds.get(why.split(":")[0][:90], 0) + 1
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"     {v} x {k}")
        rr = build_report(st)
        print("  real phone note:", next((x for x in rr.limits if x.startswith("Calls marked Phone")), None))
        for x in invariants(st, rs / "sessions"):
            fail(f"real: {x}")
        h = hashes(rs / "ops")
        run_ingest(st, rs / "sessions")
        if hashes(rs / "ops") != h:
            fail("real copies: second ingest changed the store")

print("FAILURES:", len(FAILS))
