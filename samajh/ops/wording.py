"""Every word a review page shows for a rule, tier, outcome, status or decision.

A flag is a request for a person to look. Nothing here states a conclusion about a sale, and
`banned_in` is the check that keeps it so: the tests run it over this module and over every
generated view.
"""

import re
from collections.abc import Sequence

from samajh.ops.model import AttemptOutcome, Channel, Decision, FinalStatus, IngestSummary, PhoneSession
from samajh.rules.clauses import INTERNAL
from samajh.types import Basis, GapReason, LoanKind, RuleId, Tier

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
    r"\bfinding",  # a flag is evidence for review; the word reads as a conclusion about the sale
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
    AttemptOutcome.do_not_call: "Asked not to be called again",
    AttemptOutcome.written_requested: "Asked for this in writing instead",
    AttemptOutcome.completed_not_analysed: "Completed, but the call could not be analysed",
    AttemptOutcome.completed: "Completed",
    AttemptOutcome.request_unconfirmed: "Request from a speaker not confirmed as the borrower",
}

# What the dialogue itself recorded, beside a `request_unconfirmed` attempt: the request the
# unconfirmed speaker made (samajh.ops.model.UNCONFIRMED_REQUESTS).
UNCONFIRMED_REQUEST_LABEL: dict[str, str] = {
    "do_not_call": "asked not to be called again",
    "human_requested": "asked to speak to a person",
    "call_back_later": "asked to be called later",
    "written_requested": "asked for this in writing instead",
}

