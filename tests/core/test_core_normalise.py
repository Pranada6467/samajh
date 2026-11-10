"""RawExtraction -> Beliefs -> CaseResult, end to end on a transcript.

Each test starts from one compliant Hindi call (verdict `clear`) and changes what the customer
said, what the extraction claims, or both. A sloppy or hallucinating extraction must never
turn a customer who was misled, or who was not asked, into `clear`.
"""

import pytest

from samajh.rules import evaluate, to_beliefs
from samajh.types import (
    CaseResult,
    DontKnow,
    Evidence,
    GapReason,
    LoanRecord,
    NotAsked,
    RawExtraction,
    RuleId,
    Stated,
    Transcript,
    Unclear,
    Verdict,
)

BOT, CUSTOMER = "bot", "customer"
CLEAR, FLAGGED, UNCLEAR = Verdict.clear, Verdict.flag_for_review, Verdict.unclear_needs_human

# (id, speaker, step, text, question the bot turn asks). One credit-life product, P1.
TURNS = [
    (1, BOT, "open_recall", "लोन के साथ आपने क्या-क्या लिया, और कितने का?", None),
    (2, CUSTOMER, "open_recall", "लोन के साथ एक बीमा लिया था, बावन हज़ार का।", None),
    (3, BOT, "teach_back", "यह बीमा है, एफ़डी है या कुछ और?", "kind"),
    (4, CUSTOMER, "teach_back", "यह बीमा है।", None),
    (5, BOT, "teach_back", "इसकी कीमत कितनी थी?", "premium"),
    (6, CUSTOMER, "teach_back", "बावन हज़ार रुपये।", None),
    (7, BOT, "read_back", "बावन हज़ार, यानी 52,000, सही है?", "premium"),
    (8, CUSTOMER, "read_back", "हाँ, सही है।", None),
    (9, BOT, "teach_back", "पैसे कैसे दिए?", "payment_source"),
    (10, CUSTOMER, "teach_back", "लोन की रकम से कटे थे।", None),
    (11, BOT, "teach_back", "क्या यह लोन के लिए ज़रूरी था?", "required_for_loan"),
    (12, CUSTOMER, "teach_back", "नहीं, मेरी मर्ज़ी से लिया।", None),
    (13, BOT, "teach_back", "कितने का कवर है?", "cover"),
    (14, CUSTOMER, "teach_back", "5,00,000 का कवर है।", None),
    (15, BOT, "teach_back", "कितने समय के लिए?", "term"),
    (16, CUSTOMER, "teach_back", "पाँच साल के लिए।", None),
    (17, BOT, "teach_back", "क्या आपको बताया गया था कि इसे रद्द कर सकते हैं या नहीं, और कब तक?", "cancel_window"),
    (18, CUSTOMER, "teach_back", "हाँ, तीस दिन के अंदर रद्द कर सकते हैं।", None),
    (19, BOT, "teach_back", "अगर आप यह पैसा वापस लेना चाहें तो क्या होगा?", "features"),
    (20, CUSTOMER, "teach_back", "यह बीमा है, पैसा वापस नहीं मिलता।", None),
    (21, BOT, "teach_back", "क्या आपको बताया गया था कि यह बीमा किसी और कंपनी से भी ले सकते हैं?", "provider_choice"),
    (22, CUSTOMER, "teach_back", "हाँ, बताया था।", None),
    (23, BOT, "consent_check", "लोन लेते समय आपने क्या-क्या लेने की सहमति दी थी, और कैसे?", "consent"),
    (24, CUSTOMER, "consent_check", "बीमा लेने की हाँ की थी, मोबाइल पर ओटीपी आया था।", None),
]


def transcript(turns=TURNS, tagged=True) -> Transcript:
    return Transcript.model_validate(
        {
            "call_id": "c1",
            "loan_id": "LN-TEST-0001",
            "language": "hi",
            "turns": [
                {"id": i, "speaker": who, "step": step, "text": text}
                | ({"asks": asks} if asks and tagged else {})
                # the consent question is open and names no product
                | ({"product_id": "P1"} if asks and tagged and asks != "consent" else {})
                for i, who, step, text, asks in turns
            ],
        }
    )


def swap(changes: dict[int, str]) -> Transcript:
    """The compliant call with the text of some turns replaced."""
    return transcript([(i, who, step, changes.get(i, text), asks) for i, who, step, text, asks in TURNS])


def record(**product_changes) -> LoanRecord:
    product = {
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
    } | product_changes
    return LoanRecord.model_validate(
        {
            "loan_id": "LN-TEST-0001",
            "lender_type": "bank",
            "borrower": {"name": "Test Borrower One", "dob": "1990-01-01", "language": "hi"},
            "loan_kind": "gold",
            "sanctioned_inr": 500000,
            "disbursed_inr": 448000,
            "disbursed_on": "2026-10-01",
            "products": [product],
        }
    )


def stated(value, quote, turn_id) -> dict:
    return {"status": "stated", "value": value, "evidence": {"quote": quote, "turn_id": turn_id}}


def dont_know(quote, turn_id) -> dict:
    return {"status": "dont_know", "evidence": {"quote": quote, "turn_id": turn_id}}


def answers(**changes) -> dict:
    base = {
        "product_id": "P1",
        "kind": stated("insurance", "यह बीमा है", 4),
        "premium": stated("बावन हज़ार", "बावन हज़ार रुपये", 6),
        "premium_readback": stated(True, "हाँ, सही है", 8),
        "payment_source": stated("from_loan", "लोन की रकम से कटे थे", 10),
        "required_for_loan": stated(False, "नहीं, मेरी मर्ज़ी से लिया", 12),
        "cover": stated("5,00,000", "5,00,000 का कवर है", 14),
        "term": stated("पाँच साल", "पाँच साल के लिए", 16),
        "cancel_allowed": stated(True, "तीस दिन के अंदर रद्द कर सकते हैं", 18),
        "cancel_window": stated("तीस दिन", "तीस दिन के अंदर रद्द कर सकते हैं", 18),
        "feature_probe": stated([], "पैसा वापस नहीं मिलता", 20),
        "provider_choice_offered": stated(True, "हाँ, बताया था", 22),
        "consent_given": stated(True, "बीमा लेने की हाँ की थी", 24),
        "consent_method": stated("otp", "मोबाइल पर ओटीपी आया था", 24),
    }
    return {k: v for k, v in (base | changes).items() if v is not None}


RECALL = {
    "asked": True,
    "answer": {"quote": "लोन के साथ एक बीमा लिया था, बावन हज़ार का।", "turn_id": 2},
    "items": [
        {
            "evidence": {"quote": "एक बीमा लिया था, बावन हज़ार का", "turn_id": 2},
            "kind": "insurance",
            "amount_text": "बावन हज़ार",
            "product_id": "P1",
        }
    ],
}


