"""The reviewer's case summary: one line per distinct issue. Pure: record and result in, summary out.

A misled customer can raise many flags for a few issues (an FD named in recall and at the kind
question, the bundling and feature checks that follow from it). Flags that describe the same
issue share a key and become one line. A line is evidence for review, never a finding.
"""

from collections.abc import Iterable
from typing import ClassVar

from samajh.rules.checks import CONSENT_LABEL, FEATURE_LABEL, KIND_LABEL, QUESTION_RULE, rupees
from samajh.rules.clauses import KIND_ON_RECORD
from samajh.types import (
    AnswerConflict,
    Basis,
    CaseResult,
    FeatureClaim,
    Flag,
    FlagReason,
    Frozen,
    Gap,
    GapReason,
    KindClaim,
    LoanRecord,
    Product,
    ProductId,
    ProductKind,
    Question,
    RuleId,
    Tier,
    TurnId,
    referral_basis,
)

R = FlagReason

NOT_ASKED = "not_asked"  # the key of a case-level line of questions never asked
RECORD_ONLY_MARK = "from the lender's record; no customer statement"
# The first line of a summary whose referral rests on the lender's record alone. True of every such
# referral: a gap or a lower-tier flag may rest on the customer's words, but never the referral.
RECORD_ONLY_FIRST_LINE = (
    "Referred on the lender's record alone; nothing the customer said is the reason for the referral."
)


class IssueLine(Frozen):
    """One distinct issue for a reviewer: what it is, what the record shows, the customer's words."""

    product_id: ProductId | None  # None for a case-level line
    tier: Tier
    title: str  # one plain sentence: what the issue is
    record_value: str  # what the lender's record shows
    quote: str | None  # the customer's best quote
    turn_id: TurnId | None
    clauses: tuple[str, ...]  # the paragraphs the merged flags may engage
    rule_ids: tuple[RuleId, ...]  # the rules merged into this line
    record_only: bool = False  # True when no outcome carries a customer quote: the line rests on the record
    # True for a note, not an issue: a correction the customer made inside one reply. A note has
    # tier `clear` so that no display or count treats it as something to refer or report.
    note: bool = False
    # On a `refer` line: what its refer-tier flags rest on (`referral_basis`). None on other lines.
    basis: Basis | None = None

    added_later: ClassVar[frozenset[str]] = frozenset({"basis"})


class CaseSummary(Frozen):
    """Every issue of one call: refer first, then incomplete, then understanding gaps.

    `referral_basis` is the case's (`CaseResult.referral_basis`). `first_line` is set only on a
    referral on the record alone: `RECORD_ONLY_FIRST_LINE`, shown above
    the lines.
    """

    loan_id: str
    call_id: str
    tier: Tier
    lines: tuple[IssueLine, ...]
    referral_basis: Basis | None = None
    first_line: str | None = None

    added_later: ClassVar[frozenset[str]] = frozenset({"referral_basis", "first_line"})


# --- which flags are one issue -------------------------------------------------

# The refer-tier issue each flag reason belongs to. Conflicts and sale concerns are keyed per flag.
ISSUE: dict[FlagReason, str] = {
    R.kind_differs: "kind",
    R.kind_dont_know: "kind",
    R.bundled_described_as_deposit: "kind",
    R.consent_no_record: "consent",
    R.consent_not_recognised: "consent",
    R.consent_method_differs: "consent",
    R.consent_dont_know: "consent",
    R.funded_no_consent: "consent",
    R.funded_says_separately: "payment",
    R.funded_dont_know: "payment",
    R.unfunded_says_deducted: "payment",
    R.bundled_not_mitigant: "bundling",
    R.bundled_no_choice_on_record: "bundling",
    R.bundled_no_choice_told: "bundling",
    R.premium_differs_confirmed: "premium",
    R.cover_differs_confirmed: "cover",
    R.recall_denied: "denied",
    R.recall_off_record: "off_record",
}


def never_asked(o: Flag | Gap) -> bool:
    """The question was never put on the call, as opposed to asked with no usable answer.

    `checks._gap_for` turns `NotAsked` into `GapReason.not_asked` with no quote. The premium gap for
    a read-back never asked is also `not_asked` but carries the amount the customer said: that
    question was asked, so it is not counted here.
    """
    return isinstance(o, Gap) and o.reason is GapReason.not_asked and o.quote is None


