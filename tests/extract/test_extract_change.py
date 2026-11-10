"""The change check: a second, independent model look at a reply of two or more clauses.

It never adds a conflict: a correction whose final answer stands keeps the earlier words (clause runs
resolved by code) in `also`; otherwise the stated answer is taken away. The call is the small synthetic one in `extractkit` (an informed customer
on a clean record), with one exchange changed per test; the check's output is scripted with
`llm.say("ChangeReply", reply, ...)`, and an unscripted check replays as "none".
"""

import hashlib
import json

import pytest
from extractkit import BASE, answered, build, record, swap

from samajh.clients.errors import LlmOutputInvalid, TransportError
from samajh.clients.llm import strict_json_schema
from samajh.extract import SlotKind, extract, extract_traced
from samajh.extract._ground import Reply
from samajh.extract._prompt import change_messages, messages, screen_messages
from samajh.extract._wire import SCHEMA, ScreenReply
from samajh.pipeline import run_text
from samajh.rules.summary import summarise
from samajh.types import (
    DontKnow,
    Evidence,
    GapReason,
    Language,
    ProductResult,
    Question,
    Stated,
    Tier,
    Unclear,
)

KIND_Q = "वह क्या है: बीमा, एफ़डी, या कुछ और?"
READBACK_Q = "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?"


def change(llm, reply: str, label: str, first=(), final=()) -> None:
    llm.say("ChangeReply", reply, change=label, first_clauses=list(first), final_clauses=list(final))


def kind_call(reply: str, **output):
    return build(answered(BASE, "kind", reply, **output))


def turn(transcript, reply: str) -> int:
    (found,) = [t.id for t in transcript.turns if t.text == reply]
    return found


def run(transcript, llm, workers: int = 8):
    return run_text(transcript, record(), llm, max_workers=workers)


# --- which replies are checked, and what the check is shown -----------------------------------


def test_only_replies_of_two_or_more_clauses_to_a_checked_question_get_the_check():
    transcript, llm = build(BASE)
    traces = extract_traced(transcript, record(), llm).slots
    checked = {t.turn_id for t in traces if t.check}
    answered_turns = {t.turn_id for t in traces if not t.check and not t.screen}
    many = {t.id for t in transcript.turns if t.id in answered_turns and len(Reply(t.text).clauses()) >= 2}
    assert checked == many
    assert checked  # BASE has several two-clause replies ("नहीं, मर्ज़ी से लिया।")
    assert answered_turns - checked  # and single-clause ones ("बीमा है।")
    single = next(t for t in transcript.turns if t.text == "बीमा है।")
    assert single.id not in checked


# The requests as they were before the change check existed (recorded from the unmodified code).
# The answer and screening requests are cached by their bytes; the frozen-set comparison needs them unchanged.
_BEFORE = {
    "all answer requests": "f5375055ed087ceb046255e73924df2f4dc8a14a3e11e84b9b1aefbe6fcd61fd",
    "kind/hi": "f806afa2443d2bea3a66a3d974b74f51cc1ae836b20fc81ef397d5405ba4f8f6",
    "screen": "035244ade3520822432eacaa889e1a087d13fdc6d0812902004d88ecf89fd1c8",
}


def _digest(body: object) -> str:
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def test_the_answer_and_screening_requests_are_byte_identical_to_before_the_check():
    q, r = KIND_Q, "बीमा है, नहीं नहीं, एफ़डी है।"
    each = {
        f"{kind}/{lang}": _digest(
            {"m": [m.model_dump() for m in messages(kind, lang, q, r)], "s": strict_json_schema(schema)}
        )
        for kind, schema in SCHEMA.items()
        for lang in Language
    }
    screen = {
        "m": [m.model_dump() for m in screen_messages(Language.hi, q, r)],
        "s": strict_json_schema(ScreenReply),
    }
    each["screen"] = _digest(screen)
    assert each["kind/hi"] == _BEFORE["kind/hi"]
    assert each["screen"] == _BEFORE["screen"]
    assert (
        hashlib.sha256(json.dumps(each, sort_keys=True).encode()).hexdigest()
        == _BEFORE["all answer requests"]
    )


