"""P5: an outside model writes each customer's spoken replies from a fact sheet alone.

Commands (run from the repo root with `uv run python eval/p5/write_customers.py ...`):
  models         print the two writer models, why, and the model x language x kind counts
  rewrite --id P5-Cnnn --arm open|closed
                 repeat one arm's request with the other writer model, only when more than half
                 of that arm's replies fail a mechanical check
  add-defer [--resume]
                 one request per customer for the open call's `defer` version (topics.json open_defer)
  inputs-hash    print the five digests FROZEN.json["inputs"] must hold (the same code run checks)
  render-closed  write data/p5/closed_statements.jsonl (the closed call per customer; no LLM)
  smoke --out D  both requests for the built-in example customers on both models, written to D
  run [--resume] the real run; refuses unless data/p5/FROZEN.json matches the inputs on disk

Independence: the open request carries the system prompt, the customer's fact sheet and the
open-call topics from topics.json, nothing else. The closed request carries the same fact sheet
and the closed statements rendered from the record. Neither sees the other's replies.
Checks on replies are mechanical only (empty, digits, length, script); nothing is filtered or
edited on content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from samajh.amounts import spoken_amount
from samajh.clients.errors import LlmOutputInvalid
from samajh.clients.llm import LlmClient, Message
from samajh.server.records import CallRecord
from samajh.types import ConsentMethod, FeatureClaim, Language

P5 = ROOT / "data" / "p5"
TOPICS = P5 / "topics.json"
CLOSED_SCRIPT = P5 / "closed_script.json"
CUSTOMERS = P5 / "customers.jsonl"
RECORDS = P5 / "records"
FROZEN = P5 / "FROZEN.json"
REPLIES = P5 / "replies.jsonl"
REQUESTS = P5 / "writer_requests.jsonl"
CLOSED_OUT = P5 / "closed_statements.jsonl"
FROZEN_INPUTS = ("customers.jsonl", "gold.jsonl", "topics.json", "closed_script.json")

# Chosen from the OpenRouter model list on 2026-11-10 (prices per million tokens, input/output).
MODEL_A = "google/gemini-3.7-flash"
MODEL_B = "deepseek/deepseek-v4.1-flash"
MODELS_WHY = {
    MODEL_A: "Google Gemini Flash (USD 0.75 / 3.75 per M tokens): strong Hindi and Devanagari, "
             "strict JSON-schema output; a family the project's builders, extractor and classifier do not use.",
    MODEL_B: "DeepSeek V4.1 Flash (USD 0.006 / 0.50 per M tokens as listed): natural Devanagari Hindi and "
             "Hinglish in the smoke test, strict JSON-schema output, a second family distinct from Google and "
             "from Anthropic, OpenAI and Mistral. Rejected: qwen/qwen3.8-flash (wrote Hinglish in Latin script "
             "only, ran out of tokens on 2 of 3 open requests, about 2 minutes a request).",
}
TEMPERATURE = 0.8
MAX_TOKENS = 8192
MAX_EXTRA_ATTEMPTS = 2  # a failing reply set is asked again at most twice
LIMIT = {"own": 240, "again": 240, "go_along": 60, "defer": 60}

# ---------------------------------------------------------------- the system prompt

_SYSTEM = """You are playing one person on a phone call. The message below says everything this person knows.

Answer each thing the caller says as this person would actually say it aloud on the phone, in their own manner (see "How you talk" and "On this call"). Stay inside the fact sheet and never add a fact it does not hold. Where the sheet says the person does not know something, or says nothing about it, answer as that person honestly would (often that they do not know). If you are not the borrower, answer as yourself.

Spoken language only: one or two short sentences, most replies under fifteen words, go_along replies a few words. Fillers and half-sentences are fine. No stage directions, no explanations, no quotation marks.

{language}

Every number as spoken words, never digits.

{versions}

Return only the JSON object asked for."""

_LANGUAGE = {
    "hi": "Language: Hindi in Devanagari, as it is spoken. English loan words such as loan or bank are written in Devanagari.",
    "hi-en": "Language: Hinglish. Hindi words in Devanagari and English words in Latin script, mixed the way urban speakers mix them.",
}


def system_prompt(language: str, topics: dict[str, Any]) -> str:
    v = topics["variants"]
    versions = (f"For some things the caller says you write more than one version:\n- own: {v['own']}\n"
                f"- again: {v['again']}\n- go_along: {v['go_along']}")
    return _SYSTEM.format(language=_LANGUAGE[language], versions=versions)


def defer_system_prompt(language: str, topics: dict[str, Any]) -> str:
    """The open request's system prompt with the version lines replaced by the one `defer` definition."""
    versions = f"For each thing the caller says you write one version:\n- defer: {topics['open_defer']['variant']['defer']}"
    return _SYSTEM.format(language=_LANGUAGE[language], versions=versions)


