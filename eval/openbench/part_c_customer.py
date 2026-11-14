"""Part C customer: the router (an LLM that reads one agent utterance) and the pure reply rules.

The router (`ROUTER_MODEL`) sees only the agent's latest utterance and `ROUTER_INSTRUCTION`; never the record,
the belief or gold. It returns `RouterOut`, a list of items. Code (`reply`) then decides what the customer
says, following eval/openbench/PLAN.md "Part C":

- an open question on a field topic (`asks` true, no value): W3's open-arm rule. defer when `ua_f < a`;
  `again` when that topic already got a reply in this call, else `own`. Open recall (`what_did_you_take`)
  follows W3's premium rule: kind deferred -> its defer reply; else premium deferred -> the `what_is_it`
  reply; else the recall reply.
- a stated value v (`states_span`: the router's exact words, kept only when inside the utterance and read by
  code into a value; else no stated value) for the topic's field, compared in code with the belief and the record:
  amounts (premium, cover) through the frozen parser (eval/amounts_v2/frozen_parser.py), term in months
  (a value in years is multiplied by 12), cancel in days, enums by equality. v = belief -> yes; belief dk ->
  yes if `ur_f < r` else own; belief false and v = record -> yes if `ua_f < a` else own; otherwise own.
  A value code cannot read counts as equal to neither (own). Kind: the belief values fee and deposit are
  "other" in the router's vocabulary.
- one "हाँ जी, सही है।" per turn however many fields are confirmed, then the non-yes replies in item order.
- canned replies for the non-field items; identity, can_we_talk, human, any_questions and understood_check only
  when the router marks them asked (`asks`). "जी।" (explains_only) and "जी, समझ नहीं आया।" (other) are said only
  when nothing else is; a turn whose only reply is the not-understood line is unmapped.
- the same topic answered twice in one turn gives one reply (the first item).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (ROOT / "eval" / "acq", ROOT / "eval" / "amounts_v2", ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

from acq_common import u  # noqa: E402

ROUTER_MODEL = "mistralai/mistral-small-3.2-24b-instruct"

FIELD_TOPICS: dict[str, str] = {
    "what_did_you_take": "kind", "what_is_it": "kind", "how_much": "premium", "how_paid": "source",
    "how_often": "frequency", "needed_or_choice": "required", "where_to_take_it_from": "required",
    "what_it_gives": "cover", "how_long": "term", "can_cancel": "cancel", "money_back": "money_back",
    "what_you_agreed_to": "consent",
}  # fmt: skip
OTHER_KINDS = ("identity", "can_we_talk", "human", "closing", "explains_only", "understood_check",
               "any_questions", "other")  # fmt: skip
ItemKind = Literal[
    "what_did_you_take", "what_is_it", "how_much", "how_paid", "how_often", "needed_or_choice",
    "where_to_take_it_from", "what_it_gives", "how_long", "can_cancel", "money_back", "what_you_agreed_to",
    "identity", "can_we_talk", "human", "closing", "explains_only", "understood_check", "any_questions", "other",
]  # fmt: skip


class RouterItem(BaseModel):
    kind: ItemKind
    asks: bool
    states_span: str | None


class RouterOut(BaseModel):
    items: list[RouterItem]


ROUTER_INSTRUCTION = """You label one utterance that a caller from a lender said to a borrower on a phone call about a product the borrower bought with a loan. You see only that utterance. List every thing the utterance does, in the order it does them, as items: at most 6 items, never the same kind twice.

