"""What happens to model output at the boundary. The fake LLM replays recorded outputs.

Each test starts from a development call whose recorded extraction gives the right verdict and
changes what the model returns for one reply. A quote the customer did not say must never
become an answer, and must never leave a call `clear`.
"""

import devset
import pytest
from extractkit import FakeLlm, recorded_outputs

from samajh import pipeline
from samajh.extract import SlotKind, extract, extract_traced, slots
from samajh.pipeline import run_text, run_text_case
from samajh.types import DontKnow, GapReason, LoanRecord, RuleId, Stated, Transcript, Unclear, Verdict

CLEAR, FLAGGED, UNCLEAR = Verdict.clear, Verdict.flag_for_review, Verdict.unclear_needs_human
SCENARIOS = {s.id: s for s in devset.scenarios()}
HI = SCENARIOS["hi-01"]  # compliant Hindi call: clear

PREMIUM = "चौबीस हज़ार रुपये लगे थे।"
KIND = "बीमा है, लोन वाला बीमा।"
CONSENT = "बीमा के लिए हाँ की थी, फ़ोन पर ओटीपी आया था वो बताया था।"
FEATURES = "नहीं, यह तो बीमा है, इसका पैसा वापस नहीं आता।"
RECALL = "लोन के साथ एक बीमा भी लिया था, चौबीस हज़ार का।"
COVER = "चार लाख का कवर है।"


def answers(llm: FakeLlm, scenario=HI):
    return extract(scenario.transcript, scenario.record, llm).products[0]


def gaps(run) -> set[tuple[RuleId, GapReason]]:
    return {(g.rule_id, g.reason) for g in run.result.all_gaps()}


# --- the recorded extraction, replayed -------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_recorded_outputs_give_the_expected_verdict_and_flags(llm, scenario):
    result = run_text_case(scenario.transcript, scenario.record, llm)
    assert result.verdict is scenario.gold.verdict
    assert {(f.product_id, f.rule_id) for f in result.all_flags()} == scenario.gold.flags


def test_every_answer_quote_is_text_of_the_turn_it_cites(llm):
    for scenario in SCENARIOS.values():
        turns = {t.id: t.text for t in scenario.transcript.turns}
        raw = extract(scenario.transcript, scenario.record, llm)
        for name in type(raw.products[0]).model_fields:
            answer = getattr(raw.products[0], name)
            evidence = getattr(answer, "evidence", None)
            if evidence is not None:
                assert evidence.quote in turns[evidence.turn_id], (scenario.id, name)


def test_the_extraction_is_the_same_on_a_second_run(llm):
    assert extract(HI.transcript, HI.record, llm) == extract(HI.transcript, HI.record, llm)


# --- quotes and spans the customer did not say -----------------------------------------------


def test_an_amount_the_customer_did_not_say_is_dropped_and_counted(llm):
    llm.say("SpanReply", PREMIUM, span="बावन हज़ार")
    run = run_text(HI.transcript, HI.record, llm)
    premium = run.extraction.raw.products[0].premium
    assert premium == Unclear(reason=GapReason.quote_not_grounded)
    assert [t.not_in_reply for t in run.extraction.slots if t.not_in_reply] == [["span"]]
    assert run.result.verdict is UNCLEAR
    assert (RuleId.premium, GapReason.quote_not_grounded) in gaps(run)


@pytest.mark.parametrize(
    "span",
    [
        "चौबीस हज़ार रुपये थे",  # words joined across a gap
        "24,000",  # digits for words
        "चौबीस हजार",  # spelling changed (no nukta)
        "twenty four thousand",  # translated
        "हज़ार चौबीस",  # reordered
    ],
)
def test_a_rewritten_amount_is_not_accepted(llm, span):
    llm.say("SpanReply", PREMIUM, span=span)
    assert answers(llm).premium == Unclear(reason=GapReason.quote_not_grounded)


def test_an_amount_copied_with_a_word_too_many_is_passed_on_whole_and_still_reads(llm):
    """No trimming, and no refusal of a harmless verb: the parser reads it (verifier iter2)."""
    llm.say("SpanReply", PREMIUM, span="चौबीस हज़ार रुपये लगे")
    premium = answers(llm).premium
    assert isinstance(premium, Stated)
    assert premium.value == "चौबीस हज़ार रुपये लगे"
    assert run_text_case(HI.transcript, HI.record, llm).verdict is CLEAR


