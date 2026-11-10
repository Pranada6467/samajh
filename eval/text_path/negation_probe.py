"""Probe: replies whose first clause, read alone, gives the opposite of what the customer means.

    uv run python eval/text_path/negation_probe.py --model openai/gpt-6-luna --model mistralai/mistral-small-3.2-24b-instruct

24 replies written by the W5 reviewer on 2026-11-10 to attack one weakness: the model points at
a clause and stops reading before a "not" in a later clause ("ज़रूरी था, ऐसा तो किसी ने नहीं कहा।").
Hindi and Hinglish only: the reviewer cannot write Tamil or Kannada negation reliably. None of
these replies is in the development set, the prompt examples or the frozen set. One LLM call
per reply through the real client, with the extractor's own prompts and token limit. The pass
condition of each probe is written next to it. The output is printed and saved to
`runs/negation_probe.md`. Rerunning is free: every call is cached.
"""

import argparse
import json
from pathlib import Path

from samajh.clients.errors import LlmOutputInvalid
from samajh.clients.llm import LlmClient
from samajh.extract._extract import _MAX_TOKENS
from samajh.extract._prompt import messages, screen_messages
from samajh.extract._wire import SCHEMA, ScreenReply, SlotKind
from samajh.pipeline import WithoutTemperature, takes_temperature
from samajh.types import Language

OUT = Path(__file__).parent / "runs" / "negation_probe.md"

