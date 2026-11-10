"""Command line for the evaluation harness.

  uv run python -m samajh.evalkit status EXPERIMENT.toml     what is done, spent and still to pay
  uv run python -m samajh.evalkit run    EXPERIMENT.toml     voice, degrade, transcribe (resumable)
  uv run python -m samajh.evalkit score  EXPERIMENT.toml     write scores.jsonl and summary.md

The run store defaults to `run/` next to the experiment file. Audio lives under the state
directory (`.samajh/evalkit/<experiment name>/`), outside the repository.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from samajh.clients._runtime import Ledger, load_defaults, state_dir
from samajh.clients.gnani import GnaniClient
from samajh.evalkit.manifest import load_manifest
from samajh.evalkit.plan import load_experiment
from samajh.evalkit.runner import Job, Rates, RunStore, current_rows, jobs, run, run_spend
from samajh.evalkit.score import aggregate, cell_text, markdown_table, score
from samajh.evalkit.scorers import SCORERS

# Timbre speaks about this many characters a second on the pilot's sentences; only used to
# guess the length of clips that are not voiced yet.
_CHARS_PER_SECOND = 13.0


def remaining_estimate(planned: list[Job], store: RunStore, rates: Rates) -> tuple[int, int, float]:
    """(clips to voice, cells to transcribe, estimated credits for both)."""
    voiced = {row.fingerprint: row for row in store.voice_rows()}
    done = {row.fingerprint for row in store.stt_rows()}
    credits = 0.0
    to_voice: set[str] = set()
    cells = 0
    for job in planned:
        if job.fingerprint in done:
            continue
        cells += 1
        clip = voiced.get(job.voice_fingerprint)
        if clip is None and job.voice_fingerprint not in to_voice:
            to_voice.add(job.voice_fingerprint)
            credits += len(job.item.text) * rates.tts_credits_per_char
        seconds = clip.audio_seconds if clip else len(job.item.text) / _CHARS_PER_SECOND
        credits += seconds * rates.stt_credits_per_second
    return len(to_voice), cells, credits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m samajh.evalkit")
    parser.add_argument("command", choices=["status", "run", "score"])
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--store", type=Path, help="run store directory (default: run/ next to the file)")
    parser.add_argument("--max-items", type=int, help="only the first N manifest items")
    parser.add_argument("--budget", type=float, help="override the experiment's budget_credits")
    args = parser.parse_args(argv)

    experiment = load_experiment(args.experiment)
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    store = RunStore(args.store or args.experiment.parent / "run")
    defaults = load_defaults()["gnani"]
    rates = Rates(defaults["stt_credits_per_second"], defaults["tts_credits_per_char"])
    ledger = Ledger(state_dir() / "ledger.jsonl")
    planned = jobs(items, experiment, max_items=args.max_items)

    if args.command == "status":
        clips, cells, credits = remaining_estimate(planned, store, rates)
        spent = run_spend(store, ledger)
        print(f"items {len({job.item.id for job in planned})}, cells planned {len(planned)}")
        print(f"cells done {len(planned) - cells}, to transcribe {cells}, clips to voice {clips}")
        print(f"spent by this run (ledger estimate) {spent:.3f} credits")
        print(f"estimated to finish {credits:.3f} credits; budget {experiment.budget_credits:g}")
        return 0

    if args.command == "run":
        summary = run(
            experiment,
            items,
            client=GnaniClient.from_env(),
            store=store,
            audio_root=state_dir() / "evalkit" / experiment.name,
            ledger=ledger,
            rates=rates,
            max_items=args.max_items,
            budget_credits=args.budget,
        )
        print(
            f"planned {summary.planned}, already done {summary.already_done}, "
            f"transcribed {summary.transcribed}, voiced {summary.voiced}, errors {summary.errors}, "
            f"pending {summary.pending}, spent {summary.spent_credits:.3f} credits"
        )
        if summary.stopped:
            print(f"stopped: {summary.stopped}")
        return 0 if summary.pending == 0 else 1

    rows = score(items, current_rows(store, planned).values(), SCORERS[experiment.scorer])
    out = store.root
    (out / "scores.jsonl").write_text("".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8")
    by = ["language", "condition", "stt", "output", "method"]
    table = markdown_table(
        [*by, "correct/n (rate, Wilson 95%)"],
        ([*summary.group.values(), cell_text(summary)] for summary in aggregate(rows, by)),
    )
    (out / "summary.md").write_text(table + "\n", encoding="utf-8")
    print(f"{len(rows)} scored rows -> {out / 'scores.jsonl'}, {out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
