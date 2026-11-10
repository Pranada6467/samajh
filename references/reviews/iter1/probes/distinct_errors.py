"""Verifier probe: the frozen run counted per distinct reply and per customer state. Cache only.

    uv run python references/reviews/iter1/probes/distinct_errors.py

The same templated reply recurs across scenarios (1,604 replies, 560 distinct by language,
question and text), and an identical request returns the cached output, so a field-weighted
score counts one reading many times. This recounts wrong readings per distinct reply, and
false clears by what the scenario says about the customer.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "eval" / "text_path"))

import run as builders_run  # noqa: E402
import scenario_sets  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.extract import SlotKind, slots  # noqa: E402
from samajh.pipeline import WithoutTemperature  # noqa: E402
from samajh.types import Verdict  # noqa: E402

MODEL = "openai/gpt-6-luna"
SLOT_OF = {**builders_run._ASKED_BY, "volunteered_claims": None, "sale_concerns": None}


def main() -> int:
    _, scenarios = scenario_sets.load("frozen")
    llm = WithoutTemperature(LlmClient.from_env(model=MODEL, usd_cap=0.0))
    runs = [builders_run.run_case(s, llm, MODEL) for s in scenarios]
    state = {json.loads(line)["id"]: json.loads(line)["customer_state"]
             for line in (ROOT / "data/scenarios/gold.jsonl").read_text().splitlines()}

    pairs = Counter()
    wrong_pairs = set()
    for r in runs:
        found = slots(r.scenario.transcript, r.scenario.record)
        for s in found:
            if s.kind is not SlotKind.other:
                pairs[(r.scenario.language.value, s.kind.value, s.turn.text)] += 1
        for f in r.score.fields:
            if f.ok:
                continue
            kinds = SLOT_OF.get(f.name)
            hit = [s for s in found if kinds and s.kind in kinds]
            if not hit:  # a claim or concern said in passing: charge the whole call once
                wrong_pairs.add((r.scenario.language.value, f.name, r.scenario.id))
            for s in hit:
                wrong_pairs.add((r.scenario.language.value, s.kind.value, s.turn.text))
    print(f"replies to a checked question: {sum(pairs.values())}; distinct (language, question kind, text): {len(pairs)}")
    reused = Counter(pairs.values())
    print("  times a distinct reply is used -> how many replies:", dict(sorted(reused.items())))
    print(f"distinct replies with at least one wrong field charged to them: {len(wrong_pairs)}")
    for w in sorted(wrong_pairs):
        print("   ", w, "used", pairs.get(w, "-"), "time(s)")

    by_state = Counter()
    clear_by_state = Counter()
    for r in runs:
        if r.score.gold_verdict is Verdict.clear:
            continue
        by_state[state[r.scenario.id]] += 1
        clear_by_state[state[r.scenario.id]] += r.score.false_clear
    print("\nfalse clears among gold-not-clear calls, by the scenario's customer state:")
    for name, n in sorted(by_state.items()):
        print(f"   {name}: {clear_by_state[name]} of {n}")
    harmed = sum(n for k, n in by_state.items() if k != "informed")
    print(f"   customers with a problem of their own (not 'informed'): "
          f"{sum(v for k, v in clear_by_state.items() if k != 'informed')} of {harmed} calls, "
          f"{harmed // 4} base cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
