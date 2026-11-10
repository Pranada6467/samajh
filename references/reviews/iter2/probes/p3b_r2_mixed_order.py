"""P3b round 2: a phone attempt ingested first, then the simulated calls of the same draw run.
Usage: uv run python p3b_r2_mixed_order.py <copy of the state written by p3b_r2_ingest.py>"""
import sys
from collections import Counter
from pathlib import Path
from samajh.ops import book as books
from samajh.ops.batch import load_batch
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore

store = OpsStore(Path(sys.argv[1]) / "ops")
_, _, customers = books.generate_book(85)
cust = {c.loan_id: c for c in customers}
for d in store.draws()[6:]:
    run_draw(store, d, cust, scripted_analysis)
batch = load_batch(store)
for s in batch.sampled:
    nums = Counter(a.number for a in s.attempts)
    if any(v > 1 for v in nums.values()) or any(a.source.kind == "phone_session" for a in s.attempts):
        print(s.drawn.loan_id, s.status.value, [(a.number, a.day_since_sale, a.outcome.value, a.source.kind) for a in s.attempts])
