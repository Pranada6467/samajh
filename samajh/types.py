"""Shared types for Samajh. Pure data: no network, no LLM, no audio.

Data flow:
    Transcript --LLM--> RawExtraction --samajh.rules.to_beliefs--> Beliefs
    (LoanRecord, Beliefs) --samajh.rules.evaluate--> CaseResult

The LLM only fills RawExtraction: enums and verbatim text. Amounts and durations
stay as the customer's words until deterministic code parses them into Beliefs.
"""

from datetime import date
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Generic, Literal, NewType, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)
from typing_extensions import TypeAliasType

T = TypeVar("T")

ProductId = NewType("ProductId", str)  # id of a product on the loan record
TurnId = NewType("TurnId", int)  # id of one turn in a transcript
Count = Annotated[
    int, Field(strict=True, gt=0)
]  # rupees, months or days on the record; never a bool or a string


class Frozen(BaseModel):
    """Base for every model: immutable, unknown fields rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --- enums -----------------------------------------------------------------


class Language(StrEnum):
    """Call language. Tamil and Kannada content is not human-reviewed."""

    hi = "hi"
    hi_en = "hi-en"
    ta = "ta"
    kn = "kn"


class ProductKind(StrEnum):
    """What the product is on the lender's record. One family in v1."""

    credit_life = "credit_life"


class KindClaim(StrEnum):
    """What the customer says the product is."""

    insurance = "insurance"
    deposit = "deposit"
    investment = "investment"
    fee = "fee"
    other = "other"


class PaymentSource(StrEnum):
    """How the customer says the product was paid for."""

    from_loan = "from_loan"
    separately = "separately"


class FeatureClaim(StrEnum):
    """A claim about a product. `Product.features` lists the claims that are true of it."""

    is_deposit = "is_deposit"
    refundable_anytime = "refundable_anytime"
    guaranteed_return = "guaranteed_return"
    one_time_payment = "one_time_payment"
    withdrawable_after_period = "withdrawable_after_period"


class SaleConcern(StrEnum):
    """Something the customer says about how the sale or the confirmation was handled. Any one is a flag."""

    coached_answers = "coached_answers"
    learned_after_sale = "learned_after_sale"
    signed_without_explanation = "signed_without_explanation"


class LenderType(StrEnum):
    """Which RBI direction the lender falls under. Selects the paragraph numbers in `samajh.rules.CLAUSES`."""

    bank = "bank"
    nbfc = "nbfc"


class LoanKind(StrEnum):
    """Type of the loan the products were sold with."""

    personal = "personal"
    gold = "gold"


class ConsentMethod(StrEnum):
    """How consent was given: on the lender's record, or as the customer describes it."""

    signed_form = "signed_form"
    otp = "otp"
    digital_click = "digital_click"
    recorded_call = "recorded_call"
    verbal = "verbal"  # by word of mouth only


class Speaker(StrEnum):
    """Who spoke a turn."""

    bot = "bot"
    customer = "customer"


class CallStep(StrEnum):
    """Step of the call flow, in order (DESIGN.md section 5)."""

    right_party_check = "right_party_check"
    disclosure = "disclosure"
    second_check = "second_check"
    context = "context"
    open_recall = "open_recall"
    teach_back = "teach_back"
    consent_check = "consent_check"
    read_back = "read_back"
    close = "close"


class Question(StrEnum):
    """The per-product field a bot turn asks about. A read-back of the premium asks `premium`."""

    kind = "kind"
    premium = "premium"
    payment_source = "payment_source"
    required_for_loan = "required_for_loan"
    provider_choice = "provider_choice"
    cover = "cover"
    term = "term"
    cancel_window = "cancel_window"
    features = "features"
    consent = "consent"


