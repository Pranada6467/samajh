"""Independent recount of the P3b report from the raw store files (no samajh imports).
Usage: python p3b_recount.py <state>/ops <report.json>"""
import glob, json, math, sys
from collections import Counter, defaultdict

ops, rep_path = sys.argv[1], sys.argv[2]
rep = json.load(open(rep_path))
rd = lambda n: [json.loads(l) for l in open(f"{ops}/{n}") if l.strip()]
draws, atts, disp = rd("draws.jsonl"), rd("attempts.jsonl"), rd("dispositions.jsonl")
book = {json.loads(l)["record"]["loan_id"]: json.loads(l) for l in open(f"{ops}/book.jsonl") if l.strip()}
calls = {json.load(open(f))["call_id"]: json.load(open(f)) for f in glob.glob(f"{ops}/calls/*.json")}

def wilson(c, n, z=1.959964):
    p = c / n; d = 1 + z * z / n; ce = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, ce - h), min(1, ce + h)

errs = []
def chk(label, mine, prop):
    ok = (mine[0] == prop["count"] and mine[1] == prop["n"])
    if ok and prop["n"]:
        lo, hi = wilson(*mine)
        ok = abs(lo - prop["low"]) < 1e-9 and abs(hi - prop["high"]) < 1e-9
    print(f"{'OK ' if ok else 'BAD'} {label}: mine {mine[0]}/{mine[1]} page {prop['count']}/{prop['n']}")
    if not ok: errs.append(label)

sampled = [(d, x) for d in draws for x in d["drawn"]]
ids = [x["loan_id"] for _, x in sampled]
print("sampled", len(ids), "distinct", len(set(ids)))
by = defaultdict(list)
for a in atts: by[a["loan_id"]].append(a)
for v in by.values(): v.sort(key=lambda a: a["number"])
n = len(ids)
st = {k: 0 for k in ("attempted", "reached", "right_party_confirmed", "completed")}
status = {}
nest_bad = 0
for i in ids:
    A = by.get(i, [])
    st["attempted"] += bool(A)
    r = any(a["outcome"] != "no_answer" for a in A); st["reached"] += r
    rp = any(a["right_party_confirmed"] for a in A); st["right_party_confirmed"] += rp
    c = bool(A) and A[-1]["outcome"] == "completed"; st["completed"] += c
    if c and not (rp and r): nest_bad += 1
    status[i] = "not_attempted" if not A else ("unreachable" if A[-1]["outcome"] == "no_answer" else A[-1]["outcome"])
print("nesting violations", nest_bad, "attempts", len(atts), "page", rep["funnel"]["attempts"])
for row in rep["funnel"]["stages"]: chk("stage " + row["key"], (st[row["key"]], n), row["value"])
sc = Counter(status.values())
for row in rep["funnel"]["exits"]: chk("exit " + row["key"], (sc.get(row["key"], 0), n), row["value"])
# days
dss = [a["day_since_sale"] for a in atts]
print("attempt day_since_sale range", min(dss), max(dss), "after 30:", sum(d > 30 for d in dss), "page", rep["timing"]["attempts_after_window"])
for d, x in sampled:
    sold = book[x["loan_id"]]["sold_on"]; assert x["sold_on"] == sold
# completed
comp = [i for i in ids if status[i] == "completed"]
cr = {i: calls[by[i][-1]["call_id"]]["result"] for i in comp}
nc = len(comp)
tc = Counter(r["tier"] for r in cr.values())
for row in rep["tiers"]: chk("tier " + row["tier"], (tc.get(row["tier"], 0), nc), row["value"])
def flags(r): return [f for p in r["products"] for f in p["flags"]] + r["case_flags"]
def gaps(r): return [g for p in r["products"] for g in p["gaps"]] + r["case_gaps"]
for row in rep["findings"]:
    rule = row["rule_id"]
    fl = [i for i in comp if any(f["rule_id"] == rule for f in flags(cr[i]))]
    und = sum(1 for i in comp if i not in fl and any(g["rule_id"] == rule for g in gaps(cr[i])))
    chk(f"finding {rule}", (len(fl), nc), row["flagged"])
    if und != row["undecided"]: print("BAD undecided", rule, und, row["undecided"]); errs.append("und " + rule)
# referrals
ref = [by[i][-1]["call_id"] for i in comp if cr[i]["tier"] == "refer"]
latest = {}
for x in disp: latest[x["case_id"]] = x["decision"]
lc = Counter(latest.get(c, "awaiting") for c in ref)
for row in rep["referrals"]: chk("disp " + row["key"], (lc.get(row["key"], 0), len(ref)), row["value"])
dec = sum(latest.get(c) in ("established", "not_established") for c in ref)
chk("established of decided", (lc.get("established", 0), dec), rep["established_of_decided"])
print("dispositions on non-referral ids:", [x["case_id"] for x in disp if x["case_id"] not in ref])
# breakdowns
for bd in rep["breakdowns"]:
    key = {"loan_kind": lambda i: book[i]["record"]["loan_kind"], "branch": lambda i: book[i]["branch"],
           "channel": lambda i: book[i]["channel"]}[bd["by"]]
    for row in bd["rows"]:
        mem = [i for i in ids if key(i) == row["key"]]
        cm = [i for i in mem if i in cr]
        assert row["sampled"] == len(mem) and row["completed"] == len(cm), (bd["by"], row["key"])
        chk(f"{bd['by']} {row['key']} refer", (sum(cr[i]["tier"] == "refer" for i in cm), len(cm)), row["referred"])
        chk(f"{bd['by']} {row['key']} gap", (sum(cr[i]["tier"] == "understanding_gap" for i in cm), len(cm)), row["understanding_gap"])
print("ERRORS:", errs or "none")
