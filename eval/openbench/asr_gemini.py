"""Gemini as a closed reference transcriber (not an open baseline), through `samajh/clients/llm.py`.

    uv run python eval/openbench/asr_gemini.py --set amounts-v2|realvoice|fleurs [--condition C]
        [--limit N] [--subset-only | --only-field NAME] [--workers N] --usd-cap X

Every request goes through `LlmClient` (cache, ledger, USD cap). The model and prompt are fixed here
before any counted run (PLAN.md). Rows go to `store.transcripts_path(set, "gemini")`; resumable: a job
already transcribed without error is skipped. A per-clip failure is written as an error row.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import itertools
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import json
import sys
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

from samajh.clients.errors import CapExceeded  # noqa: E402
from samajh.clients.llm import LlmClient  # noqa: E402

# Model id -> system id. Pro's reasoning ran to max_tokens on many clips (2026-11-14); Flash is the default.
SYSTEMS = {"google/gemini-3-flash-preview": "gemini-3-flash", "google/gemini-3.1-pro-preview": "gemini-3.1-pro"}
MODEL = "google/gemini-3-flash-preview"
MAX_TOKENS = 4096
GEMINI_PROMPT = (
    "Transcribe this audio clip verbatim. It is Indian speech, mostly Hindi, sometimes mixed with English. "
    "Write every word in the script of the language it is spoken in: Hindi words in Devanagari, English words "
    "in Latin letters. Write numbers and amounts as the words that were spoken, not as digits. Do not "
    "translate, correct, summarise or add anything. If a word is unclear, write your best guess of what was "
    "said. Return only the transcript."
)
PROMPT_SHA256 = hashlib.sha256(GEMINI_PROMPT.encode("utf-8")).hexdigest()


class AudioMessage(BaseModel):
    """`llm.Message` takes str content only; `LlmClient.complete` only calls `model_dump()` on each."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Literal["user"]
    content: list[dict[str, Any]]


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript: str


def message(wav: bytes) -> AudioMessage:
    return AudioMessage(
        role="user",
        content=[
            {"type": "text", "text": GEMINI_PROMPT},
            {"type": "input_audio", "input_audio": {"data": base64.b64encode(wav).decode("ascii"), "format": "wav"}},
        ],
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=store.SETS)
    ap.add_argument("--condition")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--subset-only", action="store_true")
    ap.add_argument("--only-field", help="keep only jobs whose boolean field NAME is true")
    ap.add_argument("--model", default=MODEL, choices=sorted(SYSTEMS))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--usd-cap", type=float, required=True)
    args = ap.parse_args(argv)

    jobs = store.read_jsonl(store.jobs_path(args.set))
    if not jobs:
        print(f"no jobs at {store.jobs_path(args.set)}", file=sys.stderr)
        return 1
    if args.condition:
        jobs = [j for j in jobs if j["condition"] == args.condition]
    field = args.only_field or ("subset" if args.subset_only else None)
    if field:
        jobs = [j for j in jobs if j.get(field) is True]
    model, system = args.model, SYSTEMS[args.model]
    out = store.transcripts_path(args.set, system)
    finished = store.done(out)
    todo = [j for j in jobs if (j["item_id"], j["condition"], j["audio_sha256"]) not in finished]
    if args.limit is not None:
        todo = todo[: args.limit]

    meta_path = out.parent / f"{system}.meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps(
            {"model": model, "system": system, "prompt": GEMINI_PROMPT, "prompt_sha256": PROMPT_SHA256, "max_tokens": MAX_TOKENS,
             "date": dt.date.today().isoformat(), "label": "closed reference"},
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    client = LlmClient.from_env(model=model, usd_cap=args.usd_cap, timeout=180.0)
    print(f"{len(jobs)} jobs, {len(jobs) - len(todo)} done or beyond --limit; running {len(todo)}")
    total = run_jobs(client, todo, out, workers=args.workers, model=model, system=system)
    print(f"total USD this run: {total:.4f} (client spent {client.spent_usd:.4f})")
    return 0


def transcribe(client, job: dict, model: str = MODEL, system: str = SYSTEMS[MODEL]) -> tuple[dict, bool]:
    """One job to one row; the flag is True when the USD cap refused it (no row is then written)."""
    row = {k: job[k] for k in ("set", "item_id", "condition", "audio_sha256")}
    row["system"] = system
    started = time.monotonic()
    try:
        wav = Path(job["audio_path"]).read_bytes()
        if hashlib.sha256(wav).hexdigest() != job["audio_sha256"]:
            raise ValueError("audio_sha256 mismatch")
        result = client.complete(Transcript, [message(wav)], model=model, max_tokens=MAX_TOKENS)
        row.update(
            text=result.value.transcript, error=None,
            meta={"model": result.model, "usd": result.usd, "prompt_tokens": result.prompt_tokens,
                  "completion_tokens": result.completion_tokens, "cache_hit": result.cache_hit},
        )
    except CapExceeded as exc:
        print(f"cap reached: {exc}")
        return row, True
    except Exception as exc:  # per-clip: record and go on
        row.update(text="", error=f"{type(exc).__name__}: {exc}"[:300], meta={"model": model})
    row["compute_s"] = round(time.monotonic() - started, 3)
    return row, False


def run_jobs(client, todo: list[dict], out: Path, *, workers: int = 1, model: str = MODEL,
             system: str = SYSTEMS[MODEL]) -> float:
    """Run `todo` on `workers` threads sharing one client (its spend and per-key lock are thread-safe).
    Rows are appended under one lock. After a CapExceeded no new job is submitted; in-flight ones finish."""
    write = threading.Lock()
    pending = iter(todo)
    stop = False
    total = 0.0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        running = {pool.submit(transcribe, client, job, model, system) for job in itertools.islice(pending, max(1, workers))}
        while running:
            finished, running = wait(running, return_when=FIRST_COMPLETED)
            for fut in finished:
                row, capped = fut.result()
                if capped:
                    stop = True
                    continue
                with write:
                    store.append_row(out, row)
                    total += row["meta"].get("usd") or 0.0
                    m = row["meta"]
                    print(f"{row['item_id']} {row['condition']} usd={m.get('usd')} "
                          f"completion={m.get('completion_tokens')} error={row['error']}", flush=True)
                if not stop:
                    job = next(pending, None)
                    if job is not None:
                        running.add(pool.submit(transcribe, client, job, model, system))
    return total


if __name__ == "__main__":
    raise SystemExit(main())
