"""P5 scorer: the contract section 4 tables from a run's call files and the gold rows only.

    uv run python eval/p5/score.py eval/p5/runs/NAME        # writes NAME/score.md and NAME/score.json

Counts per 100 with n and a Wilson 95% interval on customers, always by kind of customer, arm and level;
never one pooled rate. What each call counts as:
- open call: `refer` when its tier is refer (however the call ended); else `ended_early` when the dialogue
  did not end `completed`; else its tier (`incomplete`, `understanding_gap`, `clear`);
- closed call: `refer` on `closed_not_confirmed`, `confirmed` on `closed_confirmed`, else `ended_early`
  (it ended in the shared opening);
- `no_result` when the call raised; shown in its row and listed, never dropped.
A miss on a `problem` customer: open `clear` or `understanding_gap`, closed `confirmed`; `incomplete` and
`ended_early` are shown apart as neither. The per-100 denominator is every customer with a result.
Arms are compared (exact McNemar, paired by customer) at level 0 only; above level 0 each arm stands on
its own and no open-minus-closed difference is computed (contract section 8).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from samajh.evalkit.score import mcnemar_exact, wilson

NON_PROBLEM = ("no_problem", "knowledge_gap_only")
MISS = frozenset({"clear", "understanding_gap", "confirmed"})
MATTER_STEPS = frozenset({"context", "open_recall", "teach_back", "consent_check", "read_back"})
LOAN_KEYS = frozenset({"context.loan", "verify.after_loan"})
REFUSAL_INTENTS = frozenset({"decline", "maybe_decline", "no", "do_not_call"})


def arm_label(call: dict[str, Any]) -> str:
    if call["arm"] == "closed":
        return "closed"
    return "open-terse" if call.get("condition") == "terse" else "open"


def state(call: dict[str, Any]) -> str:
    """What one call counts as (module docstring)."""
    if call.get("status") != "ok":
        return "no_result"
    if call["arm"] == "closed":
        return {"closed_not_confirmed": "refer", "closed_confirmed": "confirmed"}.get(
            call.get("outcome"), "ended_early"
        )
    if call.get("tier") == "refer":
        return "refer"
    if call.get("outcome") != "completed":
        return "ended_early"
    return call["tier"]


def per100(count: int, n: int) -> str:
    if n == 0:
        return "n/a"
    low, high = wilson(count, n)
    return f"{100 * count / n:.0f} [{100 * low:.0f}-{100 * high:.0f}]"


def _rate(count: int, n: int) -> dict[str, Any]:
    low, high = wilson(count, n)
    return {
        "per100": round(100 * count / n, 1) if n else None,
        "ci95": [round(100 * low, 1), round(100 * high, 1)],
    }


def _key(call: dict[str, Any]) -> tuple[str, float]:
    return arm_label(call), call["level"]


def misses(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Table 1: misses per 100 customers with a problem, by arm, level and kind."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        g = gold[c["customer_id"]]
        if g["class"] == "problem":
            cells[(*_key(c), g["kind"])][state(c)] += 1
    rows = []
    for (arm, level, kind), k in sorted(cells.items()):
        miss = sum(k[s] for s in MISS)
        n = sum(k.values()) - k["no_result"]
        rows.append({"arm": arm, "level": level, "kind": kind, "n": n, "caught": k["refer"], "miss": miss,
                     "incomplete": k["incomplete"], "ended_early": k["ended_early"], "no_result": k["no_result"],
                     "miss_tiers": {s: k[s] for s in sorted(MISS) if k[s]}, **_rate(miss, n)})  # fmt: skip
    return rows


def referrals(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Table 2: referrals per 100 customers without a problem, by arm, level, gold class and kind."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        g = gold[c["customer_id"]]
        if g["class"] in NON_PROBLEM:
            cells[(*_key(c), g["class"], g["kind"])][state(c)] += 1
    rows = []
    for (arm, level, cls, kind), k in sorted(cells.items()):
        n = sum(k.values()) - k["no_result"]
        rows.append({"arm": arm, "level": level, "gold_class": cls, "kind": kind, "n": n, "referred": k["refer"],
                     "clear": k["clear"], "understanding_gap": k["understanding_gap"], "incomplete": k["incomplete"],
                     "confirmed": k["confirmed"], "ended_early": k["ended_early"], "no_result": k["no_result"],
                     **_rate(k["refer"], n)})  # fmt: skip
    return rows


def basis_split(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Table 3: what open referrals rest on, by arm, level and gold class."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        if c["arm"] != "closed" and state(c) == "refer":
            cells[(*_key(c), gold[c["customer_id"]]["class"])][c.get("referral_basis") or "none"] += 1
    return [{"arm": a, "level": lv, "gold_class": cls, "customer_statement": k["customer_statement"],
             "record_only": k["record_only"], "none": k["none"]}
            for (a, lv, cls), k in sorted(cells.items())]  # fmt: skip


def _bot_lines(call: dict[str, Any]) -> list[dict[str, Any]]:
    lines = [ln for t in call.get("turns", []) for ln in t["bot"]]
    return lines + list(call.get("final_bot", []))


def loan_named(call: dict[str, Any]) -> bool:
    """Any bot line that names the loan (`context.loan`, `verify.after_loan`) or belongs to a later step."""
    return any(ln["key"] in LOAN_KEYS or ln.get("step") in MATTER_STEPS for ln in _bot_lines(call))


def after_refusal(call: dict[str, Any]) -> dict[str, Any]:
    """Whether the bot asked anything after the first turn it read as a refusal (decline, maybe_decline,
    no, do_not_call), and whether any of it was a question about the loan."""
    turns = call.get("turns", [])
    first = next((i for i, t in enumerate(turns)
                  if any(r.get("intent") in REFUSAL_INTENTS for r in t.get("readings", []))), None)  # fmt: skip
    if first is None:
        return {"refusal_read": False, "further_question": None, "matter_question": None}
    later = turns[first + 1 :]
    return {
        "refusal_read": True,
        "further_question": bool(later),
        "matter_question": any(ln.get("step") in MATTER_STEPS for t in later for ln in t["bot"]),
    }


def opening_kinds(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Table 4: the opening kinds, open arm only."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for c in calls:
        g = gold[c["customer_id"]]
        if g["class"] == "procedural" and arm_label(c) == "open":
            cells[(c["level"], g["kind"])].append(c)
    rows = []
    for (level, kind), group in sorted(cells.items()):
        done = [c for c in group if c.get("status") == "ok"]
        reached = sum(c.get("outcome") == gold[c["customer_id"]]["expected_outcome"] for c in done)
        row = {"level": level, "kind": kind, "n": len(done), "reached": reached,
               "outcomes": dict(Counter(c.get("outcome") for c in done)),
               "no_result": len(group) - len(done), **_rate(reached, len(done))}  # fmt: skip
        if kind == "third_party":
            row["loan_named"] = sum(loan_named(c) for c in done)
        if kind == "refusal":
            seen = [after_refusal(c) for c in done]
            row["refusal_not_read"] = sum(not s["refusal_read"] for s in seen)
            row["asked_further"] = sum(bool(s["further_question"]) for s in seen)
            row["asked_about_loan_after"] = sum(bool(s["matter_question"]) for s in seen)
        rows.append(row)
    return rows


def _caught(call: dict[str, Any]) -> bool:
    return state(call) == "refer"


def paired(
    calls: Iterable[dict],
    gold: dict[str, dict],
    level: float = 0.0,
    closed_caught: Callable[[dict], bool] | None = None,
) -> list[dict[str, Any]]:
    """Table 5: open against closed on the same customers, at level 0 only (contract sections 1 and 8).

    `caught` means referred (open tier refer, closed not confirmed). Pairs with a no-result call are left
    out and counted. Raises for any other level: the arms are not compared above level 0. `closed_caught`
    reads a closed call (default: the primary reading)."""
    closed_caught = closed_caught or _caught
    if level != 0:
        raise ValueError("open and closed are compared at level 0 only (contract section 8)")
    by = {(c["customer_id"], arm_label(c)): c for c in calls if c["level"] == 0}
    groups: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for (cid, arm), open_call in by.items():
        if arm != "open" or (cid, "closed") not in by:
            continue
        closed_call = by[(cid, "closed")]
        g = gold[cid]
        if g["class"] == "procedural":
            continue
        cls = "problem" if g["class"] == "problem" else "no_problem_or_gap"
        for group in ((cls, "all kinds"), (cls, g["kind"])):
            k = groups[group]
            if state(open_call) == "no_result" or state(closed_call) == "no_result":
                k["no_result_pairs"] += 1
                continue
            o, s = _caught(open_call), closed_caught(closed_call)
            k["both" if o and s else "open_only" if o else "closed_only" if s else "neither"] += 1
    rows = []
    for (cls, kind), k in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1] != "all kinds", x[0][1])):
        rows.append({"level": 0.0, "gold_class": cls, "kind": kind,
                     "pairs": k["both"] + k["open_only"] + k["closed_only"] + k["neither"],
                     "both": k["both"], "open_only": k["open_only"], "closed_only": k["closed_only"],
                     "neither": k["neither"], "no_result_pairs": k["no_result_pairs"],
                     "mcnemar_p": round(mcnemar_exact(k["open_only"], k["closed_only"]), 4)})  # fmt: skip
    return rows


# --- closed arm, lenient reading (a sensitivity, reported apart; declared before any counting run) ------

AFFIRM = frozenset({"हाँ", "हां", "जी", "हाँजी", "हांजी", "ji", "haan", "han", "yes", "sahi", "सही", "ठीक"})
NEGATION = frozenset({"नहीं", "नही", "ना", "न", "मत", "ग़लत", "गलत", "nahi", "nahin", "na", "no", "not",
                      "never", "galat", "wrong"})  # fmt: skip
LENIENT_RULE = (
    "**Closed, lenient** (a sensitivity reading, reported apart; the primary closed outcome is the "
    "interpreter's yes/no/other as built). A statement counts as a yes when the interpreter said yes, or when "
    "all of these hold: (a) the reply's first word is one of "
    + ", ".join(sorted(AFFIRM))
    + "; (b) neither of its first two words is a negation word ("
    + ", ".join(sorted(NEGATION))
    + "); (c) the reply holds no negation word anywhere, unless the statement's own claim (the sentence "
    'before the final "is that correct?") holds one, in which case a repeated negation is the claim '
    "agreed with. Words are split on spaces and the marks , . ! ? । - and compared in lower case. "
    "Fixed before any counting run; not tuned on outcomes."
)
_SPLIT = re.compile(r"[\s,.!?।\-–—\"'“”‘’]+")


def _words(text: str) -> list[str]:
    return [w for w in _SPLIT.split(text.lower()) if w]


def claim_of(bot_text: str) -> str:
    """The statement's own claim: the sentence before the closing question (an intro before it is dropped)."""
    parts = [p for p in bot_text.split("।") if p.strip()]
    return parts[-2] if len(parts) >= 2 else bot_text


