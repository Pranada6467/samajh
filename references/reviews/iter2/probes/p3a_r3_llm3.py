"""P3a re-verification (round 3), third batch: more unpunctuated withdrawals, subtle punctuated changes.

    uv run python references/reviews/iter2/probes/p3a_r3_llm3.py

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
    ("subtle", "kind", "बीमा बोला था उन्होंने, पर असल में एफ़डी है।", {R}, "insurance", None),
    ("subtle", "kind", "पहले लगा बीमा है, बाद में पता चला एफ़डी है।", {R}, "insurance", None),
    ("subtle", "payment_source", "लोन से कटा, ऐसा उन्होंने कहा, पर मैंने तो अलग से भरा।", {R}, "from_loan", None),
    ("subtle", "kind", "बीमा... नहीं... एफ़डी।", {R}, "insurance", None),
    ("subtle", "kind", "बीमा है, या शायद एफ़डी, पक्का नहीं।", NC, "insurance", None),
    ("nopunct", "kind", "बीमा है ऐसा नहीं पता मुझे", NC, "insurance", None),
    ("nopunct", "payment_source", "loan se kata tha shayad nahi pata", NC, "from_loan", None),
    ("nopunct", "required_for_loan", "zaroori nahi tha nahi nahi mujhe nahi pata", NC, False, None),
    ("nopunct", "kind", "बीमा है रुकिए मुझे पक्का नहीं पता", NC, "insurance", None),
    ("nopunct", "payment_source", "लोन से कटा था नहीं नहीं मुझे नहीं मालूम", NC, "from_loan", None),
    ("nopunct", "kind", "insurance tha ruko nahi yaad nahi", NC, "insurance", None),
    ("nopunct", "payment_source", "लोन में से गया था पर पक्का नहीं याद नहीं", NC, "from_loan", None),
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

