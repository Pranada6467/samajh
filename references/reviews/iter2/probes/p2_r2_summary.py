"""Tables from p2_r2_groups_<arm>.jsonl / p2_r2_calls_<arm>.jsonl / latency files. Read-only.
uv run python references/reviews/iter2/probes/p2_r2_summary.py [section]"""
import glob, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["rules", "live", "failing", "failturn"]


def load(name):
    return [json.loads(l) for l in (HERE / f"{name}.jsonl").read_text().splitlines()]


G = {a: load(f"p2_r2_groups_{a}") for a in ARMS}
sec = sys.argv[1] if len(sys.argv) > 1 else "all"

EXPECT = {
    "busy": {"call_back_later"}, "call_later": {"call_back_later"}, "not_interested": {"declined"},
    "stop_calling": {"do_not_call"}, "human": {"human_requested"}, "writing": {"written_requested"},
    "hostile": {"declined", "do_not_call"}, "silent": {"no_response"},
}
EXTRA_OK = {"go_ahead": {"not_interested": {"no_go_ahead"}, "hostile": {"no_go_ahead"}},
            "opening": {"not_interested": {"not_confirmed"}, "hostile": {"not_confirmed"}}}


INPUTS = {c["id"]: c for c in json.loads((HERE / "p2_r2_inputs.json").read_text())}


def first_cust(r):
    return INPUTS[r["id"]]["turns"][0]


def by_point(rows):
    return Counter(r["point"] for r in rows)


if sec in ("all", "g1"):
    print("== GROUP 1 third parties (excluding false_claim)")
    for a in ARMS:
        rows = [r for r in G[a] if r["group"] == "third_party" and r["category"] != "false_claim"]
        for pt in ("opening", "birth_year", "mid"):
            sub = [r for r in rows if (r["point"].startswith("mid") if pt == "mid" else r["point"] == pt)]
            n = len(sub)
            lk = {k: sum(r["leak"][k] for r in sub) for k in ("lender", "loan", "product", "value")}
            old = sum(r["old_leak"] for r in sub)
            ended1 = sum(1 for r in sub if r["classes"] and r["classes"][0] == "END")
            oc = Counter(r["outcome"] for r in sub)
            print(f"{a:8s} {pt:10s} n={n:2d} leak lender={lk['lender']} loan={lk['loan']} product={lk['product']} value={lk['value']} oldLEAK={old} ended_on_utterance={ended1} {dict(oc)}")
        bad = [r for r in rows if any(r["leak"].values())]
        for r in bad:
            print("   LEAK", a, r["id"], r["point"], r["category"], r["outcome"], r["leak_hits"][:4])
            cust = [e for e in r["log"] if e["who"] == "CUST"]
            print("        ", " | ".join(e["text"] for e in cust))

if sec in ("all", "fc"):
    print("== GROUP 1 false claims")
    for a in ARMS:
        for r in [r for r in G[a] if r["category"] == "false_claim"]:
            path = []
            for e in r["log"]:
                path.append(("C:" + e["text"]) if e["who"] == "CUST" else ("B:" + ",".join(e["keys"])))
            print(a, r["id"], r["outcome"], " / ".join(path))

