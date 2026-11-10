"""Pick the cheap default extraction model by measurement.

    uv run python tests/clients/probes/llm_model_probe.py [extra-model-id ...]

Runs 16 synthetic borrower utterances (4 each: Hindi, Hinglish, Tamil, Kannada) through each
candidate model via `LlmClient`, so the cache, ledger and USD cap apply. A rerun is all cache hits
and costs nothing; the latency, cost and attempt count of the original uncached call are carried
over from `<state>/probe/llm_probe.json`.

What this can show: whether a model returns schema-valid output on these prompts, and gross
differences in extraction on short, clean, typed text. What it cannot show: n=16 with gold labels
written by the same author as the prompt, no second annotator, no speech-to-text noise, and the
Tamil and Kannada rows are `not human-reviewed`. One wrong field moves accuracy by 1.6 points, so
differences of a few fields between models are not evidence that one is better.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from samajh.clients import _runtime
from samajh.clients.errors import ApiError, BadResponse, LlmOutputInvalid, TransportError
from samajh.clients.llm import LlmClient, Message

CANDIDATES = [
    "google/gemini-2.5-flash-lite",
    "openai/gpt-4.1-nano",
    "mistralai/mistral-small-3.2-24b-instruct",
]
USD_CAP = 0.30
FIELDS = ("product_kind", "amount_quote", "paid_from_loan", "said_required_for_loan")
NOT_REVIEWED = {"ta", "kn"}  # no fluent human reviewer yet: not human-reviewed


class ProbeExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_kind: Literal["insurance", "fixed_deposit", "other", "not_stated"]
    amount_quote: str | None
    paid_from_loan: Literal["yes", "no", "not_stated"]
    said_required_for_loan: Literal["yes", "no", "not_stated"]


SYSTEM = """\
You extract facts from one thing a borrower said on a phone call. The call asks about a product \
that was sold to them together with a loan. The text may be Hindi, Hindi-English mix, Tamil or Kannada.

