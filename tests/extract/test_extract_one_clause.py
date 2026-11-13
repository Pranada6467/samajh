"""One-clause replies and the change check (P3a round 4).

Speech-to-text can leave a withdrawal unpunctuated ("बीमा है नहीं पता नहीं क्या है"): one clause, so
the clause count alone gave it no check, and four such withdrawals ended `clear` with the withdrawn
value (`references/reviews/iter2/verify-P3a-r3.md`, failure 2). A reply that holds a marker word now
gets the check whatever its clause count. On one clause a correction has no replacement code can
point at, so `withdrawn`, `corrected` or a failed check make the reply's stated answer unusable.
The model is scripted (`extractkit`); an unscripted check replays as "none".
"""

from dataclasses import replace

import pytest
from extractkit import BASE, answered, build, record
from test_extract_carry import assert_not_carried, checked, failing, judged_scripted, premium_outcomes

from samajh.clients.errors import LlmOutputInvalid, TransportError
from samajh.extract import extract_traced
from samajh.extract._extract import _Call, _carries, slots
from samajh.extract._ground import Reply
from samajh.pipeline import run_text
from samajh.types import Evidence, GapReason, Stated, Tier, Unclear

ERRORS = [LlmOutputInvalid(model="m", attempts=3, last_error="x"), TransportError("down")]

# The verifier's four one-clause withdrawals that ended `clear`, each with the question it answered.
WITHDRAWALS = [
    ("kind", "बीमा है नहीं पता नहीं क्या है", {"kind": "insurance"}),
    ("kind", "insurance hai nahi pata nahi", {"kind": "insurance"}),
    ("payment_source", "लोन से कटा था नहीं याद नहीं", {"source": "from_loan"}),
    ("kind", "बीमा है रुकिए मुझे पक्का नहीं पता", {"kind": "insurance"}),
]
FIELD = {"kind": "kind", "payment_source": "payment_source", "required_for_loan": "required_for_loan"}


def one(asks: str, reply: str, **output):
    """BASE with one reply changed, the answer call reading it as stated from clause 1."""
    transcript, llm = build(answered(BASE, asks, reply, status="stated", clauses=[1], **output))
    return transcript, llm


def run(transcript, llm):
    return run_text(transcript, record(), llm)


def turn_of(transcript, reply: str) -> int:
    (found,) = [t.id for t in transcript.turns if t.text == reply]
    return found


@pytest.mark.parametrize(("asks", "reply", "output"), WITHDRAWALS)
def test_a_one_clause_reply_with_a_marker_word_gets_the_check(asks, reply, output):
    assert len(Reply(reply).clauses()) == 1 and Reply(reply).has_change_marker()
    transcript, llm = one(asks, reply, **output)
    traces = extract_traced(transcript, record(), llm).slots
    assert turn_of(transcript, reply) in {t.turn_id for t in traces if t.check}


@pytest.mark.parametrize("reply", ["बीमा है जी", "loan se kata tha", "लोन में से कटा था"])
def test_a_one_clause_reply_without_a_marker_word_gets_no_check(reply):
    transcript, llm = one("kind", reply, kind="insurance")
    traces = extract_traced(transcript, record(), llm).slots
    assert turn_of(transcript, reply) not in {t.turn_id for t in traces if t.check}


@pytest.mark.parametrize(("asks", "reply", "output"), WITHDRAWALS)
def test_a_one_clause_withdrawal_is_unusable_and_never_clear(asks, reply, output):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="withdrawn", first_clauses=[1], final_clauses=[])
    result = run(transcript, llm)
    answer = getattr(result.extraction.raw.products[0], FIELD[asks])
    assert answer == Unclear(evidence=Evidence(quote=reply, turn_id=turn_of(transcript, reply)))
    assert result.result.tier is Tier.incomplete


@pytest.mark.parametrize(
    ("first", "final"),
    [([1], [1]), ([1], []), ([1], [2]), ([], [1])],
    ids=["overlap", "no-final", "out", "no-first"],
)
@pytest.mark.parametrize(
    ("asks", "reply", "output"),
    [
        ("kind", "डिपॉज़िट है अरे नहीं बीमा है", {"kind": "insurance"}),
        ("payment_source", "अलग से दिया था नहीं लोन से कटा", {"source": "from_loan"}),
    ],
)
def test_a_one_clause_correction_has_no_replacement_to_point_at_and_is_unusable(
    asks, reply, output, first, final
):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="corrected", first_clauses=first, final_clauses=final)
    result = run(transcript, llm)
    answer = getattr(result.extraction.raw.products[0], FIELD[asks])
    assert isinstance(answer, Unclear) and answer.reason is GapReason.no_usable_answer
    assert result.result.products[0].self_corrections == ()
    assert result.result.tier is Tier.incomplete


