"""One command per W7 part. It runs the existing steps in order, prints each command and stops on the
first failure.

    uv run python eval/openbench/run.py a|b|c [--offline] [--usd-cap X]

  a  amounts: job files, the local open models and Gemini Flash on phone audio, then part_a.py
  b  FLEURS: fetch, freeze check, jobs, Prisma on the subset, local models, Gemini Flash, then part_b.py
  c  generic agent baseline: the counted cells of PLAN.md Part C, Samajh's own call, then part_c.py

--offline runs only the scoring step, from stored outputs. Every API step is resumable and cached, so a
rerun on the machine that made the outputs sends no new paid request. --usd-cap is the cap passed to each
paid OpenRouter step (one client per step).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
UV = ["uv", "run", "python"]
LOCAL = ["uv", "run", "--no-project", "--python", "3.11", "--with-requirements",
         "eval/openbench/requirements-asr.txt", "python"]
LOCAL_SYSTEMS = ("whisper-large-v3", "indicwhisper")
FLASH = ["--model", "google/gemini-3-flash-preview", "--workers", "6"]


def py(script: str, *args: str, prefix: list[str] = UV) -> list[str]:
    return [*prefix, f"eval/openbench/{script}", *args]


def steps_a(cap: str) -> list[list[str]]:
    sets = ["amounts-v2"]
    if (REPO / ".samajh-realvoice").exists():
        sets.append("realvoice")
    else:
        print("note: .samajh-realvoice/ is absent; the public-clip half needs the local-only clips and is skipped")
    out = [py("inputs.py", s) for s in sets]
    out += [py("asr_local.py", "--system", m, "--set", s, "--condition", "phone", prefix=LOCAL)
            for s in sets for m in LOCAL_SYSTEMS]
    out += [py("asr_gemini.py", *FLASH, "--set", s, "--condition", "phone", "--usd-cap", cap) for s in sets]
    return out


def steps_b(cap: str) -> list[list[str]]:
    out = [py("fleurs.py", c) for c in ("fetch", "freeze", "jobs")]
    out.append(py("asr_prisma.py", "--set", "fleurs", "--subset-only"))
    out += [py("asr_local.py", "--system", m, "--set", "fleurs", "--only-field", "gemini100", "--condition", c,
               prefix=LOCAL) for m in LOCAL_SYSTEMS for c in ("native16k", "phone")]
    out += [py("asr_gemini.py", *FLASH, "--set", "fleurs", "--subset-only", "--condition", c, "--usd-cap", cap)
            for c in ("native16k", "phone")]
    return out


def steps_c(cap: str) -> list[list[str]]:
    agent = lambda *a: py("part_c_agent.py", *a, "--usd-cap", cap)  # noqa: E731
    return [
        agent("--arm", "B0", "--r", "0", "--a", "0"),
        agent("--arm", "B0", "--r", "1", "--a", "0"),
        agent("--arm", "B0", "--r", "0.5", "--a", "0.5"),
        agent("--arm", "B1", "--r", "1", "--a", "0", "--with-dk-only"),
        agent("--arm", "B0", "--r", "0", "--a", "0", "--third-party"),
        py("part_c_samajh.py", "--usd-cap", cap),
    ]


PARTS = {"a": (steps_a, "part_a.py"), "b": (steps_b, "part_b.py"), "c": (steps_c, "part_c.py")}


def plan(part: str, offline: bool, cap: str) -> list[list[str]]:
    steps, scorer = PARTS[part]
    return ([] if offline else steps(cap)) + [py(scorer)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("part", choices=sorted(PARTS))
    ap.add_argument("--offline", action="store_true", help="run only the scoring step, from stored outputs")
    ap.add_argument("--usd-cap", default="5", help="USD cap for each paid OpenRouter step (default 5)")
    args = ap.parse_args(argv)
    for cmd in plan(args.part, args.offline, args.usd_cap):
        print("$ " + shlex.join(cmd), flush=True)
        code = subprocess.run(cmd, cwd=REPO).returncode
        if code != 0:
            print(f"stopped: exit {code}", file=sys.stderr)
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
