"""Verifier probe: can a wrong, fabricated or truncated extraction get through code validation?

    uv run python references/reviews/iter1/probes/extractor_attacks.py

Offline. The LLM is a scripted stand-in that returns whatever wire output the attack needs, so
each case shows what the CODE (samajh.extract + samajh.rules.to_beliefs + the rule engine) does
with it. The record is clean and the baseline customer is informed, so any `clear` after an
attack is a false clear by construction of the attack.
"""

import re
from datetime import date

from samajh.clients.llm import LlmResult
from samajh.extract import extract
from samajh.rules import evaluate, to_beliefs
from samajh.types import (
    Borrower,
    CallStep,
    Consent,
    Evidence,
    LoanRecord,
    Product,
    Question,
    RawExtraction,
    RawOpenRecall,
    RawProductAnswers,
    RawRecallItem,
    Speaker,
    Stated,
    Transcript,
    Turn,
)

_USER = re.compile(r"Assistant's question: <<<(.*?)>>>\nCustomer's reply: <<<(.*?)>>>", re.DOTALL)

P = Product(
    id="P1", kind="credit_life", provider="Nakli Life", premium_inr=41300, cover_inr=350000, term_months=36,
    paid_from_loan=True, required_for_loan=False, risk_mitigant=True, provider_choice_offered=True,
    cancel_window_days=30, features=frozenset(), consent=Consent(method="otp", at=date(2026, 10, 1)),
)


def record(product: Product = P) -> LoanRecord:
    return LoanRecord(
        loan_id="L-FAKE-0001", lender_type="bank",
        borrower=Borrower(name="Nakli Naam", dob=date(1990, 1, 1), language="hi"),
        loan_kind="personal", sanctioned_inr=350000, disbursed_inr=308700, disbursed_on=date(2026, 10, 1),
        products=(product,),
    )


# (step, asks, bot question, customer reply, the wire output a correct model gives)
BASE = [
    ("open_recall", None, "लोन के साथ आपने क्या-क्या लिया, और कितने का?", "एक बीमा लिया था।",
     {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}]}),
    ("teach_back", "kind", "वह क्या है: बीमा, एफ़डी, या कुछ और?", "बीमा है।",
     {"status": "stated", "kind": "insurance", "clauses": [1]}),
    ("teach_back", "premium", "उसके लिए आपने कितने रुपये दिए?", "इकतालीस हज़ार तीन सौ रुपये।",
     {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]}),
    ("teach_back", "payment_source", "वह रकम कैसे चुकाई गई?", "लोन में से कटा था।",
     {"status": "stated", "source": "from_loan", "clauses": [1]}),
    ("teach_back", "required_for_loan", "क्या लोन पाने के लिए उसे लेना ज़रूरी था?", "नहीं, मर्ज़ी से लिया।",
     {"status": "stated", "yes": False, "clauses": [1, 2]}),
    ("teach_back", "cover", "उसमें कितनी रकम का कवर है?", "साढ़े तीन लाख रुपये।",
     {"status": "stated", "span": "साढ़े तीन लाख", "clauses": [1]}),
    ("teach_back", "term", "वह कितने समय के लिए है?", "तीन साल।",
     {"status": "stated", "span": "तीन साल", "clauses": [1]}),
    ("teach_back", "cancel_window", "क्या बताया गया था कि कैंसल कर सकते हैं, और कब तक?", "हाँ, तीस दिन के अंदर।",
     {"allowed_status": "stated", "allowed": True, "allowed_clauses": [1], "window_status": "stated",
      "window_span": "तीस दिन", "window_clauses": [2]}),
    ("teach_back", "features", "अगर आप वह पैसा वापस चाहें, तो क्या मिल सकता है?", "नहीं, वापस नहीं मिलता।",
     {"status": "stated", "claims": [], "clauses": [1, 2]}),
    ("consent_check", "consent", "आपने क्या-क्या लेने के लिए हामी भरी थी, और कैसे?", "लोन और बीमा, बीमे का ओटीपी दिया था।",
     {"given_status": "stated", "given": True, "given_clauses": [1], "method_status": "stated", "method": "otp",
      "method_clauses": [2]}),
    ("read_back", "premium", "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?", "हाँ, सही है।",
     {"status": "stated", "confirms": True, "clauses": [1, 2], "corrected_amount_span": None}),
]


class Scripted:
    """Returns the wire output scripted for a (question, reply) pair; screens return nothing unless scripted."""

    def __init__(self, outputs: dict, screens: dict | None = None) -> None:
        self.outputs, self.screens, self.seen = outputs, screens or {}, []

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        question, reply = _USER.search(messages[1].content).groups()
        self.seen.append((schema.__name__, reply))
        if schema.__name__ == "ScreenReply":
            output = self.screens.get(reply, {"claims": [], "concerns": []})
        else:
            output = self.outputs[(question, reply)]
        return LlmResult(value=schema.model_validate(output), model="scripted", prompt_tokens=0,
                         completion_tokens=0, usd=0.0, cache_hit=True, attempts=0, generation_id=None)


