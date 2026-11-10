"""Compare the frozen gold with the rule engine on perfect input. Run only after the freeze.

Two paths, both without an LLM:
  * `beliefs`: the customer's true beliefs handed to `evaluate` as perfect `Beliefs`.
  * `extraction`: the perfect extraction of the scripted call, through `to_beliefs` and then
    `evaluate`. This also exercises the amount parser and quote grounding on the scripted text.

This is the only module in the package that imports `samajh.rules`.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from samajh.rules import evaluate, to_beliefs
from samajh.scenarios.model import CallScripts, ProductBelief, Scenario
from samajh.types import (
    Answer,
    Beliefs,
    CaseResult,
    DontKnow,
    NotAsked,
    OpenRecall,
    ProductBeliefs,
    ProductId,
    RawProductAnswers,
    RecallItem,
    RuleId,
    Stated,
    Unclear,
    Verdict,
)

Path = Literal["beliefs", "extraction"]
Key = tuple[ProductId | None, RuleId]


def _number(raw: Answer, value) -> Answer:
    """The raw answer with its words replaced by the number the customer means."""
    if isinstance(raw, Stated):
        return Stated(value=value, evidence=raw.evidence)
    assert isinstance(raw, NotAsked | Unclear | DontKnow)
    return raw


def _product_beliefs(raw: RawProductAnswers, belief: ProductBelief) -> ProductBeliefs:
    shared = raw.model_dump(exclude={"premium", "cover", "term", "cancel_window"})
    return ProductBeliefs(
        **shared,
        premium_inr=_number(raw.premium, belief.premium_inr),
        cover_inr=_number(raw.cover, belief.cover_inr),
        term_months=_number(raw.term, belief.term_months),
        cancel_window_days=_number(raw.cancel_window, belief.cancel_window_days),
    )


def perfect_beliefs(scenario: Scenario, calls: CallScripts) -> Beliefs:
    """The scenario's true beliefs as `Beliefs`: numbers come from the belief, not from parsing words."""
    extraction = calls.teach_back.extraction
    recall = extraction.recall
    items = tuple(
        RecallItem(
            evidence=item.evidence,
            kind=item.kind,
            amount_inr=(
                scenario.belief(item.product_id).premium_inr if item.amount_text is not None else None
            ),
            product_id=item.product_id,
        )
        for item in recall.items
    )
    return Beliefs(
        call_id=extraction.call_id,
        loan_id=scenario.record.loan_id,
        language=scenario.language,
        recall=OpenRecall(asked=recall.asked, answer=recall.answer, items=items),
        products=tuple(_product_beliefs(raw, scenario.belief(raw.product_id)) for raw in extraction.products),
        sale_concerns=extraction.sale_concerns,
    )


def run_engine(scenario: Scenario, calls: CallScripts, path: Path) -> CaseResult:
    """The rule engine's result for one scenario on perfect input."""
    if path == "beliefs":
        beliefs = perfect_beliefs(scenario, calls)
    else:
        beliefs = to_beliefs(calls.teach_back.extraction, scenario.record, calls.teach_back.transcript)
    return evaluate(scenario.record, beliefs)


@dataclass(frozen=True)
class Comparison:
    """Gold against the engine for one scenario."""

    scenario_id: str
    gold_verdict: Verdict
    engine_verdict: Verdict
    product_verdicts_agree: bool
    gold_flags: frozenset[Key]
    engine_flags: frozenset[Key]
    gold_unclear: frozenset[Key]
    engine_gaps: frozenset[Key]
    engine_detail: tuple[str, ...]

    @property
    def verdict_agrees(self) -> bool:
        return self.gold_verdict is self.engine_verdict and self.product_verdicts_agree

    @property
    def flags_agree(self) -> bool:
        return self.gold_flags == self.engine_flags

    @property
    def unclear_agrees(self) -> bool:
        return self.gold_unclear == self.engine_gaps

    @property
    def agrees(self) -> bool:
        """The headline: every verdict and the whole flag set match."""
        return self.verdict_agrees and self.flags_agree


