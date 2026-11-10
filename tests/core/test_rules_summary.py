"""The reviewer's summary: one line per distinct issue per product (contract section 6)."""

import re
from datetime import date

import pytest
from test_rules_engine import (
    P1,
    P2,
    beliefs,
    demo_case,
    dont_know,
    ev,
    everything_flagged,
    named,
    product,
    product_beliefs,
    recall_of,
    record,
    run,
    said,
)

from samajh.rules import CaseSummary, IssueLine, evaluate, summarise
from samajh.types import (
    AnswerConflict,
    CaseResult,
    ClaimEvidence,
    ConcernEvidence,
    Consent,
    ConsentMethod,
    FeatureClaim,
    KindClaim,
    LoanRecord,
    NotAsked,
    OpenRecall,
    PaymentFrequency,
    PaymentSource,
    Question,
    RuleId,
    SaleConcern,
    Stated,
    Tier,
)

PROVIDER = "Namoona Life (synthetic)"
REFER, INCOMPLETE, UNDERSTANDING = Tier.refer, Tier.incomplete, Tier.understanding_gap


def summary_of(product_changes=None, belief_changes=None, **beliefs_kw) -> CaseSummary:
    rec = record(product(**(product_changes or {})))
    return summarise(rec, evaluate(rec, beliefs(product_beliefs(**(belief_changes or {})), **beliefs_kw)))


def lines(summary: CaseSummary, tier: Tier) -> list[IssueLine]:
    return [line for line in summary.lines if line.tier is tier]


def one_line(summary: CaseSummary, tier: Tier = REFER) -> IssueLine:
    (line,) = lines(summary, tier)
    return line


def test_a_clear_case_has_no_lines():
    rec = record()
    summary = summarise(rec, evaluate(rec, beliefs()))
    assert summary == CaseSummary(loan_id="LN-TEST-0000", call_id="CALL-TEST-0000", tier=Tier.clear, lines=())


def test_a_customer_who_thinks_it_is_an_fd_yields_at_most_three_refer_lines():
    """FD in recall and at the kind question, guaranteed returns, withdrawal after a year, required product."""
    summary = summary_of(
        {"required_for_loan": True},
        {
            "kind": said(KindClaim.deposit, "FD hai", 9),
            "feature_probe": said(
                (FeatureClaim.guaranteed_return, FeatureClaim.withdrawable_after_period), "ek saal baad nikal sakte hain", 19
            ),
        },
        recall=recall_of(named(P1, KindClaim.deposit, "ek FD liya tha")),
    )
    assert summary.tier is REFER
    described, believes = lines(summary, REFER)  # six flags, two lines
    assert "deposit" in described.title
    assert described.rule_ids == (RuleId.kind, RuleId.bundling, RuleId.belief_mismatch)
    assert described.clauses == ("85Y", "85V", "4(20A)(ii)")
    assert described.record_value == f"credit-life insurance from {PROVIDER}"
    assert (described.quote, described.turn_id) == ("FD hai", 9)  # the direct answer, before the recall item
    assert described.product_id == P1
    assert believes.rule_ids == (RuleId.belief_mismatch,)
    assert "guaranteed return" in believes.title and "withdrawn after a period" in believes.title
    assert (believes.quote, believes.turn_id) == ("ek saal baad nikal sakte hain", 19)


def test_the_other_money_beliefs_are_one_line_and_a_single_payment_is_its_own():
    claims = tuple(
        ClaimEvidence(claim=c, evidence=ev(c.value, 20 + n))
        for n, c in enumerate(
            (FeatureClaim.refundable_anytime, FeatureClaim.guaranteed_return, FeatureClaim.withdrawable_after_period)
        )
    )
    once = said(PaymentFrequency.one_time, "ek hi baar", 31)
    summary = summary_of({"features": frozenset()}, {"volunteered_claims": claims, "payment_frequency": once})
    money, single = lines(summary, REFER)
    assert all(word in money.title for word in ("any time", "guaranteed return", "after a period"))
    assert "once" in single.title and (single.quote, single.turn_id) == ("ek hi baar", 31)
    assert "features on record: none" in money.record_value


def test_no_consent_and_a_premium_deducted_without_consent_are_one_line():
    line = one_line(summary_of({"consent": None}))
    assert line.rule_ids == (RuleId.consent, RuleId.loan_funded)
    assert line.clauses == ("85G", "85W")
    assert line.record_value == "no consent on record; premium ₹52,000, deducted from the loan"


def test_a_consent_line_shows_the_consent_on_record():
    changes = {"consent": Consent(method=ConsentMethod.signed_form, at=date(2026, 10, 20))}
    line = one_line(summary_of(changes, {"consent_given": said(False, "maine haan nahin ki", 24)}))
    assert line.record_value == "consent on record: signed form on 2026-10-20"
    assert (line.quote, line.turn_id) == ("maine haan nahin ki", 24)


