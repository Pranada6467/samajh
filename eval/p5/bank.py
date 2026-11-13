"""P5 inputs, read-only: customers, replies, gold, records, closed statements, the disposition draw,
and the fail-closed check of every digest in `data/p5/FROZEN.json`.

Nothing here writes under the data directory. `check_frozen()` raises `FrozenMismatch` on any digest that
does not match; a runner calls it before the first call and refuses to start otherwise.

Every loader takes the data directory (`data/p5` by default; `data/p5b` has the same layout), and a
`Customer` remembers the one it came from, so its record and closed statements are read from there.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P5 = ROOT / "data" / "p5"


def resolve_data(arg: str | Path | None) -> Path:
    """The data directory a `--data` option names (relative to the repo root when not absolute)."""
    if arg is None or str(arg) == "":
        return P5
    path = Path(arg)
    return (path if path.is_absolute() else ROOT / path).resolve()


def harness_hashes(directory: Path = HERE) -> dict[str, str]:
    """sha256 of every `*.py` of the harness, by file name: put in each run's manifest."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.py"))}


class FrozenMismatch(RuntimeError):
    """A P5 file does not match the digest frozen in `FROZEN.json`."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records_digest(directory: Path) -> str:
    """As `FROZEN.json` says: sha256 of the lines `<sha256>  <file name>` for `*.json`, sorted by name."""
    lines = "".join(
        f"{sha256(p)}  {p.name}\n" for p in sorted(directory.glob("*.json"), key=lambda p: p.name)
    )
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _resolve(p5: Path, root: Path, name: str) -> Path:
    """A key of `FROZEN.json` names a file in `data/p5/`, or a path from the repo root."""
    return p5 / name if (p5 / name).exists() or "/" not in name else root / name


def frozen_digests(p5: Path = P5, root: Path = ROOT) -> dict[str, dict[str, str]]:
    """The digests on disk now, for every key `FROZEN.json` pins (inputs, words, other)."""
    frozen = json.loads((p5 / "FROZEN.json").read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for section in ("inputs", "words", "other"):
        out[section] = {}
        for name in frozen[section]:
            path = p5 / "records" if name == "records" else _resolve(p5, root, name)
            if name == "records":
                out[section][name] = records_digest(path) if path.is_dir() else "missing"
            else:
                out[section][name] = sha256(path) if path.is_file() else "missing"
    return out


def check_frozen(p5: Path = P5, root: Path = ROOT) -> dict[str, dict[str, str]]:
    """Every pinned digest, checked. Returns them; raises `FrozenMismatch` naming each mismatch."""
    frozen = json.loads((p5 / "FROZEN.json").read_text(encoding="utf-8"))
    now = frozen_digests(p5, root)
    problems = [
        f"{section}/{name}: frozen {want[:8]}, on disk {now[section][name][:8]}"
        for section in ("inputs", "words", "other")
        for name, want in frozen[section].items()
        if now[section][name] != want
    ]
    if problems:
        raise FrozenMismatch("data/p5 does not match FROZEN.json: " + "; ".join(problems))
    return now


# --- the disposition draw ------------------------------------------------------


def draw(seed: str, customer_id: str, group: str) -> float:
    """`topics.json` disposition rule: u in [0, 1), one per customer and grouped matter."""
    return int(hashlib.sha256(f"{seed}|{customer_id}|{group}".encode()).hexdigest()[:8], 16) / 2**32


def gives_way(seed: str, customer_id: str, group: str | None, level: float) -> bool:
    """True when the customer does not answer for themselves on this matter at this level."""
    return group is not None and draw(seed, customer_id, group) < level


# --- the bank -------------------------------------------------------------------


@dataclass(frozen=True)
class Customer:
    id: str
    kind: str
    language: str
    record_id: str
    speaker: dict[str, Any]
    writer_model_by_arm: dict[str, str]
    open: dict[str, dict[str, str]]  # topic -> variant -> text
    closed: dict[str, dict[str, str]]  # statement id -> variant -> text
    gold: dict[str, Any]
    data_dir: Path = P5  # the data directory the customer was loaded from

    @property
    def procedural(self) -> bool:
        return self.gold["class"] == "procedural"


@dataclass(frozen=True)
class Topics:
    seed: str
    group: dict[str, str | None]  # open topic -> group (None: never gives way)
    defer_topics: frozenset[str]
    variants: dict[str, tuple[str, ...]]  # open topic -> variants written
    closed_group: dict[str, str]  # closed statement id -> group
    levels_text: tuple[float, ...]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@cache
def load_topics(p5: Path = P5) -> Topics:
    t = json.loads((p5 / "topics.json").read_text(encoding="utf-8"))
    return Topics(
        seed=t["disposition"]["seed"],
        group={x["id"]: x.get("group") for x in t["open_call"]},
        defer_topics=frozenset(t["open_defer"]["topics"]),
        variants={x["id"]: tuple(x["variants"]) for x in t["open_call"]},
        closed_group={s["id"]: s["group"] for s in t["closed_call"]["statements"]},
        levels_text=tuple(t["disposition"]["levels_text"]),
    )


@cache
def load_customers(p5: Path = P5) -> dict[str, Customer]:
    replies = {r["id"]: r for r in _jsonl(p5 / "replies.jsonl")}
    gold = {g["id"]: g for g in _jsonl(p5 / "gold.jsonl")}
    out = {}
    for c in _jsonl(p5 / "customers.jsonl"):
        r = replies[c["id"]]
        out[c["id"]] = Customer(
            id=c["id"],
            kind=c["kind"],
            language=c["language"],
            record_id=c["record_id"],
            speaker=c["speaker"],
            writer_model_by_arm=r["writer_model_by_arm"],
            open=r["open"],
            closed=r["closed"],
            gold=gold[c["id"]],
            data_dir=p5,
        )
    return out


@cache
def load_closed_statements(p5: Path = P5) -> dict[str, dict[str, Any]]:
    """customer id -> {intro, statements: [{id, group, text}]}, in the frozen order."""
    return {row["id"]: row for row in _jsonl(p5 / "closed_statements.jsonl")}


def load_record(record_id: str, p5: Path = P5):
    """A `samajh.server.records.CallRecord` (the record, its lender name and label)."""
    from samajh.server.records import CallRecord

    return CallRecord.model_validate_json((p5 / "records" / f"{record_id}.json").read_bytes())
