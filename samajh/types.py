"""Shared types for Samajh. Pure data: no network, no LLM, no audio.

Data flow:
    Transcript --LLM--> RawExtraction --samajh.rules.to_beliefs--> Beliefs
    (LoanRecord, Beliefs) --samajh.rules.evaluate--> CaseResult

The LLM only fills RawExtraction: enums and verbatim text. Amounts and durations
stay as the customer's words until deterministic code parses them into Beliefs.
"""

from collections.abc import Iterable
from datetime import date
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Any, ClassVar, Generic, Literal, NewType, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_serializer,
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
    """Base for every model: immutable, unknown fields rejected.

    `added_later` names fields added after scenario set version 3 was frozen. A dump leaves such
    a field out while it holds its default, so a file written before the field existed keeps its
    bytes and its hash, and still loads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    added_later: ClassVar[frozenset[str]] = frozenset()

    @model_serializer(mode="wrap")
    def _omit_later_defaults(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = handler(self)
        for name in self.added_later:
            if name in data and getattr(self, name) == type(self).model_fields[name].default:
                del data[name]
        return data


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


class PaymentFrequency(StrEnum):
    """How often the customer says the product is paid for."""

    one_time = "one_time"
    recurring = "recurring"


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
    payment_frequency = "payment_frequency"


class GapReason(StrEnum):
    """Why a rule could not decide. Each one sends the case to a human."""

    not_asked = "not_asked"
    no_usable_answer = "no_usable_answer"
    value_not_parsed = "value_not_parsed"
    readback_rejected = "readback_rejected"
    readback_mismatch = "readback_mismatch"
    quote_not_grounded = "quote_not_grounded"
    extraction_failed = "extraction_failed"  # the model gave no valid output for this reply
    not_comparable = "not_comparable"  # a usable answer the record gives nothing to compare with


class Severity(StrEnum):
    """Review priority of a flag."""

    high = "high"
    medium = "medium"
    low = "low"


class Verdict(StrEnum):
    """The strict outcome: any flag is `flag_for_review`. The frozen gold is written in it.

    Triage reads `Tier`. Never a finding of wrongdoing.
    """

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


class Tier(StrEnum):
    """Triage of a product or a case, derived from its flags and gaps by `tier_of`. Never a finding.

    `refer`: a human must look. `incomplete`: the call did not yield enough to decide.
    `understanding_gap`: reported in aggregate, not queued. `clear`: every rule passed.
    """

    refer = "refer"
    incomplete = "incomplete"
    understanding_gap = "understanding_gap"
    clear = "clear"


class FlagReason(StrEnum):
    """Each distinct reason a rule raises a flag. Keys of `samajh.rules.checks.SEVERITY` and `FLAG_TIER`."""

    kind_differs = "kind_differs"
    kind_dont_know = "kind_dont_know"
    premium_differs_confirmed = "premium_differs_confirmed"  # customer confirmed the read-back
    premium_differs = "premium_differs"  # a differing amount that no read-back confirmed
    premium_dont_know = "premium_dont_know"
    premium_approximate = "premium_approximate"  # within the approximate tolerance, not the exact one
    cover_differs = "cover_differs"  # hedged or approximate, and not near the record
    cover_differs_confirmed = "cover_differs_confirmed"  # a plain figure the customer confirmed at a read-back
    cover_differs_unconfirmed = "cover_differs_unconfirmed"  # a plain figure no read-back confirmed
    cover_dont_know = "cover_dont_know"
    term_differs = "term_differs"
    term_dont_know = "term_dont_know"
    cancel_unaware = "cancel_unaware"
    cancel_dont_know = "cancel_dont_know"
    cancel_window_differs = "cancel_window_differs"
    cancel_window_dont_know = "cancel_window_dont_know"
    cancel_not_on_record = "cancel_not_on_record"
    recall_not_named = "recall_not_named"
    recall_denied = "recall_denied"  # says they took nothing with the loan
    recall_off_record = "recall_off_record"
    consent_no_record = "consent_no_record"
    consent_not_recognised = "consent_not_recognised"
    consent_method_differs = "consent_method_differs"
    consent_dont_know = "consent_dont_know"
    funded_no_consent = "funded_no_consent"
    funded_says_separately = "funded_says_separately"
    funded_dont_know = "funded_dont_know"
    unfunded_says_deducted = "unfunded_says_deducted"
    bundled_not_mitigant = "bundled_not_mitigant"
    bundled_described_as_deposit = "bundled_described_as_deposit"
    bundled_no_choice_on_record = "bundled_no_choice_on_record"
    bundled_no_choice_told = "bundled_no_choice_told"
    feature_contradicted = "feature_contradicted"
    feature_dont_know = "feature_dont_know"
    frequency_recurring_on_single = "frequency_recurring_on_single"
    frequency_dont_know = "frequency_dont_know"
    sale_concern = "sale_concern"
    answers_conflict = "answers_conflict"  # one question, asked more than once, differing answers


# A gap under one of these rules leaves a question a reviewer would act on undecided: `incomplete`.
# A gap under any other rule (cover, term, cancel window, recall) is an `understanding_gap`.
REFER_RULES: frozenset[RuleId] = frozenset(
    {
        RuleId.kind,
        RuleId.premium,
        RuleId.consent,
        RuleId.loan_funded,
        RuleId.bundling,
        RuleId.belief_mismatch,
        RuleId.recall_unmatched,
        RuleId.sale_conduct,
        RuleId.evidence,
    }
)

_R = FlagReason
# The tier of every flag, by its reason. Tune here and nowhere else. `answers_conflict` is not
# listed: its tier follows the rule it is raised under (`flag_tier`).
FLAG_TIER: dict[FlagReason, Tier] = {
    **dict.fromkeys(
        (
            _R.kind_differs,
            _R.kind_dont_know,
            _R.premium_differs_confirmed,
            _R.cover_differs_confirmed,  # coordinator decision 2026-11-10
            _R.recall_denied,
            _R.recall_off_record,
            _R.consent_no_record,
            _R.consent_not_recognised,
            _R.consent_method_differs,
            _R.consent_dont_know,
            _R.funded_no_consent,
            _R.funded_says_separately,
            _R.funded_dont_know,
            _R.unfunded_says_deducted,
            _R.bundled_not_mitigant,
            _R.bundled_described_as_deposit,
            _R.bundled_no_choice_on_record,
            _R.bundled_no_choice_told,
            _R.feature_contradicted,
            _R.sale_concern,
        ),
        Tier.refer,
    ),
    # The amount differs but the customer never confirmed it: it may be a mis-hearing.
    _R.premium_differs: Tier.incomplete,
    _R.cover_differs_unconfirmed: Tier.incomplete,
    **dict.fromkeys(
        (
            _R.premium_dont_know,
            _R.premium_approximate,
            _R.cover_differs,
            _R.cover_dont_know,
            _R.term_differs,
            _R.term_dont_know,
            _R.cancel_unaware,
            _R.cancel_dont_know,
            _R.cancel_window_differs,
            _R.cancel_window_dont_know,
            _R.cancel_not_on_record,
            _R.recall_not_named,
            _R.feature_dont_know,
            _R.frequency_recurring_on_single,
            _R.frequency_dont_know,
        ),
        Tier.understanding_gap,
    ),
}
if set(FLAG_TIER) != set(FlagReason) - {FlagReason.answers_conflict}:
    raise RuntimeError("FLAG_TIER must give a tier to every FlagReason except answers_conflict")


class Basis(StrEnum):
    """What a flag rests on: the customer's words, or the lender's record and nothing the customer said.

    A tag beside the tier, never a tier. A flag on the record alone needs no call to raise.
    """

    customer_statement = "customer_statement"
    record_only = "record_only"


# What every flag rests on, by its reason. `Flag.rests_on` overrides it on one path only (bundling
# raised on the customer's word that the product was required); `Flag.basis` reads both.
# A new FlagReason must be placed here by hand: the check below fails until it is.
FLAG_BASIS: dict[FlagReason, Basis] = {
    **dict.fromkeys(
        (
            _R.consent_no_record,
            _R.funded_no_consent,
            _R.bundled_not_mitigant,
            _R.bundled_no_choice_on_record,
        ),
        Basis.record_only,
    ),
    **dict.fromkeys(
        (
            _R.kind_differs,
            _R.kind_dont_know,
            _R.premium_differs_confirmed,
            _R.premium_differs,
            _R.premium_dont_know,
            _R.premium_approximate,
            _R.cover_differs,
            _R.cover_differs_confirmed,
            _R.cover_differs_unconfirmed,
            _R.cover_dont_know,
            _R.term_differs,
            _R.term_dont_know,
            _R.cancel_unaware,
            _R.cancel_dont_know,
            _R.cancel_window_differs,
            _R.cancel_window_dont_know,
            _R.cancel_not_on_record,
            _R.recall_not_named,
            _R.recall_denied,
            _R.recall_off_record,
            _R.consent_not_recognised,
            _R.consent_method_differs,
            _R.consent_dont_know,
            _R.funded_says_separately,
            _R.funded_dont_know,
            _R.unfunded_says_deducted,
            _R.bundled_described_as_deposit,
            _R.bundled_no_choice_told,
            _R.feature_contradicted,
            _R.feature_dont_know,
            _R.frequency_recurring_on_single,
            _R.frequency_dont_know,
            _R.sale_concern,
            _R.answers_conflict,
        ),
        Basis.customer_statement,
    ),
}
if set(FLAG_BASIS) != set(FlagReason):
    raise RuntimeError("FLAG_BASIS must give a basis to every FlagReason")


def flag_tier(rule_id: RuleId, reason: FlagReason) -> Tier:
    """The tier of one flag. Conflicting answers follow the rule they were raised under."""
    if reason is FlagReason.answers_conflict:
        return Tier.refer if rule_id in REFER_RULES else Tier.understanding_gap
    return FLAG_TIER[reason]


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
    tenure_months: Count | None = None  # lets "as long as the loan runs" be compared with a term
    added_later: ClassVar[frozenset[str]] = frozenset({"tenure_months"})

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
    """The customer gave an answer.

    `hedged`: said with a word of doubt ("शायद", "I think"). `approximate`: an amount said as
    "about X" or as a range; for a range `low` is its lower end and `value` its upper end.
    These are markers. No rule lets one turn a wrong answer into a pass.
    `also`: the customer's other replies to the same question that this answer stands over, in
    call order: an earlier "I don't know", or a restatement consistent with it.
    """

    status: Literal["stated"] = "stated"
    value: T
    evidence: Evidence
    hedged: bool = False
    approximate: bool = False
    low: StrictInt | None = None
    also: tuple[Evidence, ...] = ()
    added_later: ClassVar[frozenset[str]] = frozenset({"hedged", "approximate", "low", "also"})

    @model_validator(mode="after")
    def _a_range_is_an_approximate_amount(self) -> "Stated[T]":
        is_amount = isinstance(self.value, int) and not isinstance(self.value, bool)
        if self.approximate and not is_amount:
            raise ValueError("only an amount can be approximate")
        if self.low is not None and not (self.approximate and self.low < self.value):
            raise ValueError("low is the lower end of an approximate range and must be under value")
        return self


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


class AnswerConflict(Frozen):
    """One question asked more than once, with usable answers that differ. Each is a whole reply, in call order."""

    question: Question
    answers: Annotated[tuple[Evidence, ...], Field(min_length=2)]


class _ProductAnswers(Frozen):
    """Per-product answers that need no parsing. Shared by the raw and normalised layers.

    `premium_readback` is the customer's reply to the last read-back of the premium (True = "yes, right").
    `provider_choice_offered`: "were you told you could buy this cover from another company?"
    `cancel_allowed`: "were you told whether you can cancel this cover?" The "by when" half of
    that answer is `cancel_window` (raw words) and `cancel_window_days` (normalised).
    `consent_given` and `consent_method` come from the open consent question: does the customer's
    own account of what they agreed to buy include this product, and how do they say they agreed.
    `feature_probe` is the reply to the open question about getting the money back: the claims made, or ().
    `payment_frequency`: "do you pay for it once, or again and again?" Checked only when asked.
    `cover_readback` is the reply to the last read-back of the cover figure, like `premium_readback`:
    a bot turn with step `read_back` and `asks=cover`.
    Each field holds the last stated answer (else the last "I don't know"); `conflicts` holds a
    question whose stated answers are incompatible. A failed model call on any asking of a
    question makes its fields `Unclear(extraction_failed)`.
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
    payment_frequency: Answer[PaymentFrequency] = NotAsked()
    cover_readback: Answer[StrictBool] = NotAsked()
    volunteered_claims: tuple[ClaimEvidence, ...] = ()
    conflicts: tuple[AnswerConflict, ...] = ()
    added_later: ClassVar[frozenset[str]] = frozenset({"payment_frequency", "cover_readback", "conflicts"})