def raw(recall=RECALL, sale_concerns=(), **changes) -> RawExtraction:
    return RawExtraction.model_validate(
        {"call_id": "c1", "recall": recall, "products": [answers(**changes)], "sale_concerns": sale_concerns}
    )


def judge(
    extraction: RawExtraction, call: Transcript | None = None, loan: LoanRecord | None = None
) -> CaseResult:
    loan = loan or record()
    return evaluate(loan, to_beliefs(extraction, loan, call or transcript()))


def product_gaps(result: CaseResult) -> set[tuple[RuleId, GapReason]]:
    return {(g.rule_id, g.reason) for g in result.products[0].gaps}


# --- the compliant call --------------------------------------------------------


def test_a_grounded_compliant_call_normalises_and_comes_out_clear():
    beliefs = to_beliefs(raw(), record(), transcript())
    product = beliefs.for_product("P1")
    assert product.premium_inr == Stated(value=52000, evidence=Evidence(quote="बावन हज़ार रुपये", turn_id=6))
    assert product.premium_readback.value is True
    assert product.cover_inr.value == 500000
    assert product.term_months.value == 60
    assert product.cancel_window_days.value == 30
    assert (product.consent_given.value, product.consent_method.value) == (True, "otp")
    assert beliefs.recall.items[0].amount_inr == 52000
    assert (beliefs.loan_id, beliefs.language) == ("LN-TEST-0001", "hi")
    assert not product.ungrounded and not beliefs.ungrounded
    result = evaluate(record(), beliefs)
    assert result.verdict is CLEAR
    assert not result.all_flags() and not result.all_gaps()


def test_grounding_ignores_case_punctuation_and_spacing_only():
    assert judge(raw(premium=stated("बावन  हज़ार", "बावन हज़ार   रुपये!", 6))).verdict is CLEAR
    assert judge(raw(kind=stated("insurance", "यह बीमा नहीं है", 4))).verdict is UNCLEAR


def test_the_number_comes_from_the_parser_not_from_the_llm():
    """Digits the LLM wrote itself are accepted only because the parser reads the same from the turn."""
    assert judge(raw(premium=stated("52000", "बावन हज़ार रुपये", 6))).verdict is CLEAR
    wrong = judge(raw(premium=stated("25000", "बावन हज़ार रुपये", 6)))
    assert product_gaps(wrong) == {(RuleId.premium, GapReason.value_not_parsed)}


# --- quotes that the transcript does not support ---------------------------------


@pytest.mark.parametrize(
    "premium",
    [
        stated("बावन हज़ार", "बावन हज़ार रुपये दिए थे मैंने", 6),  # words the customer never said
        stated("बावन हज़ार", "बावन हज़ार रुपये", 5),  # cites the bot's question
        stated("बावन हज़ार", "बावन हज़ार रुपये", 99),  # cites a turn that does not exist
        stated("बावन हज़ार", "बावन हज़ार, यानी 52,000", 7),  # the bot's read-back, not the customer
        stated("बावन हज़ार", "बावन हज़ार का", 2),  # said in open recall, not in reply to the premium question
        dont_know("पता नहीं", 6),  # an invented "do not know"
    ],
)
def test_an_answer_the_transcript_does_not_support_is_a_gap_never_a_pass(premium):
    result = judge(raw(premium=premium))
    assert product_gaps(result) == {(RuleId.premium, GapReason.quote_not_grounded)}
    assert result.verdict is UNCLEAR


def test_a_yes_from_another_question_does_not_confirm_a_rejected_read_back():
    call = swap({8: "नहीं, इतना नहीं था।"})
    result = judge(raw(premium_readback=stated(True, "हाँ", 18)), call)
    assert product_gaps(result) == {(RuleId.premium, GapReason.quote_not_grounded)}
    assert result.verdict is UNCLEAR


def test_answers_to_questions_the_bot_never_asked_do_not_count():
    """The call was cut off after the read-back; the extraction answers everything with that 'yes'."""
    cut_off = transcript(
        [
            t if t[0] != 2 else (2, CUSTOMER, "open_recall", "पाँच लाख के लोन के साथ एक बीमा, पाँच साल का।", None)
            for t in TURNS
            if t[0] <= 8
        ]
    )
    extraction = raw(
        recall={
            "asked": True,
            "items": [{"evidence": {"quote": "एक बीमा", "turn_id": 2}, "product_id": "P1"}],
        },
        payment_source=stated("from_loan", "हाँ", 8),
        required_for_loan=stated(False, "लोन", 2),
        cover=stated("पाँच लाख", "पाँच लाख", 2),
        term=stated("पाँच साल", "पाँच साल", 2),
        cancel_allowed=stated(True, "हाँ", 8),
        cancel_window=None,
        feature_probe=stated([], "हाँ", 8),
        provider_choice_offered=stated(True, "हाँ", 8),
        consent_given=stated(True, "हाँ", 8),
        consent_method=None,
    )
    result = judge(extraction, cut_off)
    assert result.verdict is UNCLEAR
    assert {rule for rule, _ in product_gaps(result)} == {
        RuleId.loan_funded,
        RuleId.bundling,
        RuleId.cover,
        RuleId.term,
        RuleId.cancel_window,
        RuleId.belief_mismatch,
        RuleId.consent,
    }


def test_an_untagged_transcript_cannot_support_any_answer():
    result = judge(raw(), transcript(tagged=False))
    assert result.verdict is UNCLEAR
    assert RuleId.premium not in result.products[0].passed
    assert not result.products[0].flags


@pytest.mark.parametrize(
    "kind, said",
    [
        (stated("insurance", "यह बीमा है", 4), "एफ़डी है।"),  # the customer said FD; the LLM kept an old quote
        (dont_know("मुझे पता नहीं", 4), "पता नहीं जी, कुछ कागज़ पर साइन कराए थे।"),  # paraphrased quote
    ],
)
def test_an_unsupported_kind_answer_is_not_rescued_by_recall(kind, said):
    result = judge(raw(kind=kind), swap({4: said}))
    assert (RuleId.kind, GapReason.quote_not_grounded) in product_gaps(result)
    assert result.verdict is UNCLEAR


def test_dont_know_with_the_customers_real_words_is_a_flag():
    call = swap({4: "पता नहीं जी, कुछ कागज़ पर साइन कराए थे।"})
    beliefs = to_beliefs(raw(kind=dont_know("पता नहीं जी", 4)), record(), call)
    assert isinstance(beliefs.for_product("P1").kind, DontKnow)
    assert evaluate(record(), beliefs).verdict is FLAGGED