Item kinds about the product (a topic):
- what_did_you_take: asks or says whether something else was taken with the loan and what it was (an open "what did you take")
- what_is_it: what the product is (insurance or something else)
- how_much: the premium, the amount paid for it
- how_paid: where the money came from: deducted from the loan amount, or paid separately
- how_often: paid once, or again and again
- needed_or_choice: whether it was required for the loan or the borrower's own choice
- where_to_take_it_from: whether it could be taken from another company or provider
- what_it_gives: what it gives, the cover amount
- how_long: how long it runs, the term
- can_cancel: whether and until when it can be cancelled
- money_back: whether any money comes back (at the end, or if it is cancelled)
- what_you_agreed_to: how the borrower agreed or gave consent
Other item kinds:
- identity: asks whether the speaker is the borrower (for example by name), or asks who is speaking. Only when the utterance asks this now; a question about the loan is not identity
- can_we_talk: asks whether this is a good time, or whether the borrower can talk
- human: offers or asks about transfer to a human agent
- closing: thanks the borrower or says goodbye
- explains_only: explains or informs, asks nothing, and states no value of the topics above
- understood_check: asks whether the borrower understood, or whether what was said is right, without naming a topic; also a question asking the borrower to confirm the loan itself (that they took a loan)
- any_questions: asks whether the borrower has any questions
- other: anything else

For a topic item:
- asks: true if the utterance asks the borrower about that topic.
- states_span: the exact words of the utterance, copied character for character, that give the value the utterance itself says for that topic (an amount, a number of days, months or years, insurance or another product, deducted from the loan or paid separately, once or again and again, required or own choice, money back or not, how consent was given); null if it says no value. Never infer a value the utterance does not say.
For other item kinds set asks true if the utterance asks it as a question, else false; states_span null.
A name used to address the borrower ('अमित जी, …', 'धन्यवाद रानी जी') is not identity. identity only when the utterance asks whether the listener is that person or who is speaking.
closing: ends the call. A 'धन्यवाद' or 'ठीक है' before a question is not closing.
Give states_span for what_is_it/what_did_you_take only when the utterance tells the borrower, or asks them to confirm, what the product is. A reference back ('इस इंश्योरेंस', 'यह बीमा') is not a value; add no item for it. A loan type (gold loan, personal loan) is never a product value. A date is never how_long.
A yes/no question that names a value ('क्या आपने OTP डालकर सहमति दी थी?', 'क्या आपने app में accept किया था?', 'क्या आपने … credit-life insurance लिया था?') states it. 'क्या आपको पता है कि X?' states X when X is a plain statement with a value ('पैसे वापस नहीं मिलते' gives money_back no; '30 दिनों के भीतर' gives 30 days). When X holds कितना, क्या, or या नहीं, it is an open question with no states_span.
A question about which company provides it is where_to_take_it_from.
Reply as JSON with the list of items."""


# --- canned replies --------------------------------------------------------------------------------

YES = "हाँ जी, सही है।"
NOT_UNDERSTOOD = "जी, समझ नहीं आया।"
CANNED = {
    "understood_check": "हाँ जी।",
    "explains_only": "जी।",
    "any_questions": "नहीं जी, कोई सवाल नहीं।",
    "can_we_talk": "हाँ जी, बोलिए।",
    "human": "नहीं, आप ही पूछिए।",
    "closing": "ठीक है जी, धन्यवाद।",
    "other": NOT_UNDERSTOOD,
}
ASKED_ONLY = ("identity", "can_we_talk", "human", "any_questions", "understood_check")  # answered only when asked
LOW_PRIORITY = ("explains_only", "other", "closing")  # said only when nothing else is


def identity_reply(gender: str) -> str:
    return "हाँ जी, मैं ही बोल रही हूँ।" if gender == "f" else "हाँ जी, मैं ही बोल रहा हूँ।"


THIRD_PARTY_NOTHING = "मुझे इस बारे में कुछ नहीं पता, आप ही बताइए।"


def third_party_identity(cid: str) -> str:
    """C001-C020 a brother answers; C021-C040 a sister."""
    n = int(cid.rsplit("C", 1)[1])
    if n <= 20:
        return "नहीं जी, मैं उनका भाई बोल रहा हूँ, वो अभी घर पर नहीं हैं।"
    return "नहीं जी, मैं उनकी बहन बोल रही हूँ, वो अभी घर पर नहीं हैं।"


def third_party_reply(cid: str, items: Sequence[RouterItem]) -> tuple[str, list[dict[str, Any]]]:
    """Identity in the turn -> the relative's line; every other turn -> "I know nothing, you tell me"."""
    if any(it.kind == "identity" and it.asks for it in items):
        return third_party_identity(cid), [{"kind": "identity", "variant": "third_party_identity"}]
    return THIRD_PARTY_NOTHING, [{"kind": "any", "variant": "third_party_nothing"}]


