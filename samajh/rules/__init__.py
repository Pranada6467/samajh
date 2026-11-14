"""Deterministic core: RawExtraction -> Beliefs -> CaseResult. No network, no LLM, no audio."""

from samajh.rules.clauses import CLAUSES
from samajh.rules.halves import method_only, missing_half, what_only
from samajh.rules.engine import RULES, RuleSpec, evaluate, verdict_of
from samajh.rules.normalise import to_beliefs
from samajh.rules.summary import CaseSummary, IssueLine, call_ended_label, summarise

__all__ = [
    "CLAUSES",
    "RULES",
    "CaseSummary",
    "IssueLine",
    "RuleSpec",
    "call_ended_label",
    "evaluate",
    "method_only",
    "missing_half",
    "summarise",
    "to_beliefs",
    "verdict_of",
    "what_only",
]
