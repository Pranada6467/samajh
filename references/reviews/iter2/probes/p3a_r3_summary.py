"""P3a re-verification (round 3): summary wording (addition C), scripted model, offline.

    uv run python references/reviews/iter2/probes/p3a_r3_summary.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402
from p3a_r3_orders import Scripted  # noqa: E402

from samajh.extract import extract  # noqa: E402
from samajh.rules import evaluate, summarise, to_beliefs  # noqa: E402
from samajh.rules.summary import call_ended_label  # noqa: E402


def show(name, rows, product=ea.P):
    transcript, outputs = ea.build(rows)
    rec = ea.record(product)
    res = evaluate(rec, to_beliefs(extract(transcript, rec, Scripted(outputs)), rec, transcript))
    s = summarise(rec, res)
    print(f"--- {name}: result tier {res.tier.value}, summary tier {s.tier.value}")
    for line in s.lines:
        print(f"   [{line.tier.value}] {line.model_dump(exclude={'tier'})}")


stop = [r for r in ea.BASE if r[1] not in ("cover", "term", "cancel_window", "features", "consent")
        and r[0] != "read_back"]
show("A. call stopped after the payment question (cover, term, cancel, features, consent, read-back never asked)",
     stop)
dk = [(r[0], r[1], r[2], "पता नहीं।", {"status": "dont_know", "span": None, "clauses": [1]}) if r[1] == "cover"
      else r for r in ea.BASE]
show("B. cover asked, customer: 'पता नहीं।'", dk)
show("C. consent missing on the record (record-only flag)", ea.BASE, ea.P.model_copy(update={"consent": None}))
show("D. not a risk mitigant and no provider choice on record", ea.BASE,
     ea.P.model_copy(update={"risk_mitigant": False, "provider_choice_offered": False, "required_for_loan": True}))
for o in (None, "", "in_progress", "completed", "declined", "some_new_outcome"):
    print(f"call_ended_label({o!r}) -> {call_ended_label(o)!r}")
show("E. as D, but the required question and the consent question were never asked",
     [r for r in ea.BASE if r[1] not in ("required_for_loan", "consent")],
     ea.P.model_copy(update={"risk_mitigant": False, "provider_choice_offered": False, "required_for_loan": True,
                             "consent": None}))