def defer_user_message(customer: dict[str, Any], topics: dict[str, Any]) -> str:
    callers = {t["id"]: t["caller"] for t in topics["open_call"]}
    parts = [fact_sheet_text(customer), "", "THE CALL",
             "Here is each thing the caller may say. For each one, write what you would say, in the version listed.", ""]
    for topic_id in topics["open_defer"]["topics"]:
        parts.append(f"[{topic_id}] {callers[topic_id]}\nVersions: defer")
    parts += ["", "Return one JSON object with one key per id above; under each key, the string defer."]
    return "\n".join(parts)


def defer_schema(topics: dict[str, Any]) -> type[BaseModel]:
    fields = {topic_id: (_variant_model(("defer",)), ...) for topic_id in topics["open_defer"]["topics"]}
    return create_model("DeferReplies", __base__=_Strict, **fields)


# ---------------------------------------------------------------- user messages


def _speaker_line(speaker: dict[str, Any]) -> str:
    person = {"f": "a woman", "m": "a man"}[speaker["gender"]]
    if speaker["who"] == "borrower":
        return f"You are {person}, and you are the borrower."
    relation = speaker.get("relation") or "someone else"
    return f"You are {person}. You are not the borrower; you are the borrower's {relation}."


def fact_sheet_text(customer: dict[str, Any]) -> str:
    fs = customer["fact_sheet"]
    lines = ["ABOUT YOU", _speaker_line(customer["speaker"]), f"You are: {fs['you_are']}",
             f"What happened: {fs['what_happened']}", "What you know:"]
    lines += [f"- {x}" for x in fs["what_you_know"]] or ["- (nothing listed)"]
    lines.append("What you do not know:")
    lines += [f"- {x}" for x in fs["what_you_do_not_know"]] or ["- (nothing listed)"]
    lines += [f"How you talk: {fs['how_you_talk']}", f"On this call: {fs['on_this_call']}"]
    return "\n".join(lines)


def open_user_message(customer: dict[str, Any], topics: dict[str, Any]) -> str:
    parts = [fact_sheet_text(customer), "", "THE CALL",
             "Here is each thing the caller may say. For each one, write what you would say, in each version listed.", ""]
    for t in topics["open_call"]:
        parts.append(f"[{t['id']}] {t['caller']}\nVersions: {', '.join(t['variants'])}")
    parts += ["", "Return one JSON object with one key per id above; under each key, one string per version listed."]
    return "\n".join(parts)


def closed_user_message(customer: dict[str, Any], closed: dict[str, Any]) -> str:
    parts = [fact_sheet_text(customer), "", "THE CALL",
             "The caller reads out details one at a time and asks after each whether it is correct.",
             f"First the caller says: {closed['intro']}", "",
             "Here is each detail the caller reads. For each one, write what you would say, in the versions own and go_along.", ""]
    for s in closed["statements"]:
        parts.append(f"[{s['id']}] {s['text']}")
    parts += ["", "Return one JSON object with one key per id above; under each key, the strings own and go_along."]
    return "\n".join(parts)


def with_attempt(user: str, attempt: int) -> str:
    return user if attempt == 1 else f"{user}\n\nattempt {attempt}"


# ---------------------------------------------------------------- schemas


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


_VARIANT_MODELS: dict[tuple[str, ...], type[BaseModel]] = {}


def _variant_model(variants: tuple[str, ...]) -> type[BaseModel]:
    if variants not in _VARIANT_MODELS:
        name = "Reply_" + "_".join(variants)
        _VARIANT_MODELS[variants] = create_model(name, __base__=_Strict, **{v: (str, ...) for v in variants})
    return _VARIANT_MODELS[variants]


def open_schema(topics: dict[str, Any]) -> type[BaseModel]:
    fields = {t["id"]: (_variant_model(tuple(t["variants"])), ...) for t in topics["open_call"]}
    return create_model("OpenCallReplies", __base__=_Strict, **fields)


def closed_schema(topics: dict[str, Any]) -> type[BaseModel]:
    variants = tuple(topics["closed_call"]["variants"])
    fields = {s["id"]: (_variant_model(variants), ...) for s in topics["closed_call"]["statements"]}
    return create_model("ClosedCallReplies", __base__=_Strict, **fields)


# ---------------------------------------------------------------- the closed call, rendered

_NOT_SAVINGS_CONTRADICTED = {FeatureClaim.is_deposit, FeatureClaim.refundable_anytime,
                             FeatureClaim.guaranteed_return, FeatureClaim.withdrawable_after_period}


def _words(n: int, language: str) -> str:
    return spoken_amount(n, Language(language))


