"""P5 fix round through the extractor and the rules, with scripted model outputs.

Each test swaps one reply of the informed BASE call (`extractkit`) and the model's output for it.
Informed and misled versions of each cause; the retraction guards (change check, take-back tail,
grounding) still apply to the new answers.
"""

import pytest
from extractkit import BASE, PRODUCT, answered, build, record

from samajh.extract._prompt import messages
from samajh.extract._wire import SlotKind
from samajh.pipeline import run_text
from samajh.rules.normalise import paid_otherwise
from samajh.types import (
    ConsentMethod,
    FeatureClaim,
    FlagReason,
    GapReason,
    Language,
    PaymentSource,
    RuleId,
    Stated,
    Tier,
    Unclear,
    tier_of,
)

R = FlagReason
NO_READBACK = [r for r in BASE if r[0] != "read_back"]
REQUIRED = PRODUCT.model_copy(update={"required_for_loan": True})
PC_Q = "क्या आपको बताया गया था कि यह आप कहीं और से भी ले सकते हैं, या नहीं?"
PC_ROW = (
    "teach_back",
    "provider_choice",
    PC_Q,
    "हाँ, बताया था।",
    {"status": "stated", "yes": True, "clauses": [1, 2]},
)


def call(rows, product=PRODUCT, checks: dict[str, dict] | None = None):
    transcript, llm = build(rows)
    for reply, output in (checks or {}).items():
        llm.say("ChangeReply", reply, **output)
    return run_text(transcript, record(product), llm)


def rule_tier(run, rule: RuleId) -> Tier:
    p = run.result.products[0]
    return tier_of([f for f in p.flags if f.rule_id is rule], [g for g in p.gaps if g.rule_id is rule])


def reasons(run, rule: RuleId) -> list:
    p = run.result.products[0]
    return [f.reason for f in p.flags if f.rule_id is rule] + [g.reason for g in p.gaps if g.rule_id is rule]


WITHDRAWN = {"change": "withdrawn", "first_clauses": [1], "final_clauses": []}

# --- (A) consent: the way of agreeing alone --------------------------------------------------

METHOD_ONLY = {"given_status": "unclear", "given": None, "given_clauses": [], "method_status": "stated",
               "method": "otp", "method_clauses": [1]}  # fmt: skip


def test_a_method_only_consent_reply_is_clear_when_the_product_was_named_earlier():
    run = call(answered(BASE, "consent", "ओटीपी दिया था।", **METHOD_ONLY))
    assert isinstance(run.beliefs.products[0].consent_given, Unclear)  # the model's reading is unchanged
    assert RuleId.consent in run.result.products[0].passed
    assert run.result.tier is Tier.clear


def test_a_method_only_reply_that_differs_from_the_record_refers():
    run = call(answered(BASE, "consent", "फॉर्म पर साइन किया था।", **METHOD_ONLY | {"method": "signed_form"}))
    assert reasons(run, RuleId.consent) == [R.consent_method_differs]
    assert run.result.tier is Tier.refer


def test_a_method_only_reply_with_the_product_named_nowhere_is_an_understanding_gap():
    rows = answered(BASE, None, "अभी याद नहीं आ रहा।", items=[], took_nothing=False)
    rows = answered(rows, "kind", "पता नहीं जी।", status="dont_know", kind=None, clauses=[1])
    run = call(answered(rows, "consent", "ओटीपी दिया था।", **METHOD_ONLY))
    assert reasons(run, RuleId.consent) == [R.consent_product_not_named]
    assert rule_tier(run, RuleId.consent) is Tier.understanding_gap


def test_a_method_only_reply_is_clear_when_only_open_recall_named_the_product():
    rows = answered(BASE, "kind", "पता नहीं जी।", status="dont_know", kind=None, clauses=[1])
    run = call(answered(rows, "consent", "ओटीपी दिया था।", **METHOD_ONLY))
    assert RuleId.consent in run.result.products[0].passed


def test_a_differing_method_with_the_product_named_nowhere_still_refers():
    rows = answered(BASE, None, "अभी याद नहीं आ रहा।", items=[], took_nothing=False)
    rows = answered(rows, "kind", "पता नहीं जी।", status="dont_know", kind=None, clauses=[1])
    run = call(answered(rows, "consent", "फॉर्म पर साइन किया था।", **METHOD_ONLY | {"method": "signed_form"}))
    assert reasons(run, RuleId.consent) == [R.consent_method_differs]


