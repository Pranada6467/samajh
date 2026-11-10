"""P3b sampler probe: edge dates, reproducibility, inclusion probability across the 4 weekly draws."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from samajh.ops import book as books, sampler
from samajh.ops.__main__ import DEMO_DRAWS, DEMO_SEED

meta, loans, customers = books.generate_book(DEMO_SEED)
as_of = date(2027, 2, 8)
days = Counter((as_of - l.sold_on).days for l in loans)
el = sampler.eligible(loans, as_of)
ed = sorted({(as_of - l.sold_on).days for l in el})
print("eligible days range", ed[0], ed[-1], "n eligible", len(el),
      "book loans at day 30:", days[30], "day 31:", days[31], "day 0:", days[0], "day -1:", days[-1])
d1 = sampler.draw(loans, meta, as_of, 20, 85, ())
d2 = sampler.draw(loans, meta, as_of, 20, 85, ())
print("reproducible:", d1 == d2, "verify:", sampler.verify_draw(d1, loans, []))
print("draw days:", sorted(x.day_since_sale for x in d1.drawn))
# size larger than eligible
big = sampler.draw(loans, meta, as_of, 10_000, 85, ())
print("oversize request drew", len(big.drawn), "of", len(big.eligible))
# far future as_of: no eligible
try:
    e = sampler.draw(loans, meta, date(2030, 1, 1), 20, 85, ())
    print("empty window drew", len(e.drawn), "eligible", len(e.eligible))
except Exception as ex:
    print("empty window error", type(ex).__name__, ex)
# tampering detection
import dataclasses
t = d1.model_copy(update={"drawn": d1.drawn[:-1]})
print("tampered verify:", sampler.verify_draw(t, loans, []))
# inclusion probability over 4 weekly draws, by sale date, over many seeds
inc = defaultdict(int); R = 400
for seed in range(R):
    taken = set()
    for a in DEMO_DRAWS:
        d = sampler.draw(loans, meta, a, 20, seed, taken)
        taken |= {x.loan_id for x in d.drawn}
    for i in taken: inc[i] += 1
byweek = defaultdict(list)
for l in loans:
    byweek[l.sold_on.isoformat()[:8] + ("1" if l.sold_on.day < 16 else "2")].append(inc[l.record.loan_id] / R)
for k in sorted(byweek):
    v = byweek[k]; print(f"  sold {k}: n={len(v)} mean inclusion {sum(v)/len(v):.2f} min {min(v):.2f} max {max(v):.2f}")
never = [l for l in loans if inc[l.record.loan_id] == 0]
print("never eligible:", len(never), "sold", min(l.sold_on for l in never), "..", max(l.sold_on for l in never))
