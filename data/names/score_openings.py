"""Score opening replies at the right-party check: false rejections of genuine borrowers, and the loan or lender named
to third parties, each per 100 with n and a Wilson 95% interval.

Input: JSONL, one row per case: {"id", "first_name" (the record's, Latin script), "language" ("hi" or "hi-en"),
"kind" ("borrower" or "third_party"), "replies": [what the speaker says to each bot question, in order]}. The call is
played from the start (no second check, the default lender setting) with one reply per bot turn until the call ends,
the right-party check passes, or the replies run out.

- A borrower case is a **false rejection** unless the check passes (`check_passed`) before the replies run out.
- A third-party case is a **leak** if the check passes or any bot line after the speaker's first reply names the
  lender or the loan (the iteration 3 verifiers' definition: lender names, लोन/loan/ऋण/बीमा/policy/premium/cover).

    uv run python data/names/score_openings.py CASES.jsonl [--llm] [--out RESULTS.jsonl]

`--llm` adds the turn classifier (OpenRouter through `samajh/clients/llm.py`, cached); without it the word lists alone.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from samajh.dialogue import EndOfCall, RuleInterpreter, TurnInterpreter, start, step
from samajh.types import Language, LoanRecord

LENDER = "Udaharan Bank"
NAMED = re.compile(
    r"Udaharan|उदाहरण|लोन|loan|ऋण|क़र्ज़|कर्ज|बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|cover", re.IGNORECASE
)
RECORD = {
    "loan_id": "LN-NAMES-0001",
    "lender_type": "bank",
    "loan_kind": "gold",
    "sanctioned_inr": 500000,
    "disbursed_inr": 448000,
    "disbursed_on": "2026-10-20",
    "products": [
        {
            "id": "P1",
            "kind": "credit_life",
            "provider": "Namoona Life (synthetic)",
            "premium_inr": 52000,
            "cover_inr": 500000,
            "term_months": 24,
            "paid_from_loan": True,
            "required_for_loan": False,
            "risk_mitigant": True,
            "provider_choice_offered": False,
            "cancel_window_days": 30,
            "features": [],
            "consent": None,
        }
    ],
}


def record_for(first_name: str) -> LoanRecord:
    borrower = {"name": f"{first_name} Kalpit", "dob": "1984-06-15", "language": "hi"}
    return LoanRecord.model_validate(RECORD | {"borrower": borrower})


def play_opening(first_name: str, language: Language, replies: list[str], interpreter: TurnInterpreter) -> dict:
    """Play the opening: did the check pass, was anything named after the first reply, and how did it end?"""
    state, said = start(record_for(first_name), language, lender_name=LENDER)
    named, used = False, 0
    for reply in replies:
        state, said = step(state, reply, interpreter=interpreter)
        used += 1
        lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
        named = named or any(NAMED.search(line.text) for line in lines)
        if isinstance(said, EndOfCall) or state.check_passed:
            break
    outcome = said.outcome.value if isinstance(said, EndOfCall) else None
    return {"passed": bool(state.check_passed), "named": named, "outcome": outcome, "replies_used": used}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 100.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (100 * max(0.0, centre - half), 100 * min(1.0, centre + half))


def _interpreter(use_llm: bool) -> TurnInterpreter:
    if not use_llm:
        return RuleInterpreter()
    from samajh.clients.llm import LlmClient
    from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter

    return LlmFallbackInterpreter(LlmClient.from_env(), model=FALLBACK_MODEL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    interpreter = _interpreter(args.llm)
    rows = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for row in rows:
        got = play_opening(row["first_name"], Language(row["language"]), row["replies"], interpreter)
        bad = not got["passed"] if row["kind"] == "borrower" else (got["passed"] or got["named"])
        results.append(row | got | {"error": bad})
    if args.out:
        Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    arm = "classifier on" if args.llm else "word lists only"
    for kind, label in (("borrower", "false rejections per 100 genuine borrowers"),
                        ("third_party", "loan or lender named per 100 third parties")):  # fmt: skip
        group = [r for r in results if r["kind"] == kind]
        k = sum(r["error"] for r in group)
        low, high = wilson(k, len(group))
        rate = 100 * k / len(group) if group else 0.0
        print(f"{arm}: {label}: {k} of {len(group)} = {rate:.1f} (Wilson 95% {low:.1f}-{high:.1f})")
        for r in group:
            if r["error"]:
                print(f"  {r['id']} {r['first_name']}: {r['replies']} -> {r['outcome']} passed={r['passed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
