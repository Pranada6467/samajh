"""Verifier probe: play the real Prisma transcript pairs of the amounts run into the dialogue's
premium question, and count which figure the call would go on to read back.

    uv run python references/reviews/iter1/probes/dialogue_second_reading.py

Offline. Reads eval/amounts/run/stt.jsonl (phone condition, format=transcribe, the item's language)
and data/amounts/amounts-v1.jsonl (gold). The audio is Timbre TTS over a simulated phone line, one
amount per sentence, and the amount parser has since been tuned on these same 240 sentences, so the
counts are in-sample and say nothing about real callers. They compare the two orders of the readings.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from samajh.dialogue import start, step
from samajh.dialogue.machine import AtTeachBack, _say
from samajh.types import Language, LoanRecord, Question

ROOT = Path(__file__).resolve().parents[4]
RECORD = LoanRecord.model_validate(
    {
        "loan_id": "LN-VERIFY-0002", "lender_type": "bank",
        "borrower": {"name": "Ramesh Namoona", "dob": "1984-06-15", "language": "hi"},
        "loan_kind": "gold", "sanctioned_inr": 500000, "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
        "products": [{
            "id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
            "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
            "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30, "features": [],
            "consent": None}],
    }
)  # fmt: skip


def stored_figure(language: Language, first: str, second: str | None) -> tuple[int | None, bool | None]:
    """(the premium the call holds after this reply, whether the two readings agreed)."""
    state, _ = start(RECORD, language, lender_name="Namoona Bank")
    state, _ = _say(state, AtTeachBack(product=0, question=Question.premium))
    state, _ = step(state, first, second_reading=second)
    agreed = state.second_readings[-1].agreed if state.second_readings else None
    return state.premium_of(0), agreed


def main() -> None:
    gold = {}
    for line in (ROOT / "data/amounts/amounts-v1.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        gold[row["id"]] = (Language(row["language"]), row["gold"]["amount_inr"], row["tags"]["stratum"])
    readings: dict[tuple[str, str], str] = {}
    literal: dict[str, str] = {}
    for line in (ROOT / "eval/amounts/run/stt.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        stt = row["stt"]
        if row["condition"] == "phone" and stt["format"] == "transcribe" and stt["language"] == "item":
            readings[row["item_id"], stt["model"]] = row["text"]
            if stt["model"] == "prisma-v2.5" and row.get("literal"):
                literal[row["item_id"]] = row["literal"]
    assert len(readings) == 480, len(readings)

    plans = {
        "v3.0 alone": lambda i: (readings[i, "prisma-v3.0"], None),
        "v2.5 alone": lambda i: (readings[i, "prisma-v2.5"], None),
        "v3.0 first, v2.5 second": lambda i: (readings[i, "prisma-v3.0"], readings[i, "prisma-v2.5"]),
        "v2.5 first, v3.0 second": lambda i: (readings[i, "prisma-v2.5"], readings[i, "prisma-v3.0"]),
        "v2.5 literal first, v3.0 second": lambda i: (literal.get(i, readings[i, "prisma-v2.5"]), readings[i, "prisma-v3.0"]),
        "v2.5 literal alone": lambda i: (literal.get(i, readings[i, "prisma-v2.5"]), None),
        "v2.5 literal first, v2.5 transcribe second (one call)": lambda i: (literal.get(i, readings[i, "prisma-v2.5"]), readings[i, "prisma-v2.5"]),
    }  # fmt: skip
    print(f"{'order of readings':34s} right  WRONG  none   | agreed: right/all | wrong held, by language")
    for name, plan in plans.items():
        tally: Counter[str] = Counter()
        agreed_right = agreed_all = 0
        wrong_by_language: Counter[str] = Counter()
        examples = []
        for item, (language, amount, stratum) in gold.items():
            first, second = plan(item)
            held, agreed = stored_figure(language, first, second)
            kind = "none" if held is None else ("right" if held == amount else "wrong")
            tally[kind] += 1
            if agreed:
                agreed_all += 1
                agreed_right += held == amount
            if kind == "wrong":
                wrong_by_language[language.value] += 1
                if len(examples) < 4:
                    examples.append(f"{item} [{stratum}] gold {amount} held {held}: {first!r} | {second!r}")
        print(f"{name:34s} {tally['right']:5d}  {tally['wrong']:5d}  {tally['none']:4d}   | "
              f"{agreed_right}/{agreed_all:<12d} | {dict(wrong_by_language)}")  # fmt: skip
        for example in examples:
            print(f"      {example}")


if __name__ == "__main__":
    main()