def lenient_yes(statement: dict[str, Any]) -> bool:
    if statement.get("reading") == "yes":
        return True
    words = _words(statement["reply"]["text"])
    if not words or words[0] not in AFFIRM or any(w in NEGATION for w in words[:2]):
        return False
    claim_negative = any(w in NEGATION for w in _words(claim_of(statement.get("bot", ""))))
    return claim_negative or not any(w in NEGATION for w in words)


def closed_lenient_state(call: dict[str, Any]) -> str:
    """As `state` for a closed call, with each statement read leniently."""
    primary = state(call)
    if primary in ("no_result", "ended_early"):
        return primary
    return "confirmed" if all(lenient_yes(st) for st in call.get("closed", [])) else "refer"


def closed_readings(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Closed confirmed counts under both readings, by level and kind."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        if c["arm"] != "closed":
            continue
        g = gold[c["customer_id"]]
        k = cells[(c["level"], g["class"], g["kind"])]
        k["calls"] += 1
        k["primary_" + state(c)] += 1
        k["lenient_" + closed_lenient_state(c)] += 1
    rows = []
    for (level, cls, kind), k in sorted(cells.items()):
        n = k["calls"] - k["primary_no_result"]
        rows.append({"level": level, "gold_class": cls, "kind": kind, "n": n,
                     "confirmed_primary": k["primary_confirmed"], "confirmed_lenient": k["lenient_confirmed"],
                     "ended_early": k["primary_ended_early"], "no_result": k["primary_no_result"]})  # fmt: skip
    return rows


def closed_not_yes_without_problem(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Every closed statement the primary reading called no or other, on a customer without a problem."""
    return [
        {"customer_id": c["customer_id"], "kind": gold[c["customer_id"]]["kind"],
         "gold_class": gold[c["customer_id"]]["class"], "level": c["level"], "statement_id": st["statement_id"],
         "reply": st["reply"]["text"], "reading": st["reading"], "lenient_yes": lenient_yes(st)}
        for c in calls if c["arm"] == "closed" and c.get("status") == "ok"
        and gold[c["customer_id"]]["class"] in NON_PROBLEM
        for st in c.get("closed", []) if st["reading"] != "yes"
    ]  # fmt: skip


# --- text against voice (contract section 4 item 4) ------------------------------------------------------


def _open0(calls: Iterable[dict]) -> dict[str, dict]:
    return {c["customer_id"]: c for c in calls if arm_label(c) == "open" and c["level"] == 0}


def voice_section(text_calls: list[dict], voice_calls: list[dict], gold: dict[str, dict]) -> dict[str, Any]:
    """Tables 1 to 4 on the voice run (open arm, level 0), and the customers whose tier or outcome differs."""
    wrong = [c.get("customer_id") for c in voice_calls if c.get("path") != "voice"]
    if wrong:
        raise ValueError(f'--voice call files must carry "path": "voice"; not on {wrong[:5]}')
    voice = list(_open0(voice_calls).values())
    text = _open0(text_calls)
    differs = []
    for c in sorted(voice, key=lambda x: x["customer_id"]):
        t = text.get(c["customer_id"])
        a = (state(t), t.get("tier"), t.get("outcome")) if t else ("no_text_call", None, None)
        b = (state(c), c.get("tier"), c.get("outcome"))
        if a != b:
            differs.append({"customer_id": c["customer_id"], "kind": gold[c["customer_id"]]["kind"],
                            "gold_class": gold[c["customer_id"]]["class"],
                            "text": {"counts_as": a[0], "tier": a[1], "outcome": a[2]},
                            "voice": {"counts_as": b[0], "tier": b[1], "outcome": b[2]}})  # fmt: skip
    return {
        "misses": misses(voice, gold),
        "referrals": referrals(voice, gold),
        "referral_basis": basis_split(voice, gold),
        "opening_kinds": opening_kinds(voice, gold),
        "differs": differs,
        "voice_calls": len(voice),
        "text_calls_without_voice": sorted(set(text) - {c["customer_id"] for c in voice}),
    }


def by_writer(calls: Iterable[dict], gold: dict[str, dict]) -> list[dict[str, Any]]:
    """Table 6: misses (problem) and referrals (no problem), by arm, level, writer model and gold class."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        g = gold[c["customer_id"]]
        if g["class"] != "procedural":
            cells[(*_key(c), c.get("writer_model"), g["class"])][state(c)] += 1
    rows = []
    for (arm, level, writer, cls), k in sorted(cells.items(), key=lambda x: tuple(map(str, x[0]))):
        n = sum(k.values()) - k["no_result"]
        what, count = ("miss", sum(k[s] for s in MISS)) if cls == "problem" else ("referred", k["refer"])
        rows.append({"arm": arm, "level": level, "writer_model": writer, "gold_class": cls, "n": n,
                     "counts": what, "count": count, "no_result": k["no_result"], **_rate(count, n)})  # fmt: skip
    return rows


def health(calls: Iterable[dict]) -> list[dict[str, Any]]:
    """Table 7: degraded turns and unmapped lines, by arm and level."""
    cells: dict[tuple, Counter] = defaultdict(Counter)
    keys: dict[tuple, Counter] = defaultdict(Counter)
    for c in calls:
        k = cells[_key(c)]
        k["calls"] += 1
        k["customer_turns"] += len(c.get("turns", [])) + len(c.get("closed", []))
        k["degraded_turns"] += c.get("degraded_turns") or 0
        k["unmapped"] += len(c.get("unmapped", []))
        k["no_result"] += c.get("status") != "ok"
        for u in c.get("unmapped", []):
            keys[_key(c)][u["line_key"]] += 1
    return [{"arm": a, "level": lv, **dict(k), "unmapped_keys": dict(keys[(a, lv)])}
            for (a, lv), k in sorted(cells.items())]  # fmt: skip


def no_results(calls: Iterable[dict]) -> list[dict[str, Any]]:
    return [{"customer_id": c["customer_id"], "arm": arm_label(c), "level": c["level"],
             "error": (c.get("errors") or [{"error": "?"}])[0]["error"][:200]}
            for c in calls if c.get("status") != "ok"]  # fmt: skip


def score(calls: list[dict], gold: dict[str, dict], voice_calls: list[dict] | None = None) -> dict[str, Any]:
    has_level0_pairs = any(arm_label(c) == "closed" and c["level"] == 0 for c in calls)
    return {
        "closed_readings": closed_readings(calls, gold),
        "paired_level0_lenient": paired(
            calls, gold, closed_caught=lambda c: closed_lenient_state(c) == "refer"
        )
        if has_level0_pairs
        else [],
        "closed_not_yes_without_problem": closed_not_yes_without_problem(calls, gold),
        "voice": voice_section(calls, voice_calls, gold) if voice_calls is not None else None,
        "misses": misses(calls, gold),
        "referrals": referrals(calls, gold),
        "referral_basis": basis_split(calls, gold),
        "opening_kinds": opening_kinds(calls, gold),
        "paired_level0": paired(calls, gold) if has_level0_pairs else [],
        "by_writer": by_writer(calls, gold),
        "health": health(calls),
        "no_result": no_results(calls),
        "calls": len(calls),
    }


# --- markdown ----------------------------------------------------------------


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(x) for x in row) + " |" for row in rows]
    return "\n".join(out)


