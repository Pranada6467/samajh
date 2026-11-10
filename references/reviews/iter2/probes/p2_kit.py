"""Shared runner for the P2 verification probes (iteration 2). Rules only unless an interpreter is passed."""

from __future__ import annotations

import json
import re
from pathlib import Path

from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.types import Language, LoanRecord

ROOT = Path(__file__).resolve().parents[4]
RECORD = LoanRecord.model_validate_json((ROOT / "tests/dialogue/fixtures/record_gold_loan.json").read_text())
LENDER = "Udaharan Bank"
RULES = RuleInterpreter()

# What tells a stranger that a loan, a lender relationship, a product or an amount exists.
LEAK = re.compile(r"Udaharan|लोन|loan|बीमा|insurance|पैसे|रक़म|रुपये|rupees|\d", re.I)


def play(turns, *, lang="hi", interpreter=RULES, record=RECORD, seconds=None):
    """Play scripted turns; returns (log, outcome, end). log: list of (who, text, keys)."""
    state, said = start(record, Language(lang), lender_name=LENDER)
    log = [("BOT", said.text, [l.key for l in said.lines])]
    seconds = seconds or {}
    for k, turn in enumerate(turns):
        state, said = step(state, turn, second_reading=seconds.get(k), interpreter=interpreter)
        log.append(("YOU", turn, []))
        if isinstance(said, EndOfCall):
            log.append(("BOT", said.utterance.text, [l.key for l in said.utterance.lines]))
            return log, said.outcome.value, said
        log.append(("BOT", said.text, [l.key for l in said.lines]))
    return log, f"open@{state.position.at}", state


def bot_after_first(log):
    """Bot text said after the customer's first reply."""
    return [text for who, text, _ in log[2:] if who == "BOT"]


def dump(log):
    return "\n".join(f"  {who}: {text}" for who, text, _ in log)


def save(name, rows):
    out = ROOT / "references/reviews/iter2/probes" / f"{name}.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