# --- amounts and terms ----------------------------------------------------------


@pytest.mark.parametrize(
    "said, span",
    [
        ("1,52,000 रुपये।", "52,000"),  # the span is the tail of a larger amount
        ("एक लाख बावन हज़ार रुपये।", "बावन हज़ार"),
        ("बावन हज़ार नहीं, पचपन हज़ार।", "बावन हज़ार"),  # the customer corrected themselves
        ("बावन हज़ार महीने का, पाँच साल तक।", "बावन हज़ार"),
        ("पता नहीं, शायद कुछ हज़ार।", "हज़ार"),
    ],
)
def test_a_premium_reply_that_is_not_one_clear_amount_is_a_gap(said, span):
    result = judge(raw(premium=stated(span, said, 6)), swap({6: said}))
    assert product_gaps(result) == {(RuleId.premium, GapReason.value_not_parsed)}
    assert result.verdict is UNCLEAR


def test_a_spoken_range_far_from_the_record_is_read_and_differs():
    said = "दो तीन लाख होगा।"
    call = swap({6: said, 7: "दो से तीन लाख, यानी 2,00,000 से 3,00,000, सही है?"})
    result = judge(raw(premium=stated("दो तीन लाख", said, 6)), call)
    (flag,) = result.all_flags()
    assert (flag.reason.value, flag.heard) == ("premium_differs_confirmed", "customer said ₹2,00,000 to ₹3,00,000")
    assert result.tier.value == "refer"


def test_a_cover_span_that_drops_the_fraction_word_is_a_gap():
    """The pilot's dropped "पौने", made by the extraction instead of the recogniser. Cover has no read-back."""
    call = swap({14: "पौने पाँच लाख का कवर है।"})
    result = judge(raw(cover=stated("पाँच लाख", "पौने पाँच लाख का कवर है", 14)), call)
    assert product_gaps(result) == {(RuleId.cover, GapReason.value_not_parsed)}
    truncated = judge(raw(cover=stated("पाँच लाख", "पाँच लाख का कवर है", 14)), call)
    assert product_gaps(truncated) == {(RuleId.cover, GapReason.quote_not_grounded)}
    honest = judge(raw(cover=stated("पौने पाँच लाख", "पौने पाँच लाख का कवर है", 14)), call)
    assert [(f.rule_id, f.heard) for f in honest.products[0].flags] == [
        (RuleId.cover, "customer said ₹4,75,000")
    ]


def test_an_amount_in_words_the_parser_does_not_know_is_a_gap_not_a_guess():
    call = swap({14: "dedh lakh ka cover hai."})
    result = judge(
        raw(cover=stated("dedh lakh", "dedh lakh ka cover hai", 14)), call, record(cover_inr=100000)
    )
    assert product_gaps(result) == {(RuleId.cover, GapReason.value_not_parsed)}


@pytest.mark.parametrize(
    "said, span, outcome",
    [
        ("पाँच साल, 60 महीने।", "पाँच साल", "passed"),  # the same term said twice
        ("डेढ़ साल के लिए।", "डेढ़ साल", "flag"),  # 18 months against a 60-month record
        ("पाँच से छह साल।", "पाँच", "gap"),
        ("बहुत लंबा है।", "लंबा", "gap"),
    ],
)
def test_term_is_read_from_the_whole_reply(said, span, outcome):
    result = judge(raw(term=stated(span, said.rstrip("।"), 16)), swap({16: said}))
    product = result.products[0]
    assert (RuleId.term in product.passed) is (outcome == "passed")
    assert bool([f for f in product.flags if f.rule_id is RuleId.term]) is (outcome == "flag")
    assert bool([g for g in product.gaps if g.rule_id is RuleId.term]) is (outcome == "gap")


# --- read-back -------------------------------------------------------------------


def test_the_pilot_recognition_miss_is_caught_by_read_back():
    """Pilot item hi08: the customer said 1,75,000 but Prisma heard 2,00,000.

    Here the record says 2,00,000, so the misheard amount matches the record by accident.
    Only the customer's "no" to the read-back shows that it is not what they said.
    """
    heard = stated("2,00,000", "उन्होंने 2,00,000 रुपये जमा किए", 6)
    loan = record(premium_inr=200000)
    said = {6: "उन्होंने 2,00,000 रुपये जमा किए।", 7: "दो लाख, यानी 2,00,000, सही है?"}

    rejected = judge(
        raw(premium=heard, premium_readback=stated(False, "नहीं, गलत है", 8)),
        swap(said | {8: "नहीं, गलत है।"}),
        loan,
    )
    assert product_gaps(rejected) == {(RuleId.premium, GapReason.readback_rejected)}
    assert rejected.verdict is UNCLEAR

    confirmed = judge(raw(premium=heard), swap(said), loan)
    assert confirmed.verdict is CLEAR

    no_readback = transcript([(i, w, s, said.get(i, t), a) for i, w, s, t, a in TURNS if i not in (7, 8)])
    unconfirmed = judge(raw(premium=heard, premium_readback=None), no_readback, loan)
    assert product_gaps(unconfirmed) == {(RuleId.premium, GapReason.not_asked)}
    assert unconfirmed.verdict is UNCLEAR


def test_a_yes_to_a_read_back_of_another_amount_confirms_nothing():
    call = swap({7: "पचपन हज़ार, यानी 55,000, सही है?"})
    result = judge(raw(), call)
    assert product_gaps(result) == {(RuleId.premium, GapReason.readback_mismatch)}
    assert result.verdict is UNCLEAR


def test_a_question_the_bot_asked_cannot_read_as_not_asked():
    product = to_beliefs(raw(kind=None, premium_readback=None), record(), transcript()).for_product("P1")
    assert product.kind == Unclear()
    assert product.premium_readback == Unclear()
    never_asked = transcript([t for t in TURNS if t[0] not in (3, 4)])
    assert to_beliefs(raw(kind=None), record(), never_asked).for_product("P1").kind == NotAsked()


# --- open recall -----------------------------------------------------------------


def test_recall_counts_only_what_was_said_in_reply_to_the_recall_question():
    """The customer named nothing unprompted; the extraction cites the prompted teach-back answer."""
    recall = {
        "asked": True,
        "items": [
            {"evidence": {"quote": "यह बीमा है", "turn_id": 4}, "kind": "insurance", "product_id": "P1"}
        ],
    }
    beliefs = to_beliefs(raw(recall=recall), record(), swap({2: "कुछ नहीं लिया, बस लोन।"}))
    assert beliefs.recall.items == ()
    result = evaluate(record(), beliefs)
    assert [f.rule_id for f in result.products[0].flags] == [RuleId.recall]
    assert (RuleId.evidence, GapReason.quote_not_grounded) in product_gaps(result)
    assert result.verdict is FLAGGED


