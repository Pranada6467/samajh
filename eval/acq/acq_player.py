"""The ACQ reply chooser for the open call, the fixed entry replies, and the symbolic closed arm.

Pure functions of (customer, knowledge row, a or r, the bot's lines, what the customer said before), so a
resumed call repeats them. Draws: `ua_f = u(cid, f, "a")`, `ur_f = u(cid, f, "r")`, one per customer and
field, shared by both arms and every cell (`acq_common.u`).

Open arm: the topic comes from `player.topic_for` (eval/p5). A field topic (data/acq/topics.json) gets
`defer` when `ua_<field> < a`, else `again` on a re-ask (key ends `.reask`, `cover.say_again`, or the topic
was already answered in this call), else `own`; the text is `knowledge.replies[topic][variant]`, played as
written. Other topics get the canned replies below; anything unmapped gets "जी, समझ नहीं आया।" and the
choice says so (`mapped=False`).

Closed arm (no text, no LLM): belief correct -> yes; false -> yes if `ua_f < a` else no; dk -> yes if
`ur_f < r` else dont_know.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acq_common import DATA, FIELDS, read_jsonl, u
from player import BotLineView, Said, topic_for

# --- entry -----------------------------------------------------------------------------------------

ENTRY_KEYS = ("right_party.ask", "right_party.reask", "disclosure.go_ahead")
SCORED_START_KEY = "open_recall.ask"


def entry_reply(key: str, gender: str) -> str | None:
    """The fixed entry reply to `key`, or None for a key that is not an entry key. The name is never said."""
    if key == "right_party.ask":
        return "हाँ जी।"
    if key == "right_party.reask":
        return "हाँ जी, मैं ख़ुद ही बात कर रहा हूँ।" if gender != "f" else "हाँ जी, मैं ख़ुद ही बात कर रही हूँ।"
    if key == "disclosure.go_ahead":
        return "हाँ जी, बोलिए।"
    return None


# --- open arm --------------------------------------------------------------------------------------

NOT_UNDERSTOOD_TEXT = "जी, समझ नहीं आया।"
CANNED: dict[str, str] = {
    "figure_read_back_right": "हाँ जी, सही है।",
    "carry_on": "हाँ, पूछिए।",
    "want_a_person": "नहीं, आप ही पूछिए।",
    "can_we_talk": "हाँ जी, बोलिए।",
    "can_we_talk_after_check": "हाँ जी, बोलिए।",
    "when_to_call": "अभी बात कर लीजिए।",
}
# Topics answered with the customer's own reply to a field topic: (that topic, its field).
BORROWED: dict[str, tuple[str, str]] = {
    "figure_read_back_wrong": ("how_much", "premium"),
    "what_is_right_amount": ("how_much", "premium"),
    "say_amount_again": ("how_much", "premium"),
    "benefit_read_back_wrong": ("what_it_gives", "cover"),
}


def load_topic_fields(data: Path = DATA) -> dict[str, str]:
    """Field topic id -> belief field, from topics.json."""
    topics = json.loads((data / "topics.json").read_text(encoding="utf-8"))
    return {t["id"]: t["field"] for t in topics["open_call"]}


def load_knowledge(path: Path) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in read_jsonl(path)}


@dataclass(frozen=True)
class AcqChoice:
    topic: str
    variant: str
    text: str
    line_key: str
    mapped: bool = True
    note: str | None = None
    field: str | None = None
    draw_a: float | None = None  # ua of the field that decided defer, when there was one
    readback: dict[str, Any] | None = None
    recall_rule: str | None = None  # own_recall / what_is_it_for_premium_defer / defer (recall topics only)
    source_topic: str | None = None  # the knowledge topic whose reply was played


def is_reask(key: str, topic: str, history: Sequence[Said]) -> bool:
    return key.endswith(".reask") or key == "cover.say_again" or any(s.topic == topic for s in history)


def choose_open(
    customer: dict[str, Any],
    knowledge: dict[str, Any],
    topic_fields: dict[str, str],
    a: float,
    lines: Sequence[BotLineView],
    history: Sequence[Said],
) -> AcqChoice:
    """The reply to the bot's last utterance, after entry."""
    cid = customer["id"]
    last = lines[-1]
    topic, readback = topic_for(lines, history)
    replies = knowledge["replies"]
    if topic in ("what_did_you_take", "anything_else"):
        # Open recall and "anything else?": kind deferred -> defer; else premium deferred -> the what_is_it
        # reply (no premium figure said); else the recall reply. "anything else?" counts as a re-ask.
        again = topic == "anything_else" or is_reask(last.key, topic, history)
        ua_kind, ua_premium = u(cid, "kind", "a"), u(cid, "premium", "a")
        if ua_kind < a:
            source, variant, rule = "what_did_you_take", "defer", "defer"
        elif ua_premium < a:
            source, variant, rule = "what_is_it", ("again" if again else "own"), "what_is_it_for_premium_defer"
        else:
            source, variant, rule = "what_did_you_take", ("again" if again else "own"), "own_recall"
        return AcqChoice(topic, variant, replies[source][variant], last.key, field="kind", draw_a=ua_kind,
                         readback=readback, recall_rule=rule, source_topic=source)  # fmt: skip
    if topic in topic_fields:
        field = topic_fields[topic]
        draw = u(cid, field, "a")
        if draw < a:
            variant = "defer"
        else:
            variant = "again" if is_reask(last.key, topic, history) else "own"
        return AcqChoice(topic, variant, replies[topic][variant], last.key, field=field, draw_a=draw,
                         readback=readback, source_topic=topic)  # fmt: skip
    if topic in BORROWED:
        source, field = BORROWED[topic]
        draw = u(cid, field, "a")
        variant = "defer" if draw < a else "again"
        return AcqChoice(topic, variant, replies[source][variant], last.key, field=field, draw_a=draw,
                         note=f"reply of {source}", readback=readback, source_topic=source)  # fmt: skip
    if topic == "is_this_you_again":
        return AcqChoice(topic, "canned", entry_reply("right_party.reask", customer["gender"]) or "", last.key)
    if topic in CANNED:
        return AcqChoice(topic, "canned", CANNED[topic], last.key, readback=readback)
    note = f"topic {topic!r} for line key {last.key!r}" if topic else f"unmapped line key {last.key!r}"
    return AcqChoice(topic or "not_understood", "canned", NOT_UNDERSTOOD_TEXT, last.key, mapped=False, note=note)


