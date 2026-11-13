"""The seeded synthetic loan book, and the simulation's hidden truth about each customer.

Everything is invented. The mix of customers (`ARCHETYPES`), the branch and channel that carry
more problems (`HOT_BRANCH`, `HOT_CHANNEL`) and the chance of each call outcome (`REACH`) are the
builders' assumptions: they estimate nothing about any real lender.

A scripted customer can only say what the scenario phrase banks hold, so every premium, cover,
term, cancellation window and year of birth is read from `samajh.scenarios.phrases.BANKS`.
"""

import hashlib
import json
import os
import random
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from samajh.ops.model import (
    MAX_ATTEMPTS,
    RETRY_AFTER,
    AttemptOutcome,
    BookLoan,
    BookMeta,
    Channel,
    SimCustomer,
    SimStep,
)
from samajh.scenarios.model import DONT_KNOW, EVASIVE, DepositWord, ProductBelief, Recall
from samajh.scenarios.phrases import BANKS
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

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "loanbook"
LANGUAGES = (Language.hi, Language.hi_en)  # the product languages
LENDER_NAME = {LenderType.bank: "Namoona Bank (synthetic)", LenderType.nbfc: "Namoona Finance (synthetic)"}
PROVIDER = "Namoona Life (synthetic)"
SYNTHETIC = " (synthetic)"
P1 = ProductId("P1")
LOAN_CODE = {LoanKind.gold: "GL", LoanKind.personal: "PL"}
BRANCHES = tuple(f"SYN-BR-{n:02d}" for n in range(1, 7))
CHANNEL_WEIGHT = {Channel.branch: 5, Channel.agent: 3, Channel.app: 2}
HOT_BRANCH, HOT_CHANNEL = "SYN-BR-04", Channel.agent
HOT_WEIGHT = 4  # a problem archetype is this many times likelier there (assumption)
PREMIUMS_BELOW_INR = 100_000  # phrase-bank amounts below this serve as premiums, the rest as covers
PAID_FROM_LOAN_SHARE = 0.7
MAX_STEPS = 3
# The chance of each outcome of one call attempt (assumption).
REACH: dict[AttemptOutcome, float] = {
    AttemptOutcome.no_answer: 0.25,
    AttemptOutcome.call_back_later: 0.08,
    AttemptOutcome.wrong_party: 0.03,
    AttemptOutcome.not_confirmed: 0.03,
    AttemptOutcome.declined: 0.07,
    AttemptOutcome.incomplete: 0.05,
    AttemptOutcome.completed: 0.49,
}
DECLINED_AFTER_IDENTITY_SHARE = 0.5

# Consent phrases exist only for these methods per word the customer uses for the product
# (`_consent_key` in samajh/scenarios/script.py).
_DEPOSIT_CONSENT = {
    DepositWord.fd: (ConsentMethod.signed_form, ConsentMethod.otp),
    DepositWord.security_deposit: (ConsentMethod.signed_form,),
}
_INVESTMENT_CONSENT = ConsentMethod.otp


@dataclass(frozen=True)
class _Tables:
    """What a scripted customer can say in every product language."""

    premiums: tuple[int, ...]
    covers: tuple[int, ...]
    terms: tuple[int, ...]
    windows: tuple[int, ...]
    years: tuple[int, ...]


def _tables() -> _Tables:
    def shared(table: str) -> tuple[int, ...]:
        keys = [set(getattr(BANKS[language], table)) for language in LANGUAGES]
        return tuple(sorted(set.intersection(*keys)))

    amounts = shared("amounts")
    return _Tables(
        premiums=tuple(a for a in amounts if a < PREMIUMS_BELOW_INR),
        covers=tuple(a for a in amounts if a >= PREMIUMS_BELOW_INR),
        terms=shared("durations"),
        windows=shared("windows"),
        years=shared("years"),
    )


def _with(product: Product, **changes) -> Product:
    return Product.model_validate(product.model_dump() | changes)


def _informed(product: Product, **changes) -> ProductBelief:
    """A belief that matches the record in every field, with `changes` applied."""
    base = {
        "product_id": product.id,
        "recall": Recall.named,
        "kind": KindClaim.insurance,
        "premium_inr": product.premium_inr,
        "payment_source": PaymentSource.from_loan if product.paid_from_loan else PaymentSource.separately,
        "required_for_loan": product.required_for_loan,
        "provider_choice_offered": product.provider_choice_offered if product.required_for_loan else None,
        "cover_inr": product.cover_inr,
        "term_months": product.term_months,
        "cancel_allowed": True,
        "cancel_window_days": product.cancel_window_days,
        "money_back": (),
        "consent_given": True,
        "consent_method": product.consent.method if product.consent else ConsentMethod.verbal,
    }
    return ProductBelief(**(base | changes))


