"""Verifier probe: reproduce the nine gaps of W9-dialogue-report.md section 5 ("Proved and not fixed").

    uv run python references/reviews/iter1/probes/dialogue_nine_gaps.py

Offline. Gaps 8 and 9 are covered by dialogue_attack.py (false_declines, refusals).
"""

from samajh.dialogue import EndOfCall, start, step
from samajh.dialogue.lint import lint_line
from samajh.dialogue.machine import AtReadBack, AtTeachBack, _say
from samajh.types import Language, LoanRecord, Question

REC = LoanRecord.model_validate({
    "loan_id": "LN-VERIFY-0003", "lender_type": "bank",
    "borrower": {"name": "Ramesh Namoona", "dob": "1984-06-15", "language": "hi"},
    "loan_kind": "gold", "sanctioned_inr": 500000, "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
    "products": [{"id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
                  "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
                  "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30,
                  "features": [], "consent": None}]})  # fmt: skip


def run(replies, language=Language.hi, record=REC):
    state, said = start(record, language, lender_name="Namoona Bank")
    said_all = [line.text for line in said.lines]
    for reply in replies:
        state, said = step(state, reply)
        lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
        said_all += [line.text for line in lines]
    return state, said, said_all


def where(state, said):
    return said.outcome.value if isinstance(said, EndOfCall) else state.position.at


print("1. 'I am not Ramesh but 1984' at the second check")
for text in ["मैं रमेश नहीं हूँ पर 1984", "रमेश तो मेरा भाई है, 1984", "ये मेरा नंबर नहीं है वैसे, 1984"]:
    state, said, lines = run(["हाँ", "हाँ", text])
    print(f"   {text!r} -> {where(state, said)}; loan named: {any('लोन' in line for line in lines)}")

print("2. another name at the first question")
for text in ["मैं सुरेश बोल रहा हूँ", "जी सुरेश बोल रहा हूँ, रमेश नहीं" , "सुरेश हियर, बोलिए"]:
    state, said, lines = run([text])
    print(f"   {text!r} -> {where(state, said)}; lender named: {any('Namoona' in line for line in lines)}")

print("3. a yes plus another amount at the read-back")
state, _ = start(REC, Language.hi, lender_name="Namoona Bank")
state = state.model_copy(update={"premiums": ()})
state, said = _say(state, AtReadBack(product=0, amount_inr=52000, read_backs=1))
for text in ["हाँ सही है। और कवर पाँच लाख था", "हाँ, बावन हज़ार, लोन पाँच लाख का था", "जी हाँ सही, बीस हज़ार तो मैंने अलग से दिए थे"]:
    after, said2 = step(state, text)
    last = (said2.utterance.lines if isinstance(said2, EndOfCall) else said2.lines)[-1].text
    print(f"   {text!r} -> {where(after, said2)}; premium now {after.premium_of(0)}; bot: {last}")

print("4. 'no fifty five thousand' at the read-back")
for text in ["no fifty five thousand", "no, fifty five thousand", "नहीं पचपन हज़ार"]:
    after, said2 = step(state, text)
    last = (said2.utterance.lines if isinstance(said2, EndOfCall) else said2.lines)[-1].text
    print(f"   {text!r} -> {where(after, said2)}; bot: {last}")

print("5. 'paid nothing' / 'it was free' at the premium question")
state, _ = start(REC, Language.hi, lender_name="Namoona Bank")
state, _ = _say(state, AtTeachBack(product=0, question=Question.premium))
for text in ["कुछ नहीं दिया", "फ्री था", "एक पैसा नहीं लगा", "ज़ीरो"]:
    after, said2 = step(state, text)
    after2, said3 = step(after, text)
    print(f"   {text!r} -> {where(after, said2)} (reasked={getattr(after.position, 'reasked', None)}), then "
          f"{where(after2, said3)}, unresolved {[u.asks.value for u in after2.unresolved if u.asks]}")  # fmt: skip

print("6. the bot's words show a product is on the record, to a customer who said they took nothing")
state, said, lines = run(["हाँ", "हाँ", "1984", "कुछ नहीं लिया, बस लोन"])
print("   bot after 'I took nothing, only the loan':", [line.text for line in said.lines])
zero = LoanRecord.model_validate(REC.model_dump(mode="json") | {"products": []})
state, said, lines = run(["हाँ", "हाँ", "1984", "कुछ नहीं लिया, बस लोन"], record=zero)
print("   same reply, record with no product:    ", [line.text for line in said.lines])

print("7. lines the lint still passes (empty list = may be spoken)")
for text in ["एक मिनट और दीजिए प्लीज़", "आपको यह बात समझनी चाहिए", "आपके साथ ग़लत हुआ है", "यह कंपल्सरी नहीं था",
             "आप इसे तीस दिन में रद्द कर सकते हैं",
             # the verifier's own, on DESIGN.md section 11 and the secrets list
             "आपका बावन हज़ार कट चुका है", "यह सुरक्षा कवच आपके परिवार के लिए है", "अपनी माताजी का नाम बताइए",
             "अपना पूरा पता और पिन कोड बताइए", "आपके मोबाइल पर आया कोड बताइए", "जो छह अंकों का नंबर आया है वो बोलिए",
             "आरबीआई के नियम के तहत यह कॉल ज़रूरी है", "भारतीय रिज़र्व बैंक ने यह कॉल अनिवार्य की है",
             "आपको ग़लत जानकारी देकर यह बेचा गया", "पैसे आपको वापस दिला देंगे", "आपकी रकम लौटाई जाएगी",
             "Your money will be returned", "tell me the code sent to your mobile", "your mother's name please",
             "share the six digit number you received", "RBI rule ke hisaab se ye zaroori hai"]:  # fmt: skip
    print(f"   {'PASSES' if not lint_line('probe.line', text) else 'refused'}  {text}")
