"""Measure candidate models for the live LLM fallback on the labelled turn set. Spends OpenRouter money.

    uv run python tests/dialogue/probes/fallback_models.py OUT.json MODEL [MODEL ...]

For each model, every reply of `fixtures/turns_heldout.jsonl` is played into the real machine with
`LlmFallbackInterpreter(model=...)`. The LLM is asked only about the replies the rules leave as
plain `said`. Reported per model and fold: replies with the labelled effect, calls that ended on a
reply that was not a refusal, failed LLM calls, and the seconds each uncached call took. A rerun
answers from the client's cache, so its latency columns are empty: the numbers to keep are in OUT.json.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from samajh.clients.errors import ClientError
from samajh.clients.llm import LlmClient
from samajh.dialogue.__main__ import effect_of
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

ROWS = [
    json.loads(line)
    for line in (Path(__file__).parents[1] / "fixtures" / "turns_heldout.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
ENDS = {"decline", "human", "wrong_party"}
USD_CAP = 0.30


class Timed:
    """Passes calls to the client and keeps how long each took, and whether it failed."""

    def __init__(self, llm: LlmClient) -> None:
        self.llm, self.calls = llm, []

    def complete(self, schema, messages, **options):
        started = time.monotonic()
        try:
            result = self.llm.complete(schema, messages, **options)
        except ClientError as error:
            self.calls.append({"seconds": time.monotonic() - started, "error": type(error).__name__})
            raise
        self.calls.append(
            {"seconds": time.monotonic() - started, "cache_hit": result.cache_hit, "usd": result.usd}
        )
        return result


def measure(model: str) -> dict:
    timed = Timed(LlmClient.from_env(usd_cap=USD_CAP))
    interpreter = LlmFallbackInterpreter(timed, model=model)
    folds = {}
    for fold in (0, 1):
        rows = [row for row in ROWS if row["fold"] == fold]
        got = [
            effect_of(Language(row["language"]), row["question_key"], row["text"], interpreter)
            for row in rows
        ]
        folds[fold] = {
            "n": len(rows),
            "right": sum(
                g in (row["gold"], f"check_{row['gold']}") for g, row in zip(got, rows, strict=True)
            ),
            "ended_wrongly": sum(
                row["gold"] not in ENDS and g in ENDS for g, row in zip(got, rows, strict=True)
            ),
        }
    live = sorted(c["seconds"] for c in timed.calls if not c.get("cache_hit") and "error" not in c)
    return {
        "model": model,
        "folds": folds,
        "llm_calls": len(timed.calls),
        "failed": sum("error" in c for c in timed.calls),
        "errors": sorted({c["error"] for c in timed.calls if "error" in c}),
        "live_calls": len(live),
        "median_s": round(statistics.median(live), 2) if live else None,
        "p95_s": round(live[int(len(live) * 0.95) - 1], 2) if live else None,
        "max_s": round(live[-1], 2) if live else None,
        "usd": round(sum(c.get("usd", 0.0) for c in timed.calls), 5),
    }


def main(out: str, models: list[str]) -> None:
    results = []
    for model in models:
        result = measure(model)
        results.append(result)
        Path(out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        f0, f1 = result["folds"][0], result["folds"][1]
        print(
            f"{model}: fold 0 {f0['right']}/{f0['n']}, fold 1 {f1['right']}/{f1['n']}, "
            f"ended wrongly {f0['ended_wrongly'] + f1['ended_wrongly']}, failed {result['failed']}/"
            f"{result['llm_calls']} {result['errors']}, median {result['median_s']} s, "
            f"p95 {result['p95_s']} s, max {result['max_s']} s (n={result['live_calls']}), USD {result['usd']}",
            flush=True,
        )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