def _ci(row: dict[str, Any], count: str) -> str:
    return per100(row[count], row["n"])


def _tables_1_to_4(result: dict[str, Any], prefix: str) -> list[str]:
    miss_note = (
        "Open miss: tier clear or understanding_gap. Closed miss: confirmed. `incomplete` and `ended early` "
        "are neither; the denominator n is every customer with a result."
    )
    parts = [f"## {prefix}1. Misses per 100 customers with a problem", "", miss_note, ""]
    parts.append(_table(
        ["arm", "level", "kind", "n", "caught", "miss", "incomplete", "ended early", "no result", "misses per 100 [95% CI]"],
        [[r["arm"], f"{r['level']:g}", r["kind"], r["n"], r["caught"], r["miss"], r["incomplete"], r["ended_early"],
          r["no_result"], _ci(r, "miss")] for r in result["misses"]],
    ))  # fmt: skip
    parts += ["", f"## {prefix}2. Referrals per 100 customers without a problem", ""]
    parts.append(_table(
        ["arm", "level", "gold class", "kind", "n", "referred", "clear", "gap", "incomplete", "confirmed",
         "ended early", "no result", "referrals per 100 [95% CI]"],
        [[r["arm"], f"{r['level']:g}", r["gold_class"], r["kind"], r["n"], r["referred"], r["clear"],
          r["understanding_gap"], r["incomplete"], r["confirmed"], r["ended_early"], r["no_result"],
          _ci(r, "referred")] for r in result["referrals"]],
    ))  # fmt: skip
    parts += ["", f"## {prefix}3. What open referrals rest on", ""]
    parts.append(_table(
        ["arm", "level", "gold class", "customer statement", "record only"],
        [[r["arm"], f"{r['level']:g}", r["gold_class"], r["customer_statement"], r["record_only"]]
         for r in result["referral_basis"]],
    ))  # fmt: skip
    opening_note = (
        "Third parties: loan named = any bot line `context.loan` or `verify.after_loan`, or of a later step. "
        "Refusals: a further question = any bot utterance after the first turn read as a refusal "
        "(decline, maybe_decline, no, do_not_call)."
    )
    parts += ["", f"## {prefix}4. Opening kinds (open arm only)", "", opening_note, ""]
    parts.append(_table(
        ["level", "kind", "n", "expected outcome reached", "per 100 [95% CI]", "outcomes", "loan named",
         "refusal: asked further / about the loan / refusal not read", "no result"],
        [[f"{r['level']:g}", r["kind"], r["n"], r["reached"], per100(r["reached"], r["n"]),
          ", ".join(f"{k}: {v}" for k, v in r["outcomes"].items()), r.get("loan_named", ""),
          f"{r['asked_further']} / {r['asked_about_loan_after']} / {r['refusal_not_read']}" if "asked_further" in r else "",
          r["no_result"]] for r in result["opening_kinds"]],
    ))  # fmt: skip
    return parts