def test_the_payment_source_is_one_line():
    line = one_line(summary_of({}, {"payment_source": said(PaymentSource.separately, "cash diya", 10)}))
    assert line.rule_ids == (RuleId.loan_funded,)
    assert line.record_value == "premium ₹52,000, deducted from the loan"
    assert line.quote == "cash diya"
    apart = one_line(summary_of({"paid_from_loan": False}, {}))
    assert apart.record_value == "premium ₹52,000, paid separately"


def test_every_tied_sale_reason_is_one_line():
    on_record = {"required_for_loan": True, "risk_mitigant": False, "provider_choice_offered": False}
    summary = summary_of(on_record, {"provider_choice_offered": said(False, "nahin bataya", 22)})
    line = one_line(summary)
    assert line.rule_ids == (RuleId.bundling,)
    assert line.quote == "nahin bataya"
    assert line.record_value == (
        "required for the loan: yes; risk mitigant: no; choice of provider offered: no"
    )


def test_a_confirmed_differing_premium_is_one_refer_line():
    line = one_line(summary_of({}, {"premium_inr": said(70_000, "sattar hazaar", 6)}))
    assert line.rule_ids == (RuleId.premium,)
    assert line.record_value == "premium ₹52,000, deducted from the loan"
    assert "₹70,000" in line.title and line.quote == "sattar hazaar"


def test_a_denial_in_recall_is_one_line():
    denial = ev("kuch nahin liya", 3)
    summary = summary_of({}, {"kind": said(KindClaim.insurance)}, recall=OpenRecall(asked=True, denial=denial))
    assert not lines(summary, REFER)  # named the right kind afterwards: only not named unprompted
    summary = summary_of({}, {"kind": NotAsked()}, recall=OpenRecall(asked=True, denial=denial))
    line = one_line(summary)
    assert line.rule_ids == (RuleId.recall,) and line.quote == "kuch nahin liya"
    assert PROVIDER in line.record_value and "₹52,000" in line.record_value


def test_each_kind_of_sale_concern_is_one_case_level_line():
    concerns = (
        ConcernEvidence(concern=SaleConcern.coached_answers, evidence=ev("bola tha haan bolna", 5)),
        ConcernEvidence(concern=SaleConcern.coached_answers, evidence=ev("agent ne sikhaya", 9)),
        ConcernEvidence(concern=SaleConcern.learned_after_sale, evidence=ev("baad mein pata chala", 12)),
    )
    summary = summary_of(sale_concerns=concerns)
    coached, learned = lines(summary, REFER)
    assert coached.product_id is None and learned.product_id is None
    assert coached.quote == "bola tha haan bolna" and learned.quote == "baad mein pata chala"
    assert coached.rule_ids == (RuleId.sale_conduct,) and coached.clauses == ("internal",)
    assert "LN-TEST-0000" in coached.record_value


def test_every_understanding_gap_of_a_product_is_one_line_that_lists_them():
    changes = {
        "cover_inr": dont_know(),
        "term_months": said(12),
        "cancel_window_days": NotAsked(),
        "premium_inr": Stated(value=55_000, evidence=ev(), approximate=True, low=50_000),
    }
    summary = summary_of({}, changes, recall=recall_of())
    assert summary.tier is UNDERSTANDING
    line = one_line(summary, UNDERSTANDING)
    assert summary.lines == (line,)
    assert set(line.rule_ids) == {RuleId.premium, RuleId.cover, RuleId.term, RuleId.cancel_window, RuleId.recall}
    for words in ("premium", "cover", "term", "cancellation window", "unprompted"):
        assert words in line.title
    assert "cover ₹5,00,000" in line.record_value and "term 36 months" in line.record_value


def test_every_incomplete_finding_of_a_product_is_one_line_that_lists_the_undecided_questions():
    changes = {
        "kind": NotAsked(),
        "payment_source": NotAsked(),
        "premium_inr": said(70_000, "sattar hazaar", 6),
        "premium_readback": NotAsked(),
        "ungrounded": (ev("made up", 5),),
    }
    summary = summary_of({}, changes)
    assert summary.tier is INCOMPLETE
    line = one_line(summary, INCOMPLETE)
    assert summary.lines == (line,)
    assert set(line.rule_ids) == {RuleId.kind, RuleId.premium, RuleId.loan_funded, RuleId.evidence}
    assert line.quote == "sattar hazaar"  # the unconfirmed amount is the customer's; the ungrounded quote may not be
    for words in ("what the product is", "premium", "how it was paid for"):
        assert words in line.title