def test_recall_the_transcript_does_not_contain_was_not_asked():
    no_recall = transcript([t for t in TURNS if t[0] > 2])
    beliefs = to_beliefs(raw(), record(), no_recall)
    assert beliefs.recall.asked is False and beliefs.recall.items == ()
    result = evaluate(record(), beliefs)
    assert (RuleId.recall, GapReason.not_asked) in product_gaps(result)
    assert result.verdict is UNCLEAR


def test_an_ungrounded_claim_or_recall_item_blocks_clear_instead_of_vanishing():
    claim = {"claim": "refundable_anytime", "evidence": {"quote": "कभी भी निकाल सकते हैं", "turn_id": 20}}
    beliefs = to_beliefs(raw(volunteered_claims=[claim]), record(), transcript())
    product = beliefs.for_product("P1")
    assert product.volunteered_claims == ()
    assert product.ungrounded == (Evidence(quote="कभी भी निकाल सकते हैं", turn_id=20),)
    assert evaluate(record(), beliefs).verdict is UNCLEAR

    invented = {"evidence": {"quote": "एक एफ़डी भी खोली", "turn_id": 2}, "kind": "deposit"}
    recall = RECALL | {"items": [*RECALL["items"], invented, invented | {"product_id": "P1"}]}
    beliefs = to_beliefs(raw(recall=recall), record(), transcript())
    assert len(beliefs.recall.items) == 1
    assert len(beliefs.ungrounded) == 1 and len(beliefs.for_product("P1").ungrounded) == 1
    assert evaluate(record(), beliefs).verdict is UNCLEAR


# --- beliefs and concerns the customer volunteers --------------------------------


def test_a_grounded_feature_claim_is_flagged():
    call = swap({20: "कभी भी निकाल सकते हैं।"})
    result = judge(raw(feature_probe=stated(["refundable_anytime"], "कभी भी निकाल सकते हैं", 20)), call)
    assert result.verdict is FLAGGED
    assert [f.rule_id for f in result.products[0].flags] == [RuleId.belief_mismatch]


def test_a_customer_told_to_say_yes_to_everything_is_flagged_though_every_answer_is_right():
    turns = [*TURNS, (25, CUSTOMER, "close", "एजेंट ने कहा था कि सब में हाँ बोलना।", None)]
    concern = {"concern": "coached_answers", "evidence": {"quote": "सब में हाँ बोलना", "turn_id": 25}}
    result = judge(raw(sale_concerns=[concern]), transcript(turns))
    assert [(f.rule_id, f.quote) for f in result.case_flags] == [(RuleId.sale_conduct, "सब में हाँ बोलना")]
    assert result.verdict is FLAGGED

    invented = judge(raw(sale_concerns=[concern]))
    assert [(g.rule_id, g.reason) for g in invented.case_gaps] == [
        (RuleId.evidence, GapReason.quote_not_grounded)
    ]
    assert invented.verdict is UNCLEAR


# --- cancel window: an open question compared with the record ---------------------


def cancel_outcome(result: CaseResult) -> str:
    product = result.products[0]
    if RuleId.cancel_window in product.passed:
        return "passed"
    if any(f.rule_id is RuleId.cancel_window for f in product.flags):
        return "flag"
    return "gap"


@pytest.mark.parametrize(
    "said, allowed, window, outcome",
    [
        ("हाँ, एक महीने के अंदर।", stated(True, "हाँ", 18), stated("एक महीने", "एक महीने के अंदर", 18), "passed"),
        ("हाँ, 30 दिन, यानी एक महीना।", stated(True, "हाँ", 18), stated("30 दिन", "30 दिन", 18), "passed"),
        ("हाँ, पंद्रह दिन में।", stated(True, "हाँ", 18), stated("पंद्रह दिन", "पंद्रह दिन में", 18), "flag"),
        ("नहीं, ऐसा कुछ नहीं बताया।", stated(False, "ऐसा कुछ नहीं बताया", 18), None, "flag"),
        ("पता नहीं।", dont_know("पता नहीं", 18), None, "flag"),
        ("हाँ, पर कब तक यह पता नहीं।", stated(True, "हाँ", 18), dont_know("पर कब तक यह पता नहीं", 18), "flag"),
        # can be cancelled, but no "by when" the parser can read: a person has to listen
        ("हाँ, कर सकते हैं।", stated(True, "हाँ, कर सकते हैं", 18), None, "gap"),
        ("हाँ, कुछ दिन में।", stated(True, "हाँ", 18), stated("कुछ दिन", "कुछ दिन में", 18), "gap"),
        ("हाँ, 15 से 30 दिन में।", stated(True, "हाँ", 18), stated("30 दिन", "30 दिन में", 18), "gap"),
        # the extraction's span says 30 days; the customer said 15
        ("हाँ, पंद्रह दिन में।", stated(True, "हाँ", 18), stated("30 दिन", "पंद्रह दिन में", 18), "gap"),
    ],
)
def test_the_cancel_answer_is_compared_with_the_window_on_record(said, allowed, window, outcome):
    result = judge(raw(cancel_allowed=allowed, cancel_window=window), swap({18: said}))
    assert cancel_outcome(result) == outcome
    assert result.verdict is {"passed": CLEAR, "flag": FLAGGED, "gap": UNCLEAR}[outcome]


def test_a_customer_told_of_a_cancel_right_the_record_does_not_show_is_flagged():
    loan = record(cancel_window_days=None)
    assert cancel_outcome(judge(raw(), loan=loan)) == "flag"
    not_told = raw(cancel_allowed=stated(False, "ऐसा कुछ नहीं बताया", 18), cancel_window=None)
    assert judge(not_told, swap({18: "नहीं, ऐसा कुछ नहीं बताया।"}), loan).verdict is CLEAR


# --- consent: an open question, never cleared by the record alone -----------------


def test_a_consent_record_does_not_clear_a_customer_who_only_remembers_the_loan_papers():
    call = swap({24: "मैंने तो बस लोन के कागज़ों पर साइन किए थे, और कुछ नहीं लिया।"})
    extraction = raw(
        consent_given=stated(False, "मैंने तो बस लोन के कागज़ों पर साइन किए थे, और कुछ नहीं लिया", 24),
        consent_method=stated("signed_form", "मैंने तो बस लोन के कागज़ों पर साइन किए थे", 24),
    )
    result = judge(extraction, call)
    assert [(f.rule_id, f.severity, f.clause) for f in result.products[0].flags] == [
        (RuleId.consent, "high", "85G")
    ]
    assert result.products[0].evidence_pack.quotes() == (
        Evidence(quote="मैंने तो बस लोन के कागज़ों पर साइन किए थे, और कुछ नहीं लिया", turn_id=24),
    )
    assert result.verdict is FLAGGED


