"""The reviewer's case summary: one line per distinct issue. Pure: record and result in, summary out.

A misled customer can raise many flags for a few issues (an FD named in recall and at the kind
question, the bundling and feature checks that follow from it). Flags that describe the same
issue share a key and become one line. A line is evidence for review, never a finding.
"""

from collections.abc import Iterable

from samajh.rules.checks import CONSENT_LABEL, FEATURE_LABEL, KIND_LABEL, rupees
from samajh.rules.clauses import KIND_ON_RECORD
from samajh.types import (
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
    RuleId,
    Tier,
    TurnId,
)

R = FlagReason


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


class CaseSummary(Frozen):
    """Every issue of one call: refer first, then incomplete, then understanding gaps."""

    loan_id: str
    call_id: str
    tier: Tier
    lines: tuple[IssueLine, ...]


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
    R.recall_denied: "denied",
    R.recall_off_record: "off_record",
}

# Flags raised from the record alone: their quote is incidental, so it is the last choice.
FROM_RECORD = frozenset(
    {R.consent_no_record, R.funded_no_consent, R.bundled_not_mitigant, R.bundled_no_choice_on_record}
)


def _key(index: int, o: Flag | Gap) -> tuple:
    if isinstance(o, Gap) or o.tier is not Tier.refer:
        # One line per rule for a product; the case-level gaps share one line.
        return (o.tier,) if o.product_id is None else (o.tier, o.rule_id)
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

    A gap whose quote was not found in the transcript is never quoted.
    """
    flags = [o for o in outcomes if isinstance(o, Flag)]
    ranked = [
        *(f for f in flags if f.reason not in FROM_RECORD),
        *(f for f in flags if f.reason in FROM_RECORD),
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
    for o in outcomes:
        topic = _topic(o)
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
    return "; ".join(_unique(parts))


def _title(key: tuple, record: LoanRecord, p: Product | None, outcomes: list[Flag | Gap]) -> str:
    flags = [o for o in outcomes if isinstance(o, Flag)]
    issue = key[0]
    topics = "; ".join(_unique(map(_topic, outcomes)))
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
    return IssueLine(
        product_id=p.id if p else None,
        tier=outcomes[0].tier,
        title=_sentence(_title(key, record, p, outcomes)),
        record_value="; ".join(_unique(_record_part(rule, record, p) for rule in shown)),
        quote=quote,
        turn_id=turn_id,
        clauses=tuple(_unique(o.clause for o in outcomes)),
        rule_ids=rule_ids,
    )


def summarise(record: LoanRecord, result: CaseResult) -> CaseSummary:
    """One line per distinct issue: by tier, then product in record order (case-level last), then first seen."""
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
    return CaseSummary(loan_id=result.loan_id, call_id=result.call_id, tier=result.tier, lines=tuple(lines))