# --- closed arm ------------------------------------------------------------------------------------


def closed_answers(customer: dict[str, Any], r: float, a: float) -> list[dict[str, Any]]:
    """One answer per field in FIELDS order: answer, the belief state and the draw that decided it."""
    out = []
    for field in FIELDS:
        state = customer["belief"][field]["state"]
        ua, ur = u(customer["id"], field, "a"), u(customer["id"], field, "r")
        if state == "correct":
            answer, decided = "yes", None
        elif state == "false":
            answer, decided = ("yes" if ua < a else "no"), {"axis": "a", "value": ua, "level": a}
        elif state == "dk":
            answer, decided = ("yes" if ur < r else "dont_know"), {"axis": "r", "value": ur, "level": r}
        else:
            raise ValueError(f"{customer['id']} {field}: unknown belief state {state!r}")
        out.append({"field": field, "belief_state": state, "answer": answer, "decided_by": decided})
    return out


def closed_outcomes(answers: Sequence[dict[str, Any]]) -> dict[str, Any]:
    strict = [x["field"] for x in answers if x["answer"] in ("no", "dont_know")]
    lenient = [x["field"] for x in answers if x["answer"] == "no"]
    return {
        "outcome_strict": "caught" if strict else "confirmed",
        "caught_fields_strict": strict,
        "outcome_lenient": "caught" if lenient else "confirmed",
        "caught_fields_lenient": lenient,
    }
