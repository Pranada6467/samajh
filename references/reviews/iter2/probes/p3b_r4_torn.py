"""P3b round 4, claim 5: a torn last line in each append-only log; a torn line in the middle; appends
from several processes with a torn line present.

usage: uv run python references/reviews/iter2/probes/p3b_r4_torn.py <state dir>
Writes only under <state dir>. No network.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import shutil
import sys
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_r3_kit import case_file, new_batch, put  # noqa: E402

from samajh.ops import sampler  # noqa: E402
from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.model import Decision, Disposition  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.sessions import ingest, packaged_records  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402

STATE = Path(sys.argv[1]) if __name__ == "__main__" else None
FAILS: list[str] = []
T = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)

FRAGMENTS = {
    "mid-key": b'{"attempt_id": "D-2027-0',
    "mid-string multibyte cut": '{"note": "ग्राहक ने कहा'.encode()[:-2],
    "bare {": b"{",
    "whitespace only": b"   \t",
    "a lone NUL": b"\x00",
    "valid line without newline": None,  # filled per log: a copy of a new valid entry
}


def logs_counts(store: OpsStore) -> dict[str, int]:
    return {"attempts": len(store.attempts()), "outside": len(store.outside()),
            "dispositions": len(store.dispositions()), "draws": len(store.draws())}


def raw_lines(path: Path) -> list[bytes]:
    return path.read_bytes().split(b"\n") if path.exists() else []


def setup(root: Path):
    store, meta, loans, cust = new_batch(root, seed=8128, n=50, draws=[(date(2027, 2, 2), 0.6)],
                                         sold_from=date(2027, 1, 18), days=14)
    by = {b.record.loan_id: b for b in loans}
    d0 = store.draws()[0]
    drawn = [by[x.loan_id] for x in d0.drawn]
    und = [b for b in loans if all(b.record.loan_id != x.loan_id for x in d0.drawn)]
    sess = root / "sessions"
    for i, b in enumerate(drawn[:3]):
        put(sess, case_file(store, b, cust[b.record.loan_id], d0.as_of + timedelta(days=1), T + timedelta(minutes=i)))
    put(sess, case_file(store, und[0], cust[und[0].record.loan_id], und[0].sold_on + timedelta(days=2), T + timedelta(minutes=9)))
    ingest(store, sess, packaged_records())
    cid = store.attempts()[0].call_id
    store.add_disposition(Disposition(case_id=cid, decision=Decision.needs_information, note="पहला नोट",
                                      reviewer="r1", recorded_at=datetime(2027, 3, 1, tzinfo=UTC)))
    return store, loans, cust, drawn, und


def new_entry(log: str, root: Path, store: OpsStore, loans, cust, drawn, und, k: int):
    """Append one new entry to `log` through the store's normal path; returns (model instance or None)."""
    sess = root / "sessions"
    if log == "attempts":
        b = drawn[4 + k]
        put(sess, case_file(store, b, cust[b.record.loan_id], store.draws()[0].as_of + timedelta(days=2),
                            T + timedelta(minutes=30 + k)))
        ingest(store, sess, packaged_records())
    elif log == "outside":
        b = und[1 + k]
        put(sess, case_file(store, b, cust[b.record.loan_id], b.sold_on + timedelta(days=3), T + timedelta(minutes=60 + k)))
        ingest(store, sess, packaged_records())
    elif log == "dispositions":
        store.add_disposition(Disposition(case_id=store.attempts()[0].call_id, decision=Decision.call_customer,
                                          note=f"नया नोट {k}", reviewer="r2",
                                          recorded_at=datetime(2027, 3, 2 + k, tzinfo=UTC)))
    elif log == "draws":
        meta = store.meta().book
        last = store.draws()[-1]
        d = sampler.draw(store.book(), meta, last.as_of + timedelta(days=7 * (k + 1)), 0.5, 8128, after=last.as_of)
        store.add_draw(d)


def valid_line_for(log: str, store: OpsStore) -> bytes:
    if log == "dispositions":
        return Disposition(case_id=store.attempts()[0].call_id, decision=Decision.concern_not_supported,
                           note="बिना नई पंक्ति", reviewer="r3",
                           recorded_at=datetime(2027, 3, 20, tzinfo=UTC)).model_dump_json().encode()
    return b""  # for the others a valid line without newline is made by cutting the newline off the last line


