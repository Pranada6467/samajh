"""The reply chooser: every dialogue line key is accounted for, and the variant rules."""

from __future__ import annotations

import pytest
from bank import Customer, Topics, load_topics
from player import NO_REPLY, OPEN_TOPIC, RULE_KEYS, BotLineView, Said, choose_closed, choose_open

from samajh.dialogue import LINES


def test_every_dialogue_line_key_is_mapped_or_listed_as_no_reply() -> None:
    mapped, rules, silent = set(OPEN_TOPIC), set(RULE_KEYS), set(NO_REPLY)
    assert not (mapped & rules or mapped & silent or rules & silent)
    assert set(LINES) - (mapped | rules | silent) == set(), "new dialogue line keys need a mapping"
    assert (mapped | rules | silent) - set(LINES) == set(), "mapped keys the dialogue no longer has"


def test_every_mapped_topic_is_a_frozen_topic() -> None:
    assert set(OPEN_TOPIC.values()) <= set(load_topics().group)


def _customer() -> Customer:
    def t(name: str, *variants: str) -> dict[str, str]:
        return {v: f"{name}:{v}" for v in variants}

    return Customer(
        id="P5-TEST",
        kind="misled",
        language="hi",
        record_id="r",
        speaker={},
        gold={"class": "problem"},
        writer_model_by_arm={"open": "a", "closed": "a", "defer": "a"},
        open={
            "how_much": {
                "own": "बावन हज़ार दिए थे",
                "again": "बावन हज़ार",
                "go_along": "बावन",
                "defer": "छोड़िए",
            },
            "what_is_it": t("what_is_it", "own", "again", "go_along", "defer"),
            "can_we_talk": t("can_we_talk", "own"),
            "can_we_talk_after_check": t("can_we_talk_after_check", "own"),
            "what_it_gives": {"own": "चार लाख", "again": "चार लाख", "go_along": "चार लाख", "defer": "आगे"},
            "figure_read_back_right": t("right", "own"),
            "figure_read_back_wrong": t("wrong", "own"),
            "benefit_read_back_wrong": t("benefit_wrong", "own"),
            "not_understood": t("not_understood", "own"),
        },
        closed={"c_kind": t("c_kind", "own", "go_along")},
    )


TOPICS = Topics(seed="s", group={"how_much": "premium", "what_is_it": "kind", "what_it_gives": "cover"},
                defer_topics=frozenset({"how_much", "what_is_it", "what_it_gives"}), variants={},
                closed_group={"c_kind": "kind"}, levels_text=(0.0, 1.0))  # fmt: skip


def line(key: str, **kw) -> BotLineView:
    return BotLineView(key=key, text=kw.pop("text", key), **kw)


def test_own_first_then_again_on_a_reask() -> None:
    c = _customer()
    first = choose_open(c, TOPICS, 0.0, "disposition", [line("kind.ask")], [])
    assert (first.topic, first.variant) == ("what_is_it", "own")
    said = [Said(first.topic, first.variant, first.text)]
    second = choose_open(c, TOPICS, 0.0, "disposition", [line("kind.reask")], said)
    assert (second.topic, second.variant) == ("what_is_it", "again")


def test_a_customer_who_gives_way_defers_and_repeats_it() -> None:
    c = _customer()
    first = choose_open(c, TOPICS, 1.0, "disposition", [line("kind.ask")], [])
    again = choose_open(
        c, TOPICS, 1.0, "disposition", [line("kind.reask")], [Said("what_is_it", "defer", "x")]
    )
    assert first.variant == again.variant == "defer"


def test_terse_uses_go_along() -> None:
    assert choose_open(_customer(), TOPICS, 0.0, "terse", [line("kind.ask")], []).variant == "go_along"


def test_go_ahead_after_a_verification_answer() -> None:
    c = _customer()
    plain = choose_open(
        c, TOPICS, 0.0, "disposition", [line("disclosure.who"), line("disclosure.go_ahead")], []
    )
    checked = choose_open(
        c, TOPICS, 0.0, "disposition", [line("verify.before_loan"), line("disclosure.go_ahead")], []
    )
    assert plain.topic == "can_we_talk" and checked.topic == "can_we_talk_after_check"
    routine = [line("disclosure.who"), line("verify.short"), line("disclosure.go_ahead")]
    assert choose_open(c, TOPICS, 0.0, "disposition", routine, []).topic == "can_we_talk"


@pytest.mark.parametrize(
    ("read", "asks", "topic"),
    [("बावन हज़ार", "premium", "figure_read_back_right"), ("पचपन हज़ार", "premium", "figure_read_back_wrong"),
     ("पाँच लाख", "cover", "benefit_read_back_wrong"), ("चार लाख", "cover", "figure_read_back_right")],
)  # fmt: skip
def test_read_back_is_judged_against_the_customers_own_figure(read: str, asks: str, topic: str) -> None:
    c = _customer()
    said = [
        Said("how_much", "own", c.open["how_much"]["own"]),
        Said("what_it_gives", "own", c.open["what_it_gives"]["own"]),
    ]
    key = "read_back.cover_confirm" if asks == "cover" else "read_back.confirm"
    choice = choose_open(
        c, TOPICS, 0.0, "disposition", [line(key, asks=asks, slots={"amount_words": read})], said
    )
    assert choice.topic == topic


def test_unmapped_line_gets_not_understood_and_is_flagged() -> None:
    c = _customer()
    choice = choose_open(c, TOPICS, 0.0, "disposition", [line("brand.new_line")], [])
    assert (choice.topic, choice.mapped) == ("not_understood", False)
    ended = choose_open(c, TOPICS, 0.0, "disposition", [line("context.loan")], [])
    assert (ended.topic, ended.mapped) == ("not_understood", False)


def test_closed_reply_follows_the_draw() -> None:
    c = _customer()
    assert choose_closed(c, TOPICS, 0.0, "c_kind").variant == "own"
    assert choose_closed(c, TOPICS, 1.0, "c_kind").variant == "go_along"