@pytest.mark.parametrize("error", ERRORS)
@pytest.mark.parametrize(("asks", "reply", "output"), WITHDRAWALS[:3])
def test_a_failed_check_on_a_one_clause_marker_reply_is_never_clear(asks, reply, output, error):
    transcript, llm = one(asks, reply, **output)
    llm.errors[("ChangeReply", reply)] = error
    result = run(transcript, llm)
    answer = getattr(result.extraction.raw.products[0], FIELD[asks])
    assert answer == Unclear(
        reason=GapReason.extraction_failed, evidence=Evidence(quote=reply, turn_id=turn_of(transcript, reply))
    )
    assert result.result.tier is not Tier.clear


@pytest.mark.parametrize("reply", ["नहीं मर्ज़ी से लिया", "nahi apni marzi se liya tha", "बिल्कुल नहीं ज़रूरी नहीं था"])
def test_a_one_clause_no_that_is_the_answer_stands_when_the_check_says_none(reply):
    transcript, llm = one("required_for_loan", reply, yes=False)
    llm.say("ChangeReply", reply, change="none", first_clauses=[], final_clauses=[])
    result = run(transcript, llm)
    answer = result.extraction.raw.products[0].required_for_loan
    assert isinstance(answer, Stated) and answer.value is False
    assert result.result.tier is Tier.clear, (result.result.all_flags(), result.result.all_gaps())


def test_a_one_clause_recall_withdrawal_drops_its_items_and_is_unscreened():
    reply = "एक बीमा लिया था नहीं कुछ नहीं लिया"
    rows = [("open_recall", None, BASE[0][2], reply,
             {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}], "took_nothing": False}),
            *BASE[1:]]  # fmt: skip
    transcript, llm = build(rows)
    llm.say("ChangeReply", reply, change="withdrawn", first_clauses=[1], final_clauses=[])
    result = run(transcript, llm)
    raw = result.extraction.raw
    assert raw.recall.items == ()
    assert [e.quote for e in raw.unscreened] == [reply]
    assert result.result.tier is not Tier.clear


# --- the carried premium follows the same rule --------------------------------------------------
# A one-clause recall reply the amount parser accepts although it takes the figure back.
CARRY_WITHDRAWN = "एक बीमा लिया था इकतालीस हज़ार तीन सौ का रुकिए वो लोन की किस्त थी।"


@pytest.mark.parametrize(("label", "first", "final"), [("withdrawn", [1], []), ("corrected", [1], [1])])
def test_a_one_clause_recall_reply_with_a_marker_is_not_carried_after_a_change(label, first, final):
    assert_not_carried(*judged_scripted(CARRY_WITHDRAWN, checked(CARRY_WITHDRAWN, label, first, final)))


@pytest.mark.parametrize("error", ERRORS)
def test_a_one_clause_recall_reply_with_a_marker_and_a_failed_check_is_not_carried(error):
    assert_not_carried(*judged_scripted(CARRY_WITHDRAWN, failing("ChangeReply", CARRY_WITHDRAWN, error)))


def test_a_one_clause_recall_reply_with_a_marker_is_carried_when_its_check_says_none():
    raw, beliefs, result = judged_scripted(CARRY_WITHDRAWN, checked(CARRY_WITHDRAWN, "none"))
    assert isinstance(raw.products[0].premium, Stated)
    assert beliefs.for_product("P1").premium_inr.value == 41300
    assert premium_outcomes(result) == []


def test_a_reply_that_needed_a_check_and_has_none_is_never_carried():
    transcript, _ = build(answered(BASE, None, CARRY_WITHDRAWN))
    (slot,) = [s for s in slots(transcript, record()) if s.turn.text == CARRY_WITHDRAWN]
    answered_only = {_Call.answer: (object(), None)}
    assert _carries(slot, answered_only) is False
    plain = replace(slot, turn=slot.turn.model_copy(update={"text": "एक बीमा लिया था"}))
    assert _carries(plain, answered_only) is True


def test_a_correction_whose_runs_overlap_is_unusable_even_where_the_answer_lies_in_the_final_run():
    reply = "डिपॉज़िट है, अरे नहीं, बीमा है।"
    transcript, llm = one("kind", reply, kind="insurance")
    llm.say("KindReply", reply, clauses=[3])
    llm.say("ChangeReply", reply, change="corrected", first_clauses=[1], final_clauses=[1, 3])
    result = run(transcript, llm)
    assert isinstance(result.extraction.raw.products[0].kind, Unclear)
    assert result.result.tier is Tier.incomplete


