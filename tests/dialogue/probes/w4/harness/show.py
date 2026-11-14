"""Show the trail of cases: show.py RUNFILE ID [ID...]"""
import json, sys
from pathlib import Path
res = {r["id"]: r for r in (json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip())}
for rid in sys.argv[2:]:
    r = res[rid]
    print(f"== {rid} outcome={r.get('outcome')} passed={r.get('passed')} err={r.get('error','')}")
    for t in r["trail"]:
        if "reply" in t:
            print(f"   C[{t.get('bank', t.get('i',''))}]: {t['reply']}")
        print(f"   B({t['language']}): {t['keys']}" + (f" END={t['end']} req={t.get('requested_language')}" if t.get('end') else ""))
