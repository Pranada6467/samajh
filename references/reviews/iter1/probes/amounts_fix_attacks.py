"""Attempts to break the W8 review fixes. Fake client and temp dirs only: no network, nothing in the repo.

  PYTHONPATH=/path/to/scratch/repo2 .venv/bin/python references/reviews/iter1/probes/amounts_fix_attacks.py /path/to/scratch/repo2 /path/to/workdir
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

copy, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path[:0] = [str(copy), str(copy / "tests" / "evalkit")]

import evalkit_bench  # noqa: E402
import filelock  # noqa: E402
import samajh  # noqa: E402
from samajh.audio import steps as audio_steps  # noqa: E402
from samajh.evalkit.manifest import load_manifest  # noqa: E402
from samajh.evalkit.plan import load_experiment  # noqa: E402
from samajh.evalkit.runner import RunStore, StoreBusy, current_rows, jobs  # noqa: E402

assert Path(samajh.__file__).resolve().is_relative_to(copy), samajh.__file__
shutil.rmtree(work, ignore_errors=True)
CELLS = 72


def bench(name: str) -> evalkit_bench.Bench:
    root = work / name
    root.mkdir(parents=True)
    return evalkit_bench.Bench(root)


# --- fix 2: transform version in the fingerprint, on the real run store (read-only copy in scratch) ---
experiment = load_experiment(copy / "eval" / "amounts" / "experiment.toml")
items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
store = RunStore(copy / "eval" / "amounts" / "run")
print("fix 2. real run store, TRANSFORM_VERSION 1:", len(current_rows(store, jobs(items, experiment))), "of 2640 rows current")
audio_steps.TRANSFORM_VERSION = 2
now = current_rows(store, jobs(items, experiment))
print("       after a bump to 2:", len(now), "rows current, conditions kept:", sorted({r.condition for r in now.values()}))
audio_steps.TRANSFORM_VERSION = 1

# --- fix 3: torn lines ---
b = bench("torn")
b.run(max_items=2)
path = b.store.root / "stt.jsonl"
before = len(b.store.stt_rows())
with path.open("ab") as f:
    f.write('{"fingerprint": "torn mid multibyte ಕ'.encode()[:-1])  # cut inside a UTF-8 character
try:
    rows = len(b.store.stt_rows())
    summary = b.run(max_items=4)
    with path.open("ab") as f:
        f.write(b'{"fingerprint": "second torn line')  # a second crash
    final = b.run()
    print(f"fix 3. torn inside a UTF-8 character then torn again: rows readable before {before}, after first tear {rows}, "
          f"final rows {len(b.store.stt_rows())} (want {CELLS}), pending {final.pending}, stt calls {len(b.client.stt_calls)} (want {CELLS})")
except Exception as exc:  # noqa: BLE001
    print("fix 3. BROKEN:", type(exc).__name__, str(exc)[:200])

b = bench("torn-complete")
b.run(max_items=1)
path = b.store.root / "stt.jsonl"
data = path.read_bytes()
path.write_bytes(data[:-1])  # the last row is complete but its newline is missing
summary = b.run()
print(f"       complete last row without its newline: rows {len(b.store.stt_rows())} (want {CELLS}), stt calls {len(b.client.stt_calls)} (want {CELLS})")

b = bench("torn-nul")
b.run(max_items=1)
path = b.store.root / "stt.jsonl"
with path.open("ab") as f:
    f.write(b"\x00" * 64)  # what some filesystems leave after power loss
try:
    summary = b.run()
    print(f"       NUL padding at the end: rows {len(b.store.stt_rows())} (want {CELLS}), pending {summary.pending}")
except Exception as exc:  # noqa: BLE001
    print("       NUL padding BROKE the store:", type(exc).__name__, str(exc)[:200])

# --- fix 4: one run per store ---
b = bench("lock")
b.store.root.mkdir(parents=True)
lock_path = b.store.root / ".run.lock"
# Interleaving: run A releases its lock; run B acquires before A unlinks the file; A unlinks; run C starts.
a = filelock.FileLock(lock_path, timeout=0, thread_local=False)
a.acquire()
a.release()                      # A: lock.release()
held_by_b = filelock.FileLock(lock_path, timeout=0, thread_local=False)
held_by_b.acquire()              # B: starts in the gap and now "holds the store"
lock_path.unlink(missing_ok=True)  # A: lock_path.unlink(missing_ok=True)
try:
    summary = b.run(max_items=1)  # C
    print(f"fix 4. release-then-unlink race: a third run was ADMITTED while B holds the lock (transcribed {summary.transcribed}); B still locked: {held_by_b.is_locked}")
except StoreBusy:
    print("fix 4. release-then-unlink race: third run refused")
finally:
    held_by_b.release()

b = bench("lock-plain")
b.store.root.mkdir(parents=True)
with filelock.FileLock(b.store.root / ".run.lock"):
    try:
        b.run()
        print("       plain case: second run admitted (BROKEN)")
    except StoreBusy:
        print("       plain case: second run on a held store refused")

# two stores, one budget: the lock and the budget are per store
b1 = bench("store-a")
b2 = evalkit_bench.Bench(work / "store-a")  # same manifest, ledger and audio; another run store
b2.store = RunStore(work / "store-a" / "run-2")
b2.client = b1.client
s1 = b1.run(budget_credits=0.30)
s2 = b2.run(budget_credits=0.30)
print(f"       two run stores, budget 0.30 each, one ledger: run 1 spent {s1.spent_credits:.3f}, run 2 spent {s2.spent_credits:.3f}, "
      f"ledger total {b1.ledger.total_credits():.3f}")

# --- fix 5: a call paid before a crash ---
b = bench("crash")
b.client.cache = {}
real_add = b.store.add
state = {"n": 0}


def crash_every_fifth(row):
    state["n"] += 1
    if state["n"] % 5 == 0:
        raise KeyboardInterrupt
    real_add(row)


b.store.add = crash_every_fifth
crashes = 0
for _ in range(200):
    try:
        summary = b.run(budget_credits=0.50)
        break
    except KeyboardInterrupt:
        crashes += 1
print(f"fix 5. crash on every fifth store write ({crashes} crashes), budget 0.50: stopped {summary.stopped!r}, run says spent {summary.spent_credits:.4f}, "
      f"ledger total {b.ledger.total_credits():.4f}, over budget by {max(0.0, b.ledger.total_credits() - 0.50):.4f}")
