"""Prisma v3.0 and v2.5 `verbatim` (hi-IN) on the FLEURS jobs, through GnaniClient only.

`uv run python eval/openbench/asr_prisma.py --set fleurs [--condition C] [--limit N] [--budget CREDITS]
[--subset-only] [--system S]`. Resumable: a job already transcribed without error is skipped. `--limit N` takes the
first N jobs per system and condition (already-done ones count). Stops cleanly on a busy slot, a rate limit, the credit cap or the run budget.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import store

from samajh.clients._runtime import Ledger, state_dir
from samajh.clients.errors import (
    ApiError,
    CapExceeded,
    LockTimeout,
    RateLimited,
)
from samajh.clients.gnani import GnaniClient, PrismaV25, PrismaV30, wav_seconds

SYSTEMS = {
    "prisma-v3.0-verbatim": PrismaV30(language="hi-IN", format="verbatim"),
    "prisma-v2.5-verbatim": PrismaV25(language="hi-IN", format="verbatim"),
}
CONDITIONS = ("native16k", "phone")
RATE = 0.010  # estimated credits per audio second (samajh/clients/defaults.toml)


def ledger_estimate() -> float:
    rows = [e for e in Ledger(state_dir() / "ledger.jsonl").entries() if e.provider == "gnani"]
    return round(sum(e.est_credits for e in rows), 4)


class Stop(Exception):
    pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["fleurs"])
    ap.add_argument("--condition", choices=CONDITIONS)
    ap.add_argument("--system", choices=sorted(SYSTEMS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--budget", type=float, default=120.0)
    ap.add_argument("--subset-only", action="store_true")
    a = ap.parse_args()

    jobs = store.read_jsonl(store.jobs_path(a.set))
    if not jobs:
        raise SystemExit(f"no jobs at {store.jobs_path(a.set)}; run fleurs.py jobs")
    if a.subset_only:
        jobs = [j for j in jobs if j["subset"]]
    conditions = [a.condition] if a.condition else list(CONDITIONS)
    systems = [a.system] if a.system else list(SYSTEMS)

    before = ledger_estimate()
    print(f"ledger estimate before: {before}")
    # A short lock wait: if a live call holds the slot we stop rather than queue for minutes.
    client = GnaniClient.from_env(lock_timeout=60.0)
    spent = 0.0
    counts = {"ok": 0, "cached": 0, "error": 0, "skipped_done": 0}
    try:
        for system in systems:
            path = store.transcripts_path(a.set, system)
            for cond in conditions:
                done = store.done(path)
                todo = [j for j in jobs if j["condition"] == cond]
                if a.limit is not None:
                    todo = todo[: a.limit]  # the first N jobs, done or not
                for job in todo:
                    if (job["item_id"], cond, job["audio_sha256"]) in done:
                        counts["skipped_done"] += 1
                        continue
                    audio = Path(job["audio_path"]).read_bytes()
                    est = wav_seconds(audio) * RATE
                    if spent + est > a.budget:
                        raise Stop(f"run budget: spent {spent:.3f} + {est:.3f} would cross {a.budget:g}")
                    t0 = time.monotonic()
                    row = {
                        "set": a.set,
                        "item_id": job["item_id"],
                        "condition": cond,
                        "system": system,
                        "audio_sha256": job["audio_sha256"],
                    }
                    try:
                        tr = client.stt(audio, SYSTEMS[system])
                    except (LockTimeout, RateLimited, CapExceeded) as e:
                        raise Stop(f"{type(e).__name__}: {e} (a live call may hold the slot)") from None
                    except ApiError as e:
                        if e.code in ("RATE_LIMITED", "gnani_busy"):
                            raise Stop(f"{e}") from None
                        store.append_row(
                            path,
                            {
                                **row,
                                "text": "",
                                "error": f"{type(e).__name__}: {e}"[:200],
                                "compute_s": round(time.monotonic() - t0, 3),
                                "meta": {},
                            },
                        )
                        counts["error"] += 1
                        continue
                    spent += tr.call.est_credits
                    counts["cached" if tr.call.cache_hit else "ok"] += 1
                    store.append_row(
                        path,
                        {
                            **row,
                            "text": tr.text,
                            "error": None,
                            "compute_s": round(time.monotonic() - t0, 3),
                            "meta": {
                                "request_id": tr.request_id,
                                "est_credits": tr.call.est_credits,
                                "cache_hit": tr.call.cache_hit,
                                "attempts": tr.call.attempts,
                                "model": tr.model,
                            },
                        },
                    )
    except Stop as e:
        print(f"stopped: {e}")
    print(json.dumps({"run_est_credits": round(spent, 4), **counts}))
    print(f"ledger estimate after: {ledger_estimate()}")


if __name__ == "__main__":
    main()