class _OpenRecall(Frozen):
    """Open recall, shared by both layers. `answer` is the customer's whole reply.

    `denial`: the customer's words when they say they took nothing with the loan.
    """

    asked: bool
    answer: Evidence | None = None
    items: tuple = ()
    denial: Evidence | None = None
    added_later: ClassVar[frozenset[str]] = frozenset({"denial"})

    @model_validator(mode="after")
    def _no_answer_without_a_question(self) -> "_OpenRecall":
        if not self.asked and (self.items or self.answer or self.denial):
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
    unscreened: tuple[Evidence, ...] = ()  # replies whose screening call failed
    added_later: ClassVar[frozenset[str]] = frozenset({"unscreened"})


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
    unscreened: tuple[Evidence, ...] = ()  # replies nobody screened for claims and concerns

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


# How `checks.bundling` starts `heard` when the record does not mark the product as required and only
# the customer said it was. One home for the text: the backfill in `Flag` matches on it.
TOLD_REQUIRED_HEARD = "customer says the product was required for the loan"
_TOLD_REQUIRED_REASONS = (FlagReason.bundled_not_mitigant, FlagReason.bundled_no_choice_on_record)


class Flag(Frozen):
    """A mismatch for human review. `product_id` is None for a case-level flag.

    `clause` is the paragraph the flag may engage for this lender type. It is never a finding.
    `claim` is the belief on a `feature_contradicted` flag. `also` holds further quotes: a
    conflict flag lists every differing answer after `quote`.
    """

    outcome: Literal["flag"] = "flag"
    rule_id: RuleId
    reason: FlagReason
    clause: str
    product_id: ProductId | None
    severity: Severity
    expected: str
    heard: str
    quote: str | None = None
    turn_id: TurnId | None = None
    claim: FeatureClaim | None = None
    also: tuple[Evidence, ...] = ()
    # Set only where the reason's `FLAG_BASIS` class is `record_only` but this flag rests on the
    # customer's words (bundling raised because the customer said the product was required).
    rests_on: Basis | None = None

    added_later: ClassVar[frozenset[str]] = frozenset({"rests_on"})

    @model_validator(mode="before")
    @classmethod
    def _backfill_rests_on(cls, data: Any) -> Any:
        """Backfill for results stored before `rests_on` existed: a bundling flag raised on the
        customer's word that the product was required (its `heard` starts with
        `TOLD_REQUIRED_HEARD`) rests on what the customer said. Only a dict with no `rests_on` key."""
        if (
            isinstance(data, dict)
            and "rests_on" not in data
            and data.get("reason") in _TOLD_REQUIRED_REASONS
            and isinstance(data.get("heard"), str)
            and data["heard"].startswith(TOLD_REQUIRED_HEARD)
        ):
            return {**data, "rests_on": Basis.customer_statement}
        return data

    @model_validator(mode="after")
    def _override_only_to_statement(self) -> "Flag":
        if self.rests_on is not None and not (
            self.rests_on is Basis.customer_statement and FLAG_BASIS[self.reason] is Basis.record_only
        ):
            raise ValueError("rests_on may only mark a record_only reason as resting on a customer statement")
        return self

    @property
    def tier(self) -> Tier:
        return flag_tier(self.rule_id, self.reason)

    @property
    def basis(self) -> Basis:
        """What this flag rests on: the override when set, else the reason's class."""
        return self.rests_on or FLAG_BASIS[self.reason]


