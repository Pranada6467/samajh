"""The hash chain of one phone session (format: `samajh.evidence`, "Session chain").

`append_chain` is called by `SessionStore.save` under the session's file lock; `verify_session_dir`
re-reads a session directory and names the first thing that does not match.

A session first written before the chain existed and saved again by this code is *adopted*: its
entry 0 carries `"adopted": true`, and nothing it did before that save is covered by the chain.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from samajh.evidence.digest import GENESIS, after_epoch, digest, file_sha256, sha256_hex, tagged

CHAIN_FILE = "chain.jsonl"
SEAL_TAG = "samajh-session-seal-v1"
_EXCLUDED = ("events", "dialogue_state", "dialogue_undo", "chain")


def _str_sha(value: str | None) -> str | None:
    return None if value is None else sha256_hex(value.encode("utf-8"))


def session_fields_json(data: dict[str, Any]) -> dict[str, Any]:
    """`session_fields` of a session.json already parsed to plain JSON."""
    fields = {k: v for k, v in data.items() if k not in _EXCLUDED}
    fields["dialogue_state_sha256"] = _str_sha(data.get("dialogue_state"))
    fields["dialogue_undo_sha256"] = _str_sha(data.get("dialogue_undo"))
    return fields


def session_fields(log: Any) -> dict[str, Any]:
    """Every SessionLog field except events, dialogue_state, dialogue_undo and chain, plus the
    sha256 of the two dialogue strings (never the strings)."""
    return session_fields_json(log.model_dump(mode="json"))


def event_digest(event: Any) -> str:
    return digest(event.model_dump(mode="json"))


def session_seal(head: str, recording_sha256: str) -> str:
    return tagged(SEAL_TAG, head, recording_sha256)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _entry_hash(entry: dict[str, Any]) -> str:
    return digest({k: v for k, v in entry.items() if k != "hash"})


def _mend_tail(path: Path) -> None:
    """A last line with no newline: ended with one when it is a whole entry, else (a torn append)
    moved to `chain.jsonl.torn` and cut, as `samajh.ops.store` does."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return
    end = data.rfind(b"\n") + 1
    tail = data[end:]
    if not tail:
        return
    try:
        entry = json.loads(tail)
        whole = isinstance(entry, dict) and entry.get("hash") == _entry_hash(entry)
    except ValueError:
        whole = False
    if whole:
        _append_bytes(path, b"\n")
        return
    _append_bytes(path.with_name(CHAIN_FILE + ".torn"), tail + b"\n")
    os.truncate(path, end)


