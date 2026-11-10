"""Spoken Indian amounts: text from Prisma STT in, whole rupees out, and the read-back form.

Pure functions: no network, no LLM, no audio. Decimal and integer arithmetic only.

Handles Hindi (Devanagari), English number words (Latin or Devanagari script), Tamil and
Kannada, plus digits in ASCII or native script with Indian or Western grouping. Romanised
Hindi number words (bavan, saadhe) are out of scope: a text with one of the listed words, or
with an unknown word directly before a unit word, comes back `Ambiguous`, never as a number.
Tamil and Kannada tables and output are not human-reviewed.

`parse_duration_months` reads a term; `parse_duration_days` reads a cancellation window.

`parse_amount` never rounds and never picks between readings: see its docstring for the
weak-candidate rule that decides which numbers in a sentence count, and for `exact=True`,
which accepts a text only when it is the amount and nothing else. `cross_check` compares
two readings of the same turn and says whether a read-back is needed. `parse_approx_amount`
reads what `parse_amount` refuses as hedged ("करीब पचास हज़ार", "पचास से बावन हज़ार") as an
`Approximate` range; `has_doubt_word` and `is_loan_tenure` mark answers that carry no number.
"""

from samajh.amounts._approx import (
    MAX_RANGE_RATIO,
    Approximate,
    has_doubt_word,
    is_loan_tenure,
    parse_approx_amount,
    too_wide,
)
from samajh.amounts._parse import (
    CLAUSE_END,
    Agreed,
    AmbiguityReason,
    Ambiguous,
    AmountResult,
    NoAmount,
    Parsed,
    ReadBackNeeded,
    Span,
    cross_check,
    parse_amount,
    parse_duration_days,
    parse_duration_months,
)
from samajh.amounts._speak import NOT_HUMAN_REVIEWED, format_inr, spoken_amount

__all__ = [
    "CLAUSE_END",
    "MAX_RANGE_RATIO",
    "NOT_HUMAN_REVIEWED",
    "Agreed",
    "AmbiguityReason",
    "Ambiguous",
    "AmountResult",
    "Approximate",
    "NoAmount",
    "Parsed",
    "ReadBackNeeded",
    "Span",
    "cross_check",
    "format_inr",
    "has_doubt_word",
    "is_loan_tenure",
    "parse_amount",
    "parse_approx_amount",
    "parse_duration_days",
    "parse_duration_months",
    "spoken_amount",
    "too_wide",
]