# --- values --------------------------------------------------------------------------------------

_AMOUNTS = None


_AMOUNTS_LOCK = __import__("threading").Lock()
# Part C's own export directory for the pinned parser. Crash fix during the counted run: the shared default
# (<tmp>/samajh-frozen-parser) was left holding an empty package by another process, so load() raised OSError 66.
PARSER_DIR = Path(__import__("tempfile").gettempdir()) / "samajh-frozen-parser-partc"


def amounts():
    """The frozen parser (commit 59c12d9), loaded once per process under a lock, from PARSER_DIR."""
    global _AMOUNTS
    with _AMOUNTS_LOCK:
        if _AMOUNTS is None:
            from frozen_parser import load

            _AMOUNTS = load(PARSER_DIR)
    return _AMOUNTS


def _digits(text: str) -> int | None:
    m = re.fullmatch(r"\s*(?:rs\.?|₹|inr)?\s*([0-9][0-9,]*)\s*(?:rs\.?|rupees|रुपये|रुपए)?\s*", text, re.I)
    return int(m.group(1).replace(",", "")) if m else None


def parse_amount_value(text: str) -> int | None:
    d = _digits(text)
    if d is not None:
        return d
    res = amounts().parse_amount(text)
    if getattr(res, "status", None) == "parsed":
        return int(res.rupees)
    cands = getattr(res, "candidates", ()) or ()
    vals = {int(c.rupees) for c in cands}
    return vals.pop() if len(vals) == 1 else None


def parse_months(text: str) -> int | None:
    t = text.strip().lower()
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(months?|month|mahine|महीने|महीना|years?|yrs?|saal|साल|वर्ष)?", t)
    if m:
        n = float(m.group(1))
        unit = m.group(2) or "months"
        months = n * 12 if unit.startswith(("year", "yr", "saal", "साल", "वर्ष")) else n
        return int(round(months)) if abs(months - round(months)) < 1e-9 else None
    res = amounts().parse_duration_months(text)
    return int(res) if isinstance(res, int) else None


def parse_days(text: str) -> int | None:
    t = text.strip().lower()
    m = re.fullmatch(r"([0-9]+)\s*(days?|din|दिन)?", t)
    if m:
        return int(m.group(1))
    res = amounts().parse_duration_days(text)
    return int(res) if isinstance(res, int) else None


def _enum(text: str) -> str:
    return text.strip().lower().replace(" ", "_").replace("-", "_")


def _search_months(text: str) -> int | None:
    m = re.search(r"([0-9]+)\s*(महीने|महीनों|महीना|months?|mahine|साल|सालों|वर्ष|years?|saal)", text, re.I)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        return n * 12 if unit.startswith(("साल", "वर्ष", "year", "saal")) else n
    res = amounts().parse_duration_months(text)
    return int(res) if isinstance(res, int) else None


def _search_days(text: str) -> int | None:
    m = re.search(r"([0-9]+)\s*(दिन|दिनों|days?|din)", text, re.I)
    if m:
        return int(m.group(1))
    res = amounts().parse_duration_days(text)
    return int(res) if isinstance(res, int) else None


