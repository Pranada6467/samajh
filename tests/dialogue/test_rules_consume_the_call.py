"""A finished call goes into `samajh.rules` unchanged: every question is tagged so answers ground."""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, play, product, record

from samajh.dialogue import PRODUCT_QUESTIONS
from samajh.rules import evaluate, to_beliefs
from samajh.types import (
    CallStep,
    GapReason,
    Language,
    Question,
    RawExtraction,
    RuleId,
    Speaker,
    Transcript,
    Verdict,
)

HI = Language.hi
CONSENT = {"method": "signed_form", "at": "2026-10-20"}


def reply_to(transcript: Transcript, asks: Question, *, read_back: bool = False, last: bool = False) -> dict:
    """Evidence for the customer's reply to the bot turn that asked `asks`: the whole reply, quoted."""
    found = [
        (turn, transcript.turns[k + 1])
        for k, turn in enumerate(transcript.turns[:-1])
        if turn.speaker is Speaker.bot
        and turn.asks is asks
        and (turn.step is CallStep.read_back) == read_back
    ]
    _, reply = found[-1] if last else found[0]
    assert reply.speaker is Speaker.customer
    return {"quote": reply.text, "turn_id": reply.id}


def stated(value, evidence: dict) -> dict:
    return {"status": "stated", "value": value, "evidence": evidence}


def extraction(
    transcript: Transcript, *, premium_words: str, premium_from_read_back: bool = False
) -> RawExtraction:
    """What a faithful extractor would return for the scripted Hindi customer (an FD, paid from the loan)."""
    recall = next(
        t for t in transcript.turns if t.speaker is Speaker.customer and t.step is CallStep.open_recall
    )

    def r(asks: Question, **where) -> dict:
        return reply_to(transcript, asks, **where)

    premium = r(Question.premium, read_back=True) if premium_from_read_back else r(Question.premium)
    answers = {
        "product_id": "P1",
        "kind": stated("deposit", r(Question.kind)),
        "premium": stated(premium_words, premium),
        "premium_readback": stated(True, r(Question.premium, read_back=True, last=True)),
        "payment_source": stated("from_loan", r(Question.payment_source)),
        "required_for_loan": stated(True, r(Question.required_for_loan)),
        "provider_choice_offered": stated(False, r(Question.provider_choice)),
        "cover": {"status": "unclear", "evidence": r(Question.cover)},
        "term": stated("दो साल", r(Question.term)),
        "cancel_allowed": stated(False, r(Question.cancel_window)),
        "cancel_window": {"status": "unclear", "evidence": r(Question.cancel_window)},
        "consent_given": stated(True, r(Question.consent)),
        "consent_method": stated("signed_form", r(Question.consent)),
        "feature_probe": stated(["withdrawable_after_period"], r(Question.features)),
    }
    return RawExtraction.model_validate(
        {
            "call_id": transcript.call_id,
            "recall": {
                "asked": True,
                "answer": {"quote": recall.text, "turn_id": recall.id},
                "items": [
                    {
                        "evidence": {"quote": "एफडी", "turn_id": recall.id},
                        "kind": "deposit",
                        "product_id": "P1",
                    }
                ],
            },
            "products": [answers],
        }
    )


def test_every_rule_finds_its_question_asked_and_its_answer_grounded():
    rec = record(product(consent=CONSENT))
    transcript = play(rec, HI, CUSTOMERS[HI].happy()).end.transcript
    result = evaluate(rec, to_beliefs(extraction(transcript, premium_words="बावन हज़ार"), rec, transcript))

    reasons = {gap.reason for gap in result.all_gaps()}
    assert not reasons & {GapReason.not_asked, GapReason.quote_not_grounded, GapReason.readback_mismatch}
    assert result.verdict is Verdict.flag_for_review
    flagged = {flag.rule_id for flag in result.all_flags()}
    assert {RuleId.kind, RuleId.bundling, RuleId.belief_mismatch} <= flagged
    assert RuleId.premium not in flagged  # 52,000 said, read back and confirmed against 52,000 on record
    assert RuleId.premium in result.products[0].passed


def test_a_premium_corrected_at_read_back_is_the_one_the_rules_compare():
    customer = CUSTOMERS[HI]
    rec = record(product(premium_inr=55000, consent=CONSENT))
    k = customer.happy().index(customer.confirm)  # the read-back follows the premium answer
    replies = customer.happy()
    replies[k : k + 1] = [customer.correction, customer.confirm]
    transcript = play(rec, HI, replies).end.transcript
    raw = extraction(transcript, premium_words="पचपन हज़ार", premium_from_read_back=True)
    result = evaluate(rec, to_beliefs(raw, rec, transcript))

    assert RuleId.premium in result.products[0].passed
    assert not [gap for gap in result.all_gaps() if gap.rule_id is RuleId.premium]


def test_a_call_that_ends_early_reads_as_not_asked_never_as_clear():
    rec = record(product(consent=CONSENT))
    customer = CUSTOMERS[HI]
    transcript = play(rec, HI, customer.happy()[:6] + [customer.decline]).end.transcript
    raw = RawExtraction.model_validate(
        {"call_id": transcript.call_id, "recall": {"asked": True}, "products": [{"product_id": "P1"}]}
    )
    result = evaluate(rec, to_beliefs(raw, rec, transcript))
    assert result.verdict is not Verdict.clear
    assert GapReason.not_asked in {gap.reason for gap in result.all_gaps()}


@pytest.mark.parametrize("language", list(Language))
def test_a_full_call_asks_everything_the_rules_need_for_clear(language):
    """W1 report section 3: recall, the nine product questions, consent, and a premium read-back."""
    transcript = play(record(), language, CUSTOMERS[language].happy()).end.transcript
    bot = [t for t in transcript.turns if t.speaker is Speaker.bot]
    assert any(t.step is CallStep.open_recall for t in bot)
    for question in PRODUCT_QUESTIONS:
        assert any(t.asks is question and t.product_id == "P1" and t.step is CallStep.teach_back for t in bot)
    assert any(t.asks is Question.consent and t.product_id is None for t in bot)
    assert any(
        t.asks is Question.premium and t.step is CallStep.read_back and t.product_id == "P1" for t in bot
    )
