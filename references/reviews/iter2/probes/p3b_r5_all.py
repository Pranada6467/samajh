"""P3b round 5: folder gone, limits wording, reason caps, bad result shapes, equal time.

usage: uv run python references/reviews/iter2/probes/p3b_r5_all.py <state dir>
Writes only under <state dir>. No network.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import at_ist, case_file, hashes, invariants, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.simulate import run_draw, scripted_analysis  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.views import attempt_log_view, batch_view, case_view, queue_view  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
NOW = datetime(2027, 7, 1, tzinfo=UTC)
T = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
LONGEST = [0, ""]


def where(f, sid):
    return (["linked"] if sid in f.linked else []) + (["outside"] if sid in f.outside else []) + (
        ["skipped"] if any(s == sid for s, _ in f.skipped) else [])


def raw(root):
    eff, outs = {}, {}
    p = root / "attempts.jsonl"
    for l in (p.read_text().splitlines() if p.exists() else []):
        if l:
            r = json.loads(l); eff[r["attempt_id"]] = r
    p = root / "outside.jsonl"
    for l in (p.read_text().splitlines() if p.exists() else []):
        if l:
            o = json.loads(l); outs[o["session_id"]] = o
    return eff, outs


def reasons_check(tag, f, root):
    for kind, lst in (("skipped", f.skipped), ("changed", f.changed)):
        for sid, why in lst:
            if len(why) > LONGEST[0]:
                LONGEST[0], LONGEST[1] = len(why), f"{tag} {kind}"
            if len(why) > 300:
                FAILS.append(f"[{tag}] {kind} reason {len(why)} chars: {why[:80]}")
            if len(why) == 300 and not why.endswith("…"):
                FAILS.append(f"[{tag}] {kind} reason exactly 300, no ellipsis")
    j = json.loads((root / "ingest.json").read_text())
    for s in j["skipped"]:
        if len(s["reason"]) > 300:
            FAILS.append(f"[{tag}] ingest.json skipped reason {len(s['reason'])}")
    for s in j.get("changed", []):
        if len(s.get("differs", "")) > 300:
            FAILS.append(f"[{tag}] ingest.json changed reason {len(s['differs'])}")


def full_check(tag, st, sess, f):
    """every folder + store session in exactly one list; note counts vs raw; views don't raise."""
    eff, outs = raw(st.root)
    phone = {a["source"]["session_id"] for a in eff.values() if a["source"]["kind"] == "phone_session"}
    store_s = phone | set(outs)
    folders = {p.name for p in sess.iterdir() if p.is_dir()} if sess.is_dir() else set()
    listed = f.linked + f.outside + [s for s, _ in f.skipped]
    dup = {x for x in listed if listed.count(x) > 1}
    if dup:
        FAILS.append(f"[{tag}] listed twice {sorted(dup)}")
    exp = folders | (store_s if sess.is_dir() else set())
    if set(listed) != exp and sess.is_dir():
        FAILS.append(f"[{tag}] listed vs folders+store: missing {sorted(exp - set(listed))} extra {sorted(set(listed) - exp)}")
    for s, _ in f.skipped:
        if s in store_s:
            FAILS.append(f"[{tag}] {s} skipped but in store")
    for s in store_s:
        if sess.is_dir() and s not in folders and not any(c == s for c, w in f.changed if "folder" in w.lower()):
            FAILS.append(f"[{tag}] {s} folder gone but changed lacks folder words: {[w for c, w in f.changed if c == s]}")
    reasons_check(tag, f, st.root)
    try:
        b = load_batch(st)
        log = attempt_log_view(b)
        rep = build_report(st, NOW)
        batch_view(b); qv = queue_view(b)
        for cid in set(re.findall(r'"case_id": "([^"]+)"', qv.model_dump_json()))[:5] if False else list(set(re.findall(r'"case_id": "([^"]+)"', qv.model_dump_json())))[:5]:
            case_view(b, cid)
    except Exception as e:  # noqa: BLE001
        FAILS.append(f"[{tag}] view raised {type(e).__name__}: {e}")
        return
    note = log.ingest_note
    for c in log.changed:
        if len(c.differs if hasattr(c, "differs") else str(c)) > 300:
            FAILS.append(f"[{tag}] attempt log changed reason > 300")
    for v in log.not_ingested:
        r = getattr(v, "reason", "")
        if len(r) > 300:
            FAILS.append(f"[{tag}] attempt log not_ingested reason {len(r)}")
    print(f"[{tag}] linked={len(f.linked)} outside={len(f.outside)} skipped={len(f.skipped)} changed={len(f.changed)} "
          f"raw phone attempts={len(phone)} outside={len(outs)}\n    note: {note[:260]}")
    nums = [int(x) for x in re.findall(r"\d+", note)]
    if f.linked and len(phone) not in nums:
        FAILS.append(f"[{tag}] note lacks phone attempt count {len(phone)}: {note[:200]}")
    if f.outside and len(outs) not in nums:
        FAILS.append(f"[{tag}] note lacks outside count {len(outs)}: {note[:200]}")
    for x in invariants(st, None):
        FAILS.append(f"[{tag}] invariant {x}")


