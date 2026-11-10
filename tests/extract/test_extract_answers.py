"""How answers are kept: a question asked twice, a failed model call, parallel requests, hedges.

The call is the small synthetic one in `extractkit` (an informed customer on a clean record), with
one exchange changed per test.
"""

import random
import time

import pytest
from extractkit import BASE, PRODUCT, answered, build, record, swap

from samajh.clients.errors import (
    AuthError,
    BadResponse,
    CapExceeded,
    ConfigError,
    LlmOutputInvalid,
    RateLimited,
    ServerError,
    TransportError,
)
from samajh.extract import SlotKind, extract, extract_traced
from samajh.pipeline import run_text
from samajh.types import (
    AnswerConflict,
    Evidence,
    GapReason,
    PaymentFrequency,
    Question,
    Stated,
    Tier,
    Unclear,
)

KIND_Q, KIND_AGAIN = "वह क्या है: बीमा, एफ़डी, या कुछ और?", "एक बार फिर: बीमा, एफ़डी, या कुछ और?"
PREMIUM_Q, PREMIUM_AGAIN = "उसके लिए आपने कितने रुपये दिए?", "एक बार फिर, कितने रुपये दिए?"
READBACK_Q = "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?"


def kind_row(reply: str, question: str = KIND_Q, **output):
    return ("teach_back", "kind", question, reply, output)


def premium_row(reply: str, question: str = PREMIUM_Q, **output):
    return ("teach_back", "premium", question, reply, output)


def product(rows):
    transcript, llm = build(rows)
    return extract(transcript, record(), llm).products[0]


def quotes(conflict: AnswerConflict) -> list[str]:
    return [e.quote for e in conflict.answers]


# --- a question asked twice --------------------------------------------------------------------


def test_the_baseline_call_has_no_conflict_and_is_clear():
    transcript, llm = build(BASE)
    run = run_text(transcript, record(), llm)
    assert run.extraction.raw.products[0].conflicts == ()
    assert run.result.tier is Tier.clear


def test_a_kind_answered_fd_and_then_insurance_keeps_both_answers():
    """Verifier case 10: the FD answer used to leave no trace."""
    rows = swap(
        BASE,
        "kind",
        kind_row("एफ़डी है, जमा किया है।", status="stated", kind="deposit", clauses=[1]),
        kind_row("अच्छा, बीमा।", KIND_AGAIN, status="stated", kind="insurance", clauses=[2]),
    )
    transcript, llm = build(rows)
    run = run_text(transcript, record(), llm)
    answers = run.extraction.raw.products[0]
    assert answers.kind.value == "insurance"  # the field holds the last usable answer
    (conflict,) = answers.conflicts
    assert conflict.question is Question.kind
    assert quotes(conflict) == ["एफ़डी है, जमा किया है।", "अच्छा, बीमा।"]
    assert [e.turn_id for e in conflict.answers] == [8, 10]
    assert run.result.tier is not Tier.clear


def test_a_payment_answered_cash_and_then_from_the_loan_keeps_both_answers():
    """Verifier case 11."""
    rows = swap(
        BASE,
        "payment_source",
        ("teach_back", "payment_source", "वह रकम कैसे चुकाई गई?", "अलग से नकद दिया था।",
         {"status": "stated", "source": "separately", "clauses": [1]}),
        ("teach_back", "payment_source", "लोन की रकम में से, या अलग से?", "लोन में से।",
         {"status": "stated", "source": "from_loan", "clauses": [1]}),
    )  # fmt: skip
    transcript, llm = build(rows)
    run = run_text(transcript, record(), llm)
    answers = run.extraction.raw.products[0]
    assert answers.payment_source.value == "from_loan"
    (conflict,) = answers.conflicts
    assert conflict.question is Question.payment_source
    assert quotes(conflict) == ["अलग से नकद दिया था।", "लोन में से।"]
    assert run.result.tier is not Tier.clear


def test_the_same_answer_twice_is_no_conflict():
    rows = swap(
        BASE,
        "kind",
        kind_row("बीमा है।", status="stated", kind="insurance", clauses=[1]),
        kind_row("हाँ, बीमा ही है।", KIND_AGAIN, status="stated", kind="insurance", clauses=[2]),
    )
    answers = product(rows)
    assert answers.conflicts == ()
    assert answers.kind.evidence.quote == "हाँ, बीमा ही है।"