# Keyword tables: (value, words). A span matching words of exactly one value gets that value; else None.
KEYWORDS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "kind": [("insurance", ("insurance", "इंश्योरेंस", "इन्श्योरेंस", "इंशुरेंस", "बीमा", "cover", "कवर", "policy",
                            "पॉलिसी")),
             ("other", ("fee", "फ़ीस", "फीस", "charge", "चार्ज", "deposit", "डिपॉज़िट", "डिपॉजिट", "fd", "एफडी",
                        "जमा", "savings", "बचत"))],
    "source": [("from_loan", ("काट", "कट", "deduct", "डिडक्ट", "loan amount से", "लोन अमाउंट से", "रकम से",
                              "रकम में से", "लोन से", "loan से")),
               ("separately", ("अलग से", "separately", "separate", "नकद", "cash", "खुद भरा", "अलग भुगतान"))],
    "frequency": [("one_time", ("एक बार", "one time", "one-time", "single", "एक ही बार", "एकमुश्त")),
                  ("recurring", ("हर साल", "हर महीने", "बार-बार", "बार बार", "recurring", "monthly", "yearly",
                                 "सालाना", "मासिक", "हर बार"))],
    "required": [("no", ("ज़रूरी नहीं", "जरूरी नहीं", "अनिवार्य नहीं", "optional", "मर्ज़ी", "मर्जी", "choice",
                         "चुनने", "किसी भी", "कहीं से भी", "दूसरी कंपनी", "दूसरी company", "any company")),
                 ("yes", ("ज़रूरी", "जरूरी", "अनिवार्य", "compulsory", "mandatory", "उन्हीं से"))],
    "money_back": [("no", ("वापस नहीं", "नहीं मिल", "नहीं आता", "no refund", "refund नहीं")),
                   ("yes", ("वापस मिल", "वापस आ", "refund मिल", "return मिल", "money back"))],
    "consent": [("otp", ("otp", "ओटीपी")),
                ("digital_click", ("app", "ऐप", "एप", "click", "क्लिक", "online", "ऑनलाइन", "accept", "स्वीकृति",
                                   "स्वीकार")),
                ("signed_form", ("form", "फ़ॉर्म", "फॉर्म", "sign", "साइन", "हस्ताक्षर", "दस्तख़त", "दस्तखत")),
                ("recorded_call", ("call", "कॉल", "recorded", "रिकॉर्ड", "फ़ोन पर", "फोन पर"))],
}  # fmt: skip
# Where a "not" form contains the positive form, the first value listed wins when both match.
NEGATED_FIRST = {"required", "money_back"}


_CLAUSES = re.compile(r"[।?!;.]+")


def _tokens(text: str) -> list[str]:
    import unicodedata

    t = unicodedata.normalize("NFC", text).lower()
    return "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in t).split()


def is_question_clause(span: str, utterance: str) -> bool:
    """The span, or the utterance clause holding it, asks an open question: it holds "या नहीं" or "कितन", or
    "क्या" anywhere but as the yes/no particle (first word of the clause, or first word after "कि")."""
    clause = next((c for c in _CLAUSES.split(utterance) if _in_order(_tokens(span), _tokens(c))), span)
    for text in (span, clause):
        if "या नहीं" in text or "कितन" in text:
            return True
        toks = _tokens(text)
        for i, t in enumerate(toks):
            if t == "क्या" and i > 0 and toks[i - 1] != "कि":
                return True
    return False


def _keyword(field: str, span: str, utterance: str = "") -> str | None:
    if is_question_clause(span, utterance or span):
        return None
    low = span.lower()
    hits = [v for v, words in KEYWORDS[field] if any(w.lower() in low for w in words)]
    if field in NEGATED_FIRST and hits:
        return hits[0]
    return hits[0] if len(hits) == 1 else None


def normalise_span(field: str, span: str, utterance: str = "") -> Any:
    """The value a span gives, read by code, or None when code cannot read one."""
    if field in ("premium", "cover"):
        return parse_amount_value(span)
    if field == "term":
        return _search_months(span)
    if field == "cancel":
        return _search_days(span)
    return _keyword(field, span, utterance)


def _clean(text: str) -> str:
    import unicodedata

    return " ".join(unicodedata.normalize("NFC", text).split())


def grounded_span(span: str | None, utterance: str) -> str | None:
    """The span when its words (NFC, lower-case, punctuation stripped) appear in the utterance in order."""
    if not span or not _tokens(span):
        return None
    return span if _in_order(_tokens(span), _tokens(utterance)) else None


def _in_order(words: list[str], within: list[str]) -> bool:
    """Every word of `words` appears in `within`, in the same order (not necessarily adjacent)."""
    it = iter(within)
    return bool(words) and all(w in it for w in words)


