from __future__ import annotations

from opskit import COMPLETED, customer, loan

from samajh.ops import book as books
from samajh.ops.model import Tier
from samajh.ops.simulate import script_call, scripted_analysis
from samajh.ops.triage import triage
from samajh.scenarios.model import DONT_KNOW, DepositWord
from samajh.types import FeatureClaim, KindClaim, RuleId, SaleConcern


def _triage(of, who):
    result, _ = scripted_analysis(script_call(of, who), of.record)
    return result, triage(result)


def test_the_tier_of_a_call_is_the_one_the_core_gives_it() -> None:
    _, loans, customers = books.generate_book(85)
    for of, who in zip(loans, customers, strict=True):
        result, found = _triage(of, who)
        assert found.tier.value == result.tier.value
        assert (found.severity is not None) == (found.tier is Tier.refer)


def test_flags_under_one_rule_become_one_line_that_keeps_every_quote() -> None:
    of = loan(1)
    believes_fd = customer(
        of,
        COMPLETED,
        kind=KindClaim.deposit,
        deposit_word=DepositWord.fd,
        money_back=(FeatureClaim.is_deposit, FeatureClaim.refundable_anytime),
        cover_inr=DONT_KNOW,
    )
    result, found = _triage(of, believes_fd)
    kind_flags = [f for f in result.all_flags() if f.rule_id is RuleId.kind]
    assert len(kind_flags) == 2  # said once unprompted and once when asked

    rules = [line.rule_id for line in found.lines]
    assert len(rules) == len(set(rules))
    (kind,) = (line for line in found.lines if line.rule_id is RuleId.kind)
    assert {q.turn_id for q in kind.quotes} == {f.turn_id for f in kind_flags} and len(kind.quotes) == 2
    assert (kind.tier, kind.severity, kind.clause) == (Tier.refer, "high", "85Y")
    assert kind.heard == "customer described it as a deposit (FD)"


def test_refer_lines_come_first_and_a_report_only_line_never_opens_a_case() -> None:
    of = loan(1)
    _, mixed = _triage(
        of, customer(of, COMPLETED, cover_inr=DONT_KNOW, concerns=(SaleConcern.coached_answers,))
    )
    assert [(line.rule_id, line.tier) for line in mixed.lines] == [
        (RuleId.sale_conduct, Tier.refer),
        (RuleId.cover, Tier.understanding_gap),
    ]
    assert (mixed.tier, mixed.severity) == (Tier.refer, "high")

    _, gap_only = _triage(of, customer(of, COMPLETED, cover_inr=DONT_KNOW))
    assert (gap_only.tier, gap_only.severity) == (Tier.understanding_gap, None)
    _, nothing = _triage(of, customer(of, COMPLETED))
    assert (nothing.tier, nothing.lines) == (Tier.clear, ())
    _, undecided = _triage(of, customer(of, COMPLETED, consent_method=DONT_KNOW))
    assert (undecided.tier, undecided.lines) == (Tier.incomplete, ())