class GapReason(StrEnum):
    """Why a rule could not decide. Each one sends the case to a human."""

    not_asked = "not_asked"
    no_usable_answer = "no_usable_answer"
    value_not_parsed = "value_not_parsed"
    readback_rejected = "readback_rejected"
    readback_mismatch = "readback_mismatch"
    quote_not_grounded = "quote_not_grounded"


class Severity(StrEnum):
    """Review priority of a flag."""

    high = "high"
    medium = "medium"
    low = "low"


class Verdict(StrEnum):
    """Outcome for a product or a case. Never a finding of wrongdoing."""

    clear = "clear"
    flag_for_review = "flag_for_review"
    unclear_needs_human = "unclear_needs_human"


class RuleId(StrEnum):
    """Neutral rule names. Regulatory paragraph numbers live in `samajh.rules.CLAUSES` only."""

    kind = "kind"
    premium = "premium"
    cover = "cover"
    term = "term"
    cancel_window = "cancel_window"
    recall = "recall"
    recall_unmatched = "recall_unmatched"
    consent = "consent"
    loan_funded = "loan_funded"
    bundling = "bundling"
    belief_mismatch = "belief_mismatch"
    sale_conduct = "sale_conduct"
    evidence = "evidence"


# A flag under one of these rules also gets an evidence pack for the lender's reviewer.
EVIDENCE_PACK_RULES: frozenset[RuleId] = frozenset(
    {RuleId.kind, RuleId.premium, RuleId.consent, RuleId.bundling, RuleId.loan_funded}
)


# --- the lender's record ---------------------------------------------------


class Consent(Frozen):
    """The lender's record that the customer agreed to one product."""

    method: ConsentMethod
    at: date


class Product(Frozen):
    """One product sold with the loan, as the lender recorded it.

    `risk_mitigant`: the lender required it to cover the risk on the loan (our reading for
    credit-life cover). `provider_choice_offered`: the customer was told they could buy it from
    any provider. `cancel_window_days` is None when the record shows no cancellation window.
    """

    id: ProductId
    kind: ProductKind
    provider: str
    premium_inr: Count
    cover_inr: Count
    term_months: Count
    paid_from_loan: StrictBool
    required_for_loan: StrictBool
    risk_mitigant: StrictBool
    provider_choice_offered: StrictBool
    cancel_window_days: Count | None
    features: frozenset[FeatureClaim]  # required: an omitted claim reads as "not true of this product"
    consent: Consent | None


class Borrower(Frozen):
    """The customer. Synthetic and obviously fake."""

    name: str
    dob: date
    language: Language


