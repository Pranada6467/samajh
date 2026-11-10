"""Run a draw against the simulated customers: log each attempt, script and analyse each completed call.

No phone is involved. An attempt's outcome comes from `SimCustomer.attempts`, and a completed
call's transcript from `samajh.scenarios.script.teach_back`, so every reply is phrase-bank text.
"""

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from samajh.ops.model import (
    RETRY_AFTER,
    Attempt,
    AttemptOutcome,
    BookLoan,
    CallRecord,
    Draw,
    SimCustomer,
    SimulatedCall,
)
from samajh.ops.store import OpsStore
from samajh.rules import evaluate, to_beliefs
from samajh.scenarios.model import ProductBelief, TeachBackCall
from samajh.scenarios.script import teach_back
from samajh.types import CaseResult, Language, LoanRecord, ProductId, SaleConcern

IST = timezone(timedelta(hours=5, minutes=30))
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
    max_attempts: int = 3,
    workers: int = 1,
) -> None:
    """Make the calls of one draw.

    Attempt k of a loan is on day `as_of + (k - 1)` at 11:00 IST. Attempts stop at the first
    outcome outside `RETRY_AFTER` or at `max_attempts`. Safe to run again: an attempt already in
    the log is not logged again, and a call already saved is not analysed again.
    """
    loans = {loan.record.loan_id: loan for loan in store.book()}
    attempts: list[Attempt] = []
    scripts: dict[str, tuple[Attempt, TeachBackCall]] = {}
    for drawn in draw.drawn:
        loan, customer = loans[drawn.loan_id], customers[drawn.loan_id]
        for number, step in enumerate(customer.attempts[:max_attempts], start=1):
            day = draw.as_of + timedelta(days=number - 1)
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
            attempts.append(attempt)
            if script and store.call(attempt.call_id) is None:
                scripts[attempt.call_id] = (attempt, script)
            if step.outcome not in RETRY_AFTER:
                break

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
    for attempt in attempts:
        if attempt.call_id not in failed:
            store.add_attempt(attempt)
    if failed:
        detail = "; ".join(f"{call_id}: {error}" for call_id, error in failed.items())
        raise RuntimeError(f"{len(failed)} call(s) of {draw.draw_id} were not analysed; run again. {detail}")
