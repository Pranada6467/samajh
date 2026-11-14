"""Have outside models write the replies for the scaffolds. Round-robin over three writers, 6 cases per request.

    uv run --project REPO python gen/write.py A|B|C
"""

from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)
from pydantic import BaseModel  # noqa: E402

from samajh.clients.llm import LlmClient, Message  # noqa: E402

HERE = Path(__file__).resolve().parent
WRITERS = ["openai/gpt-5-mini", "google/gemini-2.5-flash", "anthropic/claude-haiku-4.5"]
SPEND = HERE / "spend.jsonl"
_lock = threading.Lock()

SYSTEM = (
    "You write synthetic test data: what an ordinary person in India actually says on a phone call to an automated "
    "customer-care voice bot from a bank. Write natural spoken replies, the way a speech-to-text system would "
    "transcribe them: short, informal, fillers (haan ji, arey, accha, ek minute, matlab), chatter, code-mixing of "
    "Hindi and English, little or no punctuation sometimes. Use the requested script for each case. Never add stage "
    "directions, quotes around the reply, translations or explanations. Never use real phone numbers, account "
    "numbers or ID numbers. Follow each case's scenario exactly: it says who the speaker is and what they do. "
    "Vary the wording across cases; do not reuse the example phrases verbatim."
)


class CaseA(BaseModel):
    id: str
    replies: list[str]


class OutA(BaseModel):
    cases: list[CaseA]


class CaseB(BaseModel):
    id: str
    first: str
    followup: str


class OutB(BaseModel):
    cases: list[CaseB]


class CaseC(BaseModel):
    id: str
    first: str
    if_reask: str
    if_stop_check: str
    if_when: str


class OutC(BaseModel):
    cases: list[CaseC]


def prompt_a(batch: list[dict]) -> str:
    parts = ["For each case write exactly one reply per bot turn listed, in order (the `replies` list must have the "
             "same length as `bot_turns`)."]
    for c in batch:
        parts.append(json.dumps({"id": c["id"], "script": c["script"], "scenario": c["scenario"],
                                 "bot_turns": c["bot_questions"]}, ensure_ascii=False))
    return "\n".join(parts)


def prompt_b(batch: list[dict]) -> str:
    parts = ["The call is about a loan the customer took. For each case write `first`: the customer's reply to the bot "
             "question, holding exactly what the scenario says. Then write `followup`: the customer's reply if the bot "
             "then asks ONLY for the part the first reply left out (supply that missing part, briefly; for a refusal or "
             "don't-know case, stay consistent with it; if nothing was left out, a short 'jo bataya wahi' style reply). "
             "Any amount is said in words, never digits. The thing taken with the loan was a small insurance cover that "
             "pays off the loan if something happens to the borrower; the customer may or may not know that."]
    for c in batch:
        parts.append(json.dumps({"id": c["id"], "script": c["script"], "bot_question": c["question"],
                                 "first_reply_holds": c["scenario"]}, ensure_ascii=False))
    return "\n".join(parts)


def prompt_c(batch: list[dict]) -> str:
    parts = ["The call is about a loan the customer took; the bot is asking questions about something taken with the "
             "loan. For each case write `first`: the customer's reply to the bot question, doing exactly what the "
             "scenario says. Then the customer's reply in three possible next moments, consistent with the same "
             "attitude: `if_reask` (the bot asks the same question again in simpler words), `if_stop_check` (the bot "
             "asks 'shall I go on?'), `if_when` (the bot asks 'when shall we call you?'). A customer who was deferring "
             "or answering (not refusing) wants to talk now: in `if_when` they say to carry on now, and in "
             "`if_stop_check` they say yes go on. A customer who refused says no in both. Amounts in words, never "
             "digits."]
    for c in batch:
        parts.append(json.dumps({"id": c["id"], "script": c["script"], "bot_question": c["question"],
                                 "scenario": c["scenario"]}, ensure_ascii=False))
    return "\n".join(parts)


def main() -> int:
    bank = sys.argv[1]
    rows = [json.loads(x) for x in (HERE / "scaffolds" / f"{bank}.jsonl").read_text().splitlines() if x.strip()]
    schema, build = {"A": (OutA, prompt_a), "B": (OutB, prompt_b), "C": (OutC, prompt_c)}[bank]
    client = LlmClient.from_env(usd_cap=1.5)
    batches = [rows[i:i + 6] for i in range(0, len(rows), 6)]
    out: dict[str, dict] = {}

    def run(ix: int) -> None:
        batch = batches[ix]
        model = WRITERS[ix % len(WRITERS)]
        res = client.complete(schema, [Message(role="system", content=SYSTEM), Message(role="user", content=build(batch))],
                              model=model, temperature=None, max_tokens=6000)
        with _lock:
            with SPEND.open("a") as f:
                f.write(json.dumps({"bank": bank, "batch": ix, "model": model, "usd": res.usd, "cache": res.cache_hit}) + "\n")
            got = {c.id: c.model_dump() for c in res.value.cases}
            for c in batch:
                if c["id"] in got:
                    out[c["id"]] = c | got[c["id"]] | {"writer_model": model}
                else:
                    print("missing", c["id"], file=sys.stderr)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(run, range(len(batches))))
    ordered = [out[r["id"]] for r in rows if r["id"] in out]
    (HERE / f"written-{bank}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered))
    print(bank, len(ordered), "of", len(rows), "spent", client.spent_usd, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
