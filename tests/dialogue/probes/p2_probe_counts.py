"""Counts for the P2 report: the reviewers' probes and the P2 fresh probes, played into the call.

    uv run python tests/dialogue/probes/p2_probe_counts.py

Same sentences as tests/dialogue/test_p2_call_v2.py. Unlike the verifier's dialogue_attack.py, this
counts the new "when should we call?" question as stopping, not as the next question. Rules only, no
LLM. Counts of probes, not rates; all sentences are LLM-written text, not speech.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import test_p2_call_v2 as t
from dialogue_kit import play, record


def main() -> None:
    for name, sets in [("verifier", t.VERIFIER_THIRD_PARTY), ("fresh", t.FRESH_THIRD_PARTY)]:
        cases = [(lang, r) for lang, rs in sets.items() for r in rs]
        named = sum(t.loan_named(play(record(), lang, r)) for lang, r in cases)
        print(f"third party, {name}: loan named to {named}/{len(cases)}")
    for name, sets in [("verifier", t.VERIFIER_REFUSALS), ("fresh", t.FRESH_REFUSALS)]:
        tally = Counter(t.effect(t.at_first_question(lang), x) for lang, xs in sets.items() for x in xs)
        print(
            f"refusals, {name}: carried on to the next question on {tally['carried_on']}/{tally.total()}  {dict(tally)}"
        )
    for name, sets in [("verifier", t.VERIFIER_ACCOUNTS), ("fresh", t.FRESH_ACCOUNTS)]:
        tally = Counter(t.effect(t.at_first_question(lang), x) for lang, xs in sets.items() for x in xs)
        ended = sum(n for effect, n in tally.items() if effect.startswith("ended"))
        print(f"accounts of the sale, {name}: call ended on {ended}/{tally.total()}  {dict(tally)}")


if __name__ == "__main__":
    main()
