"""P3a verifier probe: recompute the frozen-set triage numbers from cached LLM calls only.

    SAMAJH_STATE_DIR=<scratch state with cache/openrouter symlinked> \
      uv run python references/reviews/iter2/probes/p3a_frozen_recompute.py <out.json>

Cap 0 USD: a cache miss raises (counted as an error), it never spends. Transcripts run one at a
time and one request at a time (max_workers=1), so no request races another. Writes one JSON row
per call (id, base, language, group, tier, verdict, gold verdict, flags, gaps) to <out.json>
outside the repo, and prints the headline triage numbers.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "eval" / "text_path"))
import run as tp  # noqa: E402
import scenario_sets  # noqa: E402
import triage  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.pipeline import WithoutTemperature, run_text, takes_temperature  # noqa: E402
from samajh.types import Verdict  # noqa: E402


def main() -> int:
    out = Path(sys.argv[1])
    _note, scenarios = scenario_sets.load("frozen")
    client = LlmClient.from_env(usd_cap=0.0)
    model = client._model
    llm = client if takes_temperature(model) else WithoutTemperature(client)
    rows, errors, hits, total = [], 0, 0, 0
    for s in scenarios:
        try:
            r = run_text(s.transcript, s.record, llm, model=model, max_workers=1)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            rows.append({"id": s.id, "error": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        total += len(r.extraction.slots)
        hits += sum(t.cache_hit for t in r.extraction.slots)
        gold_clear = s.gold.verdict is Verdict.clear
        rows.append({
            "id": s.id, "base": s.base, "language": s.language.value,
            "group": triage.group(s.customer_state, gold_clear),
            "tier": r.result.tier.value, "verdict": r.result.verdict.value, "gold": s.gold.verdict.value,
            "flags": sorted(f"{f.rule_id.value}:{f.reason.value}" for f in r.result.all_flags()),
            "gaps": sorted(f"{g.rule_id.value}:{g.reason.value}" for g in r.result.all_gaps()),
            "ceiling": s.perfect.tier.value if s.perfect else None,
        })
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    ok = [r for r in rows if "error" not in r]
    print(f"calls {len(rows)}, errors {errors}, requests {total}, cache hits {hits}")
    print("strict verdict agreement:", sum(r["verdict"] == r["gold"] for r in ok), "of", len(rows))
    for label, langs in triage.SLICES:
        sub = [r for r in ok if r["language"] in langs]
        for grp in ("problem", "informed_clear", "informed_flagged"):
            g = [r for r in sub if r["group"] == grp]
            miss = [r for r in g if r["tier"] in ("clear", "understanding_gap")]
            ref = [r for r in g if r["tier"] == "refer"]
            tiers = {}
            for r in g:
                tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
            print(f"{label:18} {grp:16} calls {len(g):3} bases {len({r['base'] for r in g}):2} | "
                  f"misses {len(miss)} calls / {len({r['base'] for r in miss})} bases | "
                  f"refer {len(ref)} calls / {len({r['base'] for r in ref})} bases | {tiers}")
            if grp == "problem" and miss:
                print("     missed:", sorted(r["id"] + "-" + r["language"] for r in miss))
    return 0


if __name__ == "__main__":
    sys.exit(main())