def test_agreeing_in_a_way_the_record_does_not_show_is_flagged():
    call = swap({24: "बीमा लेने की हाँ की थी, फ़ॉर्म पर साइन किया था।"})
    extraction = raw(consent_method=stated("signed_form", "फ़ॉर्म पर साइन किया था", 24))
    result = judge(extraction, call)
    assert [(f.rule_id, f.severity) for f in result.products[0].flags] == [(RuleId.consent, "medium")]


@pytest.mark.parametrize("given", [None, stated(True, "हाँ, सही है", 8), stated(True, "ओटीपी आया था", 99)])
def test_a_consent_answer_the_call_does_not_support_is_a_gap_whatever_the_record_holds(given):
    result = judge(raw(consent_given=given, consent_method=None))
    assert RuleId.consent in {rule for rule, _ in product_gaps(result)}
    assert RuleId.consent not in result.products[0].passed
    assert result.verdict is UNCLEAR


def test_the_consent_question_was_not_asked_when_the_call_has_none():
    no_consent_step = transcript([t for t in TURNS if t[0] <= 22])
    result = judge(raw(), no_consent_step)
    assert (RuleId.consent, GapReason.quote_not_grounded) in product_gaps(result)
    silent = judge(raw(consent_given=None, consent_method=None), no_consent_step)
    assert (RuleId.consent, GapReason.not_asked) in product_gaps(silent)
    assert silent.verdict is UNCLEAR


def test_one_open_consent_question_counts_for_every_product_on_the_record():
    loan = record()
    second = loan.products[0].model_copy(update={"id": "P2"})
    loan = loan.model_copy(update={"products": (loan.products[0], second)})
    extraction = RawExtraction.model_validate(
        {
            "call_id": "c1",
            "recall": RECALL,
            "products": [
                answers(),
                {
                    "product_id": "P2",
                    "consent_given": stated(False, "बीमा लेने की हाँ की थी", 24),
                    "kind": stated("insurance", "यह बीमा है", 4),  # replies to a question about P1
                },
            ],
        }
    )
    beliefs = to_beliefs(extraction, loan, transcript())
    assert beliefs.for_product("P1").consent_given.value is True
    p2 = beliefs.for_product("P2")
    assert p2.consent_given.value is False
    assert p2.kind == Unclear(reason=GapReason.quote_not_grounded, evidence=Evidence(quote="यह बीमा है", turn_id=4))


# --- bundling: required, risk mitigant, choice of provider ------------------------

REQUIRED_SAID = {12: "हाँ, बोला था कि लोन के लिए लेना ही पड़ेगा।"}
REQUIRED = stated(True, "बोला था कि लोन के लिए लेना ही पड़ेगा", 12)


def bundling_flags(result: CaseResult) -> list[str]:
    return [f.heard for f in result.products[0].flags if f.rule_id is RuleId.bundling]


def test_a_required_risk_mitigant_offered_with_a_choice_of_provider_is_clear():
    result = judge(raw(required_for_loan=REQUIRED), swap(REQUIRED_SAID), record(required_for_loan=True))
    assert result.verdict is CLEAR
    assert RuleId.bundling in result.products[0].passed
    told_only = judge(raw(required_for_loan=REQUIRED), swap(REQUIRED_SAID))  # the record says optional
    assert told_only.verdict is CLEAR


def test_a_required_product_the_customer_could_not_buy_elsewhere_is_flagged():
    call = swap(REQUIRED_SAID | {22: "नहीं, किसी और कंपनी का नहीं बताया।"})
    extraction = raw(
        required_for_loan=REQUIRED,
        provider_choice_offered=stated(False, "किसी और कंपनी का नहीं बताया", 22),
    )
    for loan in (record(required_for_loan=True), record()):
        result = judge(extraction, call, loan)
        (flag,) = [f for f in result.products[0].flags if f.rule_id is RuleId.bundling]
        assert (flag.clause, flag.quote, flag.turn_id) == ("85V", "किसी और कंपनी का नहीं बताया", 22)
        assert result.products[0].evidence_pack is not None
        assert result.verdict is FLAGGED


def test_required_for_the_loan_and_described_as_a_security_deposit_is_flagged_whatever_the_record_says():
    """Record: required, risk mitigant, choice offered. The customer calls it a security deposit."""
    call = swap(REQUIRED_SAID | {4: "यह सिक्योरिटी डिपॉज़िट है।"})
    extraction = raw(required_for_loan=REQUIRED, kind=stated("deposit", "यह सिक्योरिटी डिपॉज़िट है", 4))
    result = judge(extraction, call, record(required_for_loan=True))
    (heard,) = bundling_flags(result)
    assert "deposit" in heard
    assert {f.rule_id for f in result.products[0].flags} == {
        RuleId.kind,
        RuleId.bundling,
        RuleId.belief_mismatch,
    }


def test_a_required_product_needs_the_choice_of_provider_answer_from_the_call():
    call = transcript(
        [(i, who, step, REQUIRED_SAID.get(i, text), asks) for i, who, step, text, asks in TURNS if i not in (21, 22)]
    )
    extraction = raw(required_for_loan=REQUIRED, provider_choice_offered=None)
    result = judge(extraction, call, record(required_for_loan=True))
    assert (RuleId.bundling, GapReason.not_asked) in product_gaps(result)
    assert result.verdict is UNCLEAR


# --- found by the independent review ------------------------------------------------


@pytest.mark.parametrize(
    "said, extraction",
    [
        # the quote stops short of the "नहीं" in the same clause
        ({4: "यह बीमा नहीं है, एफ़डी है।"}, {"kind": stated("insurance", "यह बीमा", 4)}),
        ({4: "यह बीमा नहीं है, एफ़डी है।"}, {"kind": stated("insurance", "ह", 4)}),  # one letter of the turn
        (
            {24: "मैंने कोई बीमा लेने की हाँ नहीं की थी, बस काग़ज़ पर साइन किया।"},
            {"consent_given": stated(True, "बीमा लेने की हाँ", 24), "consent_method": None},
        ),
        ({8: "नहीं, सही नहीं है।"}, {"premium_readback": stated(True, "सही", 8)}),
    ],
)
def test_a_quote_cut_short_of_a_negation_cannot_ground_an_answer(said, extraction):
    result = judge(raw(**extraction), swap(said))
    assert GapReason.quote_not_grounded in {reason for _, reason in product_gaps(result)}
    assert result.verdict is UNCLEAR


