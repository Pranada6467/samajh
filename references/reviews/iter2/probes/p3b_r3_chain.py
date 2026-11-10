"""P3b round 3: order and numbering when phone sessions and the simulator both write a loan's chain
(claim 6), on a book, seed and dates the builders never used.

Usage: uv run python references/reviews/iter2/probes/p3b_r3_chain.py <state dir>
Writes only under <state dir>. Prints a line per scenario and FAIL lines.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import IST, at_ist, case_file, hashes, invariants, new_batch, put  # noqa: E402

from samajh.ops import book as books  # noqa: E402
from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.chain import chain_of  # noqa: E402
from samajh.ops.model import RETRY_AFTER  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.simulate import run_draw, scripted_analysis  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
REPO = Path(__file__).resolve().parents[4]


def fail(m: str) -> None:
    FAILS.append(m)
    print("FAIL", m)


def check(store: OpsStore, sessions: Path, label: str) -> None:
    for x in invariants(store, sessions):
        fail(f"{label}: {x}")


def run_all(store: OpsStore, cust) -> str | None:
    try:
        for d in store.draws():
            run_draw(store, d, cust, scripted_analysis)
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"[:200]
    return None


def chain_str(store: OpsStore, lid: str) -> str:
    return " ".join(
        f"{a.number}:{a.day_since_sale}d:{a.outcome.value}:{'P' if a.source.kind == 'phone_session' else 'S'}"
        for a in chain_of(store.attempts(), lid)
    )


DRAWS = [(date(2027, 1, 27), 0.6), (date(2027, 2, 5), 0.6), (date(2027, 2, 14), 0.6), (date(2027, 2, 22), 0.6)]
wall = iter(range(10**6))


def started(hh: int | None = None, day: int = 10) -> datetime:
    if hh is not None:
        return at_ist(date(2026, 11, day), hh, next(wall) % 60)
    return datetime(2026, 11, 10, 3, 0, tzinfo=UTC) + timedelta(minutes=next(wall))


# ======== S1: phone attempts first, then the simulator (in-process run_draw and the CLI) ==========
store, meta, loans, cust = new_batch(STATE / "S1", 2718, 70, DRAWS, sold_from=date(2027, 1, 20), days=30)
by_id = {b.record.loan_id: b for b in loans}
drawn = [(d, by_id[x.loan_id]) for d in store.draws() for x in d.drawn]
print(f"S1 book: {len(loans)} loans, {len(drawn)} drawn")
sess = STATE / "S1" / "sessions"
plan = {}
it = iter(drawn)
# a: one phone no-answer on the draw day; b: two phone no-answers (days 0 and 2 after the draw)
# c: phone no-answer on day 30 from the sale; d: phone call_back_later then phone completed
# e: phone do_not_call; f: three phone no-answers (the limit)
for tag in "aaaabbcdef":
    d, b = next(it)
    lid = b.record.loan_id
    if tag == "a":
        put(sess, case_file(store, b, None, d.as_of, started(), outcome="no_response"))
    elif tag == "b":
        put(sess, case_file(store, b, None, d.as_of, started(), outcome="no_response"))
        put(sess, case_file(store, b, None, d.as_of + timedelta(days=2), started(), outcome="no_response"))
    elif tag == "c":
        put(sess, case_file(store, b, None, b.sold_on + timedelta(days=30), started(), outcome="no_response"))
    elif tag == "d":
        put(sess, case_file(store, b, None, d.as_of, started(), outcome="call_back_later"))
        put(sess, case_file(store, b, cust[lid], d.as_of + timedelta(days=1), started()))
    elif tag == "e":
        put(sess, case_file(store, b, None, d.as_of, started(), outcome="do_not_call"))
    elif tag == "f":
        for k in range(3):
            put(sess, case_file(store, b, None, d.as_of + timedelta(days=k), started(), outcome="no_response"))
    plan.setdefault(tag, []).append(lid)
found = ingest(store, sess, packaged_records())
print("S1 ingest:", found.describe().splitlines()[0])
check(store, sess, "S1 after ingest")
book_dir = STATE / "S1" / "bookdir"
meta2, loans2, customers2 = books.generate_book(2718, 70, sold_from=date(2027, 1, 20), days=30)
books.write_book(book_dir, meta2, loans2, customers2)
r = subprocess.run(
    [sys.executable, "-m", "samajh.ops", "run", "--state", str(STATE / "S1"), "--book", str(book_dir)],
    cwd=REPO, capture_output=True, text=True, timeout=600,
)
print("S1 CLI run exit", r.returncode, (r.stderr.strip().splitlines() or [""])[-1][:200])
check(store, sess, "S1 after run")
for tag, lids in plan.items():
    for lid in lids:
        print(f"  S1 {tag} {lid}: {chain_str(store, lid)}")
for lid in plan["f"] + plan["e"]:
    if any(a.source.kind == "simulated" for a in chain_of(store.attempts(), lid)):
        fail(f"S1 simulator added to a loan at its limit or after do_not_call: {chain_str(store, lid)}")
for lid in plan["c"]:
    ch = chain_of(store.attempts(), lid)
    if len(ch) != 1:
        fail(f"S1 simulator called after a day-30 phone no-answer: {chain_str(store, lid)}")
    s = next(x for x in load_batch(store).sampled if x.drawn.loan_id == lid)
    print(f"  S1 c status: {s.status.value}")
h = hashes(STATE / "S1" / "ops")
r2 = subprocess.run(
    [sys.executable, "-m", "samajh.ops", "run", "--state", str(STATE / "S1"), "--book", str(book_dir)],
    cwd=REPO, capture_output=True, text=True, timeout=600,
)
if hashes(STATE / "S1" / "ops") != h:
    fail("S1 second CLI run changed the store")
found = ingest(store, sess, packaged_records())
if hashes(STATE / "S1" / "ops") != h:
    fail("S1 ingest after run changed the store")
print("S1 second run and re-ingest: unchanged:", hashes(STATE / "S1" / "ops") == h)

# ======== S2: the simulator first, then phone sessions ==========================================
store, meta, loans, cust = new_batch(STATE / "S2", 2718, 70, DRAWS, sold_from=date(2027, 1, 20), days=30)
sess = STATE / "S2" / "sessions"
err = run_all(store, cust)
print("S2 run:", err or "ok")
batch = load_batch(store)
pick = {}
for s in batch.sampled:
    ch = s.attempts
    last = ch[-1] if ch else None
    if last is None:
        continue
    key = (
        "completed" if last.outcome.value == "completed"
        else "terminal" if last.outcome not in RETRY_AFTER
        else "limit" if len(ch) >= 3
        else "open"
    )
    pick.setdefault(key, []).append(s)
print("S2 chains:", {k: len(v) for k, v in pick.items()})
cases = []
for s in pick.get("completed", [])[:3]:
    last = s.attempts[-1]
    c = case_file(store, s.loan, None, s.loan.sold_on + timedelta(days=last.day_since_sale + 1), started(), outcome="no_response")
    cases.append(("after completed", s.drawn.loan_id, c, "skipped"))
for s in pick.get("terminal", [])[:2]:
    last = s.attempts[-1]
    c = case_file(store, s.loan, cust[s.drawn.loan_id], s.loan.sold_on + timedelta(days=last.day_since_sale + 1), started())
    cases.append(("after terminal", s.drawn.loan_id, c, "skipped"))
for s in pick.get("limit", [])[:2]:
    last = s.attempts[-1]
    c = case_file(store, s.loan, None, s.loan.sold_on + timedelta(days=last.day_since_sale + 1), started(), outcome="no_response")
    cases.append(("beyond limit", s.drawn.loan_id, c, "skipped"))
for s in pick.get("open", [])[:3]:
    last = s.attempts[-1]
    c = case_file(store, s.loan, None, s.loan.sold_on + timedelta(days=last.day_since_sale - 1), started(), outcome="no_response")
    cases.append(("before last attempt", s.drawn.loan_id, c, "skipped"))
    c = case_file(store, s.loan, None, s.loan.sold_on + timedelta(days=last.day_since_sale),
                  datetime.combine(date(2026, 11, 10), datetime.min.time(), tzinfo=IST).astimezone(UTC) + timedelta(hours=9), outcome="no_response")
    cases.append(("same day 09:00 IST before 11:00 sim", s.drawn.loan_id, c, "skipped"))
    c = case_file(store, s.loan, None, s.loan.sold_on + timedelta(days=last.day_since_sale), at_ist(date(2026, 11, 10), 15), outcome="no_response")
    cases.append(("same day 15:00 IST after 11:00 sim", s.drawn.loan_id, c, "linked"))
for _, _, c, _ in cases:
    put(sess, c)
before = {lid: chain_str(store, lid) for _, lid, _, _ in cases}
status_before = {s.drawn.loan_id: s.status for s in load_batch(store).sampled}
found = ingest(store, sess, packaged_records())
got = {x: "linked" for x in found.linked} | {x: "outside" for x in found.outside} | {x: "skipped" for x, _ in found.skipped}
why = dict(found.skipped)
for label, lid, c, want in cases:
    g = got.get(c["session_id"])
    print(f"  S2 {label:36s} {lid}: {g} {why.get(c['session_id'], '')[:110]}")
    if g != want:
        fail(f"S2 {label}: expected {want}, got {g}")
for label, lid, c, want in cases:
    if want == "skipped" and chain_str(store, lid) != before[lid] and "same day" not in label:
        fail(f"S2 {label}: chain changed {before[lid]} -> {chain_str(store, lid)}")
status_after = {s.drawn.loan_id: s.status for s in load_batch(store).sampled}
for lid, st in status_before.items():
    if st.value == "completed" and status_after[lid].value != "completed":
        fail(f"S2 a completed loan became {status_after[lid]}")
check(store, sess, "S2 after ingest")
h = hashes(STATE / "S2" / "ops")
err = run_all(store, cust)
print("S2 run again:", err or "ok")
check(store, sess, "S2 after second run")
for label, lid, c, want in cases:
    if label.startswith("same day 15"):
        print(f"  S2 after run {lid}: {chain_str(store, lid)}")

# ======== S2b: one simulated attempt per loan (max_attempts=1), then same-day phone calls ======
store, meta, loans, cust = new_batch(STATE / "S2b", 2718, 70, DRAWS, sold_from=date(2027, 1, 20), days=30)
sess = STATE / "S2b" / "sessions"
for d in store.draws():
    run_draw(store, d, cust, scripted_analysis, max_attempts=1)
open_ = [s for s in load_batch(store).sampled if s.attempts and s.attempts[-1].outcome in RETRY_AFTER]
print(f"S2b: {len(open_)} loans with one simulated retry outcome")
cases = []
for i, s in enumerate(open_):
    last = s.attempts[-1]
    day = s.loan.sold_on + timedelta(days=last.day_since_sale)
    kind = i % 4
    if kind == 0:
        c = case_file(store, s.loan, None, day - timedelta(days=1), started(), outcome="no_response")
        cases.append(("day before the sim attempt", s.drawn.loan_id, c, "skipped"))
    elif kind == 1:
        c = case_file(store, s.loan, None, day, at_ist(date(2026, 11, 10), 9), outcome="no_response")
        cases.append(("same day 09:xx IST (sim at 11:00)", s.drawn.loan_id, c, "skipped"))
    elif kind == 2:
        c = case_file(store, s.loan, None, day, at_ist(date(2026, 11, 10), 15), outcome="no_response")
        cases.append(("same day 15:xx IST (sim at 11:00)", s.drawn.loan_id, c, "linked"))
    else:
        c = case_file(store, s.loan, cust[s.drawn.loan_id], day + timedelta(days=1), started())
        cases.append(("next day completed", s.drawn.loan_id, c, "linked"))
for _, _, c, _ in cases:
    put(sess, c)
found = ingest(store, sess, packaged_records())
got = {x: "linked" for x in found.linked} | {x: "skipped" for x, _ in found.skipped} | {x: "outside" for x in found.outside}
for label, lid, c, want in cases:
    if got.get(c["session_id"]) != want:
        fail(f"S2b {label} {lid}: {got.get(c['session_id'])} != {want} {dict(found.skipped).get(c['session_id'], '')[:120]}")
print("S2b ingest:", found.describe().splitlines()[0])
check(store, sess, "S2b after ingest")
err = run_all(store, cust)
print("S2b full run:", err or "ok")
check(store, sess, "S2b after run")
for label, lid, c, want in cases[:8]:
    print(f"  S2b {label:34s} {chain_str(store, lid)}")
ingest(store, sess, packaged_records())
h = hashes(STATE / "S2b" / "ops")
run_all(store, cust)
ingest(store, sess, packaged_records())
if hashes(STATE / "S2b" / "ops") != h:
    fail("S2b run+ingest again changed the store")

# ======== S3: two sessions on one loan, both file orders, and the time-of-day trap ===============
store, meta, loans, cust = new_batch(STATE / "S3", 2718, 70, DRAWS, sold_from=date(2027, 1, 20), days=30)
by_id = {b.record.loan_id: b for b in loans}
drawn = [(d, by_id[x.loan_id]) for d in store.draws() for x in d.drawn]
sess = STATE / "S3" / "sessions"
it = iter(drawn)
results = []
# (i) folder names sort opposite to started_at; distinct call dates
d, b = next(it)
x1 = case_file(store, b, None, d.as_of, started(10), outcome="no_response", sid="20261110T235959-0000000000a1")
x2 = case_file(store, b, None, d.as_of + timedelta(days=1), started(11), outcome="call_back_later", sid="20261110T000001-0000000000a2")
put(sess, x1), put(sess, x2)
results.append(("folder order opposite to time", b.record.loan_id, [x1, x2], ["linked", "linked"]))
# (ii) the same call date (the server's default before either is ingested), later time of day second
d, b = next(it)
y1 = case_file(store, b, None, d.as_of, started(10, day=10), outcome="no_response")
y2 = case_file(store, b, None, d.as_of, started(16, day=10), outcome="no_response")
put(sess, y1), put(sess, y2)
results.append(("same call date, later time of day", b.record.loan_id, [y1, y2], ["linked", "linked"]))
# (iii) the same call date, second session a day later on the wall clock but earlier in the day
d, b = next(it)
z1 = case_file(store, b, None, d.as_of, started(18, day=10), outcome="no_response")
z2 = case_file(store, b, None, d.as_of, started(9, day=11), outcome="no_response")
put(sess, z1), put(sess, z2)
results.append(("same call date, next wall day, earlier hour", b.record.loan_id, [z1, z2], ["linked", "skipped"]))
# (iv) the later call date ingested first (wall clock), then an earlier call date
d, b = next(it)
w1 = case_file(store, b, None, d.as_of + timedelta(days=3), started(10, day=10), outcome="no_response")
w2 = case_file(store, b, None, d.as_of + timedelta(days=1), started(12, day=10), outcome="no_response")
put(sess, w1), put(sess, w2)
results.append(("later call date first on wall clock", b.record.loan_id, [w1, w2], ["linked", "skipped"]))
# (v) completed, then a later no-answer: the completed call stays
d, b = next(it)
v1 = case_file(store, b, cust[b.record.loan_id], d.as_of, started(10, day=10))
v2 = case_file(store, b, None, d.as_of + timedelta(days=2), started(11, day=10), outcome="no_response")
put(sess, v1), put(sess, v2)
results.append(("completed then no-answer", b.record.loan_id, [v1, v2], ["linked", "skipped"]))
# (vi) four sessions on one loan: the fourth beyond the limit
d, b = next(it)
q = [case_file(store, b, None, d.as_of + timedelta(days=k), started(10 + k, day=10), outcome="no_response") for k in range(4)]
for c in q:
    put(sess, c)
results.append(("four sessions", b.record.loan_id, q, ["linked", "linked", "linked", "skipped"]))
found = ingest(store, sess, packaged_records())
got = {x: "linked" for x in found.linked} | {x: "outside" for x in found.outside} | {x: "skipped" for x, _ in found.skipped}
why = dict(found.skipped)
for label, lid, cs, wants in results:
    gs = [got.get(c["session_id"]) for c in cs]
    print(f"  S3 {label:44s}: {gs} | {chain_str(store, lid)}")
    for c, g in zip(cs, gs):
        if g == "skipped":
            print(f"       skipped: {why[c['session_id']][:140]}")
    if gs != wants:
        fail(f"S3 {label}: {gs} != {wants}")
check(store, sess, "S3")
h = hashes(STATE / "S3" / "ops")
# ingest a session that falls between existing ones later (a late-arriving folder with an earlier start)
d, b = next(it)
e1 = case_file(store, b, None, d.as_of + timedelta(days=2), started(12, day=10), outcome="no_response")
put(sess, e1)
ingest(store, sess, packaged_records())
e0 = case_file(store, b, None, d.as_of, started(8, day=10), outcome="no_response")
put(sess, e0)
f = ingest(store, sess, packaged_records())
print(f"  S3 late-arriving earlier session: {dict(f.skipped).get(e0['session_id'], 'not skipped')[:140]} | {chain_str(store, b.record.loan_id)}")
check(store, sess, "S3 late arrival")
err = run_all(store, cust)
print("  S3 run after:", err or "ok")
check(store, sess, "S3 after run")
ingest(store, sess, packaged_records())  # a skipped session's reason may name the new last attempt
h = hashes(STATE / "S3" / "ops")
run_all(store, cust)
ingest(store, sess, packaged_records())
if hashes(STATE / "S3" / "ops") != h:
    fail("S3 run+ingest again changed the store")

# ======== S4: ingest, run, ingest more, run again, many loans ==================================
store, meta, loans, cust = new_batch(STATE / "S4", 9001, 120, [(date(2027, 2, 1), 0.5), (date(2027, 2, 15), 0.5), (date(2027, 3, 1), 0.5)],
                                     sold_from=date(2027, 1, 10), days=50)
by_id = {b.record.loan_id: b for b in loans}
drawn = [(d, by_id[x.loan_id]) for d in store.draws() for x in d.drawn]
sess = STATE / "S4" / "sessions"
import random  # noqa: E402

rng = random.Random(77)
outs = ["no_response", "call_back_later", "language_switch", "completed", "declined", "do_not_call", "written_requested", "turn_limit"]
for d, b in drawn[: len(drawn) // 2]:
    put(sess, case_file(store, b, cust[b.record.loan_id], d.as_of + timedelta(days=rng.randrange(0, 3)), started(), outcome=rng.choice(outs)))
ingest(store, sess, packaged_records())
check(store, sess, "S4 ingest 1")
run_all(store, cust)
check(store, sess, "S4 run 1")
for d, b in drawn:
    ch = chain_of(store.attempts(), b.record.loan_id)
    base = ch[-1].day_since_sale if ch else (d.as_of - b.sold_on).days
    put(sess, case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=base + rng.randrange(-1, 3)), started(), outcome=rng.choice(outs)))
f = ingest(store, sess, packaged_records())
print("S4 ingest 2:", f.describe().splitlines()[0])
check(store, sess, "S4 ingest 2")
err = run_all(store, cust)
check(store, sess, "S4 run 2")
h = hashes(STATE / "S4" / "ops")
run_all(store, cust)
ingest(store, sess, packaged_records())
if hashes(STATE / "S4" / "ops") != h:
    fail("S4 third run + ingest changed the store")
n_att = len(store.attempts())
n_phone = sum(a.source.kind == "phone_session" for a in store.attempts())
print(f"S4: {n_att} attempts ({n_phone} phone) over {len(drawn)} drawn loans")

print("FAILURES:", len(FAILS))