def referral_basis(flags: Iterable[Flag]) -> Basis | None:
    """What a referral rests on, from the refer-tier flags only.

    None when no flag is refer-tier. `customer_statement` when at least one refer-tier flag rests
    on the customer's words; else `record_only`.
    """
    bases = {f.basis for f in flags if f.tier is Tier.refer}
    if not bases:
        return None
    return Basis.customer_statement if Basis.customer_statement in bases else Basis.record_only


class Gap(Frozen):
    """A rule could not decide. Blocks `clear`."""

    outcome: Literal["gap"] = "gap"
    rule_id: RuleId
    clause: str
    product_id: ProductId | None
    reason: GapReason
    quote: str | None = None
    turn_id: TurnId | None = None

    @property
    def tier(self) -> Tier:
        return Tier.incomplete if self.rule_id in REFER_RULES else Tier.understanding_gap


Outcome = Annotated[Passed | Flag | Gap, Field(discriminator="outcome")]
"""What one rule returns for one product: it must commit to Passed, Flag or Gap."""


def _verdict(flags: tuple[Flag, ...], gaps: tuple[Gap, ...]) -> Verdict:
    """Any flag -> flag_for_review; else any gap -> unclear_needs_human; else clear."""
    if flags:
        return Verdict.flag_for_review
    return Verdict.unclear_needs_human if gaps else Verdict.clear


