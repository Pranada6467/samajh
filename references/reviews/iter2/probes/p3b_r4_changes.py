"""P3b round 4, claim 2: a session brought in whose case file later changes stays where it is.

usage: uv run python references/reviews/iter2/probes/p3b_r4_changes.py <state dir>
Writes only under <state dir>. No network. Also runs the CLI (ingest, report) on copies.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, hashes, invariants, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.views import attempt_log_view  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []
NOW = datetime(2027, 6, 1, tzinfo=UTC)

store, meta, loans, cust = new_batch(
    STATE / "base", seed=31337, n=70,
    draws=[(date(2027, 4, 6), 0.75)], sold_from=date(2027, 3, 20), days=20,
)
by_id = {b.record.loan_id: b for b in loans}
d0 = store.draws()[0]
drawn = [by_id[x.loan_id] for x in d0.drawn]
undrawn = [b for b in loans if all(b.record.loan_id != x.loan_id for x in d0.drawn)]
print(f"{len(loans)} loans, {len(drawn)} drawn, {len(undrawn)} not drawn")
T = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)
SESS = STATE / "base" / "sessions"
SESS.mkdir()
CD = date(2027, 4, 8)


def mk(i, loan, **kw):
    return case_file(store, loan, cust[loan.record.loan_id], CD, T + timedelta(minutes=7 * i), **kw)


cases = {
    "A_ready": mk(1, drawn[0]),
    "B_failed": mk(2, drawn[1], status="failed"),
    "C_outside": mk(3, undrawn[0]),
    "D_dnc": mk(4, drawn[2], outcome="do_not_call", speaker_confirmed=True),
    "E_noans": mk(5, drawn[3], outcome="no_response"),
    "F_outside_nobook": mk(6, drawn[4], book=False),
    "G_failed2": mk(7, drawn[5], status="failed"),
}
for c in cases.values():
    put(SESS, c)
SID = {k: c["session_id"] for k, c in cases.items()}
first = ingest(store, SESS, packaged_records())
print(first.describe().splitlines()[0])
BASE_HASH = {k: v for k, v in hashes(store.root).items() if k != "ingest.json"}


def numbers(rep: dict) -> dict:
    """The report without its free-text notes on ingest."""
    rep = json.loads(json.dumps(rep))
    rep.pop("generated_at", None); rep.pop("phone_sessions_changed", None)
    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items()}
        if isinstance(x, list):
            return [strip(v) for v in x if not (isinstance(v, str) and ("ingest" in v or "brought in" in v))]
        if isinstance(x, str) and ("ingest" in x or "brought in" in x):
            return "<ingest note>"
        return x
    return strip(rep)


BASE_REP = numbers(build_report(store, NOW).model_dump(mode="json"))


def diffpaths(a, b, path=""):
    if type(a) is not type(b):
        return [f"{path}: {str(a)[:150]!r} -> {str(b)[:150]!r}"]
    if isinstance(a, dict):
        out = []
        for k in set(a) | set(b):
            out += diffpaths(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: len {len(a)} -> {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diffpaths(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {str(a)[:150]!r} -> {str(b)[:150]!r}"]


def where(found, sid):
    p = []
    if sid in found.linked:
        p.append("linked")
    if sid in found.outside:
        p.append("outside")
    if any(s == sid for s, _ in found.skipped):
        p.append("skipped")
    return p


def check(tag, root, sid, expect_place, allow_store_change=False):
    st = OpsStore(root / "ops")
    sess = root / "sessions"
    found = ingest(st, sess, packaged_records())
    pl = where(found, sid)
    ch = [w for s, w in found.changed if s == sid]
    out = f"[{tag}] {sid}: {pl} changed={ch!r:.160}"
    print(out)
    if not allow_store_change:
        if pl != [expect_place]:
            if not (sess / sid).exists() and pl == []:
                FAILS.append(f"[{tag}] folder deleted: session in no list of the ingest (not in changed); store keeps it")
            else:
                FAILS.append(f"[{tag}] place {pl}, expected [{expect_place}]")
        if not ch:
            FAILS.append(f"[{tag}] not listed under changed")
        h = {k: v for k, v in hashes(st.root).items() if k != "ingest.json"}
        if h != BASE_HASH:
            FAILS.append(f"[{tag}] store changed: {sorted(k for k in set(h) | set(BASE_HASH) if h.get(k) != BASE_HASH.get(k))}")
        rep = numbers(build_report(st, NOW).model_dump(mode="json"))
        if rep != BASE_REP:
            FAILS.append(f"[{tag}] report numbers moved: {diffpaths(BASE_REP, rep)[:4]}")
    b = load_batch(st)
    log = attempt_log_view(b)
    if any(v.session_id == sid for v in log.not_ingested):
        FAILS.append(f"[{tag}] attempt log lists {sid} as not brought in")
    if (sid in [c.session_id for c in log.changed]) != bool(ch):
        FAILS.append(f"[{tag}] attempt log changed list disagrees with ingest")
    # "in no count" sentence: only when skipped sessions exist, and N must equal sessions not in store
    in_store = {a.source.session_id for a in st.attempts() if getattr(a.source, "session_id", None)} | {
        o.session_id for o in st.outside()}
    skipped_ids = [s for s, _ in found.skipped]
    wrongly = [s for s in skipped_ids if s in in_store]
    if wrongly:
        FAILS.append(f"[{tag}] skipped but in store: {wrongly}")
    if "in no count" in log.ingest_note and not skipped_ids:
        FAILS.append(f"[{tag}] 'in no count' said with no skipped session")
    for x in invariants(st, sess):
        FAILS.append(f"[{tag}] invariant: {x}")
    return found, st


def variant(tag):
    root = STATE / tag
    shutil.copytree(STATE / "base", root, symlinks=True)
    return root, root / "sessions"


def rewrite(sess, sid, fn):
    p = sess / sid / "case.json"
    c = json.loads(p.read_text())
    p.write_text(json.dumps(fn(c), ensure_ascii=False))


A, B, C, D, E, F, G = (SID[k] for k in ("A_ready", "B_failed", "C_outside", "D_dnc", "E_noans", "F_outside_nobook", "G_failed2"))
single = [
    ("A_models", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"models": {"extraction": {"model": "zz-other"}}})),
    ("A_outcome_noanswer", A, "linked", lambda s: rewrite(s, A, lambda c: {k: v for k, v in c.items() if k not in ("transcript", "result")} | {"call_outcome": "no_answer"})),
    ("A_ready_to_failed", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"status": "failed"})),
    ("A_running", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"status": "running"})),
    ("A_malformed", A, "linked", lambda s: (s / A / "case.json").write_text('{"session_id": ')),
    ("A_invalid_utf8", A, "linked", lambda s: (s / A / "case.json").write_bytes((s / A / "case.json").read_bytes().replace(b'"language": "', b'"language": "\xff', 1))),
    ("A_unreadable", A, "linked", lambda s: os.chmod(s / A / "case.json", 0)),
    ("A_case_deleted", A, "linked", lambda s: (s / A / "case.json").unlink()),
    ("A_folder_deleted", A, "linked", lambda s: shutil.rmtree(s / A)),
    ("A_book_call_date", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"book": c["book"] | {"call_date": "2027-04-09", "day_since_sale": c["book"]["day_since_sale"] + 1}})),
    ("A_book_removed", A, "linked", lambda s: rewrite(s, A, lambda c: {k: v for k, v in c.items() if k != "book"})),
    ("A_book_other_batch", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"book": c["book"] | {"batch_id": "B-other"}})),
    ("A_language", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"language": "ta"})),
    ("A_audio", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"customer_audio": {"mic": 3, "file": 0, "none": 0}})),
    ("A_readings", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"turns": [dict(t, readings=[{"role": "primary", "model": "p", "text": "x"}], readings_agreed=True) for t in c["turns"]]})),
    ("A_speaker_false", A, "linked", lambda s: rewrite(s, A, lambda c: c | {"speaker_confirmed": False})),
    ("C_outcome", C, "outside", lambda s: rewrite(s, C, lambda c: {k: v for k, v in c.items() if k not in ("transcript", "result")} | {"call_outcome": "human_requested"})),
    ("C_case_deleted", C, "outside", lambda s: (s / C / "case.json").unlink()),
    ("C_given_book_of_drawn", C, "outside", lambda s: rewrite(s, C, lambda c: c | {"loan_id": drawn[6].record.loan_id, "record_id": drawn[6].record.loan_id})),
    ("D_speaker_false", D, "linked", lambda s: rewrite(s, D, lambda c: c | {"speaker_confirmed": False})),
    ("E_now_completed", E, "linked", lambda s: rewrite(s, E, lambda c: case_file(store, drawn[3], cust[drawn[3].record.loan_id], CD, T + timedelta(minutes=35), sid=E))),
    ("F_book_added", F, "outside", lambda s: rewrite(s, F, lambda c: case_file(store, drawn[4], cust[drawn[4].record.loan_id], CD, T + timedelta(minutes=42), sid=F))),
    ("B_ready_to_failed_other_models", B, "linked", lambda s: rewrite(s, B, lambda c: c | {"models": {"extraction": {"model": "q"}}})),
]
for tag, sid, place, change in single:
    root, sess = variant(tag)
    change(sess)
    check(tag, root, sid, place)
    if (sess / sid / "case.json").exists() and not (sess / sid / "case.json").is_symlink():
        os.chmod(sess / sid / "case.json", 0o644)

# sequences
root, sess = variant("seq_change_back")
orig = (sess / A / "case.json").read_bytes()
rewrite(sess, A, lambda c: c | {"models": {"extraction": {"model": "zz"}}})
check("seq1 change", root, A, "linked")
(sess / A / "case.json").write_bytes(orig)
f, st = check("seq1 back", root, A, "linked", allow_store_change=True)
if f.changed or f.skipped:
    FAILS.append(f"[seq1 back] after change back: changed={f.changed} skipped={f.skipped}")

root, sess = variant("seq_twice")
rewrite(sess, A, lambda c: c | {"models": {"extraction": {"model": "one"}}})
check("seq2 first", root, A, "linked")
rewrite(sess, A, lambda c: c | {"call_outcome": "wrong_party", "status": "ready"} )
check("seq2 second", root, A, "linked")

# failed -> ready -> failed -> ready (different content)
root, sess = variant("seq_supersede")
st = OpsStore(root / "ops")
rewrite(sess, G, lambda c: c | {"status": "ready"})
f = ingest(st, sess, packaged_records())
att = [a for a in st.attempts() if getattr(a.source, "session_id", None) == G]
print(f"[sup ready] G -> {[(a.outcome.value, a.call_id is not None, a.supersedes) for a in att]} changed={f.changed}")
if [a.outcome.value for a in att] != ["completed"]:
    FAILS.append(f"[sup ready] G not superseded to completed: {att}")
H1 = {k: v for k, v in hashes(st.root).items() if k != "ingest.json"}
REP1 = numbers(build_report(st, NOW).model_dump(mode="json"))
if REP1 == BASE_REP:
    FAILS.append("[sup ready] report did not take in the analysed call")
rewrite(sess, G, lambda c: c | {"status": "failed"})
f = ingest(st, sess, packaged_records())
print(f"[sup failed again] place={where(f, G)} changed={[w for s, w in f.changed if s == G]}")
if where(f, G) != ["linked"] or not any(s == G for s, _ in f.changed):
    FAILS.append("[sup failed again] not kept+changed")
if {k: v for k, v in hashes(st.root).items() if k != "ingest.json"} != H1:
    FAILS.append("[sup failed again] store changed")
rewrite(sess, G, lambda c: c | {"status": "ready", "models": {"extraction": {"model": "zzz"}}})
f = ingest(st, sess, packaged_records())
print(f"[sup ready other] place={where(f, G)} changed={[w for s, w in f.changed if s == G]}")
if where(f, G) != ["linked"] or not any(s == G for s, _ in f.changed):
    FAILS.append("[sup ready other] not kept+changed")
if {k: v for k, v in hashes(st.root).items() if k != "ingest.json"} != H1:
    FAILS.append("[sup ready other] store changed")
if numbers(build_report(st, NOW).model_dump(mode="json")) != REP1:
    FAILS.append("[sup ready other] report moved")
for x in invariants(st, sess):
    FAILS.append(f"[sup] invariant {x}")

# CLI agreement on one changed state
root, sess = variant("cli")
rewrite(sess, A, lambda c: c | {"models": {"extraction": {"model": "cli-other"}}})
(sess / "20261110T235900-0000000fffff").mkdir()
env = dict(os.environ, PYTHONPATH=str(REPO))
r = subprocess.run([sys.executable, "-m", "samajh.ops", "ingest", "--state", str(root)], capture_output=True, text=True, env=env, cwd=REPO)
print("CLI ingest:", r.returncode, r.stdout.splitlines()[:4], r.stderr[-300:])
r2 = subprocess.run([sys.executable, "-m", "samajh.ops", "report", "--state", str(root)], capture_output=True, text=True, env=env, cwd=REPO)
cli_rep = json.loads(r2.stdout)
st = OpsStore(root / "ops")
if numbers(cli_rep) != numbers(build_report(st, NOW).model_dump(mode="json")):
    # generated time differs; compare after dropping fields that mention dates of generation
    a, b = numbers(cli_rep), numbers(build_report(st, NOW).model_dump(mode="json"))
    diff = [k for k in a if a[k] != b.get(k)]
    print("CLI report differs from in-process in keys:", diff)
    if set(diff) - {"generated_at", "header"}:
        FAILS.append(f"CLI report differs in {diff}")
log = attempt_log_view(load_batch(st))
print("CLI state ingest_note:", log.ingest_note)
if "in no count" in log.ingest_note and A in [v.session_id for v in log.not_ingested]:
    FAILS.append("CLI state: A in not_ingested")
if "did not bring in 1:" not in log.ingest_note:
    FAILS.append(f"CLI state: note does not say 1 not brought in: {log.ingest_note}")

for p in STATE.rglob("case.json"):
    if p.exists() and not p.is_symlink():
        os.chmod(p, 0o644)
print(f"\ninputs: {len(single)} single changes + 3 sequences + CLI")
print(f"FAILURES: {len(FAILS)}")
for x in FAILS:
    print("FAIL", x)