K = SlotKind
# (kind, language, question, reply, check(output dict) -> bool, what a correct reading is)
PROBES = [
    (
        K.required_for_loan,
        "hi",
        "क्या लोन पाने के लिए उसे लेना ज़रूरी था?",
        "ज़रूरी था, ऐसा तो किसी ने नहीं कहा।",
        lambda o: not (o["status"] == "stated" and o["yes"] is True),
        "not yes=true",
    ),
    (
        K.required_for_loan,
        "hi",
        "क्या लोन पाने के लिए उसे लेना ज़रूरी था?",
        "लेना ही पड़ेगा, यह बात नहीं थी, मैंने खुद लिया।",
        lambda o: not (o["status"] == "stated" and o["yes"] is True),
        "not yes=true",
    ),
    (
        K.required_for_loan,
        "hi-en",
        "क्या ये loan के लिए ज़रूरी था?",
        "Compulsory है, ऐसा नहीं बोला था, optional ही था.",
        lambda o: o["status"] == "stated" and o["yes"] is False,
        "yes=false",
    ),
    (
        K.provider_choice,
        "hi",
        "क्या आपको बताया गया था कि वही चीज़ आप किसी दूसरी कंपनी से भी ले सकते हैं?",
        "दूसरी कंपनी से ले सकते हैं, यह तो नहीं बताया था।",
        lambda o: o["status"] == "stated" and o["yes"] is False,
        "yes=false",
    ),
    (
        K.provider_choice,
        "hi-en",
        "क्या आपको बताया गया था कि ये किसी और company से भी ले सकते हैं?",
        "हाँ बताया था, मतलब नहीं नहीं, ये बात नहीं बताई थी.",
        lambda o: not (o["status"] == "stated" and o["yes"] is True),
        "not yes=true",
    ),
    (
        K.provider_choice,
        "hi",
        "क्या आपको बताया गया था कि वही चीज़ आप किसी दूसरी कंपनी से भी ले सकते हैं?",
        "कहीं से भी ले सकते हो, ऐसा किसी ने नहीं कहा, बोले यहीं से लेना होगा।",
        lambda o: o["status"] == "stated" and o["yes"] is False,
        "yes=false",
    ),
    (
        K.cancel_window,
        "hi",
        "क्या आपको बताया गया था कि आप उसे कैंसल कर सकते हैं या नहीं, और कब तक?",
        "रद्द करवा सकते हैं, ऐसा किसी ने नहीं बताया।",
        lambda o: not (o["allowed_status"] == "stated" and o["allowed"] is True),
        "not allowed=true",
    ),
    (
        K.cancel_window,
        "hi",
        "क्या आपको बताया गया था कि आप उसे कैंसल कर सकते हैं या नहीं, और कब तक?",
        "पंद्रह दिन में कैंसल हो जाता है, यह मुझे बाद में पड़ोसी से पता चला, बैंक ने नहीं बताया।",
        lambda o: not (o["allowed_status"] == "stated" and o["allowed"] is True),
        "not allowed=true",
    ),
    (
        K.cancel_window,
        "hi-en",
        "क्या आपको बताया गया था कि इसे cancel कर सकते हैं या नहीं, और कब तक?",
        "Cancel कर सकते हैं, ये नहीं बताया था, बस sign करवा लिया.",
        lambda o: not (o["allowed_status"] == "stated" and o["allowed"] is True),
        "not allowed=true",
    ),
    (
        K.kind,
        "hi",
        "लोन के साथ जो चीज़ ली गई, आपकी समझ में वह क्या है: बीमा, एफ़डी, या कुछ और?",
        "बीमा है, ऐसा नहीं लगता, मुझे तो एफ़डी बोला था।",
        lambda o: not (o["status"] == "stated" and o["kind"] == "insurance"),
        "not insurance",
    ),
    (
        K.kind,
        "hi-en",
        "Loan के साथ जो product आपको दिया गया, वो insurance है, FD है या कुछ और?",
        "Insurance, नहीं नहीं, FD है वो.",
        lambda o: o["status"] == "stated" and o["kind"] == "deposit",
        "deposit",
    ),
    (
        K.kind,
        "hi",
        "लोन के साथ जो चीज़ ली गई, आपकी समझ में वह क्या है: बीमा, एफ़डी, या कुछ और?",
        "बीमा, एफ़डी, यह सब मुझे नहीं पता।",
        lambda o: o["status"] != "stated",
        "dont_know or unclear",
    ),
    (
        K.readback,
        "hi",
        "बावन हज़ार, यानी 52,000 रुपये, सही है?",
        "सही है, नहीं रुकिए, गलत है।",
        lambda o: not (o["status"] == "stated" and o["confirms"] is True),
        "not confirms=true",
    ),
    (
        K.readback,
        "hi-en",
        "बावन हज़ार, यानी 52,000 रुपये, सही है?",
        "Correct, ऐसा नहीं है, थोड़ा कम था.",
        lambda o: not (o["status"] == "stated" and o["confirms"] is True),
        "not confirms=true",
    ),
    (
        K.consent,
        "hi",
        "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?",
        "बीमा के लिए हामी भरी थी, ऐसा मुझे याद नहीं, मैंने तो सिर्फ़ लोन के कागज़ पर दस्तखत किए।",
        lambda o: not (o["given_status"] == "stated" and o["given"] is True),
        "not given=true",
    ),
    (
        K.consent,
        "hi-en",
        "Loan लेते time आपने क्या-क्या लेने के लिए agree किया था, और कैसे?",
        "Policy के लिए agree किया, ये गलत है, मैंने सिर्फ loan के लिए OTP दिया था.",
        lambda o: not (o["given_status"] == "stated" and o["given"] is True),
        "not given=true",
    ),
    (
        K.features,
        "hi",
        "अगर आप वह पैसा वापस चाहें, तो क्या मिल सकता है, और कब?",
        "जब चाहूँ निकाल सकता हूँ, ऐसा नहीं है, यह बीमा है।",
        lambda o: "refundable_anytime" not in o["claims"],
        "no refundable_anytime",
    ),
    (
        K.features,
        "hi-en",
        "अगर आप ये पैसा वापस लेना चाहें, तो क्या वापस मिल सकता है, और कब?",
        "Interest के साथ वापस मिलेगा, ऐसा पहले लगा था, पर अब पता है कि नहीं मिलता.",
        lambda o: "guaranteed_return" not in o["claims"],
        "no guaranteed_return",
    ),
    (
        K.payment_source,
        "hi",
        "वह रकम कैसे चुकाई गई: लोन की रकम में से, या अलग से?",
        "लोन में से कटा, ऐसा नहीं है, मैंने अलग से नकद दिया था।",
        lambda o: o["status"] == "stated" and o["source"] == "separately",
        "separately",
    ),
    (
        K.payment_source,
        "hi-en",
        "ये payment कैसे हुआ, loan amount में से या अलग से?",
        "अलग से दिया, नहीं sorry, loan amount में से ही कटा था.",
        lambda o: o["status"] == "stated" and o["source"] == "from_loan",
        "from_loan",
    ),
]
SCREENS = [
    (
        "hi",
        "लोन के साथ आपने क्या-क्या लिया, और कितने का?",
        "यह एफ़डी है ऐसा किसी ने नहीं बोला, बीमा ही बताया था।",
        lambda o: not any(c["claim"] == "is_deposit" for c in o["claims"]),
        "no is_deposit",
    ),
    (
        "hi",
        "क्या लोन पाने के लिए उसे लेना ज़रूरी था?",
        "किसी ने नहीं कहा कि हर बात पर हाँ कहना, मैं अपनी समझ से बता रहा हूँ।",
        lambda o: not any(c["concern"] == "coached_answers" for c in o["concerns"]),
        "no coached_answers",
    ),
    (
        "hi-en",
        "ये कितने time के लिए है?",
        "पैसा कभी भी निकाल सकते हैं ऐसा मुझे नहीं बोला गया था, तीन साल का है.",
        lambda o: not any(c["claim"] == "refundable_anytime" for c in o["claims"]),
        "no refundable_anytime",
    ),
    (
        "hi",
        "उसमें कितनी रकम का कवर है?",
        "दस्तखत तो किए थे, और सब कुछ अच्छे से समझाया भी था, पाँच लाख का कवर है।",
        lambda o: not any(c["concern"] == "signed_without_explanation" for c in o["concerns"]),
        "no signed_without_explanation",
    ),
]
LANG = {"hi": Language.hi, "hi-en": Language.hi_en}


