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
    readback = "readback"  # the read-back of the premium
    cover_readback = "cover_readback"  # the read-back of the cover: step read_back, asks=cover
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


class _ScreenClaim(StrEnum):
    """A claim about a product. `Product.features` lists the claims that are true of it."""

    is_deposit = "is_deposit"
    refundable_anytime = "refundable_anytime"
    guaranteed_return = "guaranteed_return"
    one_time_payment = "one_time_payment"
    withdrawable_after_period = "withdrawable_after_period"


# The screening call keeps the five claims it was measured with: its schema and prompt are
# byte-identical to before `FeatureClaim.money_back` (P5 fix round 2), so its cached readings stand.
# An untimed "the money comes back" is read by the money-back probe (`FeaturesReply`) only.
_ScreenClaim.__name__ = _ScreenClaim.__qualname__ = "FeatureClaim"


class WireClaim(Frozen):
    claim: _ScreenClaim
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


class PremiumReply(Frozen):
    """The premium: an amount in the customer's words, or `free` when they say it cost nothing."""

    status: Status
    span: str | None
    free: bool
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


class Change(StrEnum):
    """Does the customer, inside one reply, give an answer and then change it?"""

    none = "none"  # one answer, however often repeated or stressed; or no answer at all
    corrected = "corrected"  # an answer, then a DIFFERENT answer to the same question
    withdrawn = "withdrawn"  # an answer, then taken back, with no other answer given


# This docstring is sent to the model as the schema's description: it is part of the prompt and of
# the cache key. Do not reword it without rerunning the evaluations (a rewording on 2026-11-10
# changed 1 of 1,107 frozen-set readings). Its last sentence is out of date about the code: code
# keeps a corrected answer's earlier words in `also` or takes a stated answer away, and adds no
# conflict (`samajh.extract._extract._Assembly.check`).
# Stale but pinned: since P3a round 4 the check also runs on a one-clause reply with a marker word
# (`Reply.has_change_marker`). The docstring below is sent to the model as the schema description,
# so it is left as measured; tests/extract/test_extract_prompt_pin.py holds it.
class ChangeReply(Frozen):
    """The change check: a separate call on every checked reply of two or more clauses.

    It never gives a value. Code uses it only to take a stated answer away or to add a conflict.
    """

    change: Change
    first_clauses: Clauses  # the clause(s) holding the answer given first; empty for none
    final_clauses: Clauses  # the clause(s) holding the answer that replaces it; corrected only, else empty


WireReply = (
    KindReply
    | PaymentReply
    | FrequencyReply
    | YesNoReply
    | SpanReply
    | PremiumReply
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
    SlotKind.premium: PremiumReply,
    SlotKind.readback: ReadbackReply,
    SlotKind.cover_readback: ReadbackReply,
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
