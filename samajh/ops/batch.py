"""One read of the store, joined: each sampled loan with its attempts, its analysed call and its
triage. The views and the report both count from this, so they cannot disagree.

Nothing here reads the simulation's hidden truth (`sim-customers.jsonl`).
"""

from dataclasses import dataclass

from samajh.ops.model import (
    FINAL_DECISIONS,
    RETRY_AFTER,
    WINDOW_DAYS,
    Attempt,
    AttemptOutcome,
    BatchMeta,
    BookLoan,
    CallRecord,
    Disposition,
    Draw,
    DrawnLoan,
    FinalStatus,
    IngestSummary,
    OutsideCall,
    PhoneSession,
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
    attempts: tuple[Attempt, ...]  # by number, which is time order (samajh.ops.chain)
    call: CallRecord | None  # the analysed call; set exactly when the last attempt completed
    triage: Triage | None

    @property
    def status(self) -> FinalStatus:
        """From the last attempt.

        None: not_attempted. Completed on day 0 to 30 from the sale: completed; on any other day:
        completed_late. A retry outcome (no answer, call back later, another language, a request
        from a speaker not confirmed as the borrower) on day 30 or later: not_reached_in_time, since no attempt is made after day 30. Otherwise no_answer
        is unreachable, and every other outcome keeps its name.
        """
        if not self.attempts:
            return FinalStatus.not_attempted
        last = self.attempts[-1]
        if last.outcome is AttemptOutcome.completed:
            in_window = 0 <= last.day_since_sale <= WINDOW_DAYS
            return FinalStatus.completed if in_window else FinalStatus.completed_late
        if last.outcome in RETRY_AFTER and last.day_since_sale >= WINDOW_DAYS:
            return FinalStatus.not_reached_in_time
        if last.outcome is AttemptOutcome.no_answer:
            return FinalStatus.unreachable
        return FinalStatus(last.outcome.value)

    @property
    def counted(self) -> bool:
        """The call is one the report counts: completed within 30 days of the sale and analysed."""
        return self.call is not None and self.status is FinalStatus.completed

    @property
    def referred(self) -> bool:
        return self.triage is not None and self.triage.tier is Tier.refer


@dataclass(frozen=True)
class Outside:
    """A phone call that is not in the sample, with its analysed call when there is one."""

    call: OutsideCall
    record: CallRecord | None
    triage: Triage | None


@dataclass(frozen=True)
class Batch:
    meta: BatchMeta
    draws: tuple[Draw, ...]
    verified: dict[str, bool]  # draw id -> the draw was recomputed from the book and matched
    sampled: tuple[Sampled, ...]  # every drawn loan of every draw, in draw order
    history: dict[str, tuple[Disposition, ...]]  # case id -> its decisions, oldest first
    outside: tuple[Outside, ...] = ()  # phone calls that are not attempts in the sample: never counted
    book: tuple[BookLoan, ...] = ()  # every loan on the book
    ingest: IngestSummary | None = None  # the last ingest of phone sessions; None if none has run

    @property
    def phone_sessions(self) -> tuple[PhoneSession, ...]:
        """Every phone session in the batch, linked attempts and calls outside the sample."""
        linked = (a.source for s in self.sampled for a in s.attempts if isinstance(a.source, PhoneSession))
        outside = (o.call.source for o in self.outside if isinstance(o.call.source, PhoneSession))
        return (*linked, *outside)

    @property
    def completed(self) -> tuple[Sampled, ...]:
        """The calls the report counts: completed within 30 days of the sale and analysed."""
        return tuple(s for s in self.sampled if s.counted)

    @property
    def late(self) -> tuple[Sampled, ...]:
        """Sampled loans whose call completed outside the 30-day window. Shown apart."""
        return tuple(s for s in self.sampled if s.status is FinalStatus.completed_late)

    @property
    def referrals(self) -> tuple[Sampled, ...]:
        """Referred calls the report counts: sampled, completed in the window."""
        return tuple(s for s in self.completed if s.referred)

    @property
    def other_referrals(self) -> tuple[Sampled | Outside, ...]:
        """Referred calls a reviewer must still see that the report does not count."""
        late = (s for s in self.late if s.referred)
        outside = (o for o in self.outside if o.triage is not None and o.triage.tier is Tier.refer)
        return (*late, *outside)

    @property
    def simulated(self) -> bool:
        """True while every attempt in the batch is simulated."""
        phone = any(a.source.kind == "phone_session" for s in self.sampled for a in s.attempts)
        return not phone and not self.outside

    def open(self, case_ids: tuple[str, ...]) -> int:
        """How many of these cases have no final decision. The one definition of an open case."""
        return sum(not self.decided(case_id) for case_id in case_ids)

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
    outside = []
    for o in store.outside():
        record = store.call(o.call_id) if o.call_id else None
        outside.append(
            Outside(call=o, record=record, triage=triage(o.record, record.result) if record else None)
        )
    return Batch(
        meta=meta,
        draws=draws,
        verified={
            draw.draw_id: verify_draw(draw, book, draws[i - 1] if i else None) for i, draw in enumerate(draws)
        },
        sampled=tuple(sampled),
        history={case_id: tuple(entries) for case_id, entries in history.items()},
        outside=tuple(outside),
        book=book,
        ingest=store.ingest_summary(),
    )
