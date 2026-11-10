"""P3a re-verification (round 3): fresh retraction replies through the real extraction model.

    uv run python references/reviews/iter2/probes/p3a_r3_llm.py [--cap 0.25]

Each case swaps ONE reply of the iter1 informed BASE call (record: credit-life insurance, premium
41,300 from the loan, not required, cover 3,50,000) and runs `samajh.pipeline.run_text` with
openai/gpt-6-luna through samajh/clients/llm.py (cache first). Gold was written before the first run.

Groups:
  noise    informed answer with emphasis / filler / apology / restatement -> must be clear
  toward   a wrong answer corrected to the record value -> clear, earlier words in `also`
  away     a right answer corrected to a wrong value -> refer (never clear)
  withdraw an answer withdrawn with nothing in its place -> not clear, value not stated
  nopunct  speech-to-text style, no punctuation (one clause): shows what one-clause replies do
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.extract._ground import Reply  # noqa: E402
from samajh.pipeline import WithoutTemperature, run_text, takes_temperature  # noqa: E402

C, R, I = "clear", "refer", "incomplete"
NOT_CLEAR = {"refer", "incomplete", "understanding_gap"}
FIELD = {"kind": "kind", "payment_source": "payment_source", "required_for_loan": "required_for_loan",
         "premium": "premium_inr"}

# (group, asks, reply, wanted tiers, forbidden stated value or None, premium read-back text or None)
CASES = [
    # --- noise: informed customer, must end clear ---
    ("noise", "kind", "बीमा है जी, बीमा, हाँ हाँ बीमा ही है।", {C}, None, None),
    ("noise", "kind", "देखिए, वो बीमा है, मतलब लाइफ़ वाला।", {C}, None, None),
    ("noise", "kind", "हैलो? हाँ, सुनाई दिया, बीमा है।", {C}, None, None),
    ("noise", "kind", "insurance hai, haan ji, pakka insurance.", {C}, None, None),
    ("noise", "kind", "sorry, aawaz kat gayi thi, insurance hai.", {C}, None, None),
    ("noise", "kind", "अरे, एक सेकंड, हाँ, बीमा है वो।", {C}, None, None),
    ("noise", "payment_source", "लोन से ही कटा, नहीं नहीं, अलग से कुछ नहीं दिया।", {C}, None, None),
    ("noise", "payment_source", "loan amount se hi kata tha, maaf kijiye, line kharab hai.", {C}, None, None),
    ("noise", "payment_source", "जी, वो लोन में से काट लिया था, लोन में से।", {C}, None, None),
    ("noise", "required_for_loan", "नहीं जी, बिल्कुल ज़रूरी नहीं था, बिल्कुल नहीं।", {C}, None, None),
    ("noise", "required_for_loan", "nahi nahi, zaroori nahi tha, apni marzi se liya.", {C}, None, None),
    ("noise", "required_for_loan", "नहीं, ज़रूरी नहीं था, सॉरी, बच्चा रो रहा है।", {C}, None, None),
    ("noise", "required_for_loan", "उम्म, नहीं, ज़रूरी तो नहीं था, मैंने खुद लिया।", {C}, None, None),
    ("noise", "premium", "इकतालीस हज़ार तीन सौ, हाँ, इकतालीस हज़ार तीन सौ ही।", {C}, None, None),
    ("noise", "premium", "matlab, iktalis hazaar teen sau rupaye, sorry line pe disturbance hai.", {C}, None, None),
    ("noise", "kind", "बीमा है, कोई एफ़डी वगैरह नहीं, बस बीमा।", {C}, None, None),
    # --- toward the record: clear with also ---
    ("toward", "kind", "एफ़डी, अरे रुको, नहीं, बीमा है।", {C}, None, None),
    ("toward", "kind", "FD hai, I mean, insurance hai.", {C}, None, None),
    ("toward", "kind", "जमा योजना, मतलब नहीं, बीमा है बीमा।", {C}, None, None),
    ("toward", "payment_source", "अलग से नकद दिया था, ओह नहीं, लोन से कटा था।", {C}, None, None),
    ("toward", "payment_source", "cash diya tha, nahi galat bola, loan se kata.", {C}, None, None),
    ("toward", "required_for_loan", "हाँ ज़रूरी था, नहीं, गलत बोल गया, ज़रूरी नहीं था।", {C}, None, None),
    ("toward", "required_for_loan", "haan zaroori tha, ruko, nahi, optional tha.", {C}, None, None),
    ("toward", "premium", "पैंतालीस हज़ार, नहीं, इकतालीस हज़ार तीन सौ।", {C}, None, None),
    ("toward", "kind", "एफ़डी है, नहीं बीमा, हाँ बीमा ही।", {C}, None, None),
    # --- away from the record: refer, never clear ---
    ("away", "kind", "बीमा है, अरे नहीं, एफ़डी है।", {R}, "insurance", None),
    ("away", "kind", "insurance, I mean FD hai.", {R}, "insurance", None),
    ("away", "kind", "बीमा, रुकिए, ग़लत बोला, एफ़डी करवाई थी।", {R}, "insurance", None),
    ("away", "kind", "बीमा है, नहीं, एफ़डी, नहीं नहीं, बीमा... नहीं, एफ़डी ही है।", {R}, "insurance", None),
    ("away", "payment_source", "लोन से कटा, नहीं, मैंने अलग से नकद दिया था।", {R}, "from_loan", None),
    ("away", "payment_source", "loan se kata tha, matlab nahi, alag se UPI kiya tha.", {R}, "from_loan", None),
    ("away", "required_for_loan", "नहीं, ज़रूरी नहीं था, अरे नहीं, ज़रूरी बोला था उन्होंने।", {R}, False, None),
    ("away", "required_for_loan", "optional tha, sorry, nahi, compulsory bola tha.", {R}, False, None),
    ("away", "required_for_loan", "नहीं ज़रूरी, रुको, हाँ ज़रूरी था वो लोन के लिए।", {R}, False, None),
    ("away", "kind", "बीमा, ओह, सॉरी, एफ़डी।", {R}, "insurance", None),
    ("away", "premium", "इकतालीस हज़ार तीन सौ, नहीं, इक्यावन हज़ार तीन सौ।", {R, I}, 41300,
     "इक्यावन हज़ार तीन सौ, यानी 51,300 रुपये, सही है?"),
    # --- withdrawn: not clear, value not stated ---
    ("withdraw", "kind", "बीमा है, नहीं, पता नहीं असल में क्या है।", NOT_CLEAR, "insurance", None),
    ("withdraw", "kind", "insurance hai, nahi nahi, pakka nahi pata.", NOT_CLEAR, "insurance", None),
    ("withdraw", "payment_source", "लोन से कटा था, नहीं, याद नहीं कैसे दिया।", NOT_CLEAR, "from_loan", None),
    ("withdraw", "required_for_loan", "ज़रूरी नहीं था, रुकिए, मुझे नहीं पता था।", NOT_CLEAR, False, None),
    ("withdraw", "premium", "इकतालीस हज़ार तीन सौ, नहीं, ठीक से याद नहीं कितना।", NOT_CLEAR, 41300, None),
    # --- no punctuation: one clause; the change check never runs ---
    ("nopunct", "kind", "बीमा है नहीं नहीं एफ़डी है", {R}, "insurance", None),
    ("nopunct", "kind", "एफ़डी है नहीं बीमा है", {C}, None, None),
    ("nopunct", "kind", "insurance hai matlab FD hai", {R}, "insurance", None),
    ("nopunct", "payment_source", "लोन से कटा नहीं नहीं अलग से नकद दिया था", {R}, "from_loan", None),
    ("nopunct", "required_for_loan", "नहीं ज़रूरी नहीं था अरे नहीं ज़रूरी बोला था", {R}, False, None),
    ("nopunct", "kind", "बीमा है नहीं पता नहीं क्या है", NOT_CLEAR, "insurance", None),
    ("nopunct", "required_for_loan", "नहीं नहीं बिल्कुल ज़रूरी नहीं था", {C}, None, None),
    ("nopunct", "kind", "बीमा है जी बीमा ही है", {C}, None, None),
]


def rows_for(asks, reply, readback):
    rows = []
    for row in ea.BASE:
        if row[1] == asks and row[0] != "read_back":
            row = (row[0], row[1], row[2], reply, row[4])
        if readback and row[0] == "read_back":
            row = (row[0], row[1], readback, row[3], row[4])
        rows.append(row)
    return rows


def main() -> int:
    cap = float(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else 0.25
    client = LlmClient.from_env(usd_cap=cap)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    bad = 0
    for group, asks, reply, want, forbidden, readback in CASES:
        transcript, _ = ea.build(rows_for(asks, reply, readback))
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        res = run.result
        belief = getattr(run.beliefs.products[0], FIELD[asks])
        bval = getattr(belief, "value", None)
        btype = type(belief).__name__
        false_value = forbidden is not None and btype == "Stated" and bval == forbidden
        ok = res.tier.value in want and not false_value
        bad += not ok
        tid = next(t.id for t in transcript.turns if t.text == reply)
        checks = [s.change for s in run.extraction.slots if s.turn_id == tid and s.check]
        also = [e.quote for e in getattr(belief, "also", ()) if e.turn_id == tid]
        reasons = sorted({f"{f.reason.value}" for f in res.all_flags()}
                         | {f"gap:{g.rule_id.value}:{g.reason.value}" for g in res.all_gaps()})
        notes = [n.answers[0].quote for n in res.products[0].self_corrections] if hasattr(
            res.products[0], "self_corrections") else []
        print(f"{'ok ' if ok else 'BAD'} [{group:8}] {res.tier.value:17} want {sorted(want)} | {asks}: {reply}\n"
              f"      clauses={len(Reply(reply).clauses())} check={checks} belief={btype}({bval!r})"
              f" also={also} notes={notes}{' FALSE-VALUE' if false_value else ''}\n      {reasons}")
    print(f"\n{len(CASES)} cases, {bad} outside gold; spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