def test_an_answer_and_then_i_do_not_know_is_no_conflict_and_the_answer_stands():
    rows = swap(
        BASE,
        "kind",
        kind_row("एफ़डी है।", status="stated", kind="deposit", clauses=[1]),
        kind_row("पता नहीं।", KIND_AGAIN, status="dont_know", kind=None, clauses=[1]),
    )
    answers = product(rows)
    assert answers.kind.value == "deposit"
    assert [e.quote for e in answers.kind.also] == ["पता नहीं।"]
    assert answers.conflicts == ()


def test_i_do_not_know_and_then_an_answer_is_no_conflict_and_keeps_the_earlier_reply():
    rows = swap(
        BASE,
        "kind",
        kind_row("पता नहीं।", status="dont_know", kind=None, clauses=[1]),
        kind_row("अच्छा, बीमा है।", KIND_AGAIN, status="stated", kind="insurance", clauses=[1]),
    )
    transcript, llm = build(rows)
    run = run_text(transcript, record(), llm)
    answers = run.extraction.raw.products[0]
    assert answers.kind.value == "insurance"
    assert [e.quote for e in answers.kind.also] == ["पता नहीं।"]
    assert answers.conflicts == ()
    assert run.result.tier is Tier.clear


@pytest.mark.parametrize(
    ("first", "first_span", "second", "second_span"),
    [
        ("करीब इकतालीस हज़ार।", "करीब इकतालीस हज़ार", "41,300 रुपये।", "41,300"),  # approximate, then exact inside it
        ("इकतालीस हज़ार रुपये।", "इकतालीस हज़ार", "41,300 रुपये।", "41,300"),  # within one percent
        ("चालीस बयालीस हज़ार के आसपास।", "चालीस बयालीस हज़ार के आसपास", "41,300।", "41,300"),
    ],
)
def test_amounts_consistent_with_each_other_are_no_conflict(first, first_span, second, second_span):
    """The dialogue re-asks an amount whenever its two speech readings disagree."""
    rows = swap(
        BASE,
        "premium",
        premium_row(first, status="stated", span=first_span, clauses=[1]),
        premium_row(second, PREMIUM_AGAIN, status="stated", span=second_span, clauses=[1]),
    )
    transcript, llm = build(rows)
    run = run_text(transcript, record(), llm)
    assert run.extraction.raw.products[0].conflicts == ()
    assert run.result.tier is Tier.clear


def test_an_unusable_reply_neither_replaces_an_answer_nor_conflicts_with_it():
    rows = swap(
        BASE,
        "kind",
        kind_row("एफ़डी है।", status="stated", kind="deposit", clauses=[1]),
        kind_row("जी, बोलिए।", KIND_AGAIN, status="unclear", kind=None, clauses=[]),
    )
    answers = product(rows)
    assert answers.kind.value == "deposit"
    assert answers.conflicts == ()


def test_three_answers_list_each_change_once_in_call_order():
    rows = swap(
        BASE,
        "kind",
        kind_row("एफ़डी है।", status="stated", kind="deposit", clauses=[1]),
        kind_row("एफ़डी ही है।", KIND_AGAIN, status="stated", kind="deposit", clauses=[1]),
        kind_row("नहीं, बीमा है।", "आख़िरी बार: बीमा या एफ़डी?", status="stated", kind="insurance", clauses=[2]),
    )
    assert [quotes(c) for c in product(rows).conflicts] == [["एफ़डी है।", "नहीं, बीमा है।"]]


def test_one_amount_said_in_words_and_then_in_digits_is_no_conflict():
    rows = swap(
        BASE,
        "premium",
        premium_row("इकतालीस हज़ार तीन सौ रुपये।", status="stated", span="इकतालीस हज़ार तीन सौ", clauses=[1]),
        premium_row("41,300 रुपये।", PREMIUM_AGAIN, status="stated", span="41,300", clauses=[1]),
    )
    answers = product(rows)
    assert answers.conflicts == ()
    assert answers.premium.value == "41,300"