def _ask(llm, schema, request, model: str) -> dict:
    try:
        return llm.complete(schema, request, model=model, max_tokens=_MAX_TOKENS).value.model_dump(
            mode="json"
        )
    except LlmOutputInvalid as exc:
        return {"error": str(exc)}


def probe(model: str) -> str:
    client = LlmClient.from_env(model=model, usd_cap=0.15)
    llm = client if takes_temperature(model) else WithoutTemperature(client)
    wrong = []
    for kind, language, question, reply, right, want in PROBES:
        out = _ask(llm, SCHEMA[kind], messages(kind, LANG[language], question, reply), model)
        if "error" in out or not right(out):
            wrong.append((kind.value, reply, want, out))
    for language, question, reply, right, want in SCREENS:
        out = _ask(llm, ScreenReply, screen_messages(LANG[language], question, reply), model)
        if "error" in out or not right(out):
            wrong.append(("screen", reply, want, out))
    total = len(PROBES) + len(SCREENS)
    lines = [f"## `{model}`: {total - len(wrong)} of {total} read correctly", ""]
    for kind, reply, want, out in wrong:
        lines += [
            f'- [{kind}] "{reply}"',
            f"  - correct: {want}",
            f"  - model: `{json.dumps(out, ensure_ascii=False)}`",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", required=True)
    args = parser.parse_args()
    text = (
        "# Negation probe\n\n"
        f"{len(PROBES) + len(SCREENS)} reviewer-written Hindi and Hinglish replies, max_tokens {_MAX_TOKENS}. "
        "Each reply is built so that its first clause, read alone, gives the opposite answer. "
        "Not a sample of real speech: it shows a failure pattern, not a rate.\n\n"
    )
    text += "\n".join(probe(model) for model in args.model)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
