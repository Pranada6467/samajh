"""Builder probe (not evidence): one-clause replies through the real extraction model.

    uv run python eval/text_path/one_clause_probe.py [--cap 0.05]

P3a round 4 gives a one-clause reply that holds a marker word the change check. Each case swaps ONE
reply of the iter1 informed BASE call (`references/reviews/iter1/probes/extractor_attacks.py`;
record: credit-life insurance, premium 41,300 from the loan, not required) and runs
`samajh.pipeline.run_text` with the default model through `samajh/clients/llm.py` (cache first).
Cases 1-11 are the iter2 verifier's unpunctuated replies (`references/reviews/iter2/probes/
p3a_r3_llm.py`); the rest were written by the builder, gold before the first run. Typed text only.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "references" / "reviews" / "iter1" / "probes"))
import extractor_attacks as ea

from samajh.clients.llm import LlmClient
from samajh.extract._ground import Reply
from samajh.pipeline import WithoutTemperature, run_text, takes_temperature

C, R, I, U = "clear", "refer", "incomplete", "understanding_gap"
NOT_CLEAR = {R, I, U}
FIELD = {"kind": "kind", "payment_source": "payment_source", "required_for_loan": "required_for_loan",
         "features": "feature_probe"}  # fmt: skip

# (group, asks (None: open recall), reply, wanted tiers, forbidden stated value or None)
CASES = [
    # the verifier's unpunctuated replies
    ("withdraw", "kind", "बीमा है नहीं पता नहीं क्या है", NOT_CLEAR, "insurance"),
    ("withdraw", "kind", "insurance hai nahi pata nahi", NOT_CLEAR, "insurance"),
    ("withdraw", "payment_source", "लोन से कटा था नहीं याद नहीं", NOT_CLEAR, "from_loan"),
    ("withdraw", "kind", "बीमा है रुकिए मुझे पक्का नहीं पता", NOT_CLEAR, "insurance"),
    ("away", "kind", "बीमा है नहीं नहीं एफ़डी है", {R, I}, "insurance"),
    ("toward", "kind", "एफ़डी है नहीं बीमा है", {C, I}, None),
    ("away", "kind", "insurance hai matlab FD hai", {R, I}, "insurance"),
    ("away", "payment_source", "लोन से कटा नहीं नहीं अलग से नकद दिया था", {R, I}, "from_loan"),
    ("away", "required_for_loan", "नहीं ज़रूरी नहीं था अरे नहीं ज़रूरी बोला था", {R, I}, False),
    ("answer", "required_for_loan", "नहीं नहीं बिल्कुल ज़रूरी नहीं था", {C}, None),
    ("answer", "kind", "बीमा है जी बीमा ही है", {C}, None),
    # new: withdrawals
    ("withdraw", "kind", "पॉलिसी है शायद नहीं नहीं मुझे नहीं मालूम", NOT_CLEAR, "insurance"),
    ("withdraw", "kind", "FD hai nahi nahi pata nahi kya hai", NOT_CLEAR, "deposit"),
    ("withdraw", "payment_source", "loan se kata tha ruko yaad nahi aa raha", NOT_CLEAR, "from_loan"),
    ("withdraw", "required_for_loan", "हाँ ज़रूरी था अरे नहीं पता नहीं मुझे", NOT_CLEAR, True),
    ("withdraw", "payment_source", "अलग से दिया था नहीं मतलब याद नहीं", NOT_CLEAR, "separately"),
    ("withdraw", None, "बीमा लिया था नहीं नहीं कुछ नहीं लिया बस लोन", NOT_CLEAR, None),
    # new: corrections toward and away from the record value
    ("toward", "kind", "एफडी है अरे नहीं बीमा है बीमा", {C, I}, None),
    ("toward", "payment_source", "cash diya tha nahi nahi loan se kata tha", {C, I}, None),
    ("toward", "required_for_loan", "हाँ ज़रूरी था नहीं गलत बोला ज़रूरी नहीं था", {C, I}, None),
    ("away", "kind", "बीमा है sorry FD है", {R, I}, "insurance"),
    ("away", "payment_source", "लोन से कटा था नहीं मैंने अलग से दिया", {R, I}, "from_loan"),
    ("away", "required_for_loan", "optional tha nahi actually compulsory tha", {R, I}, False),
    # new: informed answers in which a "no" is the answer or part of it
    ("answer", "required_for_loan", "नहीं मर्ज़ी से लिया था", {C}, None),
    ("answer", "required_for_loan", "nahi zaroori nahi tha apni marzi se", {C}, None),
    ("answer", "features", "नहीं वापस नहीं मिलता", {C}, None),
    ("answer", "kind", "बीमा है एफडी नहीं", {C}, None),
    ("answer", "payment_source", "अलग से नहीं दिया लोन से कटा", {C}, None),
    ("answer", "kind", "sorry awaaz nahi aayi insurance hai", {C}, None),
    ("answer", "required_for_loan", "बिल्कुल नहीं ज़रूरी नहीं था", {C}, None),
    ("answer", "payment_source", "loan se hi kata tha alag se kuch nahi diya", {C}, None),
    ("answer", None, "एक बीमा लिया था और कुछ नहीं", {C}, None),
]


def rows_for(asks, reply):
    return [(r[0], r[1], r[2], reply, r[4]) if r[1] == asks and r[0] != "read_back" else r for r in ea.BASE]


def main() -> int:
    cap = float(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else 0.05
    client = LlmClient.from_env(usd_cap=cap)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    bad = 0
    for k, (group, asks, reply, want, forbidden) in enumerate(CASES, 1):
        transcript, _ = ea.build(rows_for(asks, reply))
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        tid = next(t.id for t in transcript.turns if t.text == reply)
        checks = [s.change or s.failed for s in run.extraction.slots if s.turn_id == tid and s.check]
        if asks is None:
            value = [i.kind.value for i in run.extraction.raw.recall.items]
            false_value = False
        else:
            answer = getattr(run.extraction.raw.products[0], FIELD[asks])
            value = f"{type(answer).__name__}({getattr(answer, 'value', getattr(answer, 'reason', ''))!s})"
            false_value = forbidden is not None and getattr(answer, "value", None) == forbidden
        ok = run.result.tier.value in want and not false_value
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {k:2} [{group:8}] {run.result.tier.value:17} check={checks} "
              f"{asks or 'recall'}={value} clauses={len(Reply(reply).clauses())} | {reply}")  # fmt: skip
    print(f"\n{len(CASES)} cases, {bad} outside gold; spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