def test_real_words_that_are_not_the_amount_cannot_pass_as_the_premium(llm):
    llm.say("SpanReply", PREMIUM, span="लगे थे")
    run = run_text(HI.transcript, HI.record, llm)
    assert run.result.verdict is UNCLEAR
    assert (RuleId.premium, GapReason.value_not_parsed) in gaps(run)


@pytest.mark.parametrize("clauses", [[], [0], [3], [1, 7], [-1]])
def test_a_clause_number_that_is_not_in_the_reply_drops_the_answer(llm, clauses):
    llm.say("KindReply", KIND, clauses=clauses)
    run = run_text(HI.transcript, HI.record, llm)
    assert run.extraction.raw.products[0].kind == Unclear(reason=GapReason.quote_not_grounded)
    assert [t.bad_pointers for t in run.extraction.slots if t.bad_pointers] == [["kind"]]
    assert run.result.verdict is not CLEAR


def test_stated_without_a_value_is_unclear(llm):
    llm.say("KindReply", KIND, kind=None)
    kind = answers(llm).kind
    assert isinstance(kind, Unclear) and kind.reason is GapReason.no_usable_answer
    llm.say("SpanReply", COVER, span=None)
    assert isinstance(answers(llm).cover, Unclear)


def test_dont_know_together_with_a_belief_is_unclear(llm):
    llm.say("FeaturesReply", FEATURES, status="dont_know", claims=["refundable_anytime"])
    assert isinstance(answers(llm).feature_probe, Unclear)


def test_a_concern_the_customer_did_not_voice_cannot_leave_the_call_clear(llm):
    llm.say(
        "ScreenReply", KIND, claims=[], concerns=[{"concern": "coached_answers", "span": "सब में हाँ बोलना"}]
    )
    run = run_text(HI.transcript, HI.record, llm)
    assert run.beliefs.sale_concerns == ()  # it is not counted as a concern
    assert run.result.verdict is UNCLEAR  # and it is not silently dropped either
    assert (RuleId.evidence, GapReason.quote_not_grounded) in gaps(run)


def test_a_claim_the_customer_did_not_make_cannot_leave_the_call_clear(llm):
    llm.say("ScreenReply", KIND, claims=[{"claim": "is_deposit", "span": "यह एफ़डी है"}], concerns=[])
    run = run_text(HI.transcript, HI.record, llm)
    assert run.beliefs.products[0].volunteered_claims == ()
    assert run.result.verdict is UNCLEAR


def test_a_recall_item_the_customer_did_not_name_is_never_matched_to_a_product(llm):
    llm.say("RecallReply", RECALL, items=[{"span": "एक पॉलिसी", "kind": "insurance", "amount_span": None}])
    run = run_text(HI.transcript, HI.record, llm)
    assert run.extraction.raw.recall.items[0].product_id is None
    assert run.result.verdict is not CLEAR
    assert RuleId.recall in {f.rule_id for f in run.result.all_flags()}  # the product was not named


def test_claims_from_the_screen_of_the_money_back_probe_are_not_counted_twice(llm):
    llm.say("ScreenReply", FEATURES, claims=[{"claim": "is_deposit", "span": "यह तो बीमा है"}], concerns=[])
    assert answers(llm).volunteered_claims == ()


# --- silence, re-asks, corrections -----------------------------------------------------------


def test_silence_is_unclear_and_costs_no_llm_call():
    scenario = SCENARIOS["ta-03"]  # the payment reply is empty
    llm = FakeLlm(recorded_outputs())
    payment = answers(llm, scenario).payment_source
    assert payment == Unclear()
    assert not any("PaymentReply" in str(request) for request in llm.sent)
    silent = [s for s in slots(scenario.transcript, scenario.record) if not s.turn.text.strip()]
    assert [s.kind for s in silent] == [SlotKind.payment_source]


def test_a_question_asked_again_keeps_the_last_usable_answer(llm):
    hi5 = SCENARIOS["hi-05"]  # kind: "हाँ जी।" then "बीमा।"; premium: off-topic then "तीस हज़ार।"
    product = answers(llm, hi5)
    assert isinstance(product.kind, Stated) and product.kind.evidence.quote == "बीमा।"
    assert isinstance(product.premium, Stated) and product.premium.value == "तीस हज़ार"