# --- a who-knows, forgot or don't-know tail takes the answer back, whatever the check says ------
# The check's prompt reads doubt as leaning to the answer, and gpt-6-luna said `none` on "41300 kya
# pata" (references/reviews/iter3/verify-chain.md, failure 2). Code decides these on one clause.

TAILS = [
    ("kind", "बीमा था भूल गया क्या था", {"kind": "insurance"}),
    ("kind", "insurance tha bhool gaya kya tha", {"kind": "insurance"}),
    ("payment_source", "loan se kata tha kya pata", {"source": "from_loan"}),
    ("required_for_loan", "optional tha kya pata", {"yes": False}),
    ("kind", "बीमा है या कुछ और कौन जाने", {"kind": "insurance"}),
]


@pytest.mark.parametrize(("asks", "reply", "output"), TAILS)
def test_a_one_clause_answer_with_a_take_back_tail_is_unusable_although_the_check_says_none(
    asks, reply, output
):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="none", first_clauses=[], final_clauses=[])
    result = run(transcript, llm)
    answer = getattr(result.extraction.raw.products[0], FIELD[asks])
    assert answer == Unclear(evidence=Evidence(quote=reply, turn_id=turn_of(transcript, reply)))
    assert result.result.tier is Tier.incomplete


def test_a_premium_with_a_who_knows_tail_is_unusable():
    reply = "इकतालीस हज़ार तीन सौ था कौन जाने"
    transcript, llm = build(answered(BASE, "premium", reply, status="stated", span="इकतालीस हज़ार तीन सौ"))
    result = run(transcript, llm)  # the unscripted check replays as "none"
    assert isinstance(result.extraction.raw.products[0].premium, Unclear)
    assert result.result.tier is not Tier.clear


@pytest.mark.parametrize(
    ("asks", "reply", "output"),
    [
        ("kind", "पता नहीं बीमा है", {"kind": "insurance"}),  # "I don't know" first, then the answer
        ("kind", "बीमा है ठीक से याद नहीं", {"kind": "insurance"}),  # doubt about exactness leans
        ("payment_source", "लोन से कटा था पक्का नहीं पता", {"source": "from_loan"}),
    ],
)
def test_doubt_before_the_answer_or_about_exactness_is_not_a_take_back_tail(asks, reply, output):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="none", first_clauses=[], final_clauses=[])
    answer = getattr(run(transcript, llm).extraction.raw.products[0], FIELD[asks])
    assert isinstance(answer, Stated)


@pytest.mark.parametrize(
    "reply",
    ["बीमा लिया था इकतालीस हज़ार तीन सौ का कौन जाने", "बीमा लिया था इकतालीस हज़ार तीन सौ का या कुछ और भूल गया"],
)
def test_a_recall_premium_with_a_take_back_tail_is_not_carried_although_the_check_says_none(reply):
    assert_not_carried(*judged_scripted(reply, checked(reply, "none")))


def test_a_recall_reply_with_a_take_back_tail_drops_its_items_and_is_unscreened():
    reply = "एक बीमा लिया था कौन जाने"
    rows = [("open_recall", None, BASE[0][2], reply,
             {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}], "took_nothing": False}),
            *BASE[1:]]  # fmt: skip
    transcript, llm = build(rows)
    result = run(transcript, llm)
    assert result.extraction.raw.recall.items == ()
    assert [e.quote for e in result.extraction.raw.unscreened] == [reply]
    assert result.result.tier is not Tier.clear


# --- carry without a check: a second and third killing test -------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।",  # two clauses
        "एक बीमा लिया था इकतालीस हज़ार तीन सौ का अरे",  # one clause, a marker word
        "एक बीमा लिया था इकतालीस हज़ार तीन सौ का कौन जाने",  # one clause, a take-back tail
    ],
)
def test_no_reply_that_needed_a_check_is_carried_without_one(text):
    transcript, _ = build(answered(BASE, None, CARRY_WITHDRAWN))
    (slot,) = [s for s in slots(transcript, record()) if s.turn.text == CARRY_WITHDRAWN]
    assert (
        _carries(
            replace(slot, turn=slot.turn.model_copy(update={"text": text})), {_Call.answer: (object(), None)}
        )
        is False
    )


def test_a_premium_is_not_carried_when_the_planner_drops_the_check_the_reply_needed(monkeypatch):
    """End to end: if `_plan` ever stops asking for the check, `_carries` still refuses the carry."""
    from samajh.extract import _extract as ex

    planned = ex._plan
    monkeypatch.setattr(ex, "_plan", lambda t, r: (p for p in planned(t, r) if p[1] is not ex._Call.check))
    raw, _, result = judged_scripted(CARRY_WITHDRAWN, checked(CARRY_WITHDRAWN, "none"))
    assert not isinstance(raw.products[0].premium, Stated)
    assert result.tier is not Tier.clear


