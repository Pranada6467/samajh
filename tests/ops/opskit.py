"""Hand-built loans and customers with known outcomes. Nothing here touches the network."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from samajh.ops import sampler
from samajh.ops.book import book_sha256
from samajh.ops.model import AttemptOutcome, BookLoan, BookMeta, Channel, Draw, SimCustomer, SimStep
from samajh.ops.simulate import run_draw, script_call, scripted_analysis
from samajh.ops.store import OpsStore
from samajh.scenarios.model import ProductBelief, Recall
from samajh.types import (
    Borrower,
    Consent,
    ConsentMethod,
    FeatureClaim,
    KindClaim,
    Language,
    LenderType,
    LoanKind,
    LoanRecord,
    PaymentSource,
    Product,
    ProductId,
    ProductKind,
    SaleConcern,
)

SOLD = date(2027, 1, 11)
NOW = datetime(2027, 2, 1, 9, 0, tzinfo=UTC)
COMPLETED = SimStep(outcome=AttemptOutcome.completed, right_party_confirmed=True)
NO_ANSWER = SimStep(outcome=AttemptOutcome.no_answer, right_party_confirmed=False)
DECLINED_AFTER_CHECKS = SimStep(outcome=AttemptOutcome.declined, right_party_confirmed=True)


def loan(
    serial: int, sold_on: date = SOLD, branch: str = "SYN-BR-01", channel: Channel = Channel.branch
) -> BookLoan:
    """A gold loan with one credit-life product that a fully informed customer passes on every rule."""
    product = Product(
        id=ProductId("P1"),
        kind=ProductKind.credit_life,
        provider="Namoona Life (synthetic)",
        premium_inr=12_500,
        cover_inr=250_000,
        term_months=24,
        paid_from_loan=True,
        required_for_loan=False,
        risk_mitigant=True,
        provider_choice_offered=True,
        cancel_window_days=30,
        features=frozenset({FeatureClaim.one_time_payment}),
        consent=Consent(method=ConsentMethod.otp, at=sold_on),
    )
    record = LoanRecord(
        loan_id=f"SYN-GL-{sold_on:%y%m%d}-{serial:04d}",
        lender_type=LenderType.bank,
        borrower=Borrower(
            name=f"Udaharan Lal {serial:03d} (synthetic)", dob=date(1985, 1, 1), language=Language.hi
        ),
        loan_kind=LoanKind.gold,
        sanctioned_inr=250_000,
        disbursed_inr=237_500,
        disbursed_on=sold_on,
        products=(product,),
    )
    return BookLoan(record=record, sold_on=sold_on, branch=branch, channel=channel)


def customer(
    of: BookLoan, *attempts: SimStep, concerns: tuple[SaleConcern, ...] = (), **beliefs
) -> SimCustomer:
    """A customer who states everything on the record, except for `beliefs`."""
    (product,) = of.record.products
    informed = {
        "product_id": product.id,
        "recall": Recall.named,
        "kind": KindClaim.insurance,
        "premium_inr": product.premium_inr,
        "payment_source": PaymentSource.from_loan,
        "required_for_loan": False,
        "provider_choice_offered": None,
        "cover_inr": product.cover_inr,
        "term_months": product.term_months,
        "cancel_allowed": True,
        "cancel_window_days": product.cancel_window_days,
        "money_back": (),
        "consent_given": True,
        "consent_method": product.consent.method,
    }
    return SimCustomer(
        loan_id=of.record.loan_id,
        archetype="hand-built",
        beliefs=(ProductBelief(**(informed | beliefs)),),
        concerns=concerns,
        attempts=attempts,
    )


def coached(of: BookLoan, *attempts: SimStep) -> SimCustomer:
    """A high-severity referral: the customer says they were told what to answer."""
    return customer(of, *attempts, concerns=(SaleConcern.coached_answers,))


def other_consent_method(of: BookLoan, *attempts: SimStep) -> SimCustomer:
    """A medium-severity referral: the customer names another way of agreeing than the record."""
    return customer(of, *attempts, consent_method=ConsentMethod.signed_form)


def open_batch(root: Path, loans: list[BookLoan], as_of: date) -> tuple[OpsStore, Draw]:
    """A batch over a hand-built book with every loan drawn on `as_of`. No call is made yet."""
    meta = BookMeta(
        lender_name="Namoona Bank (synthetic)",
        lender_type=LenderType.bank,
        seed=1,
        loans=len(loans),
        sold_from=min(b.sold_on for b in loans),
        sold_to=max(b.sold_on for b in loans),
        sha256=book_sha256(loans),
    )
    store = OpsStore(root)
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), NOW)
    drawn = sampler.draw(loans, meta, as_of, rate=1.0, seed=1, after=None)
    store.add_draw(drawn)
    return store, drawn


def run_batch(root: Path, loans: list[BookLoan], customers: list[SimCustomer], as_of: date) -> OpsStore:
    """`open_batch`, then every call scripted and analysed."""
    store, drawn = open_batch(root, loans, as_of)
    run_draw(store, drawn, {c.loan_id: c for c in customers}, scripted_analysis)
    return store


# --- phone sessions, as samajh/server/casefile.py writes their case files ------------------------

WALL = datetime(2026, 11, 10, 5, 30, tzinfo=UTC)  # the wall clock of a session (the book is dated 2027)
_serial = iter(range(1, 10**6))


def session_id(started: datetime) -> str:
    return f"{started.astimezone(UTC):%Y%m%dT%H%M%S}-{next(_serial):012x}"


def phone_case(
    store: OpsStore,
    of: BookLoan,
    who: SimCustomer | None,
    call_date: date | None,
    outcome: str = "completed",
    status: str = "ready",
    *,
    started: datetime = WALL,
    sid: str | None = None,
    audio: dict[str, int] | None = None,
    **changes,
) -> dict:
    """A case file for a session on `of`. With `call_date`, a loan-book call with its `book` block
    worked out from the store; with None, no `book` block. A completed call carries the scripted
    transcript and result of `who`, also when its status is failed (a failed case keeps them)."""
    sid = sid or session_id(started)
    case: dict = {
        "version": 1,
        "session_id": sid,
        "record_id": of.record.loan_id,
        "loan_id": of.record.loan_id,
        "language": "hi",
        "status": status,
        "started_at": started.isoformat(),
        "call_outcome": outcome,
        "ended_reason": "dialogue",
        "models": {"extraction": {"model": "scripted (test)"}},
        "turns": [],
    }
    if audio is not None:
        case["customer_audio"] = audio
    if call_date is not None:
        draw = next((d for d in store.draws() if any(x.loan_id == of.record.loan_id for x in d.drawn)), None)
        case["book"] = {
            "batch_id": store.meta().batch_id,
            "draw_id": draw.draw_id if draw else "D-none",
            "sold_on": of.sold_on.isoformat(),
            "call_date": call_date.isoformat(),
            "day_since_sale": (call_date - of.sold_on).days,
        }
    if outcome == "completed" and who is not None:
        script = script_call(of, who)
        result, _ = scripted_analysis(script, of.record)
        transcript = script.transcript.model_dump(mode="json")
        transcript["call_id"] = sid
        case["transcript"] = transcript
        case["result"] = result.model_dump(mode="json")
    return case | changes


def put_case(sessions: Path, case: dict) -> Path:
    folder = sessions / case["session_id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "case.json").write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return folder


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file of a store but its lock, by path."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".lock"
    }


def assert_each_call_named_once(store: OpsStore) -> None:
    """Every call file is named by exactly one effective attempt or outside call."""
    named = [a.call_id for a in store.attempts() if a.call_id] + [
        o.call_id for o in store.outside() if o.call_id
    ]
    files = sorted(p.stem for p in (store.root / "calls").glob("*.json"))
    assert sorted(named) == files, (named, files)
