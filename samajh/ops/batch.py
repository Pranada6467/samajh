"""One read of the store, joined: each sampled loan with its attempts, its analysed call and its
triage. The views and the report both count from this, so they cannot disagree.

Nothing here reads the simulation's hidden truth (`sim-customers.jsonl`).
"""

from dataclasses import dataclass

from samajh.ops.model import (
    FINAL_DECISIONS,
    Attempt,
    AttemptOutcome,
    BatchMeta,
    BookLoan,
    CallRecord,
    Disposition,
    Draw,
    DrawnLoan,
    FinalStatus,
    Triage,
)
from samajh.ops.sampler import verify_draw
from samajh.ops.store import OpsStore
from samajh.ops.triage import triage
from samajh.types import Tier


@dataclass(frozen=True)
class Sampled:
    """One drawn loan and everything that happened to it."""

    draw: Draw
    drawn: DrawnLoan
    loan: BookLoan
    attempts: tuple[Attempt, ...]  # in order
    call: CallRecord | None  # the analysed call; set exactly when the loan's status is completed
    triage: Triage | None

    @property
    def status(self) -> FinalStatus:
        """From the last attempt: none is not_attempted, no_answer is unreachable, else the same name."""
        if not self.attempts:
            return FinalStatus.not_attempted
        last = self.attempts[-1].outcome
        return FinalStatus.unreachable if last is AttemptOutcome.no_answer else FinalStatus(last.value)

    @property
    def referred(self) -> bool:
        return self.triage is not None and self.triage.tier is Tier.refer


@dataclass(frozen=True)
class Batch:
    meta: BatchMeta
    draws: tuple[Draw, ...]
    verified: dict[str, bool]  # draw id -> the draw was recomputed from the book and matched
    sampled: tuple[Sampled, ...]  # every drawn loan of every draw, in draw order
    history: dict[str, tuple[Disposition, ...]]  # case id -> its decisions, oldest first

    @property
    def completed(self) -> tuple[Sampled, ...]:
        """The analysed calls: one per sampled loan whose last attempt completed."""
        return tuple(s for s in self.sampled if s.call is not None)

    @property
    def referrals(self) -> tuple[Sampled, ...]:
        return tuple(s for s in self.sampled if s.referred)

    def latest(self, case_id: str) -> Disposition | None:
        """The decision that stands for a case: the last one recorded."""
        entries = self.history.get(case_id)
        return entries[-1] if entries else None

    def decided(self, case_id: str) -> bool:
        latest = self.latest(case_id)
        return latest is not None and latest.decision in FINAL_DECISIONS


def load_batch(store: OpsStore) -> Batch:
    """Read the whole store. Raises `NoBatch` when it holds none."""
    meta = store.meta()
    book = store.book()
    loans = {loan.record.loan_id: loan for loan in book}
    draws = store.draws()
    by_loan: dict[str, list[Attempt]] = {}
    for attempt in store.attempts():
        by_loan.setdefault(attempt.loan_id, []).append(attempt)
    history: dict[str, list[Disposition]] = {}
    for disposition in store.dispositions():
        history.setdefault(disposition.case_id, []).append(disposition)

    sampled: list[Sampled] = []
    for draw in draws:
        for drawn in draw.drawn:
            attempts = tuple(sorted(by_loan.get(drawn.loan_id, ()), key=lambda a: a.number))
            call = None
            if attempts and attempts[-1].outcome is AttemptOutcome.completed:
                call = store.call(attempts[-1].call_id)
                if call is None:
                    raise ValueError(
                        f"attempt {attempts[-1].attempt_id} names a call that is not in the store"
                    )
            sampled.append(
                Sampled(
                    draw=draw,
                    drawn=drawn,
                    loan=loans[drawn.loan_id],
                    attempts=attempts,
                    call=call,
                    triage=triage(loans[drawn.loan_id].record, call.result) if call else None,
                )
            )
    return Batch(
        meta=meta,
        draws=draws,
        verified={draw.draw_id: verify_draw(draw, book, draws[:i]) for i, draw in enumerate(draws)},
        sampled=tuple(sampled),
        history={case_id: tuple(entries) for case_id, entries in history.items()},
    )