# ---------- claim 1: folders gone ----------
st, meta, loans, cust = new_batch(STATE / "c1", seed=90210, n=50, draws=[(date(2027, 5, 3), 0.8)],
                                  sold_from=date(2027, 4, 20), days=12)
by = {b.record.loan_id: b for b in loans}
drawn = [by[x.loan_id] for x in st.draws()[0].drawn]
und = [b for b in loans if b.record.loan_id not in {x.loan_id for x in st.draws()[0].drawn}]
SESS = STATE / "c1" / "sessions"; SESS.mkdir()
CD = date(2027, 5, 6)
mk = lambda i, loan, **kw: case_file(st, loan, cust[loan.record.loan_id], CD, T + timedelta(minutes=13 * i), **kw)
cs = [mk(1, drawn[0]), mk(2, drawn[1], outcome="no_response"), mk(3, und[0]), mk(4, und[1], book=False),
      mk(5, drawn[2], status="failed"), mk(6, drawn[3])]
for c in cs:
    put(SESS, c)
S = [c["session_id"] for c in cs]
f = ingest(st, SESS, packaged_records())
print("c1 first:", f.describe().splitlines()[0])
# supersede S[4]
p = SESS / S[4] / "case.json"; c = json.loads(p.read_text()); c["status"] = "ready"; p.write_text(json.dumps(c))
f = ingest(st, SESS, packaged_records())
print("c1 supersede:", f.describe().splitlines()[0])
BASE = {k: v for k, v in hashes(st.root).items() if k != "ingest.json"}
shutil.copytree(STATE / "c1", STATE / "c1_base")

# (a) delete attempts + outside mixed + superseded, add new sessions same run
saved = {s: (SESS / s / "case.json").read_bytes() for s in S}
for s in (S[0], S[2], S[3], S[4]):
    shutil.rmtree(SESS / s)
new = [mk(7, drawn[4]), mk(8, und[2])]
for c in new:
    put(SESS, c)
f = ingest(st, SESS, packaged_records())
full_check("1a mixed gone + new", st, SESS, f)
for s in (S[0], S[2], S[3], S[4]):
    if where(f, s) not in (["linked"], ["outside"]):
        FAILS.append(f"[1a] {s} place {where(f, s)}")
h1 = {k: v for k, v in hashes(st.root).items() if k != "ingest.json"}
f2 = ingest(st, SESS, packaged_records())
if {k: v for k, v in hashes(st.root).items() if k != "ingest.json"} != h1:
    FAILS.append("[1a] second ingest changed store")
# replace S[0] by a FILE
(SESS / S[0]).write_text("x")
f = ingest(st, SESS, packaged_records())
full_check("1b file in place", st, SESS, f)
if not any(c == S[0] for c, _ in f.changed):
    FAILS.append(f"[1b] file-in-place not changed: {where(f, S[0])}")
(SESS / S[0]).unlink()
# folders come back unchanged
for s in (S[0], S[2], S[3], S[4]):
    (SESS / s).mkdir(); (SESS / s / "case.json").write_bytes(saved[s])
f = ingest(st, SESS, packaged_records())
full_check("1c back unchanged", st, SESS, f)
if f.changed:
    FAILS.append(f"[1c] back unchanged still changed: {f.changed}")