Made = tuple[Product, ProductBelief, tuple[SaleConcern, ...]]
_NO_CANCEL = {"cancel_allowed": DONT_KNOW, "cancel_window_days": None}


def _informed_full(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _informed(p), ()


def _informed_ordinary(rng: random.Random, t: _Tables, p: Product) -> Made:
    forgotten = rng.sample(("cover", "term", "cancel"), rng.randint(1, 3))
    changes: dict = {}
    if "cover" in forgotten:
        changes["cover_inr"] = DONT_KNOW
    if "term" in forgotten:
        changes["term_months"] = DONT_KNOW
    if "cancel" in forgotten:
        changes |= {"cancel_allowed": rng.choice((DONT_KNOW, False)), "cancel_window_days": None}
    return p, _informed(p, **changes), ()


def _forgot_premium(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _informed(p, premium_inr=DONT_KNOW), ()


def _not_named_unprompted(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _informed(p, recall=Recall.not_named), ()


def _cannot_say_how_agreed(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _informed(p, consent_method=DONT_KNOW), ()


def _told_it_is_a_deposit(rng: random.Random, t: _Tables, p: Product) -> Made:
    word = rng.choice(tuple(DepositWord))
    p = _with(p, consent=Consent(method=rng.choice(_DEPOSIT_CONSENT[word]), at=p.consent.at))
    if word is DepositWord.fd:
        money_back = {"money_back": (FeatureClaim.is_deposit, FeatureClaim.refundable_anytime)}
    else:
        money_back = {
            "money_back": (FeatureClaim.is_deposit, FeatureClaim.withdrawable_after_period),
            "money_back_period_months": p.term_months,
        }
    belief = _informed(
        p, kind=KindClaim.deposit, deposit_word=word, cover_inr=DONT_KNOW, **_NO_CANCEL, **money_back
    )
    return p, belief, ()


def _believes_investment(rng: random.Random, t: _Tables, p: Product) -> Made:
    p = _with(p, consent=Consent(method=_INVESTMENT_CONSENT, at=p.consent.at))
    belief = _informed(
        p,
        kind=KindClaim.investment,
        cover_inr=DONT_KNOW,
        money_back=(FeatureClaim.guaranteed_return,),
        **_NO_CANCEL,
    )
    return p, belief, ()


def _did_not_agree(rng: random.Random, t: _Tables, p: Product) -> Made:
    if rng.random() < 0.5:
        p = _with(p, consent=None)  # nothing on the record either
    return p, _informed(p, consent_given=False, consent_method=None), ()


def _deduction_not_known(rng: random.Random, t: _Tables, p: Product) -> Made:
    p = _with(p, paid_from_loan=True)
    return p, _informed(p, payment_source=rng.choice((PaymentSource.separately, DONT_KNOW))), ()


def _required_no_choice(rng: random.Random, t: _Tables, p: Product) -> Made:
    p = _with(p, required_for_loan=True, provider_choice_offered=rng.random() < 0.5)
    return p, _informed(p, required_for_loan=True, provider_choice_offered=False), ()


def _expects_money_back(rng: random.Random, t: _Tables, p: Product) -> Made:
    if rng.random() < 0.5:
        return p, _informed(p, money_back=(FeatureClaim.guaranteed_return,)), ()
    belief = _informed(
        p, money_back=(FeatureClaim.withdrawable_after_period,), money_back_period_months=rng.choice(t.terms)
    )
    return p, belief, ()


def _wrong_cancel_window(rng: random.Random, t: _Tables, p: Product) -> Made:
    other = rng.choice([w for w in t.windows if w != p.cancel_window_days])
    return p, _informed(p, cancel_window_days=other), ()


def _coached(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _informed(p), (SaleConcern.coached_answers,)


def _answers(p: Product, how: str, recall: Recall) -> ProductBelief:
    return ProductBelief(
        product_id=p.id,
        recall=recall,
        kind=how,
        premium_inr=how,
        payment_source=how,
        required_for_loan=how,
        provider_choice_offered=how if p.required_for_loan else None,
        cover_inr=how,
        term_months=how,
        cancel_allowed=how,
        money_back=how,
        consent_given=how,
        consent_method=None,
    )


def _knows_almost_nothing(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _answers(p, DONT_KNOW, Recall.dont_know), ()


def _evasive(rng: random.Random, t: _Tables, p: Product) -> Made:
    return p, _answers(p, EVASIVE, Recall.evasive), ()


@dataclass(frozen=True)
class Archetype:
    """One kind of customer: how common (a relative weight) and whether it counts as a problem
    for the branch and channel that carry more of them."""

    weight: float
    problem: bool
    what: str
    make: Callable[[random.Random, _Tables, Product], Made]


ARCHETYPES: dict[str, Archetype] = {
    "informed_full": Archetype(30, False, "states everything on the record", _informed_full),
    "informed_ordinary": Archetype(
        30, False, "knows the product, its cost and how they agreed; forgot cover, term or the window",
        _informed_ordinary,
    ),
    "forgot_premium": Archetype(4, False, "knows the product, forgot the premium", _forgot_premium),
    "not_named_unprompted": Archetype(
        4, False, "does not name the product until asked about it", _not_named_unprompted
    ),
    "cannot_say_how_agreed": Archetype(
        3, False, "agrees they bought it, cannot say how they agreed", _cannot_say_how_agreed
    ),
    "told_it_is_a_deposit": Archetype(
        1.3, True, "believes it is an FD or a security deposit", _told_it_is_a_deposit
    ),
    "believes_investment": Archetype(1, True, "believes it is an investment with a return", _believes_investment),
    "did_not_agree": Archetype(
        1.3, True, "says they agreed only to the loan; half have no consent on the record", _did_not_agree
    ),
    "deduction_not_known": Archetype(
        1.3, True, "premium deducted from the loan; thinks they paid separately or does not know",
        _deduction_not_known,
    ),
    "required_no_choice": Archetype(
        1, True, "required for the loan, and not told of a choice of provider", _required_no_choice
    ),
    "expects_money_back": Archetype(1, True, "wrongly expects the money back", _expects_money_back),
    "wrong_cancel_window": Archetype(1, True, "states a different cancellation window", _wrong_cancel_window),
    "coached": Archetype(0.6, True, "says they were told what to answer", _coached),
    "knows_almost_nothing": Archetype(0.6, True, "answers \"don't know\" to almost everything", _knows_almost_nothing),
    "evasive": Archetype(0.6, True, "gives no usable answer to anything", _evasive),
}  # fmt: skip


def _attempts(rng: random.Random) -> tuple[SimStep, ...]:
    steps: list[SimStep] = []
    while len(steps) < MAX_STEPS:
        (outcome,) = rng.choices(tuple(REACH), weights=tuple(REACH.values()))
        confirmed = outcome in (AttemptOutcome.completed, AttemptOutcome.incomplete) or (
            outcome is AttemptOutcome.declined and rng.random() < DECLINED_AFTER_IDENTITY_SHARE
        )
        steps.append(SimStep(outcome=outcome, right_party_confirmed=confirmed))
        if outcome not in RETRY_AFTER:
            break
    return tuple(steps)


def _loan(
    rng: random.Random, t: _Tables, serial: int, sold_on: date, lender_type: LenderType
) -> tuple[BookLoan, SimCustomer]:
    language = rng.choice(LANGUAGES)
    loan_kind = rng.choice(tuple(LoanKind))
    branch = rng.choice(BRANCHES)
    (channel,) = rng.choices(tuple(CHANNEL_WEIGHT), weights=tuple(CHANNEL_WEIGHT.values()))
    cover = rng.choice(t.covers)
    product = Product(
        id=P1,
        kind=ProductKind.credit_life,
        provider=PROVIDER,
        premium_inr=rng.choice([p for p in t.premiums if p * 10 <= cover]),
        cover_inr=cover,
        term_months=rng.choice(t.terms),
        paid_from_loan=rng.random() < PAID_FROM_LOAN_SHARE,
        required_for_loan=False,
        risk_mitigant=True,
        provider_choice_offered=True,
        cancel_window_days=rng.choice(t.windows),
        features=frozenset({FeatureClaim.one_time_payment}),
        consent=Consent(method=rng.choice(tuple(ConsentMethod)), at=sold_on),
    )
    hot = (HOT_WEIGHT if branch == HOT_BRANCH else 1) * (HOT_WEIGHT if channel is HOT_CHANNEL else 1)
    weights = [a.weight * (hot if a.problem else 1) for a in ARCHETYPES.values()]
    (name,) = rng.choices(tuple(ARCHETYPES), weights=weights)
    product, belief, concerns = ARCHETYPES[name].make(rng, t, product)

    loan_id = f"SYN-{LOAN_CODE[loan_kind]}-{sold_on:%y%m%d}-{serial:04d}"
    borrower = BANKS[language].borrower
    assert borrower.endswith(SYNTHETIC), "the phrase bank's borrower name is marked synthetic"
    record = LoanRecord(
        loan_id=loan_id,
        lender_type=lender_type,
        borrower=Borrower(
            name=f"{borrower.removesuffix(SYNTHETIC)} {serial:03d}{SYNTHETIC}",
            dob=date(rng.choice(t.years), 1, 1),
            language=language,
        ),
        loan_kind=loan_kind,
        sanctioned_inr=cover,
        disbursed_inr=cover - (product.premium_inr if product.paid_from_loan else 0),
        disbursed_on=sold_on,
        products=(product,),
    )
    customer = SimCustomer(
        loan_id=loan_id, archetype=name, beliefs=(belief,), concerns=concerns, attempts=_attempts(rng)
    )
    return BookLoan(record=record, sold_on=sold_on, branch=branch, channel=channel), customer


def jsonl(rows: Sequence) -> str:
    """One model per line. The same rows always give the same bytes."""
    return "".join(row.model_dump_json() + "\n" for row in rows)


def book_sha256(loans: Sequence[BookLoan]) -> str:
    return hashlib.sha256(jsonl(loans).encode()).hexdigest()


def generate_book(
    seed: int,
    loans: int = 200,
    sold_from: date = date(2027, 1, 4),
    days: int = 60,
    lender_type: LenderType = LenderType.bank,
) -> tuple[BookMeta, tuple[BookLoan, ...], tuple[SimCustomer, ...]]:
    """`loans` sales over `days` days from `sold_from`, in order of sale. The same seed gives the same book."""
    rng = random.Random(seed)
    tables = _tables()
    sold = sorted(sold_from + timedelta(days=rng.randrange(days)) for _ in range(loans))
    made = [_loan(rng, tables, serial, day, lender_type) for serial, day in enumerate(sold, start=1)]
    book = tuple(loan for loan, _ in made)
    meta = BookMeta(
        lender_name=LENDER_NAME[lender_type],
        lender_type=lender_type,
        seed=seed,
        loans=loans,
        sold_from=sold_from,
        sold_to=sold_from + timedelta(days=days - 1),
        sha256=book_sha256(book),
    )
    return meta, book, tuple(customer for _, customer in made)


def _readme(meta: BookMeta, counts: Counter) -> str:
    total = sum(a.weight for a in ARCHETYPES.values())
    rows = "\n".join(
        f"| `{name}` | {a.what} | {a.weight / total:.0%} | {'yes' if a.problem else 'no'} | {counts[name]} |"
        for name, a in ARCHETYPES.items()
    )
    reach = "\n".join(f"| {outcome.value} | {chance:.0%} |" for outcome, chance in REACH.items())
    return f"""# Synthetic loan book

Generated by `uv run python -m samajh.ops book --seed {meta.seed}`. Do not edit by hand: the same
seed gives the same bytes, and `BOOK.json` holds the sha256 of `book.jsonl`.

**Everything here is synthetic.** No lender, borrower, loan or branch is real, and no call is with
a lender's customer: simulated calls are scripted, and a phone call brought in with `ingest` is made
on the browser phone against a synthetic record. Every id starts with `SYN-` and every name ends in
"(synthetic)". There are no phone numbers, account numbers, Aadhaar or PAN.

## Files

- `book.jsonl`: {meta.loans} sales of {meta.lender_name}, one `BookLoan` per line, sold
  {meta.sold_from.isoformat()} to {meta.sold_to.isoformat()}. Each is a gold or personal loan with one
  credit-life product. This is all the sampler, the queue and the report read.
- `sim-customers.jsonl`: one `SimCustomer` per loan. This is the simulation's hidden truth: what
  the customer believes and how each call attempt ends. Only the call simulator reads it.
- `BOOK.json`: the book's metadata, the generator's parameters and the count of each archetype.

## What is assumed, not measured

**The mix of customers is the builders' assumption.** It estimates nothing about any real lender,
and no share in a report built on this book is evidence about real sales.

| Archetype | The customer | Base share | Problem | Loans |
|---|---|---|---|---|
{rows}

**One branch and one channel carry more problems, by assumption.** At branch `{HOT_BRANCH}` and
in the `{HOT_CHANNEL.value}` channel each problem archetype is {HOT_WEIGHT} times likelier (both
factors apply together). This exists so the report's breakdown has something to show.

**The reach probabilities are assumptions too.** Each attempt ends as below; an attempt that goes
unanswered, or where the customer asks for a later call, is followed by another, up to {MAX_STEPS}.
{DECLINED_AFTER_IDENTITY_SHARE:.0%} of the customers who decline do so after the identity checks.

| Outcome of one attempt | Chance |
|---|---|
{reach}

## Limits

- A simulated customer's replies come from the scenario phrase banks (`samajh/scenarios/phrases/`),
  so the text is templated: a few wordings per answer, Hindi and Hinglish only, model-written and
  model-reviewed with no human reviewer. Text only, no speech. A phone call brought in with
  `ingest` is speech read by Gnani Prisma (its case file names the model); the report says how many
  calls are of each kind.
- Premiums, covers, terms, cancellation windows and years of birth are limited to the values the
  phrase banks can say. They are not a realistic distribution of loan sizes or prices.
- Every loan has exactly one product, and every product is credit-life cover.
- No simulated attempt is made after day 30 from the sale, so a customer still to be retried then is
  "not reached within 30 days of the sale" and counts in the funnel, not among the counted calls.

## The review pages built on this book

- **No authentication (demo limitation).** The review pages and their API have no sign-in: anyone
  who can reach the server can record a decision, and the reviewer's name is free text that
  nobody checks. A real deployment needs sign-in and a named, authorised reviewer per decision.
- Draws do not overlap: each takes a share of the sales made since the previous draw that are
  still within 30 days of the sale (`uv run python -m samajh.ops draw --as-of DATE --rate 0.4`).
- Finished phone sessions enter with `uv run python -m samajh.ops ingest` (the rules are in the
  docstring of `samajh/ops/sessions.py`). Every session folder ends in exactly one place, and ingest
  never stops on a session:
  - **An attempt** only when the case file has a `book` block (written by the phone when it opened
    the call on a drawn loan) that matches the batch: the batch id, the loan's sale date, the draw
    that holds the loan, and a day since the sale equal to the call date minus the sale date. The
    attempt is dated by the book's `call_date` (the book's 2027 calendar, at the session's India
    time of day), never by the wall clock. It takes the loan's next attempt number.
  - **Outside the sample** (listed, never counted): a loan on the book that no draw holds ("the loan
    was not drawn in this batch", shown with the book's record); a drawn loan called without a
    `book` block; a packaged phone record (`hero`, `informed`, `third-party`).
  - **Skipped, with the reason**: no case file, an unreadable or malformed one (any field of the
    wrong type, a date outside the years 2000 to 2100, a case file that contradicts itself), one
    still running, a dialogue outcome with no attempt outcome, a `book` block that does not match the book, a call
    dated before the sale or before the loan's draw, a call on a loan whose attempts have ended
    (any outcome other than no answer, call back later or another language, including "asked not
    to be called again"), a call on a loan that already has {MAX_ATTEMPTS} logged attempts, simulated or
    phone (the most a loan gets; a superseded line and its replacement are one attempt, and a session
    already brought in is still recognised), and a call dated before the loan's last logged attempt
    (it cannot be put in without renumbering). Any other error while bringing in one session is a
    skip naming the error, with nothing written for it. The last ingest's list is kept in the store
    and shown on the attempt log; the report says how many sessions it left out, and they are in no
    count.
  - **Changed after it was brought in**: a session already brought in (an attempt or outside) whose
    case file now gives something else stays where it is, and the version brought in first is kept
    and counted. It is listed apart, with what differs, and is never among the skipped.
  - **A request from a speaker not confirmed as the borrower**: a case file's `speaker_confirmed` is
    true only once the year of birth has passed. A "do not call", "speak to a person" or "call back
    later" with `speaker_confirmed` false is the attempt outcome "request from a speaker not
    confirmed as the borrower": the loan is called again, and it is never counted as the borrower's
    own request. When `speaker_confirmed` is present, "right person confirmed" follows it; a case
    file without it is read as before.
  - A phone attempt after day 30 from the sale is logged and shown, and is never counted in the
    outcome shares. Running ingest again changes nothing, except that a case file that failed and
    was rebuilt to `ready` turns its "completed, not analysed" attempt into the analysed call (both
    lines stay in `attempts.jsonl`; the later one says what it supersedes). The simulator, run
    after a phone attempt, continues the loan's numbering after it and counts it towards the
    attempt limit.
  - The note on phone calls is counted from each case file's `customer_audio` (microphone,
    prepared audio files, both, none, or not recorded in the case file). No phone call is a real
    customer's.

## The rendered pages

`references/pilots/p3b-artifacts/` holds the review pages rendered from the demo batch on this book
(`uv run python -m samajh.ops demo`), with copies of this machine's phone sessions brought in.
`RENDERED.md` in that folder names the commit and the working-tree state of the render.

- The pages committed at 4180556 showed 11 of the 64 analysed calls referred for review. The pages
  rendered again on 2026-11-10 show 7, on the same book, draws and scripted calls. No committed
  code gives 11: the code of commit 4180556 itself, and of each commit after it up to 993edf4,
  gives 7. The four calls that differ are customers who said at the open question that they took
  nothing with the loan and then, asked directly, named the product as insurance. The old pages
  show each as a referral ("said they took nothing with the loan"). The rule in the code
  (`samajh/rules/checks.py`, `recall`) is that a denial is withdrawn when the customer names the
  product as the kind on record in a later turn, so each of these calls is an understanding gap
  ("did not name the product before it was mentioned"), reported in aggregate. The likely cause,
  not confirmed: the old pages were rendered from a working tree in which the rules were being
  edited, a state that was never committed.
- The pages rendered on 2026-11-13 (commit 2568759 plus the ops edits; `RENDERED.md`) show 8
  referrals of 65 completed calls, one of them the loan-book phone call (attempt 1 on
  SYN-PL-270107-0008, ingested before the simulated calls).
"""


def write_book(
    directory: Path, meta: BookMeta, loans: Sequence[BookLoan], customers: Sequence[SimCustomer]
) -> None:
    """Write the four files. Each is written to a temporary file and moved into place."""
    counts = Counter(c.archetype for c in customers)
    parameters = {
        "seed": meta.seed,
        "loans": meta.loans,
        "sold_from": meta.sold_from.isoformat(),
        "days": (meta.sold_to - meta.sold_from).days + 1,
        "lender_type": meta.lender_type.value,
        "hot_branch": HOT_BRANCH,
        "hot_channel": HOT_CHANNEL.value,
        "hot_weight": HOT_WEIGHT,
        "paid_from_loan_share": PAID_FROM_LOAN_SHARE,
        "max_steps": MAX_STEPS,
        "reach": {outcome.value: chance for outcome, chance in REACH.items()},
        "declined_after_identity_share": DECLINED_AFTER_IDENTITY_SHARE,
        "archetype_weights": {name: a.weight for name, a in ARCHETYPES.items()},
    }
    summary = {
        "meta": meta.model_dump(mode="json"),
        "parameters": parameters,
        "archetypes": {name: counts[name] for name in ARCHETYPES},
    }
    files = {
        "book.jsonl": jsonl(loans),
        "sim-customers.jsonl": jsonl(customers),
        "BOOK.json": json.dumps(summary, indent=2) + "\n",
        "README.md": _readme(meta, counts),
    }
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        temporary = directory / f".{name}.tmp"
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, directory / name)


def parse_loans(text: str) -> tuple[BookLoan, ...]:
    return tuple(BookLoan.model_validate_json(line) for line in text.splitlines() if line)


def load_book(directory: Path = DATA_DIR) -> tuple[BookMeta, tuple[BookLoan, ...]]:
    """The book on disk. Fails if `book.jsonl` is not the file `BOOK.json` describes."""
    meta = BookMeta.model_validate(json.loads((directory / "BOOK.json").read_text(encoding="utf-8"))["meta"])
    loans = parse_loans((directory / "book.jsonl").read_text(encoding="utf-8"))
    if book_sha256(loans) != meta.sha256:
        raise ValueError(f"{directory / 'book.jsonl'} does not match the sha256 in BOOK.json")
    return meta, loans


def load_customers(directory: Path = DATA_DIR) -> dict[str, SimCustomer]:
    """The simulation's hidden truth, by loan id. Only the call simulator may read it."""
    text = (directory / "sim-customers.jsonl").read_text(encoding="utf-8")
    customers = (SimCustomer.model_validate_json(line) for line in text.splitlines() if line)
    return {c.loan_id: c for c in customers}
