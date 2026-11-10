"""Verifier probe: W9b's fixes R2, R6 and R7 (W9-dialogue-report.md section 5) against fresh replies.
R1/R3, R4, R9 and R10 are in dialogue_attack.py and dialogue_nine_gaps.py; R5 in the loops section;
R8 in dialogue_second_reading.py; R11 in dialogue_llm_fallback_live.py. Offline.

    uv run python references/reviews/iter1/probes/w9b_fixes_recheck.py
"""

from samajh.dialogue import EndOfCall, start, step
from samajh.dialogue.machine import AtBirthYear, AtReadBack, _say
from samajh.types import Language, LoanRecord


def record(dob: str) -> LoanRecord:
    return LoanRecord.model_validate({
        "loan_id": "LN-VERIFY-0006", "lender_type": "bank", "borrower": {"name": "Ramesh Namoona", "dob": dob, "language": "hi"},
        "loan_kind": "gold", "sanctioned_inr": 500000, "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
        "products": [{"id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
                      "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
                      "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30,
                      "features": [], "consent": None}]})  # fmt: skip


def where(state, said):
    return f"ended:{said.outcome.value}" if isinstance(said, EndOfCall) else state.position.at


print("R2: replies that give no year, to borrowers whose year ends in a number those replies hold")
for dob, replies in {
    "2002-01-01": ["दो मिनट रुकिए", "two seconds please", "दो बार पूछ चुके हो"],
    "2003-01-01": ["तीन बार बता चुका हूँ", "three"],
    "2010-01-01": ["दस मिनट बाद बताता हूँ", "ten minutes please", "दस"],
    "2011-01-01": ["ग्यारह बजे फ़ोन करना", "मेरे ग्यारह बच्चे हैं"],
    "1990-01-01": ["नब्बे परसेंट याद नहीं", "मेरी उम्र छत्तीस है, नब्बे में तो नहीं"],
    "1984-01-01": ["चौरासी लाख का लोन था", "मेरा नंबर 98201 98412 है", "8 4"],
}.items():
    for text in replies:
        state, _ = start(record(dob), Language.hi, lender_name="Namoona Bank")
        state, _ = _say(state, AtBirthYear())
        after, said = step(state, text)
        passed = after.position.at == "recall"
        print(f"   born {dob[:4]}: {text!r} -> {'PASSED THE CHECK' if passed else where(after, said)}")

print("R6 / R7: fresh replies to the read-back of 52,000")
state, _ = start(record("1984-06-15"), Language.hi, lender_name="Namoona Bank")
state, _ = _say(state, AtReadBack(product=0, amount_inr=52000, read_backs=1))
for text, want in [
    ("अरे नहीं भाई, पचपन था", "restate or 55,000"), ("बावन नहीं, बयालीस", "restate or 42,000"),
    ("थोड़ा ज़्यादा था शायद", "restate"), ("पचास के आसपास", "restate or re-read"),
    ("हाँ लगभग इतना ही", "confirmed"), ("जी बिल्कुल", "confirmed"), ("हम्म", "re-read"),
    ("याद नहीं आ रहा अब", "recorded, not pressed"), ("मालूम नहीं जी, उन्होंने ही भरा था", "recorded, not pressed"),
    ("कौन सा बावन हज़ार?", "re-read or explain"), ("ये किस चीज़ का पैसा है?", "re-read or explain"),
    ("बावन हज़ार तो लोन की किस्त है", "not a plain yes"), ("नहीं नहीं, सही है", "confirmed"),
    ("गलत नहीं है", "confirmed"), ("सही नहीं है", "restate"),
]:
    after, said = step(state, text)
    lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
    print(f"   {text!r} (want: {want}) -> {where(after, said)}; unresolved {len(after.unresolved)}; bot: {lines[-1].text if not isinstance(said, EndOfCall) else lines[0].text}")