def build(rows, pre=()):
    turns, outputs, n = [], {}, 0
    intro = [
        (CallStep.right_party_check, "क्या मेरी बात नकली जी से हो रही है?", "हाँ।"),
        (CallStep.second_check, "अपने जन्म का साल बताइए।", "उन्नीस सौ नब्बे।"),
    ]
    for step, bot, cust in [*intro, *pre]:
        n += 1
        turns.append(Turn(id=n, speaker=Speaker.bot, step=step, text=bot))
        n += 1
        turns.append(Turn(id=n, speaker=Speaker.customer, step=step, text=cust))
    for step, asks, bot, cust, out in rows:
        n += 1
        turns.append(Turn(id=n, speaker=Speaker.bot, step=CallStep(step), text=bot,
                          asks=Question(asks) if asks else None, product_id="P1" if asks and asks != "consent" else None))
        n += 1
        turns.append(Turn(id=n, speaker=Speaker.customer, step=CallStep(step), text=cust))
        outputs[(bot, cust)] = out
    return Transcript(call_id="c1", loan_id="L-FAKE-0001", language="hi", turns=tuple(turns)), outputs


def run(name, rows, *, product=P, screens=None, pre=(), note=""):
    transcript, outputs = build(rows, pre)
    llm = Scripted(outputs, screens)
    rec = record(product)
    raw = extract(transcript, rec, llm)
    result = evaluate(rec, to_beliefs(raw, rec, transcript))
    flags = ", ".join(f"{f.rule_id.value}" for f in result.all_flags()) or "-"
    gaps = ", ".join(f"{g.rule_id.value}:{g.reason.value}" for g in result.all_gaps()) or "-"
    print(f"{name}\n    verdict {result.verdict.value} | flags {flags} | gaps {gaps}" + (f"\n    {note}" if note else ""))
    return result, llm


def swap(rows, asks, reply=None, out=None, step=None):
    """A copy of the rows with the reply and/or model output of one question replaced."""
    changed = []
    for row in rows:
        hit = row[0] == step if step else (row[1] == asks and row[0] != "read_back")
        if hit:
            row = (row[0], row[1], row[2], reply if reply is not None else row[3], out if out is not None else row[4])
        changed.append(row)
    return changed