def markdown(result: dict[str, Any], title: str) -> str:
    intro = (
        "Synthetic customers, scripted replies, text only (no audio). Counts per 100 with n and a Wilson "
        "95% interval on customers, by kind; no pooled rate. A referral is evidence for human review, "
        "never a finding. Above level 0 each arm stands on its own: no open-minus-closed difference is "
        "computed (contract section 8)."
    )
    parts = [f"# P5 text path: {title}", "", intro, "", LENIENT_RULE, ""]
    parts += _tables_1_to_4(result, "")
    parts += [
        "",
        "## 5. Open against closed, paired by customer, level 0 only",
        "",
        "`caught` = referred (open tier refer; closed not confirmed). Exact McNemar on the discordant pairs.",
        "",
    ]
    if result["paired_level0"]:
        parts.append(_table(
            ["gold class", "kind", "pairs", "both", "open only", "closed only", "neither", "no-result pairs", "McNemar p"],
            [[r["gold_class"], r["kind"], r["pairs"], r["both"], r["open_only"], r["closed_only"], r["neither"],
              r["no_result_pairs"], r["mcnemar_p"]] for r in result["paired_level0"]],
        ))  # fmt: skip
    else:
        parts.append("No level-0 closed calls in this run.")
    parts += ["", "## 6. By writer model", ""]
    parts.append(_table(
        ["arm", "level", "writer model", "gold class", "n", "counts", "count", "no result", "per 100 [95% CI]"],
        [[r["arm"], f"{r['level']:g}", r["writer_model"], r["gold_class"], r["n"], r["counts"], r["count"],
          r["no_result"], per100(r["count"], r["n"])] for r in result["by_writer"]],
    ))  # fmt: skip
    parts += ["", "## 7. Degraded turns and unmapped lines", ""]
    parts.append(_table(
        ["arm", "level", "calls", "customer turns", "degraded turns", "unmapped lines", "unmapped keys", "no result"],
        [[r["arm"], f"{r['level']:g}", r["calls"], r["customer_turns"], r["degraded_turns"], r["unmapped"],
          ", ".join(f"{k}: {v}" for k, v in r["unmapped_keys"].items()) or "none", r["no_result"]]
         for r in result["health"]],
    ))  # fmt: skip
    parts += ["", "## 8. No-result calls", ""]
    if result["no_result"]:
        parts.append(
            _table(
                ["customer", "arm", "level", "error"],
                [[r["customer_id"], r["arm"], f"{r['level']:g}", r["error"]] for r in result["no_result"]],
            )
        )
    else:
        parts.append("None.")
    parts += [
        "",
        "## 9. Closed arm under both readings (lenient: a sensitivity, see the rule at the top)",
        "",
    ]
    parts.append(_table(
        ["level", "gold class", "kind", "n", "confirmed (primary)", "confirmed (lenient)", "ended early", "no result"],
        [[f"{r['level']:g}", r["gold_class"], r["kind"], r["n"], r["confirmed_primary"], r["confirmed_lenient"],
          r["ended_early"], r["no_result"]] for r in result["closed_readings"]],
    ) if result["closed_readings"] else "No closed calls in this run.")  # fmt: skip
    parts += ["", "Paired open against closed at level 0, closed read leniently:", ""]
    if result["paired_level0_lenient"]:
        parts.append(_table(
            ["gold class", "kind", "pairs", "both", "open only", "closed only", "neither", "no-result pairs", "McNemar p"],
            [[r["gold_class"], r["kind"], r["pairs"], r["both"], r["open_only"], r["closed_only"], r["neither"],
              r["no_result_pairs"], r["mcnemar_p"]] for r in result["paired_level0_lenient"]],
        ))  # fmt: skip
    else:
        parts.append("No level-0 closed calls in this run.")
    parts += ["", "## 10. Closed statements read as no or other, customers without a problem (verbatim)", ""]
    rows = result["closed_not_yes_without_problem"]
    parts.append(_table(
        ["customer", "kind", "gold class", "level", "statement", "reply", "reading", "lenient yes"],
        [[r["customer_id"], r["kind"], r["gold_class"], f"{r['level']:g}", r["statement_id"],
          r["reply"].replace("|", "/"), r["reading"], r["lenient_yes"]] for r in rows],
    ) if rows else "None.")  # fmt: skip
    voice = result.get("voice")
    if voice is not None:
        parts += ["", "## 11. Voice path (open arm, level 0), tables V1 to V4", "",
                  (f"{voice['voice_calls']} voice calls. Text open level-0 calls with no voice call: "
                   f"{', '.join(voice['text_calls_without_voice']) or 'none'}."), ""]  # fmt: skip
        parts += _tables_1_to_4(voice, "V")
        parts += [
            "",
            "## 12. Customers whose tier or outcome differs, text against voice (open, level 0)",
            "",
        ]
        parts.append(_table(
            ["customer", "kind", "gold class", "text: counts as / tier / outcome", "voice: counts as / tier / outcome"],
            [[d["customer_id"], d["kind"], d["gold_class"],
              " / ".join(str(d["text"][k]) for k in ("counts_as", "tier", "outcome")),
              " / ".join(str(d["voice"][k]) for k in ("counts_as", "tier", "outcome"))] for d in voice["differs"]],
        ) if voice["differs"] else "None.")  # fmt: skip
    return "\n".join(parts) + "\n"


def load_calls(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir / "calls").glob("*.json"))]


def _harness_hashes() -> dict[str, str]:
    import hashlib

    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob("*.py"))}


def load_gold(path: Path) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {g["id"]: g for g in rows}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--data", default="data/p5", help="the frozen data directory whose gold is used")
    parser.add_argument("--gold", type=Path, default=None, help="default: DATA/gold.jsonl")
    parser.add_argument("--voice", type=Path, help='a voice run directory (call files with "path": "voice")')
    args = parser.parse_args(argv)
    calls = load_calls(args.run_dir)
    voice = load_calls(args.voice) if args.voice else None
    data = (Path(args.data) if Path(args.data).is_absolute() else ROOT / args.data).resolve()
    gold_path = args.gold or data / "gold.jsonl"
    result = score(calls, load_gold(gold_path), voice)
    result["inputs"] = {"data_dir": str(data), "gold": str(gold_path), "harness_sha256": _harness_hashes()}
    (args.run_dir / "score.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    md = markdown(result, args.run_dir.name)
    (args.run_dir / "score.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
