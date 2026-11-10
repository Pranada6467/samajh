"""The type contract: illegal states are rejected at construction, and everything survives JSON."""

from datetime import date

import pytest
from pydantic import ValidationError

from samajh.types import (
    Beliefs,
    Borrower,
    CallStep,
    CaseResult,
    DontKnow,
    Evidence,
    Language,
    LenderType,
    LoanRecord,
    NotAsked,
    OpenRecall,
    Product,
    ProductBeliefs,
    RawExtraction,
    RawOpenRecall,
    RawProductAnswers,
    Stated,
    Transcript,
    Unclear,
    Verdict,
)

EV = {"quote": "FD hai", "turn_id": 3}


def product(**changes) -> dict:
    base = {
        "id": "P1",
        "kind": "credit_life",
        "provider": "Namoona Life (synthetic)",
        "premium_inr": 52000,
        "cover_inr": 500000,
        "term_months": 60,
        "paid_from_loan": True,
        "required_for_loan": False,
        "risk_mitigant": True,
        "provider_choice_offered": True,
        "cancel_window_days": 30,
        "features": [],
        "consent": {"method": "otp", "at": "2026-10-01"},
    }
    return base | changes


def record(products: list[dict]) -> dict:
    return {
        "loan_id": "LN-TEST-0001",
        "lender_type": "bank",
        "borrower": {"name": "Test Borrower One", "dob": "1990-01-01", "language": "hi"},
        "loan_kind": "gold",
        "sanctioned_inr": 500000,
        "disbursed_inr": 448000,
        "disbursed_on": "2026-10-01",
        "products": products,
    }


@pytest.mark.parametrize(
    "answer",
    [
        {"status": "stated", "evidence": EV},  # stated without a value
        {"status": "stated", "value": "fd", "evidence": EV},  # value outside the enum
        {"status": "stated", "value": "deposit"},  # stated without evidence
        {"status": "dont_know"},  # "does not know" without the customer's words
        {"status": "unclear", "reason": "not_asked"},  # not-asked smuggled in as unclear
        {"status": "stated", "value": "deposit", "evidence": {"quote": "", "turn_id": 3}},  # empty quote
        {"status": "not_asked", "value": "deposit"},  # not asked, yet carries a value
        {"status": "maybe"},
        None,
    ],
)
def test_illegal_answers_are_rejected(answer):
    with pytest.raises(ValidationError):
        RawProductAnswers.model_validate({"product_id": "P1", "kind": answer})


def test_the_llm_cannot_put_a_number_where_words_belong():
    with pytest.raises(ValidationError):
        RawProductAnswers.model_validate(
            {"product_id": "P1", "premium": {"status": "stated", "value": 52000, "evidence": EV}}
        )


def test_normalised_amounts_must_be_integers_even_when_built_in_python():
    evidence = Evidence(quote="bavan hazaar", turn_id=4)
    assert ProductBeliefs(product_id="P1", premium_inr=Stated(value=52000, evidence=evidence))
    with pytest.raises(ValidationError):
        ProductBeliefs(product_id="P1", premium_inr=Stated(value="bavan hazaar", evidence=evidence))


def test_every_answer_defaults_to_not_asked():
    for model in (RawProductAnswers(product_id="P1"), ProductBeliefs(product_id="P1")):
        answers = [v for k, v in model if k not in {"product_id", "volunteered_claims", "ungrounded", "conflicts"}]
        assert answers and all(a == NotAsked() for a in answers)


def test_a_product_the_call_never_covered_reads_as_not_asked():
    beliefs = Beliefs(call_id="c1", loan_id="L1", language="hi", recall=OpenRecall(asked=False), products=())
    assert beliefs.for_product("P9") == ProductBeliefs(product_id="P9")


@pytest.mark.parametrize("model", [RawOpenRecall, OpenRecall])
def test_recall_cannot_have_an_answer_to_a_question_never_asked(model):
    with pytest.raises(ValidationError):
        model.model_validate({"asked": False, "answer": EV})
    with pytest.raises(ValidationError):
        model.model_validate({"asked": False, "items": [{"evidence": EV}]})
    assert model.model_validate({"asked": True}).items == ()


def test_models_are_frozen_and_reject_unknown_fields():
    answers = RawProductAnswers(product_id="P1")
    with pytest.raises(ValidationError):
        answers.kind = DontKnow(evidence=Evidence(quote="pata nahi", turn_id=2))
    with pytest.raises(ValidationError):
        RawProductAnswers.model_validate({"product_id": "P1", "verdict": "clear"})


def test_loan_record_rejects_duplicate_product_ids_and_non_positive_amounts():
    assert LoanRecord.model_validate(record([product()])).products[0].premium_inr == 52000
    with pytest.raises(ValidationError):
        LoanRecord.model_validate(record([product(), product()]))
    with pytest.raises(ValidationError):
        Product.model_validate(product(premium_inr=0))


def test_the_record_says_which_lender_type_it_is():
    assert {t.value for t in LenderType} == {"bank", "nbfc"}
    assert LoanRecord.model_validate(record([product()]) | {"lender_type": "nbfc"}).lender_type is LenderType.nbfc
    for bad in ({"lender_type": "hfc"}, {"lender_type": None}):
        with pytest.raises(ValidationError):
            LoanRecord.model_validate(record([product()]) | bad)
    missing = record([product()])
    del missing["lender_type"]
    with pytest.raises(ValidationError):
        LoanRecord.model_validate(missing)


@pytest.mark.parametrize("field", ["risk_mitigant", "provider_choice_offered", "cancel_window_days"])
def test_the_bundling_and_cancel_fields_of_a_product_must_be_given(field):
    data = product()
    del data[field]
    with pytest.raises(ValidationError):
        Product.model_validate(data)


