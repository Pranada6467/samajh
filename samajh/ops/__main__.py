"""Command line for the operating layer. Run from the repository root."""

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from samajh.clients._runtime import state_dir
from samajh.ops import book as books
from samajh.ops import sampler
from samajh.ops.batch import load_batch
from samajh.ops.model import BookLoan, BookMeta, Draw, SimCustomer
from samajh.ops.report import build_report
from samajh.ops.simulate import Analyse, llm_analysis, run_draw, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.types import LenderType

DEMO_SEED = 85
DEMO_PERIOD = (date(2027, 1, 1), date(2027, 6, 30))
DEMO_DRAWS = (date(2027, 2, 8), date(2027, 2, 15), date(2027, 2, 22), date(2027, 3, 1))
DEMO_DRAW_SIZE = 20


def _draw(store: OpsStore, book: tuple[BookLoan, ...], meta: BookMeta, as_of: date, size: int) -> Draw:
    """Draw and log. A day that already has a draw gets that draw back unchanged."""
    earlier = store.draws()
    existing = next((d for d in earlier if d.as_of == as_of), None)
    if existing is not None:
        return existing
    taken = {loan.loan_id for d in earlier for loan in d.drawn}
    drawn = sampler.draw(book, meta, as_of, size, meta.seed, taken)
    store.add_draw(drawn)
    return drawn


def _run(store: OpsStore, customers: dict[str, SimCustomer], analyse: Analyse, workers: int) -> None:
    for drawn in store.draws():
        run_draw(store, drawn, customers, analyse, workers=workers)


def _summary(store: OpsStore) -> str:
    report = build_report(store, datetime.now(UTC))
    funnel = report.funnel
    lines = [f"sampled {funnel.sampled}, attempts {funnel.attempts}", "funnel:"]
    lines += [f"  {row.key}: {row.value.count} of {row.value.n}" for row in (*funnel.stages, *funnel.exits)]
    lines.append("tiers of analysed calls:")
    lines += [f"  {row.tier.value}: {row.value.count} of {row.value.n}" for row in report.tiers]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m samajh.ops", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, help: str, *, state: bool = True, book: bool = False) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=help)
        if state:
            sub.add_argument("--state", type=Path, default=state_dir(), help="the state directory")
        if book:
            sub.add_argument("--book", type=Path, default=books.DATA_DIR, help="the loan book's directory")
        return sub

    sub = command("book", "generate the synthetic loan book", state=False)
    sub.add_argument("--seed", type=int, default=DEMO_SEED)
    sub.add_argument("--loans", type=int, default=200)
    sub.add_argument("--lender-type", type=LenderType, choices=tuple(LenderType), default=LenderType.bank)
    sub.add_argument("--out", type=Path, default=books.DATA_DIR)
    command("init", "start a batch over the book (half-year 1 January to 30 June 2027)", book=True)
    sub = command("draw", "draw a random sample of loans sold in the last 30 days")
    sub.add_argument("--as-of", type=date.fromisoformat, required=True)
    sub.add_argument("--size", type=int, default=DEMO_DRAW_SIZE)
    sub = command("run", "make the simulated calls of every draw and analyse them", book=True)
    sub.add_argument("--analysis", choices=("scripted", "llm"), default="scripted")
    sub.add_argument("--workers", type=int, default=1)
    command("verify", "recompute every draw from the book")
    command("report", "print the half-yearly report as JSON")
    command("demo", "the whole scripted loop into --state: book, batch, four weekly draws, calls")
    args = parser.parse_args(argv)

    if args.command == "book":
        meta, loans, customers = books.generate_book(args.seed, args.loans, lender_type=args.lender_type)
        books.write_book(args.out, meta, loans, customers)
        print(f"wrote {meta.loans} loans to {args.out} (book.jsonl sha256 {meta.sha256})")
        return 0

    store = OpsStore(args.state / "ops")
    if args.command == "init":
        meta, loans = books.load_book(args.book)
        batch = store.init(meta, loans, *DEMO_PERIOD, datetime.now(UTC))
        print(f"batch {batch.batch_id} in {store.root}")
    elif args.command == "draw":
        drawn = _draw(store, store.book(), store.meta().book, args.as_of, args.size)
        print(f"{drawn.draw_id}: drew {len(drawn.drawn)} of {len(drawn.eligible)} eligible")
    elif args.command == "run":
        if args.analysis == "llm":
            from samajh.pipeline import default_llm  # needs the OpenRouter key

            analyse = llm_analysis(default_llm())
        else:
            analyse = scripted_analysis
        _run(store, books.load_customers(args.book), analyse, args.workers)
        print(_summary(store))
    elif args.command == "verify":
        verified = load_batch(store).verified
        for draw_id, matched in verified.items():
            print(f"{draw_id}: {'matches the book' if matched else 'DOES NOT MATCH'}")
        return 0 if all(verified.values()) else 1
    elif args.command == "report":
        print(build_report(store, datetime.now(UTC)).model_dump_json(indent=2))
    elif args.command == "demo":
        meta, loans, customers = books.generate_book(DEMO_SEED)
        store.init(meta, loans, *DEMO_PERIOD, datetime.now(UTC))
        for as_of in DEMO_DRAWS:
            _draw(store, loans, meta, as_of, DEMO_DRAW_SIZE)
        _run(store, {c.loan_id: c for c in customers}, scripted_analysis, workers=1)
        print(f"simulated batch in {store.root} (scripted customers, scripted extraction, no model)")
        print(_summary(store))
    return 0


if __name__ == "__main__":
    sys.exit(main())
