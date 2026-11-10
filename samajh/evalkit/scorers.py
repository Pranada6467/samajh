"""The scorers an experiment can name. Each predictor reads a transcript and never sees gold."""

from __future__ import annotations

import re
from decimal import Decimal

from samajh.amounts import Ambiguous, Parsed, parse_amount
from samajh.evalkit.score import Hypothesis, Prediction, Scorer

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_UNITS = (
    (10_000_000, ("करोड़", "करोड", "crore", "கோடி", "ಕೋಟಿ")),
    (100_000, ("लाख", "lakh", "லட்ச", "ಲಕ್ಷ")),
    (1_000, ("हज़ार", "हजार", "thousand", "ஆயிரம்", "ಸಾವಿರ")),
)


def naive_digits(hypothesis: Hypothesis) -> Prediction:
    """What a pipeline does that trusts Prisma's number formatting: take the first digit string,
    multiply by a unit word standing directly after it, and ignore every other word.

    The rule of the 2026-11-10 pilot (`references/pilots/score.py`, `fix=False`), except that a
    value that is not a whole number of rupees is no answer here, where the pilot rounded it.
    """
    match = _NUMBER.search(hypothesis.text)
    if match is None:
        return Prediction(value=None, note="no_digits")
    value = Decimal(match.group().replace(",", ""))
    after = hypothesis.text[match.end() :].lstrip().lower()
    for size, words in _UNITS:
        if after.startswith(words):
            value *= size
            break
    if value != value.to_integral_value():
        return Prediction(value=None, note="non_integer")
    return Prediction(value=int(value))


def parser(hypothesis: Hypothesis) -> Prediction:
    """`samajh.amounts.parse_amount` in its default mode. Anything but exactly one amount is no answer."""
    result = parse_amount(hypothesis.text)
    if isinstance(result, Parsed):
        return Prediction(value=result.rupees)
    if isinstance(result, Ambiguous):
        candidates = ",".join(str(candidate.rupees) for candidate in result.candidates)
        return Prediction(value=None, note=f"ambiguous:{result.reason.value}[{candidates}]")
    return Prediction(value=None, note="no_amount")


AMOUNT = Scorer(name="amount", gold_field="amount_inr", methods={"naive": naive_digits, "parser": parser})

SCORERS: dict[str, Scorer] = {AMOUNT.name: AMOUNT}