def term_words(months: int, language: str) -> str:
    if months % 12 == 0:
        years = months // 12
        if language == "hi":
            return f"{_words(years, language)} साल"
        return "one year" if years == 1 else f"{_words(years, language)} years"
    if language == "hi":
        return "एक महीने" if months == 1 else f"{_words(months, language)} महीने"
    return "one month" if months == 1 else f"{_words(months, language)} months"


def days_words(days: int, language: str) -> str:
    if language == "hi":
        return f"{_words(days, language)} दिन"
    return "one day" if days == 1 else f"{_words(days, language)} days"


def spoken_provider(provider: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", provider).strip()


def render_closed(record: CallRecord, language: str, script: dict[str, Any], topics: dict[str, Any]) -> dict[str, Any]:
    if len(record.record.products) != 1:
        raise ValueError(f"{record.id}: the closed call reads one product, the record has {len(record.record.products)}")
    p = record.record.products[0]
    if p.features & _NOT_SAVINGS_CONTRADICTED:
        raise ValueError(f"{record.id}: features {sorted(p.features)} contradict c_not_savings")
    lines = script[language]
    slots = {
        "provider": spoken_provider(p.provider),
        "premium_words": _words(p.premium_inr, language),
        "cover_words": _words(p.cover_inr, language),
        "term_words": term_words(p.term_months, language),
        "cancel_days_words": days_words(p.cancel_window_days, language) if p.cancel_window_days else "",
    }
    pick = {
        "c_source": "paid_from_loan" if p.paid_from_loan else "paid_separately",
        "c_voluntary": "required_true" if p.required_for_loan else "required_false",
        "c_cancel": "with_window" if p.cancel_window_days else "no_window",
        "c_consent": p.consent.method.value if p.consent is not None else "none",
    }
    statements = []
    for s in topics["closed_call"]["statements"]:
        template = lines["statements"][s["id"]]
        if isinstance(template, dict):
            template = template[pick[s["id"]]]
        text = template.format(**slots)
        if re.search(r"[0-9०-९{}]", text):
            raise ValueError(f"{record.id} {s['id']}: a digit or an unfilled slot in {text!r}")
        statements.append({"id": s["id"], "group": s["group"], "text": text})
    return {"intro": lines["intro"], "statements": statements, "close": lines["close"]}


def check_script(script: dict[str, Any], topics: dict[str, Any]) -> None:
    """The script has every statement id for both languages and every consent method."""
    ids = [s["id"] for s in topics["closed_call"]["statements"]]
    for lang in ("hi", "hi-en"):
        got = list(script[lang]["statements"])
        if got != ids:
            raise ValueError(f"closed_script {lang}: statements {got} are not {ids}")
        consent = set(script[lang]["statements"]["c_consent"])
        want = {m.value for m in ConsentMethod} | {"none"}
        if consent != want:
            raise ValueError(f"closed_script {lang}: c_consent variants {sorted(consent)} are not {sorted(want)}")


# ---------------------------------------------------------------- mechanical checks

_DIGIT = re.compile(r"[0-9०-९]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN_WORD = re.compile(r"^[A-Za-z][A-Za-z'.\-]*[,.!?]*$")


def _latin_run(text: str) -> int:
    best = run = 0
    for token in text.split():
        run = run + 1 if _LATIN_WORD.match(token) else 0
        best = max(best, run)
    return best


def reply_problems(text: str, variant: str, language: str) -> list[str]:
    if not text or not text.strip():
        return ["empty"]
    problems = []
    if _DIGIT.search(text):
        problems.append("digit")
    if len(text) > LIMIT[variant]:
        problems.append(f"over_{LIMIT[variant]}_chars")
    if not _DEVANAGARI.search(text):
        problems.append("no_devanagari")
    if language == "hi" and _latin_run(text) > 3:
        problems.append("latin_run_over_3")
    return problems


def check_replies(replies: dict[str, dict[str, str]], language: str) -> list[dict[str, str]]:
    return [{"key": key, "variant": variant, "check": problem}
            for key, versions in replies.items()
            for variant, text in versions.items()
            for problem in reply_problems(text, variant, language)]


# ---------------------------------------------------------------- one arm of one customer


def run_arm(client: LlmClient, model: str, schema: type[BaseModel], system: str, user: str,
            language: str, customer_id: str, arm: str) -> dict[str, Any]:
    """Ask, check, ask again (at most twice more) while a reply fails a mechanical check.
    Keeps the first attempt with no failure, else the attempt with fewest failures (earliest on a tie)."""
    requests, attempts, usd = [], [], 0.0
    for attempt in range(1, MAX_EXTRA_ATTEMPTS + 2):
        messages = [Message(role="system", content=system), Message(role="user", content=with_attempt(user, attempt))]
        row = {"id": customer_id, "arm": arm, "model": model, "attempt": attempt,
               "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS, "schema": schema.__name__,
               "messages": [m.model_dump() for m in messages]}
        try:
            result = client.complete(schema, messages, model=model, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
        except LlmOutputInvalid as exc:  # any other error (cap, transport, auth) stops the run; --resume continues it
            row["error"] = type(exc).__name__
            requests.append(row)
            attempts.append((None, [{"key": "*", "variant": "*", "check": f"request_failed:{type(exc).__name__}"}]))
            continue
        usd += result.usd
        row.update(reported_model=result.model, prompt_tokens=result.prompt_tokens,
                   completion_tokens=result.completion_tokens, generation_id=result.generation_id)
        requests.append(row)
        replies = result.value.model_dump()
        problems = check_replies(replies, language)
        attempts.append((replies, problems))
        if not problems:
            break
    regenerated = [{"arm": arm, "attempt": i + 1, "reasons": sorted({p["check"] for p in probs})}
                   for i, (_, probs) in enumerate(attempts) if probs and i + 1 < len(attempts)]
    best = min(range(len(attempts)), key=lambda i: (attempts[i][0] is None, len(attempts[i][1]), i))
    replies, problems = attempts[best]
    return {"replies": replies, "failed": [{"arm": arm, **p} for p in problems], "regenerated": regenerated,
            "kept_attempt": best + 1, "requests": requests, "usd": usd}


def writer_models(customers: list[dict[str, Any]]) -> dict[str, str]:
    """Customer id -> writer model. Within each language, customers sorted by id alternate A, B, A, ...
    so the model is not confounded with the language. A pure function of the customers file."""
    out: dict[str, str] = {}
    for language in sorted({c["language"] for c in customers}):
        ids = sorted(c["id"] for c in customers if c["language"] == language)
        out.update({cid: MODEL_A if rank % 2 == 0 else MODEL_B for rank, cid in enumerate(ids)})
    return out


def write_customer(client: LlmClient, customer: dict[str, Any], record: CallRecord, topics: dict[str, Any],
                   script: dict[str, Any], model: str | None) -> dict[str, Any]:
    language = customer["language"]
    if model is None:
        raise ValueError("write_customer needs a model (see writer_models)")
    system = system_prompt(language, topics)
    closed = render_closed(record, language, script, topics)
    open_arm = run_arm(client, model, open_schema(topics), system, open_user_message(customer, topics),
                       language, customer["id"], "open")
    closed_arm = run_arm(client, model, closed_schema(topics), system, closed_user_message(customer, closed),
                         language, customer["id"], "closed")
    row = {"id": customer["id"], "language": language, "writer_model": model,
           "writer_model_by_arm": {"open": model, "closed": model},
           "open": open_arm["replies"], "closed": closed_arm["replies"],
           "checks": {"regenerated": open_arm["regenerated"] + closed_arm["regenerated"],
                      "failed": open_arm["failed"] + closed_arm["failed"]}}
    return {"row": row, "requests": open_arm["requests"] + closed_arm["requests"],
            "usd": open_arm["usd"] + closed_arm["usd"]}


# ---------------------------------------------------------------- inputs


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_customers(path: Path = CUSTOMERS) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_record(record_id: str, directory: Path = RECORDS) -> CallRecord:
    return CallRecord.model_validate_json((directory / f"{record_id}.json").read_bytes())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records_digest(directory: Path = RECORDS) -> str:
    """sha256 of one line per `*.json` file, sorted by name: `<sha256 of the bytes>  <file name>\n`."""
    lines = "".join(f"{sha256(path)}  {path.name}\n" for path in sorted(directory.glob("*.json"), key=lambda p: p.name))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def input_digests() -> dict[str, str | None]:
    """The digests FROZEN.json["inputs"] must hold; None for a missing input. Hashes bytes only:
    gold.jsonl is never parsed or printed."""
    digests: dict[str, str | None] = {name: sha256(P5 / name) if (P5 / name).exists() else None
                                      for name in FROZEN_INPUTS}
    digests["records"] = records_digest() if RECORDS.is_dir() else None
    return digests


def frozen_problems() -> list[str]:
    if not FROZEN.exists():
        return [f"{FROZEN.relative_to(ROOT)} does not exist: freeze the gold before any customer words are written"]
    listed = load_json(FROZEN).get("inputs", {})
    problems = []
    for name, digest in input_digests().items():
        if name not in listed:
            problems.append(f"FROZEN.json lists no sha256 for {name}")
        elif digest is None:
            problems.append(f"{name} is listed in FROZEN.json but missing on disk")
        elif digest != listed[name]:
            problems.append(f"{name} on disk does not match its sha256 in FROZEN.json")
    return problems


# ---------------------------------------------------------------- built-in smoke examples (not part of the set)

EXAMPLES: list[tuple[dict[str, Any], Path]] = [
    ({"id": "SMOKE-1", "language": "hi-en", "record_id": "hero",
      "speaker": {"who": "borrower", "relation": None, "gender": "m"},
      "fact_sheet": {
          "you_are": "Ramesh, born 1984.",
          "what_happened": "Last month you took a gold loan of about five lakh from your bank. The officer said you "
                           "also had to open an FD 'for loan security'. About fifty-two thousand was cut from the loan "
                           "money for it. He said without it the loan would not be passed. You signed many pages at the "
                           "branch; nobody explained them.",
          "what_you_know": ["You took a gold loan of about five lakh from your bank last month.",
                            "About fifty-two thousand was cut from the loan money for the FD.",
                            "The officer said the loan would not be passed without the FD.",
                            "You believe the money is yours and you can take it out later.",
                            "You signed many pages at the branch."],
          "what_you_do_not_know": ["How long it runs.", "Whether you could cancel it.", "What you get from it.",
                                   "What the pages you signed said."],
          "how_you_talk": "Friendly, a little busy, short answers, Hindi mixed with English.",
          "on_this_call": "You are happy to talk for a few minutes and answer what you can."}},
     ROOT / "samajh" / "server" / "records" / "hero.json"),
    ({"id": "SMOKE-2", "language": "hi", "record_id": "third-party",
      "speaker": {"who": "third_party", "relation": "husband", "gender": "m"},
      "fact_sheet": {
          "you_are": "Mahesh, Sunita's husband, about fifty. Sunita has gone to her mother's place and left her phone at home; you pick it up.",
          "what_happened": "Sunita took a personal loan a couple of weeks ago for the house repairs. She went to the "
                           "office alone and dealt with it herself.",
          "what_you_know": ["The phone is Sunita's, not yours.", "Sunita took a loan recently for house repairs.",
                            "Sunita will be back in two or three days."],
          "what_you_do_not_know": ["What papers Sunita signed.", "Whether anything else was taken with the loan.",
                                   "How much was paid for anything.", "Sunita's year of birth by heart."],
          "how_you_talk": "Polite, plain village Hindi, a little suspicious of calls about money.",
          "on_this_call": "You do not pretend to be Sunita. You would rather the caller speak to her when she is back."}},
     ROOT / "samajh" / "server" / "records" / "third-party.json"),
]


# ---------------------------------------------------------------- commands


def cmd_models(_: argparse.Namespace) -> None:
    print("Writer models (within each language, customers sorted by id alternate A, B, A, ...):")
    for label, model in (("A", MODEL_A), ("B", MODEL_B)):
        print(f"  {label}: {model}\n     {MODELS_WHY[model]}")
    if CUSTOMERS.exists():
        customers = load_customers()
        assigned = writer_models(customers)
        counts = Counter((assigned[c["id"]], c["language"], c["kind"]) for c in customers)
        print(f"Assignment over {CUSTOMERS.relative_to(ROOT)} ({len(customers)} customers): model, language, kind, count")
        for (model, language, kind), n in sorted(counts.items()):
            print(f"  {model:32} {language:6} {kind:32} {n}")
        for model in (MODEL_A, MODEL_B):
            by_lang = Counter(c["language"] for c in customers if assigned[c["id"]] == model)
            print(f"  total {model}: {dict(sorted(by_lang.items()))}")
    print(f"Temperature {TEMPERATURE} (sent where defaults.toml [llm.sampling] allows it). Not Anthropic, OpenAI or "
          "Mistral: the project's builders, extractor and classifier use those.")


def cmd_inputs_hash(_: argparse.Namespace) -> None:
    print(json.dumps(input_digests(), indent=2))


def cmd_render_closed(args: argparse.Namespace) -> None:
    topics, script = load_json(TOPICS), load_json(CLOSED_SCRIPT)
    check_script(script, topics)
    rows = []
    for c in load_customers():
        rendered = render_closed(load_record(c["record_id"]), c["language"], script, topics)
        rows.append({"id": c["id"], "language": c["language"], "record_id": c["record_id"], **rendered})
    out = Path(args.out)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {out}")


def cmd_smoke(args: argparse.Namespace) -> None:
    topics, script = load_json(TOPICS), load_json(CLOSED_SCRIPT)
    check_script(script, topics)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = LlmClient.from_env(model=MODEL_A, usd_cap=args.usd_cap)
    models = args.models.split(",") if args.models else [MODEL_A, MODEL_B]
    total = 0.0
    for customer, record_path in EXAMPLES:
        record = CallRecord.model_validate_json(record_path.read_bytes())
        for model in models:
            result = write_customer(client, customer, record, topics, script, model=model)
            total += result["usd"]
            stem = f"{customer['id']}__{model.replace('/', '_')}"
            (out / f"{stem}.replies.json").write_text(json.dumps(result["row"], ensure_ascii=False, indent=1), encoding="utf-8")
            (out / f"{stem}.requests.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["requests"]), encoding="utf-8")
            checks = result["row"]["checks"]
            print(f"{stem}: requests {len(result['requests'])}, regenerated {len(checks['regenerated'])}, "
                  f"failed {len(checks['failed'])}, usd {result['usd']:.4f}")
    print(f"total usd {total:.4f}")


def cmd_run(args: argparse.Namespace) -> None:
    problems = frozen_problems()
    if problems:
        sys.exit("refusing to run:\n  " + "\n  ".join(problems))
    if REPLIES.exists() and not args.resume:
        sys.exit(f"refusing to run: {REPLIES.relative_to(ROOT)} exists (pass --resume to continue it)")
    topics, script = load_json(TOPICS), load_json(CLOSED_SCRIPT)
    check_script(script, topics)
    customers = load_customers()
    records = {c["id"]: load_record(c["record_id"]) for c in customers}
    for c in customers:  # render every closed call before any request: a bad record stops the run here
        render_closed(records[c["id"]], c["language"], script, topics)

    done: dict[str, dict[str, Any]] = {}
    kept_requests: list[dict[str, Any]] = []
    if REPLIES.exists():
        done = {r["id"]: r for r in load_customers(REPLIES)}
        if REQUESTS.exists():
            kept_requests = [r for r in load_customers(REQUESTS) if r["id"] in done]
    REPLIES.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in done.values()), encoding="utf-8")
    REQUESTS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept_requests), encoding="utf-8")

    assigned = writer_models(customers)
    client = LlmClient.from_env(model=MODEL_A, usd_cap=args.usd_cap)
    lock = threading.Lock()
    spent = [0.0]
    todo = [c for c in customers if c["id"] not in done]

    def one(customer: dict[str, Any]) -> None:
        result = write_customer(client, customer, records[customer["id"]], topics, script,
                                model=assigned[customer["id"]])
        with lock:  # requests first, then the row: a resume drops requests whose row is missing
            with REQUESTS.open("a", encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in result["requests"])
            with REPLIES.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result["row"], ensure_ascii=False) + "\n")
            spent[0] += result["usd"]
            print(f"{customer['id']}: {result['row']['writer_model']}, failed {len(result['row']['checks']['failed'])}",
                  flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(one, todo))

    # Final order is the customers' order, so a rerun from the cache gives the same files.
    order = {c["id"]: i for i, c in enumerate(customers)}
    rows = sorted(load_customers(REPLIES), key=lambda r: order[r["id"]])
    reqs = sorted(load_customers(REQUESTS), key=lambda r: request_order(order, r))
    REPLIES.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    REQUESTS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reqs), encoding="utf-8")

    reasons = Counter(reason for r in rows for g in r["checks"]["regenerated"] for reason in g["reasons"])
    failures = [(r["id"], f) for r in rows for f in r["checks"]["failed"]]
    print(f"rows {len(rows)} of {len(customers)}; requests {len(reqs)}; USD spent this run {spent[0]:.4f}")
    print("regenerations by reason:", dict(reasons) or "none")
    print(f"failures kept: {len(failures)}")
    for cid, f in failures:
        print(f"  {cid} {f['arm']} {f['key']}.{f['variant']}: {f['check']}")


