"""Types for the scenario set: the lender's record, what the customer believes, and the gold verdict.

A `BaseCase` is language-neutral and written by hand in `cases.py`, gold included. A `Scenario` is
one base case in one call language. Nothing here imports `samajh.rules`: gold is written from the
scenario's facts and is compared with the rule engine only afterwards (`consistency.py`).
"""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from samajh.types import (
    ConsentMethod,
    FeatureClaim,
    Frozen,
    KindClaim,
    Language,
    LenderType,
    LoanKind,
    LoanRecord,
    PaymentSource,
    Product,
    ProductId,
    RawExtraction,
    RuleId,
    SaleConcern,
    Transcript,
    Verdict,
)

NOT_HUMAN_REVIEWED = "not human-reviewed"
MODEL_REVIEWED_ONLY = "model-written, model-reviewed, no human reviewer"
REVIEW_LABEL: dict[Language, str] = {
    Language.hi: MODEL_REVIEWED_ONLY,
    Language.hi_en: MODEL_REVIEWED_ONLY,
    Language.ta: NOT_HUMAN_REVIEWED,
    Language.kn: NOT_HUMAN_REVIEWED,
}

# How the customer answers one question when they give no value.
Unknown = Literal["dont_know", "evasive"]
DONT_KNOW: Unknown = "dont_know"
EVASIVE: Unknown = "evasive"  # a non-answer such as "yes, all fine" to an open question


class Recall(StrEnum):
    """What the customer does at the open-recall question, before any product is named."""

    named = "named"  # names the product (as whatever they believe it is)
    not_named = "not_named"  # says they took only the loan
    dont_know = "dont_know"
    evasive = "evasive"


class DepositWord(StrEnum):
    """Which word a customer who believes the product is a deposit uses for it."""

    fd = "fd"
    security_deposit = "security_deposit"


class ProductBelief(Frozen):
    """What the customer truly believes about one product. This is the scenario's ground truth.

    `provider_choice_offered` is None when the question is not asked (the product was not required
    per the record or per the customer). `cancel_window_days` is None unless `cancel_allowed` is
    True. `money_back` is the reply to the money-back probe: the claims made, or () for none.
    `money_back_mentions_window` marks a correct "no, except inside the cancellation window".
    `one_time_claim`: the customer volunteers, at the premium question, that it is paid only once.
    """

    product_id: ProductId
    recall: Recall
    kind: KindClaim | Unknown
    deposit_word: DepositWord | None = None
    premium_inr: int | Unknown
    one_time_claim: bool = False
    payment_source: PaymentSource | Unknown
    required_for_loan: bool | Unknown
    required_said_softly: bool = False  # "not required, the officer only suggested it"
    provider_choice_offered: bool | Unknown | None
    cover_inr: int | Unknown
    term_months: int | Unknown
    cancel_allowed: bool | Unknown
    cancel_window_days: int | None = None
    money_back: tuple[FeatureClaim, ...] | Unknown
    money_back_period_months: int | None = None
    money_back_mentions_window: bool = False
    consent_given: bool | Unknown
    consent_method: ConsentMethod | Unknown | None

    @model_validator(mode="after")
    def _coherent(self) -> "ProductBelief":
        if (self.deposit_word is not None) != (self.kind == KindClaim.deposit):
            raise ValueError("deposit_word is set exactly when the customer believes it is a deposit")
        if (self.cancel_window_days is not None) != (self.cancel_allowed is True):
            raise ValueError("a cancel window is stated exactly when the customer says they can cancel")
        if (self.consent_method is not None) != (self.consent_given is True):
            raise ValueError("a consent method is given (or unknown) exactly when consent_given is True")
        withdrawable = isinstance(self.money_back, tuple) and (
            FeatureClaim.withdrawable_after_period in self.money_back
        )
        if (self.money_back_period_months is not None) != withdrawable:
            raise ValueError("money_back_period_months goes with the withdrawable_after_period claim")
        if self.money_back_mentions_window and self.money_back != ():
            raise ValueError("money_back_mentions_window is for a customer who makes no claim")
        if self.one_time_claim and not isinstance(self.premium_inr, int):
            raise ValueError("one_time_claim needs a stated premium")
        return self


