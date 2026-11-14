"""Make the bot's fixed lines with Timbre ahead of a call, so that a call finds them in the cache.

    uv run python -m samajh.server.prompts build --lang hi [--lang hi-en] [--record ID ...]
                                                 [--line-rate 8000] [--dry-run]
    uv run python -m samajh.server.prompts check [--lang hi ...] [--line-rate 8000 ...]

`check` lists the static and record-book first-name lines (below) that are not in the cache, for every record the server
can call, and exits 1 if any is missing. It makes no request.

A fixed line is one whose words do not depend on what the customer says: a template with no slot,
or one whose only slots are the first name, the lender's name or an ordinal, filled for each
record named. A static line is a fixed line that names no customer (no slot, or only the lender
and an ordinal): the server makes these at start (`prewarm_static`). A per-record line carries
the first name and is warmed for one session (`record_lines`). Read-backs carry the customer's figure and are made on the call. Each request is
the one the server makes on a call (same options, same pieces of a long line), so the Gnani
client's cache answers the server later.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import get_args

from samajh.clients import _runtime
from samajh.clients.errors import ClientError
from samajh.clients.gnani import GnaniClient, Timbre
from samajh.dialogue import LINES, load_prompts
from samajh.server import speech
from samajh.server.loanbook import SYNTHETIC, LoanBook, LoanRefused
from samajh.server.records import PACKAGED_DIR, CallRecord, RecordBook, default_book, load_book
from samajh.server.samajh_dialogue import TTS_LANGUAGE, spoken_pieces
from samajh.server.sessionlog import LineRate
from samajh.server.settings import Settings, load_settings
from samajh.types import Language

log = logging.getLogger(__name__)

_RECORD_SLOTS = frozenset({"first_name", "lender", "ordinal"})
_STATIC_SLOTS = frozenset({"lender", "ordinal"})


@dataclass(frozen=True)
class Slots:
    """What a record puts into a line: the borrower's first name, the lender, its product count."""

    first_name: str
    lender: str
    products: int

    @classmethod
    def of(cls, record: CallRecord) -> Slots:
        return cls(record.record.borrower.name.split()[0], record.lender_name, len(record.record.products))


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


def _fillings(slots: frozenset[str], ordinals: Sequence[str], sources: Sequence[Slots]) -> list[dict]:
    if not slots:
        return [{}]
    fillings = []
    for source in sources:
        names = {"first_name": source.first_name, "lender": source.lender}
        # An ordinal line comes before the second and later products only (the first product is
        # introduced as in a one-product record), so a one-product record has none to make.
        said = ordinals[1 : source.products] if "ordinal" in slots else ("",)
        fillings += [{slot: (names | {"ordinal": ordinal})[slot] for slot in slots} for ordinal in said]
    return fillings


