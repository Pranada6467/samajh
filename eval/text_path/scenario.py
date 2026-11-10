"""One evaluation scenario and its gold labels, whatever set it comes from."""

from dataclasses import dataclass

from samajh.types import (
    CaseResult,
    Language,
    LoanRecord,
    ProductId,
    RawExtraction,
    RuleId,
    Transcript,
    Verdict,
)

FlagKey = tuple[ProductId | None, RuleId]  # product is None for a case-level flag


@dataclass(frozen=True)
class GoldLabels:
    """What a correct pipeline returns for one call: verdicts and flagged rules."""

    verdict: Verdict
    products: tuple[tuple[ProductId, Verdict], ...]
    flags: frozenset[FlagKey]

    @classmethod
    def of(cls, result: CaseResult) -> "GoldLabels":
        return cls(
            verdict=result.verdict,
            products=tuple((p.product_id, p.verdict) for p in result.products),
            flags=frozenset((f.product_id, f.rule_id) for f in result.all_flags()),
        )


@dataclass(frozen=True)
class Scenario:
    """One call with its record and gold.

    `gold` is what the set says is right. `perfect` is the rule engine run on the gold
    extraction: what the pipeline returns when the extractor makes no mistake. The two are the
    same thing on the development set and may differ on a set whose gold was written by hand.
    """

    id: str
    record: LoanRecord
    transcript: Transcript
    gold: GoldLabels
    gold_raw: RawExtraction | None = None
    perfect: CaseResult | None = None
    note: str = ""

    @property
    def language(self) -> Language:
        return self.transcript.language
