"""Score an ACQ run: per cell (r, a), per kind and per gold class, open against closed, unit = customer.

    uv run python eval/acq/acq_score.py RUN_DIR [--out tables.md] [--json scores.json]

Reads only RUN_DIR/calls/*.json and data/acq/gold.jsonl, customers.jsonl. Wilson 95% intervals, exact
McNemar on paired customers; no pooling across cells. Open calls with status entry_failed or no_result
are counted and left out of n (in every cell of their a). Never prints an open-minus-closed difference.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

from acq_common import DATA, read_jsonl  # noqa: E402

from samajh.evalkit.score import mcnemar_exact, wilson  # noqa: E402

KINDS = ("informed", "knowledge_gap", "misled", "misled_with_gaps")
CLASSES = ("problem", "knowledge_gap_only", "no_problem")
FAMILY = {"misled": "problem", "misled_with_gaps": "problem", "knowledge_gap": "knowledge_gap_only",
          "informed": "no_problem"}  # fmt: skip
EXCLUDED_NOTE = "n excludes open calls with status entry_failed or no_result (counted on the line above)"
EARLY_OUTCOMES = ("declined", "wrong_party", "not_confirmed", "no_go_ahead", "second_check_failed",
                  "human_requested", "turn_limit", "call_back_later", "language_switch", "no_response",
                  "do_not_call", "written_requested", "other")  # fmt: skip
OWN_VARIANTS = frozenset({"own", "again"})
EXCLUSION_LIMIT = 0.05
# Pre-declared primary tests (coordinator, fix round 1). Every other p-value is descriptive.
PRIMARY = {("P1", 0.0, r) for r in (0.5, 0.75, 1.0)} | {("P2a", 0.0, r) for r in (0.0, 0.25, 0.5, 0.75, 1.0)}


# --- per-customer facts ----------------------------------------------------------------------------


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


def provenance(quote: str | None, call: dict[str, Any]) -> str:
    """Where a flag's quote was said: "own_or_again" if some scored customer reply played as own/again
    holds it, else the variant of the first reply that holds it ("defer", "canned", "fixed"), else "unknown"."""
    q = _norm(quote)
    if not q:
        return "unknown"
    found = [t.get("variant") or t["reply"].get("variant") for t in call.get("turns", [])
             if q in _norm(t["reply"].get("text"))]  # fmt: skip
    if any(v in OWN_VARIANTS for v in found):
        return "own_or_again"
    return found[0] if found else "unknown"


def _counts(f: dict[str, Any], call: dict[str, Any], gold: dict[str, Any]) -> bool:
    """A flag counts toward refer_ground / gap_found: its quote is from an own or again reply and, on a
    gold false field, its reason does not end in `_dont_know`."""
    if provenance(f.get("quote"), call) != "own_or_again":
        return False
    return not (f.get("field") in set(gold["false_fields"]) and str(f["reason"]).endswith("_dont_know"))


def open_facts(call: dict[str, Any], gold: dict[str, Any]) -> dict[str, bool]:
    tier = call.get("tier")
    outcome = call.get("outcome")
    ended_early = outcome != "completed"
    refer = tier == "refer"
    flags = call.get("flags", [])
    gaps = call.get("gaps", [])
    ground, dk, false = set(gold["ground"]), set(gold["dk_fields"]), set(gold["false_fields"])
    rest = None if refer else ("ended_early" if ended_early else tier)
    ref_g = [f for f in flags if f["tier"] == "refer" and f.get("field") in ground]
    ug_dk = [f for f in flags if f["tier"] == "understanding_gap" and f.get("field") in dk]
    early = (outcome if outcome in EARLY_OUTCOMES else "other") if rest == "ended_early" else None
    facts = {
        "refer": refer,
        "refer_ground": any(_counts(f, call, gold) for f in ref_g),
        "refer_ground_any_source": bool(ref_g),
        "refer_basis_customer_statement": refer and call.get("referral_basis") == "customer_statement",
        "refer_basis_record_only": refer and call.get("referral_basis") == "record_only",
        "incomplete": rest == "incomplete",
        "understanding_gap": rest == "understanding_gap",
        "clear": rest == "clear",
        "ended_early": rest == "ended_early",
        "miss": not refer,
        "silent_miss": rest in ("clear", "understanding_gap"),
        "gap_found": tier == "understanding_gap" and any(_counts(f, call, gold) for f in ug_dk),
        "gap_found_any_source": tier == "understanding_gap" and bool(ug_dk),
        "gap_flag_any_tier": any(_counts(f, call, gold) for f in ug_dk),
        "not_clear": tier != "clear" or ended_early,
        "incomplete_on_ground": any(x["tier"] == "incomplete" and x.get("field") in false for x in flags + gaps),
        "any_degraded": bool(call.get("degraded_turn_count") or call.get("degraded_turns")),
    }
    for o in EARLY_OUTCOMES:
        facts[f"ended_early.{o}"] = early == o
    return facts


def closed_facts(call: dict[str, Any], gold: dict[str, Any]) -> dict[str, bool]:
    ground, dk = set(gold["ground"]), set(gold["dk_fields"])
    answers = {x["field"]: x["answer"] for x in call["answers"]}
    strict, lenient = set(call["caught_fields_strict"]), set(call["caught_fields_lenient"])
    return {
        "strict_caught": call["outcome_strict"] == "caught",
        "strict_caught_ground": bool(strict & ground),
        "strict_confirmed": call["outcome_strict"] == "confirmed",
        "strict_gap_found": any(answers.get(f) == "dont_know" for f in dk),
        "lenient_caught": call["outcome_lenient"] == "caught",
        "lenient_caught_ground": bool(lenient & ground),
        "lenient_confirmed": call["outcome_lenient"] == "confirmed",
        "lenient_gap_found": False,  # lenient never catches a dk: printed anyway
    }


_EARLY = [("open", f"ended_early.{o}") for o in EARLY_OUTCOMES]
_TAIL = [("open", "any_degraded")]
METRICS: dict[str, list[tuple[str, str]]] = {
    "problem": [
        ("open", "refer"), ("open", "refer_ground"), ("open", "refer_ground_any_source"),
        ("open", "refer_basis_customer_statement"), ("open", "refer_basis_record_only"),
        ("open", "incomplete"), ("open", "incomplete_on_ground"), ("open", "understanding_gap"),
        ("open", "clear"), ("open", "ended_early"), *_EARLY, ("open", "miss"), ("open", "silent_miss"),
        ("closed", "strict_caught"), ("closed", "strict_caught_ground"), ("closed", "strict_confirmed"),
        ("closed", "lenient_caught"), ("closed", "lenient_caught_ground"), ("closed", "lenient_confirmed"), *_TAIL,
    ],
    "knowledge_gap_only": [
        ("open", "gap_found"), ("open", "gap_flag_any_tier"), ("open", "gap_found_any_source"),
        ("open", "refer"), ("open", "refer_basis_customer_statement"), ("open", "refer_basis_record_only"),
        ("open", "incomplete"), ("open", "understanding_gap"), ("open", "clear"), ("open", "ended_early"), *_EARLY,
        ("closed", "strict_gap_found"), ("closed", "strict_confirmed"),
        ("closed", "lenient_gap_found"), ("closed", "lenient_confirmed"), *_TAIL,
    ],
    "no_problem": [
        ("open", "refer"), ("open", "refer_basis_customer_statement"), ("open", "refer_basis_record_only"),
        ("open", "incomplete"), ("open", "understanding_gap"), ("open", "clear"), ("open", "ended_early"), *_EARLY,
        ("open", "not_clear"), ("closed", "strict_caught"), ("closed", "lenient_caught"), *_TAIL,
    ],
}  # fmt: skip
PAIRS: dict[str, list[tuple[str, str, str]]] = {
    "problem": [("P2a", "refer_ground", "strict_caught_ground"), ("P2b", "refer", "strict_caught"),
                ("P3", "not_clear", "strict_caught")],
    "knowledge_gap_only": [("P1", "gap_found", "strict_gap_found"), ("P3", "not_clear", "strict_caught")],
    "no_problem": [],  # informed: open not_clear is printed as a cost line, no test
}  # fmt: skip


def load(run_dir: Path, data: Path = DATA):
    gold = {g["id"]: g for g in read_jsonl(data / "gold.jsonl")}
    customers = {c["id"]: c for c in read_jsonl(data / "customers.jsonl")}
    opens: dict[tuple[str, float], dict] = {}
    closeds: dict[tuple[str, float, float], dict] = {}
    for path in sorted((run_dir / "calls").glob("*.json")):
        call = json.loads(path.read_text(encoding="utf-8"))
        if call["arm"] == "open":
            opens[(call["customer_id"], float(call["a"]))] = call
        else:
            closeds[(call["customer_id"], float(call["r"]), float(call["a"]))] = call
    return gold, customers, opens, closeds


def _rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "per100": round(100 * k / n, 1) if n else None,
            "ci95_per100": [round(100 * lo, 1), round(100 * hi, 1)]}  # fmt: skip


def score_group(ids, family, gold, opens, closeds, r, a) -> dict[str, Any]:
    excluded = {"entry_failed": 0, "no_result": 0, "missing_open": 0, "missing_closed": 0}
    rows = []
    degraded_turns = 0
    for cid in ids:
        o, c = opens.get((cid, a)), closeds.get((cid, r, a))
        if o is None:
            excluded["missing_open"] += 1
            continue
        if o["status"] != "ok":
            excluded[o["status"] if o["status"] in excluded else "no_result"] += 1
            continue
        if c is None:
            excluded["missing_closed"] += 1
            continue
        degraded_turns += int(o.get("degraded_turn_count") or o.get("degraded_turns") or 0)
        rows.append((open_facts(o, gold[cid]), closed_facts(c, gold[cid])))
    n = len(rows)
    metrics = {f"{arm}.{m}": _rate(sum(r_[0 if arm == "open" else 1][m] for r_ in rows), n)
               for arm, m in METRICS[family]}  # fmt: skip
    pairs = {}
    for name, om, cm in PAIRS[family]:
        b = sum(o[om] and not c[cm] for o, c in rows)
        cc = sum(c[cm] and not o[om] for o, c in rows)
        both = sum(o[om] and c[cm] for o, c in rows)
        pairs[f"{name}:{om}~{cm}"] = {"b_open_only": b, "c_closed_only": cc, "both": both,
                                     "neither": n - b - cc - both, "p": mcnemar_exact(b, cc),
                                     "primary": (name, a, r) in PRIMARY}  # fmt: skip
    return {"family": family, "n": n, "excluded": excluded, "degraded_turns": degraded_turns,
            "metrics": metrics, "mcnemar": pairs}  # fmt: skip


def groups(customers, gold) -> dict[str, tuple[str, list[str]]]:
    out: dict[str, tuple[str, list[str]]] = {}
    for kind in KINDS:
        ids = sorted(c for c, row in customers.items() if row["kind"] == kind)
        classes = {gold[c]["class"] for c in ids}
        if classes - {FAMILY[kind]}:
            raise ValueError(f"kind {kind} holds gold classes {classes}")
        out[f"kind={kind}"] = (FAMILY[kind], ids)
    for cls in CLASSES:
        out[f"class={cls}"] = (cls, sorted(c for c in gold if gold[c]["class"] == cls))
    return out


def breakdown(customers, gold, opens, closeds, a: float) -> dict[str, Any]:
    """Counts only, by writer model and by language, for one a: open tiers, closed strict caught at r=0 and 1."""
    out: dict[str, Any] = {}
    for axis in ("writer_model", "language"):
        table: dict[str, Any] = defaultdict(lambda: defaultdict(int))
        for cid, row in customers.items():
            o = opens.get((cid, a))
            if o is None:
                continue
            key = f"{row[axis]} | {gold[cid]['class']}"
            t = table[key]
            if o["status"] != "ok":
                t[o["status"]] += 1
                continue
            f = open_facts(o, gold[cid])
            t["n"] += 1
            for m in ("refer", "incomplete", "understanding_gap", "clear", "ended_early"):
                t[f"open.{m}"] += f[m]
            for r in (0.0, 1.0):
                c = closeds.get((cid, r, a))
                if c is not None:
                    t[f"closed_r{r:g}.strict_caught"] += c["outcome_strict"] == "caught"
        out[axis] = {k: dict(v) for k, v in sorted(table.items())}
    return out


def completeness(run_dir: Path, opens) -> dict[str, Any]:
    """From the run's manifest plan: is every planned open call on disk, and the exclusions per a cell."""
    manifest_path = run_dir / "manifest.json"
    plan = []
    if manifest_path.exists():
        for m in json.loads(manifest_path.read_text(encoding="utf-8")):
            plan += [(cid, float(a)) for cid, a in m.get("plan", [])]
    plan = sorted(set(plan))
    missing = [p for p in plan if p not in opens]
    per_a: dict[str, Any] = {}
    for a in sorted({a for _, a in plan} | {a for _, a in opens}):
        planned = sum(1 for _, x in plan if x == a) or sum(1 for _, x in opens if x == a)
        bad = sum(1 for (_, x), o in opens.items() if x == a and o["status"] != "ok")
        per_a[f"a={a:g}"] = {"planned": planned, "excluded": bad,
                             "over_limit": planned > 0 and bad / planned > EXCLUSION_LIMIT}  # fmt: skip
    return {"planned": len(plan), "missing": len(missing), "complete": bool(plan) and not missing,
            "per_a": per_a, "exclusion_limit": EXCLUSION_LIMIT}  # fmt: skip


