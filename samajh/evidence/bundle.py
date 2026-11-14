"""The evidence bundle of one reviewed case: `export` writes it, `verify_bundle` re-checks it from the
bundle alone, `check_state` re-checks a whole state directory.

What verify proves: the bundle's files agree with each other and with the digests written down when
the session, the case and each decision were made, and with `root_sha256`. What it cannot prove: that
nobody rebuilt every digest after an edit (anyone with this code can), who made a decision, or when.
Compare `root_sha256` with the copy made at export time: that comparison is what makes the bundle
"what was exported then". Layout and order of checks: the W6 spec; `__main__` prints usage.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import wave
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from samajh.evidence.case_seal import verify_case
from samajh.evidence.decisions import CASE_TAG, verify_dispositions
from samajh.evidence.digest import GENESIS, after_epoch, digest, file_sha256, sha256_hex, tagged
from samajh.evidence.ledger import (
    LEDGER,
    batch_created_at,
    call_dated_after_epoch,
    ledger_entries,
    ledger_head,
    verify_call_ledger,
)
from samajh.evidence.ledger import (
    _entry_hash as _ledger_entry_hash,
)
from samajh.evidence.session import (
    _entry_hash,
    session_fields_json,
    session_seal,
    verify_session_dir,
)

KIND = "samajh-evidence-bundle"
MANIFEST = "manifest.json"
OK, MISMATCH, USAGE, UNVERIFIABLE, WARNING = 0, 1, 2, 3, 4
PHONE_FILES = ("case/case.json", "session/chain.jsonl", "session/fields.json", "session/events.json")
SECOND_CHECK_STEP = "second_check"  # the `step` tag of the year-of-birth question's line


class Refused(Exception):
    """Export refused; `code` is the exit code (USAGE or MISMATCH)."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class Mismatch(Exception):
    pass


# --- shared helpers -----------------------------------------------------------------


def _safe_name(name: str) -> bool:
    return bool(name) and "/" not in name and "\\" not in name and name not in (".", "..")


def _quotes_of_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Every flag and gap of a CaseResult's JSON, products first, as (kind, row) pairs."""
    rows: list[dict[str, Any]] = []
    for product in result.get("products") or []:
        rows += [{"kind": "flag", **f} for f in product.get("flags") or []]
        rows += [{"kind": "gap", **g} for g in product.get("gaps") or []]
    rows += [{"kind": "flag", **f} for f in result.get("case_flags") or []]
    rows += [{"kind": "gap", **g} for g in result.get("case_gaps") or []]
    return rows


