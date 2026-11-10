"""Kill the runner with SIGKILL mid-run, resume, and count paid calls. Fake client only: no network.

  .venv/bin/python references/reviews/iter1/probes/amounts_kill_resume.py /path/to/scratch/repo /path/to/scratch/workdir

The fake client is the test suite's (tests/evalkit/evalkit_bench.py in the scratch copy), slowed down, and
with a file-backed cache so a repeated request behaves as the real client's cache would (a hit, unpaid).
Child mode (argv[3] == "child") runs one `run`; the parent kills it after a number of ledger rows.
Also: a run in which the client charges for a call and then fails (the "2xx that cannot be parsed" case).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

copy, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path[:0] = [str(copy), str(copy / "tests" / "evalkit")]

import evalkit_bench  # noqa: E402
import samajh  # noqa: E402
from samajh.clients.errors import BadResponse  # noqa: E402
from samajh.clients.gnani import CallInfo  # noqa: E402

assert Path(samajh.__file__).resolve().is_relative_to(copy), samajh.__file__


class DiskCacheClient(evalkit_bench.FakeClient):
    """Like the real client: a request already answered is a cache hit and is not paid again."""

    def __init__(self, ledger, cache_dir: Path, delay: float) -> None:
        super().__init__(ledger)
        self.cache_dir, self.delay = cache_dir, delay
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _row(self, kind, key, credits):
        marker = self.cache_dir / key
        if marker.exists():
            return CallInfo(cache_hit=True, cache_key=key, seconds=0.0, est_credits=0.0, attempts=0)
        time.sleep(self.delay)
        info = super()._row(kind, key, credits)  # the ledger row: the call is paid here
        marker.write_text("x")
        return info


def bench_at(root: Path, delay: float = 0.0):
    root.mkdir(parents=True, exist_ok=True)
    bench = evalkit_bench.Bench(root)
    bench.client = DiskCacheClient(bench.ledger, root / "cache", delay)
    return bench


def ledger_rows(root: Path) -> list[dict]:
    path = root / "ledger.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


if len(sys.argv) > 3 and sys.argv[3] == "child":
    root = Path(sys.argv[4])
    summary = bench_at(root, delay=0.01).run(budget_credits=float(sys.argv[5]) if len(sys.argv) > 5 else None)
    print(json.dumps({"transcribed": summary.transcribed, "already_done": summary.already_done, "voiced": summary.voiced,
                      "pending": summary.pending, "spent": round(summary.spent_credits, 4), "stopped": summary.stopped}))
    sys.exit(0)

CELLS, CLIPS = 72, 16
print(f"imported samajh from {Path(samajh.__file__).parent}")
for kill_after in (3, 11, 25, 40, 57, 70, 85):
    root = work / f"kill-{kill_after}"
    child = subprocess.Popen([sys.executable, __file__, str(copy), str(work), "child", str(root)], stdout=subprocess.PIPE, text=True)
    while child.poll() is None and len(ledger_rows(root)) < kill_after:
        time.sleep(0.002)
    killed = child.poll() is None
    if killed:
        os.kill(child.pid, signal.SIGKILL)
    child.wait()
    at_kill = len(ledger_rows(root))
    stt_lines_at_kill = len((root / "run" / "stt.jsonl").read_text().splitlines()) if (root / "run" / "stt.jsonl").exists() else 0
    lock_left = (root / "run" / ".run.lock").exists()
    resumed = subprocess.run([sys.executable, __file__, str(copy), str(work), "child", str(root)], capture_output=True, text=True)
    rows = ledger_rows(root)
    paid = Counter(r["cache_key"] for r in rows if not r["cache_hit"])
    stt = [json.loads(x) for x in (root / "run" / "stt.jsonl").read_text().splitlines() if x.startswith("{") and x.endswith("}")]
    fingerprints = Counter(r["fingerprint"] for r in stt)
    total = sum(r["est_credits"] for r in rows)
    print(
        f"kill after {kill_after:2d} ledger rows (killed={killed}, ledger {at_kill}, stt lines {stt_lines_at_kill}, stale lock file {lock_left}): "
        f"resume says {resumed.stdout.strip() or resumed.stderr.strip()[-200:]} | paid calls {len(paid)} (want {CELLS + CLIPS}), "
        f"paid twice {sum(v > 1 for v in paid.values())}, stt rows {len(stt)}, distinct fingerprints {len(fingerprints)}, ledger total {total:.4f}"
    )

# budget: stop before overspending, across a kill
root = work / "budget"
child = subprocess.run([sys.executable, __file__, str(copy), str(work), "child", str(root), "0.25"], capture_output=True, text=True)
total = sum(r["est_credits"] for r in ledger_rows(root))
print(f"budget 0.25: {child.stdout.strip()} | ledger total {total:.4f} (must be <= 0.25)")
child = subprocess.run([sys.executable, __file__, str(copy), str(work), "child", str(root), "0.30"], capture_output=True, text=True)
total = sum(r["est_credits"] for r in ledger_rows(root))
print(f"then budget 0.30: {child.stdout.strip()} | ledger total {total:.4f} (must be <= 0.30)")

# a client that charges and then fails on every third STT call: does the run's spend see it?
root = work / "charged-failures"
bench = bench_at(root)
real_stt, count = bench.client.stt, {"n": 0}


def stt(audio, options):
    count["n"] += 1
    if count["n"] % 3 == 0:
        # what GnaniClient does on a 2xx it cannot parse: the ledger row is written with the estimate, nothing is cached
        bench.client.ledger.append(evalkit_bench.LedgerEntry(
            ts="2026-01-01T00:00:00+00:00", provider="gnani", kind="stt", model="fake", status=200, attempt=1,
            seconds=0.1, cache_hit=False, cache_key=f"unparsed-{count['n']}", est_credits=0.005))
        raise BadResponse("a 200 that does not parse")
    return real_stt(audio, options)


bench.client.stt = stt
try:
    summary = bench.run(budget_credits=0.30)
    total = sum(r["est_credits"] for r in ledger_rows(root))
    print(f"charged-then-failed calls, budget 0.30: errors {summary.errors}, transcribed {summary.transcribed}, stopped {summary.stopped!r}, "
          f"run says spent {summary.spent_credits:.4f}, ledger total {total:.4f}")
except Exception as exc:  # noqa: BLE001
    print("charged-then-failed run raised", type(exc).__name__, exc)