def test_a_method_only_reply_that_was_withdrawn_stays_incomplete():
    reply = "ओटीपी दिया था, नहीं, याद नहीं कैसे।"
    run = call(answered(BASE, "consent", reply, **METHOD_ONLY), checks={reply: WITHDRAWN})
    assert reasons(run, RuleId.consent) == [GapReason.no_usable_answer]
    assert rule_tier(run, RuleId.consent) is Tier.incomplete


def test_a_method_only_reply_whose_method_was_corrected_stays_incomplete():
    reply = "फॉर्म पर साइन किया था, नहीं, ओटीपी दिया था।"
    output = METHOD_ONLY | {"method_clauses": [3]}
    check = {"change": "corrected", "first_clauses": [1], "final_clauses": [3]}
    run = call(answered(BASE, "consent", reply, **output), checks={reply: check})
    method = run.beliefs.products[0].consent_method
    assert isinstance(method, Stated) and method.value is ConsentMethod.otp and method.also
    assert rule_tier(run, RuleId.consent) is Tier.incomplete


def test_a_method_only_reply_with_a_take_back_tail_stays_incomplete():
    reply = "ओटीपी दिया था या कुछ और"
    run = call(answered(BASE, "consent", reply, **METHOD_ONLY))
    assert rule_tier(run, RuleId.consent) is Tier.incomplete


# --- (F) a phone yes: classed recorded_call by the model unless it was not recorded ------------

RECORDED = PRODUCT.model_copy(
    update={"consent": PRODUCT.consent.model_copy(update={"method": "recorded_call"})}
)
SIGNED = PRODUCT.model_copy(update={"consent": PRODUCT.consent.model_copy(update={"method": "signed_form"})})
PHONE_YES = "फ़ोन पर हाँ बोला था।"


def test_a_phone_yes_is_clear_against_a_recorded_call():
    run = call(answered(BASE, "consent", PHONE_YES, **METHOD_ONLY | {"method": "recorded_call"}), RECORDED)
    assert run.result.tier is Tier.clear


def test_a_phone_yes_the_customer_says_was_not_recorded_refers():
    reply = "phone par haan bola tha, recording nahi hui"
    run = call(answered(BASE, "consent", reply, **METHOD_ONLY | {"method": "verbal"}), RECORDED)
    assert reasons(run, RuleId.consent) == [R.consent_method_differs]


def test_a_phone_yes_against_a_signed_form_record_refers():
    run = call(answered(BASE, "consent", PHONE_YES, **METHOD_ONLY | {"method": "recorded_call"}), SIGNED)
    assert reasons(run, RuleId.consent) == [R.consent_method_differs]


def test_the_consent_prompt_classes_a_phone_yes_as_recorded_call_unless_not_recorded():
    system = messages(SlotKind.consent, Language.hi, "q", "r")[0].content
    assert '"recorded_call": said yes on a phone call, unless they say the call was not recorded' in system
    assert "they say was not recorded" in system
    assert "phone_call" not in system


# --- (C) a premium of nothing -----------------------------------------------------------------


def free(span: str) -> dict:
    return {"status": "stated", "span": span, "free": True, "clauses": [1]}


def test_it_was_free_is_a_premium_of_zero_and_refers():
    run = call(answered(NO_READBACK, "premium", "मुफ़्त था, कुछ नहीं लगा।", **free("कुछ नहीं लगा")))
    premium = run.beliefs.products[0].premium_inr
    assert isinstance(premium, Stated) and premium.value == 0
    assert reasons(run, RuleId.premium) == [R.premium_said_zero]
    assert run.result.tier is Tier.refer


def test_zero_rupees_read_by_the_parser_is_the_same_zero():
    reply = "zero rupees लगे।"
    run = call(answered(NO_READBACK, "premium", reply, status="stated", span="zero rupees", clauses=[1]))
    assert reasons(run, RuleId.premium) == [R.premium_said_zero]
    # The model's `free` answer for the same reply reaches the same zero.
    run = call(answered(NO_READBACK, "premium", reply, **free("zero rupees")))
    assert reasons(run, RuleId.premium) == [R.premium_said_zero]


def test_zero_rupees_cut_from_the_loan_is_not_a_premium_of_zero_by_either_route():
    reply = "zero rupees diye, loan se kata."
    for output in ({"status": "stated", "span": "zero rupees", "clauses": [1]}, free("zero rupees")):
        run = call(answered(NO_READBACK, "premium", reply, **output))
        assert R.premium_said_zero not in reasons(run, RuleId.premium)