IDENTITY_ASK = re.compile(r"बात कर|कौन|बोल रहे|speak(ing)? (to|with)|talking (to|with)|who('s| is)", re.I)


def record_values(record: dict[str, Any]) -> dict[str, Any]:
    """The record's value per field, in the router's vocabulary. `record` is the file's "record" object."""
    p = record["products"][0]
    return {
        "kind": "insurance" if p["kind"] == "credit_life" else "other",
        "premium": p["premium_inr"],
        "source": "from_loan" if p["paid_from_loan"] else "separately",
        "frequency": "one_time" if "one_time_payment" in p["features"] else "recurring",
        "required": "yes" if p["required_for_loan"] else "no",
        "cover": p["cover_inr"],
        "term": p["term_months"],
        "cancel": p["cancel_window_days"],
        "money_back": "yes" if "money_back" in " ".join(p["features"]) else "no",
        "consent": p["consent"]["method"],
    }


def belief_value(field: str, belief: dict[str, Any]) -> Any:
    v = belief["value"]
    if v is None:
        return None
    if field == "kind":
        return "insurance" if v == "insurance" else "other"
    if field in ("required", "money_back"):
        return "yes" if v else "no"
    return v


# --- the reply -----------------------------------------------------------------------------------


def _open(cid: str, knowledge: dict[str, Any], topic: str, a: float, answered: set[str]) -> dict[str, Any]:
    replies = knowledge["replies"]
    again = topic in answered
    if topic == "what_did_you_take":
        ua_kind, ua_premium = u(cid, "kind", "a"), u(cid, "premium", "a")
        if ua_kind < a:
            src, variant, rule = "what_did_you_take", "defer", "defer"
        elif ua_premium < a:
            src, variant, rule = "what_is_it", ("again" if again else "own"), "what_is_it_for_premium_defer"
        else:
            src, variant, rule = "what_did_you_take", ("again" if again else "own"), "own_recall"
        return {"rule": "open", "variant": variant, "draw_a": ua_kind, "recall_rule": rule, "source_topic": src,
                "text": replies[src][variant]}  # fmt: skip
    field = FIELD_TOPICS[topic]
    draw = u(cid, field, "a")
    variant = "defer" if draw < a else ("again" if again else "own")
    return {"rule": "open", "variant": variant, "draw_a": draw, "source_topic": topic, "text": replies[topic][variant]}


def _stated(customer, knowledge, record_vals, topic, value_text, v, r, a) -> dict[str, Any]:
    cid = customer["id"]
    field = FIELD_TOPICS[topic]
    belief = customer["belief"][field]
    bv, rv = belief_value(field, belief), record_vals[field]
    state = belief["state"]
    ua, ur = u(cid, field, "a"), u(cid, field, "r")
    out = {"rule": "stated", "stated": value_text, "stated_value": v, "belief_state": state, "belief_value": bv,
           "record_value": rv, "draw_a": ua, "draw_r": ur, "source_topic": topic}  # fmt: skip
    if state == "dk":
        yes, why = ur < r, "dk_r"
    elif v == bv:
        yes, why = True, "equals_belief"
    elif state == "false" and v == rv:
        yes, why = ua < a, "false_record_a"
    else:
        yes, why = False, "neither"
    out["decided"] = why
    if yes:
        out.update(variant="yes", text=YES)
    else:
        out.update(variant="own", text=knowledge["replies"][topic]["own"])
    return out


