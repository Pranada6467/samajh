"""Reference-transcript templates and word/character error rates against them."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from samajh.amounts import Parsed, parse_amount
from samajh.human.sessions import Session, load_sessions
from samajh.human.stats import per100
from samajh.rules.normalise import _norm

REF_FIELDS = ["session", "turn", "audio", "asked_key", "v3_0", "v2_5", "reference"]
READINGS = [("prisma-v3.0", "text"), ("prisma-v2.5", "text"), ("prisma-v2.5", "literal")]


def edits(ref: Sequence[str], hyp: Sequence[str]) -> int:
    """Levenshtein distance (substitution, insertion, deletion all cost 1)."""
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1]


def word_counts(ref: str, hyp: str) -> tuple[int, int]:
    r, h = _norm(ref).split(), _norm(hyp).split()
    return edits(r, h), len(r)


def char_counts(ref: str, hyp: str) -> tuple[int, int]:
    r, h = _norm(ref).replace(" ", ""), _norm(hyp).replace(" ", "")
    return edits(r, h), len(r)


def rupees(text: str | None) -> int | None:
    result = parse_amount(text or "")
    return result.rupees if isinstance(result, Parsed) else None


def _reading(c: dict, model: str, field: str) -> str | None:
    for r in c.get("readings") or []:
        if r.get("model") == model and r.get("ok", True):
            return r.get(field)
    return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def refs(sessions: list[Session], out: Path) -> int:
    kept = {(r.get("session"), r.get("turn")): r.get("reference", "") for r in _read_csv(out)}
    rows = []
    for s in sessions:
        for c in s.customers():
            if not c.get("audio") or s.is_year_answer(c):
                continue
            lines = (s.asked(c) or {}).get("lines") or []
            key = (s.id, str(c.get("seq")))
            rows.append(
                {
                    "session": s.id,
                    "turn": c.get("seq"),
                    "audio": str((s.dir / c["audio"]).resolve()),
                    "asked_key": (lines[-1].get("key") or "") if lines else "",
                    "v3_0": _reading(c, "prisma-v3.0", "text") or "",
                    "v2_5": _reading(c, "prisma-v2.5", "text") or "",
                    "reference": kept.get(key, ""),
                }
            )
    write_csv(out, REF_FIELDS, rows)
    return len(rows)


def _hypotheses(rows: list[dict[str, str]], csv_path: Path, roots: list[Path], state: Path) -> list[dict]:
    """(row id, reading label, reference, hypothesis) for every filled row."""
    out: list[dict] = []
    filled = [r for r in rows if (r.get("reference") or "").strip()]
    if filled and "note" in filled[0]:
        readings: dict[tuple, dict] = {}
        path = csv_path.parent / "readings.jsonl"
        for line in path.read_text().splitlines() if path.is_file() else []:
            d = json.loads(line)
            readings[(d.get("note"), d.get("condition"), d.get("model"))] = d
        for r in filled:
            for cond in ("16k", "8k"):
                for model, field in READINGS:
                    d = readings.get((r["note"], cond, model))
                    hyp = d.get(field) if d and d.get("ok") else None
                    out.append(
                        {
                            "row": r["note"],
                            "reading": f"{model} {field} {cond}",
                            "ref": r["reference"],
                            "hyp": hyp,
                        }
                    )
        return out
    by_id = {s.id: s for s in load_sessions(roots, state)} if roots else {}
    for r in filled:
        s = by_id.get(r["session"])
        if s is None:
            found = load_sessions(
                [
                    p
                    for p in [state / "sessions" / r["session"], *state.glob(f"*/sessions/{r['session']}")]
                    if p.exists()
                ],
                state,
            )
            s = found[0] if found else None
        c = s.event(int(r["turn"])) if s else None
        for model, field in READINGS:
            out.append(
                {
                    "row": f"{r['session']}#{r['turn']}",
                    "reading": f"{model} {field}",
                    "ref": r["reference"],
                    "hyp": _reading(c, model, field) if c else None,
                }
            )
    return out


def wer_report(csv_path: Path, roots: list[Path], state: Path) -> str:
    items = _hypotheses(_read_csv(csv_path), csv_path, roots, state)
    agg: dict[str, list[int]] = defaultdict(
        lambda: [0, 0, 0, 0, 0, 0, 0]
    )  # we, wn, ce, cn, rows, amt_ok, amt_n
    table = ["| row | reading | WER | CER | amount ok |", "|---|---|---|---|---|"]
    for it in items:
        a = agg[it["reading"]]
        if it["hyp"] is None:
            table.append(f"| {it['row']} | {it['reading']} | missing | missing | |")
            continue
        we, wn = word_counts(it["ref"], it["hyp"])
        ce, cn = char_counts(it["ref"], it["hyp"])
        a[0] += we
        a[1] += wn
        a[2] += ce
        a[3] += cn
        a[4] += 1
        ref_amount, amount_cell = rupees(it["ref"]), ""
        if ref_amount is not None:
            ok = rupees(it["hyp"]) == ref_amount
            a[5] += ok
            a[6] += 1
            amount_cell = "yes" if ok else "no"
        table.append(
            f"| {it['row']} | {it['reading']} | {we / max(wn, 1):.3f} | {ce / max(cn, 1):.3f} "
            f"| {amount_cell} |"
        )
    lines = [
        "# WER and CER against typed references",
        "",
        (
            f"References: {csv_path}. Reference and hypothesis are normalised with samajh.rules.normalise._norm "
            "(NFC, casefold, punctuation and symbols removed). CER counts characters with spaces removed. "
            "Rates are total edits / total reference tokens."
        ),
        (
            "`transcribe` writes numbers as digits, so WER against a words reference penalises formatting; "
            "the v2.5 literal is the fairer word-level reading."
        ),
        "",
        "| reading | rows | WER | CER | exact amount (one amount in reference) |",
        "|---|---|---|---|---|",
    ]
    for name, a in agg.items():
        wer = f"{a[0] / a[1]:.3f} ({a[0]}/{a[1]})" if a[1] else "n/a"
        cer = f"{a[2] / a[3]:.3f} ({a[2]}/{a[3]})" if a[3] else "n/a"
        lines.append(f"| {name} | {a[4]} | {wer} | {cer} | {per100(a[5], a[6])} |")
    return "\n".join(lines + ["", "## Per row", "", *table, ""])