@pytest.mark.parametrize("kind", SCHEMA, ids=lambda k: k.value)
def test_the_check_is_shown_the_numbered_reply_the_answer_call_sees_and_nothing_else(kind):
    q, r = "सवाल?", "पहला हिस्सा, दूसरा हिस्सा।"
    check_user = change_messages(kind, Language.hi, q, r)[1].content
    numbered = messages(SlotKind.kind, Language.hi, q, r)[1].content
    assert check_user == numbered


def test_the_check_is_never_shown_the_first_readings_answer():
    transcript, llm = kind_call("बीमा है, नहीं नहीं, एफ़डी है।", kind="deposit", clauses=[3])
    extract(transcript, record(), llm)
    checks = [req for req in llm.sent if "decide whether the customer" in req[0].content]
    assert len(checks) >= 1
    for request in checks:
        assert "deposit" not in request[1].content and '"kind"' not in request[1].content


# --- none, withdrawn, corrected ----------------------------------------------------------------


def test_none_leaves_the_first_reading_as_it_was():
    reply = "बीमा है, सॉरी, आवाज़ कट रही थी।"
    transcript, llm = kind_call(reply, kind="insurance", clauses=[1])
    change(llm, reply, "none")
    result = run(transcript, llm)
    expected = Stated(value="insurance", evidence=Evidence(quote=reply, turn_id=turn(transcript, reply)))
    assert result.extraction.raw.products[0].kind == expected
    assert result.result.tier is Tier.clear


def test_withdrawn_makes_the_stated_answer_unclear_with_no_conflict():
    reply = "बीमा है, नहीं नहीं, पता नहीं।"
    transcript, llm = kind_call(reply, kind="insurance", clauses=[1])
    change(llm, reply, "withdrawn", first=[1])
    result = run(transcript, llm)
    raw = result.extraction.raw.products[0]
    expected = Evidence(quote=reply, turn_id=turn(transcript, reply))
    assert raw.kind == Unclear(reason=GapReason.no_usable_answer, evidence=expected)
    assert raw.conflicts == ()
    assert result.result.tier is not Tier.clear


def test_a_correction_to_the_record_answer_stands_with_the_earlier_words_beside_it_and_ends_clear():
    reply = "डिपॉज़िट... अरे नहीं, बीमा है, बीमा।"
    transcript, llm = kind_call(reply, kind="insurance", clauses=[3, 4])
    change(llm, reply, "corrected", first=[1], final=[3, 4])
    result = run(transcript, llm)
    raw = result.extraction.raw.products[0]
    tid = turn(transcript, reply)
    assert raw.kind == Stated(
        value="insurance",
        evidence=Evidence(quote=reply, turn_id=tid),
        also=(Evidence(quote="डिपॉज़िट", turn_id=tid),),
    )
    assert raw.conflicts == ()
    (product,) = result.result.products
    assert [[e.quote for e in c.answers] for c in product.self_corrections] == [["डिपॉज़िट", reply]]
    assert product.self_corrections[0].question is Question.kind
    assert result.result.tier is Tier.clear
    summary = summarise(record(), result.result)
    assert summary.tier is Tier.clear
    (note,) = summary.lines
    assert note.note is True and note.tier is Tier.clear and note.quote == reply
    assert note.title == 'Customer first said "डिपॉज़िट" about what the product is, then corrected it in the same reply.'