def score(run_dir: Path, data: Path = DATA) -> dict[str, Any]:
    gold, customers, opens, closeds = load(run_dir, data)
    a_levels = sorted({a for _, a in opens})
    r_levels = sorted({r for _, r, _ in closeds})
    grp = groups(customers, gold)
    cells = {}
    for a in a_levels:
        for r in r_levels:
            cells[f"r={r:g},a={a:g}"] = {name: score_group(ids, fam, gold, opens, closeds, r, a)
                                         for name, (fam, ids) in grp.items()}  # fmt: skip
    return {"a_levels": a_levels, "r_levels": r_levels, "cells": cells, "note": EXCLUDED_NOTE,
            "completeness": completeness(run_dir, opens),
            "breakdown": {f"a={a:g}": breakdown(customers, gold, opens, closeds, a)
                          for a in (0.0, 1.0) if a in a_levels}}  # fmt: skip


def _fmt(m: dict[str, Any]) -> str:
    if not m["n"]:
        return f"{m['k']}/0"
    lo, hi = m["ci95_per100"]
    return f"{m['k']}/{m['n']} = {m['per100']} per 100 [{lo}, {hi}]"


def markdown(s: dict[str, Any], *, incomplete_banner: bool = False) -> str:
    out = ["# ACQ scores", ""]
    if incomplete_banner:
        out += ["> **INCOMPLETE RUN** (--allow-incomplete): "
                f"{s['completeness']['missing']} of {s['completeness']['planned']} planned open calls have no file. "
                "Not a result.", ""]  # fmt: skip
    for a, c in s["completeness"]["per_a"].items():
        if c["over_limit"]:
            out += [f"> **{a}: cell over the exclusion limit** ({c['excluded']} of {c['planned']} open calls "
                    f"entry_failed or no_result, limit {100 * EXCLUSION_LIMIT:g}%).", ""]  # fmt: skip
    out += ["Unit: customer. Per 100 with Wilson 95% intervals; exact McNemar on paired customers.",
            "No pooling across cells; each arm is given as its own count. A flag counts toward refer_ground and",
            "gap_found only when its quote is from an own or again reply (and, on a false field, its reason is not",
            "a `_dont_know`); the `_any_source` lines count every flag. Calls with a degraded turn are kept.", "",
            "Primary tests (pre-declared): P1 at a=0, r in {0.5, 0.75, 1}; P2a at a=0, every r.", ""]  # fmt: skip
    primary, descriptive = [], []
    for cell, grps in s["cells"].items():
        out += [f"## Cell {cell}", ""]
        for name, g in grps.items():
            ex = ", ".join(f"{k} {v}" for k, v in g["excluded"].items())
            out += [f"### {name} (family {g['family']})", "",
                    f"Excluded: {ex}. {EXCLUDED_NOTE}. Degraded turns in counted calls: {g['degraded_turns']}.", "",
                    "| measure | count |", "|---|---|"]  # fmt: skip
            out += [f"| {k} | {_fmt(m)} |" for k, m in g["metrics"].items()
                    if not (k.startswith("open.ended_early.") and m["k"] == 0 and not k.endswith(".declined"))]
            out.append("")
            for k, p in g["mcnemar"].items():
                row = (f"| {cell} | {name} | {k} | {p['b_open_only']} | {p['c_closed_only']} | {p['both']} | "
                       f"{p['neither']} | {p['p']:.3g} |")  # fmt: skip
                (primary if p["primary"] else descriptive).append(row)
    head = ["| cell | group | pair | b open only | c closed only | both | neither | p |",
            "|---|---|---|---|---|---|---|---|"]
    out += ["## McNemar: primary", "", *head, *primary, "",
            "## McNemar: descriptive, not a test", "", *head, *descriptive, ""]
    for a, axes in s["breakdown"].items():
        out += [f"## Counts by writer model and language, {a} (no tests)", ""]
        for axis, table in axes.items():
            out += [f"### {axis}", ""]
            out += [f"- {k}: " + ", ".join(f"{m} {v}" for m, v in sorted(row.items())) for k, row in table.items()]
            out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args(argv)
    s = score(args.run_dir)
    if not s["completeness"]["complete"] and not args.allow_incomplete:
        c = s["completeness"]
        print(f"REFUSED: incomplete run ({c['missing']} of {c['planned']} planned open calls missing, or no plan "
              "in manifest.json); pass --allow-incomplete for a bannered table", file=sys.stderr)  # fmt: skip
        return 1
    md = markdown(s, incomplete_banner=not s["completeness"]["complete"])
    if args.out:
        args.out.write_text(md, encoding="utf-8")
    else:
        print(md)
    if args.json:
        args.json.write_text(json.dumps(s, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
