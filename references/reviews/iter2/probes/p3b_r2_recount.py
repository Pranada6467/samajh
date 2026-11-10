"""P3b re-verification (round 2): recount every number of the half-yearly report from the raw store
files. No samajh imports except `samajh.rules.summarise` for the per-rule `referred` column (marked).

Usage: uv run python references/reviews/iter2/probes/p3b_r2_recount.py <state>/ops <report.json>

Status of a sampled loan is recomputed from its last attempt by number: completed on day 0..30 ->
completed, otherwise completed_late; a retry outcome (no_answer, call_back_later, language_switch)
on day >= 30 -> not_reached_in_time; no_answer -> unreachable; else the outcome's name.
"""

import glob
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

ops, rep_path = sys.argv[1], sys.argv[2]
rep = json.load(open(rep_path))


def rd(name):
    try:
        return [json.loads(l) for l in open(f"{ops}/{name}") if l.strip()]
    except FileNotFoundError:
        return []


draws, atts, disp, outside = rd("draws.jsonl"), rd("attempts.jsonl"), rd("dispositions.jsonl"), rd("outside.jsonl")
book = {r["record"]["loan_id"]: r for r in rd("book.jsonl")}
batch = json.load(open(f"{ops}/batch.json"))
calls = {}
for f in glob.glob(f"{ops}/calls/*.json"):
    c = json.load(open(f))
    calls[c["call_id"]] = c

Z = 1.959964
rows_checked = 0
errs = []


def wilson(c, n):
    p = c / n
    d = 1 + Z * Z / n
    ce = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, ce - h), min(1.0, ce + h)


def chk(label, mine, page, interval=True):
    global rows_checked
    rows_checked += 1
    ok = mine[0] == page["count"] and mine[1] == page["n"]
    if interval:
        if "low" not in page:
            ok = False
        elif page["n"]:
            lo, hi = wilson(*mine)
            ok = ok and abs(lo - page["low"]) < 1e-9 and abs(hi - page["high"]) < 1e-9
    elif "low" in page or "high" in page:
        ok = False  # a count that must carry no interval
    if not ok:
        errs.append(label)
        print(f"BAD {label}: mine {mine} page {page}")


def eq(label, mine, page):
    global rows_checked
    rows_checked += 1
    if mine != page:
        errs.append(label)
        print(f"BAD {label}: mine {mine!r} page {page!r}")


RETRY = {"no_answer", "call_back_later", "language_switch"}
sampled = [(d, x) for d in draws for x in d["drawn"]]
ids = [x["loan_id"] for _, x in sampled]
eq("sampled distinct", len(set(ids)), len(ids))
by = defaultdict(list)
for a in atts:
    by[a["loan_id"]].append(a)
for v in by.values():
    v.sort(key=lambda a: a["number"])


def status(i):
    A = by.get(i, [])
    if not A:
        return "not_attempted"
    last = A[-1]
    if last["outcome"] == "completed":
        return "completed" if 0 <= last["day_since_sale"] <= 30 else "completed_late"
    if last["outcome"] in RETRY and last["day_since_sale"] >= 30:
        return "not_reached_in_time"
    if last["outcome"] == "no_answer":
        return "unreachable"
    return last["outcome"]


n = len(ids)
S = {i: status(i) for i in ids}
f = rep["funnel"]
eq("funnel sampled", n, f["sampled"])
eq("funnel attempts", sum(len(by.get(i, [])) for i in ids), f["attempts"])
stage = {
    "attempted": sum(bool(by.get(i)) for i in ids),
    "reached": sum(any(a["outcome"] != "no_answer" for a in by.get(i, [])) for i in ids),
    "right_party_confirmed": sum(any(a["right_party_confirmed"] for a in by.get(i, [])) for i in ids),
    "completed": sum(S[i] == "completed" for i in ids),
}
for row in f["stages"]:
    chk("stage " + row["key"], (stage[row["key"]], n), row["value"])
sc = Counter(S.values())
for row in f["exits"]:
    chk("exit " + row["key"], (sc.get(row["key"], 0), n), row["value"])