@pytest.mark.parametrize(
    "reply", ["मैंने कुछ नहीं दिया, लोन से कटा था।", "कुछ नहीं लगा, बैंक ने भरा।", "kuch nahi diya, kisi aur ne bhara"]
)
def test_nothing_out_of_pocket_is_not_a_premium_of_zero(reply):
    run = call(
        answered(NO_READBACK, "premium", reply, **free("कुछ नहीं" if "कुछ" in reply else "kuch nahi diya"))
    )
    premium = run.beliefs.products[0].premium_inr
    assert isinstance(premium, Unclear) and premium.reason is GapReason.no_usable_answer
    assert R.premium_said_zero not in reasons(run, RuleId.premium)


def test_a_free_reply_that_also_gives_an_amount_is_not_read():
    reply = "मुफ़्त बोला था, पर इकतालीस हज़ार तीन सौ लगे।"
    run = call(answered(NO_READBACK, "premium", reply, **free("मुफ़्त")))
    premium = run.beliefs.products[0].premium_inr
    assert isinstance(premium, Unclear) and premium.reason is GapReason.value_not_parsed


@pytest.mark.parametrize(("reply", "span"), [("मुफ़्त था।", "बिल्कुल फ्री"), ("free tha ji", "it was free")])
def test_free_words_that_are_not_in_the_reply_are_not_grounded(reply, span):
    run = call(answered(NO_READBACK, "premium", reply, **free(span)))
    assert reasons(run, RuleId.premium) == [GapReason.quote_not_grounded]


def test_a_free_reply_with_an_amount_in_english_is_not_read_either():
    run = call(answered(NO_READBACK, "premium", "It was free, I think 500 rupees.", **free("It was free")))
    premium = run.beliefs.products[0].premium_inr
    assert isinstance(premium, Unclear) and premium.reason is GapReason.value_not_parsed


def test_a_free_premium_taken_back_is_not_kept():
    reply = "मुफ़्त था, अरे नहीं, याद नहीं।"
    run = call(answered(NO_READBACK, "premium", reply, **free("मुफ़्त था")), checks={reply: WITHDRAWN})
    assert isinstance(run.beliefs.products[0].premium_inr, Unclear)
    assert R.premium_said_zero not in reasons(run, RuleId.premium)


def test_a_free_premium_with_a_who_knows_tail_is_not_kept():
    run = call(answered(NO_READBACK, "premium", "मुफ़्त था क्या पता", **free("मुफ़्त था")))
    assert isinstance(run.beliefs.products[0].premium_inr, Unclear)


def test_the_informed_figure_still_passes():
    assert call(BASE).result.tier is Tier.clear


def test_paid_otherwise_reads_the_loan_a_cut_or_another_payer():
    assert (
        paid_otherwise("loan se kat gaya")
        and paid_otherwise("बैंक ने भरा")
        and paid_otherwise("it was deducted")
    )
    assert not paid_otherwise("मुफ़्त था, कुछ नहीं लगा।") and not paid_otherwise("I paid nothing, it was free.")


# --- (D) a premium paid by nobody -------------------------------------------------------------


def test_the_bank_paid_is_not_charged_and_refers_against_a_premium_from_the_loan():
    run = call(
        answered(BASE, "payment_source", "मैंने कुछ नहीं दिया, बैंक ने भरा।", source="not_charged", clauses=[1, 2])
    )
    assert run.beliefs.products[0].payment_source.value is PaymentSource.not_charged
    assert reasons(run, RuleId.loan_funded) == [R.payment_says_not_charged]


def test_from_the_loan_with_nothing_paid_separately_is_still_clear():
    reply = "लोन में से कटा था, मैंने अलग से कुछ नहीं दिया।"
    run = call(answered(BASE, "payment_source", reply, source="from_loan", clauses=[1, 2]))
    assert run.result.tier is Tier.clear


# --- (B) "nobody told me about another company" ------------------------------------------------

PC_ROWS = [*BASE[:5], PC_ROW, *BASE[5:]]


@pytest.mark.parametrize(
    "reply", ["दूसरी कंपनी के बारे में कुछ नहीं बताया पता नहीं", "mujhe nahi pata tha ki bahar se bhi le sakte hain"]
)
def test_nobody_told_me_with_a_dont_know_tail_is_a_usable_no(reply):
    run = call(answered(PC_ROWS, "provider_choice", reply, yes=False, clauses=[1]), REQUIRED)
    assert run.beliefs.products[0].provider_choice_offered.value is False
    assert reasons(run, RuleId.bundling) == [R.bundled_no_choice_told]