def _lines(
    language: Language, sources: Sequence[Slots], wanted: Callable[[frozenset[str]], bool]
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    pack = load_prompts(language)
    clips: dict[str, str] = {}  # text -> key, in first-seen order
    skipped: list[str] = []
    for key, spec in LINES.items():
        if not wanted(spec.slots):
            skipped.append(key)
            continue
        for filling in _fillings(spec.slots, pack.ordinals, sources):
            for piece in spoken_pieces(pack.render(key, **filling)):
                clips.setdefault(piece, key)
    return tuple((key, text) for text, key in clips.items()), tuple(skipped)


def fixed_lines(language: Language, records: Iterable[CallRecord]) -> FixedLines:
    clips, _ = _lines(language, [Slots.of(r) for r in records], lambda slots: slots <= _RECORD_SLOTS)
    on_demand = tuple(key for key, spec in LINES.items() if not spec.slots <= _RECORD_SLOTS)
    return FixedLines(language, clips, on_demand)


def static_lines(language: Language, sources: Iterable[Slots]) -> tuple[tuple[str, str], ...]:
    """(key, clip text) of every line that names no customer, for every lender and product count."""
    return _lines(language, list(sources), lambda slots: slots <= _STATIC_SLOTS)[0]


def record_lines(language: Language, source: Slots) -> tuple[tuple[str, str], ...]:
    """(key, clip text) of the lines that carry this record's first name."""
    return _lines(language, [source], lambda slots: "first_name" in slots and slots <= _RECORD_SLOTS)[0]


def servable(book: RecordBook | None, loans: LoanBook | None) -> list[Slots]:
    """The slots of every record a server with this book and loan book can call: the book's records
    and each loan of the batch under the loan book (drawn or not: a later draw needs no restart)."""
    sources = [Slots.of(book.get(record_id)) for record_id in book.ids()] if book is not None else []
    if loans is not None:
        try:
            snapshot = loans._snapshot()
        except LoanRefused:
            return sources  # no batch: no loan can be called
        lender = snapshot.lender_name.removesuffix(SYNTHETIC)  # as `LoanBook.resolve` speaks it
        sources += sorted(
            {Slots("", lender, len(loan.record.products)) for loan in snapshot.loans.values()},
            key=lambda s: s.products,
        )
    return sources


def is_cached(client: object, text: str, options: Timbre) -> bool | None:
    """The client's answer without a request, or None when it cannot say (no `tts_cached`)."""
    probe = getattr(client, "tts_cached", None)
    return bool(probe(text, options)) if probe is not None else None


def offline_reader() -> GnaniClient:
    """A client that can only read the cache: no key, and a credit cap of 0 so it can never spend."""
    return GnaniClient(api_key="offline-cache-reader", credit_cap=0.0)


@dataclass(frozen=True)
class Missing:
    key: str
    language: Language
    line_rate: LineRate
    text: str
    error: str = ""

    def __str__(self) -> str:
        why = f": {self.error}" if self.error else ""
        return f"{self.key} [{self.language.value} {self.line_rate} Hz] {self.text!r}{why}"


class PrewarmFailed(RuntimeError):
    def __init__(self, missing: Sequence[Missing]) -> None:
        self.missing = tuple(missing)
        lines = "\n".join(f"  {m}" for m in self.missing)
        super().__init__(f"{len(self.missing)} static bot line(s) could not be made:\n{lines}")


class PrewarmOverBudget(RuntimeError):
    """The missing lines would cost more than `[prewarm] max_credits`: nothing was made."""

    def __init__(self, missing: Sequence[Missing], est_credits: float, limit: float) -> None:
        self.missing, self.est_credits, self.limit = tuple(missing), est_credits, limit
        languages = sorted({m.language.value for m in self.missing})
        rates = sorted({m.line_rate for m in self.missing})
        command = "uv run python -m samajh.server.prompts build " + " ".join(f"--lang {x}" for x in languages)
        command += "".join(f" --line-rate {r}" for r in rates if r != 8000)
        super().__init__(
            f"prewarm refused: {len(self.missing)} missing bot line(s) would cost about {est_credits:.2f} "
            f"credits (an estimate), over [prewarm] max_credits = {limit:g}; nothing was made. "
            f"Make them by hand with `{command}`, or raise max_credits in samajh/server/settings.toml."
        )


@dataclass
class PrewarmReport:
    checked: int = 0
    missing: int = 0
    made: int = 0
    est_credits: float = 0.0


def prewarm_lines(language: Language, sources: Sequence[Slots]) -> tuple[tuple[str, str], ...]:
    """The static lines, then the first-name lines of each source that has a first name (the record
    book's records; a loan-book source has none, so its lines are made at session create)."""
    clips = {text: key for key, text in static_lines(language, sources)}  # each text once
    for source in sources:
        if source.first_name:
            for key, text in record_lines(language, source):
                clips.setdefault(text, key)
    return tuple((key, text) for text, key in clips.items())


def missing_static(
    client: object, settings: Settings, sources: Sequence[Slots]
) -> list[tuple[Missing, Timbre]]:
    """The prewarm lines (`prewarm_lines`) of the prewarm languages and rates that `client` does
    not hold. For a client with no `tts_cached`, every line (asking `tts` for a cached line is a hit)."""
    out = []
    for language in settings.prewarm.languages:
        for rate in settings.prewarm.line_rates:
            options = speech.tts_options(settings.tts_for(language), TTS_LANGUAGE[language], rate)
            for key, text in prewarm_lines(language, sources):
                if not is_cached(client, text, options):
                    out.append((Missing(key, language, rate, text), options))
    return out


def prewarm_static(
    client: speech.SpeechClient, settings: Settings, sources: Sequence[Slots]
) -> PrewarmReport:
    """Make every static line not in the cache, one at a time. PrewarmFailed lists each line that
    could not be made, after every other line has been tried."""
    report = PrewarmReport(
        checked=sum(
            len(prewarm_lines(language, sources)) * len(settings.prewarm.line_rates)
            for language in settings.prewarm.languages
        )
    )
    todo = missing_static(client, settings, sources)
    report.missing = len(todo)
    estimate = sum(len(line.text) for line, _ in todo) * credits_per_char()
    if estimate > settings.prewarm.max_credits:
        raise PrewarmOverBudget([line for line, _ in todo], estimate, settings.prewarm.max_credits)
    failed: list[Missing] = []
    for line, options in todo:
        try:
            call = client.tts(line.text, options).call
        except Exception as error:  # noqa: BLE001 - every failure is listed, then the start is refused
            failed.append(
                Missing(
                    line.key, line.language, line.line_rate, line.text, f"{type(error).__name__}: {error}"
                )
            )
            continue
        report.made += not call.cache_hit
        report.est_credits += call.est_credits
    if failed:
        raise PrewarmFailed(failed)
    return report


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
    check = commands.add_parser("check", help="list the static lines not in the cache (no request)")
    check.add_argument("--lang", action="append", choices=[lang.value for lang in Language])
    check.add_argument("--line-rate", action="append", type=int, choices=get_args(LineRate))
    args = parser.parse_args(argv)

    if args.command == "check":
        return _check(args, client)

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


def _check(args: argparse.Namespace, client: object | None) -> int:
    settings = load_settings()
    prewarm = settings.prewarm.model_copy(
        update={
            **({"languages": tuple(Language(x) for x in dict.fromkeys(args.lang))} if args.lang else {}),
            **({"line_rates": tuple(dict.fromkeys(args.line_rate))} if args.line_rate else {}),
        }
    )
    settings = settings.model_copy(update={"prewarm": prewarm})
    sources = servable(default_book(), LoanBook(_runtime.state_dir()))
    missing = missing_static(client or offline_reader(), settings, sources)
    for language in prewarm.languages:
        for rate in prewarm.line_rates:
            total = len(prewarm_lines(language, sources))
            here = [m for m, _ in missing if (m.language, m.line_rate) == (language, rate)]
            print(
                f"{language.value} {rate} Hz: {total} static and record-book first-name lines, "
                f"{len(here)} not in the cache"
            )
            for line in here:
                print(f"  MISSING {line}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
