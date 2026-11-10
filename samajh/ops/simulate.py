"""Run a draw against the simulated customers: log each attempt, script and analyse each completed call.

No phone is involved. An attempt's outcome comes from `SimCustomer.attempts`, and a completed
call's transcript from `samajh.scenarios.script.teach_back`, so every reply is phrase-bank text.
"""

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from samajh.ops.chain import IST, at_limit, chain_of, india_day, next_number
from samajh.ops.model import (
    MAX_ATTEMPTS,
    RETRY_AFTER,
    WINDOW_DAYS,
    Attempt,
    AttemptOutcome,
    BookLoan,
    CallRecord,
    Draw,
    PhoneSession,
    SimCustomer,
    SimulatedCall,
)
from samajh.ops.store import OpsStore
from samajh.rules import evaluate, to_beliefs
from samajh.scenarios.model import ProductBelief, TeachBackCall
from samajh.scenarios.script import teach_back
from samajh.types import CaseResult, Language, LoanRecord, ProductId, SaleConcern

CALL_TIME = time(11, 0, tzinfo=IST)
SCRIPTED_CALL = SimulatedCall(script="samajh.scenarios.script.teach_back")
SCRIPTED_OUTCOME = SimulatedCall(script="samajh.ops.book (scripted outcome, no transcript)")

Analyse = Callable[[TeachBackCall, LoanRecord], tuple[CaseResult, str]]
"""A scripted call and the loan record in; the rule result and how it was produced out."""


@dataclass(frozen=True)
class SimCall:
    """What `teach_back` reads of a `Scenario`: the record and the customer's beliefs. No gold."""

    id: str
    language: Language
    record: LoanRecord
    concerns: tuple[SaleConcern, ...]
    beliefs: tuple[ProductBelief, ...]

    def belief(self, product_id: ProductId) -> ProductBelief:
        return next(b for b in self.beliefs if b.product_id == product_id)


def script_call(loan: BookLoan, customer: SimCustomer) -> TeachBackCall:
    """The scripted teach-back call for one loan, in the borrower's language."""
    record = loan.record
    return teach_back(
        SimCall(
            id=record.loan_id,
            language=record.borrower.language,
            record=record,
            concerns=customer.concerns,
            beliefs=customer.beliefs,
        )
    )


def scripted_analysis(call: TeachBackCall, record: LoanRecord) -> tuple[CaseResult, str]:
    """The rules on the script's own extraction. No model reads the transcript."""
    beliefs = to_beliefs(call.extraction, record, call.transcript)
    return evaluate(record, beliefs), "scripted extraction, no model"


def llm_analysis(llm) -> Analyse:
    """The rules on what the extraction model reads from the transcript. The label is the model id."""
    from samajh.pipeline import run_text  # imports the network clients

    def analyse(call: TeachBackCall, record: LoanRecord) -> tuple[CaseResult, str]:
        run = run_text(call.transcript, record, llm)
        return run.result, next((slot.model for slot in run.extraction.slots), "llm")

    return analyse


def run_draw(
    store: OpsStore,
    draw: Draw,
    customers: Mapping[str, SimCustomer],
    analyse: Analyse,
    max_attempts: int = MAX_ATTEMPTS,
    workers: int = 1,
) -> None:
    """Make the calls of one draw, continuing each loan's chain of attempts (`samajh.ops.chain`).

    Attempt n of a loan is on day `as_of + (n - 1)` at 11:00 IST, or the day after the loan's last
    logged attempt if that is later. The k-th simulated attempt plays the customer's k-th scripted
    step, so a phone attempt already logged (from `sessions.ingest`) takes its place in the chain
    and counts towards `max_attempts`. Attempts stop when the chain has ended (an outcome outside
    `RETRY_AFTER`), at `max_attempts` attempts of any kind, when the script runs out, or when the
    next day would be past day 30 from the sale (`WINDOW_DAYS`): no simulated attempt is ever made
    after the window. Safe to run again: only attempts after the chain's end are added, and a call
    already saved is not analysed again.
    """
    loans = {loan.record.loan_id: loan for loan in store.book()}
    logged = store.attempts()
    attempts: list[Attempt] = []
    scripts: dict[str, tuple[Attempt, TeachBackCall]] = {}
    for drawn in draw.drawn:
        loan, customer = loans[drawn.loan_id], customers[drawn.loan_id]
        made = chain_of(logged, drawn.loan_id)
        while not made or made[-1].outcome in RETRY_AFTER:
            number = next_number(made)
            scripted = sum(not isinstance(a.source, PhoneSession) for a in made)
            if at_limit(made, max_attempts) or scripted >= len(customer.attempts):
                break
            day = draw.as_of + timedelta(days=number - 1)
            if made:
                day = max(day, india_day(made[-1].at) + timedelta(days=1))
            if (day - loan.sold_on).days > WINDOW_DAYS:
                break  # no attempt after day 30 from the sale
            step = customer.attempts[scripted]
            completed = step.outcome is AttemptOutcome.completed
            script = script_call(loan, customer) if completed else None
            attempt = Attempt(
                attempt_id=f"{draw.draw_id}/{drawn.loan_id}/{number}",
                draw_id=draw.draw_id,
                loan_id=drawn.loan_id,
                number=number,
                at=datetime.combine(day, CALL_TIME),
                day_since_sale=(day - loan.sold_on).days,
                language=loan.record.borrower.language,
                source=SCRIPTED_CALL if completed else SCRIPTED_OUTCOME,
                outcome=step.outcome,
                right_party_confirmed=step.right_party_confirmed,
                call_id=script.transcript.call_id if script else None,
            )
            made.append(attempt)
            attempts.append(attempt)
            if script and store.call(attempt.call_id) is None:
                scripts[attempt.call_id] = (attempt, script)

    def analysed(item: tuple[Attempt, TeachBackCall]) -> CallRecord | Exception:
        attempt, script = item
        try:
            result, how = analyse(script, loans[attempt.loan_id].record)
        except Exception as error:  # noqa: BLE001 - one call that cannot be analysed must not stop the others
            return error
        return CallRecord(
            call_id=attempt.call_id,
            attempt_id=attempt.attempt_id,
            loan_id=attempt.loan_id,
            source=attempt.source,
            transcript=script.transcript,
            result=result,
            analysis=how,
        )

    failed: dict[str, Exception] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for call_id, call in zip(scripts, pool.map(analysed, scripts.values()), strict=True):
            if isinstance(call, Exception):
                failed[call_id] = call
            else:
                store.save_call(call)
    # The call is saved before its attempt is logged, so a logged completed attempt always has its call.
    # A loan whose chain changed while the calls were analysed (an ingest ran) is left for the next run.
    moved: list[str] = []
    with store.locked():
        now = store.attempts()
        for drawn in draw.drawn:
            if chain_of(now, drawn.loan_id) != chain_of(logged, drawn.loan_id):
                moved.append(drawn.loan_id)
        for attempt in attempts:
            if attempt.call_id not in failed and attempt.loan_id not in moved:
                store.add_attempt(attempt)
    if failed or moved:
        detail = "; ".join(f"{call_id}: {error}" for call_id, error in failed.items())
        raise RuntimeError(
            f"{len(failed)} call(s) of {draw.draw_id} were not analysed and {len(moved)} loan(s) gained an "
            f"attempt meanwhile; run again. {detail}"
        )
