"""Deterministic core: RawExtraction -> Beliefs -> CaseResult. No network, no LLM, no audio."""

from samajh.rules.clauses import CLAUSES
from samajh.rules.engine import RULES, RuleSpec, evaluate, verdict_of
from samajh.rules.normalise import to_beliefs

__all__ = ["CLAUSES", "RULES", "RuleSpec", "evaluate", "to_beliefs", "verdict_of"]
