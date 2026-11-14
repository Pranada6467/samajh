"""Evidence bundles. Run from the repository root.

  export --case ID --out DIR [--state S] [--with-recording]   write one case's bundle
  verify DIR                                                   re-check a bundle from its files alone
  check [--state S]                                            re-check every session, case and decision

Exit codes: 0 verified; 1 mismatch (the first one is printed; export also exits 1 when the source or
the bundle it wrote does not verify, and deletes what it wrote); 2 usage error, export refused (no
such case, the session deleted by retention) or --state is not a state directory; 3 no mismatch, but
some part is unverifiable (written before the evidence epoch); 4 no mismatch, but a decision was made
on a different version of this case (an earlier version, or the line was moved from another case).
A warning (4) wins over unverifiable (3) when both apply.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from samajh.clients._runtime import state_dir
from samajh.evidence.bundle import USAGE, Refused, check_state, export, verify_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m samajh.evidence", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("export", help="write one case's evidence bundle")
    sub.add_argument("--case", required=True, help="the case id as the review queue shows it")
    sub.add_argument("--out", type=Path, required=True)
    sub.add_argument("--state", type=Path, default=None)
    sub.add_argument("--with-recording", action="store_true", help="also the call recording and turn audio")
    sub = commands.add_parser("verify", help="re-check a bundle from its files alone")
    sub.add_argument("dir", type=Path)
    sub = commands.add_parser("check", help="re-check every session, case file and the decision log")
    sub.add_argument("--state", type=Path, default=None)
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return USAGE if e.code else 0

    if args.command == "export":
        try:
            done = export(args.state or state_dir(), args.case, args.out, with_recording=args.with_recording)
        except Refused as e:
            print(f"refused: {e}", file=sys.stderr)
            return e.code
        for w in done.warnings:
            print(f"WARNING: {w}")
        for note in done.manifest["notes"]:
            print(f"note: {note}")
        print(f"exported case {args.case} to {args.out}")
        print(f"root_sha256 {done.root_sha256}")
        print("Copy this root_sha256 somewhere else now (an email, a ticket): it is what proves later that")
        print("the bundle is the one exported today, since anyone with this code can rebuild every digest.")
        return 0

    if args.command == "verify":
        if not args.dir.is_dir():
            print(f"{args.dir} is not a directory", file=sys.stderr)
            return USAGE
        verdict = verify_bundle(args.dir)
        for line in verdict.checked:
            print(f"checked: {line}")
        if verdict.mismatch:
            print(f"MISMATCH: {verdict.mismatch}")
            return verdict.code
        for line in verdict.unverifiable:
            print(f"UNVERIFIABLE: {line}")
        for line in verdict.warnings:
            print(f"WARNING: {line}")
        if verdict.code == 0:
            print("verified: compare root_sha256 with the copy made at export")
        return verdict.code

    result = check_state(args.state or state_dir())
    if result.usage:
        print(result.usage, file=sys.stderr)
        return result.code
    for line in result.lines:
        print(line)
    for problem in result.problems:
        print(f"MISMATCH: {problem}")
    for line in result.unverifiable:
        print(f"UNVERIFIABLE: {line}")
    return result.code


if __name__ == "__main__":
    sys.exit(main())