def _flatten(rows: list[dict[str, Any]], spans: Any) -> list[dict[str, Any]]:
    """One item per quote: each row's own quote, then its `also` quotes. `spans(item)` gives
    (start_s, end_s)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        for q in [row, *(row.get("also") or [])]:
            if q.get("quote") is None:
                continue
            start, end = spans(q)
            out.append(
                {
                    "kind": row["kind"],
                    "rule_id": row.get("rule_id"),
                    "reason": row.get("reason"),
                    "quote": q["quote"],
                    "turn_id": q.get("turn_id"),
                    "start_s": start,
                    "end_s": end,
                }
            )
    return out


def cut_clip(call_wav: bytes, start_s: float, end_s: float) -> bytes:
    """Frames round(start*rate) to round(end*rate) of a mono 16-bit WAV, as a WAV at the same rate."""
    with wave.open(io.BytesIO(call_wav)) as src:
        if src.getnchannels() != 1 or src.getsampwidth() != 2:
            raise ValueError("call.wav is not mono 16-bit")
        rate, total = src.getframerate(), src.getnframes()
        a = min(max(round(start_s * rate), 0), total)
        b = min(max(round(end_s * rate), a), total)
        src.setpos(a)
        frames = src.readframes(b - a)
    out = io.BytesIO()
    with wave.open(out, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(rate)
        dst.writeframes(frames)
    return out.getvalue()


def _wav_info(data: bytes) -> tuple[int, int]:
    with wave.open(io.BytesIO(data)) as w:
        return w.getframerate(), w.getnframes()


def _lines(data: bytes) -> list[bytes]:
    return [line for line in data.split(b"\n") if line]


def _withheld_seqs(events: list[dict[str, Any]]) -> set[int]:
    """Seqs of the customer events `samajh_dialogue.shown_log` withholds: replies to the
    year-of-birth question (also one already withheld on disk)."""
    from pydantic import TypeAdapter

    from samajh.server.samajh_dialogue import answers_year_question
    from samajh.server.sessionlog import BotEvent, CustomerEvent, Event

    parsed = [TypeAdapter(Event).validate_python(e) for e in events]
    seqs = set()
    for e in parsed:
        if isinstance(e, CustomerEvent) and e.reply_to is not None and e.reply_to < len(parsed):
            asked = parsed[e.reply_to]
            if isinstance(asked, BotEvent) and answers_year_question(asked.lines):
                seqs.add(e.seq)
    return seqs


# --- export -------------------------------------------------------------------------


@dataclass
class Exported:
    root_sha256: str
    manifest: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def export(state: Path, case_id: str, out: Path, *, with_recording: bool = False) -> Exported:
    ops = state / "ops"
    sessions = state / "sessions"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Refused(USAGE, f"{out} exists and is not empty")
    call_path = ops / "calls" / f"{case_id}.json"
    if not _safe_name(case_id) or not call_path.is_file():
        raise Refused(USAGE, f"no case {case_id!r} in {ops / 'calls'}")
    call_raw = call_path.read_bytes()
    try:
        call = json.loads(call_raw)
        source = call.get("source") or {}
        phone = source.get("kind") == "phone_session"
    except (ValueError, AttributeError) as e:
        raise Refused(MISMATCH, f"{call_path.name}: malformed ({type(e).__name__})") from None
    session_id = source.get("session_id") if phone else None
    if (
        phone
        and isinstance(session_id, str)
        and _safe_name(session_id)
        and not (sessions / session_id).exists()
    ):
        deleted = _retention_date(ops, session_id)
        if deleted is not None:
            raise Refused(USAGE, f"the session was deleted by retention on {deleted} (ops/retention.jsonl)")

    notes: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}
    files: dict[str, bytes] = {"case/call-record.json": call_raw}

    disp_path = ops / "dispositions.jsonl"
    ok, problem, head = verify_dispositions(disp_path)
    if not ok:
        raise Refused(MISMATCH, f"source dispositions.jsonl: {problem}")
    checks["decisions"] = "verified"

    entry = next((e for e in reversed(ledger_entries(ops)) if e.get("call_id") == case_id), None)
    created = batch_created_at(ops)
    if entry is None:
        if call_dated_after_epoch(call, created):
            raise Refused(MISMATCH, f"call {case_id}: dated after the evidence epoch but has no ledger line")
        notes.append("The call record was written before the call ledger: its file is not covered by one.")
        checks["call_ledger"] = "unverifiable"
    elif entry.get("sha256") != sha256_hex(call_raw):
        raise Refused(MISMATCH, f"call {case_id}: sha256 differs from its line in {LEDGER}")
    else:
        checks["call_ledger"] = "verified"
    lhead, lcount = ledger_head(ops)
    files["case/call-ledger.json"] = _json(
        {"entry": entry, "head": lhead, "lines": lcount, "batch_created_at": created}
    )

    case: dict[str, Any] | None = None
    session: dict[str, Any] | None = None
    sdir: Path | None = None
    if phone:
        if not isinstance(session_id, str) or not _safe_name(session_id):
            raise Refused(MISMATCH, "the call record names no usable session id")
        sdir = sessions / session_id
        sc = verify_session_dir(sdir)
        if sc.status == "mismatch":
            raise Refused(MISMATCH, f"source session {session_id}: {sc.problem}")
        checks["session"] = sc.status
        if sc.status == "unverifiable":
            notes.append(
                f"The session was {sc.problem}: its log and audio are exported but not covered by a chain."
            )
        if sc.adopted:
            notes.append("The session chain was adopted: nothing before its entry 0 is covered.")
        case_path = sdir / "case.json"
        if not case_path.is_file():
            raise Refused(MISMATCH, f"source session {session_id} has no case.json")
        case_raw = case_path.read_bytes()
        cc = verify_case(case_raw, sdir)
        if cc.status == "mismatch":
            raise Refused(MISMATCH, f"source case.json of {session_id}: {cc.problem}")
        checks["case"] = cc.status
        if cc.status == "unverifiable":
            notes.append(f"The case file was {cc.problem}: its content is not covered by a seal.")
        if cc.changed_after_seal:
            checks["changed_after_seal"] = cc.changed_after_seal
            notes.append(
                "The session changed after the case was sealed (browser reports and the like): "
                + "; ".join(cc.changed_after_seal)
            )
        case = json.loads(case_raw)
        files["case/case.json"] = case_raw
        session = json.loads((sdir / "session.json").read_bytes())
        if (sdir / "chain.jsonl").is_file():
            files["session/chain.jsonl"] = (sdir / "chain.jsonl").read_bytes()
        files["session/fields.json"] = _json(session_fields_json(session))
        events = session.get("events") or []
        withheld = _withheld_seqs(events)
        shown = [
            {"seq": e["seq"], "type": e.get("type"), "reply_to": e.get("reply_to"), "withheld": True,
             "sha256": digest(e)} if e["seq"] in withheld else e
            for e in events
        ]  # fmt: skip
        files["session/events.json"] = _json(shown)
        if withheld:
            notes.append(
                "The reply to the year-of-birth question is withheld: events.json carries its digest only, "
                "and its audio is never exported."
            )
    else:
        checks["session"] = "not applicable"
        checks["case"] = "not applicable"
        notes.append(
            "Simulated call: no phone session, no audio and no case file; the call record is the case."
        )

    # Quotes
    wav_bytes: bytes | None = None
    if phone:
        assert case is not None and sdir is not None
        rows = [dict(r) for r in case.get("evidence") or []]

        def spans(q: dict[str, Any]) -> tuple[Any, Any]:
            return q.get("start_s"), q.get("end_s")

        items = _flatten(rows, spans)
        if (sdir / "call.wav").is_file():
            wav_bytes = (sdir / "call.wav").read_bytes()
    else:
        turns = {t["id"]: t for t in (call.get("transcript") or {}).get("turns") or []}

        def spans(q: dict[str, Any]) -> tuple[Any, Any]:
            t = turns.get(q.get("turn_id"))
            return (t.get("start_s"), t.get("end_s")) if t else (None, None)

        items = _flatten(_quotes_of_result(call.get("result") or {}), spans)
    clips: dict[tuple[Any, Any, Any], str] = {}
    for n, item in enumerate(items, start=1):
        item_out = {"n": n, **item, "clip": None, "clip_sha256": None}
        if wav_bytes is not None and item["start_s"] is not None and item["end_s"] is not None:
            key = (item["turn_id"], item["start_s"], item["end_s"])
            if key not in clips:
                name = f"quotes/q{len(clips) + 1:02d}.wav"
                clips[key] = name
                files[name] = cut_clip(wav_bytes, item["start_s"], item["end_s"])
            item_out["clip"] = clips[key]
            item_out["clip_sha256"] = sha256_hex(files[clips[key]])
        items[n - 1] = item_out
    files["quotes/quotes.json"] = _json(items)
    if phone and wav_bytes is None:
        notes.append("The session has no call.wav: no quote has a clip.")

    # Recording
    recording = (session or {}).get("recording") if phone else None
    if phone:
        rec = {
            "sha256": recording.get("sha256") if recording else None,
            "seconds": recording.get("seconds") if recording else None,
            "sample_rate": recording.get("sample_rate") if recording else None,
            "included": bool(with_recording and wav_bytes is not None),
        }
        if with_recording and wav_bytes is not None:
            assert sdir is not None and session is not None
            files["recording/call.wav"] = wav_bytes
            for e in session.get("events") or []:
                ref = e.get("audio")
                if ref is None or e["seq"] in withheld:
                    continue
                name = ref.removeprefix("audio/")
                if not ref.startswith("audio/") or not _safe_name(name):
                    raise Refused(MISMATCH, f"event seq {e['seq']} has a malformed audio name")
                path = sdir / "audio" / name
                if path.is_file():
                    files[f"session/audio/{name}"] = path.read_bytes()
            if withheld:
                warnings.append(
                    "recording/call.wav still holds the spoken reply to the year-of-birth question: "
                    "the case file withholds only its words."
                )
                notes.append(warnings[-1])
        else:
            notes.append("The recording is not included: its sha256 is, and clips are cut from it.")
    else:
        rec = {"included": False, "reason": "simulated call: no audio"}
    files["recording.json"] = _json(rec)

    # Decisions
    lines = _lines(disp_path.read_bytes()) if disp_path.is_file() else []
    mine: list[bytes] = []
    chain_rows = []
    for n, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except ValueError:
            row = {}
        is_case = row.get("case_id") == case_id
        if is_case:
            mine.append(line)
        chain_rows.append(
            {"n": n, "sha256": sha256_hex(line), "prev_sha256": row.get("prev_sha256"), "case": is_case}
        )
    files["decisions/decisions.jsonl"] = b"".join(line + b"\n" for line in mine)
    files["decisions/chain.json"] = _json({"head": head, "lines": chain_rows})

    seal = (case or {}).get("seal") or {}
    inputs = seal.get("inputs") or {}
    call_sha = sha256_hex(call_raw)
    content = seal.get("content_sha256")
    manifest: dict[str, Any] = {
        "version": 1,
        "kind": KIND,
        "case_id": case_id,
        "source": "phone_session" if phone else "simulated",
        "session_id": session_id,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": [{"path": p, "sha256": sha256_hex(b), "bytes": len(b)} for p, b in sorted(files.items())],
        "digests": {
            "call_record_sha256": call_sha,
            "case_digest": tagged(CASE_TAG, call_sha, content or "none"),
            "case_content_sha256": content,
            "case_inputs_sha256": seal.get("inputs_sha256"),
            "session_head": inputs.get("session_head"),
            "session_entries": inputs.get("session_entries"),
            "session_seal": inputs.get("session_seal"),
            "recording_sha256": rec.get("sha256"),
            "decisions_head": head,
            "call_ledger_head": lhead,
        },
        "source_checks": checks,
        "notes": notes,
    }
    manifest["root_sha256"] = digest(manifest)
    created_out = not out.exists()
    out.mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (out / MANIFEST).write_bytes(_json(manifest))
    verdict = verify_bundle(out)
    if verdict.mismatch:
        if created_out:
            shutil.rmtree(out)
        else:
            for child in out.iterdir():
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        raise Refused(MISMATCH, f"the bundle written does not verify, so it was deleted: {verdict.mismatch}")
    return Exported(manifest["root_sha256"], manifest, warnings)


def _retention_date(ops: Path, session_id: str) -> str | None:
    """The date retention deleted this session, from `ops/retention.jsonl`, or None."""
    try:
        data = (ops / "retention.jsonl").read_bytes()
    except FileNotFoundError:
        return None
    found = None
    for line in data.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("session_id") == session_id:
            found = str(row.get("deleted_at") or "")[:10] or "an unrecorded date"
    return found


def _json(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, ensure_ascii=False).encode() + b"\n"


# --- verify -------------------------------------------------------------------------


@dataclass
class Verdict:
    mismatch: str | None = None
    unverifiable: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    reading: str = MANIFEST  # the file being read, named when malformed input raises

    @property
    def code(self) -> int:
        if self.mismatch:
            return MISMATCH
        if self.warnings:
            return WARNING
        return UNVERIFIABLE if self.unverifiable else OK


def verify_bundle(root: Path) -> Verdict:
    v = Verdict()
    try:
        _verify(root, v)
    except Mismatch as e:
        v.mismatch = str(e)
    except Exception as e:  # noqa: BLE001  (malformed input of any shape)  # malformed input of any shape is a mismatch, never a traceback
        v.mismatch = f"{v.reading}: malformed ({type(e).__name__})"
    return v


def _load_json(data: bytes, where: str) -> Any:
    try:
        return json.loads(data)
    except ValueError:
        raise Mismatch(f"{where} does not parse") from None


def _verify(root: Path, v: Verdict) -> None:
    mpath = root / MANIFEST
    if mpath.is_symlink() or not mpath.is_file():
        raise Mismatch(f"{MANIFEST} is missing")
    manifest = _load_json(mpath.read_bytes(), MANIFEST)
    if not isinstance(manifest, dict) or manifest.get("kind") != KIND or manifest.get("version") != 1:
        raise Mismatch(f"{MANIFEST} is not a version 1 {KIND}")
    body = {k: val for k, val in manifest.items() if k != "root_sha256"}
    if manifest.get("root_sha256") != digest(body):
        raise Mismatch(f"{MANIFEST}: root_sha256 does not recompute")
    v.checked.append(f"manifest root_sha256 {manifest['root_sha256']}")

    # Files: every listed one present and matching, nothing else, nothing outside DIR.
    listed: dict[str, dict[str, Any]] = {}
    for row in manifest.get("files") or []:
        p = row.get("path")
        pure = PurePosixPath(p) if isinstance(p, str) else None
        if pure is None or pure.is_absolute() or ".." in pure.parts or "\\" in p or p == MANIFEST or not p:
            raise Mismatch(f"{MANIFEST}: file path {p!r} is not inside the bundle")
        if p in listed:
            raise Mismatch(f"{MANIFEST}: file path {p!r} is listed twice")
        listed[p] = row
    present: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                raise Mismatch(f"{rel} is a symlink")
            if name in filenames:
                present.add(rel)
    present.discard(MANIFEST)
    for p, row in sorted(listed.items()):
        f = root / p
        if p not in present:
            raise Mismatch(f"{p} is listed in the manifest but missing")
        if f.stat().st_size != row.get("bytes") or file_sha256(f) != row.get("sha256"):
            raise Mismatch(f"{p}: sha256 or size does not match the manifest")
    extra = sorted(present - set(listed))
    if extra:
        raise Mismatch(f"{extra[0]} is in the bundle but not in the manifest")
    v.checked.append(f"{len(listed)} files match the manifest")

    def read(p: str) -> bytes | None:
        v.reading = p
        return (root / p).read_bytes() if p in listed else None

    dg = manifest.get("digests") or {}
    case_id = manifest.get("case_id")
    call_raw = read("case/call-record.json")
    if call_raw is None:
        raise Mismatch("case/call-record.json is missing")
    if sha256_hex(call_raw) != dg.get("call_record_sha256"):
        raise Mismatch("case/call-record.json: sha256 differs from the manifest's call_record_sha256")
    expected_digest = tagged(CASE_TAG, dg["call_record_sha256"], dg.get("case_content_sha256") or "none")
    if dg.get("case_digest") != expected_digest:
        raise Mismatch(f"{MANIFEST}: case_digest does not recompute")
    call = _load_json(call_raw, "case/call-record.json")
    if call.get("call_id") != case_id:
        raise Mismatch("case/call-record.json: call_id is not the bundle's case")
    v.checked.append("call record and case digest")

    # The source is the call record's, never the manifest's word alone.
    source = call.get("source") or {}
    kind = source.get("kind")
    if kind not in ("phone_session", "simulated"):
        raise Mismatch(f"case/call-record.json: source.kind {kind!r} is not phone_session or simulated")
    if manifest.get("source") != kind:
        raise Mismatch(
            f"{MANIFEST}: source {manifest.get('source')!r} differs from the call record's {kind!r}"
        )
    phone = kind == "phone_session"
    session_id = source.get("session_id") if phone else None
    if manifest.get("session_id") != session_id:
        raise Mismatch(f"{MANIFEST}: session_id differs from the call record's")
    if phone:
        for p in ("case/case.json", "session/fields.json", "session/events.json"):
            if p not in listed:
                raise Mismatch(f"{p} is missing: the call record's source is a phone session")
    else:
        stray = sorted(p for p in listed if p in PHONE_FILES or p.startswith(("session/", "recording/")))
        stray += sorted(p for p in listed if p.startswith("quotes/") and p != "quotes/quotes.json")
        if stray:
            raise Mismatch(f"{stray[0]} is in the bundle, but the call record's source is simulated")
    _verify_call_ledger(read, call_raw, case_id, session_id, dg, v)

    case = None
    if phone:
        case = _verify_phone(read, listed, manifest, dg, v)
    else:
        v.checked.append("simulated call: no session, case file or audio to check")

    # Quotes
    qraw = read("quotes/quotes.json")
    if qraw is None:
        raise Mismatch("quotes/quotes.json is missing")
    quotes = _load_json(qraw, "quotes/quotes.json")
    if not isinstance(quotes, list) or not all(isinstance(q, dict) for q in quotes):
        raise Mismatch("quotes/quotes.json: malformed (not a list of objects)")
    turns = {t.get("id"): t for t in (call.get("transcript") or {}).get("turns") or []}
    if case is not None:
        rows = [{"kind": "evidence", **r} for r in case.get("evidence") or []]
        whose = "case/case.json evidence"
    else:
        rows = _quotes_of_result(call.get("result") or {})
        whose = "the call record's result"
    expected = Counter((q["quote"], q.get("turn_id")) for q in _flatten(rows, lambda q: (None, None)))
    evidence = set(expected)
    for q in quotes:
        where = f"quotes/quotes.json item {q.get('n')}"
        turn = turns.get(q.get("turn_id"))
        if turn is None or not isinstance(q.get("quote"), str) or q["quote"] not in (turn.get("text") or ""):
            raise Mismatch(
                f"{where}: the quote is not in transcript turn {q.get('turn_id')} of the call record"
            )
        if (q["quote"], q["turn_id"]) not in evidence:
            raise Mismatch(f"{where}: the quote is not in {whose}")
        if (q.get("start_s"), q.get("end_s")) != (turn.get("start_s"), turn.get("end_s")):
            raise Mismatch(f"{where}: start_s/end_s differ from transcript turn {q['turn_id']}")
        clip = q.get("clip")
        if clip is not None:
            data = read(clip)
            if data is None:
                raise Mismatch(f"{where}: clip {clip} is not in the bundle")
            if sha256_hex(data) != q.get("clip_sha256"):
                raise Mismatch(f"{clip}: sha256 differs from {where}")
            rate, frames = _wav_info(data)
            if abs(frames - (q["end_s"] - q["start_s"]) * rate) > 1:
                raise Mismatch(f"{clip}: length is not end_s - start_s of {where}")
    held = Counter((q.get("quote"), q.get("turn_id")) for q in quotes)
    for gone, what in ((expected - held, "is missing"), (held - expected, "is there more often than in it")):
        if gone:
            quote, turn_id = min(gone, key=str)
            raise Mismatch(f"quotes/quotes.json: a quote of {whose} {what} (turn {turn_id}: {quote!r})")
    v.checked.append(f"{len(quotes)} quotes against the transcript")
    if phone and read("recording/call.wav") is not None:
        wav = read("recording/call.wav")
        for q in quotes:
            if q.get("clip") and cut_clip(wav, q["start_s"], q["end_s"]) != read(q["clip"]):
                raise Mismatch(f"{q['clip']}: not byte-identical to its cut from recording/call.wav")
        v.checked.append("every clip re-cut from recording/call.wav")

    # Decisions
    draw = read("decisions/decisions.jsonl")
    craw = read("decisions/chain.json")
    if draw is None or craw is None:
        raise Mismatch("decisions/decisions.jsonl or decisions/chain.json is missing")
    chain = _load_json(craw, "decisions/chain.json")
    v.reading = "decisions/chain.json"
    rows = chain.get("lines") or []
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise Mismatch("decisions/chain.json: malformed (lines is not a list of objects)")
    for i, row in enumerate(rows, start=1):
        if row.get("n") != i:
            raise Mismatch(f"decisions/chain.json entry {i}: has n={row.get('n')}")
    case_rows = [r for r in rows if r.get("case")]
    mine = _lines(draw)
    if len(mine) != len(case_rows):
        raise Mismatch(
            f"decisions/decisions.jsonl has {len(mine)} lines, decisions/chain.json marks {len(case_rows)} for this case"
        )
    for line, row in zip(mine, case_rows, strict=True):
        where = f"decisions/decisions.jsonl (log line {row['n']})"
        if sha256_hex(line) != row.get("sha256"):
            raise Mismatch(f"{where}: sha256 differs from decisions/chain.json")
        parsed = _load_json(line, where)
        if parsed.get("case_id") != case_id:
            raise Mismatch(f"{where}: case_id is not the bundle's case")
        if parsed.get("prev_sha256") != row.get("prev_sha256"):
            raise Mismatch(f"{where}: prev_sha256 differs from decisions/chain.json")
        if parsed.get("prev_sha256") is None and (parsed.get("case_digest") or parsed.get("reviewer_auth")):
            raise Mismatch(f"{where}: has a case digest but no prev_sha256")
    chained = False
    for i, row in enumerate(rows):
        prev = row.get("prev_sha256")
        if prev is None:
            if chained:
                raise Mismatch(f"decisions/chain.json line {row['n']}: no prev_sha256 after the chain began")
            continue
        chained = True
        expected = rows[i - 1].get("sha256") if i else GENESIS
        if prev != expected:
            raise Mismatch(f"decisions/chain.json line {row['n']}: prev_sha256 does not link to line {i}")
    last = rows[-1]["sha256"] if rows else None
    if chain.get("head") != last or dg.get("decisions_head") != last:
        raise Mismatch(
            "decisions/chain.json: head is not the last line's sha256, or differs from the manifest"
        )
    for line, row in zip(mine, case_rows, strict=True):
        made_on = json.loads(line).get("case_digest")
        if made_on is None:
            v.unverifiable.append(
                f"decision on log line {row['n']} was recorded before decisions carried a case digest"
            )
        elif made_on != dg["case_digest"]:
            v.warnings.append(
                f"decision on log line {row['n']} was made on a different version of this case: an earlier "
                "version, or the line was moved from another case"
            )
    v.checked.append(f"{len(mine)} decisions on this case, decision log of {len(rows)} lines chained")


def _verify_phone(read, listed, manifest, dg, v: Verdict) -> dict[str, Any]:
    case_raw = read("case/case.json")
    if case_raw is None:
        raise Mismatch("case/case.json is missing")
    case = _load_json(case_raw, "case/case.json")
    seal = case.get("seal")
    cc = verify_case(case_raw)
    if cc.status == "mismatch":
        raise Mismatch(f"case/case.json: {cc.problem}")
    if cc.status == "unverifiable":
        v.unverifiable.append(f"case/case.json was {cc.problem}")
        inputs: dict[str, Any] = {}
    else:
        inputs = seal["inputs"]
        for key, value in (
            ("case_content_sha256", seal["content_sha256"]),
            ("case_inputs_sha256", seal["inputs_sha256"]),
            ("session_head", inputs.get("session_head")),
            ("session_entries", inputs.get("session_entries")),
            ("session_seal", inputs.get("session_seal")),
        ):
            if dg.get(key) != value:
                raise Mismatch(f"case/case.json: seal differs from the manifest's {key}")
        v.checked.append("case/case.json seal")
    if (case.get("session_id")) != manifest.get("session_id"):
        raise Mismatch("case/case.json: session_id is not the bundle's session")

    fields = _load_json(read("session/fields.json") or b"null", "session/fields.json")
    events = _load_json(read("session/events.json") or b"null", "session/events.json")
    if not isinstance(fields, dict) or not isinstance(events, list):
        raise Mismatch("session/fields.json or session/events.json is missing")
    rec_sha = dg.get("recording_sha256")
    if rec_sha != (case.get("recording") or {}).get("sha256") or rec_sha != (
        fields.get("recording") or {}
    ).get("sha256"):
        raise Mismatch(
            "recording_sha256 differs between the manifest, case/case.json and session/fields.json"
        )

    craw = read("session/chain.jsonl")
    if craw is None:
        if inputs.get("session_head") is not None:
            raise Mismatch("session/chain.jsonl is missing but case/case.json's seal names a session_head")
        if after_epoch(manifest.get("session_id")):
            raise Mismatch(
                "session/chain.jsonl is missing: the session is dated after the evidence epoch but has no chain"
            )
        _check_withheld(events)
        v.unverifiable.append("the session was written before the evidence chain: its log is not covered")
        return case
    entries: list[dict[str, Any]] = []
    prev = GENESIS
    if not craw.endswith(b"\n"):
        raise Mismatch("session/chain.jsonl ends in a torn line")
    for n, line in enumerate(craw.decode("utf-8", errors="replace").splitlines()):
        e = _load_json(line.encode(), f"session/chain.jsonl line {n}")
        what = "session fields" if e.get("kind") == "session" else f"event seq {e.get('seq')}"
        where = f"session/chain.jsonl entry {n} ({what})"
        if e.get("i") != n:
            raise Mismatch(f"{where}: has i={e.get('i')}")
        if e.get("prev") != prev:
            raise Mismatch(f"{where}: prev does not match {'GENESIS' if n == 0 else f'entry {n - 1} hash'}")
        if e.get("hash") != _entry_hash(e):
            raise Mismatch(f"{where}: hash does not recompute")
        prev = e["hash"]
        entries.append(e)
    if entries and entries[0].get("adopted"):
        v.unverifiable.append("session chain entry 0 is adopted: the session before it is not covered")
    head = inputs.get("session_head")
    if head is None and cc.status == "verified":
        raise Mismatch(
            "case/case.json: the seal names no session_head but the bundle has session/chain.jsonl"
        )
    if head is not None:
        n = inputs.get("session_entries")
        if not isinstance(n, int) or not 1 <= n <= len(entries) or entries[n - 1]["hash"] != head:
            raise Mismatch(
                f"case/case.json: session_head is not the hash of session/chain.jsonl entry {n - 1 if isinstance(n, int) else n}"
            )
        if inputs.get("session_seal") is not None and (
            rec_sha is None or inputs["session_seal"] != session_seal(head, rec_sha)
        ):
            raise Mismatch(
                "case/case.json: session_seal does not recompute from session_head and recording_sha256"
            )
    last_session = None
    last_event: dict[int, dict[str, Any]] = {}
    for e in entries:
        if e.get("kind") == "session":
            last_session = e
        else:
            last_event[e.get("seq")] = e
    if last_session is None or last_session["sha256"] != digest(fields):
        raise Mismatch("session/fields.json does not match the latest session entry of session/chain.jsonl")
    _check_withheld(events)
    for pos, item in enumerate(events):
        if not isinstance(item, dict) or item.get("seq") != pos:
            raise Mismatch(f"session/events.json item {pos}: seq is not {pos}")
        e = last_event.get(pos)
        if e is None:
            raise Mismatch(f"session/events.json item {pos}: no chain entry for event seq {pos}")
        got = item.get("sha256") if item.get("withheld") is True else digest(item)
        if got != e["sha256"]:
            raise Mismatch(
                f"session/events.json event seq {pos} does not match session/chain.jsonl entry {e['i']}"
            )
    if set(last_event) != set(range(len(events))):
        missing = sorted(set(last_event) - set(range(len(events))))
        raise Mismatch(f"session/events.json has no item for event seq {missing[0]} of session/chain.jsonl")
    v.checked.append(f"session chain of {len(entries)} entries, fields and {len(events)} events")

    wav = read("recording/call.wav")
    if wav is not None:
        if sha256_hex(wav) != rec_sha:
            raise Mismatch("recording/call.wav: sha256 differs from recording_sha256")
        for item in events:
            ref = item.get("audio") if not item.get("withheld") else None
            if ref is None:
                continue
            path = "session/" + ref
            data = read(path)
            if data is None:
                raise Mismatch(f"{path} (event seq {item['seq']}) is not in the bundle")
            if sha256_hex(data) != last_event[item["seq"]].get("audio_sha256"):
                raise Mismatch(
                    f"{path}: sha256 differs from session/chain.jsonl entry {last_event[item['seq']]['i']} (event seq {item['seq']})"
                )
        v.checked.append("recording and event audio against the chain")
    return case


def _check_withheld(events: list[Any]) -> None:
    """A withheld stub only for a customer reply to the year-of-birth question: its `reply_to` bot
    event is present, not withheld, and its last line's `tags.step` is the second check."""
    for pos, item in enumerate(events):
        if not isinstance(item, dict) or item.get("withheld") is not True:
            continue
        asked = item.get("reply_to")
        bot = events[asked] if isinstance(asked, int) and 0 <= asked < len(events) else None
        lines = bot.get("lines") if isinstance(bot, dict) else None
        ok = (
            item.get("type") == "customer"
            and isinstance(bot, dict)
            and bot.get("type") == "bot"
            and bot.get("withheld") is not True
            and isinstance(lines, list)
            and bool(lines)
            and isinstance(lines[-1], dict)
            and (lines[-1].get("tags") or {}).get("step") == SECOND_CHECK_STEP
        )
        if not ok:
            raise Mismatch(
                f"session/events.json item {pos}: withheld, but it is not a reply to the year-of-birth question"
            )


