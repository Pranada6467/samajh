"""Behaviour of the Part C customer's reply rules (eval/openbench/part_c_customer.reply), offline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "eval" / "openbench", ROOT / "eval" / "acq"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import part_c_customer as pc  # noqa: E402
from acq_common import u  # noqa: E402

CID = "ACQ-T003"  # a premium draw below its kind draw, for the recall test
RECORD = {"products": [{"kind": "credit_life", "premium_inr": 25000, "paid_from_loan": True,
                        "features": ["one_time_payment"], "required_for_loan": False, "cover_inr": 400000,
                        "term_months": 12, "cancel_window_days": 30, "consent": {"method": "otp"}}]}  # fmt: skip
TOPICS = list(pc.FIELD_TOPICS)
KNOW = {"replies": {t: {v: f"{t}-{v}" for v in ("own", "again", "defer")} for t in TOPICS}}


def customer(**states):
    belief = {
        "kind": {"state": "correct", "value": "insurance"}, "premium": {"state": "correct", "value": 25000},
        "source": {"state": "correct", "value": "from_loan"}, "frequency": {"state": "correct", "value": "one_time"},
        "required": {"state": "correct", "value": False}, "cover": {"state": "correct", "value": 400000},
        "term": {"state": "correct", "value": 12}, "cancel": {"state": "correct", "value": 30},
        "money_back": {"state": "correct", "value": False}, "consent": {"state": "correct", "value": "otp"},
    }  # fmt: skip
    belief.update(states)
    return {"id": CID, "gender": "f", "belief": belief}


def item(kind, asks=False, states=None):
    return pc.RouterItem(kind=kind, asks=asks, states_span=states)


def say(c, items, r=0.0, a=0.0, history=(), utterance=None):
    if utterance is None:  # every span is inside the utterance unless a test says otherwise
        utterance = " ".join(i.states_span or "" for i in items) + " आप बात कर रहे हैं"
    return pc.reply(c, KNOW, RECORD, r, a, items, list(history), utterance=utterance)


def test_value_equal_to_belief_is_yes():
    text, _ = say(customer(), [item("how_much", states="25000")])
    assert text == pc.YES


def test_dk_yes_only_below_r():
    ur = u(CID, "premium", "r")
    c = customer(premium={"state": "dk", "value": None})
    assert say(c, [item("how_much", states="25000")], r=min(1.0, ur + 0.01))[0] == pc.YES
    assert say(c, [item("how_much", states="25000")], r=ur)[0] == "how_much-own"


def test_false_belief_hearing_record_value_yes_only_below_a():
    ua = u(CID, "source", "a")
    c = customer(source={"state": "false", "value": "separately"})
    assert say(c, [item("how_paid", states="लोन अमाउंट से कटा")], a=min(1.0, ua + 0.01))[0] == pc.YES
    assert say(c, [item("how_paid", states="लोन अमाउंट से कटा")], a=ua)[0] == "how_paid-own"


def test_value_equal_to_neither_gives_own():
    c = customer(premium={"state": "false", "value": 50000})
    assert say(c, [item("how_much", states="99000")], a=1.0)[0] == "how_much-own"


def test_term_in_years_is_months():
    assert say(customer(), [item("how_long", states="1 साल")])[0] == pc.YES


def test_two_confirmed_fields_say_one_yes():
    text, choices = say(customer(), [item("how_much", states="25000"), item("how_long", states="12 महीने"),
                                     item("understood_check", asks=True)])  # fmt: skip
    assert text == pc.YES
    assert sum(c["variant"] == "yes" for c in choices) == 2


def test_yes_comes_first_then_other_replies():
    c = customer(cover={"state": "dk", "value": None})
    text, _ = say(c, [item("what_it_gives", states="400000"), item("how_much", states="25000")])
    assert text == f"{pc.YES} what_it_gives-own"


def test_open_question_defers_below_a():
    ua = u(CID, "term", "a")
    assert say(customer(), [item("how_long", asks=True)], a=min(1.0, ua + 0.01))[0] == "how_long-defer"
    assert say(customer(), [item("how_long", asks=True)], a=ua)[0] == "how_long-own"


def test_reask_gives_again():
    _, first = say(customer(), [item("how_long", asks=True)])
    assert say(customer(), [item("how_long", asks=True)], history=first)[0] == "how_long-again"


def test_recall_follows_premium_draw():
    ua_k, ua_p = u(CID, "kind", "a"), u(CID, "premium", "a")
    if ua_p >= ua_k:
        pytest.skip("this id's draws do not separate the two rules")
    a = (ua_p + ua_k) / 2
    assert say(customer(), [item("what_did_you_take", asks=True)], a=a)[0] == "what_is_it-own"


def test_nothing_mapped_is_unmapped():
    text, _ = say(customer(), [item("other")])
    assert pc.is_unmapped(text)


def test_third_party():
    assert pc.third_party_reply("ACQ-C021", [item("identity", asks=True)])[0].startswith("नहीं जी, मैं उनकी बहन")
    assert pc.third_party_reply("ACQ-C001", [item("how_much", asks=True)])[0] == pc.THIRD_PARTY_NOTHING


def test_schemas_are_strict():
    from part_c_agent import AgentTurn

    from samajh.clients.llm import strict_json_schema

    strict_json_schema(pc.RouterOut)
    strict_json_schema(AgentTurn)


def test_span_not_in_utterance_is_open_question():
    text, _ = say(customer(), [item("how_long", asks=True, states="12 महीने")], utterance="यह कितने समय चलेगा?")
    assert text == "how_long-own"


def test_unreadable_span_is_open_question():
    text, _ = say(customer(), [item("how_much", asks=True, states="प्रीमियम")], utterance="प्रीमियम कितना था?")
    assert text == "how_much-own"


def test_consent_keywords():
    assert pc.normalise_span("consent", "OTP डालकर") == "otp"
    assert pc.normalise_span("consent", "app में accept") == "digital_click"
    assert pc.normalise_span("money_back", "पैसे वापस नहीं मिलते") == "no"
    assert pc.normalise_span("required", "ज़रूरी नहीं था") == "no"


def test_identity_ignored_after_first_answer_unless_asked():
    _, first = say(customer(), [item("identity", asks=True)], utterance="क्या मैं अमित जी से बात कर रहा हूँ?")
    assert say(customer(), [item("identity", asks=True)], history=first, utterance="अमित जी, प्रीमियम क्या था?")[0] \
        == pc.NOT_UNDERSTOOD
    assert say(customer(), [item("identity", asks=True)], history=first, utterance="आप कौन बोल रहे हैं?")[0] \
        == pc.identity_reply("f")


def test_closing_is_low_priority():
    assert say(customer(), [item("closing"), item("how_long", asks=True)])[0] == "how_long-own"


def test_kind_refer_back_ignored_once_kind_known():
    _, first = say(customer(), [item("what_is_it", states="इंश्योरेंस")], utterance="आपने इंश्योरेंस लिया था?")
    text, choices = say(customer(), [item("what_is_it", states="इंश्योरेंस"), item("how_much", asks=True)],
                        history=first, utterance="इंश्योरेंस का प्रीमियम कितना था?")  # fmt: skip
    assert text == "how_much-own"
    assert choices[0]["rule"] == "kind_refer_back"


def test_span_words_in_order_ground():
    assert pc.grounded_span("30 दिन", "इसे 30 के अंदर, यानी दिन में, रद्द") is not None
    assert pc.grounded_span("दिन 30", "इसे 30 दिन में रद्द") is None
    assert pc.grounded_span("OTP, डालकर", "क्या आपने OTP डालकर सहमति दी?") is not None


def test_enum_in_open_question_is_no_value():
    u = "क्या आपको पता है कि पैसा वापस मिलता है या नहीं?"
    assert pc.normalise_span("money_back", "वापस मिलता है", u) is None
    assert pc.normalise_span("consent", "OTP", "क्या आपने OTP डालकर सहमति दी थी?") == "otp"
    assert pc.normalise_span("kind", "इंश्योरेंस", "आपने जो इंश्योरेंस लिया वह क्या है?") is None
    assert pc.normalise_span("money_back", "पैसे वापस नहीं मिलते",
                             "क्या आपको पता है कि पैसे वापस नहीं मिलते?") == "no"


def test_any_questions_dropped_when_field_asked():
    assert say(customer(), [item("any_questions", asks=True), item("how_long", asks=True)])[0] == "how_long-own"


def test_duplicate_topic_keeps_asked_one():
    text, choices = say(customer(), [item("how_long"), item("how_long", asks=True)])
    assert text == "how_long-own"
    assert choices[0]["rule"] == "duplicate"


def test_unread_span_in_question_counts_as_asked():
    u = "क्या आपको पता है कि पैसा वापस मिलता है या नहीं?"
    assert say(customer(), [item("money_back", states="वापस मिलता है")], utterance=u)[0] == "money_back-own"
    assert pc.is_unmapped(say(customer(), [item("money_back", states="वापस मिलता है")],
                              utterance=u.replace("?", "।"))[0])
