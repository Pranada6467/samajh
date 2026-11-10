"""P3b round 3: recount the report from the raw store files, not through samajh.ops.report or
samajh.ops.batch (claims 8, 9, 13, 16). The core is used only for each call's tier
(`CaseResult.tier`), its flags and gaps, and `samajh.rules.summarise` for the refer lines.

Usage: uv run python references/reviews/iter2/probes/p3b_r3_recount.py <state dir> [<state dir> ...]
Reads only. Prints, per state, rows checked and every mismatch.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.rules import summarise  # noqa: E402
from samajh.types import CaseResult, LoanRecord, RuleId, Tier  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
RETRY = {"no_answer", "call_back_later", "language_switch"}


def lines(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x] if p.exists() else []


def recount(state: Path) -> tuple[int, list[str]]:
    ops = state / "ops"
    rep = json.loads(build_report(OpsStore(ops)).model_dump_json())
    book = {r["record"]["loan_id"]: r for r in lines(ops / "book.jsonl")}
    meta = json.loads((ops / "batch.json").read_text())
    draws = lines(ops / "draws.jsonl")
    eff: dict[str, dict] = {}
    for a in lines(ops / "attempts.jsonl"):
        eff[a["attempt_id"]] = a
    by_loan: dict[str, list[dict]] = {}
    for a in eff.values():
        by_loan.setdefault(a["loan_id"], []).append(a)
    decisions: dict[str, list[dict]] = {}
    for d in lines(ops / "dispositions.jsonl"):
        decisions.setdefault(d["case_id"], []).append(d)
    outside: dict[str, dict] = {}
    for o in lines(ops / "outside.jsonl"):
        outside[o["session_id"]] = o

    rows = 0
    bad: list[str] = []

    def eq(name: str, mine, theirs) -> None:
        nonlocal rows
        rows += 1
        if mine != theirs:
            bad.append(f"{name}: recount {mine} report {theirs}")

    sampled = []
    for d in draws:
        for x in d["drawn"]:
            ch = sorted(by_loan.get(x["loan_id"], []), key=lambda a: a["number"])
            sampled.append((d, x, ch))

    def status(ch: list[dict]) -> str:
        if not ch:
            return "not_attempted"
        last = ch[-1]
        if last["outcome"] == "completed":
            return "completed" if 0 <= last["day_since_sale"] <= 30 else "completed_late"
        if last["outcome"] in RETRY and last["day_since_sale"] >= 30:
            return "not_reached_in_time"
        if last["outcome"] == "no_answer":
            return "unreachable"
        return last["outcome"]

    st = [status(ch) for _, _, ch in sampled]
    n = len(sampled)
    eq("funnel.sampled", n, rep["funnel"]["sampled"])
    eq("funnel.attempts", sum(len(ch) for _, _, ch in sampled), rep["funnel"]["attempts"])
    stage = {r["key"]: r["value"] for r in rep["funnel"]["stages"]}
    eq("attempted", sum(bool(ch) for _, _, ch in sampled), stage["attempted"]["count"])
    eq("reached", sum(any(a["outcome"] != "no_answer" for a in ch) for _, _, ch in sampled), stage["reached"]["count"])
    eq("right_party", sum(any(a["right_party_confirmed"] for a in ch) for _, _, ch in sampled), stage["right_party_confirmed"]["count"])
    eq("completed", st.count("completed"), stage["completed"]["count"])
    for r in rep["funnel"]["exits"]:
        eq(f"exit {r['key']}", st.count(r["key"]), r["value"]["count"])
        eq(f"exit {r['key']} n", n, r["value"]["n"])

    counted = []
    for (d, x, ch), s in zip(sampled, st):
        if s == "completed":
            call = json.loads((ops / "calls" / f"{ch[-1]['call_id']}.json").read_text())
            res = CaseResult.model_validate(call["result"])
            rec = LoanRecord.model_validate(book[x["loan_id"]]["record"])
            counted.append((x, ch, call, res, summarise(rec, res), book[x["loan_id"]]))
    tiers = Counter(c[3].tier for c in counted)
    trow = {r["tier"]: r["value"] for r in rep["tiers"]}
    for t in Tier:
        eq(f"tier {t.value}", tiers[t], trow[t.value]["count"])
        eq(f"tier {t.value} n", len(counted), trow[t.value]["n"])

    gap_by_rule = {}
    for r in rep["rules"]:
        rule = RuleId(r["rule_id"])
        flagged = [c for c in counted if rule in {f.rule_id for f in c[3].all_flags()}]
        eq(f"rule {rule.value} flagged", len(flagged), r["flagged"]["count"])
        eq(f"rule {rule.value} n", len(counted), r["flagged"]["n"])
        und = sum(
            rule not in {f.rule_id for f in c[3].all_flags()} and any(g.rule_id is rule for g in c[3].all_gaps())
            for c in counted
        )
        eq(f"rule {rule.value} undecided", und, r["undecided"])
        ref = sum(any(rule in ln.rule_ids and ln.tier is Tier.refer for ln in c[4].lines) for c in flagged)
        eq(f"rule {rule.value} referred", ref, r["referred"])
        ug = sum(
            c[3].tier is Tier.understanding_gap
            and any(rule in ln.rule_ids and ln.tier is Tier.understanding_gap for ln in c[4].lines)
            for c in counted
        )
        eq(f"rule {rule.value} understanding_gap", ug, r["understanding_gap"])
        gap_by_rule[rule.value] = ug

    # decisions on counted referrals
    refs = [c[2]["call_id"] for c in counted if c[3].tier is Tier.refer]
    latest = [decisions[r][-1]["decision"] if r in decisions else None for r in refs]
    drow = {r["key"]: r["value"] for r in rep["referrals"]}
    for k in ("concern_supported", "concern_not_supported", "call_customer", "needs_information"):
        eq(f"decision {k}", latest.count(k), drow[k]["count"])
    eq("decision none", latest.count(None), drow["none"]["count"])
    final = {"concern_supported", "concern_not_supported"}
    eq("open referrals", sum(x not in final for x in latest), rep["open_referrals"]["count"])

    # timing
    att = [a for _, _, ch in sampled for a in ch]
    first = sorted(ch[0]["day_since_sale"] for _, _, ch in sampled if ch)
    eq("timing.first", [first[0], statistics.median_low(first), first[-1]] if first else None, rep["timing"]["first_attempt_days"])
    after = [a for a in att if a["day_since_sale"] > 30]
    eq("timing.after", len(after), rep["timing"]["attempts_after_window"]["count"])
    eq("timing.after phone", sum(a["source"]["kind"] == "phone_session" for a in after), rep["timing"]["phone_attempts_after_window"])
    eq("timing.late", st.count("completed_late"), rep["timing"]["completed_late"])
    if after and ("none by design" in rep["timing"]["note"] or str(len(after)) not in rep["timing"]["note"]):
        bad.append(f"timing note does not give the {len(after)} late attempts: {rep['timing']['note']}")
    for a in att:
        if a["day_since_sale"] < 0:
            bad.append(f"negative day {a['attempt_id']}")
    # outside, other referrals
    eq("outside_calls", len(outside), rep["outside_calls"])
    late_ref = 0
    for (d, x, ch), s in zip(sampled, st):
        if s == "completed_late":
            call = json.loads((ops / "calls" / f"{ch[-1]['call_id']}.json").read_text())
            late_ref += CaseResult.model_validate(call["result"]).tier is Tier.refer
    out_ref = 0
    for o in outside.values():
        if o.get("call_id"):
            call = json.loads((ops / "calls" / f"{o['call_id']}.json").read_text())
            out_ref += CaseResult.model_validate(call["result"]).tier is Tier.refer
    eq("other_referrals", late_ref + out_ref, rep["other_referrals"])
    # sampling
    p0, p1 = date.fromisoformat(meta["period_start"]), date.fromisoformat(meta["period_end"])
    in_period = [lid for lid, b in book.items() if p0 <= date.fromisoformat(b["sold_on"]) <= p1]
    elig = {lid for d in draws for lid in d["eligible"]}
    eq("sales_in_period", len(in_period), rep["sampling"]["sales_in_period"])
    eq("eligible", sum(x in elig for x in in_period), rep["sampling"]["eligible"])
    rates = [len(d["drawn"]) / len(d["eligible"]) for d in draws if d["eligible"]]
    lo, hi = (min(rates), max(rates)) if rates else (None, None)
    eq("inclusion_low", lo, rep["sampling"]["inclusion_low"])
    eq("inclusion_high", hi, rep["sampling"]["inclusion_high"])
    narrow = bool(rates) and hi > 0 and lo > 0 and hi / lo <= 1.25
    wide = bool(rates) and hi > 0 and not narrow
    eq("intervals_shown", not wide, rep["sampling"]["intervals_shown"])
    stmt = rep["sampling"]["statement"]
    if ("about the same chance" in stmt) != narrow:
        bad.append(f"'about the same chance' present={('about the same chance' in stmt)} but narrow={narrow}")
    if rates and lo is not None and (f"{lo:.1%}" not in stmt or f"{hi:.1%}" not in stmt):
        bad.append(f"range not stated: {stmt[:160]}")
    if wide:
        for phrase in ("differed", "unweighted counts of the calls analysed", "do not estimate the share among all sales"):
            if phrase not in stmt:
                bad.append(f"wide statement lacks '{phrase}'")

        def walk(o, path=""):
            if isinstance(o, dict):
                if "low" in o and "high" in o and (o["low"] is not None or o["high"] is not None):
                    bad.append(f"interval shown at {path} with wide chances")
                for k, v in o.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, f"{path}[{i}]")
            elif isinstance(o, str) and "interval" in o.lower() and "95%" in o:
                bad.append(f"interval words at {path} with wide chances: {o[:100]}")

        walk(rep)
    # tiles
    t = rep["tiles"]
    eq("tile sold", len(in_period), t["sold"])
    eq("tile sampled", n, t["sampled"])
    eq("tile completed", st.count("completed"), t["completed"])
    eq("tile referred", tiers[Tier.refer], t["referred"])
    eq("tile understanding_gap", tiers[Tier.understanding_gap], t["understanding_gap"])
    top = max(gap_by_rule.values(), default=0)
    eq("tile most_common_gap_count", top, t["most_common_gap_count"])
    if top:
        tied = [k for k, v in gap_by_rule.items() if v == top]
        rows += 1
        if t["most_common_gap"]["key"] not in tied:
            bad.append(f"most common gap {t['most_common_gap']['key']} not among {tied}")
    else:
        eq("tile most_common_gap none", "none", t["most_common_gap"]["key"])
    if "ynthetic" not in t["synthetic"]:
        bad.append(f"tiles synthetic label: {t['synthetic']}")
    return rows, bad


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        rows, bad = recount(Path(arg))
        print(f"{arg}: {rows} rows checked, {len(bad)} mismatches")
        for b in bad:
            print("   MISMATCH", b)