# comes back DIFFERENT
shutil.rmtree(SESS / S[2])
c = json.loads(saved[S[2]]); c["language"] = "kn"; put(SESS, c)
f = ingest(st, SESS, packaged_records())
full_check("1d back different", st, SESS, f)
print("   1d changed:", [(s[-6:], w[:90]) for s, w in f.changed])
if not any(s == S[2] for s, _ in f.changed):
    FAILS.append("[1d] different case file not changed")
# all deleted
for p in list(SESS.iterdir()):
    shutil.rmtree(p) if p.is_dir() else p.unlink()
hb = {k: v for k, v in hashes(st.root).items() if k != "ingest.json"}
f = ingest(st, SESS, packaged_records())
full_check("1e empty dir", st, SESS, f)
if {k: v for k, v in hashes(st.root).items() if k != "ingest.json"} != hb:
    FAILS.append("[1e] store changed")
# CLI on empty dir
env = dict(os.environ, PYTHONPATH=str(REPO))
r = subprocess.run([sys.executable, "-m", "samajh.ops", "ingest", "--state", str(STATE / "c1")], capture_output=True, text=True, env=env, cwd=REPO)
print("   CLI ingest empty:", r.returncode, r.stdout.splitlines()[:1], r.stderr[-200:])
r2 = subprocess.run([sys.executable, "-m", "samajh.ops", "report", "--state", str(STATE / "c1")], capture_output=True, text=True, env=env, cwd=REPO)
print("   CLI report:", r2.returncode, len(r2.stdout), r2.stderr[-200:])
if r.returncode or r2.returncode:
    FAILS.append(f"[1e CLI] rc {r.returncode} {r2.returncode}: {r.stderr[-200:]} {r2.stderr[-200:]}")
# missing directory
shutil.rmtree(SESS)
try:
    f = ingest(st, SESS, packaged_records())
    print(f"[1f missing dir] linked={f.linked} outside={f.outside} skipped={f.skipped} changed={len(f.changed)}")
    if {k: v for k, v in hashes(st.root).items() if k != "ingest.json"} != hb:
        FAILS.append("[1f] store changed")
    b = load_batch(st); attempt_log_view(b); build_report(st, NOW)
    print("   1f note:", attempt_log_view(b).ingest_note[:250])
except Exception as e:  # noqa: BLE001
    FAILS.append(f"[1f] raised {type(e).__name__}: {e}")
r = subprocess.run([sys.executable, "-m", "samajh.ops", "ingest", "--state", str(STATE / "c1")], capture_output=True, text=True, env=env, cwd=REPO)
print("   CLI ingest missing dir:", r.returncode, r.stdout.splitlines()[:1], r.stderr[-200:])

# ---------- claim 3 + 4 ----------
st, meta, loans, cust = new_batch(STATE / "c3", seed=4242, n=40, draws=[(date(2027, 3, 2), 0.8)],
                                  sold_from=date(2027, 2, 20), days=8)
by = {b.record.loan_id: b for b in loans}
drawn = [by[x.loan_id] for x in st.draws()[0].drawn]
SESS = STATE / "c3" / "sessions"; SESS.mkdir()
CD = date(2027, 3, 4)
L = "Z" * 900
i = [0]


def mk3(loan, **kw):
    i[0] += 1
    return case_file(st, loan, cust[loan.record.loan_id], CD, T + timedelta(minutes=5 * i[0]), **kw)


bad = {
    "long_loan": mk3(drawn[0], loan_id=L, record_id=L),
    "long_record": mk3(drawn[1], record_id=L),
    "long_outcome": mk3(drawn[2], call_outcome=L),
    "long_language": mk3(drawn[3], language=L),
    "long_status": mk3(drawn[4], status=L),
    "long_batch": mk3(drawn[5], book_over={"batch_id": L}),
    "long_draw": mk3(drawn[6], book_over={"draw_id": L}),
    "long_sid": mk3(drawn[7], session_id=L),
    "res_empty": mk3(drawn[8], result={}),
    "res_list": mk3(drawn[9], result=[1, 2]),
    "res_str": mk3(drawn[10], result="x"),
    "res_loan5": mk3(drawn[11], result={"loan_id": 5}),
}
ok_case = mk3(drawn[13])
prod_bad = mk3(drawn[12])
if isinstance(prod_bad.get("result"), dict):
    for k, v in prod_bad["result"].items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            prod_bad["result"][k] = [{"nonsense": [1]}]
            break