@pytest.mark.parametrize("reply", ["हाँ बताया था पता नहीं", "haan bola tha kya pata"])
def test_a_yes_with_a_dont_know_tail_is_still_taken_back(reply):
    run = call(answered(PC_ROWS, "provider_choice", reply, yes=True, clauses=[1]), REQUIRED)
    assert isinstance(run.beliefs.products[0].provider_choice_offered, Unclear)
    assert rule_tier(run, RuleId.bundling) is Tier.incomplete


def test_a_tail_on_the_required_question_still_takes_the_answer_back():
    reply = "ज़रूरी नहीं था पता नहीं"
    run = call(answered(BASE, "required_for_loan", reply, yes=False, clauses=[1]))
    assert isinstance(run.beliefs.products[0].required_for_loan, Unclear)


# --- (E) a denial of a feature is not a claim ------------------------------------------------

DENIALS = {
    FeatureClaim.refundable_anytime: ("पैसा वापस नहीं मिलता।", "जब चाहे पैसा वापस ले सकते हैं।"),
    FeatureClaim.withdrawable_after_period: ("loan khatam hone pe bhi paisa wapas nahi milega", "loan khatam hone pe paisa wapas milega"),
    FeatureClaim.guaranteed_return: ("कोई गारंटी वाला रिटर्न नहीं है।", "ब्याज के साथ पैसा वापस आएगा।"),
    FeatureClaim.is_deposit: ("ये FD नहीं है, बीमा है।", "ये तो मेरी FD है।"),
}  # fmt: skip


@pytest.mark.parametrize("claim", DENIALS)
def test_a_denied_feature_read_as_no_claim_is_clear_and_the_asserted_one_refers(claim):
    denial, assertion = DENIALS[claim]
    denied = call(answered(BASE, "features", denial, claims=[], clauses=[1]))
    assert rule_tier(denied, RuleId.belief_mismatch) is Tier.clear
    asserted = call(answered(BASE, "features", assertion, claims=[claim.value], clauses=[1]))
    assert [f.claim for f in asserted.result.products[0].flags if f.reason is R.feature_contradicted] == [
        claim
    ]


def test_the_money_back_prompt_says_a_denied_belief_is_not_a_claim():
    system = messages(SlotKind.features, Language.hi_en, "q", "r")[0].content
    assert "A belief named only to deny it is not a claim" in system
    assert '"paisa wapas nahi milega"' in system and '"it is not refundable"' in system


# --- round 2: a "no" on provider choice survives a withdrawn check whose only cause is the tail ---

WITHDRAWN_ALL = {"change": "withdrawn", "first_clauses": [1], "final_clauses": []}


@pytest.mark.parametrize(
    "reply", ["नहीं बताया पता नहीं", "nahi bola tha mujhe nahi pata", "नहीं, किसी ने नहीं बताया, पता नहीं।"]
)
def test_a_no_with_only_a_dont_know_tail_is_kept_when_the_check_says_withdrawn(reply):
    rows = answered(PC_ROWS, "provider_choice", reply, yes=False, clauses=[1])
    run = call(rows, REQUIRED, checks={reply: WITHDRAWN_ALL})
    assert run.beliefs.products[0].provider_choice_offered.value is False
    assert reasons(run, RuleId.bundling) == [R.bundled_no_choice_told]


@pytest.mark.parametrize(
    "reply",
    ["नहीं बताया, रुको, हाँ बताया था, पता नहीं", "नहीं बताया, शायद बताया हो", "nahi bataya, ruko, pata nahi"],
)
def test_a_no_taken_back_with_other_words_stays_withdrawn(reply):
    rows = answered(PC_ROWS, "provider_choice", reply, yes=False, clauses=[1])
    run = call(rows, REQUIRED, checks={reply: WITHDRAWN_ALL})
    assert isinstance(run.beliefs.products[0].provider_choice_offered, Unclear)


@pytest.mark.parametrize("reply", ["हाँ बताया था, पता नहीं", "haan bola tha, mujhe nahi pata"])
def test_a_yes_with_a_dont_know_tail_and_a_withdrawn_check_stays_withdrawn(reply):
    rows = answered(PC_ROWS, "provider_choice", reply, yes=True, clauses=[1])
    run = call(rows, REQUIRED, checks={reply: WITHDRAWN_ALL})
    assert isinstance(run.beliefs.products[0].provider_choice_offered, Unclear)