_ARM_RANK = {"open": 0, "closed": 1, "defer": 2}


def request_order(order: dict[str, int], r: dict[str, Any]) -> tuple[int, int, bool, int]:
    return order[r["id"]], _ARM_RANK[r["arm"]], bool(r.get("rewrite")), r["attempt"]


def without_defer(row: dict[str, Any]) -> dict[str, Any]:
    """The row as it was before add-defer: no defer replies, no defer model, no defer checks."""
    out = json.loads(json.dumps(row))
    for versions in out["open"].values():
        versions.pop("defer", None)
    out.get("writer_model_by_arm", {}).pop("defer", None)
    for key in ("regenerated", "failed"):
        out["checks"][key] = [x for x in out["checks"][key] if x["arm"] != "defer"]
    return out


def cmd_add_defer(args: argparse.Namespace) -> None:
    """One `defer` request per customer; the replies go into open[topic]["defer"]."""
    problems = frozen_problems()
    if problems:
        sys.exit("refusing to add defer replies:\n  " + "\n  ".join(problems))
    topics = load_json(TOPICS)
    customers = load_customers()
    before = load_customers(REPLIES)
    rows = {r["id"]: r for r in before}
    missing = [c["id"] for c in customers if c["id"] not in rows]
    if missing:
        sys.exit(f"refusing to add defer replies: no row for {missing}")
    has_defer = [r["id"] for r in before if "defer" in r.get("writer_model_by_arm", {})
                 or any("defer" in v for v in r["open"].values())]
    if has_defer and not args.resume:
        sys.exit(f"refusing to add defer replies: {len(has_defer)} rows have them already (pass --resume)")
    assigned = writer_models(customers)
    models = {}
    for c in customers:
        model = rows[c["id"]]["writer_model_by_arm"]["open"]
        if model != assigned[c["id"]] and not any(x["arm"] == "open" for x in rows[c["id"]]["checks"].get("rewritten", [])):
            sys.exit(f"refusing: {c['id']} open arm names {model}, the assignment {assigned[c['id']]}, and no rewrite is recorded")
        models[c["id"]] = model

    schema = defer_schema(topics)
    client = LlmClient.from_env(model=MODEL_A, usd_cap=args.usd_cap)

    def one(customer: dict[str, Any]) -> dict[str, Any]:
        return run_arm(client, models[customer["id"]], schema, defer_system_prompt(customer["language"], topics),
                       defer_user_message(customer, topics), customer["language"], customer["id"], "defer")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = dict(zip([c["id"] for c in customers], pool.map(one, customers), strict=True))

    after = []
    for c in customers:
        row, arm = without_defer(rows[c["id"]]), results[c["id"]]
        for topic_id, versions in arm["replies"].items():
            row["open"][topic_id]["defer"] = versions["defer"]
        row["writer_model_by_arm"]["defer"] = models[c["id"]]
        row["checks"]["regenerated"] += arm["regenerated"]
        row["checks"]["failed"] += arm["failed"]
        after.append(row)
    order = {c["id"]: i for i, c in enumerate(customers)}
    reqs = [r for r in load_customers(REQUESTS) if r["arm"] != "defer"]
    reqs += [r for c in customers for r in results[c["id"]]["requests"]]
    reqs.sort(key=lambda r: request_order(order, r))
    write_jsonl(REQUESTS, reqs)
    write_jsonl(REPLIES, after)

    reread = {r["id"]: r for r in load_customers(REPLIES)}
    old = {r["id"]: without_defer(r) for r in before}
    changed = [cid for cid, r in reread.items() if json.dumps(without_defer(r), ensure_ascii=False)
               != json.dumps(old[cid], ensure_ascii=False)]
    sent = [r for c in customers for r in results[c["id"]]["requests"]]
    reasons = Counter(reason for a in results.values() for g in a["regenerated"] for reason in g["reasons"])
    failures = [(cid, f) for cid, a in results.items() for f in a["failed"]]
    print(f"rows {len(reread)}; defer requests {len(sent)}; USD this run {sum(a['usd'] for a in results.values()):.4f}")
    print("regenerations by reason:", dict(reasons) or "none")
    print(f"failures kept: {len(failures)}")
    for cid, f in failures:
        print(f"  {cid} {f['key']}.{f['variant']}: {f['check']}")
    print(f"rows that differ from before once defer is removed: {changed or 'none'}")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def with_arm_models(row: dict[str, Any]) -> dict[str, Any]:
    """The row with `writer_model_by_arm` present (rows from before the field name the assigned model)."""
    by_arm = row.get("writer_model_by_arm") or {"open": row["writer_model"], "closed": row["writer_model"]}
    out = {k: v for k, v in row.items() if k != "writer_model_by_arm"}
    keys = list(out)
    out = {k: out[k] for k in keys[: keys.index("writer_model") + 1]} | {"writer_model_by_arm": by_arm} | \
          {k: out[k] for k in keys[keys.index("writer_model") + 1:]}
    return out


