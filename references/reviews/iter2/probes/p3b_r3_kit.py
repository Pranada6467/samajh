"""Shared helpers for the P3b round 3 probes (p3b_r3_*.py). Imported, never run on its own.

Builds books, batches and phone-session case files from scratch (own seeds, own dates, own case-file
shapes), and checks the store's invariants straight from the raw files. Writes only under the state
path a probe is given. No network.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from samajh.ops import book as books  # noqa: E402
from samajh.ops import sampler  # noqa: E402
from samajh.ops.model import (  # noqa: E402
    MAX_ATTEMPTS,
    RETRY_AFTER,
    WINDOW_DAYS,
    Attempt,
    BookLoan,
    BookMeta,
    OutsideCall,
    SimCustomer,
)
from samajh.ops.simulate import script_call, scripted_analysis  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
PERIOD = (date(2027, 1, 1), date(2027, 6, 30))
NOW = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)


def new_batch(
    state: Path,
    seed: int,
    n: int,
    draws: list[tuple[date, float]],
    sold_from: date = date(2027, 1, 4),
    days: int = 60,
) -> tuple[OpsStore, BookMeta, tuple[BookLoan, ...], dict[str, SimCustomer]]:
    meta, loans, customers = books.generate_book(seed, n, sold_from=sold_from, days=days)
    store = OpsStore(state / "ops")
    store.init(meta, loans, *PERIOD, NOW)
    for as_of, rate in draws:
        earlier = store.draws()
        d = sampler.draw(loans, meta, as_of, rate, meta.seed, after=earlier[-1].as_of if earlier else None)
        store.add_draw(d)
    return store, meta, loans, {c.loan_id: c for c in customers}


def custom_batch(
    state: Path, loans: list[BookLoan], draws: list[tuple[date, float]], seed: int = 3
) -> tuple[OpsStore, BookMeta]:
    meta = BookMeta(
        lender_name="Namoona Bank (synthetic)",
        lender_type=loans[0].record.lender_type,
        seed=seed,
        loans=len(loans),
        sold_from=min(x.sold_on for x in loans),
        sold_to=max(x.sold_on for x in loans),
        sha256=books.book_sha256(loans),
    )
    store = OpsStore(state / "ops")
    store.init(meta, loans, *PERIOD, NOW)
    for as_of, rate in draws:
        earlier = store.draws()
        store.add_draw(
            sampler.draw(loans, meta, as_of, rate, seed, after=earlier[-1].as_of if earlier else None)
        )
    return store, meta


def draw_of(store: OpsStore, loan_id: str):
    return next((d for d in store.draws() if any(x.loan_id == loan_id for x in d.drawn)), None)


_serial = iter(range(0xA000, 10**9))


def sid_for(started: datetime) -> str:
    return f"{started.astimezone(UTC):%Y%m%dT%H%M%S}-{next(_serial):012x}"


def amount_turns(transcript: dict) -> list[dict]:
    """The case file's `turns` list: one entry per customer turn, no readings."""
    return [
        {"turn_id": t["id"], "text": t["text"], "source": "file"}
        for t in transcript["turns"]
        if t["speaker"] == "customer"
    ]


def case_file(
    store: OpsStore,
    loan: BookLoan,
    customer: SimCustomer | None,
    call_date: date | None,
    started: datetime,
    outcome: str = "completed",
    status: str = "ready",
    *,
    book: bool = True,
    audio: dict | None = None,
    sid: str | None = None,
    book_over: dict | None = None,
    with_turns: bool = True,
    **over,
) -> dict:
    """A case file in the agreed contract. `call_date` None with book=True uses no book block."""
    sid = sid or sid_for(started)
    rid = loan.record.loan_id
    case: dict = {
        "version": 1,
        "session_id": sid,
        "record_id": rid,
        "loan_id": rid,
        "language": loan.record.borrower.language.value,
        "status": status,
        "started_at": started.isoformat(),
        "call_outcome": outcome,
        "ended_reason": "dialogue",
        "models": {"extraction": {"model": "r3-scripted"}},
        "turns": [],
        "recording": {"sha256": hashlib.sha256(sid.encode()).hexdigest()},
    }
    if audio is not None:
        case["customer_audio"] = audio
    if book and call_date is not None:
        d = draw_of(store, rid)
        case["book"] = {
            "batch_id": store.meta().batch_id,
            "draw_id": d.draw_id if d else "D-none",
            "sold_on": loan.sold_on.isoformat(),
            "call_date": call_date.isoformat(),
            "day_since_sale": (call_date - loan.sold_on).days,
        } | (book_over or {})
    if outcome == "completed" and customer is not None:
        script = script_call(loan, customer)
        result, _ = scripted_analysis(script, loan.record)
        transcript = script.transcript.model_dump(mode="json")
        transcript["call_id"] = sid
        case["transcript"] = transcript
        case["result"] = result.model_dump(mode="json")
        if with_turns:
            case["turns"] = amount_turns(transcript)
    case.update(over)
    return case


def put(sessions: Path, case: dict | str | bytes, name: str | None = None) -> Path:
    folder = sessions / (name or case["session_id"])  # type: ignore[index]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "case.json"
    if isinstance(case, bytes):
        path.write_bytes(case)
    elif isinstance(case, str):
        path.write_text(case, encoding="utf-8")
    else:
        path.write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
    return folder


def at_ist(d: date, hh: int, mm: int = 0) -> datetime:
    """A wall-clock started_at whose India time of day is hh:mm (the date is the wall-clock 2026 date)."""
    return datetime.combine(d, time(hh, mm), tzinfo=IST).astimezone(UTC)


def hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".lock"
    }


def india_day(at: datetime) -> date:
    return (at if at.tzinfo else at.replace(tzinfo=IST)).astimezone(IST).date()


def invariants(store: OpsStore, sessions: Path | None = None) -> list[str]:
    """Every rule the round-3 claims state, checked from the raw files (not through samajh.ops.batch)."""
    bad: list[str] = []
    root = store.root
    loans = {json.loads(l)["record"]["loan_id"]: json.loads(l) for l in (root / "book.jsonl").read_text().splitlines() if l}
    draws = [json.loads(l) for l in (root / "draws.jsonl").read_text().splitlines() if l] if (root / "draws.jsonl").exists() else []
    drawn_in = {x["loan_id"]: d for d in draws for x in d["drawn"]}
    rows = [json.loads(l) for l in (root / "attempts.jsonl").read_text().splitlines() if l] if (root / "attempts.jsonl").exists() else []
    eff: dict[str, dict] = {}
    for r in rows:
        if r["attempt_id"] in eff and r.get("supersedes") is None:
            bad.append(f"attempt id {r['attempt_id']} logged twice without supersedes")
        eff[r["attempt_id"]] = r
    outs = [json.loads(l) for l in (root / "outside.jsonl").read_text().splitlines() if l] if (root / "outside.jsonl").exists() else []
    eff_out: dict[str, dict] = {}
    for o in outs:
        eff_out[o["session_id"]] = o
    by_loan: dict[str, list[dict]] = {}
    for a in eff.values():
        by_loan.setdefault(a["loan_id"], []).append(a)
    for loan_id, chain in by_loan.items():
        if loan_id not in drawn_in:
            bad.append(f"{loan_id}: attempts on a loan no draw holds")
            continue
        chain.sort(key=lambda a: a["number"])
        nums = [a["number"] for a in chain]
        if nums != list(range(1, len(nums) + 1)):
            bad.append(f"{loan_id}: numbers {nums}")
        ats = [datetime.fromisoformat(a["at"]) for a in chain]
        if any(x >= y for x, y in zip(ats, ats[1:])):
            bad.append(f"{loan_id}: times not rising with number {[a.isoformat() for a in ats]}")
        if len(chain) > MAX_ATTEMPTS:
            bad.append(f"{loan_id}: {len(chain)} attempts > {MAX_ATTEMPTS}")
        for a, b in zip(chain, chain[1:]):
            if a["outcome"] not in {o.value for o in RETRY_AFTER}:
                bad.append(f"{loan_id}: attempt {b['number']} after terminal {a['outcome']}")
        sold = date.fromisoformat(loans[loan_id]["sold_on"])
        d = drawn_in[loan_id]
        for a, at in zip(chain, ats):
            day = (india_day(at) - sold).days
            if day != a["day_since_sale"]:
                bad.append(f"{a['attempt_id']}: day_since_sale {a['day_since_sale']} but India day gives {day}")
            if a["day_since_sale"] < 0:
                bad.append(f"{a['attempt_id']}: negative day")
            if india_day(at) < date.fromisoformat(d["as_of"]):
                bad.append(f"{a['attempt_id']}: before its draw")
            if a["draw_id"] != d["draw_id"]:
                bad.append(f"{a['attempt_id']}: draw {a['draw_id']} but loan drawn in {d['draw_id']}")
            if a["source"]["kind"] == "simulated" and a["day_since_sale"] > WINDOW_DAYS:
                bad.append(f"{a['attempt_id']}: simulated after day 30")
            if a["outcome"] == "completed" and not (root / "calls" / f"{a['call_id']}.json").exists():
                bad.append(f"{a['attempt_id']}: completed with no call file")
    # session call files: each named by exactly one effective attempt or outside call
    import re

    sess = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{12}$")
    named = [a.get("call_id") for a in eff.values()] + [o.get("call_id") for o in eff_out.values()]
    for p in (root / "calls").glob("*.json") if (root / "calls").is_dir() else ():
        if sess.fullmatch(p.stem) and named.count(p.stem) != 1:
            bad.append(f"call file {p.name} named {named.count(p.stem)} times")
    # one session -> at most one place in the store
    phone_sids = [a["source"]["session_id"] for a in eff.values() if a["source"]["kind"] == "phone_session"]
    for s in set(phone_sids):
        if phone_sids.count(s) > 1:
            bad.append(f"session {s} is {phone_sids.count(s)} attempts")
        if s in eff_out:
            bad.append(f"session {s} is both an attempt and an outside call")
    # ingest summary: each folder exactly once
    ing = root / "ingest.json"
    if ing.exists():
        j = json.loads(ing.read_text())
        listed = list(j["linked"]) + list(j["outside"]) + [s["session_id"] for s in j["skipped"]]
        dup = {x for x in listed if listed.count(x) > 1}
        if dup:
            bad.append(f"ingest summary lists sessions twice: {sorted(dup)}")
        if sessions is not None and sessions.is_dir():
            folders = {p.name for p in sessions.iterdir() if p.is_dir()}
            if folders != set(listed):
                bad.append(
                    f"ingest summary vs folders: missing {sorted(folders - set(listed))}, extra {sorted(set(listed) - folders)}"
                )
        for s in j["skipped"]:
            if not s["reason"].strip():
                bad.append(f"skipped {s['session_id']} with an empty reason")
            if s["session_id"] in phone_sids or s["session_id"] in eff_out:
                bad.append(
                    f"session {s['session_id']} is listed as skipped (not in any count) but is in the store "
                    f"as {'an attempt' if s['session_id'] in phone_sids else 'an outside call'}"
                )
    return bad