def test_two_different_amounts_are_a_conflict():
    rows = swap(
        BASE,
        "premium",
        premium_row("इकतीस हज़ार रुपये।", status="stated", span="इकतीस हज़ार", clauses=[1]),
        premium_row("इकतालीस हज़ार तीन सौ।", PREMIUM_AGAIN, status="stated", span="इकतालीस हज़ार तीन सौ", clauses=[1]),
    )
    answers = product(rows)
    assert answers.premium.value == "इकतालीस हज़ार तीन सौ"
    (conflict,) = answers.conflicts
    assert conflict.question is Question.premium
    assert quotes(conflict) == ["इकतीस हज़ार रुपये।", "इकतालीस हज़ार तीन सौ।"]


def test_two_different_durations_are_a_conflict():
    rows = swap(
        BASE,
        "term",
        ("teach_back", "term", "वह कितने समय के लिए है?", "एक साल।",
         {"status": "stated", "span": "एक साल", "clauses": [1]}),
        ("teach_back", "term", "एक बार फिर, कितने समय के लिए?", "छत्तीस महीने।",
         {"status": "stated", "span": "छत्तीस महीने", "clauses": [1]}),
        ("teach_back", "term", "आख़िरी बार, कितने समय के लिए?", "तीन साल।",
         {"status": "stated", "span": "तीन साल", "clauses": [1]}),
    )  # fmt: skip
    (conflict,) = product(rows).conflicts
    assert conflict.question is Question.term
    assert quotes(conflict) == ["एक साल।", "छत्तीस महीने।"]  # 36 months and three years read the same


def test_a_question_with_two_fields_gives_one_conflict():
    question = "क्या बताया गया था कि कैंसल कर सकते हैं, और कब तक?"
    rows = swap(
        BASE,
        "cancel_window",
        ("teach_back", "cancel_window", question, "हाँ, पंद्रह दिन के अंदर।",
         {"allowed_status": "stated", "allowed": True, "allowed_clauses": [1], "window_status": "stated",
          "window_span": "पंद्रह दिन", "window_clauses": [2]}),
        ("teach_back", "cancel_window", "एक बार फिर, कब तक?", "नहीं बताया था, तीस दिन शायद।",
         {"allowed_status": "stated", "allowed": False, "allowed_clauses": [1], "window_status": "stated",
          "window_span": "तीस दिन", "window_clauses": [2]}),
    )  # fmt: skip
    (conflict,) = product(rows).conflicts
    assert conflict.question is Question.cancel_window
    assert quotes(conflict) == ["हाँ, पंद्रह दिन के अंदर।", "नहीं बताया था, तीस दिन शायद।"]


def test_a_premium_corrected_at_the_read_back_replaces_it_and_is_no_conflict():
    rows = [
        *BASE[:-1],
        ("read_back", "premium", READBACK_Q, "नहीं, बयालीस हज़ार था।",
         {"status": "stated", "confirms": False, "clauses": [1], "corrected_amount_span": "बयालीस हज़ार"}),
        ("read_back", "premium", "बयालीस हज़ार, यानी 42,000 रुपये, सही है?", "हाँ।",
         {"status": "stated", "confirms": True, "clauses": [1], "corrected_amount_span": None}),
    ]  # fmt: skip
    answers = product(rows)
    assert answers.premium.value == "बयालीस हज़ार"
    assert answers.premium.evidence.quote == "नहीं, बयालीस हज़ार था।"
    assert answers.premium_readback.value is True
    assert answers.conflicts == ()


def test_the_last_read_back_reply_replaces_an_earlier_yes():
    rows = [
        *BASE,
        ("read_back", "premium", "एक बार फिर: 41,300 रुपये, सही है?", "जी?",
         {"status": "unclear", "confirms": None, "clauses": [], "corrected_amount_span": None}),
    ]  # fmt: skip
    answers = product(rows)
    assert isinstance(answers.premium_readback, Unclear)
    assert answers.conflicts == ()


# --- the span goes to the rules as the model returned it ---------------------------------------