def reply(customer: dict[str, Any], knowledge: dict[str, Any], record: dict[str, Any], r: float, a: float,
          items: Sequence[RouterItem], history: Sequence[dict[str, Any]], utterance: str = ""
          ) -> tuple[str, list[dict[str, Any]]]:
    """The customer's reply to one agent turn and one choice per item.

    `history`: the choices of earlier turns (dicts with `source_topic`), for re-ask detection.
    `utterance`: the agent's words. A `states_span` counts only when it is inside them and code reads a value
    from it; otherwise the item is an open question (when asked). After the first identity answer in a call,
    identity is ignored unless the utterance matches IDENTITY_ASK.
    Returns ("", []) for no items. The joined text is the yes (once, first), then the other replies."""
    answered = {h["source_topic"] for h in history if h.get("source_topic") and h.get("variant") != "yes"}
    record_vals = record_values(record)
    choices: list[dict[str, Any]] = []
    any_stated = False
    identity_done = any(h.get("kind") == "identity" and h.get("variant") == "canned" for h in history)
    kind_known = any(FIELD_TOPICS.get(h.get("source_topic") or "") == "kind" for h in history)
    keep: dict[str, int] = {}  # topic -> the item that answers it: the first asked one, else the first
    for i, it in enumerate(items):
        if it.kind in FIELD_TOPICS and (it.kind not in keep or (it.asks and not items[keep[it.kind]].asks)):
            keep[it.kind] = i
    field_asked = any(it.kind in FIELD_TOPICS and it.asks for it in items)
    for i, it in enumerate(items):
        c: dict[str, Any] = {"item": i, "kind": it.kind}
        if it.kind in FIELD_TOPICS:
            if keep[it.kind] != i:
                c.update(rule="duplicate", variant="skipped", text="")
            elif FIELD_TOPICS[it.kind] == "kind" and not it.asks and kind_known:
                c.update(rule="kind_refer_back", variant="skipped", text="")
            elif (span := grounded_span(it.states_span, utterance)) is not None and \
                    (v := normalise_span(FIELD_TOPICS[it.kind], span, utterance)) is not None:
                any_stated = True
                c.update(_stated(customer, knowledge, record_vals, it.kind, span, v, r, a))
            elif it.asks or (it.states_span and "?" in utterance):  # an unread value in a question: asked
                if not it.asks:
                    c["asks_inferred"] = True
                if it.states_span:
                    c["span_dropped"] = it.states_span
                c.update(_open(customer["id"], knowledge, it.kind, a, answered))
            else:
                c.update(rule="mention", variant="skipped", text="")  # named, neither asked nor valued
        elif it.kind == "identity" and identity_done and not IDENTITY_ASK.search(utterance):
            c.update(rule="identity_already_answered", variant="skipped", text="")
        elif it.kind == "any_questions" and field_asked:
            c.update(rule="field_asked_too", variant="skipped", text="")
        elif it.kind in ASKED_ONLY and not it.asks:
            c.update(rule="not_asked", variant="skipped", text="")  # named but not asked now
        elif it.kind == "identity":
            c.update(rule="canned", variant="canned", text=identity_reply(customer["gender"]))
        else:
            c.update(rule="canned", variant="canned", text=CANNED[it.kind])
        choices.append(c)
    # understood_check: the stated-value rule covers it when a field was stated in this turn.
    for c in choices:
        if c["kind"] == "understood_check" and any_stated:
            c.update(variant="skipped", text="", rule="covered_by_stated")
    texts = [c for c in choices if c["text"]]
    if any(c["kind"] not in LOW_PRIORITY for c in texts):
        for c in texts:
            if c["kind"] in LOW_PRIORITY:
                c.update(variant="skipped", text="", rule="low_priority")
    parts: list[str] = []
    if any(c.get("variant") == "yes" for c in choices):
        parts.append(YES)
    for c in choices:
        if c["text"] and c.get("variant") != "yes" and c["text"] not in parts:
            parts.append(c["text"])
    if not parts:
        parts = [NOT_UNDERSTOOD]
        choices.append({"item": None, "kind": "other", "rule": "nothing_mapped", "variant": "canned",
                        "text": NOT_UNDERSTOOD})  # fmt: skip
    return " ".join(parts), choices


def is_unmapped(text: str) -> bool:
    return text == NOT_UNDERSTOOD


def route(client, utterance: str):
    """One router request. Returns (RouterOut, LlmResult)."""
    from samajh.clients.llm import Message

    res = client.complete(RouterOut, [Message(role="system", content=ROUTER_INSTRUCTION),
                                      Message(role="user", content=utterance)],
                          model=ROUTER_MODEL, max_tokens=1024)  # fmt: skip
    return res.value, res
