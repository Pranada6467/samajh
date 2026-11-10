"""Run the text path on typed transcripts and print each call's tier and reviewer summary.

    uv run python eval/text_path/run_transcript.py RECORD.json TRANSCRIPT.json [TRANSCRIPT.json ...]

For transcripts typed into the terminal player, such as the judge's probes in
`references/reviews/iter1/judge-probes/`. Makes OpenRouter calls through
`samajh.pipeline.default_llm()`; a second run is all cache hits.
"""

import sys
from pathlib import Path

from samajh.pipeline import default_llm, run_text
from samajh.rules.summary import summarise
from samajh.types import LoanRecord, Transcript


def main(record_path: str, *transcript_paths: str) -> int:
    record = LoanRecord.model_validate_json(Path(record_path).read_text())
    llm = default_llm()
    for path in transcript_paths:
        transcript = Transcript.model_validate_json(Path(path).read_text())
        # The terminal player stamps its own fixture's loan id on the transcript.
        transcript = transcript.model_copy(update={"loan_id": record.loan_id})
        run = run_text(transcript, record, llm)
        result = run.result
        slots = run.extraction.slots
        print(f"\n## {Path(path).name}: tier `{result.tier.value}` (strict verdict `{result.verdict.value}`)")
        print(
            f"{len(result.all_flags())} flags, {len(result.all_gaps())} gaps, "
            f"{len(slots)} LLM requests, {sum(s.usd for s in slots):.5f} USD"
        )
        for line in summarise(record, result).lines:
            print(f"- {line.tier.value}: {line.title}")
            print(f"    record: {line.record_value}")
            print(f"    quote (turn {line.turn_id}): {line.quote}")
            print(f"    paragraphs: {', '.join(line.clauses) or '-'}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    raise SystemExit(main(*sys.argv[1:]))