bad["res_product"] = prod_bad
short = mk3(drawn[14], book_over={"batch_id": "B-x"})
sid_ = mk3(drawn[7])["session_id"]
for k, c in bad.items():
    put(SESS, c, name=sid_ if k == "long_sid" else c["session_id"])
put(SESS, ok_case)
put(SESS, short)
(SESS / ("20270101T000000-" + "a" * 12 + "q" * 220)).mkdir()  # long folder name
f = ingest(st, SESS, packaged_records())
for k, c in bad.items():
    sid = c["session_id"] if k != "long_sid" else sid_
    w = [why for s, why in f.skipped if s == sid]
    print(f"  {k}: {where(f, sid)} {w[0][:110] if w else ''!r} ({len(w[0]) if w else 0})")
    if k.startswith("res_") and (not w or not w[0].startswith("case file could not be read: result.")):
        FAILS.append(f"[4 {k}] reason {w}")
if ok_case["session_id"] not in f.linked:
    FAILS.append(f"[4] sound session not linked: {where(f, ok_case['session_id'])}")
sw = [w for s, w in f.skipped if s == short["session_id"]]
print("  short reason:", sw)
reasons_check("3 skips", f, st.root)
full_check("3 skips", st, SESS, f)
r = subprocess.run([sys.executable, "-m", "samajh.ops", "ingest", "--state", str(STATE / "c3")], capture_output=True, text=True, env=env, cwd=REPO)
for line in r.stdout.splitlines():
    m = re.match(r"\s+(skipped|changed after it was brought in) (\S+): (.*)", line)
    if m and len(m.group(3)) > 300:
        FAILS.append(f"[3 CLI] reason {len(m.group(3))}")
# changed path: long keys + result {} on linked
p = SESS / ok_case["session_id"] / "case.json"; c = json.loads(p.read_text())
c["models"] = {("k" * 400): {("m" * 400): "x"}}
c["transcript"]["turns"][0]["text"] = "y" * 2000
p.write_text(json.dumps(c))
f = ingest(st, SESS, packaged_records())
print("  changed long:", [(len(w), w[-30:]) for s, w in f.changed])
full_check("3 changed long", st, SESS, f)
c["result"] = {}
p.write_text(json.dumps(c))
f = ingest(st, SESS, packaged_records())
print("  changed result {}:", [w[:120] for s, w in f.changed])
full_check("4 linked result {}", st, SESS, f)

# ---------- claim 5 ----------
for order in ("ab", "ba"):
    for first in ("completed", "no_response"):
        tag = f"5 {order} {first}"
        st, meta, loans, cust = new_batch(STATE / f"c5{order}{first}", seed=777, n=20,
                                          draws=[(date(2027, 2, 2), 1.0)], sold_from=date(2027, 1, 28), days=3)
        by = {b.record.loan_id: b for b in loans}
        loan = by[st.draws()[0].drawn[0].loan_id]
        SESS = STATE / f"c5{order}{first}" / "sessions"; SESS.mkdir()
        other = "no_response" if first == "completed" else "completed"
        t1 = at_ist(date(2026, 11, 10), 15, 20)
        t2 = at_ist(date(2026, 11, 11), 15, 20)  # different wall day, same IST time; same call date
        a = case_file(st, loan, cust[loan.record.loan_id], date(2027, 2, 4), t1, outcome=first)
        b_ = case_file(st, loan, cust[loan.record.loan_id], date(2027, 2, 4), t2, outcome=other)
        if order == "ba":
            a["session_id"], b_["session_id"] = "20261109T000000-ffffffffffff", "20261109T000000-000000000001"
        put(SESS, a); put(SESS, b_)
        f = ingest(st, SESS, packaged_records())
        eff, _ = raw(st.root)
        n = sum(1 for x in eff.values() if x["loan_id"] == loan.record.loan_id)
        print(f"[{tag}] attempts={n} skipped={[w[:90] for _, w in f.skipped]}")
        if n != 1 or len(f.skipped) != 1 or not f.skipped[0][1].strip():
            FAILS.append(f"[{tag}] attempts={n} skipped={f.skipped}")

# ---------- claim 2 ----------
BAN = re.compile(r"finding|refund|proven|verdict|violat|breach|fraud|mis-?sell|mis-?sold|guilty|non-compliant", re.I)


