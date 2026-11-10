"""Verifier probe: does the dialogue's LLM fallback work today, or fail without a trace? LIVE: spends
OpenRouter money through samajh.clients.llm (cap 0.10 USD for this script; it used about 0.002).

    uv run python references/reviews/iter1/probes/dialogue_llm_fallback_live.py

Part 1: the pinned fallback model on refusals the word lists miss (written by the verifier).
Part 2: the same interpreter given the client's current default model (openai/gpt-6-luna).
"""

import logging
import time

from samajh.clients.llm import LlmClient
from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter
from samajh.dialogue.machine import AtStopCheck, AtTeachBack, _say
from samajh.types import Language, LoanRecord, Question

logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")

REC = LoanRecord.model_validate({
    "loan_id": "LN-VERIFY-0004", "lender_type": "bank",
    "borrower": {"name": "Ramesh Namoona", "dob": "1984-06-15", "language": "hi"},
    "loan_kind": "gold", "sanctioned_inr": 500000, "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
    "products": [{"id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
                  "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
                  "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30,
                  "features": [], "consent": None}]})  # fmt: skip

TURNS = [  # (language, reply, what a person would want the bot to do)
    (Language.hi, "मुझे इस बारे में कुछ नहीं कहना", "stop"),
    (Language.hi, "मैं गाड़ी चला रहा हूँ", "stop"),
    (Language.hi, "कल फ़ोन करना", "stop"),
    (Language.hi, "इतने सवाल मत पूछो", "stop"),
    (Language.hi_en, "I have to go now", "stop"),
    (Language.hi_en, "I'd rather not answer", "stop"),
    (Language.hi_en, "can we do this some other day", "stop"),
    (Language.ta, "நான் வண்டி ஓட்டிட்டு இருக்கேன்", "stop"),
    (Language.ta, "நாளைக்கு கூப்பிடுங்க", "stop"),
    (Language.ta, "இனிமே கேள்வி கேக்காதீங்க", "stop"),
    (Language.kn, "ನಾನು ಗಾಡಿ ಓಡಿಸ್ತಿದ್ದೀನಿ", "stop"),
    (Language.kn, "ನಾಳೆ ಫೋನ್ ಮಾಡಿ", "stop"),
    (Language.kn, "ಇನ್ನು ಪ್ರಶ್ನೆ ಕೇಳಬೇಡಿ", "stop"),
    # accounts of the sale: must be taken as answers
    (Language.hi, "पता चला बाद में कि कुछ कटा है, किसी ने समझाया नहीं", "answer"),
    (Language.ta, "வேண்டாம்னு சொன்னேன், கட்டாயம்னு சொல்லி போட்டாங்க", "answer"),
    (Language.kn, "ಬೇಡ ಅಂದೆ, ಕಡ್ಡಾಯ ಅಂತ ಹೇಳಿ ಹಾಕಿದ್ರು", "answer"),
    # off-topic
    (Language.hi, "अरे सब्ज़ी वाले भैया रुको ज़रा", "re-ask"),
]


def effect(interpreter, language, text):
    state, _ = start(REC, language, lender_name="Namoona Bank")
    state, _ = _say(state, AtTeachBack(product=0, question=Question.kind))
    started = time.monotonic()
    after, said = step(state, text, interpreter=interpreter)
    seconds = time.monotonic() - started
    if isinstance(said, EndOfCall):
        return f"ended:{said.outcome.value}", seconds
    if isinstance(after.position, AtStopCheck):
        return "stop question", seconds
    return ("re-asked" if after.position.reasked else "next question"), seconds


def main() -> None:
    llm = LlmClient.from_env(usd_cap=0.10)
    print(f"client default model: {llm._model}; fallback pinned model: {FALLBACK_MODEL}")
    for name, interpreter in [
        ("rules only", RuleInterpreter()),
        (f"fallback, pinned {FALLBACK_MODEL}", LlmFallbackInterpreter(llm)),
        ("fallback, given the client default openai/gpt-6-luna", LlmFallbackInterpreter(llm, model=llm._model)),
    ]:
        rows = TURNS if "luna" not in name else TURNS[:4]
        print(f"\n== {name}")
        right = 0
        for language, text, want in rows:
            got, seconds = effect(interpreter, language, text)
            ok = (want == "stop" and (got.startswith("ended") or got == "stop question")) or (
                want == "answer" and got == "next question") or (want == "re-ask" and got == "re-asked")  # fmt: skip
            right += ok
            print(f"  [{language.value}] {'ok ' if ok else 'MISS'} want {want:7s} got {got:22s} {seconds:5.2f}s  {text}")
        print(f"  {right}/{len(rows)} as wanted; client spent so far {llm.spent_usd:.5f} USD")


if __name__ == "__main__":
    main()
