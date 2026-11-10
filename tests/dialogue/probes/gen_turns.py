"""Generate the held-out customer-turn set for the turn interpreter. Run by hand; spends OpenRouter cents.

    uv run python tests/dialogue/probes/gen_turns.py

Each row is a reply a customer might say to one bot question, with the effect that reply should
have on the call. A cheap model writes the replies from a behaviour description, so the label is
"what the writer was told to write", not a human judgement, and the Tamil and Kannada rows are not
human-reviewed. The writer model differs from the one the fallback interpreter uses. Rows are
split into two folds by a hash of the text: fold 0 may be used to tune the word lists, fold 1 is
only for reporting. The LLM client caches every call, so a rerun costs nothing and rewrites the
same file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from samajh.clients.llm import LlmClient, Message
from samajh.dialogue.prompts import LINES, load_prompts
from samajh.types import Language

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "turns_heldout.jsonl"
WRITER_MODEL = "google/gemini-2.5-flash-lite"
PER_CELL = 6

SPEECH = {
    Language.hi: "Hindi, in Devanagari script",
    Language.hi_en: "Hinglish (Hindi mixed with English words); write some replies in Devanagari with "
    "English words in Latin script and some fully in Latin script",
    Language.ta: "Tamil, in Tamil script, colloquial",
    Language.kn: "Kannada, in Kannada script, colloquial",
}

# (expecting, question line, effect the reply should have, what the customer does)
CELLS = [
    ("identity", "right_party.ask", "confirmed", "confirms that they are that person"),
    ("identity", "right_party.ask", "wrong_party",
     "is someone else: says it is a wrong number, or that the person is not there, or that they are a relative"),
    ("identity", "right_party.ask", "reask", "does not confirm; asks who is calling or what this is about"),
    ("go_ahead", "disclosure.go_ahead", "go", "agrees to continue with the call"),
    ("go_ahead", "disclosure.go_ahead", "decline", "refuses: is busy, or wants a call later, or does not want to talk"),
    ("open", "kind.ask", "answered",
     "answers the question: says what they think the thing is (a deposit, an insurance, a fee, some paper they signed)"),
    ("open", "kind.ask", "answered", "says they do not know or do not remember"),
    ("open", "kind.ask", "reask", "did not hear or did not understand the question and asks for it to be repeated"),
    ("open", "kind.ask", "decline", "wants to end this call right now: busy, call later, stop calling, will not talk"),
    ("open", "kind.ask", "human",
     "asks to speak to a human being, a staff member or an officer instead of the automated assistant"),
    ("open", "kind.ask", "reask",
     ("says something that has nothing to do with the question: the weather, another errand, or words to someone "
     "else in the room")),
    ("open", "kind.ask", "answered",
     ("answers with a complaint about how the thing was sold to them in the past: they did not want it, or said no "
     "but it was added anyway, or got no time to read, or learned of it later, or had spoken to the branch manager. "
     "They are NOT asking to end the call and NOT asking for a human now")),
    ("amount", "premium.ask", "answered", "states one amount in rupees, between 1,000 and 99,000"),
    ("amount", "premium.ask", "answered", "says they do not remember the amount"),
    ("told", "cancel_window.ask", "answered",
     "answers: either yes they were told, with a time limit, or no, nobody told them anything"),
    ("confirmation", "read_back.confirm", "confirmed", "confirms that the amount read back is right"),
    ("confirmation", "read_back.confirm", "rejected", "says the amount read back is wrong, without giving another number"),
]  # fmt: skip


class _Replies(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replies: list[str]


def question_text(language: Language, key: str) -> str:
    pack = load_prompts(language)
    slots = {"first_name": "Ramesh", "lender": "Namoona Bank", "ordinal": pack.ordinal(0),
             "amount_words": "fifty two thousand", "amount_digits": "52,000"}  # fmt: skip
    return pack.render(key, **{name: slots[name] for name in LINES[key].slots})


def main() -> None:
    llm = LlmClient.from_env(model=WRITER_MODEL, usd_cap=0.30)
    rows = []
    for language in Language:
        for cell, (expecting, key, effect, behaviour) in enumerate(CELLS):
            question = question_text(language, key)
            prompt = (
                f"On a phone call, a lender's automated assistant asked a customer in India:\n\n{question}\n\n"
                f"Write {PER_CELL} different replies the customer might SAY. In every reply the customer {behaviour}.\n"
                f"Language: {SPEECH[language]}. Spoken, everyday register, as a speech recogniser would write it "
                "down. Vary the wording and the length (two to fifteen words). No names, no real data."
            )
            result = llm.complete(
                _Replies, [Message(role="user", content=prompt)], temperature=0.9, max_tokens=700
            )
            for text in dict.fromkeys(reply.strip() for reply in result.value.replies if reply.strip()):
                digest = hashlib.sha256(f"{language.value}|{cell}|{text}".encode()).hexdigest()
                rows.append({"id": digest[:10], "fold": int(digest[10], 16) % 2, "language": language.value,
                             "expecting": expecting, "question_key": key, "gold": effect, "cell": cell,
                             "text": text})  # fmt: skip
    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {OUT}; spent USD {llm.spent_usd:.4f}")


if __name__ == "__main__":
    main()
