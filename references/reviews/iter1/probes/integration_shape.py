"""Verifier probe: what an adapter between samajh.server's Dialogue protocol and samajh.dialogue meets.

    uv run python references/reviews/iter1/probes/integration_shape.py

Offline. Measures the length of each bot utterance against the server's 600-character limit, and
the number of customer turns a call can need against the server's 40-turn limit.
"""

from pydantic import ValidationError

from samajh.dialogue import EndOfCall, start, step
from samajh.server.app import MAX_TURNS
from samajh.server.dialogue import BotUtterance as ServerUtterance
from samajh.types import Language, LoanRecord

PRODUCT = {"id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
           "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
           "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30, "features": [],
           "consent": None}  # fmt: skip
TTS = {Language.hi: "hi-IN", Language.hi_en: "hi-en", Language.ta: "ta-IN", Language.kn: "kn-IN"}
YES = {Language.hi: "हाँ", Language.hi_en: "yes", Language.ta: "ஆமா", Language.kn: "ಹೌದು"}


def record(products: int, name: str = "Ramesh Namoona") -> LoanRecord:
    return LoanRecord.model_validate({
        "loan_id": "LN-VERIFY-0005", "lender_type": "bank",
        "borrower": {"name": name, "dob": "1984-06-15", "language": "hi"}, "loan_kind": "gold",
        "sanctioned_inr": 500000, "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
        "products": [PRODUCT | {"id": f"P{k + 1}"} for k in range(products)]})  # fmt: skip


print("== bot utterances longer than the server's BotUtterance.text limit (600 characters)")
for language in Language:
    for lender in ("Namoona Bank", "Namoona Small Finance Bank Limited"):
        state, said = start(record(1), language, lender_name=lender)
        longest = (len(said.text), said.lines[0].key)
        too_long = []
        for reply in [YES[language], YES[language], "1984"] + ["x"] * 40:
            if isinstance(said, EndOfCall):
                break
            state, said = step(state, reply)
            utterance = said.utterance if isinstance(said, EndOfCall) else said
            longest = max(longest, (len(utterance.text), utterance.lines[0].key))
            try:
                ServerUtterance(text=utterance.text, language=TTS[language])
            except ValidationError:
                too_long.append((utterance.lines[0].key, len(utterance.text), len(utterance.lines)))
        print(f"  [{language.value}] lender {lender!r}: longest {longest}; refused by the server type: {too_long}")

print(f"\n== customer turns a call can need, against the server's MAX_TURNS = {MAX_TURNS}")
for products in (0, 1, 2, 3):
    for name, reply in (("every reply unclear", "क्या?"), ("every reply an answer, premium stated", None)):
        state, said = start(record(products), Language.hi, lender_name="Namoona Bank")
        turns = 0
        script = iter(["हाँ", "हाँ", "1984"])
        while not isinstance(said, EndOfCall):
            if reply is None:
                asked = state.turns[-1]
                text = next(script, None) or ("बावन हज़ार" if asked.asks and asked.asks.value == "premium" and asked.step.value == "teach_back"
                                              else ("हाँ" if asked.step.value == "read_back" else "एक एफडी ली थी"))  # fmt: skip
            else:
                text = next(script, None) or reply
            state, said = step(state, text)
            turns += 1
        print(f"  {products} products, {name}: {turns} customer turns, {state.bot_turns} bot utterances, ended {said.outcome.value}"
              f"{'  <-- over the server limit' if turns > MAX_TURNS else ''}")  # fmt: skip