def test_a_correction_to_a_wrong_answer_refers_through_the_value_and_the_summary_shows_the_earlier_words():
    reply = "बीमा... अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="deposit", clauses=[3])
    change(llm, reply, "corrected", first=[1], final=[3])
    result = run(transcript, llm)
    flags = {(f.rule_id.value, f.reason.value) for f in result.result.all_flags()}
    assert ("kind", "kind_differs") in flags and ("kind", "answers_conflict") not in flags
    assert result.result.tier is Tier.refer
    summary = summarise(record(), result.result)
    notes = [line for line in summary.lines if line.note]
    assert [(n.title, n.quote, n.tier) for n in notes] == [
        (
            'Customer first said "बीमा" about what the product is, then corrected it in the same reply.',
            reply,
            Tier.clear,
        )
    ]
    assert summary.lines[-1].note and summary.tier is Tier.refer


def test_a_first_reading_on_the_retracted_clause_is_unusable_and_incomplete():
    reply = "बीमा... अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="insurance", clauses=[1])
    change(llm, reply, "corrected", first=[1], final=[3])
    result = run(transcript, llm)
    raw = result.extraction.raw.products[0]
    assert raw.kind == Unclear(evidence=Evidence(quote=reply, turn_id=turn(transcript, reply)))
    assert result.result.products[0].self_corrections == ()
    assert result.result.tier is Tier.incomplete


def test_a_first_reading_that_also_points_at_the_correction_words_stands():
    reply = "डिपॉज़िट... अरे नहीं, बीमा है, बीमा।"
    transcript, llm = kind_call(reply, kind="insurance", clauses=[2, 3, 4])  # as gpt-6-luna answered
    change(llm, reply, "corrected", first=[1], final=[3, 4])
    kind = extract(transcript, record(), llm).products[0].kind
    assert kind.value == "insurance" and [e.quote for e in kind.also] == ["डिपॉज़िट"]


@pytest.mark.parametrize("pointer", [[2], [1, 3], [1, 2]])
def test_a_first_reading_that_touches_the_first_clauses_or_misses_the_final_ones_is_unusable(pointer):
    reply = "बीमा... अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="deposit", clauses=pointer)
    change(llm, reply, "corrected", first=[1], final=[3])
    assert isinstance(extract(transcript, record(), llm).products[0].kind, Unclear)


def test_a_correction_of_an_amount_points_at_the_clause_of_its_span():
    reply = "बत्तीस हज़ार, नहीं, इकतालीस हज़ार तीन सौ।"
    transcript, llm = build(answered(BASE, "premium", reply, span="इकतालीस हज़ार तीन सौ", clauses=[]))
    change(llm, reply, "corrected", first=[1], final=[3])
    raw = extract(transcript, record(), llm).products[0]
    assert raw.premium.value == "इकतालीस हज़ार तीन सौ"
    assert [e.quote for e in raw.premium.also] == ["बत्तीस हज़ार"]
    wrong, llm = build(answered(BASE, "premium", reply, span="बत्तीस हज़ार", clauses=[]))
    change(llm, reply, "corrected", first=[1], final=[3])
    assert isinstance(extract(wrong, record(), llm).products[0].premium, Unclear)


def test_a_two_part_question_follows_the_rule_field_by_field():
    """ "Yes, signed a form, no no, by OTP": the method said last stands; an answer on clause 1 does not."""
    reply = "हाँ, फ़ॉर्म पर साइन किया, नहीं नहीं, OTP से।"
    transcript, llm = build(
        answered(BASE, "consent", reply, given=True, given_clauses=[1], method="otp", method_clauses=[4])
    )
    change(llm, reply, "corrected", first=[2], final=[4])
    raw = extract(transcript, record(), llm).products[0]
    assert raw.consent_method.value == "otp"
    assert [e.quote for e in raw.consent_method.also] == ["फ़ॉर्म पर साइन किया"]
    assert isinstance(raw.consent_given, Unclear)


def test_a_self_correction_kept_after_a_re_ask_is_not_lost():
    again = "एक बार फिर: बीमा, एफ़डी, या कुछ और?"
    reply = "डिपॉज़िट... अरे नहीं, बीमा है, बीमा।"
    rows = swap(BASE, "kind",
                ("teach_back", "kind", KIND_Q, "बीमा है।", {"status": "stated", "kind": "insurance", "clauses": [1]}),
                ("teach_back", "kind", again, reply, {"status": "stated", "kind": "insurance", "clauses": [3]}))  # fmt: skip
    transcript, llm = build(rows)
    change(llm, reply, "corrected", first=[1], final=[3, 4])
    kind = extract(transcript, record(), llm).products[0].kind
    assert [e.quote for e in kind.also] == ["डिपॉज़िट", "बीमा है।"]


