"""P3b round 4, claim 1: hostile case-file shapes, each alone and all together.

usage: uv run python references/reviews/iter2/probes/p3b_r4_hostile.py <state dir>
Writes only under <state dir>. No network.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, hashes, invariants, new_batch, put  # noqa: E402

from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.views import attempt_log_view  # noqa: E402

STATE = Path(sys.argv[1])
if STATE.exists():
    shutil.rmtree(STATE)
FAILS: list[str] = []

store, meta, loans, cust = new_batch(
    STATE / "tmpl", seed=60606, n=90,
    draws=[(date(2027, 3, 3), 0.8), (date(2027, 3, 17), 0.8)], sold_from=date(2027, 2, 15), days=30,
)
by_id = {b.record.loan_id: b for b in loans}
drawn = [(d, by_id[x.loan_id]) for d in store.draws() for x in d.drawn]
print(f"book: {len(loans)} loans, {len(drawn)} drawn")
H_DRAW, H_LOAN = drawn[0]
S_DRAW, S_LOAN = drawn[1]
T0 = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)


def good(minute: int = 0, **over) -> dict:
    return case_file(store, H_LOAN, cust[H_LOAN.record.loan_id], H_DRAW.as_of + timedelta(days=2),
                     T0 + timedelta(minutes=minute), **over)


def sound(minute: int = 500) -> dict:
    return case_file(store, S_LOAN, cust[S_LOAN.record.loan_id], S_DRAW.as_of + timedelta(days=3),
                     T0 + timedelta(minutes=minute))


def raw(case: dict) -> str:
    return json.dumps(case, ensure_ascii=False)


def sub(case: dict, old: str, new: str) -> str:
    text = raw(case)
    assert old in text, old
    return text.replace(old, new, 1)


def nested(depth: int) -> str:
    return "[" * depth + "]" * depth


# shape name -> builder(sessions dir) returning the folder name(s) it made
SHAPES: dict[str, object] = {}


def shape(name):
    def deco(fn):
        SHAPES[name] = fn
        return fn
    return deco


def simple(name, make):
    @shape(name)
    def _(sess: Path, i: int):
        c = good(i)
        content = make(c)
        return [put(sess, content, c["session_id"]).name]


simple("models.extraction is an int", lambda c: c | {"models": {"extraction": 7}})
simple("models is a list of dicts", lambda c: c | {"models": [{"extraction": {"model": "x"}}]})
simple("models.extraction.model is a dict", lambda c: c | {"models": {"extraction": {"model": {"n": 1}}}})
simple("started_at 2000-01-01T00:00:00+00:00", lambda c: c | {"started_at": "2000-01-01T00:00:00+00:00"})
simple("started_at 1999-12-31T23:59:59+00:00", lambda c: c | {"started_at": "1999-12-31T23:59:59+00:00"})
simple("started_at 2100-12-31T23:59:59+00:00", lambda c: c | {"started_at": "2100-12-31T23:59:59+00:00"})
simple("started_at 2100-12-31T23:59:59-14:00 (UTC 2101)", lambda c: c | {"started_at": "2100-12-31T23:59:59-14:00"})
simple("started_at 2000-01-01T00:30:00+05:30 (UTC 1999)", lambda c: c | {"started_at": "2000-01-01T00:30:00+05:30"})
simple("started_at naive", lambda c: c | {"started_at": "2026-11-10T04:00:00"})
simple("started_at an int", lambda c: c | {"started_at": 1762747200})
simple("started_at 'NaN'", lambda c: c | {"started_at": "NaN"})
simple("started_at +23:59 offset", lambda c: c | {"started_at": "2026-11-10T04:00:00+23:59"})
simple("started_at with Z and nanoseconds", lambda c: c | {"started_at": "2026-11-10T04:00:00.123456789Z"})
simple("NaN literal in result", lambda c: sub(c, '"result": {', '"result": NaN, "x": {'))
simple("Infinity in customer_audio", lambda c: raw(c | {"customer_audio": {"mic": 1, "file": 0, "none": 0}}).replace('"mic": 1', '"mic": Infinity'))
simple("-Infinity day_since_sale", lambda c: sub(c, '"day_since_sale": ', '"day_since_sale": -Infinity, "zz": '))
simple("huge int day_since_sale", lambda c: sub(c, '"day_since_sale": ', '"day_since_sale": 1' + "0" * 400 + ', "zz": '))
simple("huge int turn_id", lambda c: c | {"turns": [{"turn_id": 10**30, "text": "x"}]})
simple("deep nesting in result (5000)", lambda c: sub(c, '"result": {', '"result": ' + nested(5000) + ', "q": {'))
simple("deep nesting in extra key (100000)", lambda c: raw(c)[:-1] + ', "deep": ' + nested(100000) + "}")
simple("10 MB loan_id", lambda c: c | {"loan_id": "L" * 10_000_000})
simple("duplicate status key (ready then failed)", lambda c: raw(c)[:-1] + ', "status": "failed"}')
simple("duplicate session_id key, last differs", lambda c: raw(c)[:-1] + ', "session_id": "x"}')
simple("UTF-8 BOM", lambda c: "﻿" + raw(c))
simple("empty file", lambda c: "")
simple("whitespace only", lambda c: " \n\t ")
simple("JSON array", lambda c: "[" + raw(c) + "]")
simple("JSON null", lambda c: "null")
simple("invalid UTF-8 bytes in a string", lambda c: raw(c).encode().replace(b'"hi"', b'"h\xff"', 1))
simple("extra unknown keys everywhere", lambda c: c | {"zzz": {"a": [1, 2]}, "book": c["book"] | {"extra": 1}, "__proto__": 1})
simple("result is a string", lambda c: c | {"result": "ready"})
simple("result is {}", lambda c: c | {"result": {}})
simple("result is a list", lambda c: c | {"result": [1, 2]})
simple("transcript is a string", lambda c: c | {"transcript": "abc"})
simple("transcript missing on a ready completed", lambda c: {k: v for k, v in c.items() if k != "transcript"})
simple("turns is a string", lambda c: c | {"turns": "abc"})
simple("turns holds null", lambda c: c | {"turns": [None]})
simple("turn_id true", lambda c: c | {"turns": [{"turn_id": True, "text": "x"}]})
simple("turn readings ok 'true' and agreed 1", lambda c: c | {"turns": [{"turn_id": 1, "text": "x", "readings_agreed": 1, "readings": [{"role": "primary", "model": "m", "ok": "true", "text": "SHOULD-NOT-SHOW"}]}]})
simple("turn start_s NaN", lambda c: raw(c | {"turns": [{"turn_id": 1, "start_s": 1.5}]}).replace("1.5", "NaN"))
simple("speaker_confirmed 'false'", lambda c: c | {"speaker_confirmed": "false"})
simple("speaker_confirmed 0", lambda c: c | {"speaker_confirmed": 0})
simple("language 'xx'", lambda c: c | {"language": "xx"})
simple("book call_date 2027-02-30", lambda c: c | {"book": c["book"] | {"call_date": "2027-02-30"}})
simple("book day_since_sale 5.0", lambda c: c | {"book": c["book"] | {"day_since_sale": float(c["book"]["day_since_sale"])}})
simple("book draw_id null", lambda c: c | {"book": c["book"] | {"draw_id": None}})
simple("book is a list", lambda c: c | {"book": [c["book"]]})
simple("book sold_on 2101-01-01", lambda c: c | {"book": c["book"] | {"sold_on": "2101-01-01"}})
simple("customer_audio mic -1 / true", lambda c: c | {"customer_audio": {"mic": -1, "file": True, "none": 0}})
simple("recording sha256 a list", lambda c: c | {"recording": {"sha256": ["a"]}})
simple("status READY", lambda c: c | {"status": "READY"})
simple("call_outcome an int", lambda c: c | {"call_outcome": 3})
simple("call_outcome unknown text", lambda c: c | {"call_outcome": "teleported"})
simple("session_id differs from folder", lambda c: c | {"session_id": "20261110T030000-0000000000ff"})


@shape("directory named case.json")
def _(sess: Path, i: int):
    c = good(i)
    (sess / c["session_id"] / "case.json").mkdir(parents=True)
    return [c["session_id"]]


@shape("case.json unreadable (chmod 000)")
def _(sess: Path, i: int):
    c = good(i)
    f = put(sess, c, c["session_id"])
    os.chmod(f / "case.json", 0)
    return [f.name]


@shape("dangling symlink case.json")
def _(sess: Path, i: int):
    c = good(i)
    f = sess / c["session_id"]
    f.mkdir(parents=True)
    os.symlink("/nonexistent/x/case.json", f / "case.json")
    return [f.name]


@shape("symlinked folder to another session (two folders, same case)")
def _(sess: Path, i: int):
    c = good(i)
    f = put(sess, c, c["session_id"])
    other = good(i + 1)
    os.symlink(f, sess / other["session_id"])
    return [f.name, other["session_id"]]


@shape("case.json symlink to /dev/zero-like FIFO-free file (/etc/hosts)")
def _(sess: Path, i: int):
    c = good(i)
    f = sess / c["session_id"]
    f.mkdir(parents=True)
    os.symlink("/etc/hosts", f / "case.json")
    return [f.name]


@shape("folder not a session id")
def _(sess: Path, i: int):
    (sess / "not-a-session").mkdir(parents=True)
    (sess / "not-a-session" / "case.json").write_text(raw(good(i)))
    return ["not-a-session"]


@shape("session.json only")
def _(sess: Path, i: int):
    c = good(i)
    f = sess / c["session_id"]
    f.mkdir(parents=True)
    (f / "session.json").write_text('{"oops": ')
    return [f.name]


def check_run(tag: str, root: Path, made: list[str], expect_sound: str | None) -> None:
    st = OpsStore(root / "ops")
    sess = root / "sessions"
    try:
        found = ingest(st, sess, packaged_records())
    except BaseException as e:  # noqa: BLE001
        tb = traceback.format_exception(e)
        FAILS.append(f"[{tag}] ingest raised: {''.join(tb[-3:]).strip()}")
        return
    places: dict[str, list[str]] = {}
    for s in found.linked:
        places.setdefault(s, []).append("linked")
    for s in found.outside:
        places.setdefault(s, []).append("outside")
    for s, why in found.skipped:
        places.setdefault(s, []).append("skipped")
        if not why or not why.strip():
            FAILS.append(f"[{tag}] {s} skipped with empty reason")
    folders = sorted(p.name for p in sess.iterdir() if p.is_dir())
    for f in folders:
        if len(places.get(f, [])) != 1:
            FAILS.append(f"[{tag}] folder {f} in {places.get(f, [])}")
    for f in places:
        if f not in folders:
            FAILS.append(f"[{tag}] {f} listed but not a folder")
    if expect_sound and places.get(expect_sound) != ["linked"]:
        FAILS.append(f"[{tag}] sound session {expect_sound} is {places.get(expect_sound)}")
    try:
        b = load_batch(st)
        build_report(st)
        attempt_log_view(b)
    except BaseException as e:  # noqa: BLE001
        FAILS.append(f"[{tag}] load/report/log raised {type(e).__name__}: {e}"[:300])
    bad = invariants(st, sess)
    for x in bad:
        FAILS.append(f"[{tag}] invariant: {x}")
    h1 = hashes(st.root)
    try:
        ingest(st, sess, packaged_records())
    except BaseException as e:  # noqa: BLE001
        FAILS.append(f"[{tag}] second ingest raised {type(e).__name__}: {e}"[:300])
        return
    h2 = hashes(st.root)
    if h1 != h2:
        FAILS.append(f"[{tag}] second ingest changed {sorted(k for k in set(h1) | set(h2) if h1.get(k) != h2.get(k))}")
    summ = {k: places[k] for k in made if k in places}
    reasons = {s: w[:110] for s, w in found.skipped if s in made}
    print(f"  {tag[:60]:60s} {summ} {reasons}")


# alone
for i, (name, fn) in enumerate(SHAPES.items()):
    root = STATE / f"alone{i:02d}"
    shutil.copytree(STATE / "tmpl", root)
    sess = root / "sessions"
    sess.mkdir()
    made = fn(sess, i * 3)
    s = sound(900)
    put(sess, s, s["session_id"])
    check_run(name, root, made, s["session_id"])

# all together
root = STATE / "together"
shutil.copytree(STATE / "tmpl", root)
sess = root / "sessions"
sess.mkdir()
made: list[str] = []
for i, (name, fn) in enumerate(SHAPES.items()):
    if "case.json" in name and "symlink" in name and "folder" not in name:
        pass
    try:
        made += fn(sess, 2000 + i * 3)
    except FileExistsError:
        pass
s = sound(9000)
put(sess, s, s["session_id"])
check_run("ALL TOGETHER", root, made, s["session_id"])

# restore perms so the state can be removed later
for p in STATE.rglob("case.json"):
    try:
        if not p.is_symlink():
            os.chmod(p, 0o644)
    except OSError:
        pass
print(f"\nshapes: {len(SHAPES)}")
print(f"FAILURES: {len(FAILS)}")
for f in FAILS:
    print("FAIL", f)