def _key(index: int, o: Flag | Gap) -> tuple:
    if isinstance(o, Gap) or o.tier is not Tier.refer:
        # One line per rule for a product. The case-level gaps share one line, with the questions
        # never asked on a line of their own so that each line's statement is true of all of it.
        if o.product_id is None:
            return (o.tier, NOT_ASKED) if never_asked(o) else (o.tier,)
        return (o.tier, o.rule_id)
    if o.reason is R.feature_contradicted:
        if o.claim is FeatureClaim.is_deposit:
            return ("kind",)
        return ("single",) if o.claim is FeatureClaim.one_time_payment else ("beliefs",)
    if o.reason is R.sale_concern:
        return ("concern", o.heard)
    if o.reason is R.answers_conflict:
        return ("conflict", index)
    return (ISSUE[o.reason],)


# --- what the record shows -----------------------------------------------------

PRODUCT_LABEL: dict[ProductKind, str] = {ProductKind.credit_life: "credit-life insurance"}

FEATURE_SHORT: dict[FeatureClaim, str] = {
    FeatureClaim.is_deposit: "a deposit",
    FeatureClaim.refundable_anytime: "money back at any time",
    FeatureClaim.guaranteed_return: "a guaranteed return",
    FeatureClaim.one_time_payment: "a single payment",
    FeatureClaim.withdrawable_after_period: "withdrawal after a period",
}


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _record_part(rule: RuleId, record: LoanRecord, p: Product | None) -> str:
    if p is None:
        if rule is RuleId.recall_unmatched:
            return "products on record: " + "; ".join(f"{_describe(q)} ({q.id})" for q in record.products)
        return (
            f"loan {record.loan_id}: {record.loan_kind} loan, {rupees(record.disbursed_inr)} "
            f"disbursed on {record.disbursed_on.isoformat()}"
        )
    if rule in (RuleId.premium, RuleId.loan_funded):
        return f"premium {rupees(p.premium_inr)}, {'deducted from the loan' if p.paid_from_loan else 'paid separately'}"
    if rule is RuleId.cover:
        return f"cover {rupees(p.cover_inr)}"
    if rule is RuleId.term:
        return f"term {p.term_months} months"
    if rule is RuleId.cancel_window:
        if p.cancel_window_days is None:
            return "no cancellation window on record"
        return f"cancellation window {p.cancel_window_days} days"
    if rule is RuleId.consent:
        if p.consent is None:
            return "no consent on record"
        method = CONSENT_LABEL[p.consent.method].removeprefix("a ").removeprefix("an ")
        return f"consent on record: {method} on {p.consent.at.isoformat()}"
    if rule is RuleId.bundling:
        return (
            f"required for the loan: {_yes(p.required_for_loan)}; risk mitigant: {_yes(p.risk_mitigant)}; "
            f"choice of provider offered: {_yes(p.provider_choice_offered)}"
        )
    if rule is RuleId.belief_mismatch:
        features = [FEATURE_SHORT[c] for c in FeatureClaim if c in p.features]
        return "features on record: " + (", ".join(features) or "none")
    return _describe(p)  # kind, recall, evidence


def _describe(p: Product) -> str:
    return f"{PRODUCT_LABEL[p.kind]} from {p.provider}"


# What the issue is about, for conflicts and for the incomplete and understanding lines.
TOPIC: dict[RuleId, str] = {
    RuleId.kind: "what the product is",
    RuleId.premium: "the premium",
    RuleId.cover: "the cover",
    RuleId.term: "the term",
    RuleId.cancel_window: "the cancellation window",
    RuleId.recall: "naming the product unprompted",
    RuleId.recall_unmatched: "something named that may not be on the record",
    RuleId.consent: "how they agreed to it",
    RuleId.loan_funded: "how it was paid for",
    RuleId.bundling: "whether it was required and the choice of provider",
    RuleId.belief_mismatch: "getting the money back",
    RuleId.sale_conduct: "how the product was sold",
    RuleId.evidence: "quotes the transcript does not support",
}


def _topic(o: Flag | Gap) -> str:
    if isinstance(o, Flag) and o.reason in (R.frequency_dont_know, R.frequency_recurring_on_single):
        return "how often it is paid"
    return TOPIC[o.rule_id]


