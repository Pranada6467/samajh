"""Command line for the call core.

    uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi
    uv run python -m samajh.dialogue eval-turns --set tests/dialogue/fixtures/turns_heldout.jsonl [--llm]

`play` runs one call in the terminal: you type the customer's turns. `eval-turns` scores the turn
interpreter on a labelled set: it plays each reply into the real machine and compares the effect
on the call (answered, reask, decline, ...) with the label.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from samajh.dialogue.interpret import RuleInterpreter, TurnInterpreter
from samajh.dialogue.machine import (
    AtBirthYear,
    AtConsent,
    AtGoAhead,
    AtIdentity,
    AtReadBack,
    AtRecall,
    AtRestate,
    AtStopCheck,
    AtTeachBack,
    EndOfCall,
    Outcome,
    Position,
    _say,
    start,
    step,
)
from samajh.dialogue.prompts import PRODUCT_QUESTIONS, load_prompts
from samajh.types import Language, LoanRecord, Question


def _interpreter(use_llm: bool) -> TurnInterpreter:
    if not use_llm:
        return RuleInterpreter()
    from samajh.clients.llm import LlmClient
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    return LlmFallbackInterpreter(LlmClient.from_env())


def _play(args: argparse.Namespace) -> int:
    record = LoanRecord.model_validate_json(Path(args.record).read_text(encoding="utf-8"))
    language = Language(args.lang)
    interpreter = _interpreter(args.llm)
    state, said = start(record, language, lender_name=args.lender)
    print(f"[{language.value} prompts: {load_prompts(language).review}]")
    while True:
        for line in said.lines:
            print(f"BOT  [{line.step.value}{'/' + line.asks.value if line.asks else ''}] {line.text}")
        try:
            reply = input("YOU> ")
        except EOFError:
            print("\n[input ended before the call did]")
            return 1
        state, said = step(state, reply, interpreter=interpreter)
        if isinstance(said, EndOfCall):
            break
    for line in said.utterance.lines:
        print(f"BOT  [{line.step.value}] {line.text}")
    print(f"[call ended: {said.outcome.value}; unresolved questions: {len(said.unresolved)}]")
    if args.out:
        Path(args.out).write_text(said.transcript.model_dump_json(indent=2), encoding="utf-8")
        print(f"[transcript written to {args.out}]")
    return 0


_EVAL_RECORD = {
    "loan_id": "LN-EVAL-0001",
    "lender_type": "bank",
    "borrower": {"name": "Ramesh Namoona", "dob": "1984-06-15", "language": "hi"},
    "loan_kind": "gold",
    "sanctioned_inr": 500000,
    "disbursed_inr": 448000,
    "disbursed_on": "2026-10-20",
    "products": [
        {"id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
         "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
         "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30, "features": [],
         "consent": None}
    ],
}  # fmt: skip


def _position_for(question_key: str) -> Position:
    """Where the call stands when the bot has just said the line `question_key`."""
    stem = question_key.split(".")[0]
    if stem in {q.value for q in PRODUCT_QUESTIONS}:
        return AtTeachBack(product=0, question=Question(stem))
    fixed: dict[str, Position] = {
        "right_party.ask": AtIdentity(),
        "disclosure.go_ahead": AtGoAhead(),
        "second_check.ask": AtBirthYear(),
        "open_recall.ask": AtRecall(),
        "consent.ask": AtConsent(),
        "read_back.confirm": AtReadBack(product=0, amount_inr=52000, read_backs=1),
    }
    return fixed[question_key]


def effect_of(language: Language, question_key: str, text: str, interpreter: TurnInterpreter) -> str:
    """What one reply does to a call that has just asked `question_key`, by running the real machine."""
    state, _ = start(LoanRecord.model_validate(_EVAL_RECORD), language, lender_name="Namoona Bank")
    before = _position_for(question_key)
    state, _ = _say(state, before)
    after, said = step(state, text, interpreter=interpreter)
    if isinstance(said, EndOfCall):
        ends = {
            Outcome.declined: "decline",
            Outcome.human_requested: "human",
            Outcome.wrong_party: "wrong_party",
        }
        return ends.get(
            said.outcome, "confirmed" if said.outcome is Outcome.completed else said.outcome.value
        )
    now = after.position
    if isinstance(now, AtStopCheck):
        return f"check_{now.wish}"
    if isinstance(now, AtRestate):
        return "rejected"
    if isinstance(before, AtReadBack) and isinstance(now, AtReadBack):
        return "reask" if now.amount_inr == before.amount_inr else "corrected"
    if type(now) is type(before) and getattr(now, "reasked", False):
        return "reask"
    return {AtIdentity: "confirmed", AtGoAhead: "go"}.get(type(before), "answered")


def _eval_turns(args: argparse.Namespace) -> int:
    rows = [
        json.loads(line) for line in Path(args.set).read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if args.fold is not None:
        rows = [row for row in rows if row.get("fold") == args.fold]
    interpreter = _interpreter(args.llm)
    right: Counter[tuple[str, str]] = Counter()
    total: Counter[tuple[str, str]] = Counter()
    checked: Counter[tuple[str, str]] = Counter()  # honoured after the bot asked "do you want to stop?"
    confusions: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    results = []
    for row in rows:
        got = effect_of(Language(row["language"]), row["question_key"], row["text"], interpreter)
        for scope in (row["language"], "all"):
            total[scope, row["gold"]] += 1
            right[scope, row["gold"]] += got in (row["gold"], f"check_{row['gold']}")
            checked[scope, row["gold"]] += got == f"check_{row['gold']}"
            if got not in (row["gold"], f"check_{row['gold']}"):
                confusions[scope, row["gold"]][got] += 1
        results.append(row | {"got": got})
    for scope in sorted({scope for scope, _ in total}, key=lambda s: (s == "all", s)):
        n = sum(count for (s, _), count in total.items() if s == scope)
        ok = sum(count for (s, _), count in right.items() if s == scope)
        print(f"\n{scope}: {ok}/{n} replies had the labelled effect on the call")
        for gold in sorted({gold for s, gold in total if s == scope}):
            wrong = ", ".join(f"{got} x{count}" for got, count in confusions[scope, gold].most_common())
            line = f"  {gold:12s} {right[scope, gold]:3d}/{total[scope, gold]:<3d}"
            asked = f"  ({checked[scope, gold]} after a stop-check)" if checked[scope, gold] else ""
            print(line + asked + (f"  instead: {wrong}" if wrong else ""))
    if args.out:
        lines = "\n".join(json.dumps(r, ensure_ascii=False) for r in results)
        Path(args.out).write_text(lines + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m samajh.dialogue", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    play = commands.add_parser("play", help="play one call in the terminal")
    play.add_argument("--record", required=True, help="path to a LoanRecord JSON file (synthetic)")
    play.add_argument("--lang", required=True, choices=[language.value for language in Language])
    play.add_argument("--lender", default="Namoona Bank", help="lender name spoken in the disclosure")
    play.add_argument("--llm", action="store_true", help="add the LLM fallback (needs OPENROUTER_API_KEY)")
    play.add_argument("--out", help="write the finished transcript to this JSON file")
    play.set_defaults(run=_play)
    turns = commands.add_parser("eval-turns", help="score the turn interpreter on a labelled set")
    turns.add_argument("--set", required=True, help="JSONL rows: language, question_key, text, gold, fold")
    turns.add_argument("--fold", type=int, help="score only the rows of this fold")
    turns.add_argument("--llm", action="store_true", help="add the LLM fallback (needs OPENROUTER_API_KEY)")
    turns.add_argument("--out", help="write every row with what the interpreter read to this JSONL file")
    turns.set_defaults(run=_eval_turns)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