def one(log: str, frag_name: str, root: Path, template: Path) -> None:
    tag = f"{log}/{frag_name}"
    shutil.copytree(template, root)
    store = OpsStore(root / "ops")
    _, loans, cust = None, *new_batch_loans(root)
    drawn, und = split(store, loans)
    path = store.root / f"{log}.jsonl"
    before = logs_counts(store)
    before_lines = [l for l in raw_lines(path) if l]
    frag = FRAGMENTS[frag_name]
    expect_extra = 0
    if frag is None:
        if log == "dispositions":
            frag = valid_line_for(log, store)
            expect_extra = 1
        else:
            # cut the newline off the existing last line: a whole valid line without newline
            data = path.read_bytes()
            path.write_bytes(data[:-1])
            frag = b""
    with path.open("ab") as f:
        f.write(frag)
    try:
        mid = logs_counts(store)
        load_batch(store)
        if mid[log] != before[log] + expect_extra:
            FAILS.append(f"[{tag}] read before append: {mid[log]} entries, expected {before[log] + expect_extra}")
        new_entry(log, root, store, loans, cust, drawn, und, 0)
        after = logs_counts(store)
        if after[log] != before[log] + expect_extra + 1:
            FAILS.append(f"[{tag}] after append: {after[log]}, expected {before[log] + expect_extra + 1}")
        after_lines = [l for l in raw_lines(path) if l]
        for l in before_lines:
            if l not in after_lines:
                FAILS.append(f"[{tag}] an earlier line was lost: {l[:80]!r}")
        if len(after_lines) != len(set(after_lines)):
            FAILS.append(f"[{tag}] a line is duplicated")
        torn = path.with_name(path.name + ".torn")
        if frag and expect_extra == 0 and FRAGMENTS[frag_name] is not None:
            if not torn.exists() or frag not in torn.read_bytes():
                FAILS.append(f"[{tag}] fragment not kept in .torn")
        build_report(store)
        # a second crash: another fragment, then append again
        with path.open("ab") as f:
            f.write(b'{"x": "\xe0\xa4')
        with path.open("ab") as f:  # and a third, glued to it, before any append
            f.write(b'"y')
        logs_counts(store)
        new_entry(log, root, store, loans, cust, drawn, und, 1)
        a2 = logs_counts(store)
        if a2[log] != after[log] + 1:
            FAILS.append(f"[{tag}] after second crash and append: {a2[log]}, expected {after[log] + 1}")
        build_report(store)
        print(f"  {tag:45s} ok: {before[log]} -> {mid[log]} -> {after[log]} -> {a2[log]}; torn file: "
              f"{torn.read_bytes()[:60]!r}" if torn.exists() else f"  {tag:45s} {before[log]} -> {after[log]} -> {a2[log]}; no .torn")
    except Exception as e:  # noqa: BLE001
        FAILS.append(f"[{tag}] raised {''.join(traceback.format_exception(e)[-2:]).strip()[:400]}")


def new_batch_loans(root: Path):
    store = OpsStore(root / "ops")
    loans = store.book()
    from samajh.ops.book import generate_book
    _, _, customers = generate_book(8128, 50, sold_from=date(2027, 1, 18), days=14)
    return loans, {c.loan_id: c for c in customers}


def split(store: OpsStore, loans):
    by = {b.record.loan_id: b for b in loans}
    d0 = store.draws()[0]
    drawn = [by[x.loan_id] for x in d0.drawn]
    und = [b for b in loans if all(b.record.loan_id != x.loan_id for x in d0.drawn)]
    return drawn, und


def worker(root: str, k: int, n: int) -> None:
    store = OpsStore(Path(root))
    cid = store.attempts()[0].call_id
    for j in range(n):
        store.add_disposition(Disposition(case_id=cid, decision=Decision.needs_information,
                                          note=f"प्रक्रिया {k} पंक्ति {j}", reviewer=f"p{k}",
                                          recorded_at=datetime(2027, 4, 1, tzinfo=UTC) + timedelta(seconds=k * 1000 + j)))


if __name__ == "__main__":
    if STATE.exists():
        shutil.rmtree(STATE)
    template = STATE / "template"
    store, loans, cust, drawn, und = setup(template)
    print("template:", logs_counts(store))
    i = 0
    for log in ("attempts", "outside", "dispositions", "draws"):
        for frag_name in FRAGMENTS:
            i += 1
            one(log, frag_name, STATE / f"c{i:02d}", template)

    # a torn line in the middle (a different fault)
    for log in ("attempts", "dispositions"):
        root = STATE / f"middle_{log}"
        shutil.copytree(template, root)
        st = OpsStore(root / "ops")
        p = st.root / f"{log}.jsonl"
        lines = p.read_bytes().split(b"\n")
        lines.insert(1, b'{"attempt_id": "D-2')
        p.write_bytes(b"\n".join(lines))
        try:
            n = logs_counts(st)
            print(f"  middle {log}: reads gave {n}")
        except Exception as e:  # noqa: BLE001
            print(f"  middle {log}: read raises {type(e).__name__}: {str(e).splitlines()[0][:150]}")
        try:
            load_batch(st)
            build_report(st)
            print(f"  middle {log}: report builds")
        except Exception as e:  # noqa: BLE001
            print(f"  middle {log}: report raises {type(e).__name__}: {str(e).splitlines()[0][:150]}")

    # several processes appending at once, with a torn line present
    root = STATE / "procs"
    shutil.copytree(template, root)
    st = OpsStore(root / "ops")
    p = st.root / "dispositions.jsonl"
    base = len(st.dispositions())
    with p.open("ab") as f:
        f.write('{"case_id": "टूटा'.encode()[:-1])
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=worker, args=(str(st.root), k, 25)) for k in range(6)]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join()
    codes = [pr.exitcode for pr in procs]
    got = st.dispositions()
    raw = [l for l in p.read_bytes().split(b"\n") if l]
    torn = p.with_name(p.name + ".torn")
    print(f"  procs: exit codes {codes}; {len(got)} dispositions (expected {base + 150}); raw lines {len(raw)}; "
          f"torn file lines {len(torn.read_bytes().splitlines()) if torn.exists() else 0}")
    if codes != [0] * 6 or len(got) != base + 150 or len(raw) != base + 150 or len(set(raw)) != len(raw):
        FAILS.append(f"[procs] codes {codes}, {len(got)} entries, {len(raw)} raw lines")
    build_report(st)

    print(f"cases: {i} torn-tail cases + 2 middle + 1 multi-process")
    print(f"FAILURES: {len(FAILS)}")
    for x in FAILS:
        print("FAIL", x)