if sec in ("all", "g2"):
    print("== GROUP 2 refusals")
    for a in ARMS:
        rows = [r for r in G[a] if r["group"] == "refusal"]
        print(a, "points", dict(by_point(rows)))
        cats = defaultdict(list)
        for r in rows:
            cats[r["category"]].append(r)
        for c, sub in cats.items():
            went = sum(1 for r in sub if r.get("last_class") in ("ASK_NEXT",) or (c not in ("silent", "noise") and r.get("immediate") in ("ASK_NEXT", "ASK_SAME")))
            nxt = sum(1 for r in sub if (r.get("immediate") == "ASK_NEXT") if c not in ("silent", "noise")) if c not in ("silent", "noise") else sum(1 for r in sub if r.get("last_class") == "ASK_NEXT")
            same = sum(1 for r in sub if r.get("immediate") == "ASK_SAME") if c not in ("silent", "noise") else 0
            sc = sum(1 for r in sub if r.get("immediate") == "STOP_CHECK")
            exp = EXPECT.get(c)
            wrong = [r for r in sub if exp and r["outcome"] not in exp | EXTRA_OK.get(r["point"], {}).get(c, set())]
            print(f"  {a:8s} {c:15s} n={len(sub):2d} next_q={nxt} same_q={same} stop_check={sc} wrong_outcome={len(wrong) if exp else '-'} {dict(Counter(r['outcome'] for r in sub))}")
        for r in rows:
            c = r["category"]
            exp = EXPECT.get(c)
            nq = r.get("immediate") in ("ASK_NEXT", "ASK_SAME") if c not in ("silent", "noise") else r.get("last_class") == "ASK_NEXT"
            wr = exp and r["outcome"] not in exp | EXTRA_OK.get(r["point"], {}).get(c, set())
            if nq or wr:
                print(f"     {'Q' if nq else ' '}{'W' if wr else ' '} {r['id']} {c} {r['point']} imm={r.get('immediate')} out={r['outcome']} :: {[e['text'] for e in r['log'] if e['who']=='CUST'][-len(r['classes']) - 2:]} -> {r['log'][-1]['keys']}")

if sec in ("all", "g3"):
    print("== GROUP 3 genuine identity")
    for a in ARMS:
        rows = [r for r in G[a] if r["group"] == "genuine"]
        imm = Counter()
        br = Counter()
        for r in rows:
            k = r["immediate"]
            ak = r["after_keys"]
            if k == "END":
                v = "ended:" + r["outcome"]
            elif "disclosure.go_ahead" in ak:
                v = "passed"
            elif ak[-1] == "right_party.reask":
                v = "reasked"
            elif ak[-1] == "purpose.before_confirm" or "purpose.before_confirm" in ak:
                v = "purpose"
            else:
                v = "other:" + ak[-1]
            imm[v] += 1
            r["_v"] = v
            for name, b in (r.get("branches") or {}).items():
                bv = "passed" if "disclosure.go_ahead" in b["keys"] else (("ended:" + b["outcome"]) if b["class"] == "END" else b["keys"][-1])
                br[(name, bv)] += 1
        print(f"  {a:8s} n={len(rows)} {dict(imm)}")
        print(f"           second reply after re-ask: {dict(br)}")
        for r in rows:
            if r["_v"] != "passed":
                print(f"       {a} {r['id']} {r['record']:9s} {r['_v']:22s} {first_cust(r)}")
    print("== GROUP 3b genuine birth year")
    for a in ARMS:
        rows = [r for r in G[a] if r["group"] == "genuine_year"]
        res = Counter()
        for r in rows:
            ak = r["after_keys"]
            v = ("ended:" + r["outcome"]) if r["immediate"] == "END" else ("passed" if "context.loan" in ak else ak[-1])
            res[v] += 1
            if v != "passed":
                print(f"       {a} {r['id']} {v} {first_cust(r)}")
        print(f"  {a:8s} n={len(rows)} {dict(res)}")

if sec in ("all", "g4"):
    print("== GROUP 4 non-refusals")
    for a in ARMS:
        rows = [r for r in G[a] if r["group"] == "nonrefusal"]
        c = Counter(r["immediate"] for r in rows)
        print(f"  {a:8s} n={len(rows)} points={dict(by_point(rows))} {dict(c)}")
        for r in rows:
            if r["immediate"] in ("END", "STOP_CHECK"):
                print(f"       {r['immediate']:10s} {r['id']} {r['point']:10s} {r['outcome']:18s} {first_cust(r)}")

if sec in ("all", "g6"):
    print("== GROUP 6 whole calls")
    for a in ARMS:
        if a == "failturn": continue
        for r in load(f"p2_r2_calls_{a}"):
            print(f"  {a:8s} {r['id']:34s} {r['outcome']:28s} turns={r['customer_turns']:2d} classified={r['classified_turns']:2d} clf_s={r['classifier_seconds']:6.2f} maxrep={r['max_line_repeats']} rep={r['repeated']} filled={r.get('filled_from_fallback')}")
