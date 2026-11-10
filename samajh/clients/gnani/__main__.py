"""CLI: `uv run python -m samajh.clients.gnani {tts,stt,batch,voices,ledger} ...` (JSON on stdout)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from samajh.clients._runtime import Ledger, state_dir
from samajh.clients.errors import ClientError
from samajh.clients.gnani.client import GnaniClient, credit_cap_from_env
from samajh.clients.gnani.types import VOICES, BatchOptions, SttOptions, Timbre

BILLED_KINDS = ("stt", "tts", "batch.billed")


def _language(value: str) -> str | tuple[str, ...]:
    return tuple(value.split(",")) if "," in value else value


def _audio_format(path: Path) -> Any:
    return path.suffix.lstrip(".").lower() or "wav"


def _ledger_summary() -> dict[str, Any]:
    rows = [e for e in Ledger(state_dir() / "ledger.jsonl").entries() if e.provider == "gnani"]
    live = [e for e in rows if not e.cache_hit]
    billed = [
        e for e in live if e.kind in BILLED_KINDS and isinstance(e.status, int) and 200 <= e.status < 300
    ]
    spent, cap = sum(e.est_credits for e in rows), credit_cap_from_env()
    return {
        "rows": len(rows),
        "cache_hits": len(rows) - len(live),
        "live_attempts": dict(sorted(Counter(f"{e.kind} {e.status}" for e in live).items())),
        "audio_seconds": round(sum(e.audio_seconds or 0.0 for e in billed), 2),
        "chars": sum(e.chars or 0 for e in billed),
        "est_credits_spent": round(spent, 4),
        "credit_cap": cap,
        "remaining": round(cap - spent, 4),
    }


def _run(args: argparse.Namespace) -> dict[str, Any] | list[Any]:
    if args.command == "voices":
        models = [args.model] if args.model else list(VOICES)
        return [v.model_dump() for m in models for v in VOICES[m]]
    if args.command == "ledger":
        return _ledger_summary()
    if args.command == "tts":
        options = Timbre(
            model=args.model,
            voice=args.voice,
            language=args.language,
            sample_rate=args.sample_rate,
            container=args.container,
        )
        speech = GnaniClient.from_env().tts(args.text, options)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(speech.audio)
        return {"out": args.out, "bytes": len(speech.audio), **speech.model_dump(exclude={"audio"})}
    audio = Path(args.file).read_bytes()
    spec: dict[str, Any] = {"model": args.model, "language": _language(args.language)}
    if args.command == "stt":
        spec["format"] = args.format
        if args.keyterm:
            spec["keyterms"] = args.keyterm
        stt_options = TypeAdapter(SttOptions).validate_python(spec)
        result = GnaniClient.from_env().stt(audio, stt_options, audio_format=_audio_format(Path(args.file)))
        return result.model_dump()
    if args.model == "prisma-v3.0":
        spec["format"] = args.format
    batch_options = BatchOptions(**spec, num_speakers=args.num_speakers)
    return (
        GnaniClient.from_env()
        .batch_transcribe(audio, batch_options, audio_format=_audio_format(Path(args.file)))
        .model_dump()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m samajh.clients.gnani")
    sub = parser.add_subparsers(dest="command", required=True)
    tts = sub.add_parser("tts")
    tts.add_argument("text")
    tts.add_argument("--out", required=True)
    tts.add_argument("--model", default="timbre-v3.0")
    tts.add_argument("--voice", default="Shivani")
    tts.add_argument("--language", default="hi-IN")
    tts.add_argument("--sample-rate", type=int, default=8000)
    tts.add_argument("--container", default="wav")
    for name in ("stt", "batch"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--model", default="prisma-v3.0")
        p.add_argument("--language", default="hi-IN")
        p.add_argument("--format", default="transcribe")
        if name == "stt":
            p.add_argument("--keyterm", action="append")
        else:
            p.add_argument("--num-speakers", type=int)
    sub.add_parser("voices").add_argument("--model", choices=list(VOICES))
    sub.add_parser("ledger")
    try:
        result = _run(parser.parse_args(argv))
    except ClientError as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    except (ValidationError, OSError) as exc:
        print(f"error: {type(exc).__name__}: {' '.join(str(exc).split())[:300]}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
