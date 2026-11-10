"""P3a re-verification (round 3), second batch: unpunctuated replies, A->B->A, read-back changes.

    uv run python references/reviews/iter2/probes/p3a_r3_llm2.py

Same harness as p3a_r3_llm.py (real gpt-6-luna, cache first). Gold written before the run.
`readback` swaps the reply to the premium read-back (41,300) instead of a teach-back reply.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p3a_r3_llm as base  # noqa: E402

C, R, I, NC = "clear", "refer", "incomplete", base.NOT_CLEAR
base.FIELD["readback"] = "premium_readback"
CASES = [
    ("nopunct", "kind", "इंश्योरेंस है नहीं नहीं पक्का नहीं पता", NC, "insurance", None),
    ("nopunct", "payment_source", "लोन से कटा था नहीं याद नहीं", NC, "from_loan", None),
    ("nopunct", "required_for_loan", "ज़रूरी नहीं था रुकिए पता नहीं", NC, False, None),
    ("nopunct", "kind", "insurance hai nahi pata nahi", NC, "insurance", None),
    ("nopunct", "kind", "FD hai nahi nahi insurance hai", {C}, None, None),
    ("nopunct", "payment_source", "cash diya tha nahi loan se kata tha", {C}, None, None),
    ("nopunct", "kind", "बीमा है अरे नहीं एफडी है", {R}, "insurance", None),
    ("nopunct", "payment_source", "loan se kata nahi galat bola alag se diya", {R}, "from_loan", None),
    ("nopunct", "kind", "insurance I mean FD", {R}, "insurance", None),
    ("nopunct", "premium", "इकतालीस हज़ार तीन सौ नहीं नहीं पता नहीं कितना", NC, 41300, None),
    ("aba", "kind", "बीमा, नहीं एफ़डी, अरे नहीं, बीमा ही है।", {C}, None, None),
    ("aba", "payment_source", "लोन से, नहीं, अलग से, नहीं नहीं, लोन से ही कटा।", {C}, None, None),
    ("aba", "kind", "एफ़डी, नहीं बीमा, नहीं नहीं, एफ़डी है।", {R}, "insurance", None),
    ("readback", "readback", "हाँ, सही है, अरे नहीं, गलत है।", {I}, True, None),
    ("readback", "readback", "हाँ सही है नहीं गलत है", {I}, True, None),
    ("readback", "readback", "नहीं, गलत, अरे नहीं, सही है।", {C, I}, None, None),
    ("noise", "premium", "जी, इकतालीस हज़ार तीन सौ रुपये, सॉरी, नेटवर्क चला गया था।", {C}, None, None),
    ("noise", "payment_source", "हाँ जी, मतलब, लोन में से ही गया था।", {C}, None, None),
]

_orig = base.rows_for


def rows_for(asks, reply, readback):
    if asks != "readback":
        return _orig(asks, reply, readback)
    return [(r[0], r[1], r[2], reply, r[4]) if r[0] == "read_back" else r for r in base.ea.BASE]


base.rows_for = rows_for
base.CASES = CASES

if __name__ == "__main__":
    sys.exit(base.main())