def test_a_word_next_to_the_number_is_never_trimmed_from_the_span():
    """Verifier case 12: "सारे" is speech-to-text for "साढ़े" (three and a half lakh, not three)."""
    three_lakh = PRODUCT.model_copy(update={"premium_inr": 300000})
    rows = answered(BASE, "premium", "सारे तीन लाख रुपये।", span="सारे तीन लाख")
    rows = [(r[0], r[1], "तीन लाख, यानी 3,00,000 रुपये, सही है?", *r[3:]) if r[0] == "read_back" else r for r in rows]
    transcript, llm = build(rows)
    run = run_text(transcript, record(three_lakh), llm)
    assert run.extraction.raw.products[0].premium.value == "सारे तीन लाख"
    assert not isinstance(run.beliefs.products[0].premium_inr, Stated)
    assert run.result.tier is not Tier.clear


def test_a_verb_copied_into_the_span_is_passed_on_and_still_reads():
    """Verifier iter2: "चौबीस हज़ार रुपये लगे" must parse. The parser reads the span with its neighbours."""
    rows = answered(BASE, "premium", "इकतालीस हज़ार तीन सौ कटे थे।", span="इकतालीस हज़ार तीन सौ कटे")
    transcript, llm = build(rows)
    run = run_text(transcript, record(), llm)
    assert run.extraction.raw.products[0].premium.value == "इकतालीस हज़ार तीन सौ कटे"
    assert run.beliefs.products[0].premium_inr.value == 41300


def test_a_recall_amount_is_passed_on_untrimmed():
    rows = swap(
        BASE,
        None,
        ("open_recall", None, BASE[0][2], "एक बीमा लिया था, सारे तीन लाख का।",
         {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": "सारे तीन लाख का"}],
          "took_nothing": False}),
    )  # fmt: skip
    transcript, llm = build(rows)
    (item,) = extract(transcript, record(), llm).recall.items
    assert item.amount_text == "सारे तीन लाख का"


# --- a failed model call -----------------------------------------------------------------------

FAILURES = [
    LlmOutputInvalid(model="fake", attempts=3, last_error="not valid JSON"),
    BadResponse("no choices"),
    TransportError("connection reset"),
    RateLimited(status=429, code=None, message="slow down"),
    ServerError(status=502, code=None, message="bad gateway"),
]
MUST_RAISE = [
    CapExceeded(unit="USD", cap=0.1, spent=0.1, estimate=0.01),
    AuthError(status=401, code=None, message="no"),
    ConfigError("no key"),
]


@pytest.mark.parametrize("error", FAILURES, ids=lambda e: type(e).__name__)
def test_a_failed_answer_call_makes_that_field_unclear_and_leaves_the_rest(error):
    transcript, llm = build(BASE)
    llm.errors[("KindReply", "बीमा है।")] = error
    run = run_text(transcript, record(), llm)
    answers = run.extraction.raw.products[0]
    assert answers.kind == Unclear(
        reason=GapReason.extraction_failed, evidence=Evidence(quote="बीमा है।", turn_id=8)
    )
    assert answers.premium.value == "इकतालीस हज़ार तीन सौ"
    failed = [(t.kind, t.screen, t.failed) for t in run.extraction.slots if t.failed]
    assert failed == [(SlotKind.kind, False, type(error).__name__)]
    assert run.result.tier is Tier.incomplete


def test_a_failed_call_fills_every_field_of_its_question():
    transcript, llm = build(BASE)
    llm.invalid.add("लोन और बीमा, बीमे का ओटीपी दिया था।")
    answers = extract(transcript, record(), llm).products[0]
    for answer in (answers.consent_given, answers.consent_method):
        assert isinstance(answer, Unclear) and answer.reason is GapReason.extraction_failed


def test_a_failed_call_on_a_re_ask_makes_the_field_unclear_whatever_came_before():
    """Verifier iter2 cases 2 and 3: a failed re-ask must never be dropped."""
    rows = swap(
        BASE,
        "kind",
        kind_row("बीमा है।", status="stated", kind="insurance", clauses=[1]),
        kind_row("अच्छा, एफ़डी।", KIND_AGAIN, status="stated", kind="deposit", clauses=[2]),
    )
    transcript, llm = build(rows)
    llm.errors[("KindReply", "अच्छा, एफ़डी।")] = BadResponse("no choices")
    run = run_text(transcript, record(), llm)
    kind = run.extraction.raw.products[0].kind
    assert isinstance(kind, Unclear) and kind.reason is GapReason.extraction_failed
    assert kind.evidence.quote == "अच्छा, एफ़डी।"
    assert run.result.tier is Tier.incomplete