def test_the_required_question_with_a_withdrawn_check_is_unchanged():
    reply = "ज़रूरी नहीं था, पता नहीं"
    run = call(
        answered(BASE, "required_for_loan", reply, yes=False, clauses=[1]), checks={reply: WITHDRAWN_ALL}
    )
    assert isinstance(run.beliefs.products[0].required_for_loan, Unclear)


# --- round 2: an untimed money-back belief, and the exactness hedge marker ----------------------


@pytest.mark.parametrize("reply", ["मुझे लगता है पूरा पैसा वापस मिल जाएगा।", "haan, refund milta hai"])
def test_an_untimed_money_back_belief_refers_on_insurance(reply):
    run = call(answered(BASE, "features", reply, claims=["money_back"], clauses=[1]))
    assert [f.claim for f in run.result.products[0].flags if f.reason is R.feature_contradicted] == [
        FeatureClaim.money_back
    ]


def test_an_untimed_money_back_belief_is_clear_on_a_deposit_record():
    fd = PRODUCT.model_copy(update={"features": frozenset({FeatureClaim.is_deposit})})
    run = call(answered(BASE, "features", "पैसा वापस मिल जाएगा।", claims=["money_back"], clauses=[1]), fd)
    assert rule_tier(run, RuleId.belief_mismatch) is Tier.clear


def test_the_money_back_prompt_teaches_the_untimed_claim_and_the_screen_does_not():
    from samajh.extract._prompt import screen_messages

    assert (
        '"money_back": the money comes back' in messages(SlotKind.features, Language.hi, "q", "r")[0].content
    )
    assert "money_back" not in screen_messages(Language.hi, "q", "r")[0].content


@pytest.mark.parametrize(
    "reply",
    ["इकतालीस हज़ार तीन सौ, पक्का नहीं पता।", "41300 rupaye, exact yaad nahi.", "41300, theek se yaad nahi"],
)
def test_a_figure_with_an_exactness_doubt_is_marked_hedged_and_keeps_its_tier(reply):
    span = "41300" if reply.startswith("41300") else "इकतालीस हज़ार तीन सौ"
    run = call(answered(BASE, "premium", reply, span=span, clauses=[1]))
    premium = run.beliefs.products[0].premium_inr
    assert (
        isinstance(premium, Stated) and premium.value == 41300 and premium.hedged and not premium.approximate
    )
    assert run.result.tier is Tier.clear


@pytest.mark.parametrize(
    ("reply", "span"), [("पाँच लाख, ठीक से याद नहीं।", "पाँच लाख"), ("5 lakh, pakka nahi pata", "5 lakh")]
)
def test_a_cover_with_an_exactness_doubt_keeps_its_old_marker_so_its_tier_does_not_move(reply, span):
    run = call(answered(BASE, "cover", reply, span=span, clauses=[1]))
    cover = run.beliefs.products[0].cover_inr
    assert isinstance(cover, Stated) and not cover.hedged
    assert R.cover_differs_unconfirmed in reasons(run, RuleId.cover)


# --- last round: a filler after the tail, and Devanagari "exact" -------------------------------


@pytest.mark.parametrize("reply", ["नहीं कहा था पता नहीं जी", "नहीं कहा था पता नहीं"])
def test_a_no_with_a_dont_know_tail_and_an_optional_closing_filler_is_kept(reply):
    rows = answered(PC_ROWS, "provider_choice", reply, yes=False, clauses=[1])
    run = call(rows, REQUIRED, checks={reply: WITHDRAWN_ALL})
    assert run.beliefs.products[0].provider_choice_offered.value is False


def test_a_yes_with_a_dont_know_tail_and_a_closing_filler_stays_withdrawn():
    reply = "हाँ बताया था पता नहीं जी"
    rows = answered(PC_ROWS, "provider_choice", reply, yes=True, clauses=[1])
    run = call(rows, REQUIRED, checks={reply: WITHDRAWN_ALL})
    assert isinstance(run.beliefs.products[0].provider_choice_offered, Unclear)


@pytest.mark.parametrize(
    "reply",
    ["इकतालीस हज़ार तीन सौ, एग्ज़ैक्ट याद नहीं।", "41300, एग्जैक्ट नहीं पता", "41300 rupaye, exactly yaad nahi."],
)
def test_a_devanagari_exact_doubt_is_marked_hedged(reply):
    span = "इकतालीस हज़ार तीन सौ" if reply.startswith("इक") else "41300"
    premium = call(answered(BASE, "premium", reply, span=span, clauses=[1])).beliefs.products[0].premium_inr
    assert isinstance(premium, Stated) and premium.hedged and not premium.approximate