def test_a_quote_may_be_several_whole_clauses_or_the_whole_reply():
    call = swap({4: "देखिए, यह बीमा है, लोन के साथ लिया था।"})
    for quote in ("यह बीमा है", "देखिए, यह बीमा है", "देखिए, यह बीमा है, लोन के साथ लिया था।"):
        assert judge(raw(kind=stated("insurance", quote, 4)), call).verdict is CLEAR
    for quote in ("बीमा है", "यह बीमा है, लोन के साथ", "यह बीमा"):
        assert judge(raw(kind=stated("insurance", quote, 4)), call).verdict is UNCLEAR


@pytest.mark.parametrize(
    "method",
    [None, stated("otp", "मोबाइल पर ओटीपी आया था", 24), dont_know("फ़ॉर्म पर साइन किया था", 24)],
)
def test_a_way_of_agreeing_the_extraction_left_out_or_invented_is_a_gap(method):
    """Record: OTP. The customer said they signed a form; the extraction does not say so."""
    call = swap({24: "बीमा लेने की हाँ की थी, फ़ॉर्म पर साइन किया था।"})
    result = judge(raw(consent_method=method), call)
    assert RuleId.consent in {rule for rule, _ in product_gaps(result)}
    assert RuleId.consent not in result.products[0].passed
    assert result.verdict is UNCLEAR


def test_the_evidence_pack_never_carries_words_the_customer_did_not_say():
    invented = stated(True, "हाँ मैंने बीमा के लिए ओटीपी देकर सहमति दी थी", 24)
    result = judge(raw(consent_given=invented), loan=record(consent=None))
    pack = result.products[0].evidence_pack
    assert {f.rule_id for f in pack.flags} == {RuleId.consent, RuleId.loan_funded}
    assert pack.quotes() == (Evidence(quote="लोन की रकम से कटे थे", turn_id=10),)  # a real answer, turn 10
    consent_flag = next(f for f in pack.flags if f.rule_id is RuleId.consent)
    assert consent_flag.quote is None


# record premium 55,000; the customer first said (or was heard as) 52,000 and corrected it at read-back
CORRECTED = [
    (i, who, step, text, asks)
    for i, who, step, text, asks in TURNS
    if i <= 8
] + [
    (9, BOT, "read_back", "पचपन हज़ार, यानी 55,000, सही है?", "premium"),
    (10, CUSTOMER, "read_back", "हाँ, अब सही है।", None),
    *[(i + 2, who, step, text, asks) for i, who, step, text, asks in TURNS if i > 8],
]


def corrected_call(**changes) -> tuple[Transcript, dict]:
    said = {8: "नहीं, पचपन हज़ार।"} | changes
    call = transcript([(i, who, step, said.get(i, text), asks) for i, who, step, text, asks in CORRECTED])
    shifted = {
        key: value | {"evidence": value["evidence"] | {"turn_id": value["evidence"]["turn_id"] + 2}}
        for key, value in answers().items()
        if key not in ("product_id", "kind", "premium", "premium_readback")
    }
    return call, shifted


def test_a_premium_corrected_at_read_back_and_then_confirmed_is_clear():
    call, rest = corrected_call()
    extraction = raw(
        **rest,
        premium=stated("पचपन हज़ार", "नहीं, पचपन हज़ार", 8),
        premium_readback=stated(True, "हाँ, अब सही है", 10),
    )
    result = judge(extraction, call, record(premium_inr=55000))
    assert result.verdict is CLEAR
    assert to_beliefs(extraction, record(premium_inr=55000), call).for_product("P1").premium_inr.value == 55000


def test_the_amount_the_customer_rejected_is_never_flagged_as_what_they_said():
    """The extraction keeps the first amount (52,000) although the customer confirmed 55,000."""
    call, rest = corrected_call()
    extraction = raw(**rest, premium_readback=stated(True, "हाँ, अब सही है", 10))
    result = judge(extraction, call, record(premium_inr=55000))
    assert product_gaps(result) == {(RuleId.premium, GapReason.readback_mismatch)}
    assert not result.products[0].flags
    assert result.verdict is UNCLEAR


def test_a_correction_that_was_never_read_back_is_not_confirmed():
    call = transcript([t for t in CORRECTED if t[0] <= 8])
    call = call.model_copy(
        update={"turns": tuple(t.model_copy(update={"text": "नहीं, पचपन हज़ार।"}) if t.id == 8 else t for t in call.turns)}
    )
    extraction = RawExtraction.model_validate(
        {
            "call_id": "c1",
            "recall": RECALL,
            "products": [
                {
                    "product_id": "P1",
                    "premium": stated("पचपन हज़ार", "नहीं, पचपन हज़ार", 8),
                    "premium_readback": stated(True, "नहीं, पचपन हज़ार", 8),
                }
            ],
        }
    )
    beliefs = to_beliefs(extraction, record(premium_inr=55000), call)
    assert beliefs.for_product("P1").premium_inr == Unclear(
        reason=GapReason.readback_mismatch, evidence=Evidence(quote="नहीं, पचपन हज़ार", turn_id=8)
    )


def test_a_recall_amount_the_customer_did_not_say_is_dropped():
    recall = RECALL | {"items": [RECALL["items"][0] | {"amount_text": "पाँच हज़ार"}]}
    beliefs = to_beliefs(raw(recall=recall), record(), transcript())
    assert beliefs.recall.items[0].amount_inr is None


@pytest.mark.parametrize(
    "turn, said, extraction, rule",
    [
        (14, "पाँच लाख का तो नहीं है, कम ही है।", {"cover": stated("पाँच लाख", "पाँच लाख का तो नहीं है", 14)}, RuleId.cover),
        (
            18,
            "हाँ, 15 – 30 दिन।",
            {"cancel_allowed": stated(True, "हाँ", 18), "cancel_window": stated("30 दिन", "15 – 30 दिन", 18)},
            RuleId.cancel_window,
        ),
        (16, "पाँच साल तो नहीं।", {"term": stated("पाँच साल", "पाँच साल तो नहीं", 16)}, RuleId.term),
    ],
)
def test_a_hedged_or_ranged_reply_is_a_gap_end_to_end(turn, said, extraction, rule):
    result = judge(raw(**extraction), swap({turn: said}))
    assert product_gaps(result) == {(rule, GapReason.value_not_parsed)}
    assert result.verdict is UNCLEAR


