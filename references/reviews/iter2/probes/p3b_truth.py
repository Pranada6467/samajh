"""Hidden truth vs referral, for a store. Usage: p3b_truth.py <ops dir> <sim-customers.jsonl>"""
import json, sys
from collections import Counter
ops, simf = sys.argv[1], sys.argv[2]
PROBLEM = {"told_it_is_a_deposit","believes_investment","did_not_agree","deduction_not_known","required_no_choice",
           "expects_money_back","wrong_cancel_window","coached","knows_almost_nothing","evasive"}
sim = {json.loads(l)["loan_id"]: json.loads(l) for l in open(simf)}
atts = {}
for l in open(f"{ops}/attempts.jsonl"):
    a = json.loads(l); atts.setdefault(a["loan_id"], []).append(a)
rows = Counter(); missed = []; fp=[]
for lid, A in atts.items():
    A.sort(key=lambda a: a["number"])
    if A[-1]["outcome"] != "completed": continue
    r = json.load(open(f"{ops}/calls/{A[-1]['call_id']}.json"))["result"]
    arch = sim[lid]["archetype"]; prob = arch in PROBLEM
    rows[(prob, r["tier"])] += 1
    if prob and r["tier"] != "refer": missed.append((lid, arch, r["tier"]))
    if not prob and r["tier"] == "refer": fp.append((lid, arch))
print(sorted(rows.items())); print("missed:", missed); print("non-problem referred:", fp)