def test_a_product_may_have_no_cancellation_window_but_never_a_zero_one():
    assert Product.model_validate(product(cancel_window_days=None)).cancel_window_days is None
    for bad in (0, -1, "30", True):
        with pytest.raises(ValidationError):
            Product.model_validate(product(cancel_window_days=bad))


def test_call_steps_are_the_v2_flow_in_order():
    assert [step.value for step in CallStep] == [
        "right_party_check",
        "disclosure",
        "second_check",
        "context",
        "open_recall",
        "teach_back",
        "consent_check",
        "read_back",
        "close",
    ]


def test_transcript_turn_ids_must_increase():
    turn = {"speaker": "customer", "step": "open_recall", "text": "bas ek FD"}
    assert (
        Transcript.model_validate(
            {
                "call_id": "c1",
                "loan_id": "L1",
                "language": "hi-en",
                "turns": [turn | {"id": 1}, turn | {"id": 2}],
            }
        ).language
        is Language.hi_en
    )
    with pytest.raises(ValidationError):
        Transcript.model_validate(
            {
                "call_id": "c1",
                "loan_id": "L1",
                "language": "hi",
                "turns": [turn | {"id": 2}, turn | {"id": 2}],
            }
        )


def test_languages_are_exactly_the_four_in_scope():
    assert {language.value for language in Language} == {"hi", "hi-en", "ta", "kn"}


def test_raw_extraction_round_trips_through_json_and_has_a_schema():
    raw = RawExtraction.model_validate(
        {
            "call_id": "c1",
            "recall": {
                "asked": True,
                "answer": {"quote": "bas ek FD, bavan hazaar", "turn_id": 3},
                "items": [
                    {"evidence": EV, "kind": "deposit", "amount_text": "bavan hazaar", "product_id": "P1"}
                ],
            },
            "products": [
                {
                    "product_id": "P1",
                    "kind": {"status": "stated", "value": "deposit", "evidence": EV},
                    "premium": {"status": "dont_know", "evidence": {"quote": "pata nahi", "turn_id": 5}},
                    "cover": {"status": "unclear"},
                    "feature_probe": {
                        "status": "stated",
                        "value": ["refundable_anytime"],
                        "evidence": {"quote": "kabhi bhi nikal sakte hain", "turn_id": 9},
                    },
                    "volunteered_claims": [{"claim": "is_deposit", "evidence": EV}],
                }
            ],
        }
    )
    assert RawExtraction.model_validate_json(raw.model_dump_json()) == raw
    assert isinstance(raw.products[0].cover, Unclear)
    schema = RawExtraction.model_json_schema()
    assert {"recall", "products"} <= set(schema["properties"])


def test_case_result_round_trips_through_json():
    result = CaseResult.model_validate(
        {
            "loan_id": "L1",
            "call_id": "c1",
            "language": "ta",
            "verdict": "flag_for_review",
            "tier": "refer",
            "products": [
                {
                    "product_id": "P1",
                    "verdict": "flag_for_review",
                    "tier": "refer",
                    "flags": [
                        {
                            "rule_id": "kind",
                            "reason": "kind_differs",
                            "clause": "101Y",
                            "product_id": "P1",
                            "severity": "high",
                            "expected": "insurance",
                            "heard": "deposit",
                            "quote": "FD hai",
                            "turn_id": 3,
                        }
                    ],
                    "gaps": [
                        {
                            "rule_id": "term",
                            "clause": "101Y",
                            "product_id": "P1",
                            "reason": "not_asked",
                        }
                    ],
                    "passed": ["consent"],
                    "evidence_pack": {
                        "loan_id": "L1",
                        "call_id": "c1",
                        "lender_type": "nbfc",
                        "product": product(),
                        "flags": [
                            {
                                "rule_id": "kind",
                                "reason": "kind_differs",
                                "clause": "101Y",
                                "product_id": "P1",
                                "severity": "high",
                                "expected": "insurance",
                                "heard": "deposit",
                                "quote": "FD hai",
                                "turn_id": 3,
                            }
                        ],
                    },
                }
            ],
        }
    )
    assert CaseResult.model_validate_json(result.model_dump_json()) == result
    assert result.verdict is Verdict.flag_for_review
    (pack,) = result.evidence_packs()
    assert pack.quotes() == (Evidence(quote="FD hai", turn_id=3),)
    assert pack.clauses() == ("101Y",)


def _stated(value) -> dict:
    return {"status": "stated", "value": value, "evidence": EV}


@pytest.mark.parametrize(
    "model, data",
    [
        (Product, product(premium_inr=True)),
        (Product, product(premium_inr="52000")),
        (Product, product(paid_from_loan="no")),
        (Evidence, {"quote": "   ", "turn_id": 3}),
        (Evidence, {"quote": "haan", "turn_id": True}),
        (ProductBeliefs, {"product_id": "P1", "premium_inr": _stated(True)}),
        (Product, product(risk_mitigant="yes")),
        (Product, product(provider_choice_offered=1)),
        (ProductBeliefs, {"product_id": "P1", "consent_given": _stated("no")}),
        (ProductBeliefs, {"product_id": "P1", "consent_given": _stated(1)}),
        (ProductBeliefs, {"product_id": "P1", "provider_choice_offered": _stated("yes")}),
        (ProductBeliefs, {"product_id": "P1", "consent_method": _stated("thumbprint")}),
        (ProductBeliefs, {"product_id": "P1", "cancel_window_days": _stated("30")}),
        (RawProductAnswers, {"product_id": "P1", "cancel_window": _stated(30)}),
    ],
)
def test_values_are_not_coerced_from_other_types(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_borrower_dates_parse():
    assert Borrower(name="Test Borrower One", dob="1990-01-01", language="kn").dob == date(1990, 1, 1)