def _verify_call_ledger(read, call_raw: bytes, case_id: Any, session_id: Any, dg: dict, v: Verdict) -> None:
    raw = read("case/call-ledger.json")
    if raw is None:
        raise Mismatch("case/call-ledger.json is missing")
    ledger = _load_json(raw, "case/call-ledger.json")
    entry = ledger.get("entry")
    if ledger.get("head") != dg.get("call_ledger_head"):
        raise Mismatch("case/call-ledger.json: head differs from the manifest's call_ledger_head")
    if entry is None:
        dated = after_epoch(session_id) if session_id else after_epoch(ledger.get("batch_created_at"))
        if dated:
            raise Mismatch(
                "case/call-ledger.json: the call is dated after the evidence epoch but has no ledger line"
            )
        v.unverifiable.append("the call record was written before the call ledger: its file is not covered")
        return
    if not isinstance(entry, dict) or entry.get("hash") != _ledger_entry_hash(entry):
        raise Mismatch("case/call-ledger.json: the entry's hash does not recompute")
    if entry.get("call_id") != case_id:
        raise Mismatch("case/call-ledger.json: the entry names another call")
    if entry.get("sha256") != sha256_hex(call_raw):
        raise Mismatch("case/call-ledger.json: the entry's sha256 differs from case/call-record.json")
    v.checked.append(f"call record against its {LEDGER} entry {entry.get('i')}")


