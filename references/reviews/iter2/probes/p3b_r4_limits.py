"""P3b round 4, claim 3: report limits and notices against what the batch holds (raw recount).

usage: uv run python references/reviews/iter2/probes/p3b_r4_limits.py <state dir>
Writes only under <state dir>. No network.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.simulate import run_draw, scripted_analysis  # noqa: E402
from samajh.ops.views import attempt_log_view, batch_view, case_view, queue_view  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
T = datetime(2026, 11, 10, 7, 0, tzinfo=UTC)


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


def raw_counts(root: Path):
    rows = [json.loads(l) for l in (root / "attempts.jsonl").read_text().splitlines() if l] if (root / "attempts.jsonl").exists() else []
    eff = {}
    for r in rows:
        eff[r["attempt_id"]] = r
    outs = {}
    if (root / "outside.jsonl").exists():
        for l in (root / "outside.jsonl").read_text().splitlines():
            if l:
                o = json.loads(l)
                outs[o["session_id"]] = o
    sim = sum(a["source"]["kind"] == "simulated" for a in eff.values())
    ph = sum(a["source"]["kind"] == "phone_session" for a in eff.values())
    late_ph = sum(a["source"]["kind"] == "phone_session" and a["day_since_sale"] > 30 for a in eff.values())
    return sim, ph, len(outs), late_ph, len(eff)


def scan(tag: str, store):
    b = load_batch(store)
    rep = build_report(store, datetime(2027, 7, 1, tzinfo=UTC))
    views = {"report": rep.model_dump(mode="json"), "batch": batch_view(b).model_dump(mode="json"),
             "queue": queue_view(b).model_dump(mode="json"), "log": attempt_log_view(b).model_dump(mode="json")}
    q = views["queue"]
    ids = set(re.findall(r'"case_id": "([^"]+)"', json.dumps(q)))
    for cid in sorted(ids)[:40]:
        try:
            views[f"case {cid}"] = case_view(b, cid).model_dump(mode="json")
        except Exception as e:  # noqa: BLE001
            FAILS.append(f"[{tag}] case_view({cid}) raised {type(e).__name__}: {e}")
    sim, ph, outn, late_ph, total = raw_counts(store.root)
    phone_any = ph + outn > 0
    allt = []
    for name, v in views.items():
        for s in strings(v, []):
            allt.append((name, s))
    for name, s in allt:
        low = s.lower()
        if phone_any:
            for bad in ("calls are synthetic and simulated", "every call is synthetic", "every call are synthetic",
                        "simulated batch", "they are text only", "customer replies come from scripted phrase banks"):
                if bad in low:
                    FAILS.append(f"[{tag}] {name}: '{bad}' with phone calls: {s[:160]}")
            if "the simulation assumes" in low and sim == 0:
                FAILS.append(f"[{tag}] {name}: speaks of 'the mix of customers the simulation assumes' with 0 simulated attempts: {s[:200]}")
            if "no speech was recorded or transcribed" in low and not re.search(r"\d+ attempt\(s\) in this batch were simulated", s):
                FAILS.append(f"[{tag}] {name}: unqualified no-speech claim: {s[:160]}")
        else:
            for bad in ("phone call", "browser phone", "speech-to-text", "prisma", "microphone", "transcribed by"):
                if bad in low and "no phone" not in low and "phone sessions have been" not in low:
                    FAILS.append(f"[{tag}] {name}: '{bad}' with no phone call: {s[:160]}")
        if "none by design" in low and late_ph:
            FAILS.append(f"[{tag}] {name}: 'none by design' with {late_ph} late phone attempts")
        m = re.search(r"(\d+) attempt\(s\) in this batch were simulated", s)
        if m and int(m.group(1)) != sim:
            FAILS.append(f"[{tag}] {name}: says {m.group(1)} simulated, recount {sim}")
        if "No attempt in this batch was simulated" in s and sim:
            FAILS.append(f"[{tag}] {name}: says no simulated, recount {sim}")
        m = re.search(r"(\d+) call\(s\) were phone sessions on the browser phone \((\d+) attempt\(s\) in the sample and (\d+) call\(s\) outside it\)", s)
        if m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) != (ph + outn, ph, outn):
            FAILS.append(f"[{tag}] {name}: says phone {m.groups()}, recount {(ph + outn, ph, outn)}")
        m = re.search(r"(\d+) of (\d+) attempts were made after day 30", s)
        if m and (int(m.group(1)), int(m.group(2))) != (late_ph, total):
            FAILS.append(f"[{tag}] {name}: late {m.groups()} recount {(late_ph, total)}")
        m = re.search(r"Calls marked Phone call were made on the browser phone against synthetic records: (\d+) phone session", s)
        if m and int(m.group(1)) != ph + outn:
            FAILS.append(f"[{tag}] {name}: phone note {m.group(1)} sessions, recount {ph + outn}")
    if late_ph and "after day 30" not in rep.timing.note:
        FAILS.append(f"[{tag}] timing note silent on late phone attempts: {rep.timing.note}")
    if rep.batch.simulated != (not phone_any):
        FAILS.append(f"[{tag}] batch.simulated={rep.batch.simulated} with phone={phone_any}")
    print(f"[{tag}] raw: sim={sim} phone={ph} outside={outn} late_phone={late_ph}; views={len(views)}; strings={len(allt)}")
    print("   limits[:3]:", [l[:110] for l in rep.limits[:3]])
    print("   timing:", rep.timing.note[:150])


def batch(tag, seed):
    return new_batch(STATE / tag, seed=seed, n=60, draws=[(date(2027, 2, 9), 0.7), (date(2027, 2, 23), 0.7)],
                     sold_from=date(2027, 1, 25), days=25)


def phone(store, loans_by, cust, loan_id, cd, i, sess, **kw):
    loan = loans_by[loan_id]
    c = case_file(store, loan, cust[loan_id], cd, T + timedelta(minutes=11 * i), **kw)
    put(sess, c)


# S1 only simulated
st, meta, loans, cust = batch("S1", 5150)
for d in st.draws():
    run_draw(st, d, cust, scripted_analysis)
scan("S1 simulated only", st)

# S2 simulated + linked phone
st, meta, loans, cust = batch("S2", 5151)
by = {b.record.loan_id: b for b in loans}
sess = STATE / "S2" / "sessions"
d0 = st.draws()[0]
for i, x in enumerate(d0.drawn[:5]):
    phone(st, by, cust, x.loan_id, d0.as_of + timedelta(days=1), i, sess,
          **({"customer_audio": {"mic": 2, "file": 0, "none": 0}} if i % 2 else {}))
ingest(st, sess, packaged_records())
for d in st.draws():
    run_draw(st, d, cust, scripted_analysis)
scan("S2 simulated + phone", st)

# S3 only an outside phone call
st, meta, loans, cust = batch("S3", 5152)
by = {b.record.loan_id: b for b in loans}
sess = STATE / "S3" / "sessions"
drawn_ids = {x.loan_id for d in st.draws() for x in d.drawn}
und = next(b for b in loans if b.record.loan_id not in drawn_ids)
phone(st, by, cust, und.record.loan_id, und.sold_on + timedelta(days=3), 1, sess)
f = ingest(st, sess, packaged_records())
print("S3 ingest:", f.describe().splitlines()[0])
scan("S3 only outside", st)

# S4 only phone attempts, no simulated run
st, meta, loans, cust = batch("S4", 5153)
by = {b.record.loan_id: b for b in loans}
sess = STATE / "S4" / "sessions"
for i, x in enumerate(st.draws()[1].drawn[:6]):
    phone(st, by, cust, x.loan_id, st.draws()[1].as_of + timedelta(days=2), i, sess)
ingest(st, sess, packaged_records())
scan("S4 only phone attempts", st)

# S5 phone attempts after day 30 (plus simulated)
st, meta, loans, cust = batch("S5", 5154)
by = {b.record.loan_id: b for b in loans}
sess = STATE / "S5" / "sessions"
d0 = st.draws()[0]
for i, x in enumerate(d0.drawn[:4]):
    b = by[x.loan_id]
    phone(st, by, cust, x.loan_id, b.sold_on + timedelta(days=31 + 4 * i), i, sess,
          **({"call_outcome": "no_response"} if i == 3 else {}))
f = ingest(st, sess, packaged_records())
print("S5 ingest:", f.describe().splitlines()[0])
scan("S5 late phone, no simulated", st)
for d in st.draws():
    run_draw(st, d, cust, scripted_analysis)
scan("S5b late phone + simulated", st)

print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x[:400])