class YesNoDisposition(StrEnum):
    """How the customer behaves on the yes/no confirmation call (the E1 baseline)."""

    truthful = "truthful"  # answers each closed question by what they believe
    acquiescent = "acquiescent"  # says yes to a bank caller without weighing the question
    coached = "coached"  # was told to say yes to everything


class CustomerState(StrEnum):
    """Whether the customer holds a wrong belief. Sets the E1 denominators."""

    informed = "informed"  # beliefs match the record, apart from rounding or a forgotten amount
    misled = "misled"  # at least one belief contradicts the record
    unaware = "unaware"  # does not know what the product is or how it was paid for
    did_not_agree = "did_not_agree"  # knows the product now and says they never agreed to it


class ScenarioClass(StrEnum):
    """Relation of the scenario to its target rule."""

    violating = "violating"  # gold flags the target rule
    compliant = "compliant"  # gold is clear
    near_miss = "near_miss"  # looks close to a violation of the target rule; gold does not flag it


class Remedy(StrEnum):
    """What the source award ordered."""

    refund = "refund"
    partial_refund = "partial_refund"
    conversion = "conversion"
    other = "other"


class Template(Frozen):
    """The public award a scenario is templated on. Parties and figures in the scenario are invented."""

    case: str  # case number, e.g. BHP-L-021-1617-0529
    ledger: str  # row id in references/claims/findings-B.md
    taken: str  # the fact pattern we took from the award
    changed: str  # what the scenario changes or adds
    remedy: Remedy
    remedy_note: str


class ProductGold(Frozen):
    """Gold for one product. `flags` and `unclear` are rule ids, sorted."""

    product_id: ProductId
    verdict: Verdict
    flags: tuple[RuleId, ...] = ()
    unclear: tuple[RuleId, ...] = ()

    @model_validator(mode="after")
    def _verdict_follows(self) -> "ProductGold":
        if self.flags != tuple(sorted(set(self.flags))) or self.unclear != tuple(sorted(set(self.unclear))):
            raise ValueError("gold rule ids must be sorted and unique")
        if set(self.flags) & set(self.unclear):
            raise ValueError("a rule is flagged or unclear, not both")
        expected = (
            Verdict.flag_for_review
            if self.flags
            else Verdict.unclear_needs_human
            if self.unclear
            else Verdict.clear
        )
        if self.verdict is not expected:
            raise ValueError(f"gold verdict {self.verdict} does not follow from flags and unclear rules")
        return self


class Gold(Frozen):
    """The gold result of a perfect teach-back call. Written by hand, before the rule engine is run."""

    verdict: Verdict
    products: tuple[ProductGold, ...]
    case_flags: tuple[RuleId, ...] = ()
    rationale: str

    @model_validator(mode="after")
    def _case_verdict_follows(self) -> "Gold":
        verdicts = {p.verdict for p in self.products}
        expected = (
            Verdict.flag_for_review
            if self.case_flags or Verdict.flag_for_review in verdicts
            else Verdict.unclear_needs_human
            if Verdict.unclear_needs_human in verdicts
            else Verdict.clear
        )
        if self.verdict is not expected:
            raise ValueError(f"gold case verdict {self.verdict} does not follow from the products")
        return self

    def flag_keys(self) -> frozenset[tuple[ProductId | None, RuleId]]:
        """(product, rule) of every gold flag; product is None for a case-level flag."""
        per_product = {(p.product_id, r) for p in self.products for r in p.flags}
        return frozenset(per_product | {(None, r) for r in self.case_flags})

    def unclear_keys(self) -> frozenset[tuple[ProductId, RuleId]]:
        """(product, rule) of every rule gold says a human could not decide from the call."""
        return frozenset((p.product_id, r) for p in self.products for r in p.unclear)


class RecordFacts(Frozen):
    """The language-neutral part of the lender's record."""

    lender_type: LenderType
    loan_kind: LoanKind
    sanctioned_inr: int
    disbursed_inr: int
    disbursed_on: date
    birth_year: int
    products: tuple[Product, ...]


