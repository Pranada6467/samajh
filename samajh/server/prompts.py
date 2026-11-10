"""Make the bot's fixed lines with Timbre ahead of a call, so that a call finds them in the cache.

    uv run python -m samajh.server.prompts build --lang hi [--lang hi-en] [--record ID ...]
                                                 [--line-rate 8000] [--dry-run]

A fixed line is one whose words do not depend on what the customer says: a template with no slot,
or one whose only slots are the first name, the lender's name or an ordinal, filled for each
record named. Read-backs carry the customer's figure and are made on the call. Each request is
the one the server makes on a call (same options, same pieces of a long line), so the Gnani
client's cache answers the server later.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import get_args

from samajh.clients import _runtime
from samajh.clients.errors import ClientError
from samajh.dialogue import LINES, load_prompts
from samajh.server import speech
from samajh.server.records import PACKAGED_DIR, CallRecord, default_book, load_book
from samajh.server.samajh_dialogue import TTS_LANGUAGE, spoken_pieces
from samajh.server.sessionlog import LineRate
from samajh.server.settings import Settings, load_settings
from samajh.types import Language

_RECORD_SLOTS = frozenset({"first_name", "lender", "ordinal"})


@dataclass(frozen=True)
class FixedLines:
    language: Language
    clips: tuple[tuple[str, str], ...]  # (line key, text of one clip), each text once
    on_demand: tuple[str, ...]  # keys whose words depend on the customer

    @property
    def chars(self) -> int:
        return sum(len(text) for _, text in self.clips)


@dataclass
class BuildReport:
    language: Language
    lines: int = 0
    cache_hits: int = 0
    new_calls: int = 0
    est_credits: float = 0.0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (line key, the error)


def _fillings(slots: frozenset[str], ordinals: Sequence[str], records: Sequence[CallRecord]) -> list[dict]:
    if not slots:
        return [{}]
    fillings = []
    for record in records:
        names = {"first_name": record.record.borrower.name.split()[0], "lender": record.lender_name}
        said = ordinals[: len(record.record.products)] if "ordinal" in slots else ("",)
        fillings += [{slot: (names | {"ordinal": ordinal})[slot] for slot in slots} for ordinal in said]
    return fillings


def fixed_lines(language: Language, records: Iterable[CallRecord]) -> FixedLines:
    pack = load_prompts(language)
    records = list(records)
    clips: dict[str, str] = {}  # text -> key, in first-seen order
    on_demand: list[str] = []
    for key, spec in LINES.items():
        if not spec.slots <= _RECORD_SLOTS:
            on_demand.append(key)
            continue
        for filling in _fillings(spec.slots, pack.ordinals, records):
            for piece in spoken_pieces(pack.render(key, **filling)):
                clips.setdefault(piece, key)
    return FixedLines(language, tuple((key, text) for text, key in clips.items()), tuple(on_demand))


def credits_per_char() -> float:
    return float(_runtime.load_defaults()["gnani"]["tts_credits_per_char"])


def build(
    languages: Sequence[Language],
    records: Iterable[CallRecord],
    client: speech.SpeechClient,
    *,
    settings: Settings,
    line_rate: LineRate = 8000,
) -> list[BuildReport]:
    """Ask `client` for every fixed line. A line that fails is reported and the rest still run."""
    records = list(records)
    reports = []
    for language in languages:
        options = speech.tts_options(settings.tts_for(language), TTS_LANGUAGE[language], line_rate)
        report = BuildReport(language)
        for key, text in fixed_lines(language, records).clips:
            report.lines += 1
            try:
                call = client.tts(text, options).call
            except ClientError as error:
                report.failed.append((key, f"{type(error).__name__}: {error}"))
                continue
            report.cache_hits += call.cache_hit
            report.new_calls += not call.cache_hit
            report.est_credits += call.est_credits
        reports.append(report)
    return reports


def main(argv: Sequence[str] | None = None, *, client: speech.SpeechClient | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m samajh.server.prompts", description=__doc__.split("\n")[0]
    )
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("build", help="synthesise the fixed lines (or count them with --dry-run)")
    cmd.add_argument("--lang", action="append", required=True, choices=[lang.value for lang in Language])
    cmd.add_argument("--record", action="append", help="a record id; default: every packaged demo record")
    cmd.add_argument("--line-rate", type=int, default=8000, choices=get_args(LineRate))
    cmd.add_argument("--dry-run", action="store_true", help="make no call; print lines, characters, credits")
    args = parser.parse_args(argv)

    languages = [Language(lang) for lang in dict.fromkeys(args.lang)]
    if args.record:
        book = default_book()
        unknown = [record_id for record_id in args.record if record_id not in book.ids()]
        if unknown:
            parser.error(f"unknown record {unknown}; known: {book.ids()}")
        records = [book.get(record_id) for record_id in dict.fromkeys(args.record)]
    else:
        packaged = load_book(PACKAGED_DIR)
        records = [packaged.get(record_id) for record_id in packaged.ids()]
    settings = load_settings()

    if args.dry_run:
        rate = credits_per_char()
        for language in languages:
            fixed = fixed_lines(language, records)
            print(
                f"{language.value}: {len(fixed.clips)} lines, {fixed.chars} characters, "
                f"about {fixed.chars * rate:.2f} credits if none is cached "
                f"({rate} per character, an estimate); {len(fixed.on_demand)} on demand"
            )
        return 0

    reports = build(
        languages,
        records,
        client or speech.live_client(speech.PATIENT),
        settings=settings,
        line_rate=args.line_rate,
    )
    for report in reports:
        print(
            f"{report.language.value}: {report.lines} lines, {report.cache_hits} cache hits, "
            f"{report.new_calls} new calls, about {report.est_credits:.2f} credits spent (an estimate)"
        )
        for key, error in report.failed:
            print(f"{report.language.value}: FAILED {key}: {error}", file=sys.stderr)
    return 1 if any(report.failed for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
