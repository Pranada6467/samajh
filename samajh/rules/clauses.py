"""Regulatory paragraph for each rule, by lender type. The only place a paragraph number appears.

Source: references/claims/claims-ledger.md rows A5 and A19 (verified against RBI/2026-27/115
for commercial banks and RBI/2026-27/123 for NBFCs on 2026-11-10). The sub-paragraph letters
are the same for every lender type and only the prefix changes. Housing finance companies
follow the NBFC paragraphs. Other lender types are not mapped in v1.

A paragraph here is the one a flag may engage. The last entry of each map is the definition
the belief check may engage; it is shown next to a flag and never as a verdict.
"""

from samajh.types import KindClaim, LenderType, ProductKind, RuleId

INTERNAL = "internal"  # a check of our own that engages no paragraph


def _paragraphs(prefix: str, definition: str) -> dict[RuleId, str]:
    feedback = f"{prefix}Y"
    return {
        RuleId.kind: feedback,
        RuleId.premium: feedback,
        RuleId.cover: feedback,
        RuleId.term: feedback,
        RuleId.cancel_window: feedback,
        RuleId.recall: feedback,
        RuleId.recall_unmatched: feedback,
        RuleId.consent: f"{prefix}G",
        RuleId.loan_funded: f"{prefix}W",
        RuleId.bundling: f"{prefix}V",
        RuleId.belief_mismatch: definition,
        RuleId.sale_conduct: INTERNAL,
        RuleId.evidence: INTERNAL,
    }


CLAUSES: dict[LenderType, dict[RuleId, str]] = {
    LenderType.bank: _paragraphs("85", "4(20A)(ii)"),
    LenderType.nbfc: _paragraphs("101", "6(9A)(ii)"),
}

# What a customer who understood the product would call it.
KIND_ON_RECORD: dict[ProductKind, KindClaim] = {
    ProductKind.credit_life: KindClaim.insurance,
}