def test_tier_and_verdict_never_depend_on_self_corrections():
    reply = "बीमा... अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="deposit", clauses=[3])
    change(llm, reply, "corrected", first=[1], final=[3])
    result = run(transcript, llm).result
    product = result.products[0]
    assert product.self_corrections
    stripped = product.model_copy(update={"self_corrections": ()})
    assert (stripped.tier, stripped.verdict) == (product.tier, product.verdict)
    assert ProductResult.model_validate(stripped.model_dump()).tier is product.tier


@pytest.mark.parametrize(("first", "final"), [((1,), ()), ((), (3,)), ((1,), (9,)), ((0,), (3,))])
def test_corrected_with_a_pointer_that_does_not_resolve_is_unclear_with_no_conflict(first, final):
    reply = "बीमा है, अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="deposit", clauses=[3])
    change(llm, reply, "corrected", first=first, final=final)
    extraction = extract_traced(transcript, record(), llm)
    raw = extraction.raw.products[0]
    assert isinstance(raw.kind, Unclear) and raw.conflicts == ()
    (trace,) = [t for t in extraction.slots if t.check and t.turn_id == turn(transcript, reply)]
    assert trace.bad_pointers and trace.change == "corrected"


def test_corrected_with_overlapping_runs_is_unclear_with_no_conflict():
    reply = "बीमा है, अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, kind="deposit", clauses=[3])
    change(llm, reply, "corrected", first=[1, 2], final=[2, 3])
    raw = extract(transcript, record(), llm).products[0]
    assert isinstance(raw.kind, Unclear) and raw.conflicts == ()


def test_both_fields_of_a_two_part_question_are_taken_away():
    reply = "हाँ, तीस दिन के अंदर, नहीं, पता नहीं।"
    transcript, llm = build(answered(BASE, "cancel_window", reply))
    change(llm, reply, "withdrawn", first=[1, 2])
    raw = extract(transcript, record(), llm).products[0]
    assert isinstance(raw.cancel_allowed, Unclear) and isinstance(raw.cancel_window, Unclear)


def test_a_conflict_across_two_askings_still_refers_beside_a_self_correction():
    again = "एक बार फिर: बीमा, एफ़डी, या कुछ और?"
    reply = "बीमा... अरे नहीं, कोई plan है।"
    rows = swap(BASE, "kind",
                ("teach_back", "kind", KIND_Q, "एफ़डी है।", {"status": "stated", "kind": "deposit", "clauses": [1]}),
                ("teach_back", "kind", again, reply, {"status": "stated", "kind": "other", "clauses": [3]}))  # fmt: skip
    transcript, llm = build(rows)
    change(llm, reply, "corrected", first=[1], final=[3])
    result = run(transcript, llm)
    (conflict,) = result.extraction.raw.products[0].conflicts
    assert [e.quote for e in conflict.answers] == ["एफ़डी है।", reply]
    assert result.result.tier is Tier.refer


# --- what the check may not do ------------------------------------------------------------------


@pytest.mark.parametrize("label", ["withdrawn", "corrected"])
def test_a_dont_know_first_reading_stands_whatever_the_check_says(label):
    reply = "पता नहीं, याद नहीं आ रहा।"
    transcript, llm = kind_call(reply, status="dont_know", kind=None, clauses=[1, 2])
    change(llm, reply, label, first=[1], final=[2])
    raw = extract(transcript, record(), llm).products[0]
    assert isinstance(raw.kind, DontKnow) and raw.conflicts == ()