def tier_of(flags: Iterable[Flag], gaps: Iterable[Gap]) -> Tier:
    """The triage tier of a set of flags and gaps: the most serious tier any of them carries."""
    found = {outcome.tier for outcome in (*flags, *gaps)}
    return next((tier for tier in Tier if tier in found), Tier.clear)


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
    """Verdict, tier and evidence for one product. Both must follow from the flags and gaps.

    `evidence_pack` is present exactly when a flag falls under `EVIDENCE_PACK_RULES`.
    """

    product_id: ProductId
    verdict: Verdict
    tier: Tier
    flags: tuple[Flag, ...] = ()
    gaps: tuple[Gap, ...] = ()
    passed: tuple[RuleId, ...] = ()
    evidence_pack: EvidencePack | None = None
    # A correction inside one reply whose final answer stood: the earlier words, then the whole
    # reply. For the reviewer only: not a flag, not a gap, and never part of the verdict or tier.
    self_corrections: tuple[AnswerConflict, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> "ProductResult":
        if any(o.product_id != self.product_id for o in (*self.flags, *self.gaps)):
            raise ValueError("a flag or gap belongs to another product")
        if self.verdict is not _verdict(self.flags, self.gaps):
            raise ValueError("product verdict does not follow from its flags and gaps")
        if self.tier is not tier_of(self.flags, self.gaps):
            raise ValueError("product tier does not follow from its flags and gaps")
        pack_flags = tuple(f for f in self.flags if f.rule_id in EVIDENCE_PACK_RULES)
        if (self.evidence_pack.flags if self.evidence_pack else ()) != pack_flags:
            raise ValueError("the evidence pack does not match the product's flags")
        return self

    @property
    def referral_basis(self) -> Basis | None:
        """What this product's referral rests on; None exactly when its tier is not `refer`."""
        return referral_basis(self.flags)


class CaseResult(Frozen):
    """Result of one call, for the case UI and the half-yearly report.

    The verdict and the tier are the worst of the products and the case-level flags and gaps.
    """

    loan_id: str
    call_id: str
    language: Language
    verdict: Verdict
    tier: Tier
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
        if self.tier is not tier_of(self.all_flags(), self.all_gaps()):
            raise ValueError("case tier does not follow from the flags and gaps")
        return self

    @property
    def referral_basis(self) -> Basis | None:
        """What this case's referral rests on; None exactly when its tier is not `refer`."""
        return referral_basis(self.all_flags())

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
