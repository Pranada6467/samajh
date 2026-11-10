"""Measure P2 round 2: the verifier's iteration-2 probes and the round-2 fresh set, three ways.

    uv run python tests/dialogue/probes/p2_round2_measure.py rules|llm|down [--fresh-only]

rules: the word lists alone (no classifier available). llm: the live classifier (OpenRouter, pinned
model, 2.5 s limit; spends a little; cached afterwards). down: a classifier that always fails, the
safe default. Prints counts with n, and for llm the classifier's added latency per uncached call.
"""

from __future__ import annotations

import importlib.util
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import p2_round2_fresh as fresh

from samajh.clients.errors import TransportError
from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.dialogue.__main__ import effect_of
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language, LoanRecord

RECORD = LoanRecord.model_validate_json((ROOT / "tests/dialogue/fixtures/record_gold_loan.json").read_text())
LOAN = re.compile(r"लोन|loan", re.IGNORECASE)
LENDER = "Udaharan Bank"
ENDED = {"decline", "human", "wrong_party", "language_switch", "no_response", "not_confirmed", "no_go_ahead"}


def _verifier(name: str):
    path = ROOT / "references/reviews/iter2/probes" / f"{name}.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(f"v_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Timed:
    """Wraps an LlmClient and records the wall time of every call that was not a cache hit."""

    def __init__(self, llm):
        self.llm, self.seconds, self.cached = llm, [], 0

    def complete(self, *args, **kwargs):
        began = time.monotonic()
        reply = self.llm.complete(*args, **kwargs)
        if reply.cache_hit:
            self.cached += 1
        else:
            self.seconds.append(time.monotonic() - began)
        return reply


class Down:
    def complete(self, *args, **kwargs):
        raise TransportError("down")


def third_party(cases, interpreter) -> tuple[int, int, int]:
    loan = lender = 0
    for lang, turns in cases:
        state, said = start(RECORD, Language(lang), lender_name=LENDER)
        texts = []
        for turn in turns:
            state, said = step(state, turn, interpreter=interpreter)
            lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
            texts += [line.text for line in lines]
            if isinstance(said, EndOfCall):
                break
        loan += any(LOAN.search(t) for t in texts)
        lender += any(LENDER in t for t in texts)
    return loan, lender, len(cases)


def replies(items, interpreter) -> dict[str, int]:
    tally = {"ended": 0, "stop_check": 0, "went_on": 0}
    for key, lang, text in items:
        effect = effect_of(Language(lang), key, text, interpreter)
        kind = "ended" if effect in ENDED else "stop_check" if effect.startswith("check_") else "went_on"
        tally[kind] += 1
    return tally


def main() -> int:
    mode = sys.argv[1]
    timed = None
    if mode == "rules":
        interpreter = RuleInterpreter()
    elif mode == "down":
        interpreter = LlmFallbackInterpreter(Down())
    else:
        from samajh.clients._runtime import RetryPolicy
        from samajh.clients.llm import LlmClient

        timed = Timed(LlmClient.from_env(usd_cap=1.0, timeout=10.0, retry=RetryPolicy(max_attempts=1)))
        interpreter = LlmFallbackInterpreter(timed)
    sets = [("fresh", fresh.THIRD_PARTY, fresh.REFUSALS, fresh.NON_REFUSALS)]
    if "--fresh-only" not in sys.argv:
        tp = _verifier("p2_third_party")
        rf = _verifier("p2_refusals")
        sets.append(
            ("verifier", [(lang, turns) for _, lang, turns in tp.SCRIPTS], rf.REFUSALS, rf.NON_REFUSALS)
        )
    for name, tps, refusals, non_refusals in sets:
        loan, lender, n = third_party(tps, interpreter)
        print(f"[{mode}] {name} third parties: loan named {loan}/{n}, lender named {lender}/{n}")
        r = replies(refusals, interpreter)
        print(f"[{mode}] {name} refusals: next question (went on) {r['went_on']}/{sum(r.values())}  {r}")
        nr = replies(non_refusals, interpreter)
        print(f"[{mode}] {name} non-refusals: call ended {nr['ended']}/{sum(nr.values())}  {nr}")
    if timed is not None:
        s = sorted(timed.seconds)
        if s:
            p95 = s[min(len(s) - 1, round(0.95 * (len(s) - 1)))]
            print(f"[llm] classifier latency, uncached calls: n={len(s)} median {statistics.median(s):.2f} s, "
                  f"p95 {p95:.2f} s, max {s[-1]:.2f} s; cache hits {timed.cached}")  # fmt: skip
        print(f"[llm] spent {timed.llm.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