Fill the fields from the borrower's words only. Do not guess and do not calculate.
- product_kind: what the borrower believes the product is. "insurance", "fixed_deposit" (FD, \
deposit that comes back with interest), "other", or "not_stated" if they do not say or do not know.
- amount_quote: the borrower's exact words for the amount of that product (its premium, cover or \
deposit), copied character for character from the text: the digits or number words with their \
lakh/thousand word, without the currency word. Not the loan amount, not a number of years. \
null if they give no amount for the product.
- paid_from_loan: "yes" if they say the money was taken out of the loan amount, "no" if they say \
they paid it themselves and not from the loan, otherwise "not_stated".
- said_required_for_loan: "yes" if they say they were told the product was needed to get the \
loan, "no" if they say it was their own choice or nobody forced them, otherwise "not_stated".
"""

# Gold labels were written by hand before any model was run. (id, language, utterance, gold)
G = ProbeExtraction
UTTERANCES: list[tuple[str, str, str, ProbeExtraction]] = [
    ("hi-1", "hi",
     "हाँ, लोन के साथ एक बीमा पॉलिसी दी गई थी। उसका प्रीमियम 12,500 रुपये था और वो लोन की रकम में से ही काट लिया गया।",
     G(product_kind="insurance", amount_quote="12,500", paid_from_loan="yes",
       said_required_for_loan="not_stated")),
    ("hi-2", "hi",
     "एजेंट ने कहा था कि बीमा लेना ज़रूरी है, नहीं तो लोन पास नहीं होगा। डेढ़ लाख का बीमा है।",
     G(product_kind="insurance", amount_quote="डेढ़ लाख", paid_from_loan="not_stated",
       said_required_for_loan="yes")),
    ("hi-3", "hi",
     "मुझे तो बताया गया था कि ये एफडी है, सवा दो लाख रुपये जमा हो रहे हैं और पाँच साल बाद ब्याज के साथ वापस मिलेंगे।",
     G(product_kind="fixed_deposit", amount_quote="सवा दो लाख", paid_from_loan="not_stated",
       said_required_for_loan="not_stated")),
    ("hi-4", "hi",
     "मुझे नहीं पता कि लोन के साथ क्या दिया गया था। कुछ कागज़ों पर साइन करवाए थे, बस।",
     G(product_kind="not_stated", amount_quote=None, paid_from_loan="not_stated",
       said_required_for_loan="not_stated")),
    ("hx-1", "hinglish",
     "हाँ loan के साथ insurance भी था, premium 52,000 था, वो loan amount से ही cut हो गया था।",
     G(product_kind="insurance", amount_quote="52,000", paid_from_loan="yes",
       said_required_for_loan="not_stated")),
    ("hx-2", "hinglish",
     ("देखिए मुझे लगा ये FD है, bank वाले ने बोला था 2 लाख fix कर दो, अच्छा return मिलेगा। "
     "ये पैसे मैंने अपनी savings से दिए थे, loan से नहीं।"),
     G(product_kind="fixed_deposit", amount_quote="2 लाख", paid_from_loan="no",
       said_required_for_loan="not_stated")),
    ("hx-3", "hinglish",
     "Insurance लिया था, लेकिन किसी ने force नहीं किया, मैंने अपनी मर्ज़ी से लिया। Amount अभी याद नहीं है।",
     G(product_kind="insurance", amount_quote=None, paid_from_loan="not_stated",
       said_required_for_loan="no")),
    ("hx-4", "hinglish",
     ("Loan 8 लाख का था, उसमें से 35 हज़ार insurance के नाम पर काट लिए। "
     "Manager ने बोला ये compulsory है, इसके बिना loan नहीं मिलेगा।"),
     G(product_kind="insurance", amount_quote="35 हज़ार", paid_from_loan="yes",
       said_required_for_loan="yes")),
    # Tamil rows: not human-reviewed
    ("ta-1", "ta",
     ("ஆமாம், கடனுடன் ஒரு காப்பீடு பாலிசி கொடுத்தார்கள். அதன் பிரீமியம் 18,000 ரூபாய், "
     "அதை கடன் தொகையிலிருந்தே பிடித்துக்கொண்டார்கள்."),
     G(product_kind="insurance", amount_quote="18,000", paid_from_loan="yes",
       said_required_for_loan="not_stated")),
    ("ta-2", "ta",
     "காப்பீடு எடுத்தால்தான் கடன் கிடைக்கும் என்று சொன்னார்கள். அதனால் ஒன்றரை லட்சம் ரூபாய்க்கு காப்பீடு எடுத்தேன்.",
     G(product_kind="insurance", amount_quote="ஒன்றரை லட்சம்", paid_from_loan="not_stated",
       said_required_for_loan="yes")),
    ("ta-3", "ta",
     ("அது நிலையான வைப்பு என்று நினைத்தேன். இரண்டு லட்சம் ரூபாய் போட்டால் ஐந்து வருடத்தில் "
     "வட்டியுடன் திரும்பக் கிடைக்கும் என்று சொன்னார்கள்."),
     G(product_kind="fixed_deposit", amount_quote="இரண்டு லட்சம்", paid_from_loan="not_stated",
       said_required_for_loan="not_stated")),
    ("ta-4", "ta",
     "கடனுடன் என்ன கொடுத்தார்கள் என்று எனக்குத் தெரியாது. சில காகிதங்களில் கையெழுத்து வாங்கினார்கள், அவ்வளவுதான்.",
     G(product_kind="not_stated", amount_quote=None, paid_from_loan="not_stated",
       said_required_for_loan="not_stated")),
    # Kannada rows: not human-reviewed
    ("kn-1", "kn",
     "ಹೌದು, ಸಾಲದ ಜೊತೆ ಒಂದು ವಿಮೆ ಪಾಲಿಸಿ ಕೊಟ್ಟರು. ಅದರ ಪ್ರೀಮಿಯಂ 24,000 ರೂಪಾಯಿ, ಅದನ್ನು ಸಾಲದ ಮೊತ್ತದಿಂದಲೇ ಕಡಿತ ಮಾಡಿದರು.",
     G(product_kind="insurance", amount_quote="24,000", paid_from_loan="yes",
       said_required_for_loan="not_stated")),
    ("kn-2", "kn",
     "ವಿಮೆ ತೆಗೆದುಕೊಳ್ಳದಿದ್ದರೆ ಸಾಲ ಸಿಗುವುದಿಲ್ಲ ಎಂದು ಹೇಳಿದರು, ಅದಕ್ಕೆ ತೆಗೆದುಕೊಂಡೆ. ಎಷ್ಟು ಹಣ ಎಂದು ನನಗೆ ನೆನಪಿಲ್ಲ.",
     G(product_kind="insurance", amount_quote=None, paid_from_loan="not_stated",
       said_required_for_loan="yes")),
    ("kn-3", "kn",
     "ಅದು ಎಫ್‌ಡಿ ಎಂದು ನಾನು ಅಂದುಕೊಂಡಿದ್ದೆ. ಒಂದೂವರೆ ಲಕ್ಷ ರೂಪಾಯಿ ಇಟ್ಟರೆ ಐದು ವರ್ಷದ ನಂತರ ಬಡ್ಡಿ ಸಮೇತ ವಾಪಸ್ ಬರುತ್ತದೆ ಎಂದು ಹೇಳಿದರು.",
     G(product_kind="fixed_deposit", amount_quote="ಒಂದೂವರೆ ಲಕ್ಷ", paid_from_loan="not_stated",
       said_required_for_loan="not_stated")),
    ("kn-4", "kn",
     "ವಿಮೆ ಬೇಕೋ ಬೇಡವೋ ಎಂದು ಕೇಳಿದರು, ನಾನೇ ಬೇಕು ಎಂದೆ. 9,500 ರೂಪಾಯಿ ನನ್ನ ಕೈಯಿಂದಲೇ ಕಟ್ಟಿದೆ, ಸಾಲದಿಂದ ಅಲ್ಲ.",
     G(product_kind="insurance", amount_quote="9,500", paid_from_loan="no",
       said_required_for_loan="no")),
]
LANGS = ("hi", "hinglish", "ta", "kn")


def norm(value: str | None) -> str | None:
    return " ".join(value.split()) if isinstance(value, str) else value


def key_usage(api_key: str) -> float | None:
    """Account spend in USD from GET /key. Only `usage` is read: `label` holds part of the key."""
    try:
        data = httpx.get(
            "https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {api_key}"}, timeout=30
        ).json()
        return float(data["data"]["usage"])
    except Exception:  # noqa: BLE001 - a cross-check only; the probe must not die on it
        return None


def run_model(client: LlmClient, model: str, previous: dict[str, dict]) -> list[dict]:
    rows = []
    for uid, lang, text, gold in UTTERANCES:
        messages = [Message(role="system", content=SYSTEM), Message(role="user", content=text)]
        row: dict = {"model": model, "id": uid, "lang": lang, "got": None, "error": None}
        started = time.monotonic()
        try:
            result = client.complete(ProbeExtraction, messages, model=model, max_tokens=300)
        except (LlmOutputInvalid, ApiError, BadResponse, TransportError) as exc:
            row.update(error=f"{type(exc).__name__}: {exc}"[:300], cache_hit=False, attempts=None,
                       seconds=time.monotonic() - started, usd=None, routed_model=None)
        else:
            row.update(got=result.value.model_dump(), cache_hit=result.cache_hit, attempts=result.attempts,
                       seconds=time.monotonic() - started, usd=result.usd, routed_model=result.model)
            old = previous.get(f"{model}|{uid}")
            if result.cache_hit and old:
                # The uncached call's measurements, so a rerun reports the same table.
                row.update(attempts=old["attempts"], seconds=old["seconds"], usd=old["usd"])
            elif result.cache_hit:
                row.update(attempts=None, seconds=None, usd=None)
        row["wrong"] = [
            f for f in FIELDS
            if row["got"] is None or norm(row["got"][f]) != norm(getattr(gold, f))
        ]
        rows.append(row)
    return rows


def summarise(model: str, rows: list[dict]) -> dict:
    texts = {uid: text for uid, _, text, _ in UTTERANCES}
    quoted = [r for r in rows if r["got"] and r["got"]["amount_quote"] is not None]
    seconds = sorted(r["seconds"] for r in rows if r["seconds"] is not None and not r["error"])
    usd = [r["usd"] for r in rows if r["usd"] is not None]
    return {
        "model": model,
        "n": len(rows),
        "valid_first": sum(1 for r in rows if r["attempts"] == 1),
        "valid_any": sum(1 for r in rows if r["got"] is not None),
        "fields_right": sum(len(FIELDS) - len(r["wrong"]) for r in rows),
        "fields_total": len(FIELDS) * len(rows),
        "by_lang": {
            lang: [sum(len(FIELDS) - len(r["wrong"]) for r in rows if r["lang"] == lang),
                   len(FIELDS) * sum(1 for r in rows if r["lang"] == lang)]
            for lang in LANGS
        },
        "quote_verbatim": [sum(1 for r in quoted if r["got"]["amount_quote"] in texts[r["id"]]), len(quoted)],
        "median_s": statistics.median(seconds) if seconds else None,
        # Nearest-rank p95; with n=16 this is the slowest call.
        "p95_s": seconds[math.ceil(0.95 * len(seconds)) - 1] if seconds else None,
        "timed_calls": len(seconds),
        "usd": sum(usd) if len(usd) == len(rows) else None,
    }


def fmt(value: float | None, spec: str) -> str:
    return "n/a" if value is None else format(value, spec)


def main(extra_models: list[str]) -> None:
    _runtime.load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    out_path = _runtime.state_dir() / "probe" / "llm_probe.json"
    try:
        previous = {f"{r['model']}|{r['id']}": r for r in json.loads(out_path.read_text("utf-8"))["rows"]}
    except (OSError, ValueError, KeyError):
        previous = {}

    client = LlmClient.from_env(usd_cap=USD_CAP, model=CANDIDATES[0])
    before = key_usage(api_key)
    models = [*CANDIDATES, *extra_models]
    rows = [row for model in models for row in run_model(client, model, previous)]
    summaries = [summarise(model, [r for r in rows if r["model"] == model]) for model in models]
    time.sleep(3 if client.spent_usd else 0)  # /key lags the response by a moment
    after = key_usage(api_key)

    # Rows for models not in this run are kept, so an extra model does not have to be re-listed.
    kept = [r for k, r in previous.items() if k.split("|")[0] not in models]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "probe": "llm_model_probe", "n": len(UTTERANCES), "system_prompt": SYSTEM,
                "not_human_reviewed_languages": sorted(NOT_REVIEWED),
                "utterances": [
                    {"id": u, "lang": lang, "text": t, "gold": g.model_dump()} for u, lang, t, g in UTTERANCES
                ],
                "summaries": summaries, "rows": [*rows, *kept],
            },
            ensure_ascii=False, indent=1,
        ),
        "utf-8",
    )

    print(f"n = {len(UTTERANCES)} utterances x {len(FIELDS)} fields; gold self-written; "
          "ta* and kn* rows are not human-reviewed\n")
    print("| model | schema-valid 1st attempt | field accuracy | hi | hinglish | ta* | kn* "
          "| quote verbatim | median s | p95 s | USD |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in summaries:
        langs = " | ".join(f"{a}/{b}" for a, b in (s["by_lang"][lang] for lang in LANGS))
        print(
            f"| {s['model']} | {s['valid_first']}/{s['n']} | {s['fields_right']}/{s['fields_total']} "
            f"({s['fields_right'] / s['fields_total']:.1%}) | {langs} "
            f"| {s['quote_verbatim'][0]}/{s['quote_verbatim'][1]} | {fmt(s['median_s'], '.2f')} "
            f"| {fmt(s['p95_s'], '.2f')} | {fmt(s['usd'], '.6f')} |"
        )
    print("\n`*` not human-reviewed. Latency and USD are from the uncached calls "
          "(latency is wall time of the whole call, including any retry).\n")

    print("Wrong fields (model, utterance, field, gold, got):")
    gold_by_id = {uid: gold for uid, _, _, gold in UTTERANCES}
    wrong = 0
    for r in rows:
        for field in r["wrong"]:
            wrong += 1
            got = r["got"][field] if r["got"] else f"<no output: {r['error']}>"
            print(f"- {r['model']} | {r['id']} | {field} | gold={getattr(gold_by_id[r['id']], field)!r} "
                  f"| got={got!r}")
    print("- none" if not wrong else f"({wrong} wrong fields)")

    eligible = [s for s in summaries if s["valid_first"] == s["n"]]
    if eligible:
        pick = min(eligible, key=lambda s: (-s["fields_right"], s["usd"] or 0.0, s["median_s"] or 0.0))
        print(f"\nPick (most fields right with {pick['n']}/{pick['n']} schema-valid; ties by cost, then "
              f"median latency): {pick['model']}")
    else:
        print("\nPick: none, no model was schema-valid on the first attempt for every utterance")

    hits = sum(1 for r in rows if r.get("cache_hit"))
    print(f"\nThis run: {len(rows)} calls, {hits} cache hits, spent {client.spent_usd:.6f} USD (usage.cost sum)")
    if before is not None and after is not None:
        print(f"/key usage: before {before:.6f}, after {after:.6f}, delta {after - before:.6f} USD")
    print(f"Raw results: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