def test_an_unclear_first_reading_gets_no_conflict_and_no_value():
    reply = "बीमा है, अरे नहीं, एफ़डी है।"
    transcript, llm = kind_call(reply, status="unclear", kind=None, clauses=[])
    change(llm, reply, "corrected", first=[1], final=[3])
    raw = extract(transcript, record(), llm).products[0]
    assert raw.kind == Unclear(evidence=Evidence(quote=reply, turn_id=turn(transcript, reply)))
    assert raw.conflicts == ()


def test_a_yes_to_a_read_back_that_is_taken_back_is_unclear_and_never_a_conflict():
    reply = "हाँ, नहीं नहीं, गलत है।"
    rows = [r if r[0] != "read_back" else (*r[:3], reply, r[4]) for r in BASE]
    transcript, llm = build(rows)
    change(llm, reply, "corrected", first=[1], final=[2, 3])
    raw = extract(transcript, record(), llm).products[0]
    assert (
        isinstance(raw.premium_readback, Unclear)
        and raw.premium_readback.reason is GapReason.no_usable_answer
    )
    assert raw.conflicts == ()
    assert isinstance(raw.premium, Stated)  # the premium said earlier is not touched


def test_a_rejected_read_back_is_left_as_the_first_reading_gave_it():
    reply = "नहीं, गलत है, उनतालीस हज़ार।"
    output = {
        "status": "stated",
        "confirms": False,
        "clauses": [1, 2],
        "corrected_amount_span": "उनतालीस हज़ार",
    }
    rows = [r if r[0] != "read_back" else (*r[:3], reply, output) for r in BASE]
    transcript, llm = build(rows)
    change(llm, reply, "corrected", first=[1, 2], final=[3])
    raw = extract(transcript, record(), llm).products[0]
    assert raw.premium_readback.value is False
    assert raw.premium.value == "उनतालीस हज़ार"


# --- the check fails -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error", [LlmOutputInvalid(model="m", attempts=3, last_error="x"), TransportError("down")]
)
def test_a_failed_check_makes_the_stated_answers_of_its_reply_unclear(error):
    reply = "नहीं, मर्ज़ी से लिया।"  # BASE's reply to the required-for-loan question
    transcript, llm = build(BASE)
    llm.errors[("ChangeReply", reply)] = error
    result = run(transcript, llm)
    raw = result.extraction.raw.products[0]
    expected = Evidence(quote=reply, turn_id=turn(transcript, reply))
    assert raw.required_for_loan == Unclear(reason=GapReason.extraction_failed, evidence=expected)
    assert isinstance(raw.kind, Stated)  # other replies keep their answers
    assert result.result.tier is not Tier.clear
    (trace,) = [t for t in result.extraction.slots if t.check and t.turn_id == turn(transcript, reply)]
    assert trace.failed == type(error).__name__


# --- open recall ---------------------------------------------------------------------------------


def recall_call(reply: str, *items: tuple[str, str], took_nothing: bool = False):
    output = {
        "items": [{"span": s, "kind": k, "amount_span": None} for s, k in items],
        "took_nothing": took_nothing,
    }
    return build(swap(BASE, None, ("open_recall", None, BASE[0][2], reply, output)))


def test_a_recall_reply_that_names_a_thing_and_adds_nothing_else_is_kept():
    reply = "एक बीमा लिया था, और कुछ नहीं।"
    transcript, llm = recall_call(reply, ("एक बीमा", "insurance"))
    change(llm, reply, "none")
    result = run(transcript, llm)
    assert [i.evidence.quote for i in result.extraction.raw.recall.items] == ["एक बीमा लिया था"]
    assert result.extraction.raw.unscreened == ()
    assert result.result.tier is Tier.clear


def test_a_recall_reply_that_names_a_thing_and_then_takes_it_back_drops_it_and_is_unscreened():
    reply = "बीमा लिया था, नहीं नहीं, कुछ नहीं लिया।"
    transcript, llm = recall_call(reply, ("बीमा लिया था", "insurance"))
    change(llm, reply, "withdrawn", first=[1])
    result = run(transcript, llm)
    raw = result.extraction.raw
    assert raw.recall.items == ()
    assert raw.unscreened == (Evidence(quote=reply, turn_id=turn(transcript, reply)),)
    assert result.result.tier is not Tier.clear


