"""Summarise p2_r3_out_<arm>.jsonl. uv run python .../p2_r3_summary.py rules failing live"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
STOP = {"declined", "no_go_ahead", "do_not_call", "call_back_later", "human_requested", "written_requested", "wrong_party", "not_confirmed"}
MATCH = {"refuse": {"declined", "no_go_ahead"}, "dnc": {"do_not_call"}, "callback": {"call_back_later"}, "human": {"human_requested"},
         "takeover": {"wrong_party"}}

def load(arm): return [json.loads(l) for l in (HERE / f"p2_r3_out_{arm}.jsonl").read_text().splitlines() if l]

def verdict(r):
    g, k = r["group"], r["kind"]
    if not r.get("reached", False): return "NOT_REACHED"
    end, ap = r["end"], r["after_pos"]
    if g == "g1":
        if r["passed_identity"]: return "pass" + ("+reask" if r["rp_reasks"] else "") + ("+yr_reask" if r["year_reasks"] else "")
        return "FAIL:" + str(end or r["final_pos"])
    if g == "g2":
        L = ",".join(r["leaks"])
        if k.startswith("false_"): return ("passed" if r["passed_identity"] else "stopped:" + str(end or r["final_pos"])) + (" leak=" + L if L else "")
        return ("LEAK=" + L + " " if L else "") + str(end or r["final_pos"])
    if g == "g3":
        base = k.split("_")[0]
        first_end = None if ap else (r["end"])
        if ap is None:
            o = r["end"]
            return ("ok:" if o in MATCH.get(base, set()) else "WRONG:") + o
        if ap == "AtCallbackTime": return ("ok:" if base == "callback" else "WRONG:") + "ask_when"
        if ap == "AtStopCheck": return "asked_go_on"
        if ap == "AtIdentity" and r["after_keys"] and any("verify" in x or "who" in x for x in r["after_keys"]): return "asked_who:" + ",".join(r["after_keys"])
        return "WENT_ON:" + ap + ":" + ",".join(r["after_keys"])
    if g == "g4":
        if ap is None: return ("ENDED:" if k != "later" else "ok_end:") + r["end"]
        return ("ok:" if k != "later" else "NOT_ENDED:") + ap
    if g == "g5":
        if ap is None: return "END:" + r["end"]
        return ap
    if g == "g6":
        if ap is None: return "END:" + r["end"]
        return ap + ":" + ",".join(r["after_keys"])

for arm in sys.argv[1:]:
    rows = load(arm)
    print(f"\n===== {arm} (n={len(rows)})  test-turn degraded: {sum(r.get('test_degraded', False) for r in rows)}")
    by = defaultdict(Counter)
    for r in rows:
        by[(r["group"], r["stage"], r["kind"].split("_")[0] if r['group'] in ('g3',) else r["kind"])][verdict(r)] += 1
    for key in sorted(by): print(key, dict(by[key]))