def test_a_later_unusable_reply_does_not_erase_an_answer(llm):
    hi5 = SCENARIOS["hi-05"]
    llm.say("KindReply", "बीमा।", status="unclear", kind=None, clauses=[])
    llm.say("KindReply", "हाँ जी।", status="stated", kind="deposit", clauses=[1])
    kind = answers(llm, hi5).kind
    assert isinstance(kind, Stated) and kind.value == "deposit"


def test_a_premium_corrected_at_read_back_replaces_the_first_one(llm):
    hi4 = SCENARIOS["hi-04"]  # "चालीस हज़ार था।", then "नहीं, इकतालीस हज़ार था।", then "हाँ, अब सही है।"
    product = answers(llm, hi4)
    assert product.premium.value == "इकतालीस हज़ार"
    assert product.premium.evidence.quote == "नहीं, इकतालीस हज़ार था।"
    assert product.premium_readback.value is True
    assert run_text_case(hi4.transcript, hi4.record, llm).verdict is CLEAR


def test_a_rejected_read_back_with_no_new_amount_is_not_clear(llm):
    hi4 = SCENARIOS["hi-04"]
    llm.say("ReadbackReply", "नहीं, इकतालीस हज़ार था।", corrected_amount_span=None)
    assert run_text_case(hi4.transcript, hi4.record, llm).verdict is not CLEAR


def test_a_correction_is_ignored_when_the_customer_confirmed(llm):
    llm.say("ReadbackReply", "हाँ जी, बिल्कुल ठीक।", corrected_amount_span="बिल्कुल ठीक")
    assert answers(llm).premium.value == "चौबीस हज़ार"


def test_dont_know_keeps_the_customers_words(llm):
    hi2 = SCENARIOS["hi-02"]
    cover = answers(llm, hi2).cover
    assert isinstance(cover, DontKnow)
    assert cover.evidence.quote in "कवर? कवर का मुझे नहीं पता।"


# --- inputs that are not a call about this loan ----------------------------------------------


def test_a_transcript_for_another_loan_is_refused(llm):
    other = HI.record.model_copy(update={"loan_id": "LN-OTHER"})
    with pytest.raises(ValueError, match="loan"):
        extract(HI.transcript, other, llm)


def test_a_question_about_a_product_that_is_not_on_the_record_is_refused(llm):
    turns = [t.model_dump() | ({"product_id": "P9"} if t.product_id else {}) for t in HI.transcript.turns]
    transcript = Transcript.model_validate(HI.transcript.model_dump() | {"turns": turns})
    with pytest.raises(ValueError, match="P9"):
        extract(transcript, HI.record, llm)


def test_output_that_never_validates_makes_only_that_field_unclear(llm):
    llm.invalid.add(KIND)
    extraction = extract_traced(HI.transcript, HI.record, llm)
    kind = extraction.raw.products[0].kind
    assert isinstance(kind, Unclear) and kind.reason is GapReason.extraction_failed
    assert {(t.kind, t.screen) for t in extraction.slots if t.failed} <= {(SlotKind.kind, False), (SlotKind.kind, True)}
    assert extraction.raw.products[0].premium.status == "stated"


def test_one_consent_reply_fills_every_product(llm):
    second = HI.record.products[0].model_copy(update={"id": "P2"})
    record = LoanRecord.model_validate(HI.record.model_dump() | {"products": [*HI.record.products, second]})
    raw = extract(HI.transcript, record, llm)
    assert [p.product_id for p in raw.products] == ["P1", "P2"]
    assert raw.products[1].consent_given == raw.products[0].consent_given
    assert isinstance(raw.products[1].consent_method, Stated)
    assert raw.products[1].kind.status == "not_asked"  # no question named P2


# --- evidence the model cannot cut, and exchanges the model never sees ------------------------

CANCEL = "हाँ बताया था, तीस दिन के अंदर रद्द करवा सकते हैं।"


def with_reply(scenario, old: str, new: str) -> Transcript:
    turns = [t.model_dump() | ({"text": new} if t.text == old else {}) for t in scenario.transcript.turns]
    assert sum(t["text"] == new for t in turns) == 1
    return Transcript.model_validate(scenario.transcript.model_dump() | {"turns": turns})