STATUS_LABEL: dict[FinalStatus, str] = {
    FinalStatus.not_attempted: "Not attempted yet",
    FinalStatus.unreachable: "Not reached",
    FinalStatus.wrong_party: "Someone else answered",
    FinalStatus.not_confirmed: "Identity not confirmed",
    FinalStatus.declined: "Declined the call",
    FinalStatus.call_back_later: "Asked to be called later, not yet called",
    FinalStatus.language_switch: "Asked for another language, not yet called in it",
    # No promise of a later call: the loan may be at its attempt limit.
    FinalStatus.request_unconfirmed: "Request from a speaker not confirmed as the borrower (no call after it)",
    FinalStatus.not_reached_in_time: "Not reached within 30 days of the sale",
    FinalStatus.incomplete: "Call ended early",
    FinalStatus.do_not_call: "Asked not to be called again (no further attempt)",
    FinalStatus.written_requested: "Asked for this in writing instead (no further attempt)",
    FinalStatus.completed_not_analysed: "Completed, but the call could not be analysed (no flags raised)",
    FinalStatus.completed_late: "Completed after day 30 from the sale (not in the counted calls)",
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

# What a referral rests on (samajh.types.Basis), beside every referral count and on each case.
BASIS_LABEL: dict[Basis, str] = {
    Basis.customer_statement: "On what the customer said",
    Basis.record_only: "On the record alone",
}
REFERRED_ON_STATEMENT = "Referred on what the customer said"
REFERRED_ON_RECORD = "Referred on the record alone"
BASIS_NOTE = (
    "A referral on the record alone rests on the lender's own record (for example no consent on record) "
    "and on nothing the customer said. It is counted apart, so that the referrals on what the customer said "
    "describe the calls and not the lender's records. Either kind is a request for a person to look, and "
    "nothing more."
)
RULE_SPLIT_NOTE = (
    "In this table the two counts are by rule: whether the lines under that rule rest on the record alone "
    "or on what the customer said. A call counted on the record alone under one rule may be referred on "
    "what the customer said under another."
)

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

INTERVAL_LIMIT = (
    "Each interval is a 95% Wilson interval for sampling among eligible sales only (sales a draw "
    "covered). It does not cover sales no draw covered, errors in reading the call, or customers who "
    "were not reached."
)
# Replaces INTERVAL_LIMIT when the draws gave sales clearly different chances (report.NARROW_RATIO).
NO_INTERVAL_LIMIT = (
    "No interval is given on any share in this report, because the draws gave eligible sales different "
    "chances of being sampled; the Sampling section says why."
)

SIMULATED_ONLY_LIMITS: tuple[str, str, str] = (
    (
        "The loan book, the customers and the calls are synthetic and simulated. No real lender, customer "
        "or call is behind any number here."
    ),
    (
        "Customer replies come from scripted phrase banks. They are text only: no speech was recorded or "
        "transcribed."
    ),
    (
        "The share of calls flagged under each rule follows from the mix of customers the simulation "
        "assumes. It says nothing about any real lender."
    ),
)
COMMON_LIMITS: tuple[str, ...] = (
    INTERVAL_LIMIT,
    (
        "The flag counts describe customers who completed the call. Customers who did not answer, "
        "declined or ended the call early may differ."
    ),
    "A referral is a request for a person to look at one call, and nothing more.",
    (
        "Reviewer decisions are counted, not estimated: they are one reviewer's view of the file, and no "
        "interval is given for them."
    ),
)
LIMITS: tuple[str, ...] = (*SIMULATED_ONLY_LIMITS, *COMMON_LIMITS)  # a batch with no phone call


def _mixed_limits(simulated: int, phone_attempts: int, phone_outside: int) -> tuple[str, str, str]:
    """The first three limits for a batch with phone calls, from its counts."""
    phone = phone_attempts + phone_outside
    scripted = (
        f"{simulated} attempt(s) in this batch were simulated: their outcome and any customer reply were "
        "scripted from phrase banks, as text only, with no speech recorded or transcribed."
        if simulated
        else "No attempt in this batch was simulated."
    )
    return (
        (
            "The loan book and the customers on it are synthetic. Every phone call was made against a "
            "synthetic record, so no real lender and no customer of a lender is behind any number here."
        ),
        (
            f"{scripted} {phone} call(s) were phone sessions on the browser phone ({phone_attempts} "
            f"attempt(s) in the sample and {phone_outside} call(s) outside it): their customer turns were "
            "read by Gnani Prisma speech-to-text (each case file names the model) from the customer audio "
            "the next note counts."
        ),
        (
            "The share of calls flagged under each rule follows from the mix of customers the simulation "
            "assumes and, for phone calls, from what was said on the browser phone against synthetic "
            "records. It says nothing about any real lender."
            if simulated
            else "The share of calls flagged under each rule follows only from what was said on the browser "
            "phone against synthetic records, by whoever made the calls: they are not a sample of any "
            "lender's customers. It says nothing about any real lender."
        ),
    )


def limits(
    intervals_shown: bool,
    simulated: int = 0,
    phone_attempts: int = 0,
    phone_outside: int = 0,
    phone_note: str | None = None,
) -> tuple[str, ...]:
    """The report's limits, from what the batch holds: `simulated` simulated attempts,
    `phone_attempts` phone attempts in the sample and `phone_outside` phone calls outside it. With no
    phone call, every call is simulated text and the limits say so; with phone calls they say which
    calls are which, with their counts, and `phone_note` (where the customer audio came from) follows
    them. Without intervals, the interval sentence says why there are none."""
    common = COMMON_LIMITS if intervals_shown else (NO_INTERVAL_LIMIT, *COMMON_LIMITS[1:])
    if not phone_attempts and not phone_outside:
        return (*SIMULATED_ONLY_LIMITS, *common)
    first = _mixed_limits(simulated, phone_attempts, phone_outside)
    note = (phone_note,) if phone_note else ()
    return (*first[:2], *note, first[2], *common)


def phone_note(sessions: Sequence[PhoneSession]) -> str | None:
    """What the phone calls' case files say about where the customer audio came from. None when the
    batch has no phone call. Counted from each session's `customer_audio`, never assumed."""
    if not sessions:
        return None
    known = [s.customer_audio for s in sessions if s.customer_audio is not None]
    mic = sum(a.mic > 0 and a.file == 0 for a in known)
    file = sum(a.file > 0 and a.mic == 0 for a in known)
    both = sum(a.mic > 0 and a.file > 0 for a in known)
    silent = sum(a.mic == 0 and a.file == 0 for a in known)
    unknown = len(sessions) - len(known)
    parts = [
        f"{mic} with customer audio from the microphone only",
        f"{file} from prepared audio files only",
        f"{both} from both",
        f"{silent} with no customer audio",
    ]
    if unknown:
        parts.append(f"{unknown} where it is not recorded, or not readable, in the case file")
    return (
        f"Calls marked Phone call were made on the browser phone against synthetic records: "
        f"{len(sessions)} phone session(s), {', '.join(parts)}. None of them is a call with a real "
        "customer of a lender."
    )


def window_note(after: int, phone_after: int, attempts: int) -> str:
    """The sentence on attempts after day 30 from the sale."""
    if not after:
        return "No attempt was made after day 30 from the sale."
    simulated = after - phone_after
    who = (
        "all of them phone calls"
        if not simulated
        else f"{phone_after} phone call(s) and {simulated} simulated (which should not happen)"
    )
    return (
        f"{after} of {attempts} attempts were made after day 30 from the sale, {who}. They are logged and "
        "shown, and no call made after day 30 is counted in the outcome shares."
    )


CHANGED_LABEL = "Case file changed after it was brought in: the version brought in first is kept"
# Every skip reason for a session with a turn the classifier failed on begins with this
# (samajh.ops.sessions): such a session is void, in no count, and the call is to be repeated.
CLASSIFIER_FAILED = "not counted: the classifier failed on"


def ingest_note(summary: IngestSummary | None) -> str:
    """The sentences on phone sessions the last ingest did not bring in, and on those whose case file
    changed after they were brought in (they stay where they were, and are not among the left out)."""
    if summary is None:
        return "No phone sessions have been brought in."
    skipped = len(summary.skipped)
    if not skipped:
        note = (
            f"The last ingest saw {summary.sessions} phone session(s) and brought in every one "
            f"({len(summary.linked)} as attempts, {len(summary.outside)} outside the sample)."
        )
    else:
        note = (
            f"The last ingest saw {summary.sessions} phone session(s) and did not bring in {skipped}: they are "
            f"in no count here, not even the reach figures. {len(summary.linked)} came in as attempts and "
            f"{len(summary.outside)} as calls outside the sample. Each session left out is listed on the "
            "attempt log with the reason."
        )
        void = sum(s.reason.startswith(CLASSIFIER_FAILED) for s in summary.skipped)
        if void:
            note += (
                f" {void} of those left out had a turn the classifier failed on, so the word lists alone "
                "read it: each such call is void and is to be repeated."
            )
    if summary.changed:
        note += (
            f" {len(summary.changed)} of the sessions brought in have a case file that changed after it was "
            "brought in: the version brought in first is kept and counted as before, and each is listed on "
            "the attempt log with what differs."
        )
    return note


# --- the speech readings beside an amount quote on the case page (views.readings_view) ------------
# The closing words of the line, from the case file's `readings_agreed` (never recomputed in
# samajh/ops) and `followed_by` (what the bot did next). Without a known `followed_by`, or with
# "other", the closing says only same or differ, nothing about what followed (views.readings_view).
READINGS_SAME = "same amount"
READINGS_DIFFER = "differ"
READINGS_SAME_READ_BACK = "same amount, read back"
READINGS_SAME_ASKED_AGAIN = "same amount, asked again"
READINGS_DIFFER_ASKED_AGAIN = "differ, asked again"
# Provisional wording; the final one comes from the server side.
READINGS_DIFFER_READ_BACK = "differ, read back"
READINGS_ONE = "one reading"
READINGS_NOT_COMPARED = "two readings, not compared as amounts in the case file"
READINGS_NO_TEXT = "no text"
READINGS_NONE_FOR_TURN = "No speech reading is listed for this turn in the case file."
READINGS_NOT_KEPT = "This case file was written before case files kept the speech readings."
READINGS_TEXT_CALL = "Text call, no speech reading."


def model_label(model: str) -> str:
    """The model as the page names it: "prisma-v3.0" is "Prisma v3.0"; any other name as written."""
    return f"Prisma {model.removeprefix('prisma-')}" if model.startswith("prisma-") else model


NO_GAP = "none"  # the most common gap tile when no counted call has an understanding gap

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