eq("exits + completed = sampled", stage["completed"] + sum(r["value"]["count"] for r in f["exits"]), n)

# counted calls: completed in window and the call file exists
comp = [i for i in ids if S[i] == "completed" and by[i][-1]["call_id"] in calls]
cr = {i: calls[by[i][-1]["call_id"]]["result"] for i in comp}
nc = len(comp)
eq("batch completed", nc, rep["batch"]["completed"])
tc = Counter(r["tier"] for r in cr.values())
for row in rep["tiers"]:
    chk("tier " + row["tier"], (tc.get(row["tier"], 0), nc), row["value"])


def flags(r):
    return [x for p in r["products"] for x in p["flags"]] + r["case_flags"]


def gaps(r):
    return [g for p in r["products"] for g in p["gaps"]] + r["case_gaps"]


from samajh.rules import summarise  # noqa: E402  (only for the per-rule `referred` column)
from samajh.types import CaseResult, LoanRecord  # noqa: E402

lines = {
    i: summarise(LoanRecord.model_validate(book[i]["record"]), CaseResult.model_validate(cr[i])).lines for i in comp
}
for row in rep["findings"]:
    rule = row["rule_id"]
    fl = [i for i in comp if any(x["rule_id"] == rule for x in flags(cr[i]))]
    und = sum(1 for i in comp if i not in fl and any(g["rule_id"] == rule for g in gaps(cr[i])))
    chk(f"finding {rule}", (len(fl), nc), row["flagged"])
    eq(f"undecided {rule}", und, row["undecided"])
    ref = sum(any(rule in l.rule_ids and l.tier == "refer" for l in lines[i]) for i in fl)
    eq(f"referred {rule} (uses summarise)", ref, row["referred"])

# referrals and decisions: counts, never intervals
ref_ids = [by[i][-1]["call_id"] for i in comp if cr[i]["tier"] == "refer"]
eq("batch referred", len(ref_ids), rep["batch"]["referred"])
latest = {}
for x in disp:
    latest[x["case_id"]] = x["decision"]
lc = Counter(latest.get(c, "none") for c in ref_ids)
for row in rep["referrals"]:
    chk("decision " + row["key"], (lc.get(row["key"], 0), len(ref_ids)), row["value"], interval=False)
final = {"concern_supported", "concern_not_supported"}
decided = sum(latest.get(c) in final for c in ref_ids)
chk("open referrals", (len(ref_ids) - decided, len(ref_ids)), rep["open_referrals"], interval=False)
chk("supported of decided", (lc.get("concern_supported", 0), decided), rep["supported_of_decided"], interval=False)
eq("batch open_cases", len(ref_ids) - decided, rep["batch"]["open_cases"])

# referrals the report does not count: late sampled referrals plus outside referrals
late_ref = sum(
    S[i] == "completed_late" and by[i][-1]["call_id"] in calls and calls[by[i][-1]["call_id"]]["result"]["tier"] == "refer"
    for i in ids
)
out_ref = sum(bool(o.get("call_id")) and calls[o["call_id"]]["result"]["tier"] == "refer" for o in outside)
eq("other referrals", late_ref + out_ref, rep["other_referrals"])
eq("outside calls", len(outside), rep["outside_calls"])

# timing
first = sorted(by[i][0]["day_since_sale"] for i in ids if by.get(i))
allA = [a for i in ids for a in by.get(i, [])]
eq("first attempt days", [first[0], statistics.median_low(first), first[-1]] if first else None,
   rep["timing"]["first_attempt_days"])
chk("attempts after day 30", (sum(a["day_since_sale"] > 30 for a in allA), len(allA)),
    rep["timing"]["attempts_after_window"], interval=False)
eq("completed late", sc.get("completed_late", 0), rep["timing"]["completed_late"])

