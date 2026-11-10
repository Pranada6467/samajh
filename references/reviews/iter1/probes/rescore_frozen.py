"""Verifier probe: rescore the frozen text-path run from the LLM cache, writing nothing.

    uv run python references/reviews/iter1/probes/rescore_frozen.py

Uses the builders' loaders and scorers (eval/text_path) but not their `run.py main`, which
rewrites the report and `calls.jsonl`. The client has usd_cap=0, so a cache miss raises
`CapExceeded` instead of spending; misses are counted and printed. Independent checks at the
end recompute the headline numbers without the builders' `Summary` class.
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "eval" / "text_path"))

import e1  # noqa: E402
import run as builders_run  # noqa: E402
import scenario_sets  # noqa: E402
from scoring import by_language  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.pipeline import WithoutTemperature  # noqa: E402
from samajh.types import Verdict  # noqa: E402

MODEL = "openai/gpt-6-luna"


def main() -> int:
    note, scenarios = scenario_sets.load("frozen")
    print(note)
    llm = WithoutTemperature(LlmClient.from_env(model=MODEL, usd_cap=0.0))
    runs = [builders_run.run_case(s, llm, MODEL) for s in scenarios]

    errors = [r for r in runs if r.error]
    print(f"\nscenarios {len(runs)}; extractor/client errors {len(errors)}")
    for r in errors[:5]:
        print("  ", r.scenario.id, r.error[:200])
    traces = [t for r in runs if r.run for t in r.run.extraction.slots]
    print(f"LLM requests {len(traces)}; cache hits {sum(t.cache_hit for t in traces)}; "
          f"spent now ${sum(t.usd for t in traces):.5f}")

    # --- the builders' scorer -----------------------------------------------------------
    groups = by_language([r.score for r in runs])
    for name, g in groups.items():
        print(f"[builders' scorer] {name}: false clear {g.false_clear}; false alarm {g.false_alarm}; "
              f"verdict {g.case_verdict}; product {g.product_verdict}; fields {g.all_fields}; "
              f"flag P {g.precision()} R {g.recall()}")
    print(builders_run._span_stats(runs))
    print(builders_run._leaks(runs))
    print(builders_run._clusters(runs))
    print(builders_run._dev_overlap(runs))
    print(builders_run._e1(runs))

    # --- independent recount, from the gold file and the pipeline verdicts only -----------
    gold = {s.id: s.gold.verdict for s in scenarios}
    got = {r.scenario.id: (r.run.result.verdict if r.run else None) for r in runs}
    not_clear = [i for i, v in gold.items() if v is not Verdict.clear]
    clear = [i for i, v in gold.items() if v is Verdict.clear]
    fc = [i for i in not_clear if got[i] is Verdict.clear]
    fa = [i for i in clear if got[i] is not Verdict.clear]
    print(f"\n[independent] false clears {len(fc)}/{len(not_clear)} {fc}; "
          f"false alarms {len(fa)}/{len(clear)} {fa}; "
          f"verdicts right {sum(gold[i] is got[i] for i in gold)}/{len(gold)}")
    print("[independent] confusion", Counter((gold[i].value, got[i].value if got[i] else "error") for i in gold))
    wrong_fields = [(r.scenario.id, f.name, f.gold, f.got) for r in runs for f in r.score.fields if not f.ok]
    total_fields = sum(len(r.score.fields) for r in runs)
    print(f"[independent] fields right {total_fields - len(wrong_fields)}/{total_fields}; "
          f"wrong by language {Counter(i.rsplit('-', 1)[-1] if not i.endswith('hi-en') else 'hi-en' for i, *_ in wrong_fields)}")
    for row in wrong_fields:
        print("   ", row)
    # gold against the rule engine on the set's own extraction
    agree = sum(s.perfect.verdict is s.gold.verdict and
                frozenset((f.product_id, f.rule_id) for f in s.perfect.all_flags()) == s.gold.flags
                for s in scenarios)
    print(f"[independent] rule engine on gold extraction agrees with gold (verdict and flag set): {agree}/{len(scenarios)}")
    strata = Counter((s.yes_no.stratum, s.gold.verdict is Verdict.clear) for s in scenarios)
    print("[independent] strata", dict(strata))
    _ = e1
    return 0


if __name__ == "__main__":
    sys.exit(main())