class BaseCase(Frozen):
    """One hand-written scenario, before it is rendered in a language."""

    id: str  # e.g. U02
    title: str
    target_rule: RuleId
    scenario_class: ScenarioClass
    record: RecordFacts
    told: str  # what the customer was told at the sale, in plain English
    beliefs: tuple[ProductBelief, ...]
    concerns: tuple[SaleConcern, ...] = ()  # voiced by the customer during the teach-back call
    customer_state: CustomerState
    yes_no: YesNoDisposition
    yes_no_basis: str  # why this customer answers the closed questions this way
    gold: Gold
    template: Template | None = None
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _one_belief_per_product(self) -> "BaseCase":
        if [b.product_id for b in self.beliefs] != [p.id for p in self.record.products]:
            raise ValueError("beliefs must cover the record's products, in order")
        if [g.product_id for g in self.gold.products] != [p.id for p in self.record.products]:
            raise ValueError("gold must cover the record's products, in order")
        for belief, product in zip(self.beliefs, self.record.products, strict=True):
            asked = product.required_for_loan or belief.required_for_loan is True
            if (belief.provider_choice_offered is not None) != asked:
                raise ValueError(
                    f"{self.id}: the provider-choice question is asked exactly when the product "
                    "was required per the record or per the customer"
                )
        violating = self.scenario_class is ScenarioClass.violating
        flagged = {*self.gold.case_flags, *(r for p in self.gold.products for r in p.flags)}
        if violating != (self.target_rule in flagged):
            raise ValueError(f"{self.id}: class {self.scenario_class} disagrees with the gold target flag")
        if self.scenario_class is ScenarioClass.compliant and self.gold.verdict is not Verdict.clear:
            raise ValueError(f"{self.id}: a compliant scenario must have a clear gold verdict")
        return self


class Scenario(Frozen):
    """One base case in one call language: the row of `gold.jsonl`."""

    id: str  # e.g. U02-hi
    base: str  # id of the base case, e.g. U02
    language: Language
    text_review: str  # REVIEW_LABEL of the language
    title: str
    target_rule: RuleId
    scenario_class: ScenarioClass
    tags: tuple[str, ...]
    record: LoanRecord
    told: str
    beliefs: tuple[ProductBelief, ...]
    concerns: tuple[SaleConcern, ...]
    customer_state: CustomerState
    yes_no: YesNoDisposition
    yes_no_basis: str
    gold: Gold
    template: Template | None

    def belief(self, product_id: ProductId) -> ProductBelief:
        """The customer's belief about one product on the record."""
        return next(b for b in self.beliefs if b.product_id == product_id)


class YesNoAnswer(StrEnum):
    """The customer's reply to one closed question."""

    yes = "yes"
    no = "no"
    unsure = "unsure"


class YesNoQuestion(StrEnum):
    """The closed questions of the confirmation call, in order."""

    bought = "bought"
    premium = "premium"
    payment = "payment"
    consent = "consent"
    explained = "explained"


class YesNoOutcome(StrEnum):
    """What a confirmation script concludes: confirmed only when every answer is yes."""

    confirmed = "confirmed"
    not_confirmed = "not_confirmed"


class YesNoReply(Frozen):
    """One closed question and the scripted answer to it."""

    question: YesNoQuestion
    answer: YesNoAnswer
    turn_id: int


class TeachBackCall(Frozen):
    """The scripted Samajh call and the extraction a perfect extractor would return for it."""

    transcript: Transcript
    extraction: RawExtraction


class YesNoCall(Frozen):
    """The scripted confirmation call on the same facts."""

    transcript: Transcript
    replies: tuple[YesNoReply, ...]
    outcome: YesNoOutcome

    @model_validator(mode="after")
    def _outcome_follows(self) -> "YesNoCall":
        all_yes = all(r.answer is YesNoAnswer.yes for r in self.replies)
        if (self.outcome is YesNoOutcome.confirmed) != all_yes:
            raise ValueError("a confirmation call is confirmed exactly when every answer is yes")
        return self


class CallScripts(Frozen):
    """Both scripted calls for one scenario: the row of `calls.jsonl`."""

    id: str
    language: Language
    text_review: str
    teach_back: TeachBackCall
    yes_no: YesNoCall
