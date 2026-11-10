"""Judge probe: run the text pipeline on a transcript the judge typed into the terminal player.

Usage: uv run python references/reviews/iter1/judge-probes/judge_run_text.py RECORD.json TRANSCRIPT.json
Makes OpenRouter calls through samajh.pipeline.default_llm() (about 0.002 USD per transcript).
"""

import json
import sys
from pathlib import Path

from samajh.pipeline import default_llm, run_text
from samajh.types import LoanRecord, Transcript

record = LoanRecord.model_validate_json(Path(sys.argv[1]).read_text())
transcript = Transcript.model_validate_json(Path(sys.argv[2]).read_text())
if transcript.loan_id != record.loan_id:  # the player stamps the fixture's loan id
    transcript = transcript.model_copy(update={"loan_id": record.loan_id})
run = run_text(transcript, record, default_llm())
res = run.result
print("VERDICT:", res.verdict.value)
for p in res.products:
    print(" product", p.product_id, p.verdict.value, "| passed:", [r.value for r in p.passed])
    for f in p.flags:
        print("   FLAG", f.rule_id.value, f.clause, f.severity.value, "| expected:", f.expected, "| heard:", f.heard, "| quote:", f.quote)
    for g in p.gaps:
        print("   GAP ", g.rule_id.value, g.reason.value, "| quote:", g.quote)
    print("   evidence pack:", p.evidence_pack is not None)
for f in res.case_flags:
    print(" CASE FLAG", f.rule_id.value, f.severity.value, "| heard:", f.heard, "| quote:", f.quote)
for g in res.case_gaps:
    print(" CASE GAP", g.rule_id.value, g.reason.value, g.quote)
print(" unmatched recall:", [(i.kind, i.amount_inr, i.evidence.quote) for i in res.unmatched_recall])
slots = run.extraction.slots
print(f" LLM requests: {len(slots)}, usd: {sum(s.usd for s in slots):.5f}, seconds if run one after another: {sum(s.seconds for s in slots):.0f}")
