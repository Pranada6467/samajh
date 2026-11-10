"""What the LLM is allowed to emit for one customer reply.

Enums, the numbers of the clauses of the reply that carry an answer, and spans copied from the
reply (amounts, durations, things named in open recall, claims, concerns). No turn ids, no
product ids, no rupee figures, no verdicts. Each model here is the strict JSON schema of one
call, so every field is required and has no default. `samajh.extract._extract` turns these into
`RawExtraction` after `samajh.extract._ground` has resolved every clause number and span.
"""

from enum import StrEnum

from samajh.types import (
    ConsentMethod,
    FeatureClaim,
    Frozen,
    KindClaim,
    PaymentFrequency,
    PaymentSource,
    SaleConcern,
)


class SlotKind(StrEnum):
    """What the bot turn before a customer reply asked. Decided by code from the transcript tags."""

    recall = "recall"
    kind = "kind"
    premium = "premium"
    readback = "readback"
    payment_source = "payment_source"
    payment_frequency = "payment_frequency"
    required_for_loan = "required_for_loan"
    provider_choice = "provider_choice"
    cover = "cover"
    term = "term"
    cancel_window = "cancel_window"
    features = "features"
    consent = "consent"
    other = "other"  # no checked question: the reply is only screened for claims and concerns


class Status(StrEnum):
    stated = "stated"
    dont_know = "dont_know"
    unclear = "unclear"


class WireClaim(Frozen):
    claim: FeatureClaim
    span: str


class WireConcern(Frozen):
    concern: SaleConcern
    span: str


class ScreenReply(Frozen):
    """A second call on every reply: things the customer says without being asked."""

    claims: tuple[WireClaim, ...]
    concerns: tuple[WireConcern, ...]


Clauses = tuple[int, ...]  # 1-based numbers of the reply's clauses, as shown in the prompt


class KindReply(Frozen):
    status: Status
    kind: KindClaim | None
    clauses: Clauses


class PaymentReply(Frozen):
    status: Status
    source: PaymentSource | None
    clauses: Clauses


class FrequencyReply(Frozen):
    status: Status
    frequency: PaymentFrequency | None
    clauses: Clauses


class YesNoReply(Frozen):
    status: Status
    yes: bool | None
    clauses: Clauses


class SpanReply(Frozen):
    """An amount or a duration: the span is the value, in the customer's words."""

    status: Status
    span: str | None
    clauses: Clauses


class ReadbackReply(Frozen):
    status: Status
    confirms: bool | None
    clauses: Clauses
    corrected_amount_span: str | None


class CancelReply(Frozen):
    allowed_status: Status
    allowed: bool | None
    allowed_clauses: Clauses
    window_status: Status
    window_span: str | None
    window_clauses: Clauses


class ConsentReply(Frozen):
    given_status: Status
    given: bool | None
    given_clauses: Clauses
    method_status: Status
    method: ConsentMethod | None
    method_clauses: Clauses


class FeaturesReply(Frozen):
    """The money-back probe: `claims` is the answer."""

    status: Status
    claims: tuple[FeatureClaim, ...]
    clauses: Clauses


class WireRecallItem(Frozen):
    span: str
    kind: KindClaim | None
    amount_span: str | None


class RecallReply(Frozen):
    items: tuple[WireRecallItem, ...]
    took_nothing: bool  # the customer says they took nothing with the loan besides the loan


WireReply = (
    KindReply
    | PaymentReply
    | FrequencyReply
    | YesNoReply
    | SpanReply
    | ReadbackReply
    | CancelReply
    | ConsentReply
    | FeaturesReply
    | RecallReply
)

# `SlotKind.other` has no answer call.
SCHEMA: dict[SlotKind, type[WireReply]] = {
    SlotKind.recall: RecallReply,
    SlotKind.kind: KindReply,
    SlotKind.premium: SpanReply,
    SlotKind.readback: ReadbackReply,
    SlotKind.payment_source: PaymentReply,
    SlotKind.payment_frequency: FrequencyReply,
    SlotKind.required_for_loan: YesNoReply,
    SlotKind.provider_choice: YesNoReply,
    SlotKind.cover: SpanReply,
    SlotKind.term: SpanReply,
    SlotKind.cancel_window: CancelReply,
    SlotKind.features: FeaturesReply,
    SlotKind.consent: ConsentReply,
}