def test_a_misspelt_fraction_word_is_read_not_dropped():
    call = swap({14: "सादे चार लाख का कवर है।"})
    result = judge(raw(cover=stated("सादे चार लाख", "सादे चार लाख का कवर है", 14)), call, record(cover_inr=400000))
    assert [(f.rule_id, f.heard) for f in result.products[0].flags] == [(RuleId.cover, "customer said ₹4,50,000")]


# --- inputs that do not belong together -------------------------------------------


def test_a_product_the_extraction_skipped_is_all_gaps():
    extraction = RawExtraction.model_validate({"call_id": "c1", "recall": {"asked": False}, "products": []})
    result = judge(extraction)
    assert result.verdict is UNCLEAR
    assert result.products[0].passed == (RuleId.evidence,)


@pytest.mark.parametrize(
    "extraction, call_id, loan_id",
    [
        (
            {"call_id": "c1", "recall": {"asked": False}, "products": [{"product_id": "P9"}]},
            "c1",
            "LN-TEST-0001",
        ),
        (
            {
                "call_id": "c1",
                "recall": {"asked": False},
                "products": [{"product_id": "P1"}, {"product_id": "P1"}],
            },
            "c1",
            "LN-TEST-0001",
        ),
        (
            {
                "call_id": "c1",
                "recall": {
                    "asked": True,
                    "items": [{"evidence": {"quote": "x", "turn_id": 2}, "product_id": "P9"}],
                },
                "products": [],
            },
            "c1",
            "LN-TEST-0001",
        ),
        ({"call_id": "c2", "recall": {"asked": False}, "products": []}, "c1", "LN-TEST-0001"),
        ({"call_id": "c1", "recall": {"asked": False}, "products": []}, "c1", "LN-OTHER-0002"),
    ],
)
def test_inputs_that_do_not_describe_the_same_call_are_refused(extraction, call_id, loan_id):
    call = transcript().model_copy(update={"call_id": call_id, "loan_id": loan_id})
    with pytest.raises(ValueError):
        to_beliefs(RawExtraction.model_validate(extraction), record(), call)


# --- decision chain v2: what `to_beliefs` passes on (P3a) ------------------------------------


def premium_call(reply: str, read_back: str) -> Transcript:
    return swap({6: reply, 7: read_back})


def test_a_hedged_amount_is_read_marked_and_passes_when_the_same_figure_is_confirmed():
    call = premium_call("शायद बावन हज़ार रुपये।", "बावन हज़ार, यानी 52,000, सही है?")
    extraction = raw(premium={**stated("बावन हज़ार", "शायद बावन हज़ार रुपये।", 6), "hedged": True})
    premium = to_beliefs(extraction, record(), call).for_product("P1").premium_inr
    assert (premium.value, premium.low, premium.approximate, premium.hedged) == (52000, None, True, True)
    assert judge(extraction, call).verdict is CLEAR


def test_a_spoken_range_is_read_as_its_two_ends_and_confirmed_by_a_read_back_of_both():
    call = premium_call("पचास बावन हज़ार के आसपास।", "पचास से बावन हज़ार, यानी 50,000 से 52,000, सही है?")
    extraction = raw(premium=stated("पचास बावन हज़ार के आसपास", "पचास बावन हज़ार के आसपास।", 6))
    premium = to_beliefs(extraction, record(), call).for_product("P1").premium_inr
    assert (premium.value, premium.low, premium.approximate) == (52000, 50000, True)
    result = judge(extraction, call)
    (flag,) = result.all_flags()
    assert (flag.rule_id, flag.reason.value, result.tier.value) == (RuleId.premium, "premium_approximate", "understanding_gap")


def test_a_range_confirmed_by_a_read_back_of_one_figure_is_a_mismatch():
    call = premium_call("पचास बावन हज़ार के आसपास।", "बावन हज़ार, यानी 52,000, सही है?")
    extraction = raw(premium=stated("पचास बावन हज़ार के आसपास", "पचास बावन हज़ार के आसपास।", 6))
    assert (RuleId.premium, GapReason.readback_mismatch) in product_gaps(judge(extraction, call))


def test_a_misspelt_fraction_in_the_span_is_never_read():
    call = premium_call("सारे तीन लाख रुपये।", "तीन लाख, यानी 3,00,000, सही है?")
    extraction = raw(premium=stated("सारे तीन लाख", "सारे तीन लाख रुपये।", 6))
    result = judge(extraction, call, record(premium_inr=300000))
    assert (RuleId.premium, GapReason.value_not_parsed) in product_gaps(result)
    assert result.tier.value == "incomplete"


@pytest.mark.parametrize(
    ("tenure", "term_months", "expected"),
    [(60, 60, "pass"), (None, 60, "not_comparable"), (36, 60, "term_differs")],
)
def test_a_term_tied_to_the_loan_is_the_loans_tenure(tenure, term_months, expected):
    call = swap({16: "जब तक लोन चलेगा।"})
    extraction = raw(term=stated("जब तक लोन चलेगा", "जब तक लोन चलेगा।", 16))
    loan = record(term_months=term_months).model_copy(update={"tenure_months": tenure})
    result = judge(extraction, call, loan)
    if expected == "pass":
        assert result.verdict is CLEAR
    elif expected == "not_comparable":
        assert product_gaps(result) == {(RuleId.term, GapReason.not_comparable)}
        assert result.tier.value == "understanding_gap"
    else:
        assert [f.reason.value for f in result.all_flags()] == ["term_differs"]


def frequency_call(reply: str) -> Transcript:
    turns = [*TURNS, (25, BOT, "teach_back", "यह पैसा एक ही बार देना था, या बार-बार?", "payment_frequency"),
             (26, CUSTOMER, "teach_back", reply, None)]  # fmt: skip
    return transcript(turns)


def test_payment_frequency_is_grounded_and_once_on_a_regular_product_is_a_referral():
    call = frequency_call("एक ही बार देना था।")
    extraction = raw(payment_frequency=stated("one_time", "एक ही बार देना था।", 26))
    result = judge(extraction, call)
    assert [f.reason.value for f in result.all_flags()] == ["feature_contradicted"]
    assert result.tier.value == "refer"
    elsewhere = raw(payment_frequency=stated("one_time", "बावन हज़ार रुपये।", 6))
    assert (RuleId.belief_mismatch, GapReason.quote_not_grounded) in product_gaps(judge(elsewhere, call))


def conflict(question: str, *answers: tuple[str, int]) -> dict:
    return {"question": question, "answers": [{"quote": q, "turn_id": t} for q, t in answers]}


