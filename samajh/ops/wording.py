"""Every word a review page shows for a rule, tier, outcome, status or decision.

A flag is a request for a person to look. Nothing here names a finding about a sale, and
`banned_in` is the check that keeps it so: the tests run it over this module and over every
generated view.
"""

import re

from samajh.ops.model import AttemptOutcome, Channel, Decision, FinalStatus, Tier
from samajh.rules.clauses import INTERNAL
from samajh.types import GapReason, LoanKind, RuleId

BANNED: tuple[str, ...] = (
    r"mis[\s-]?s(?:ell|old)",
    r"\brefund",
    r"\bviolat",
    r"\bbreach",
    r"\bfraud",
    r"\bguilty\b",
    r"\bverdict",
    r"\bproven\b",
    r"\bnon[\s-]?compliant",
)


def banned_in(text: str) -> list[str]:
    """The banned patterns found in `text`, ignoring case. Empty when the text is fine."""
    return [pattern for pattern in BANNED if re.search(pattern, text, re.IGNORECASE)]


RULE_LABEL: dict[RuleId, str] = {
    RuleId.kind: "What the product is",
    RuleId.premium: "What it cost",
    RuleId.cover: "Cover amount",
    RuleId.term: "How long it runs",
    RuleId.cancel_window: "Cancellation window",
    RuleId.recall: "Naming the product unprompted",
    RuleId.recall_unmatched: "A product named that is not on the record",
    RuleId.consent: "Consent",
    RuleId.loan_funded: "Premium deducted from the loan",
    RuleId.bundling: "Required for the loan",
    RuleId.belief_mismatch: "Beliefs about the product's features",
    RuleId.sale_conduct: "How the sale was handled",
    RuleId.evidence: "Quotes found in the transcript",
}

# Completes "<count> of <n> customers who completed the call ...".
RULE_STATEMENT: dict[RuleId, str] = {
    RuleId.kind: "did not describe the product as what the record shows",
    RuleId.premium: "did not state the premium on the record",
    RuleId.cover: "did not state the cover amount on the record",
    RuleId.term: "did not state the term on the record",
    RuleId.cancel_window: "could not state the cancellation window on the record",
    RuleId.recall: "did not name the product before it was mentioned",
    RuleId.recall_unmatched: "named a product that is not on the record",
    RuleId.consent: "gave an account of agreeing that does not match the record, or the record holds no consent",
    RuleId.loan_funded: (
        "did not know the premium was deducted from the loan, or the record shows a deduction with no consent"
    ),
    RuleId.bundling: (
        "had a product required for the loan with a question over the choice of provider or what the product is"
    ),
    RuleId.belief_mismatch: "held a belief about the product that its features on the record do not support",
    RuleId.sale_conduct: "voiced a concern about how the product was sold",
    RuleId.evidence: "had a quote that could not be found in the transcript",
}

GAP_LABEL: dict[GapReason, str] = {
    GapReason.not_asked: "the question was not asked",
    GapReason.no_usable_answer: "no usable answer",
    GapReason.value_not_parsed: "the figure could not be read",
    GapReason.readback_rejected: "the customer did not confirm the read-back",
    GapReason.readback_mismatch: "the read-back did not match what was heard",
    GapReason.quote_not_grounded: "the quote was not found in the transcript",
    GapReason.extraction_failed: "the reply could not be read",
    GapReason.not_comparable: "the record has nothing to compare the answer with",
}

TIER_LABEL: dict[Tier, str] = {
    Tier.refer: "Referred for review",
    Tier.understanding_gap: "Understanding gap (report only)",
    Tier.incomplete: "Incomplete",
    Tier.clear: "No finding",
}

OUTCOME_LABEL: dict[AttemptOutcome, str] = {
    AttemptOutcome.no_answer: "No answer",
    AttemptOutcome.wrong_party: "Someone else answered",
    AttemptOutcome.not_confirmed: "Identity not confirmed",
    AttemptOutcome.declined: "Declined the call",
    AttemptOutcome.call_back_later: "Asked to be called later",
    AttemptOutcome.incomplete: "Call ended early",
    AttemptOutcome.completed: "Completed",
}

STATUS_LABEL: dict[FinalStatus, str] = {
    FinalStatus.not_attempted: "Not attempted yet",
    FinalStatus.unreachable: "Not reached",
    FinalStatus.wrong_party: "Someone else answered",
    FinalStatus.not_confirmed: "Identity not confirmed",
    FinalStatus.declined: "Declined the call",
    FinalStatus.call_back_later: "Asked to be called later, not yet called",
    FinalStatus.incomplete: "Call ended early",
    FinalStatus.completed: "Completed",
}

STAGE_LABEL: dict[str, str] = {
    "attempted": "Attempted",
    "reached": "Answered the phone",
    "right_party_confirmed": "Right person confirmed",
    "completed": "Completed the call",
}

DECISION_LABEL: dict[Decision, str] = {
    Decision.established: "Established by reviewer",
    Decision.not_established: "Not established",
    Decision.call_customer: "Call the customer",
    Decision.needs_information: "Needs more information",
}
AWAITING_LABEL = "Awaiting a decision"

BREAKDOWN_LABEL: dict[str, str] = {"loan_kind": "Loan type", "branch": "Branch", "channel": "Sales channel"}
LOAN_KIND_LABEL: dict[LoanKind, str] = {LoanKind.gold: "Gold loan", LoanKind.personal: "Personal loan"}
CHANNEL_LABEL: dict[Channel, str] = {
    Channel.branch: "Branch",
    Channel.agent: "Direct selling agent",
    Channel.app: "Lender's app",
}

SIMULATED_NOTICE = (
    "Simulated batch: the loan book, the customers and every call are synthetic. No real customer was called."
)

LIMITS: tuple[str, ...] = (
    (
        "The loan book, the customers and the calls are synthetic and simulated. No real lender, customer "
        "or call is behind any number here."
    ),
    (
        "Customer replies come from scripted phrase banks. They are text only: no speech was recorded or "
        "transcribed."
    ),
    (
        "The share of each finding follows from the mix of customers the simulation assumes. It says "
        "nothing about any real lender."
    ),
    (
        "Each interval is a 95% Wilson interval for sampling alone. It does not cover errors in reading "
        "the call or customers who were not reached."
    ),
    (
        "Findings describe customers who completed the call. Customers who did not answer, declined or "
        "ended the call early may differ."
    ),
    "A referral is a request for a person to look at one call, and nothing more.",
)


def may_engage(clause: str) -> str | None:
    """How a paragraph is shown beside a line. None for a check of our own."""
    return None if clause == INTERNAL else f"may engage para {clause}"