def test_a_failed_first_asking_is_not_hidden_by_a_later_answer():
    rows = swap(
        BASE,
        "payment_source",
        ("teach_back", "payment_source", "वह रकम कैसे चुकाई गई?", "अलग से नकद दिया था।", {}),
        ("teach_back", "payment_source", "फिर से बताइए?", "लोन में से।",
         {"status": "stated", "source": "from_loan", "clauses": [1]}),
    )  # fmt: skip
    transcript, llm = build(rows)
    llm.errors[("PaymentReply", "अलग से नकद दिया था।")] = TransportError("reset")
    run = run_text(transcript, record(), llm)
    source = run.extraction.raw.products[0].payment_source
    assert isinstance(source, Unclear) and source.reason is GapReason.extraction_failed
    assert run.result.tier is Tier.incomplete


def test_a_failed_read_back_call_replaces_an_earlier_yes():
    rows = [*BASE, ("read_back", "premium", "एक बार फिर: 41,300 रुपये, सही है?", "नहीं नहीं, गलत है।", {})]
    transcript, llm = build(rows)
    llm.errors[("ReadbackReply", "नहीं नहीं, गलत है।")] = TransportError("timeout")
    readback = extract(transcript, record(), llm).products[0].premium_readback
    assert isinstance(readback, Unclear) and readback.reason is GapReason.extraction_failed


@pytest.mark.parametrize("error", FAILURES, ids=lambda e: type(e).__name__)
def test_a_failed_screening_call_lists_the_reply_as_unscreened(error):
    transcript, llm = build(BASE)
    reply = "लोन और बीमा, बीमे का ओटीपी दिया था।"
    llm.errors[("ScreenReply", reply)] = error
    run = run_text(transcript, record(), llm)
    raw = run.extraction.raw
    assert raw.unscreened == (Evidence(quote=reply, turn_id=24),)
    assert raw.products[0].consent_given.value is True  # the answer call of the same reply stands
    assert [(t.screen, t.failed) for t in run.extraction.slots if t.failed] == [(True, type(error).__name__)]
    assert run.result.tier is not Tier.clear


def test_a_failed_open_recall_call_is_not_read_as_naming_nothing():
    transcript, llm = build(BASE)
    llm.invalid.add("एक बीमा लिया था।")
    run = run_text(transcript, record(), llm)
    raw = run.extraction.raw
    assert raw.recall.items == () and raw.recall.denial is None
    assert Evidence(quote="एक बीमा लिया था।", turn_id=6) in raw.unscreened
    assert run.result.tier is not Tier.clear


def test_a_failure_trace_holds_the_error_name_and_nothing_said_on_the_call():
    transcript, llm = build(BASE)
    llm.errors[("KindReply", "बीमा है।")] = BadResponse("बीमा है। sk-or-secret")
    (trace,) = [t for t in extract_traced(transcript, record(), llm).slots if t.failed]
    assert trace.failed == "BadResponse"
    assert "बीमा" not in repr(trace) and "secret" not in repr(trace)


@pytest.mark.parametrize("error", MUST_RAISE, ids=lambda e: type(e).__name__)
@pytest.mark.parametrize("schema", ["KindReply", "ScreenReply"])
@pytest.mark.parametrize("max_workers", [1, 8])
def test_an_error_that_no_retry_can_fix_still_raises(error, schema, max_workers):
    transcript, llm = build(answered(BASE, "kind", "बीमा है, लोन वाला।"))
    llm.errors[(schema, "बीमा है, लोन वाला।")] = error
    with pytest.raises(type(error)):
        extract_traced(transcript, record(), llm, max_workers=max_workers)


# --- requests in parallel ----------------------------------------------------------------------