def test_case_level_gaps_are_one_incomplete_line():
    bel = beliefs(recall=recall_of(named(P1), named(None)), ungrounded=(ev("made up", 5),))
    bel = bel.model_copy(update={"unscreened": (ev("unread reply", 8),)})
    rec = record()
    line = one_line(summarise(rec, evaluate(rec, bel)), INCOMPLETE)
    assert line.product_id is None
    assert line.rule_ids == (RuleId.recall_unmatched, RuleId.evidence)


def test_lines_are_ordered_refer_then_incomplete_then_understanding_gap():
    rec = record(product(P1), product(P2))
    bel = beliefs(
        product_beliefs(P1, cover_inr=dont_know(), consent_given=NotAsked()),
        product_beliefs(P2, kind=said(KindClaim.deposit), term_months=dont_know()),
        sale_concerns=(ConcernEvidence(concern=SaleConcern.coached_answers, evidence=ev()),),
    )
    summary = summarise(rec, evaluate(rec, bel))
    assert [(line.tier, line.product_id) for line in summary.lines] == [
        (REFER, P2),
        (REFER, None),
        (INCOMPLETE, P1),
        (UNDERSTANDING, P1),
        (UNDERSTANDING, P2),
    ]
    assert summary.tier is REFER


def test_a_conflict_line_shows_every_answer_and_quotes_the_first():
    conflict = AnswerConflict(question=Question.kind, answers=(ev("FD hai", 9), ev("achha, bima", 11)))
    line = one_line(summary_of({}, {"conflicts": (conflict,)}))
    assert '"FD hai"' in line.title and '"achha, bima"' in line.title
    assert (line.quote, line.turn_id) == ("FD hai", 9)
    understanding = conflict.model_copy(update={"question": Question.term})
    line = one_line(summary_of({}, {"conflicts": (understanding,)}), UNDERSTANDING)
    assert "term" in line.title and line.quote == "FD hai"


def test_the_demo_case_is_two_refer_lines_and_one_line_per_other_tier():
    rec, bel = demo_case()
    summary = summarise(rec, evaluate(rec, bel))
    refer = lines(summary, REFER)
    assert [line.rule_ids for line in refer] == [
        (RuleId.kind, RuleId.belief_mismatch),
        (RuleId.consent, RuleId.loan_funded),
    ]
    assert [line.tier for line in summary.lines[2:]] == [INCOMPLETE, UNDERSTANDING]  # what the call never asked


BANNED = re.compile(r"mis-?sell|refund", re.IGNORECASE)


def worst_cases() -> list[tuple[LoanRecord, CaseResult]]:
    conflicts = tuple(AnswerConflict(question=q, answers=(ev("one", 9), ev("two", 11))) for q in Question)
    rec = record(
        product(P1, provider_choice_offered=False),
        product(P2, paid_from_loan=False),
        product("P3", required_for_loan=True, risk_mitigant=False),
        product("P4", cancel_window_days=None),
    )
    rec1 = record()
    denied = beliefs(
        product_beliefs(kind=dont_know(), conflicts=conflicts, payment_frequency=dont_know()),
        recall=OpenRecall(asked=True, denial=ev("kuch nahin", 3)),
    )
    empty = beliefs(product_beliefs().model_copy(update={"payment_frequency": said(PaymentFrequency.recurring)}))
    return [
        (rec, everything_flagged()),
        demo_case()[:1] + (evaluate(*demo_case()),),
        (rec1, evaluate(rec1, denied)),
        (rec1, evaluate(rec1, empty)),
        (rec1, evaluate(rec1, beliefs(product_beliefs(P1).model_copy(update={"kind": NotAsked()})))),
    ]


def test_no_line_says_a_banned_word_and_every_line_is_complete():
    seen = set()
    for rec, result in worst_cases():
        summary = summarise(rec, result)
        assert (summary.loan_id, summary.call_id, summary.tier) == (result.loan_id, result.call_id, result.tier)
        for line in summary.lines:
            assert not BANNED.search(line.title) and not BANNED.search(line.record_value)
            assert line.title[0].isupper() and line.title.endswith(".")
            assert line.record_value and line.clauses and line.rule_ids
            seen.add(line.tier)
    assert seen == {REFER, INCOMPLETE, UNDERSTANDING}


@pytest.mark.parametrize("case", range(5))
def test_every_flag_and_gap_is_in_exactly_one_line_of_its_tier(case):
    rec, result = worst_cases()[case]
    summary = summarise(rec, result)
    for product_id in [*(p.id for p in rec.products), None]:
        found = [o for o in (*result.all_flags(), *result.all_gaps()) if o.product_id == product_id]
        own = [line for line in summary.lines if line.product_id == product_id]
        for tier in Tier:
            want = {o.rule_id for o in found if o.tier is tier}
            got = {rule for line in own if line.tier is tier for rule in line.rule_ids}
            assert got == want, (product_id, tier)
        assert len([line for line in own if line.tier is INCOMPLETE]) <= 1
        assert len([line for line in own if line.tier is UNDERSTANDING]) <= 1