def _append_bytes(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        written = os.write(fd, data)
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
    finally:
        os.close(fd)


def chain_entries(path: Path) -> list[dict[str, Any]]:
    """The entries of a session directory's chain (or of a chain.jsonl path), whole lines only."""
    file = path / CHAIN_FILE if path.is_dir() else path
    try:
        data = file.read_bytes()
    except FileNotFoundError:
        return []
    end = data.rfind(b"\n") + 1
    return [json.loads(line) for line in data[:end].decode("utf-8").splitlines() if line]


def entry_index(path: Path, head: str) -> int | None:
    """The index of the entry whose hash is `head`, or None."""
    for entry in chain_entries(path):
        if entry.get("hash") == head:
            return entry["i"]
    return None


def describe_entry(entry: dict[str, Any]) -> str:
    where = "session fields" if entry.get("kind") == "session" else f"event seq {entry.get('seq')}"
    return f"entry {entry.get('i')}: {where}"


def append_chain(
    session_dir: Path,
    fields: dict[str, Any],
    events: list[tuple[int, str, str | None]],
    *,
    adopted: bool,
) -> tuple[int, str]:
    """Append what changed; returns (entries, head). Caller holds the session's lock.

    `fields` is `session_fields`; `events` is (seq, event digest, audio sha256) for every event."""
    path = session_dir / CHAIN_FILE
    _mend_tail(path)
    entries = chain_entries(path)
    last_session: str | None = None
    last_event: dict[int, tuple[str, str | None]] = {}
    for e in entries:
        if e["kind"] == "session":
            last_session = e["sha256"]
        else:
            last_event[e["seq"]] = (e["sha256"], e.get("audio_sha256"))
    prev = entries[-1]["hash"] if entries else GENESIS
    i = len(entries)
    new: list[dict[str, Any]] = []

    def add(kind: str, seq: int | None, sha: str, audio: str | None) -> None:
        nonlocal prev, i
        entry: dict[str, Any] = {
            "i": i,
            "prev": prev,
            "at": _now(),
            "kind": kind,
            "seq": seq,
            "sha256": sha,
            "audio_sha256": audio,
        }
        if i == 0 and adopted:
            entry["adopted"] = True
        entry["hash"] = _entry_hash(entry)
        new.append(entry)
        prev, i = entry["hash"], i + 1

    fields_sha = digest(fields)
    if fields_sha != last_session:
        add("session", None, fields_sha, None)
    for seq, sha, audio in sorted(events):
        if last_event.get(seq) != (sha, audio):
            add("event", seq, sha, audio)
    if new:
        _append_bytes(path, b"".join(json.dumps(e, ensure_ascii=False).encode() + b"\n" for e in new))
    return i, prev


@dataclass(frozen=True)
class SessionCheck:
    status: Literal["verified", "mismatch", "unverifiable"]
    problem: str | None
    entries: int
    head: str | None
    seal: str | None
    adopted: bool


def _audio_sha(session_dir: Path, ref: str | None) -> str | None:
    if ref is None:
        return None
    path = session_dir / ref
    return file_sha256(path) if path.is_file() else None


def verify_session_dir(path: Path) -> SessionCheck:
    """Check a session directory's chain against its session.json and audio (order: module doc)."""
    try:
        data = json.loads((path / "session.json").read_bytes())
    except (OSError, ValueError):
        return SessionCheck("mismatch", "session.json is missing or does not parse", 0, None, None, False)
    chain = data.get("chain")
    file = path / CHAIN_FILE
    if chain is None and not file.exists():
        if after_epoch(path.name):
            return SessionCheck(
                "mismatch", "dated after the evidence epoch but has no chain", 0, None, None, False
            )
        return SessionCheck("unverifiable", "written before the evidence chain", 0, None, None, False)

    entries: list[dict[str, Any]] = []
    adopted = False

    def bad(problem: str) -> SessionCheck:
        head = entries[-1].get("hash") if entries else None
        return SessionCheck("mismatch", problem, len(entries), head, (chain or {}).get("seal"), adopted)

    if not file.exists():
        return bad("chain.jsonl is missing but session.json has a chain")
    raw = file.read_bytes()
    if raw and not raw.endswith(b"\n"):
        return bad("chain.jsonl ends in a torn line")
    for n, line in enumerate(raw.decode("utf-8", errors="replace").splitlines()):
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError
        except ValueError:
            return bad(f"chain line {n} does not parse")
        entries.append(entry)
    adopted = bool(entries and entries[0].get("adopted"))
    prev = GENESIS
    for n, e in enumerate(entries):
        if e.get("i") != n:
            return bad(f"chain line {n}: has i={e.get('i')}, expected {n}")
        if e.get("prev") != prev:
            what = "GENESIS" if n == 0 else f"entry {n - 1}'s hash"
            return bad(f"chain {describe_entry(e)}: prev does not match {what}")
        if e.get("hash") != _entry_hash(e):
            return bad(f"chain {describe_entry(e)}: hash does not recompute")
        prev = e["hash"]
    head = entries[-1]["hash"] if entries else None
    if chain is None:
        return bad("session.json has no chain but chain.jsonl exists")
    if chain.get("entries") != len(entries) or chain.get("head") != head:
        return bad(f"session.json chain (entries {chain.get('entries')}, head) does not match chain.jsonl")

    last_session: dict[str, Any] | None = None
    last_event: dict[int, dict[str, Any]] = {}
    for e in entries:
        if e.get("kind") == "session":
            last_session = e
        else:
            last_event[e.get("seq")] = e
    if last_session is None or last_session["sha256"] != digest(session_fields_json(data)):
        where = describe_entry(last_session) if last_session else "no session entry"
        return bad(f"session fields in session.json do not match chain {where}")
    events = data.get("events") or []
    for pos, ev in enumerate(events):
        if ev.get("seq") != pos:
            return bad(f"session.json event at position {pos} has seq {ev.get('seq')}")
    seqs = set(range(len(events)))
    if set(last_event) != seqs:
        missing = sorted(seqs ^ set(last_event))
        return bad(f"events in session.json and the chain differ at seq {missing[0]}")
    for ev in events:
        e = last_event[ev["seq"]]
        if e["sha256"] != digest(ev):
            return bad(f"event seq {ev['seq']} in session.json does not match chain {describe_entry(e)}")
    for ev in events:
        e = last_event[ev["seq"]]
        if _audio_sha(path, ev.get("audio")) != e.get("audio_sha256"):
            return bad(f"audio of event seq {ev['seq']} does not match chain {describe_entry(e)}")
    recording = data.get("recording")
    seal = chain.get("seal")
    if recording is not None:
        wav = path / "call.wav"
        if not wav.is_file() or file_sha256(wav) != recording.get("sha256"):
            return bad("call.wav does not match recording.sha256")
        if seal != session_seal(head, recording["sha256"]):
            return bad("chain seal does not recompute from the head and the recording")
    elif seal is not None:
        return bad("chain has a seal but session.json has no recording")
    return SessionCheck("verified", None, len(entries), head, seal, adopted)
