"""Rule registry and `evaluate`: (LoanRecord, Beliefs) -> CaseResult. Pure and deterministic."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from samajh.rules import checks
from samajh.rules.checks import Rule
from samajh.rules.clauses import CLAUSES
from samajh.types import (
    EVIDENCE_PACK_RULES,
    AnswerConflict,
    Beliefs,
    CaseResult,
    EvidencePack,
    Flag,
    Gap,
    LenderType,
    LoanRecord,
    Outcome,
    Passed,
    Product,
    ProductBeliefs,
    ProductResult,
    Question,
    RuleId,
    Stated,
    Verdict,
    tier_of,
)

Outcomes = tuple[Outcome, ...]
Check = Callable[[Rule, LoanRecord, Beliefs], Outcomes]
ProductCheck = Callable[[Rule, Product, Beliefs], Outcomes]


@dataclass(frozen=True)
class RuleSpec:
    """One rule: its id, a plain title for reports, and its check."""

    id: RuleId
    title: str
    check: Check

    def clause(self, lender_type: LenderType) -> str:
        """The paragraph this rule may engage for a lender of this type."""
        return CLAUSES[lender_type][self.id]


def _per_product(check: ProductCheck, case_level: Check | None = None) -> Check:
    """Adapt a per-product rule to the registry signature. There is no implicit pass."""

    def run(rule: Rule, record: LoanRecord, beliefs: Beliefs) -> Outcomes:
        outcomes: list[Outcome] = []
        for product in record.products:
            found = check(rule, product, beliefs)
            if not found or any(o.product_id != product.id for o in found):
                raise RuntimeError(f"rule {rule.id} did not commit to an outcome for {product.id}")
            outcomes += found
        if case_level:
            outcomes += case_level(rule, record, beliefs)
        return tuple(outcomes)

    return run


def _spec(rule: RuleId, title: str, check: Check) -> RuleSpec:
    return RuleSpec(id=rule, title=title, check=check)


RULES: tuple[RuleSpec, ...] = (
    _spec(RuleId.kind, "The customer knows what kind of product it is.", _per_product(checks.kind)),
    _spec(RuleId.premium, "The customer knows what the product cost.", _per_product(checks.premium)),
    _spec(RuleId.cover, "The customer knows the cover amount.", _per_product(checks.cover)),
    _spec(RuleId.term, "The customer knows how long the product runs.", _per_product(checks.term)),
    _spec(
        RuleId.cancel_window,
        "What the customer was told about cancelling matches the window on the record.",
        _per_product(checks.cancel_window),
    ),
    _spec(
        RuleId.recall,
        "The customer names the product unprompted when asked what they took with the loan.",
        _per_product(checks.recall),
    ),
    _spec(
        RuleId.recall_unmatched,
        "Every product the customer names unprompted is on the lender's record.",
        checks.recall_unmatched,
    ),
    _spec(
        RuleId.consent,
        "The lender has a consent record and the customer's own account of agreeing matches it.",
        _per_product(checks.consent),
    ),
    _spec(
        RuleId.loan_funded,
        "A premium deducted from the loan has a consent record and the customer knows about it.",
        _per_product(checks.loan_funded),
    ),
    _spec(
        RuleId.bundling,
        "A product required for the loan is a risk mitigant offered with a choice of provider.",
        _per_product(checks.bundling),
    ),
    _spec(
        RuleId.belief_mismatch,
        "What the customer believes about the product matches its features.",
        _per_product(checks.belief_mismatch),
    ),
    _spec(
        RuleId.sale_conduct,
        "The customer voices no concern about how the product was sold.",
        checks.sale_conduct,
    ),
    _spec(
        RuleId.evidence,
        "Every quote used as evidence is found in the call transcript.",
        _per_product(checks.evidence, checks.evidence_case),
    ),
)


def verdict_of(outcomes: Iterable[Passed | Flag | Gap]) -> Verdict:
    """Any flag -> flag_for_review; else any gap -> unclear_needs_human; else clear."""
    verdict = Verdict.clear
    for outcome in outcomes:
        if isinstance(outcome, Flag):
            return Verdict.flag_for_review
        if isinstance(outcome, Gap):
            verdict = Verdict.unclear_needs_human
    return verdict


def _check_ids(record: LoanRecord, beliefs: Beliefs) -> None:
    """Beliefs about another loan, or about a product not on the record, must not be judged."""
    if beliefs.loan_id != record.loan_id:
        raise ValueError(f"beliefs are for loan {beliefs.loan_id}, record is {record.loan_id}")
    on_record = {p.id for p in record.products}
    believed = [b.product_id for b in beliefs.products]
    unknown = sorted(set(believed) - on_record)
    if unknown:
        raise ValueError(f"beliefs name products that are not on the record: {unknown}")
    if len(believed) != len(set(believed)):
        raise ValueError("beliefs name the same product more than once")
    stray = sorted({i.product_id for i in beliefs.recall.items if i.product_id is not None} - on_record)
    if stray:
        raise ValueError(f"recall items name products that are not on the record: {stray}")


# The question each stated belief answers, for a self-correction kept beside it.
_BELIEF_QUESTION: dict[str, Question] = {
    "kind": Question.kind,
    "premium_inr": Question.premium,
    "cover_inr": Question.cover,
    "term_months": Question.term,
    "payment_source": Question.payment_source,
    "payment_frequency": Question.payment_frequency,
    "required_for_loan": Question.required_for_loan,
    "provider_choice_offered": Question.provider_choice,
    "cancel_allowed": Question.cancel_window,
    "cancel_window_days": Question.cancel_window,
    "consent_given": Question.consent,
    "consent_method": Question.consent,
    "feature_probe": Question.features,
}


def self_corrections(beliefs: ProductBeliefs) -> tuple[AnswerConflict, ...]:
    """Each stated belief kept with earlier words from its own reply: (the earlier words, the whole reply).

    The extractor puts them there when the customer corrected themselves inside one reply and both
    model readings agreed on the clause holding the final answer. Not an outcome: never in the tier.
    """
    found: list[AnswerConflict] = []
    for name, question in _BELIEF_QUESTION.items():
        answer = getattr(beliefs, name)
        if not isinstance(answer, Stated):
            continue
        for earlier in answer.also:
            if earlier.turn_id == answer.evidence.turn_id and earlier != answer.evidence:
                item = AnswerConflict(question=question, answers=(earlier, answer.evidence))
                if item not in found:
                    found.append(item)
    return tuple(found)


def evaluate(record: LoanRecord, beliefs: Beliefs) -> CaseResult:
    """Run every rule. The case verdict and tier are the worst of any product or case-level rule.

    A question whose answers differed adds an `answers_conflict` flag under its rule and takes
    away that rule's pass for the product; the rule's own flags and gaps stay.
    """
    _check_ids(record, beliefs)
    rules = {spec.id: Rule(spec.id, spec.clause(record.lender_type)) for spec in RULES}
    outcomes: list[Outcome] = []
    for spec in RULES:
        outcomes += spec.check(rules[spec.id], record, beliefs)
    for product in record.products:
        conflicting = checks.conflicts(rules, product, beliefs)
        contested = {(flag.rule_id, flag.product_id) for flag in conflicting}
        outcomes = [
            o for o in outcomes if not (isinstance(o, Passed) and (o.rule_id, o.product_id) in contested)
        ]
        outcomes += conflicting

    def result_for(product: Product) -> ProductResult:
        own = [o for o in outcomes if o.product_id == product.id]
        flags = tuple(o for o in own if isinstance(o, Flag))
        pack_flags = tuple(f for f in flags if f.rule_id in EVIDENCE_PACK_RULES)
        pack = None
        if pack_flags:
            pack = EvidencePack(
                loan_id=record.loan_id,
                call_id=beliefs.call_id,
                lender_type=record.lender_type,
                product=product,
                flags=pack_flags,
            )
        gaps = tuple(o for o in own if isinstance(o, Gap))
        return ProductResult(
            self_corrections=self_corrections(beliefs.for_product(product.id)),
            product_id=product.id,
            verdict=verdict_of(own),
            tier=tier_of(flags, gaps),
            flags=flags,
            gaps=gaps,
            passed=tuple(o.rule_id for o in own if isinstance(o, Passed)),
            evidence_pack=pack,
        )

    case_level = [o for o in outcomes if o.product_id is None]
    every_flag = tuple(o for o in outcomes if isinstance(o, Flag))
    every_gap = tuple(o for o in outcomes if isinstance(o, Gap))
    return CaseResult(
        loan_id=record.loan_id,
        call_id=beliefs.call_id,
        language=beliefs.language,
        verdict=verdict_of(outcomes),
        tier=tier_of(every_flag, every_gap),
        products=tuple(result_for(p) for p in record.products),
        case_flags=tuple(o for o in case_level if isinstance(o, Flag)),
        case_gaps=tuple(o for o in case_level if isinstance(o, Gap)),
        unmatched_recall=tuple(i for i in beliefs.recall.items if i.product_id is None),
    )