def cmd_rewrite(args: argparse.Namespace) -> None:
    """Repeat one arm's request with the other writer model when most of its replies fail a check."""
    problems = frozen_problems()
    if problems:
        sys.exit("refusing to rewrite:\n  " + "\n  ".join(problems))
    topics, script = load_json(TOPICS), load_json(CLOSED_SCRIPT)
    check_script(script, topics)
    customers = load_customers()
    customer = next((c for c in customers if c["id"] == args.id), None)
    if customer is None:
        sys.exit(f"refusing to rewrite: no customer {args.id}")
    before = load_customers(REPLIES)
    row = next((r for r in before if r["id"] == args.id), None)
    if row is None:
        sys.exit(f"refusing to rewrite: {args.id} has no row in {REPLIES.relative_to(ROOT)}")
    if any(x["arm"] == args.arm for x in row["checks"].get("rewritten", [])):
        sys.exit(f"refusing to rewrite: {args.id} {args.arm} was rewritten already")
    language = customer["language"]
    replies = row[args.arm]
    total = sum(len(v) for v in replies.values())
    failing = {(f["key"], f["variant"]) for f in check_replies(replies, language)}
    if not len(failing) * 2 > total:
        sys.exit(f"refusing to rewrite: {len(failing)} of {total} {args.arm} replies fail a check (needs more than half)")

    assigned = writer_models(customers)[args.id]
    if assigned != row["writer_model"]:
        sys.exit(f"refusing to rewrite: the row names {row['writer_model']}, the assignment {assigned}")
    from_model = with_arm_models(row)["writer_model_by_arm"][args.arm]
    to_model = MODEL_B if from_model == MODEL_A else MODEL_A
    system = system_prompt(language, topics)
    if args.arm == "open":
        schema, user = open_schema(topics), open_user_message(customer, topics)
    else:
        closed = render_closed(load_record(customer["record_id"]), language, script, topics)
        schema, user = closed_schema(topics), closed_user_message(customer, closed)
    sent_before = [r for r in load_customers(REQUESTS) if r["id"] == args.id and r["arm"] == args.arm]
    if not sent_before or sent_before[0]["messages"] != [{"role": "system", "content": system},
                                                         {"role": "user", "content": user}]:
        sys.exit("refusing to rewrite: the rebuilt request is not the one first sent for this arm")

    checks = sorted({f["check"] for f in check_replies(replies, language)})
    reason = (f"wrong script on {len(failing)} of {total} replies" if set(checks) <= {"no_devanagari", "latin_run_over_3"}
              else f"mechanical checks ({', '.join(checks)}) failed on {len(failing)} of {total} replies")
    client = LlmClient.from_env(model=to_model, usd_cap=args.usd_cap)
    arm = run_arm(client, to_model, schema, system, user, language, args.id, args.arm)

    new_row = with_arm_models(row)
    new_row[args.arm] = arm["replies"]
    new_row["writer_model_by_arm"] = {**new_row["writer_model_by_arm"], args.arm: to_model}
    old_checks = row["checks"]
    new_row["checks"] = {
        "regenerated": old_checks["regenerated"] + [{**g, "model": to_model} for g in arm["regenerated"]],
        "failed": [f for f in old_checks["failed"] if f["arm"] != args.arm] + arm["failed"],
        "rewritten": old_checks.get("rewritten", []) + [
            {"arm": args.arm, "from_model": from_model, "to_model": to_model, "reason": reason,
             "attempts": len(arm["requests"]), "kept_attempt": arm["kept_attempt"]}],
    }
    after = [new_row if r["id"] == args.id else with_arm_models(r) for r in before]
    order = {c["id"]: i for i, c in enumerate(customers)}
    after.sort(key=lambda r: order[r["id"]])
    reqs = load_customers(REQUESTS) + [{**r, "rewrite": True} for r in arm["requests"]]
    reqs.sort(key=lambda r: request_order(order, r))
    write_jsonl(REQUESTS, reqs)
    write_jsonl(REPLIES, after)

    strip = lambda r: {k: v for k, v in r.items() if k != "writer_model_by_arm"}
    reread = load_customers(REPLIES)
    old = {r["id"]: r for r in before}
    changed = [r["id"] for r in reread if r != old.get(r["id"])]
    changed_beyond_field = [r["id"] for r in reread if strip(r) != strip(old.get(r["id"], {}))]
    print(f"{args.id} {args.arm}: {from_model} -> {to_model}; {reason}; attempts {len(arm['requests'])}, "
          f"kept attempt {arm['kept_attempt']}; failures now {len(arm['failed'])}; USD {arm['usd']:.4f}")
    print(f"rows {len(reread)} (before {len(before)}); requests appended {len(arm['requests'])}")
    print(f"rows changed in full: {len(changed)} (writer_model_by_arm added where it was missing)")
    print(f"rows changed apart from writer_model_by_arm: {changed_beyond_field}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models").set_defaults(func=cmd_models)
    sub.add_parser("inputs-hash").set_defaults(func=cmd_inputs_hash)
    p = sub.add_parser("add-defer")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--usd-cap", type=float, default=0.60)
    p.set_defaults(func=cmd_add_defer)
    p = sub.add_parser("rewrite")
    p.add_argument("--id", required=True)
    p.add_argument("--arm", required=True, choices=["open", "closed"])
    p.add_argument("--usd-cap", type=float, default=0.10)
    p.set_defaults(func=cmd_rewrite)
    p = sub.add_parser("render-closed")
    p.add_argument("--out", default=str(CLOSED_OUT))
    p.set_defaults(func=cmd_render_closed)
    p = sub.add_parser("smoke")
    p.add_argument("--out", required=True)
    p.add_argument("--models", default="", help="comma-separated model ids (default: A and B)")
    p.add_argument("--usd-cap", type=float, default=0.30)
    p.set_defaults(func=cmd_smoke)
    p = sub.add_parser("run")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    # Estimate from the smoke test: about USD 0.6-0.95 for 60 customers with regenerations; 1.5 leaves headroom.
    p.add_argument("--usd-cap", type=float, default=1.5)
    p.set_defaults(func=cmd_run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