class LoanRecord(Frozen):
    """The loan and every product sold with it. Synthetic."""

    loan_id: str
    lender_type: LenderType
    borrower: Borrower
    loan_kind: LoanKind
    sanctioned_inr: Count
    disbursed_inr: Count
    disbursed_on: date
    products: tuple[Product, ...]

    @model_validator(mode="after")
    def _unique_product_ids(self) -> "LoanRecord":
        ids = [p.id for p in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate product id on loan record")
        return self


# --- the call ----------------------------------------------------------------


class Turn(Frozen):
    """One utterance in the call.

    Every bot question about a product must carry `asks` and `product_id`: an answer counts only
    when it cites a customer turn that replies to the bot turn tagged with its question. The
    consent question is open and names no product, so it carries `asks` alone and counts for
    every product on the record.
    """

    id: TurnId
    speaker: Speaker
    step: CallStep
    text: str
    asks: Question | None = None
    product_id: ProductId | None = None
    start_s: float | None = None
    end_s: float | None = None


class Transcript(Frozen):
    """A whole call in order."""

    call_id: str
    loan_id: str
    language: Language
    turns: tuple[Turn, ...]

    @model_validator(mode="after")
    def _increasing_turn_ids(self) -> "Transcript":
        ids = [t.id for t in self.turns]
        if any(b <= a for a, b in pairwise(ids)):
            raise ValueError("turn ids must be strictly increasing")
        return self


# --- answers: one of four states, each with its evidence ---------------------


class Evidence(Frozen):
    """The customer's verbatim words and the turn they came from."""

    quote: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    turn_id: Annotated[TurnId, Field(strict=True)]


class NotAsked(Frozen):
    """The call never put this question to the customer."""

    status: Literal["not_asked"] = "not_asked"


class Unclear(Frozen):
    """Asked, but no usable answer. `reason` says why; it is never `not_asked`."""

    status: Literal["unclear"] = "unclear"
    reason: GapReason = GapReason.no_usable_answer
    evidence: Evidence | None = None

    @model_validator(mode="after")
    def _reason_is_not_not_asked(self) -> "Unclear":
        if self.reason is GapReason.not_asked:
            raise ValueError("use NotAsked for a question that was never asked")
        return self


class DontKnow(Frozen):
    """The customer said they do not know."""

    status: Literal["dont_know"] = "dont_know"
    evidence: Evidence


class Stated(Frozen, Generic[T]):
    """The customer gave an answer."""

    status: Literal["stated"] = "stated"
    value: T
    evidence: Evidence


Answer = TypeAliasType(
    "Answer",
    Annotated[NotAsked | Unclear | DontKnow | Stated[T], Field(discriminator="status")],
    type_params=(T,),
)
"""`Answer[T]`: exactly one of NotAsked, Unclear, DontKnow, Stated[T]."""


class ClaimEvidence(Frozen):
    """A feature claim the customer made without being asked, with their words."""

    claim: FeatureClaim
    evidence: Evidence


class ConcernEvidence(Frozen):
    """A concern about the sale that the customer voiced, with their words."""

    concern: SaleConcern
    evidence: Evidence


class _ProductAnswers(Frozen):
    """Per-product answers that need no parsing. Shared by the raw and normalised layers.

    `premium_readback` is the customer's reply to the last read-back of the premium (True = "yes, right").
    `provider_choice_offered`: "were you told you could buy this cover from another company?"
    `cancel_allowed`: "were you told whether you can cancel this cover?" The "by when" half of
    that answer is `cancel_window` (raw words) and `cancel_window_days` (normalised).
    `consent_given` and `consent_method` come from the open consent question: does the customer's
    own account of what they agreed to buy include this product, and how do they say they agreed.
    `feature_probe` is the reply to the open question about getting the money back: the claims made, or ().
    """

    product_id: ProductId
    kind: Answer[KindClaim] = NotAsked()
    premium_readback: Answer[StrictBool] = NotAsked()
    payment_source: Answer[PaymentSource] = NotAsked()
    required_for_loan: Answer[StrictBool] = NotAsked()
    provider_choice_offered: Answer[StrictBool] = NotAsked()
    cancel_allowed: Answer[StrictBool] = NotAsked()
    consent_given: Answer[StrictBool] = NotAsked()
    consent_method: Answer[ConsentMethod] = NotAsked()
    feature_probe: Answer[tuple[FeatureClaim, ...]] = NotAsked()
    volunteered_claims: tuple[ClaimEvidence, ...] = ()


class _OpenRecall(Frozen):
    """Open recall, shared by both layers. `answer` is the customer's whole reply."""

    asked: bool
    answer: Evidence | None = None
    items: tuple = ()

    @model_validator(mode="after")
    def _no_answer_without_a_question(self) -> "_OpenRecall":
        if not self.asked and (self.items or self.answer):
            raise ValueError("open recall has an answer but asked is false")
        return self


# --- layer 1: what the LLM emits ---------------------------------------------


class RawRecallItem(Frozen):
    """One thing the customer named in open recall. `product_id` is None when nothing on record matches."""

    evidence: Evidence
    kind: KindClaim | None = None
    amount_text: str | None = None
    product_id: ProductId | None = None


class RawOpenRecall(_OpenRecall):
    """The open-recall step as extracted. `asked=True` with no items: the customer named nothing."""

    items: tuple[RawRecallItem, ...] = ()


class RawProductAnswers(_ProductAnswers):
    """Teach-back answers for one product. Amounts and durations are the customer's words, verbatim."""

    premium: Answer[str] = NotAsked()
    cover: Answer[str] = NotAsked()
    term: Answer[str] = NotAsked()
    cancel_window: Answer[str] = NotAsked()


class RawExtraction(Frozen):
    """Everything the LLM extracts from one call. Enums and verbatim text only."""

    call_id: str
    recall: RawOpenRecall
    products: tuple[RawProductAnswers, ...]
    sale_concerns: tuple[ConcernEvidence, ...] = ()


# --- layer 2: what the rules consume -----------------------------------------


class RecallItem(Frozen):
    """A recall item after amount parsing. `amount_inr` is None when no amount was said or parsed."""

    evidence: Evidence
    kind: KindClaim | None = None
    amount_inr: int | None = None
    product_id: ProductId | None = None


class OpenRecall(_OpenRecall):
    """The open-recall step, normalised and grounded in the transcript."""

    items: tuple[RecallItem, ...] = ()


class ProductBeliefs(_ProductAnswers):
    """What the customer believes about one product, in comparable units."""

    premium_inr: Answer[StrictInt] = NotAsked()
    cover_inr: Answer[StrictInt] = NotAsked()
    term_months: Answer[StrictInt] = NotAsked()
    cancel_window_days: Answer[StrictInt] = NotAsked()
    ungrounded: tuple[Evidence, ...] = ()


class Beliefs(Frozen):
    """Normalised beliefs for one call: one ProductBeliefs per product on record."""

    call_id: str
    loan_id: str
    language: Language
    recall: OpenRecall
    products: tuple[ProductBeliefs, ...]
    sale_concerns: tuple[ConcernEvidence, ...] = ()
    ungrounded: tuple[Evidence, ...] = ()

    def for_product(self, product_id: ProductId) -> ProductBeliefs:
        """Beliefs for one product. A product the call never covered reads as all NotAsked."""
        for p in self.products:
            if p.product_id == product_id:
                return p
        return ProductBeliefs(product_id=product_id)


# --- results -----------------------------------------------------------------


class Passed(Frozen):
    """A rule checked positive evidence and found nothing to review."""

    outcome: Literal["passed"] = "passed"
    rule_id: RuleId
    product_id: ProductId | None


class Flag(Frozen):
    """A mismatch for human review. `product_id` is None for a case-level flag.

    `clause` is the paragraph the flag may engage for this lender type. It is never a finding.
    """

    outcome: Literal["flag"] = "flag"
    rule_id: RuleId
    clause: str
    product_id: ProductId | None
    severity: Severity
    expected: str
    heard: str
    quote: str | None = None
    turn_id: TurnId | None = None


class Gap(Frozen):
    """A rule could not decide. Blocks `clear`."""

    outcome: Literal["gap"] = "gap"
    rule_id: RuleId
    clause: str
    product_id: ProductId | None
    reason: GapReason
    quote: str | None = None
    turn_id: TurnId | None = None


Outcome = Annotated[Passed | Flag | Gap, Field(discriminator="outcome")]
"""What one rule returns for one product: it must commit to Passed, Flag or Gap."""


def _verdict(flags: tuple[Flag, ...], gaps: tuple[Gap, ...]) -> Verdict:
    """Any flag -> flag_for_review; else any gap -> unclear_needs_human; else clear."""
    if flags:
        return Verdict.flag_for_review
    return Verdict.unclear_needs_human if gaps else Verdict.clear


class EvidencePack(Frozen):
    """What the lender's reviewer needs to look at one flagged product. Evidence, not a finding.

    Holds the record, and the flags under `EVIDENCE_PACK_RULES`: each carries the customer's
    words with the turn id and the paragraph the flag may engage.
    """

    loan_id: str
    call_id: str
    lender_type: LenderType
    product: Product
    flags: tuple[Flag, ...]

    @model_validator(mode="after")
    def _only_pack_flags_for_this_product(self) -> "EvidencePack":
        if not self.flags:
            raise ValueError("an evidence pack needs at least one flag")
        if any(f.rule_id not in EVIDENCE_PACK_RULES or f.product_id != self.product.id for f in self.flags):
            raise ValueError("an evidence pack holds only this product's flags under EVIDENCE_PACK_RULES")
        return self

    def quotes(self) -> tuple[Evidence, ...]:
        """The customer's words behind the flags, each once, in flag order."""
        found = (
            Evidence(quote=f.quote, turn_id=f.turn_id)
            for f in self.flags
            if f.quote is not None and f.turn_id is not None
        )
        return tuple(dict.fromkeys(found))

    def clauses(self) -> tuple[str, ...]:
        """The paragraphs the flags may engage, each once, in flag order."""
        return tuple(dict.fromkeys(f.clause for f in self.flags))


class ProductResult(Frozen):
    """Verdict and evidence for one product. The verdict must follow from the flags and gaps.

    `evidence_pack` is present exactly when a flag falls under `EVIDENCE_PACK_RULES`.
    """

    product_id: ProductId
    verdict: Verdict
    flags: tuple[Flag, ...] = ()
    gaps: tuple[Gap, ...] = ()
    passed: tuple[RuleId, ...] = ()
    evidence_pack: EvidencePack | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "ProductResult":
        if any(o.product_id != self.product_id for o in (*self.flags, *self.gaps)):
            raise ValueError("a flag or gap belongs to another product")
        if self.verdict is not _verdict(self.flags, self.gaps):
            raise ValueError("product verdict does not follow from its flags and gaps")
        pack_flags = tuple(f for f in self.flags if f.rule_id in EVIDENCE_PACK_RULES)
        if (self.evidence_pack.flags if self.evidence_pack else ()) != pack_flags:
            raise ValueError("the evidence pack does not match the product's flags")
        return self


class CaseResult(Frozen):
    """Result of one call, for the case UI and the half-yearly report.

    The verdict is the worst of the products and the case-level flags and gaps.
    """

    loan_id: str
    call_id: str
    language: Language
    verdict: Verdict
    products: tuple[ProductResult, ...]
    case_flags: tuple[Flag, ...] = ()
    case_gaps: tuple[Gap, ...] = ()
    unmatched_recall: tuple[RecallItem, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> "CaseResult":
        if any(o.product_id is not None for o in (*self.case_flags, *self.case_gaps)):
            raise ValueError("a case-level flag or gap names a product")
        if self.verdict is not _verdict(self.all_flags(), self.all_gaps()):
            raise ValueError("case verdict does not follow from the flags and gaps")
        return self

    def all_flags(self) -> tuple[Flag, ...]:
        """Every flag in the case: per product, then case-level."""
        return (*(f for p in self.products for f in p.flags), *self.case_flags)

    def all_gaps(self) -> tuple[Gap, ...]:
        """Every gap in the case: per product, then case-level."""
        return (*(g for p in self.products for g in p.gaps), *self.case_gaps)

    def evidence_packs(self) -> tuple[EvidencePack, ...]:
        """One pack per product that has one, in record order."""
        return tuple(p.evidence_pack for p in self.products if p.evidence_pack is not None)

    def flag_keys(self) -> frozenset[tuple[ProductId | None, RuleId, Severity]]:
        """(product, rule, severity) of every flag: the stable part to compare with gold."""
        return frozenset((f.product_id, f.rule_id, f.severity) for f in self.all_flags())

    def gap_keys(self) -> frozenset[tuple[ProductId | None, RuleId, GapReason]]:
        """(product, rule, reason) of every gap: the stable part to compare with gold."""
        return frozenset((g.product_id, g.rule_id, g.reason) for g in self.all_gaps())