# --- check a whole state directory ---------------------------------------------------


@dataclass
class StateCheck:
    counts: dict[str, int]
    problems: list[str]
    lines: list[str]
    unverifiable: list[str] = field(default_factory=list)
    usage: str | None = None  # set when the state directory is not one: exit 2

    @property
    def code(self) -> int:
        if self.usage:
            return USAGE
        if self.problems:
            return MISMATCH
        return UNVERIFIABLE if self.unverifiable else OK


def check_state(state: Path) -> StateCheck:
    sessions = state / "sessions"
    ops = state / "ops"
    if not state.is_dir() or not (sessions.is_dir() or ops.is_dir()):
        return StateCheck({}, [], [], usage=f"{state} is not a state directory (no sessions/ and no ops/)")
    counts = {"verified": 0, "mismatch": 0, "unverifiable": 0}
    case_counts = {"verified": 0, "mismatch": 0, "unverifiable": 0}
    problems: list[str] = []
    unverifiable: list[str] = []
    for d in sorted(p for p in sessions.iterdir() if p.is_dir()) if sessions.is_dir() else []:
        try:
            sc = verify_session_dir(d)
        except Exception as e:  # noqa: BLE001  (malformed input of any shape)
            sc = None
            problems.append(f"session {d.name}: malformed ({type(e).__name__})")
            counts["mismatch"] += 1
        if sc is not None:
            counts[sc.status] += 1
            if sc.status == "mismatch":
                problems.append(f"session {d.name}: {sc.problem}")
            elif sc.status == "unverifiable":
                unverifiable.append(f"session {d.name}: {sc.problem}")
        if (d / "case.json").is_file():
            try:
                cc = verify_case((d / "case.json").read_bytes(), d)
            except Exception as e:  # noqa: BLE001  (malformed input of any shape)
                case_counts["mismatch"] += 1
                problems.append(f"case {d.name}: case.json: malformed ({type(e).__name__})")
                continue
            case_counts[cc.status] += 1
            if cc.status == "mismatch":
                problems.append(f"case {d.name}: {cc.problem}")
            elif cc.status == "unverifiable":
                unverifiable.append(f"case {d.name}: {cc.problem}")
    try:
        ok, problem, head = verify_dispositions(ops / "dispositions.jsonl")
    except Exception as e:  # noqa: BLE001  (malformed input of any shape)
        ok, problem, head = False, f"malformed ({type(e).__name__})", None
    if not ok:
        problems.append(f"dispositions.jsonl: {problem}")
    try:
        call_problems, call_unverifiable, call_head = verify_call_ledger(ops)
    except Exception as e:  # noqa: BLE001  (malformed input of any shape)
        call_problems, call_unverifiable, call_head = [f"{LEDGER}: malformed ({type(e).__name__})"], [], None
    problems += call_problems
    unverifiable += call_unverifiable
    lines = [
        "sessions: " + ", ".join(f"{v} {k}" for k, v in counts.items()),
        "case files: " + ", ".join(f"{v} {k}" for k, v in case_counts.items()),
        f"decisions: {'verified' if ok else 'MISMATCH'} (head {head})",
        f"call files: {len(call_problems)} mismatch, {len(call_unverifiable)} unverifiable (ledger head {call_head})",
    ]
    counts_out = {**counts, **{f"case_{k}": v for k, v in case_counts.items()}}
    return StateCheck(counts_out, problems, lines, unverifiable)