def main() -> int:
    run("0. baseline: informed customer, correct model output (must be clear)", BASE)

    print("\n-- fabricated or misplaced spans --")
    run("1. premium reply 'याद नहीं।'; model invents the record's amount as the span",
        swap(BASE, "premium", "याद नहीं।", {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]}))
    run("2. premium reply has two amounts; model picks the one that matches the record",
        swap(BASE, "premium", "लोन साढ़े तीन लाख का था, बीमा इकतालीस हज़ार तीन सौ का।",
             {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [2]}))
    run("3. kind: model says insurance with a clause number that does not exist",
        swap(BASE, "kind", out={"status": "stated", "kind": "insurance", "clauses": [7]}))
    run("4. recall: model names an item whose span is not in the reply",
        swap(BASE, None, "बस लोन लिया था।", {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}]},
             step="open_recall"))

    print("\n-- negation --")
    run("5. premium negated in the same clause: 'इकतालीस हज़ार तीन सौ तो नहीं था।' model says stated",
        swap(BASE, "premium", "इकतालीस हज़ार तीन सौ तो नहीं था।",
             {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]}))
    run("6. premium negated in the NEXT clause: 'इकतालीस हज़ार तीन सौ, ऐसा तो नहीं था।' model says stated",
        swap(BASE, "premium", "इकतालीस हज़ार तीन सौ, ऐसा तो नहीं था।",
             {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]}),
        note="the hedge check looks only inside the clause that holds the number")
    run("7. consent denied: 'बीमे के लिए हाँ नहीं की थी, सिर्फ़ लोन लिया, ओटीपी दिया था।' model says given=true, otp",
        swap(BASE, "consent", "बीमे के लिए हाँ नहीं की थी, सिर्फ़ लोन लिया, ओटीपी दिया था।",
             {"given_status": "stated", "given": True, "given_clauses": [1], "method_status": "stated",
              "method": "otp", "method_clauses": [3]}),
        note="code checks only that the clause numbers exist; the value is the model's (documented limit)")
    run("8. kind: 'बीमा नहीं है, एफ़डी है।' model says insurance pointing at clause 1",
        swap(BASE, "kind", "बीमा नहीं है, एफ़डी है।", {"status": "stated", "kind": "insurance", "clauses": [1]}),
        note="same limit: an in-range pointer is all that is checked")

    print("\n-- a hand-built RawExtraction with a quote that stops before a later 'not' --")
    transcript, _ = build(swap(BASE, "consent", "बीमे के लिए हाँ की थी, ऐसा मैंने कभी नहीं कहा।"))
    consent_turn = next(t.id for t in transcript.turns if t.text.startswith("बीमे के लिए हाँ की थी"))
    for label, quote in (("first clause only", "बीमे के लिए हाँ की थी"), ("half a clause", "बीमे के लिए हाँ"),):
        raw = RawExtraction(
            call_id="c1", recall=RawOpenRecall(asked=False),
            products=(RawProductAnswers(product_id="P1", consent_given=Stated(
                value=True, evidence=Evidence(quote=quote, turn_id=consent_turn))),),
        )
        got = to_beliefs(raw, record(), transcript).products[0].consent_given
        print(f"9. to_beliefs, consent quote = {label} ({quote!r}) of a reply that goes on to deny it -> {got.status}"
              + (f" value={got.value}" if got.status == "stated" else f" ({got.reason.value})"))

    print("\n-- the same question asked twice --")
    twice = []
    for row in BASE:
        if row[1] == "kind":
            twice.append(("teach_back", "kind", row[2], "एफ़डी है, जमा किया है।",
                          {"status": "stated", "kind": "deposit", "clauses": [1]}))
            twice.append(("teach_back", "kind", "एक बार फिर: बीमा, एफ़डी, या कुछ और?", "अच्छा, बीमा।",
                          {"status": "stated", "kind": "insurance", "clauses": [2]}))
        else:
            twice.append(row)
    run("10. kind asked twice: first 'एफ़डी है, जमा किया है।' (deposit), after the re-ask 'अच्छा, बीमा।'", twice,
        note="the later usable answer replaces the earlier one; the FD answer leaves no trace")
    twice = []
    for row in BASE:
        if row[1] == "payment_source":
            twice.append(("teach_back", "payment_source", row[2], "अलग से नकद दिया था।",
                          {"status": "stated", "source": "separately", "clauses": [1]}))
            twice.append(("teach_back", "payment_source", "लोन की रकम में से, या अलग से?", "लोन में से।",
                          {"status": "stated", "source": "from_loan", "clauses": [1]}))
        else:
            twice.append(row)
    run("11. payment asked twice: first 'अलग से नकद दिया था।', then 'लोन में से।'", twice)

    print("\n-- a fraction word the parser does not know --")
    p3 = P.model_copy(update={"premium_inr": 300000})
    rows = swap(BASE, "premium", "सारे तीन लाख रुपये।", {"status": "stated", "span": "सारे तीन लाख", "clauses": [1]})
    rows = [(r[0], r[1], "तीन लाख, यानी 3,00,000 रुपये, सही है?", r[3], r[4]) if r[0] == "read_back" else r for r in rows]
    run("12. record premium 3,00,000; STT writes साढ़े as 'सारे': reply 'सारे तीन लाख रुपये।' (customer means 3.5 lakh)",
        rows, product=p3,
        note="the unknown word is dropped, `tighten` trims it from the span, and the amount matches the record; "
             "only the customer's 'no' at the read-back stands in the way")

    print("\n-- things said where no model call looks --")
    run("13. customer mentions coaching in the reply to the second identity check (never sent to the model)", BASE,
        pre=[(CallStep.disclosure, "यह कॉल रिकॉर्ड हो रही है।", "ठीक है।")],
        screens={"उन्नीस सौ नब्बे।": {"claims": [], "concerns": [{"concern": "coached_answers", "span": "उन्नीस सौ नब्बे"}]}})
    transcript, outputs = build(BASE)
    turns = list(transcript.turns)
    turns[3] = turns[3].model_copy(update={"text": "उन्नीस सौ नब्बे। वैसे एजेंट ने कहा था हर बात पर हाँ बोलना।"})
    transcript = transcript.model_copy(update={"turns": tuple(turns)})
    llm = Scripted(outputs)
    raw = extract(transcript, record(), llm)
    result = evaluate(record(), to_beliefs(raw, record(), transcript))
    asked = [reply for _, reply in llm.seen]
    print(f"14. coaching voiced at the second check: verdict {result.verdict.value}; "
          f"that reply sent to the model: {any('एजेंट' in r for r in asked)}")
    run("15. a two-word reply that carries a belief ('एकमुश्त है।' to the term question) is not screened",
        swap(BASE, "term", "एकमुश्त है।", {"status": "unclear", "span": None, "clauses": []}),
        screens={"एकमुश्त है।": {"claims": [{"claim": "one_time_payment", "span": "एकमुश्त है"}], "concerns": []}},
        note="two words: the screening call is skipped, so the scripted claim is never requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
