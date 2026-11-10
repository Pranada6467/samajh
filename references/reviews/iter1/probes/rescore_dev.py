"""Verifier probe: rescore the development-set runs of four models from the LLM cache. Writes nothing.

    uv run python references/reviews/iter1/probes/rescore_dev.py

usd_cap=0, so a cache miss raises instead of spending and shows up as an error count.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "eval" / "text_path"))

import run as builders_run  # noqa: E402
import scenario_sets  # noqa: E402
from scoring import by_language  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.pipeline import WithoutTemperature  # noqa: E402

MODELS = ["openai/gpt-6-luna", "anthropic/claude-haiku-5.5", "mistralai/mistral-small-3.2-24b-instruct",
          "google/gemini-2.5-flash-lite"]


def main() -> int:
    _, scenarios = scenario_sets.load("dev")
    for model in MODELS:
        client = LlmClient.from_env(model=model, usd_cap=0.0)
        llm = WithoutTemperature(client) if model.startswith(("openai/gpt-6-luna", "anthropic/")) else client
        runs = [builders_run.run_case(s, llm, model) for s in scenarios]
        g = by_language([r.score for r in runs])["all"]
        traces = [t for r in runs if r.run for t in r.run.extraction.slots]
        print(f"{model}: errors {g.errors}; requests {len(traces)} (cache hits {sum(t.cache_hit for t in traces)}); "
              f"false clear {g.false_clear}; false alarm {g.false_alarm}; verdict {g.case_verdict}; fields {g.all_fields}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