# --- one line ------------------------------------------------------------------


def _unique(items: Iterable) -> list:
    return list(dict.fromkeys(items))


def _and(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] + "."


def _best_quote(outcomes: list[Flag | Gap]) -> tuple[str | None, TurnId | None]:
    """The customer's own words: a flag from their answer, then a record flag, then a gap's quote.

    A flag on the record alone (`Flag.basis`) has an incidental quote, so it comes after the others.
    A gap whose quote was not found in the transcript is never quoted.
    """
    flags = [o for o in outcomes if isinstance(o, Flag)]
    ranked = [
        *(f for f in flags if f.basis is Basis.customer_statement),
        *(f for f in flags if f.basis is Basis.record_only),
        *(g for g in outcomes if isinstance(g, Gap) and g.reason is not GapReason.quote_not_grounded),
    ]
    for o in ranked:
        if o.quote is not None:
            return o.quote, o.turn_id
    return None, None


def _kind_title(p: Product, flags: list[Flag]) -> str:
    said = {f"customer described it as {label}": label for label in KIND_LABEL.values()}
    kinds = _unique(said[f.heard] for f in flags if f.reason is R.kind_differs)
    if not kinds and any(f.reason is not R.kind_dont_know for f in flags):
        kinds = [KIND_LABEL[KindClaim.deposit]]
    start = (
        f"customer described the product as {_and(kinds)}"
        if kinds
        else "customer did not know what the product is"
    )
    return f"{start}; the record shows {KIND_LABEL[KIND_ON_RECORD[p.kind]]}"


CONSENT_TITLE: dict[FlagReason, str] = {
    R.consent_no_record: "the record has no consent for this product",
    R.funded_no_consent: "the premium was deducted from the loan without a recorded consent",
    R.consent_not_recognised: "customer's account of what they agreed to buy does not include this product",
    R.consent_dont_know: "customer did not know whether they agreed to this product",
}

PAYMENT_TITLE: dict[FlagReason, str] = {
    R.funded_says_separately: "customer said the premium was paid separately; the record shows it deducted from the loan",
    R.funded_dont_know: "customer did not know the premium was deducted from the loan",
    R.unfunded_says_deducted: "customer said the premium was deducted from the loan; the record shows it paid separately",
}

BUNDLING_TITLE: dict[FlagReason, str] = {
    R.bundled_not_mitigant: "the record does not mark it as a risk mitigant",
    R.bundled_no_choice_on_record: "the record shows no choice of provider was offered",
    R.bundled_no_choice_told: "customer says they were not told they could buy it from another provider",
}


# A flag that says the customer's figure is not the record's.
FIGURE = frozenset(
    {
        R.premium_differs, R.premium_approximate, R.cover_differs, R.cover_differs_unconfirmed,
        R.term_differs, R.cancel_window_differs,
    }
)  # fmt: skip


def _rule_title(outcomes: list[Flag | Gap]) -> str:
    """One rule's incomplete or understanding-gap line: not knowing and a different figure apart."""
    parts = []
    first_gap = next((o for o in outcomes if isinstance(o, Gap)), None)
    for o in outcomes:
        topic = _topic(o)
        if never_asked(o):
            continue
        if o.rule_id is RuleId.belief_mismatch and isinstance(o, Gap) and o is not first_gap:
            # `checks.belief_mismatch` returns the money-back probe's gap, then the frequency one.
            topic = "how often it is paid"
        if isinstance(o, Gap):
            parts.append(f"the call left {topic} undecided")
        elif o.reason is R.answers_conflict:
            answers = ", ".join(f'"{q}"' for q in (o.quote, *(e.quote for e in o.also)))
            parts.append(f"customer gave differing answers about {topic}: {answers}")
        elif o.reason.value.endswith("_dont_know"):
            parts.append(f"customer did not know {topic}")
        elif o.reason in FIGURE:
            parts.append(f"customer gave a different figure for {topic} ({o.heard})")
        else:
            parts.append(o.heard)
    unasked = [o for o in outcomes if never_asked(o)]
    if unasked:
        parts.append(_did_not_get_to(unasked))
    return "; ".join(_unique(parts))


