"""The P5 reply chooser: which frozen reply a customer gives to the bot's last utterance.

A pure function of (customer, level, condition, the bot's lines, what the customer said before in
this call), so a resumed call repeats it. It knows nothing of text or voice: the text runner passes
`samajh.dialogue.Line`s, a voice runner can pass the same fields read from a session log.

Rules (eval/p5/RUNNER-PLAN.md Part 1 "Rules fixed now"; topics.json `disposition`):
- the topic comes from the last line's key (`OPEN_TOPIC`), or from a rule for the read-backs and the
  go-ahead after a verification answer (`RULE_KEYS`); a key in `NO_REPLY` is never answered (said
  before a question line, or at the end of the call);
- a key the player cannot map, or a no-reply key that ends an utterance, gets `not_understood`, and
  the choice says so (`mapped=False`): logged and counted, never skipped;
- the variant: on a grouped matter where the draw says the customer gives way, `defer` (asked again:
  `defer` again); otherwise `own` the first time and `again` on a re-ask (`own` if there is none).
  The "terse" condition gives `go_along` where one was written, first time and on a re-ask;
- a read-back is right when the figure the bot read back equals the figure `samajh.amounts` reads in
  the customer's own latest reply that carried one for that item; the gold belief is not used.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from bank import Customer, Topics, gives_way

from samajh.amounts import Approximate, Parsed, parse_amount, parse_approx_amount

Condition = Literal["disposition", "terse"]


@dataclass(frozen=True)
class BotLineView:
    """What the player needs of one bot line."""

    key: str
    text: str
    step: str | None = None
    asks: str | None = None
    slots: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Said:
    """A reply the customer gave earlier in this call."""

    topic: str
    variant: str
    text: str


@dataclass(frozen=True)
class Choice:
    topic: str
    variant: str
    text: str
    line_key: str  # the bot line it answers
    mapped: bool = True
    note: str | None = None
    readback: dict[str, Any] | None = None  # the read-back comparison, when there was one


# Line key -> topic, for the keys that need no rule. From `samajh.dialogue.LINES` as of 2568759.
OPEN_TOPIC: dict[str, str] = {
    "right_party.ask": "is_this_you",
    # The direct question "are you <name> yourself?" (with no second check, the step after a yes to the name).
    "right_party.reask": "is_this_you_again",
    # Mid-call after a sign of another speaker: "are you <name> yourself, or someone in their place?"
    "right_party.who_check": "is_this_you_again",
    "disclosure.reask": "can_we_talk",
    "second_check.ask": "year_of_birth",
    "second_check.reask": "year_of_birth",
    "open_recall.ask": "what_did_you_take",
    "open_recall.reask": "what_did_you_take",
    "open_recall.nothing": "anything_else",
    "kind.ask": "what_is_it",
    "kind.ask_named": "what_is_it",  # the kind question when the customer named something at open recall
    "kind.reask": "what_is_it",
    "premium.ask": "how_much",
    "premium.reask": "how_much",
    "premium.say_again": "say_amount_again",
    "payment_source.ask": "how_paid",
    "payment_source.reask": "how_paid",
    "payment_frequency.ask": "how_often",
    "payment_frequency.reask": "how_often",
    "required_for_loan.ask": "needed_or_choice",
    "required_for_loan.reask": "needed_or_choice",
    "provider_choice.ask": "where_to_take_it_from",
    "provider_choice.reask": "where_to_take_it_from",
    "cover.ask": "what_it_gives",
    "cover.reask": "what_it_gives",
    "cover.say_again": "what_it_gives",  # Part 1: answered with `what_it_gives`, as a re-ask
    "term.ask": "how_long",
    "term.reask": "how_long",
    "cancel_window.ask": "can_cancel",
    "cancel_window.reask": "can_cancel",
    "features.ask": "money_back",
    "features.reask": "money_back",
    "consent.ask": "what_you_agreed_to",
    "consent.reask": "what_you_agreed_to",
    "stop_check.decline": "carry_on",
    "stop_check.disengaged": "carry_on",
    "stop_check.human": "want_a_person",
    "callback.when": "when_to_call",
}

# Keys whose topic a rule picks (`topic_for`).
RULE_KEYS: frozenset[str] = frozenset({
    "disclosure.go_ahead",  # can_we_talk, or can_we_talk_after_check after a verification answer
    "read_back.confirm", "read_back.confirm_about", "read_back.reconfirm", "read_back.cover_confirm",
    "read_back.restate",
})  # fmt: skip

# Keys never answered: said before the question line of the same utterance, or at the end of a call.
NO_REPLY: frozenset[str] = frozenset({
    "purpose.before_confirm", "disclosure.who", "disclosure.not_sales", "disclosure.recording",
    "disclosure.never_ask", "disclosure.rights", "verify.before_loan", "verify.after_loan", "verify.short",
    "context.loan", "teach_back.intro", "teach_back.intro_nth", "bridge.moving_on",
    "ack.neutral",  # "जी।" said only before a teach-back question line (machine._ack), never last
    "end.third_party", "end.neutral", "end.check_failed", "end.declined", "end.human", "end.call_back",
    "end.language", "end.no_response", "end.do_not_call", "end.written",
    "close.thanks", "close.may_call_back", "close.verify", "close.bye",
})  # fmt: skip

# Topics whose reply may carry the figure a read-back repeats, by item.
FIGURE_TOPICS: dict[str, frozenset[str]] = {
    "premium": frozenset({"what_did_you_take", "how_much", "say_amount_again", "what_is_right_amount",
                          "figure_read_back_wrong"}),
    "cover": frozenset({"what_it_gives", "benefit_read_back_wrong"}),
}  # fmt: skip

NOT_UNDERSTOOD = "not_understood"
VERIFY_ANSWERS = frozenset({"verify.before_loan", "verify.after_loan"})


def figure_of(text: str) -> tuple[int, int] | None:
    """An amount in `text` as (low, high), read the way the dialogue reads one: a hedge or a narrow
    range first (`parse_approx_amount`), else exactly one amount (`parse_amount`); None otherwise."""
    approx = parse_approx_amount(text)
    if isinstance(approx, Approximate):
        return approx.low, approx.high
    parsed = parse_amount(text)
    if isinstance(parsed, Parsed):
        return parsed.rupees, parsed.rupees
    return None


def _readback(last: BotLineView, history: Sequence[Said]) -> tuple[str, dict[str, Any]]:
    item = "cover" if last.asks == "cover" else "premium"
    read = figure_of(last.slots.get("amount_words") or last.text)
    own = next((s for s in reversed(history) if s.topic in FIGURE_TOPICS[item] and figure_of(s.text)), None)
    said = figure_of(own.text) if own else None
    right = read is not None and said is not None and read == said
    info = {"item": item, "bot_read_back": read, "customer_said": said,
            "customer_topic": own.topic if own else None, "right": right}  # fmt: skip
    if right:
        return "figure_read_back_right", info
    return ("benefit_read_back_wrong" if item == "cover" else "figure_read_back_wrong"), info


def topic_for(lines: Sequence[BotLineView], history: Sequence[Said]) -> tuple[str | None, dict | None]:
    """The topic the last line asks about, or None when the player has no mapping for it."""
    last = lines[-1]
    if last.key == "disclosure.go_ahead":
        # Only the answer to "who is calling / is this genuine?" (`_on_reply`'s `before`), not `verify.short`,
        # which the disclosure now says on every call.
        verified = any(line.key in VERIFY_ANSWERS for line in lines)
        return ("can_we_talk_after_check" if verified else "can_we_talk"), None
    if last.key in ("read_back.confirm", "read_back.confirm_about", "read_back.reconfirm",
                    "read_back.cover_confirm"):  # fmt: skip
        return _readback(last, history)
    if last.key == "read_back.restate":
        return ("benefit_read_back_wrong" if last.asks == "cover" else "what_is_right_amount"), None
    return OPEN_TOPIC.get(last.key), None


def _variant(
    customer: Customer, topics: Topics, topic: str, level: float, condition: Condition, again: bool
) -> str:
    written = customer.open[topic]
    if condition == "terse" and "go_along" in written:
        return "go_along"
    if topic in topics.defer_topics and "defer" in written and \
            gives_way(topics.seed, customer.id, topics.group.get(topic), level):  # fmt: skip
        return "defer"
    if again and "again" in written:
        return "again"
    return "own"


def choose_open(
    customer: Customer,
    topics: Topics,
    level: float,
    condition: Condition,
    lines: Sequence[BotLineView],
    history: Sequence[Said],
) -> Choice:
    """The customer's reply to the bot's last utterance in the open call (and the shared opening)."""
    if not lines:
        raise ValueError("no bot line to answer")
    last = lines[-1]
    topic, readback = topic_for(lines, history)
    note = None
    if topic is None:
        note = f"no-reply line {last.key!r} ended an utterance" if last.key in NO_REPLY \
            else f"unmapped line key {last.key!r}"  # fmt: skip
        return Choice(NOT_UNDERSTOOD, "own", customer.open[NOT_UNDERSTOOD]["own"], last.key, False, note)
    again = (
        last.key.endswith(".reask") or last.key == "cover.say_again" or any(s.topic == topic for s in history)
    )
    variant = _variant(customer, topics, topic, level, condition, again)
    return Choice(topic, variant, customer.open[topic][variant], last.key, True, note, readback)


def choose_closed(customer: Customer, topics: Topics, level: float, statement_id: str) -> Choice:
    """The reply to one closed statement: `go_along` where the draw says the customer gives way, else `own`."""
    group = topics.closed_group[statement_id]
    variant = "go_along" if gives_way(topics.seed, customer.id, group, level) else "own"
    return Choice(statement_id, variant, customer.closed[statement_id][variant], statement_id)
