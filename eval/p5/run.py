"""P5 stage 1 driver: open and closed calls on text, resumable. No Gnani call.

    uv run python eval/p5/run.py --out eval/p5/runs/NAME [--arms open,closed,terse] \
        [--levels 0,0.25,0.5,0.75,1] [--customers P5-C001,P5-C029] [--usd-budget 0.15] [--workers 4]

One JSON per call under OUT/calls/; a call whose file exists is skipped, so rerunning the same command
after a crash finishes the run and does nothing more. A call that raised stays as a "no result" file
and is not rerun. Refuses to start unless every digest in data/p5/FROZEN.json matches (bank.check_frozen).

`--usd-budget` is a hard stop on this process's OpenRouter spend (read from the client): no call starts
once it is reached. The client's own cap is set above it (2 x budget + 0.10) so that no turn degrades
silently on a cap mid-call. Arms: `open` (disposition rule, every level), `closed` (every level; not run
for opening-kind customers, data/p5/README.md), `terse` (open call with the open `go_along` replies, level
0 only, reported apart).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from bank import check_frozen, harness_hashes, load_customers, load_topics, resolve_data
from text_run import run_closed, run_open

ARMS = ("open", "closed", "terse")


def call_name(customer_id: str, arm: str, level: float) -> str:
    return f"{customer_id}__{arm}__L{level:g}.json"


def planned(customers, arms, levels) -> list[tuple[str, str, float]]:
    """(customer, arm, level) in a fixed order: per customer, open and closed next to each other."""
    out = []
    for level in levels:
        for c in customers:
            for arm in arms:
                if arm == "closed" and c.procedural:
                    continue
                if arm == "terse" and level != 0:
                    continue
                out.append((c.id, arm, level))
    return out


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arms", default="open,closed")
    parser.add_argument("--levels", default="0")
    parser.add_argument("--customers", default="", help="comma-separated ids; all 60 when empty")
    parser.add_argument("--usd-budget", type=float, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--data", default="data/p5", help="the frozen data directory (data/p5, data/p5b)")
    parser.add_argument("--label", default="", help="what this run is, kept in the manifest")
    args = parser.parse_args(argv)

    data = resolve_data(args.data)
    frozen = check_frozen(data)  # raises before anything runs
    arms = [a for a in args.arms.split(",") if a]
    if set(arms) - set(ARMS):
        parser.error(f"arms are {ARMS}")
    levels = [float(x) for x in args.levels.split(",") if x]
    topics = load_topics(data)
    if set(levels) - set(topics.levels_text):
        parser.error(f"levels are {topics.levels_text}")
    bank = load_customers(data)
    ids = [x for x in args.customers.split(",") if x] or sorted(bank)
    customers = [bank[i] for i in ids]

    from samajh.clients.llm import LlmClient
    from samajh.dialogue import RuleInterpreter
    from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter
    from samajh.pipeline import WithoutTemperature, run_text, takes_temperature

    cap = 2 * args.usd_budget + 0.10
    client = LlmClient.from_env(usd_cap=cap)
    extraction_model = client._model
    llm = client if takes_temperature(extraction_model) else WithoutTemperature(client)
    interpreter = LlmFallbackInterpreter(client, RuleInterpreter(), timeout_s=None)

    calls_dir = args.out / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    plan = planned(customers, arms, levels)
    manifest_path = args.out / "manifest.json"
    runs = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    manifest = {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_status_samajh_prompts": _git("status", "--porcelain", "samajh", "data/prompts"),
        "label": args.label,
        "data_dir": str(data.relative_to(ROOT)) if data.is_relative_to(ROOT) else str(data),
        "harness_sha256": harness_hashes(),
        "frozen_digests": frozen,
        "interpreter": {"class": "LlmFallbackInterpreter", "model": FALLBACK_MODEL, "timeout_s": None},
        "extraction_model": extraction_model,
        "second_reading": None,
        "second_reading_note": "text path: no second speech model; step(..., second_reading=None)",
        "arms": arms, "levels": levels, "customers": ids, "planned_calls": len(plan),
        "usd_budget": args.usd_budget, "client_usd_cap": cap,
    }  # fmt: skip

    lock = threading.Lock()
    stopped = threading.Event()
    counts = {"done": 0, "skipped": 0, "no_result": 0, "not_started": 0}

    def one(item: tuple[str, str, float]) -> None:
        cid, arm, level = item
        path = calls_dir / call_name(cid, arm, level)
        if path.exists():
            with lock:
                counts["skipped"] += 1
            return
        if stopped.is_set() or client.spent_usd >= args.usd_budget:
            stopped.set()
            with lock:
                counts["not_started"] += 1
            return
        customer = bank[cid]
        if arm == "closed":
            record = run_closed(customer, topics, level, interpreter)
        else:
            condition = "terse" if arm == "terse" else "disposition"
            record = run_open(customer, topics, level, condition, interpreter, llm, run_text)
        record["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
        with lock:
            counts["done"] += 1
            counts["no_result"] += record["status"] != "ok"
        print(f"{cid} {arm} L{level:g}: {record.get('outcome')} tier={record.get('tier')} "
              f"status={record['status']} spent={client.spent_usd:.4f}", flush=True)  # fmt: skip

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(one, plan))

    manifest |= {
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "usd_spent_this_process": round(client.spent_usd, 6),
        "budget_reached": stopped.is_set(),
        **counts,
    }
    runs.append(manifest)
    manifest_path.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("usd_spent_this_process", "budget_reached", *counts)}))
    return 2 if stopped.is_set() else 0


if __name__ == "__main__":
    raise SystemExit(main())