# A question never put has no answer to describe: the recall topics name the question instead.
NOT_ASKED_TOPIC: dict[RuleId, str] = {
    RuleId.recall: "the open question about what they took with the loan",
    RuleId.recall_unmatched: "the open question about what they took with the loan",
}


def _did_not_get_to(outcomes: list[Flag | Gap]) -> str:
    topics = (NOT_ASKED_TOPIC.get(o.rule_id) or _topic(o) for o in outcomes)
    return "the call did not get to: " + "; ".join(_unique(topics))


def _title(key: tuple, record: LoanRecord, p: Product | None, outcomes: list[Flag | Gap]) -> str:
    flags = [o for o in outcomes if isinstance(o, Flag)]
    issue = key[0]
    topics = "; ".join(_unique(map(_topic, outcomes)))
    if issue in (Tier.incomplete, Tier.understanding_gap) and key[1:] == (NOT_ASKED,):
        return _did_not_get_to(outcomes)
    if issue in (Tier.incomplete, Tier.understanding_gap) and len(key) > 1:
        return _rule_title(outcomes)
    if issue is Tier.incomplete:
        return f"the call left these questions undecided: {topics}"
    if issue is Tier.understanding_gap:
        return f"customer did not know, or gave a different answer about: {topics}"
    if issue == "conflict":
        (f,) = flags
        answers = ", ".join(f'"{e}"' for e in (f.quote, *(a.quote for a in f.also)))
        return f"customer gave differing answers about {TOPIC[f.rule_id]}: {answers}"
    if issue == "concern":
        return key[1]
    if issue == "off_record":
        quotes = ", ".join(f'"{f.quote}"' for f in flags)
        return f"customer named products that do not match the lender's record: {quotes}"
    assert p is not None  # every other issue belongs to a product
    if issue == "kind":
        return _kind_title(p, flags)
    if issue in ("beliefs", "single"):
        believed = _and(_unique(FEATURE_LABEL[f.claim] for f in flags if f.claim is not None))
        return f"customer believes {believed}; the record does not list this feature"
    if issue == "premium":
        return f"{flags[0].heard} and confirmed it at the read-back; the record shows {rupees(p.premium_inr)}"
    if issue == "cover":
        return f"{flags[0].heard} and confirmed it at the read-back; the record shows cover of {rupees(p.cover_inr)}"
    if issue == "denied":
        return "customer said they took nothing with the loan; the record shows this product"
    if issue == "consent":
        return "; ".join(_unique(CONSENT_TITLE.get(f.reason, f.heard) for f in flags))
    if issue == "payment":
        return "; ".join(_unique(PAYMENT_TITLE[f.reason] for f in flags))
    required = "the record marks it as required for the loan"
    if not p.required_for_loan:
        required = "customer says it was required for the loan"
    return "; ".join([required, *_unique(BUNDLING_TITLE[f.reason] for f in flags)])


def _line(key: tuple, record: LoanRecord, p: Product | None, outcomes: list[Flag | Gap]) -> IssueLine:
    rule_ids = tuple(_unique(o.rule_id for o in outcomes))
    shown = {"kind": (RuleId.kind,), "denied": (RuleId.kind, RuleId.premium)}.get(key[0], rule_ids)
    quote, turn_id = _best_quote(outcomes)
    title = _title(key, record, p, outcomes)
    # A line with a flag and no customer words anywhere rests on the lender's record alone.
    record_only = any(isinstance(o, Flag) for o in outcomes) and all(o.quote is None for o in outcomes)
    if record_only:
        title += f" ({RECORD_ONLY_MARK})"
    tier = outcomes[0].tier
    return IssueLine(
        product_id=p.id if p else None,
        tier=tier,
        title=_sentence(title),
        record_value="; ".join(_unique(_record_part(rule, record, p) for rule in shown)),
        quote=quote,
        turn_id=turn_id,
        clauses=tuple(_unique(o.clause for o in outcomes)),
        rule_ids=rule_ids,
        record_only=record_only,
        basis=referral_basis(o for o in outcomes if isinstance(o, Flag)) if tier is Tier.refer else None,
    )