# --- iter3 recheck: "या फिर कुछ और", exactness only with its own word, tails about another detail ---


@pytest.mark.parametrize(
    "text",
    [
        "इकतालीस हज़ार तीन सौ कहा था या फिर कुछ और",
        "policy thi 41300 ki ya phir kuch aur",
        "41300 tha ya phir",  # bare "या फिर" at the end
        "बीमा है या कुछ और भी",
        "लोन से या कैश से याद नहीं",  # "से" alone is not exactness
    ],
)
def test_these_tails_take_the_answer_back(text):
    assert Reply(text).has_take_back_tail(other_detail_exempts=True)


@pytest.mark.parametrize(
    "text",
    [
        "loan se kata tha theek se yaad nahi",
        "बीमा है ठीक से याद नहीं",
        "zaroori nahi tha sahi se yaad nahi",
        "बीमा है जो भूल से ले लिया था",  # by mistake
        "ya phir 41300 tha",  # "या फिर" not at the end
    ],
)
def test_exactness_and_by_mistake_are_not_take_back_tails(text):
    assert not Reply(text).has_take_back_tail()


OTHER_DETAIL = [
    ("kind", "बीमा है पता नहीं कितने का", {"kind": "insurance"}),
    ("kind", "बीमा है रकम याद नहीं", {"kind": "insurance"}),
    ("kind", "insurance hai amount yaad nahi", {"kind": "insurance"}),
    ("payment_source", "लोन से कटा था कितना कटा याद नहीं", {"source": "from_loan"}),
    ("payment_source", "loan se kata tha kab kata yaad nahi", {"source": "from_loan"}),
    ("required_for_loan", "ज़रूरी नहीं था बाकी मुझे कुछ नहीं पता", {"yes": False}),
    ("required_for_loan", "nahi zaroori nahi tha baaki pata nahi", {"yes": False}),
    ("kind", "बीमा है जो भूल से ले लिया था", {"kind": "insurance"}),
    ("payment_source", "loan se kata tha theek se yaad nahi", {"source": "from_loan"}),
]


@pytest.mark.parametrize(("asks", "reply", "output"), OTHER_DETAIL)
def test_an_informed_answer_with_a_tail_about_another_detail_stays_clear_when_the_check_says_none(
    asks, reply, output
):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="none", first_clauses=[], final_clauses=[])
    result = run(transcript, llm)
    assert isinstance(getattr(result.extraction.raw.products[0], FIELD[asks]), Stated)
    assert result.result.tier is Tier.clear, (result.result.all_flags(), result.result.all_gaps())


@pytest.mark.parametrize(
    "reply", ["इकतालीस हज़ार तीन सौ था कितना पता नहीं", "41300 tha amount yaad nahi", "41300 kya pata kitne ka"]
)
def test_a_detail_word_never_exempts_a_tail_on_an_amount_question(reply):
    transcript, llm = build(
        answered(
            BASE,
            "premium",
            reply,
            status="stated",
            span=reply.split(" tha")[0].split(" था")[0].split(" kya")[0],
        )
    )
    result = run(transcript, llm)
    assert not isinstance(result.extraction.raw.products[0].premium, Stated)


@pytest.mark.parametrize(
    "reply",
    ["बीमा लिया था इकतालीस हज़ार तीन सौ का या फिर कुछ और", "policy li thi 41300 ki ya phir kuch aur"],
)
def test_a_recall_premium_ending_in_or_something_else_is_not_carried(reply):
    assert_not_carried(*judged_scripted(reply, checked(reply, "none")))


@pytest.mark.parametrize(
    ("asks", "reply", "output"),
    [
        ("kind", "बीमा था या फिर", {"kind": "insurance"}),
        ("payment_source", "loan se ya cash se yaad nahi", {"source": "from_loan"}),
        ("payment_source", "लोन से या कैश से याद नहीं", {"source": "from_loan"}),
    ],
)
def test_an_or_else_tail_or_a_bare_se_before_the_tail_is_taken_back_although_the_check_says_none(
    asks, reply, output
):
    transcript, llm = one(asks, reply, **output)
    llm.say("ChangeReply", reply, change="none", first_clauses=[], final_clauses=[])
    result = run(transcript, llm)
    assert isinstance(getattr(result.extraction.raw.products[0], FIELD[asks]), Unclear)
    assert result.result.tier is Tier.incomplete
