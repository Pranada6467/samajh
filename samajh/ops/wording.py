"""Every word a review page shows for a rule, tier, outcome, status or decision.

A flag is a request for a person to look. Nothing here names a finding about a sale, and
`banned_in` is the check that keeps it so: the tests run it over this module and over every
generated view.
"""

import re

from samajh.ops.model import AttemptOutcome, Channel, Decision, FinalStatus
from samajh.rules.clauses import INTERNAL
from samajh.types import GapReason, LoanKind, RuleId, Tier

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
    Tier.clear: "Nothing to refer",
}

OUTCOME_LABEL: dict[AttemptOutcome, str] = {
    AttemptOutcome.no_answer: "No answer",
    AttemptOutcome.wrong_party: "Someone else answered",
    AttemptOutcome.not_confirmed: "Identity not confirmed",
    AttemptOutcome.declined: "Declined the call",
    AttemptOutcome.call_back_later: "Asked to be called later",
    AttemptOutcome.language_switch: "Asked for another language",
    AttemptOutcome.incomplete: "Call ended early",
    AttemptOutcome.completed_not_analysed: "Completed, but the call could not be analysed",
    AttemptOutcome.completed: "Completed",
}

STATUS_LABEL: dict[FinalStatus, str] = {
    FinalStatus.not_attempted: "Not attempted yet",
    FinalStatus.unreachable: "Not reached",
    FinalStatus.wrong_party: "Someone else answered",
    FinalStatus.not_confirmed: "Identity not confirmed",
    FinalStatus.declined: "Declined the call",
    FinalStatus.call_back_later: "Asked to be called later, not yet called",
    FinalStatus.language_switch: "Asked for another language, not yet called in it",
    FinalStatus.not_reached_in_time: "Not reached within 30 days of the sale",
    FinalStatus.incomplete: "Call ended early",
    FinalStatus.completed_not_analysed: "Completed, but the call could not be analysed (no finding)",
    FinalStatus.completed_late: "Completed after day 30 from the sale (not in the findings)",
    FinalStatus.completed: "Completed within 30 days of the sale",
}

STAGE_LABEL: dict[str, str] = {
    "attempted": "Attempted",
    "reached": "Answered the phone",
    "right_party_confirmed": "Right person confirmed",
    "completed": "Completed the call within 30 days of the sale",
}

DECISION_LABEL: dict[Decision, str] = {
    Decision.concern_supported: "Concern supported by the file (reviewer's view)",
    Decision.concern_not_supported: "Concern not supported by the file (reviewer's view)",
    Decision.call_customer: "Call the customer",
    Decision.needs_information: "Needs more information",
}
NO_DECISION_LABEL = "No decision recorded yet"
OPEN_LABEL = "Open: no final decision yet"

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
MIXED_NOTICE = (
    "Synthetic batch: the loan book and the customers are synthetic. Calls marked Simulated were scripted; "
    "calls marked Phone call were made on the browser phone with synthetic records."
)
ACCESS_NOTICE = (
    "Demo limitation: these pages have no sign-in. Anyone who can reach this server can record a decision, "
    "and the reviewer's name is free text that nobody checks."
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
        "Each interval is a 95% Wilson interval for sampling among eligible sales only (sales a draw "
        "covered). It does not cover sales no draw covered, errors in reading the call, or customers who "
        "were not reached."
    ),
    (
        "Findings describe customers who completed the call. Customers who did not answer, declined or "
        "ended the call early may differ."
    ),
    "A referral is a request for a person to look at one call, and nothing more.",
    (
        "Reviewer decisions are counted, not estimated: they are one reviewer's view of the file, and no "
        "interval is given for them."
    ),
)
PHONE_LIMIT = (
    "Calls marked Phone call were made on the browser phone against synthetic records, with recorded "
    "synthetic voices. They are not real customers either."
)
AS_OF_NOTE = (
    "Synthetic date: the report is dated by the simulated book's clock, the day of the last call attempt."
)
NO_PREVIOUS_PERIOD = "No previous period: this is the first report of this mechanism (demo)."


def may_engage(clause: str) -> str | None:
    """How a paragraph is shown beside a line. None for a check of our own."""
    return None if clause == INTERNAL else f"may engage para {clause}"


# --- the report's grouping and ranking (the builders' judgment, stated on the page) ---------------

# 85Y asks that the report be used to review product features and risks.
GROUP: dict[RuleId, str] = {
    RuleId.kind: "features",
    RuleId.premium: "features",
    RuleId.cover: "features",
    RuleId.term: "features",
    RuleId.cancel_window: "features",
    RuleId.recall: "features",
    RuleId.recall_unmatched: "features",
    RuleId.belief_mismatch: "risks",
    RuleId.consent: "sale",
    RuleId.loan_funded: "sale",
    RuleId.bundling: "sale",
    RuleId.sale_conduct: "sale",
    RuleId.evidence: "sale",
}
GROUP_LABEL: dict[str, str] = {
    "features": "Product features: what it is, what it costs and covers, how long it runs, how to cancel",
    "risks": "Risks: what the customer believes happens to the money",
    "sale": "How the product was sold: consent, payment from the loan, bundling, conduct",
}
RISK_NOTE = (
    "Risk coverage is thin. One question in the call bears directly on risk: whether the customer can get "
    "the money back (any time, after a period, or with a return), which shows what they believe happens to "
    "the money. Describing the product as a deposit also bears on it. The call asks nothing about "
    "exclusions, claim conditions or what happens to the cover if the loan is closed early."
)

# 1 is the most serious. A customer who thinks insurance is a deposit outranks one who forgot the term.
SERIOUSNESS: dict[RuleId, int] = {
    RuleId.kind: 1,
    RuleId.belief_mismatch: 1,
    RuleId.consent: 1,
    RuleId.loan_funded: 1,
    RuleId.bundling: 1,
    RuleId.sale_conduct: 1,
    RuleId.recall_unmatched: 1,
    RuleId.evidence: 2,
    RuleId.premium: 2,
    RuleId.cancel_window: 2,
    RuleId.recall: 3,
    RuleId.cover: 3,
    RuleId.term: 3,
}
SERIOUSNESS_LABEL: dict[int, str] = {1: "Serious", 2: "Moderate", 3: "Lower"}
SERIOUSNESS_NOTE = (
    "Seriousness is the builders' ranking, not a regulatory scale: a belief about what the product is, "
    "whether it returns money, or how it was agreed to ranks above forgetting a figure."
)