class Slow:
    """The fake LLM, answering after a random wait."""

    def __init__(self, llm, seed: int) -> None:
        self.llm, self.rng = llm, random.Random(seed)

    def complete(self, schema, messages, **options):
        time.sleep(self.rng.uniform(0, 0.02))
        return self.llm.complete(schema, messages, **options)


def test_the_result_is_the_same_for_one_worker_and_for_eight():
    rows = swap(
        BASE,
        "kind",
        kind_row("एफ़डी है, जमा किया है।", status="stated", kind="deposit", clauses=[1]),
        kind_row("अच्छा, बीमा।", KIND_AGAIN, status="stated", kind="insurance", clauses=[2]),
    )
    transcript, llm = build(rows)
    llm.errors[("ScreenReply", "लोन में से कटा था।")] = ServerError(status=500, code=None, message="x")
    llm.invalid.add("तीन साल।")
    one = extract_traced(transcript, record(), Slow(llm, 1), max_workers=1)
    eight = extract_traced(transcript, record(), Slow(llm, 2), max_workers=8)
    assert one.raw == eight.raw
    assert one.raw.products[0].conflicts and one.raw.unscreened

    def order(extraction):
        return [(t.turn_id, t.kind, t.screen, t.failed) for t in extraction.slots]

    assert order(one) == order(eight)
    assert [t.turn_id for t in one.slots] == sorted(t.turn_id for t in one.slots)


def test_requests_do_run_at_the_same_time():
    transcript, llm = build(BASE)
    running, most = 0, 0

    class Counting:
        def complete(self, schema, messages, **options):
            nonlocal running, most
            running += 1
            most = max(most, running)
            time.sleep(0.01)
            running -= 1
            return llm.complete(schema, messages, **options)

    extract(transcript, record(), Counting(), max_workers=8)
    assert most > 1
    running = most = 0
    extract(transcript, record(), Counting(), max_workers=1)
    assert most == 1


def test_run_text_takes_max_workers():
    transcript, llm = build(BASE)
    one, eight = (run_text(transcript, record(), llm, max_workers=n) for n in (1, 8))
    assert (one.extraction.raw, one.beliefs, one.result) == (eight.extraction.raw, eight.beliefs, eight.result)


# --- payment frequency -------------------------------------------------------------------------

FREQUENCY_Q = "वह पैसा एक ही बार देना था, या बार-बार?"


def frequency_row(reply: str, **output):
    return ("teach_back", "payment_frequency", FREQUENCY_Q, reply, output)


def test_a_call_that_never_asks_the_frequency_leaves_it_not_asked():
    assert product(BASE).payment_frequency.status == "not_asked"


@pytest.mark.parametrize(
    ("reply", "frequency"),
    [("एकमुश्त।", PaymentFrequency.one_time), ("हर साल भरना है।", PaymentFrequency.recurring)],
)
def test_the_frequency_question_fills_payment_frequency(reply, frequency):
    rows = [*BASE[:4], frequency_row(reply, status="stated", frequency=frequency.value, clauses=[1]), *BASE[4:]]
    transcript, llm = build(rows)
    answers = extract(transcript, record(), llm).products[0]
    assert answers.payment_frequency == Stated(value=frequency, evidence=Evidence(quote=reply, turn_id=14))
    assert any("FrequencyReply" in str(type(s)) or FREQUENCY_Q in s[1].content for s in llm.sent)


def test_two_different_frequencies_are_a_conflict():
    rows = [
        *BASE[:4],
        frequency_row("एक ही बार दिया।", status="stated", frequency="one_time", clauses=[1]),
        frequency_row("हर साल भरना है।", status="stated", frequency="recurring", clauses=[1]),
        *BASE[4:],
    ]
    (conflict,) = product(rows).conflicts
    assert conflict.question is Question.payment_frequency


# --- hedged answers ----------------------------------------------------------------------------


def test_an_answer_said_with_doubt_is_stated_and_marked_hedged():
    reply = "वापस तो नहीं मिलेगा शायद, बीमा है ना।"
    answers = product(answered(BASE, "features", reply, clauses=[1]))
    assert answers.feature_probe == Stated(value=(), evidence=Evidence(quote=reply, turn_id=22), hedged=True)