def strings(x, out):
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            strings(v, out)
    elif isinstance(x, (list, tuple)):
        for v in x:
            strings(v, out)
    return out


def scan2(tag, st):
    b = load_batch(st)
    eff, outs = raw(st.root)
    sim = sum(a["source"]["kind"] == "simulated" for a in eff.values())
    ph = sum(a["source"]["kind"] == "phone_session" for a in eff.values())
    views = {"report": build_report(st, NOW).model_dump(mode="json"), "batch": batch_view(b).model_dump(mode="json"),
             "queue": queue_view(b).model_dump(mode="json"), "log": attempt_log_view(b).model_dump(mode="json")}
    for cid in sorted(set(re.findall(r'"case_id": "([^"]+)"', json.dumps(views["queue"]))))[:20]:
        v = case_view(b, cid).model_dump(mode="json")
        v.pop("transcript", None)
        views[f"case {cid}"] = v
    hits = []
    for name, v in views.items():
        for s in strings(v, []):
            low = s.lower()
            if sim == 0 and ("simulation" in low or "simulated customer" in low or "text only" in low
                             or "text-only" in low or "synthetic and simulated" in low
                             or re.search(r"\bsimulated\b", low) and "no attempt in this batch was simulated" not in low):
                hits.append(f"{name}: {s[:200]}")
            if BAN.search(s):
                FAILS.append(f"[2 {tag}] banned word in {name}: {s[:200]}")
            m = re.search(r"(\d+) attempt\(s\) in this batch were simulated", s)
            if m and int(m.group(1)) != sim:
                FAILS.append(f"[2 {tag}] says {m.group(1)} simulated, recount {sim}")
    for h in sorted(set(hits)):
        FAILS.append(f"[2 {tag}] sim words with 0 simulated: {h}")
    if sim and not any(re.search(r"attempt\(s\) in this batch were simulated", s) for v in views.values() for s in strings(v, [])):
        FAILS.append(f"[2 {tag}] no simulation sentence with {sim} simulated")
    print(f"[2 {tag}] sim={sim} phone={ph} outside={len(outs)} views={len(views)}")


def b2(tag, seed):
    return new_batch(STATE / tag, seed=seed, n=45, draws=[(date(2027, 4, 13), 0.7)], sold_from=date(2027, 4, 1), days=10)


st, meta, loans, cust = b2("w1", 6061)  # only phone attempts
by = {b.record.loan_id: b for b in loans}; SESS = STATE / "w1" / "sessions"
for k, x in enumerate(st.draws()[0].drawn[:5]):
    put(SESS, case_file(st, by[x.loan_id], cust[x.loan_id], date(2027, 4, 15), T + timedelta(minutes=9 * k)))
ingest(st, SESS, packaged_records()); scan2("phone only", st)
st, meta, loans, cust = b2("w2", 6062)  # only outside
by = {b.record.loan_id: b for b in loans}; SESS = STATE / "w2" / "sessions"
dr = {x.loan_id for x in st.draws()[0].drawn}
u = next(b for b in loans if b.record.loan_id not in dr)
put(SESS, case_file(st, u, cust[u.record.loan_id], date(2027, 4, 15), T))
ingest(st, SESS, packaged_records()); scan2("outside only", st)
st, meta, loans, cust = b2("w3", 6063)  # only late phone
by = {b.record.loan_id: b for b in loans}; SESS = STATE / "w3" / "sessions"
for k, x in enumerate(st.draws()[0].drawn[:3]):
    put(SESS, case_file(st, by[x.loan_id], cust[x.loan_id], by[x.loan_id].sold_on + timedelta(days=33 + k), T + timedelta(minutes=9 * k)))
ingest(st, SESS, packaged_records()); scan2("late phone only", st)
st, meta, loans, cust = b2("w4", 6064)  # phone + simulated
by = {b.record.loan_id: b for b in loans}; SESS = STATE / "w4" / "sessions"
for k, x in enumerate(st.draws()[0].drawn[:3]):
    put(SESS, case_file(st, by[x.loan_id], cust[x.loan_id], date(2027, 4, 14), T + timedelta(minutes=9 * k)))
ingest(st, SESS, packaged_records())
run_draw(st, st.draws()[0], cust, scripted_analysis); scan2("phone + simulated", st)

print(f"\nlongest reason seen: {LONGEST}")
print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x[:500])