def test_a_recall_correction_drops_only_the_items_said_first():
    reply = "एक एफ़डी थी, नहीं, एक बीमा था।"
    transcript, llm = recall_call(reply, ("एक एफ़डी", "deposit"), ("एक बीमा", "insurance"))
    change(llm, reply, "corrected", first=[1], final=[2, 3])
    raw = extract(transcript, record(), llm)
    assert [i.evidence.quote for i in raw.recall.items] == ["एक बीमा था"]
    assert raw.recall.items[0].product_id == "P1"
    assert raw.unscreened == (Evidence(quote=reply, turn_id=turn(transcript, reply)),)


def test_a_recall_change_whose_first_run_does_not_resolve_drops_every_item_of_that_reply():
    reply = "एक एफ़डी थी, नहीं, एक बीमा था।"
    transcript, llm = recall_call(reply, ("एक एफ़डी", "deposit"), ("एक बीमा", "insurance"))
    change(llm, reply, "corrected", first=[7], final=[3])
    raw = extract(transcript, record(), llm)
    assert raw.recall.items == () and raw.unscreened == (
        Evidence(quote=reply, turn_id=turn(transcript, reply)),
    )


def test_a_recall_reply_that_named_nothing_is_left_alone_whatever_the_check_says():
    reply = "कुछ नहीं लिया, बस लोन।"
    transcript, llm = recall_call(reply, took_nothing=True)
    change(llm, reply, "withdrawn", first=[1])
    raw = extract(transcript, record(), llm)
    assert raw.recall.denial == Evidence(quote=reply, turn_id=turn(transcript, reply))
    assert raw.unscreened == ()


def test_a_failed_recall_check_keeps_the_items_and_lists_the_reply_as_unscreened():
    reply = "एक बीमा लिया था, इकतालीस हज़ार का।"
    transcript, llm = recall_call(reply, ("एक बीमा", "insurance"))
    llm.errors[("ChangeReply", reply)] = LlmOutputInvalid(model="m", attempts=3, last_error="x")
    raw = extract(transcript, record(), llm)
    assert len(raw.recall.items) == 1
    assert raw.unscreened == (Evidence(quote=reply, turn_id=turn(transcript, reply)),)


# --- order and parallelism ----------------------------------------------------------------------


def test_the_result_with_checks_is_the_same_for_one_worker_and_for_eight():
    rows = answered(BASE, "kind", "बीमा है, अरे नहीं, एफ़डी है।", kind="deposit", clauses=[3])
    required = "नहीं, ज़रूरी नहीं था, नहीं नहीं, बिल्कुल नहीं।"
    rows = answered(rows, "required_for_loan", required, yes=False, clauses=[1, 2])
    results = []
    for workers in (1, 8):
        transcript, llm = build(rows)
        change(llm, "बीमा है, अरे नहीं, एफ़डी है।", "corrected", first=[1], final=[3])
        change(llm, required, "withdrawn", first=[1, 2])
        llm.errors[("ChangeReply", "हाँ, सही है।")] = TransportError("down")
        results.append(extract(transcript, record(), llm, max_workers=workers))
    assert results[0] == results[1]


def test_a_recall_change_that_took_back_only_a_denial_leaves_the_items_and_the_reply_alone():
    reply = "कुछ नहीं लिया, अरे हाँ, एक बीमा लिया था।"
    transcript, llm = recall_call(reply, ("एक बीमा", "insurance"))
    change(llm, reply, "corrected", first=[1], final=[2, 3])
    raw = extract(transcript, record(), llm)
    assert [i.evidence.quote for i in raw.recall.items] == ["एक बीमा लिया था"]
    assert raw.unscreened == ()