def reasked_call() -> Transcript:
    """The kind question answered "FD", asked again, and answered "insurance"."""
    first = [(i, who, step, "एफ़डी है।" if i == 4 else text, asks) for i, who, step, text, asks in TURNS]
    again = [(25, BOT, "teach_back", "एक बार फिर: बीमा, एफ़डी, या कुछ और?", "kind"),
             (26, CUSTOMER, "teach_back", "अच्छा, बीमा।", None)]  # fmt: skip
    return transcript([*first, *again])


def test_a_conflict_with_both_answers_in_the_call_is_a_referral_holding_both_quotes():
    call = reasked_call()
    extraction = raw(
        kind=stated("insurance", "अच्छा, बीमा।", 26),
        conflicts=[conflict("kind", ("एफ़डी है।", 4), ("अच्छा, बीमा।", 26))],
    )
    result = judge(extraction, call)
    (flag,) = [f for f in result.all_flags() if f.reason.value == "answers_conflict"]
    assert (flag.quote, [e.quote for e in flag.also]) == ("एफ़डी है।", ["अच्छा, बीमा।"])
    assert result.tier.value == "refer"


def test_a_conflict_quote_not_in_the_call_is_an_evidence_gap_not_a_conflict():
    extraction = raw(conflicts=[conflict("kind", ("एफ़डी है।", 4), ("यह बीमा है।", 4))])
    result = judge(extraction)
    assert not result.all_flags()
    assert (RuleId.evidence, GapReason.quote_not_grounded) in product_gaps(result)
    assert result.tier.value == "incomplete"


def test_a_grounded_denial_in_recall_is_a_referral():
    call = swap({2: "कुछ नहीं लिया, बस लोन लिया था।"})
    said = {"quote": "कुछ नहीं लिया, बस लोन लिया था।", "turn_id": 2}
    extraction = raw(recall={"asked": True, "answer": said, "items": [], "denial": said})
    beliefs = to_beliefs(extraction, record(), call)
    assert beliefs.recall.denial == Evidence(**said)
    reasons = [f.reason.value for f in judge(extraction, call, record()).all_flags()]
    assert reasons == ["recall_denied"]  # naming it later, at the kind question, does not undo it
    unnamed = raw(recall={"asked": True, "answer": said, "items": [], "denial": said}, kind=dont_know("यह बीमा है", 4))
    result = judge(unnamed, call)
    assert "recall_denied" in [f.reason.value for f in result.all_flags()]
    assert result.tier.value == "refer"


def test_a_denial_quote_not_in_the_recall_reply_is_dropped_as_ungrounded():
    said = {"quote": "कुछ नहीं लिया", "turn_id": 2}
    extraction = raw(recall={**RECALL, "denial": said})
    beliefs = to_beliefs(extraction, record(), transcript())
    assert beliefs.recall.denial is None
    assert Evidence(**said) in beliefs.ungrounded


def test_an_unscreened_reply_is_a_case_gap_and_the_call_is_incomplete():
    extraction = raw().model_copy(update={"unscreened": (Evidence(quote="यह बीमा है।", turn_id=4),)})
    beliefs = to_beliefs(extraction, record(), transcript())
    assert beliefs.unscreened == (Evidence(quote="यह बीमा है।", turn_id=4),)
    result = evaluate(record(), beliefs)
    assert {(g.rule_id, g.reason) for g in result.case_gaps} == {(RuleId.evidence, GapReason.extraction_failed)}
    assert result.tier.value == "incomplete"


# --- iteration-2 verifier fixes ----------------------------------------------------------


def cover_read_back_call(reply: str, read_back: str, answer: str = "हाँ, सही है।") -> Transcript:
    turns = [*[(i, w, st, reply if i == 14 else t, a) for i, w, st, t, a in TURNS],
             (25, BOT, "read_back", read_back, "cover"), (26, CUSTOMER, "read_back", answer, None)]  # fmt: skip
    return transcript(turns)


def test_a_plain_cover_figure_confirmed_at_its_read_back_is_a_referral():
    call = cover_read_back_call("10,00,000 का कवर है।", "दस लाख, यानी 10,00,000, सही है?")
    extraction = raw(cover=stated("10,00,000", "10,00,000 का कवर है।", 14), cover_readback=stated(True, "हाँ, सही है।", 26))
    result = judge(extraction, call)
    assert [f.reason.value for f in result.all_flags()] == ["cover_differs_confirmed"]
    assert result.tier.value == "refer"
    unconfirmed = judge(raw(cover=stated("10,00,000", "10,00,000 का कवर है।", 14)), call)
    assert [f.reason.value for f in unconfirmed.all_flags()] == ["cover_differs_unconfirmed"]
    assert unconfirmed.tier.value == "incomplete"


def test_a_cover_read_back_of_another_figure_confirms_nothing():
    call = cover_read_back_call("10,00,000 का कवर है।", "पाँच लाख, यानी 5,00,000, सही है?")
    extraction = raw(cover=stated("10,00,000", "10,00,000 का कवर है।", 14), cover_readback=stated(True, "हाँ, सही है।", 26))
    result = judge(extraction, call)
    assert (RuleId.cover, GapReason.readback_mismatch) in product_gaps(result)
    assert result.tier.value != "refer"


@pytest.mark.parametrize(
    ("turn", "reply", "field", "span"),
    [
        (14, "पाँच लाख तक का कवर है।", "cover", "पाँच लाख तक"),  # "up to five lakh"
        (6, "बावन हज़ार रुपये लगे।", "premium", "बावन हज़ार रुपये लगे"),
        (16, "पाँच साल तक चलेगा।", "term", "पाँच साल तक"),
    ],
)
def test_a_harmless_word_next_to_the_number_in_the_span_still_reads(turn, reply, field, span):
    extraction = raw(**{field: stated(span, reply, turn)})
    assert judge(extraction, swap({turn: reply})).verdict is CLEAR


def test_the_parser_sees_the_word_the_model_left_out_of_its_span():
    """The span is widened by one word each side in the reply: "सारहे" is seen, not dropped."""
    call = swap({14: "सारहे पाँच लाख का कवर है।"})
    result = judge(raw(cover=stated("पाँच लाख", "सारहे पाँच लाख का कवर है।", 14)), call)
    assert (RuleId.cover, GapReason.value_not_parsed) in product_gaps(result)


def test_an_earlier_reply_kept_with_an_answer_must_be_in_the_call():
    extraction = raw(kind={**stated("insurance", "यह बीमा है।", 4), "also": [{"quote": "पता नहीं", "turn_id": 4}]})
    beliefs = to_beliefs(extraction, record(), transcript())
    assert beliefs.for_product("P1").kind.also == ()
    assert Evidence(quote="पता नहीं", turn_id=4) in beliefs.for_product("P1").ungrounded