def test_an_answer_quotes_the_whole_reply_so_a_later_negation_is_never_cut_off(llm):
    said = "रद्द करवा सकते हैं, ऐसा किसी ने नहीं बताया, तीस दिन की बात सुनी थी।"
    llm.say(
        "CancelReply", said,
        allowed_status="stated", allowed=True, allowed_clauses=[1],
        window_status="stated", window_span="तीस दिन", window_clauses=[3],
    )  # fmt: skip
    product = extract(with_reply(HI, CANCEL, said), HI.record, llm).products[0]
    assert product.cancel_allowed.evidence.quote == said
    assert product.cancel_window.evidence.quote == said


def test_dont_know_and_enum_answers_quote_the_whole_reply_too(llm):
    hi2 = SCENARIOS["hi-02"]
    product = answers(llm, hi2)
    assert product.cover.evidence.quote == "कवर? कवर का मुझे नहीं पता।"
    assert product.kind.evidence.quote == "एफ़डी है, मैनेजर साहब ने यही बताया था।"


def test_a_concern_quote_is_widened_to_its_whole_clause(llm):
    said = "बीमा है, किसी ने नहीं कहा कि हर बात पर हाँ कहना।"
    llm.say("KindReply", said, status="stated", kind="insurance", clauses=[1])
    llm.say(
        "ScreenReply", said, claims=[], concerns=[{"concern": "coached_answers", "span": "हर बात पर हाँ कहना"}]
    )
    raw = extract(with_reply(HI, KIND, said), HI.record, llm)
    assert [c.evidence.quote for c in raw.sale_concerns] == ["किसी ने नहीं कहा कि हर बात पर हाँ कहना"]


def test_a_claim_quote_is_widened_to_its_whole_clause(llm):
    said = "बीमा है, यह एफ़डी है ऐसा किसी ने नहीं बोला।"
    llm.say("KindReply", said, status="stated", kind="insurance", clauses=[1])
    llm.say("ScreenReply", said, claims=[{"claim": "is_deposit", "span": "यह एफ़डी है"}], concerns=[])
    raw = extract(with_reply(HI, KIND, said), HI.record, llm)
    assert [c.evidence.quote for c in raw.products[0].volunteered_claims] == ["यह एफ़डी है ऐसा किसी ने नहीं बोला"]


def test_a_recall_item_quote_is_widened_to_its_whole_clause(llm):
    said = "बीमा नहीं लिया था सिर्फ़ लोन लिया, चौबीस हज़ार कटे थे।"
    llm.say("RecallReply", said, items=[{"span": "बीमा", "kind": "insurance", "amount_span": "चौबीस हज़ार"}],
            took_nothing=False)
    run = run_text(with_reply(HI, RECALL, said), HI.record, llm)
    (item,) = run.beliefs.recall.items
    assert item.evidence.quote == "बीमा नहीं लिया था सिर्फ़ लोन लिया"
    assert item.amount_inr == 24000  # the amount is still read from anywhere in the reply


def test_the_identity_checks_are_never_sent_to_the_model(llm):
    """The right-party question names the borrower and the second check asks a birth year."""
    born = "उन्नीस सौ अट्ठासी में हुआ था जी।"
    transcript = with_reply(HI, "1988", born)
    extract(transcript, HI.record, llm)
    identity = [t for t in transcript.turns if t.step in ("right_party_check", "second_check")]
    assert len(identity) == 4
    prompts = llm.prompts()
    assert not [t.text for t in identity if t.text in prompts]


# --- the default client -----------------------------------------------------------------------


class _Client:
    """Stands in for `LlmClient`: records the options of each request and replays the dev outputs."""

    _model = "vendor/reasoning-model"

    def __init__(self) -> None:
        self.fake = FakeLlm(recorded_outputs())
        self.temperatures: list[object] = []

    def complete(self, schema, messages, *, temperature=0.0, **options):
        self.temperatures.append(temperature)
        return self.fake.complete(schema, messages, **options)


@pytest.mark.parametrize(("takes", "sent"), [(False, {None}), (True, {0.0})])
def test_the_default_client_leaves_out_temperature_for_a_model_that_rejects_it(monkeypatch, takes, sent):
    client = _Client()
    monkeypatch.setattr(pipeline.LlmClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.setattr(pipeline, "takes_temperature", lambda model: takes)
    assert run_text_case(HI.transcript, HI.record).verdict is CLEAR
    assert set(client.temperatures) == sent