# sampling
ps, pe = date.fromisoformat(batch["period_start"]), date.fromisoformat(batch["period_end"])
inp = [(i, date.fromisoformat(r["sold_on"])) for i, r in book.items() if ps <= date.fromisoformat(r["sold_on"]) <= pe]
el = {i for d in draws for i in d["eligible"]}
sm = rep["sampling"]
eq("sales in period", len(inp), sm["sales_in_period"])
eq("eligible", sum(i in el for i, _ in inp), sm["eligible"])
eq("sampling sampled", n, sm["sampled"])
eq("never eligible sum", len(inp) - sm["eligible"], sum(r["count"] for r in sm["never_eligible"]))
incl = [len(d["drawn"]) / len(d["eligible"]) for d in draws if d["eligible"]]
eq("inclusion range", (min(incl), max(incl)) if incl else (None, None), (sm["inclusion_low"], sm["inclusion_high"]))
for d in rep["draws"]:
    raw = next(x for x in draws if x["draw_id"] == d["draw_id"])
    eq(f"draw {d['draw_id']} eligible/drawn", (len(raw["eligible"]), len(raw["drawn"])), (d["eligible"], d["drawn"]))

# breakdowns: each row against every other row together
keyf = {
    "loan_kind": lambda i: book[i]["record"]["loan_kind"],
    "branch": lambda i: book[i]["branch"],
    "channel": lambda i: book[i]["channel"],
}
for bd in rep["breakdowns"]:
    key = keyf[bd["by"]]
    eq(f"{bd['by']} keys", sorted({key(i) for i in ids}), [r["key"] for r in bd["rows"]])
    for row in bd["rows"]:
        mem = [i for i in ids if key(i) == row["key"]]
        cm = [i for i in comp if key(i) == row["key"]]
        rest = [i for i in comp if key(i) != row["key"]]
        eq(f"{bd['by']} {row['key']} sampled/completed", (len(mem), len(cm)), (row["sampled"], row["completed"]))
        for t, field in (("refer", "referred"), ("understanding_gap", "understanding_gap")):
            chk(f"{bd['by']} {row['key']} {field}", (sum(cr[i]["tier"] == t for i in cm), len(cm)), row[field])
            chk(f"{bd['by']} {row['key']} rest {field}", (sum(cr[i]["tier"] == t for i in rest), len(rest)), row["rest_" + field])

# policy review: one item per flagged rule, sentence counts, and the "highest" place
stmt = {r["rule_id"]: r for r in rep["findings"]}
flagged_rules = [r for r in rep["findings"] if r["flagged"]["count"]]
eq("policy items", sorted(r["rule_id"] for r in flagged_rules), sorted(p["rule_id"] for p in rep["policy_review"]))
CH = {"branch": "Branch", "agent": "Direct selling agent", "app": "Lender's app"}
for p in rep["policy_review"]:
    r = stmt[p["rule_id"]]
    eq(f"policy sentence {p['rule_id']}",
       f"{r['flagged']['count']} of {r['flagged']['n']} customers who completed the call {r['statement']}", p["sentence"])
    rule = p["rule_id"]
    best = None
    for by_name in ("branch", "channel"):
        groups = defaultdict(list)
        for i in comp:
            groups[keyf[by_name](i)].append(i)
        for k in sorted(groups):
            m = groups[k]
            cnt = sum(any(x["rule_id"] == rule for x in flags(cr[i])) for i in m)
            if len(m) >= 5 and cnt and (best is None or cnt / len(m) > best[0]):
                rest = [i for i in comp if keyf[by_name](i) != k]
                rc = sum(any(x["rule_id"] == rule for x in flags(cr[i])) for i in rest)
                name = f"branch {k}" if by_name == "branch" else f"the {CH[k].lower()} sales channel"
                others = "the other branches" if by_name == "branch" else "the other channels"
                lo, hi = wilson(cnt, len(m))
                rlo, rhi = wilson(rc, len(rest)) if rest else (None, None)
                rp = f"95% interval {rlo:.0%} to {rhi:.0%}" if rest else "no calls"
                best = (cnt / len(m), f"highest at {name}: {cnt} of {len(m)} counted calls (95% interval {lo:.0%} to "
                        f"{hi:.0%}), against {rc} of {len(rest)} at {others} ({rp})")
    eq(f"policy highest {rule}", best[1] if best else None, p["highest"])

print(f"rows checked {rows_checked}; ERRORS: {errs or 'none'}")