# What a self-correction was about, by the question it answered.
QUESTION_TOPIC: dict[Question, str] = {
    Question.kind: "what the product is",
    Question.premium: "the premium",
    Question.payment_source: "how it was paid for",
    Question.required_for_loan: "whether it was required for the loan",
    Question.provider_choice: "whether they could buy it from another provider",
    Question.cover: "the cover",
    Question.term: "the term",
    Question.cancel_window: "the cancellation window",
    Question.features: "getting the money back",
    Question.consent: "how they agreed to it",
    Question.payment_frequency: "how often it is paid",
}


def _note(record: LoanRecord, p: Product, item: AnswerConflict) -> IssueLine:
    """A correction inside one reply whose final answer stood: shown so the reviewer sees the earlier words."""
    earlier, reply = item.answers[0], item.answers[-1]
    rule = QUESTION_RULE[item.question]
    return IssueLine(
        product_id=p.id,
        tier=Tier.clear,
        title=(
            f'Customer first said "{earlier.quote}" about {QUESTION_TOPIC[item.question]}, '
            "then corrected it in the same reply."
        ),
        record_value=_record_part(rule, record, p),
        quote=reply.quote,
        turn_id=reply.turn_id,
        clauses=(),
        rule_ids=(rule,),
        note=True,
    )


def summarise(record: LoanRecord, result: CaseResult) -> CaseSummary:
    """One line per distinct issue: by tier, then product in record order (case-level last), then first seen.

    On every case, clear ones included, a note line follows for each correction the customer made
    inside one reply (`ProductResult.self_corrections`), after every issue. A note line has tier
    `clear` and `note=True`; notes never change the case tier.
    """
    products = {p.id: p for p in record.products}
    groups: dict[tuple, list[Flag | Gap]] = {}
    scopes = [*((p.product_id, (*p.flags, *p.gaps)) for p in result.products)]
    scopes.append((None, (*result.case_flags, *result.case_gaps)))
    for product_id, outcomes in scopes:
        for index, o in enumerate(outcomes):
            groups.setdefault((product_id, *_key(index, o)), []).append(o)
    lines = [_line(key[1:], record, products.get(key[0]), found) for key, found in groups.items()]
    order = list(Tier)
    lines.sort(key=lambda line: order.index(line.tier))
    lines += [_note(record, products[p.product_id], item) for p in result.products for item in p.self_corrections]
    basis = result.referral_basis
    return CaseSummary(
        loan_id=result.loan_id,
        call_id=result.call_id,
        tier=result.tier,
        lines=tuple(lines),
        referral_basis=basis,
        first_line=RECORD_ONLY_FIRST_LINE if basis is Basis.record_only else None,
    )


# --- how the call ended ----------------------------------------------------------

# The dialogue's `Outcome` values (samajh.dialogue.machine), as a reviewer reads them. Kept here as
# strings so the core does not import the dialogue; a test checks every `Outcome` has a label.
CALL_ENDED: dict[str, str] = {
    "completed": "The call reached its closing lines",
    "wrong_party": "Ended early: the person who answered said they are not the borrower",
    "not_confirmed": "Ended early: nobody confirmed being the borrower",
    "no_go_ahead": "Ended early: no clear go-ahead after the opening",
    "second_check_failed": "Ended early: the year-of-birth check did not match",
    "declined": "Ended early: the customer declined to go on",
    "human_requested": "Ended early: the customer asked to speak to a person",
    "turn_limit": "Ended early: the call reached its turn limit",
    "call_back_later": "Ended early: the customer asked to be called another time",
    "language_switch": "Ended early: the customer asked for another language",
    "no_response": "Ended early: nothing was heard from the customer, several times in a row",
    "do_not_call": "Ended early: the customer asked not to be called again",
    "written_requested": "Ended early: the customer asked for this in writing instead",
}

# A call that stopped before the dialogue reached an end ("in_progress" in the case file).
CALL_UNFINISHED = "Stopped before the call finished: the recording ends there (a hang-up or a dropped line)"


def call_ended_label(outcome: str | None) -> str:
    """How the call ended, for a reviewer. Total: an unknown value comes back readable, never raises."""
    if outcome is None or outcome.strip() in ("", "in_progress"):
        return CALL_UNFINISHED
    if outcome in CALL_ENDED:
        return CALL_ENDED[outcome]
    return "Ended: " + outcome.strip().replace("_", " ")
