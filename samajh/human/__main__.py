"""`uv run python -m samajh.human score | refs | wer | notes`: a day of human calls into numbers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from samajh.human import notes as notes_mod
from samajh.human import score as score_mod
from samajh.human.sessions import attach_gold, load_call_log, load_gold, load_sessions
from samajh.human.wer import refs, wer_report


def _emit(text: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}")


def _cuts() -> dict[str, float]:
    from samajh.server.settings import load_settings

    return {k: float(v.cut_ms) for k, v in load_settings().turn_taking.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="samajh.human")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score")
    sc.add_argument("--sessions", type=Path, action="append", required=True)
    sc.add_argument("--state", type=Path, default=Path(".samajh"))
    sc.add_argument("--cards", type=Path, default=Path(".samajh-human/cards"))
    sc.add_argument("--log", type=Path, default=Path(".samajh-human/call-log.csv"))
    sc.add_argument("--ledger", type=Path, default=Path(".samajh/ledger.jsonl"))
    sc.add_argument("--out", type=Path)
    rf = sub.add_parser("refs")
    rf.add_argument("--sessions", type=Path, action="append", required=True)
    rf.add_argument("--state", type=Path, default=Path(".samajh"))
    rf.add_argument("--out", type=Path, required=True)
    wr = sub.add_parser("wer")
    wr.add_argument("--refs", type=Path, required=True)
    wr.add_argument("--sessions", type=Path, action="append", default=[])
    wr.add_argument("--state", type=Path, default=Path(".samajh"))
    wr.add_argument("--out", type=Path)
    nt = sub.add_parser("notes")
    nt.add_argument("--in", dest="in_dir", type=Path, required=True)
    nt.add_argument("--lang", choices=["hi", "hi-en"], required=True)
    nt.add_argument("--out", type=Path)
    nt.add_argument("--max-credits", type=float, default=10.0)
    nt.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "score":
        sessions = load_sessions(a.sessions, a.state)
        attach_gold(sessions, load_gold(a.cards), load_call_log(a.log))
        text = score_mod.report(
            sessions, [str(p) for p in a.sessions], _cuts(), score_mod.read_ledger(a.ledger)
        )
        _emit(text, a.out)
    elif a.cmd == "refs":
        n = refs(load_sessions(a.sessions, a.state), a.out)
        print(f"wrote {a.out}: {n} turns")
    elif a.cmd == "wer":
        _emit(wer_report(a.refs, a.sessions, a.state), a.out)
    else:
        out = a.out or Path(".samajh-human/notes") / a.in_dir.resolve().name

        def factory():
            from samajh.server.speech import PATIENT, live_client

            return live_client(PATIENT)

        try:
            return notes_mod.run_notes(
                a.in_dir, a.lang, out, max_credits=a.max_credits, dry_run=a.dry_run, client_factory=factory
            )
        except notes_mod.Refused as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