def compare(scenario: Scenario, result: CaseResult) -> Comparison:
    gold = scenario.gold
    engine_products = {p.product_id: p.verdict for p in result.products}
    detail = (
        *(f"flag {f.rule_id.value}/{f.severity.value}: expected {f.expected!r}, heard {f.heard!r}" for f in result.all_flags()),
        *(f"gap {g.rule_id.value}: {g.reason.value}" for g in result.all_gaps()),
    )
    return Comparison(
        scenario_id=scenario.id,
        gold_verdict=gold.verdict,
        engine_verdict=result.verdict,
        product_verdicts_agree=all(engine_products.get(p.product_id) is p.verdict for p in gold.products),
        gold_flags=gold.flag_keys(),
        engine_flags=frozenset((f.product_id, f.rule_id) for f in result.all_flags()),
        gold_unclear=gold.unclear_keys(),
        engine_gaps=frozenset((g.product_id, g.rule_id) for g in result.all_gaps()),
        engine_detail=detail,
    )


def check(scenarios: tuple[Scenario, ...], calls: tuple[CallScripts, ...], path: Path) -> tuple[Comparison, ...]:
    """Compare every scenario's gold with the engine on one path."""
    by_id = {c.id: c for c in calls}
    return tuple(compare(s, run_engine(s, by_id[s.id], path)) for s in scenarios)


def _keys(keys: frozenset[Key]) -> str:
    return ", ".join(sorted(f"{rule.value}" if pid else f"case:{rule.value}" for pid, rule in keys)) or "-"


def report(comparisons: tuple[Comparison, ...], path: Path) -> str:
    """A plain-text report: the agreement numbers, per-rule flag counts, and every disagreement."""
    n = len(comparisons)
    lines = [
        f"path: {path}   scenarios: {n}",
        f"verdict and flag set agree: {sum(c.agrees for c in comparisons)}/{n}",
        f"  verdicts agree:           {sum(c.verdict_agrees for c in comparisons)}/{n}",
        f"  flag sets agree:          {sum(c.flags_agree for c in comparisons)}/{n}",
        f"  unclear-rule sets agree:  {sum(c.unclear_agrees for c in comparisons)}/{n}",
    ]
    both, gold_only, engine_only = Counter(), Counter(), Counter()
    for c in comparisons:
        both.update(rule for _, rule in c.gold_flags & c.engine_flags)
        gold_only.update(rule for _, rule in c.gold_flags - c.engine_flags)
        engine_only.update(rule for _, rule in c.engine_flags - c.gold_flags)
    lines.append("flags per rule (gold and engine / gold only / engine only):")
    for rule in RuleId:
        if both[rule] or gold_only[rule] or engine_only[rule]:
            lines.append(f"  {rule.value:<16} {both[rule]:>4} / {gold_only[rule]:>3} / {engine_only[rule]:>3}")
    disagreements = [c for c in comparisons if not (c.agrees and c.unclear_agrees)]
    lines.append(f"disagreements: {len(disagreements)}")
    for c in disagreements:
        lines.append(f"- {c.scenario_id}: gold {c.gold_verdict.value}, engine {c.engine_verdict.value}")
        if not c.flags_agree:
            lines.append(f"    gold-only flags:   {_keys(c.gold_flags - c.engine_flags)}")
            lines.append(f"    engine-only flags: {_keys(c.engine_flags - c.gold_flags)}")
        if not c.unclear_agrees:
            lines.append(f"    gold-only unclear: {_keys(c.gold_unclear - c.engine_gaps)}")
            lines.append(f"    engine-only gaps:  {_keys(c.engine_gaps - c.gold_unclear)}")
        lines.extend(f"    engine: {d}" for d in c.engine_detail)
    return "\n".join(lines)