def test_an_answer_said_plainly_is_not_hedged():
    answers = product(BASE)
    stated = [a for a in (getattr(answers, name) for name in type(answers).model_fields) if isinstance(a, Stated)]
    assert len(stated) >= 12
    assert not any(a.hedged for a in stated)


def test_the_marker_comes_from_the_reply_whatever_the_model_returns():
    reply = "शायद बीमा है।"
    assert product(answered(BASE, "kind", reply)).kind.hedged is True


def test_an_amount_said_approximately_keeps_its_approximation_words():
    reply = "ठीक से याद नहीं, पचास बावन हज़ार के आसपास था।"
    answers = product(answered(BASE, "premium", reply, span="पचास बावन हज़ार के आसपास", clauses=[2]))
    assert answers.premium.value == "पचास बावन हज़ार के आसपास"
    assert answers.premium.hedged is True


def test_a_duration_tied_to_the_loan_is_stated_in_the_customers_words():
    answers = product(answered(BASE, "term", "जब तक लोन चलेगा।", span="जब तक लोन चलेगा"))
    assert answers.term == Stated(value="जब तक लोन चलेगा", evidence=Evidence(quote="जब तक लोन चलेगा।", turn_id=18))


# --- open recall: "I took nothing" -------------------------------------------------------------


def recall_row(reply: str, **output):
    return ("open_recall", None, BASE[0][2], reply, {"items": [], "took_nothing": False} | output)


def test_saying_nothing_was_taken_is_kept_as_a_denial():
    reply = "कुछ नहीं लिया, बस लोन लिया था।"
    transcript, llm = build(swap(BASE, None, recall_row(reply, took_nothing=True)))
    recall = extract(transcript, record(), llm).recall
    assert recall.denial == Evidence(quote=reply, turn_id=6)
    assert recall.answer == recall.denial and recall.items == ()


def test_not_remembering_is_not_a_denial():
    transcript, llm = build(swap(BASE, None, recall_row("याद नहीं।")))
    recall = extract(transcript, record(), llm).recall
    assert recall.denial is None and recall.answer.quote == "याद नहीं।"


def test_a_denial_survives_a_re_asked_recall():
    """Verifier iter2 case 11."""
    first = recall_row("कुछ नहीं लिया, बस लोन।", took_nothing=True)
    again = ("open_recall", None, "और कुछ लिया था लोन के साथ?", "याद नहीं आ रहा।", {"items": [], "took_nothing": False})
    transcript, llm = build([first, again, *BASE[1:]])
    run = run_text(transcript, record(), llm)
    assert run.extraction.raw.recall.denial.quote == "कुछ नहीं लिया, बस लोन।"
    # The customer names insurance at the kind question, so the denial is retracted.
    assert "recall_not_named" in [f.reason.value for f in run.result.all_flags()]
    assert run.result.tier is Tier.understanding_gap


def test_a_denial_stands_when_the_customer_later_calls_it_an_fd():
    first = recall_row("कुछ नहीं लिया, बस लोन।", took_nothing=True)
    fd = kind_row("एफ़डी है।", status="stated", kind="deposit", clauses=[1])
    transcript, llm = build(swap(swap(BASE, None, first), "kind", fd))
    run = run_text(transcript, record(), llm)
    assert "recall_denied" in [f.reason.value for f in run.result.all_flags()]
    assert run.result.tier is Tier.refer


def test_a_denial_is_retracted_when_the_customer_names_the_kind():
    """Verifier iter2 case 12, under the coordinator's rule: the rest of the call is informed."""
    transcript, llm = build(swap(BASE, None, recall_row("कुछ नहीं लिया, बस लोन।", took_nothing=True)))
    run = run_text(transcript, record(), llm)
    assert run.result.tier is Tier.understanding_gap


def test_a_denial_next_to_a_named_item_is_not_kept():
    items = [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}]
    transcript, llm = build(swap(BASE, None, recall_row("एक बीमा लिया था।", items=items, took_nothing=True)))
    recall = extract(transcript, record(), llm).recall
    assert recall.denial is None and len(recall.items) == 1
