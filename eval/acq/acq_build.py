"""The ACQ customer set: records, beliefs, gold, fact sheets, topics and closed statements. No LLM.

Commands (from the repo root):
  uv run python eval/acq/acq_build.py build          write everything under data/acq/
  uv run python eval/acq/acq_build.py check          re-derive in memory and diff with disk (exit 1 on a difference)
  uv run python eval/acq/acq_build.py freeze-inputs  write data/acq/FROZEN_INPUTS.json (the writer refuses without it)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / "p5"))

from acq_common import DATA, FIELDS, FLAG_FIELD, RECORDS, ROOT, SEED, dump_jsonl, records_digest, sha256, u  # noqa: E402
from write_customers import MODEL_A, MODEL_B, days_words, term_words  # noqa: E402

from samajh.amounts import spoken_amount  # noqa: E402
from samajh.rules import evaluate  # noqa: E402
from samajh.server.records import CallRecord  # noqa: E402
from samajh.types import (  # noqa: E402
    Beliefs,
    ConsentMethod,
    DontKnow,
    Evidence,
    FeatureClaim,
    KindClaim,
    Language,
    NotAsked,
    OpenRecall,
    PaymentFrequency,
    PaymentSource,
    ProductBeliefs,
    RecallItem,
    Stated,
    Tier,
)

KINDS = (("informed", 32), ("knowledge_gap", 48), ("misled", 40), ("misled_with_gaps", 40))
LANGUAGES = ("hi", "hi-en")
DK_POOL = ("premium", "cover", "term", "cancel", "money_back", "frequency")
FALSE_POOL = ("kind", "premium", "source", "required", "cover", "money_back")
NEVER_DK = ("kind", "source", "required", "consent")
CONSENT_METHODS = ("signed_form", "otp", "digital_click", "recorded_call")
PROVIDER = "Namoona Life (synthetic)"
LENDER_NAME = {"bank": "नमूना बैंक", "nbfc": "नमूना फ़ाइनेंस"}
FILES = ("customers.jsonl", "gold.jsonl", "topics.json", "closed_statements.jsonl")
FROZEN_INPUTS = DATA / "FROZEN_INPUTS.json"
CLOSED_SCRIPT = DATA / "closed_script.json"

FIRST_NAMES = {
    "f": ["Sunita", "Anita", "Rekha", "Pooja", "Neha", "Priya", "Kavita", "Meena", "Geeta", "Seema", "Rani",
          "Asha", "Usha", "Sarita", "Pushpa", "Nisha", "Lata", "Shobha", "Mamta", "Radha", "Savita", "Jyoti"],
    "m": ["Suresh", "Ramesh", "Mahesh", "Rajesh", "Mukesh", "Dinesh", "Anil", "Sunil", "Vijay", "Sanjay", "Ajay",
          "Ravi", "Manoj", "Rakesh", "Ashok", "Deepak", "Amit", "Rahul", "Vinod", "Pradeep", "Santosh", "Gopal"],
}
OCCUPATIONS = ["run a small grocery shop", "drive an auto-rickshaw", "teach at a private school",
               "work as a tailor from home", "run a mobile repair stall", "work as a nurse at a clinic",
               "sell vegetables at the market", "work in a textile mill", "run a small tea stall",
               "work as an electrician", "keep accounts for a wholesale trader", "run a beauty parlour"]
TOWNS = ["a district town in Uttar Pradesh", "a small town in Madhya Pradesh", "a town near Jaipur",
         "a suburb of Lucknow", "a town in Bihar", "a town in Haryana", "a colony on the edge of Indore",
         "a town in Uttarakhand"]
HOW_YOU_TALK = {
    "hi": ["Plain Hindi, short answers, a little hesitant on the phone.",
           "Friendly, simple everyday Hindi, says what comes to mind.",
           "Polite, slow, plain village Hindi, a little wary of calls about money.",
           "Quick and busy, short Hindi sentences."],
    "hi-en": ["Hinglish, Hindi mixed with English words such as loan, policy, amount, the way city people talk.",
              "Friendly Hinglish, mixes in English words freely, short answers.",
              "Busy and to the point, Hindi with many English words.",
              "Polite Hinglish, a little unsure on the phone."],
}
WHEN = {"gold": "pledged gold at the lender's branch for a gold loan",
        "personal": "took a personal loan from the lender"}
PURPOSE = ["for a family wedding", "for house repairs", "to buy stock for your work", "for a child's school fees",
           "to pay a hospital bill", "to buy a second-hand two-wheeler"]


# ---------------------------------------------------------------- who is in the set


def slots() -> list[dict[str, str]]:
    """160 slots, writer balanced within kind x language and gender within kind x language x writer."""
    out = []
    for kind, n in KINDS:
        for language in LANGUAGES:
            for i in range(n // 2):
                model = MODEL_A if i % 2 == 0 else MODEL_B
                gender = "f" if (i // 2) % 2 == 0 else "m"
                out.append({"kind": kind, "language": language, "writer_model": model, "gender": gender})
    return out


# ---------------------------------------------------------------- records


def make_record(n: int, cid: str, slot: dict[str, str], rng: random.Random) -> CallRecord:
    gender = slot["gender"]
    first = rng.choice(FIRST_NAMES[gender])
    lender_type = rng.choice(("bank", "nbfc"))
    loan_kind = rng.choice(("gold", "personal"))
    sanctioned = rng.randrange(10, 81) * 10_000
    premium = rng.randrange(16, 121) * 500
    term = rng.choice((12, 24, 36))
    cancel = rng.choice((15, 30))
    from_loan = rng.random() < 0.75
    method = rng.choice(CONSENT_METHODS)
    disbursed_on = date(2026, 10, rng.randrange(1, 32))
    dob = date(rng.randrange(1966, 2001), rng.randrange(1, 13), rng.randrange(1, 29))
    record_id = f"acq-c{n:03d}"
    body = {
        "loan_id": f"TEST-ACQ-LN-{n:03d}",
        "lender_type": lender_type,
        "borrower": {"name": f"{first} Namoona", "dob": dob.isoformat(), "language": slot["language"]},
        "loan_kind": loan_kind,
        "sanctioned_inr": sanctioned,
        "disbursed_inr": sanctioned - premium if from_loan else sanctioned,
        "disbursed_on": disbursed_on.isoformat(),
        "tenure_months": term,
        "products": [{
            "id": "P1", "kind": "credit_life", "provider": PROVIDER, "premium_inr": premium, "cover_inr": sanctioned,
            "term_months": term, "paid_from_loan": from_loan, "required_for_loan": False, "risk_mitigant": True,
            "provider_choice_offered": True, "cancel_window_days": cancel, "features": ["one_time_payment"],
            "consent": {"method": method, "at": disbursed_on.isoformat()},
        }],
    }
    return CallRecord.model_validate({
        "id": record_id,
        "label": f"Synthetic ACQ record. {first}: a {loan_kind} loan and one add-on",
        "description": f"Synthetic ACQ record for {cid}. {first} took a {loan_kind} loan with one credit-life add-on. "
                       "For the ACQ evaluation only.",
        "lender_name": LENDER_NAME[lender_type],
        "record": body,
    })


# ---------------------------------------------------------------- beliefs


def _ordered(cid: str, prefix: str, pool: tuple[str, ...]) -> list[str]:
    return sorted(pool, key=lambda f: u(cid, f"{prefix}:{f}", "a"))


def false_fields(cid: str) -> tuple[list[str], str]:
    """1-2 contradicted fields and the believed kind. A deposit belief always brings money_back with it;
    a fee belief never sits with money_back (a charge that comes back is not a plausible belief)."""
    kind_as = "deposit" if u(cid, "kind", "r") < 0.5 else "fee"
    n = 1 + int(u(cid, "n_false", "a") * 2)
    order = _ordered(cid, "false", FALSE_POOL)
    chosen = order[:n]
    if "kind" in chosen and kind_as == "deposit":
        chosen = ["kind", "money_back"]
    elif "kind" in chosen and "money_back" in chosen:
        chosen = ["kind", next(f for f in order if f not in ("kind", "money_back"))]
    return [f for f in FIELDS if f in chosen], kind_as


def dk_fields(cid: str, n_max: int, exclude: list[str]) -> list[str]:
    n = 1 + int(u(cid, "n_dk", "a") * n_max)
    chosen = [f for f in _ordered(cid, "dk", DK_POOL) if f not in exclude][:n]
    return [f for f in FIELDS if f in chosen]


def _round_down(x: float, step: int) -> int:
    return int(math.floor(x / step)) * step


def _round_up(x: float, step: int) -> int:
    return int(math.ceil(x / step)) * step


def make_belief(cid: str, kind: str, p: dict[str, Any], tenure: int) -> dict[str, dict[str, Any]]:
    falses, kind_as = ([], "insurance")
    dks: list[str] = []
    if kind in ("misled", "misled_with_gaps"):
        falses, kind_as = false_fields(cid)
    if kind == "knowledge_gap":
        dks = dk_fields(cid, 3, [])
    elif kind == "misled_with_gaps":
        dks = dk_fields(cid, 2, falses)
    if not falses:
        kind_as = "insurance"
    state = {f: "false" if f in falses else "dk" if f in dks else "correct" for f in FIELDS}
    b: dict[str, dict[str, Any]] = {}
    b["kind"] = {"state": state["kind"], "value": kind_as if state["kind"] == "false" else "insurance"}
    r = u(cid, "premium", "r")
    if state["premium"] == "false":
        if r < 0.5:
            value = max(500, _round_down(p["premium_inr"] * (0.25 + 0.5 * r), 500))
        else:
            value = _round_up(p["premium_inr"] * (2.0 + 2.0 * (r - 0.5)), 500)
    else:
        value = p["premium_inr"] if state["premium"] == "correct" else None
    b["premium"] = {"state": state["premium"], "value": value}
    record_source = "from_loan" if p["paid_from_loan"] else "separately"
    other = "separately" if p["paid_from_loan"] else "from_loan"
    b["source"] = {"state": state["source"], "value": other if state["source"] == "false" else record_source}
    b["frequency"] = {"state": state["frequency"], "value": None if state["frequency"] == "dk" else "one_time"}
    b["required"] = {"state": state["required"], "value": state["required"] == "false"}
    rc = u(cid, "cover", "r")
    cover = {"false": max(10_000, _round_down(p["cover_inr"] * (0.15 + 0.25 * rc), 10_000)),
             "correct": p["cover_inr"], "dk": None}[state["cover"]]
    b["cover"] = {"state": state["cover"], "value": cover}
    said_as = "as_long_as_loan" if u(cid, "term", "r") < 0.4 and tenure == p["term_months"] else "months"
    b["term"] = {"state": state["term"], "value": p["term_months"] if state["term"] == "correct" else None,
                 **({"said_as": said_as} if state["term"] == "correct" else {})}
    b["cancel"] = {"state": state["cancel"],
                   "value": p["cancel_window_days"] if state["cancel"] == "correct" else None}
    b["money_back"] = {"state": state["money_back"],
                       "value": None if state["money_back"] == "dk" else state["money_back"] == "false"}
    b["consent"] = {"state": "correct", "value": p["consent"]["method"]}
    for f in NEVER_DK:
        assert b[f]["state"] != "dk", (cid, f)
    return b


# ---------------------------------------------------------------- gold and the engine


def _ev(turn: int, quote: str) -> Evidence:
    return Evidence(quote=quote, turn_id=turn)


def perfect_beliefs(record: CallRecord, belief: dict[str, dict[str, Any]]) -> Beliefs:
    """The belief as `Beliefs`, as a perfect extraction of an open call would give it."""
    lr = record.record
    kind = KindClaim(belief["kind"]["value"])

    def number(field: str, turn: int):
        s = belief[field]
        if s["state"] == "dk":
            return DontKnow(evidence=_ev(turn, f"I do not know the {field}"))
        return Stated(value=s["value"], evidence=_ev(turn, f"the {field} is {s['value']}"))

    def readback(field: str, turn: int):
        if belief[field]["state"] == "dk":
            return NotAsked()
        return Stated[bool](value=True, evidence=_ev(turn, "yes, that is right"))

    cancel = belief["cancel"]
    if cancel["state"] == "dk":
        cancel_allowed, cancel_days = DontKnow(evidence=_ev(12, "I do not know about cancelling")), NotAsked()
    else:
        cancel_allowed = Stated[bool](value=True, evidence=_ev(12, "yes, it can be cancelled"))
        cancel_days = Stated(value=cancel["value"], evidence=_ev(13, f"within {cancel['value']} days"))
    mb = belief["money_back"]
    if mb["state"] == "dk":
        probe = DontKnow(evidence=_ev(14, "I do not know what happens to the money"))
    elif mb["value"]:
        probe = Stated[tuple[FeatureClaim, ...]](value=(FeatureClaim.withdrawable_after_period,),
                                                 evidence=_ev(14, "the money comes back at the end of the loan"))
    else:
        probe = Stated[tuple[FeatureClaim, ...]](value=(), evidence=_ev(14, "no, the money does not come back"))
    freq = belief["frequency"]
    frequency = (DontKnow(evidence=_ev(6, "I do not know if it is paid again"))
                 if freq["state"] == "dk" else
                 Stated(value=PaymentFrequency.one_time, evidence=_ev(6, "it was paid one time")))
    required = belief["required"]["value"]
    product = ProductBeliefs(
        product_id="P1",
        kind=Stated(value=kind, evidence=_ev(2, f"it is {kind.value}")),
        premium_inr=number("premium", 3),
        premium_readback=readback("premium", 4),
        payment_source=Stated(value=PaymentSource(belief["source"]["value"]),
                              evidence=_ev(5, f"it was paid {belief['source']['value']}")),
        payment_frequency=frequency,
        required_for_loan=Stated[bool](value=required, evidence=_ev(7, "it was compulsory" if required
                                                                    else "it was my own choice")),
        provider_choice_offered=Stated[bool](value=not required,
                                             evidence=_ev(8, "it had to be from the lender" if required
                                                          else "I could take it from any company")),
        cover_inr=number("cover", 9),
        cover_readback=readback("cover", 10),
        term_months=(DontKnow(evidence=_ev(11, "I do not know how long it runs"))
                     if belief["term"]["state"] == "dk" else
                     Stated(value=belief["term"]["value"], evidence=_ev(11, "it runs for the loan's term"))),
        cancel_allowed=cancel_allowed,
        cancel_window_days=cancel_days,
        feature_probe=probe,
        consent_given=Stated[bool](value=True, evidence=_ev(15, "I said yes to it with the loan")),
        consent_method=Stated(value=ConsentMethod(belief["consent"]["value"]),
                              evidence=_ev(15, f"by {belief['consent']['value']}")),
    )
    recall_ev = _ev(1, f"I took {kind.value} with the loan")
    return Beliefs(
        call_id=f"perfect-{record.id}",
        loan_id=lr.loan_id,
        language=lr.borrower.language,
        recall=OpenRecall(asked=True, answer=recall_ev,
                          items=(RecallItem(evidence=recall_ev, kind=kind, product_id="P1"),)),
        products=(product,),
    )


EXPECTED_TIER = {"no_problem": Tier.clear, "knowledge_gap_only": Tier.understanding_gap, "problem": Tier.refer}


def gold_row(cid: str, kind: str, record: CallRecord, belief: dict[str, dict[str, Any]]) -> dict[str, Any]:
    falses = [f for f in FIELDS if belief[f]["state"] == "false"]
    dks = [f for f in FIELDS if belief[f]["state"] == "dk"]
    cls = "problem" if falses else "knowledge_gap_only" if dks else "no_problem"
    ground = falses if cls == "problem" else dks if cls == "knowledge_gap_only" else []
    result = evaluate(record.record, perfect_beliefs(record, belief))
    flags = sorted({f.reason.value for f in result.all_flags()})
    flag_fields = {FLAG_FIELD[f.reason] for f in result.all_flags()}
    problems = []
    if result.tier is not EXPECTED_TIER[cls]:
        problems.append(f"tier {result.tier.value}, expected {EXPECTED_TIER[cls].value}")
    missing = [f for f in ground if f not in flag_fields]
    if missing:
        problems.append(f"no engine flag on ground field(s) {missing}")
    if result.all_gaps():
        problems.append(f"engine gaps {[g.rule_id.value for g in result.all_gaps()]}")
    row = {"id": cid, "record_id": record.id, "kind": kind, "language": record.record.borrower.language.value,
           "class": cls, "false_fields": falses, "dk_fields": dks, "ground": ground,
           "engine_tier": result.tier.value, "engine_flags": flags}
    return {"row": row, "problems": problems}


# ---------------------------------------------------------------- fact sheets


def _w(n: int) -> str:
    return spoken_amount(n, Language.hi_en)


NOUN = {"insurance": "the insurance", "deposit": "the FD", "fee": "the charge"}
CONSENT_WAY = {"signed_form": "by signing a form", "otp": "by giving an OTP that came on your phone",
               "digital_click": "by clicking a button on the phone", "recorded_call": "on a recorded phone call"}


def _age_words(dob: date) -> str:
    decade = (2026 - dob.year) // 10 * 10
    return {20: "twenties", 30: "thirties", 40: "forties", 50: "fifties", 60: "sixties"}[decade]


def fact_sheet(cid: str, record: CallRecord, belief: dict[str, dict[str, Any]], language: str) -> dict[str, Any]:
    lr = record.record
    first = lr.borrower.name.split()[0]
    kind = belief["kind"]["value"]
    noun = NOUN[kind]
    pick = lambda items, axis_field: items[int(u(cid, axis_field, "r") * len(items))]  # noqa: E731
    know: list[str] = []
    dont: list[str] = []
    s = {f: belief[f]["state"] for f in FIELDS}
    know.append({"insurance": "Along with the loan you took an insurance cover on the loan.",
                 "deposit": "Along with the loan the officer opened an FD, a fixed deposit with the lender, kept "
                            "against the loan.",
                 "fee": "Along with the loan there was a charge, a loan processing fee; that is how you understood it."}
                [kind])
    if s["premium"] == "dk":
        dont.append(f"How much was paid for {noun}.")
    else:
        know.append(f"You paid exactly {_w(belief['premium']['value'])} rupees for {noun}.")
    know.append(f"The amount for {noun} was cut from the loan money; you got the loan minus that."
                if belief["source"]["value"] == "from_loan" else
                f"You paid for {noun} separately, apart from the loan; nothing was cut from the loan money.")
    if s["frequency"] == "dk":
        dont.append(f"Whether {noun} is paid once or again and again.")
    else:
        know.append("It was paid one time only; nobody has asked you to pay for it again.")
    if belief["required"]["value"]:
        know.append(f"The officer said {noun} was compulsory for the loan and had to be taken from the lender itself.")
    elif kind == "insurance":
        know.append("Taking it was your own choice, not needed for the loan, and you were told you could take "
                    "such a cover from any company.")
    else:
        know.append(f"You were told {noun} was your own choice and not needed for the loan, and that you could "
                    "take it from any company, not only from this lender.")
    if s["cover"] == "dk":
        dont.append(f"What {noun} gives you, or up to what amount.")
    else:
        know.append(f"You were told that if you die, it pays up to {_w(belief['cover']['value'])} rupees "
                    "towards the loan.")
    if s["term"] == "dk":
        dont.append(f"How long {noun} runs.")
    elif belief["term"].get("said_as") == "as_long_as_loan":
        know.append(f"{noun.capitalize()} runs as long as the loan runs.")
    else:
        know.append(f"{noun.capitalize()} runs for {term_words(belief['term']['value'], 'hi-en')}.")
    if s["cancel"] == "dk":
        dont.append(f"Whether {noun} can be cancelled, or until when.")
    else:
        know.append(f"You were told you could cancel it within {days_words(belief['cancel']['value'], 'hi-en')}.")
    if s["money_back"] == "dk":
        dont.append(f"What would happen to the money paid for {noun} if you wanted it back.")
    elif belief["money_back"]["value"]:
        know.append(f"You believe the money paid for {noun} comes back to you at the end of the loan.")
    else:
        know.append(f"The money paid for {noun} does not come back; it is not savings.")
    know.append(f"You said yes to {noun} together with the loan, {CONSENT_WAY[belief['consent']['value']]}.")
    gender_word = {"f": "a woman", "m": "a man"}[record_gender(record)]
    return {
        "you_are": f"You are {first}, {gender_word} in your {_age_words(lr.borrower.dob)}. (An invented person.) "
                   f"You {pick(OCCUPATIONS, 'occupation')} in {pick(TOWNS, 'town')}.",
        "what_happened": f"Last month you {WHEN[lr.loan_kind.value]} {pick(PURPOSE, 'purpose')}. "
                         "You signed the papers at the lender's desk.",
        "what_you_know": know,
        "what_you_do_not_know": dont,
        "how_you_talk": pick(HOW_YOU_TALK[language], "how_you_talk"),
        "on_this_call": "You pick up and are willing to talk for a few minutes.",
    }


_GENDER: dict[str, str] = {}


def record_gender(record: CallRecord) -> str:
    return _GENDER[record.id]


# ---------------------------------------------------------------- topics and closed statements

TOPIC_FIELDS = {"what_did_you_take": "kind", "what_is_it": "kind", "how_much": "premium", "how_paid": "source",
                "how_often": "frequency", "needed_or_choice": "required", "where_to_take_it_from": "required",
                "what_it_gives": "cover", "how_long": "term", "can_cancel": "cancel", "money_back": "money_back",
                "what_you_agreed_to": "consent"}
VARIANTS = {
    "own": "what this person says when they answer for themselves, from what they know; when they do not know, "
           "they say so in their own words",
    "again": "what they say when the caller asks the same thing a second time in other words: the same content, "
             "worded differently",
    "defer": "what they say when they do not answer for themselves and leave it to the lender, for example "
             "'whatever is in your records': a few words that carry no fact, no figure and no name of anything",
}


def build_topics() -> dict[str, Any]:
    p5 = json.loads((ROOT / "data" / "p5" / "topics.json").read_text(encoding="utf-8"))
    callers = {t["id"]: t["caller"] for t in p5["open_call"]}
    return {
        "about": "The topics an ACQ customer answers in the open call. The caller text is copied from "
                 "the P-five open-call topics (a paraphrase of each question, never a value). Everything the writer model "
                 "is told about the call apart from the customer's own fact sheet.",
        "variants": VARIANTS,
        "open_call": [{"id": tid, "field": field, "caller": callers[tid], "variants": ["own", "again", "defer"]}
                      for tid, field in TOPIC_FIELDS.items()],
    }


CLOSED = {
    "hi": {
        "kind": "आपने लोन के साथ {provider} का एक जीवन बीमा लिया है, जो आपके लोन पर बीमा कवर है। क्या यह सही है?",
        "premium": "इस बीमा का प्रीमियम {premium_words} रुपये था। क्या यह सही है?",
        "source": {"from_loan": "यह प्रीमियम आपके लोन की रकम में से काटा गया था। क्या यह सही है?",
                   "separately": "यह प्रीमियम लोन की रकम से नहीं काटा गया था, आपने इसे अलग से भरा था। क्या यह सही है?"},
        "frequency": "यह प्रीमियम एक ही बार भरा गया था, इसे बार-बार नहीं भरना है। क्या यह सही है?",
        "required": "यह बीमा लेना आपकी अपनी मर्ज़ी थी, लोन के लिए ज़रूरी नहीं था, और आप इसे किसी भी कंपनी से ले सकते थे। क्या यह सही है?",
        "cover": "अगर आपकी मृत्यु हो जाए, तो यह बीमा आपका लोन चुकाने के लिए {cover_words} रुपये तक देता है। क्या यह सही है?",
        "term": "यह बीमा {term_words} तक चलता है। क्या यह सही है?",
        "cancel": "आप यह बीमा {cancel_days_words} के अंदर रद्द करवा सकते थे। क्या यह सही है?",
        "money_back": "यह बीमा कोई जमा या बचत नहीं है, और जो प्रीमियम भरा गया वह आख़िर में वापस नहीं मिलता। क्या यह सही है?",
        "consent": {
            "signed_form": "आपने इस बीमा के लिए एक फ़ॉर्म पर दस्तख़त करके हाँ कहा था। क्या यह सही है?",
            "otp": "आपने इस बीमा के लिए अपने फ़ोन पर आया ओटीपी देकर हाँ कहा था। क्या यह सही है?",
            "digital_click": "आपने इस बीमा के लिए फ़ोन या कंप्यूटर पर एक बटन दबाकर हाँ कहा था। क्या यह सही है?",
            "recorded_call": "आपने इस बीमा के लिए एक रिकॉर्ड की गई फ़ोन कॉल पर हाँ कहा था। क्या यह सही है?"},
    },
    "hi-en": {
        "kind": "आपने loan के साथ {provider} का एक life insurance लिया है, जो आपके loan पर insurance cover है। क्या यह सही है?",
        "premium": "इस insurance का premium {premium_words} rupees था। क्या यह सही है?",
        "source": {"from_loan": "यह premium आपके loan amount में से cut किया गया था। क्या यह सही है?",
                   "separately": "यह premium loan amount से cut नहीं हुआ था, आपने इसे separately pay किया था। क्या यह सही है?"},
        "frequency": "यह premium एक ही बार pay हुआ था, इसे बार-बार pay नहीं करना है। क्या यह सही है?",
        "required": "यह insurance लेना आपकी अपनी choice थी, loan के लिए ज़रूरी नहीं था, और आप इसे किसी भी company से ले सकते थे। क्या यह सही है?",
        "cover": "अगर आपकी death हो जाए, तो यह insurance आपका loan चुकाने के लिए {cover_words} rupees तक देता है। क्या यह सही है?",
        "term": "यह insurance {term_words} तक चलता है। क्या यह सही है?",
        "cancel": "आप यह insurance {cancel_days_words} के अंदर cancel करवा सकते थे। क्या यह सही है?",
        "money_back": "यह insurance कोई deposit या savings नहीं है, और जो premium pay हुआ वह end में वापस नहीं मिलता। क्या यह सही है?",
        "consent": {
            "signed_form": "आपने इस insurance के लिए एक form sign करके हाँ कहा था। क्या यह सही है?",
            "otp": "आपने इस insurance के लिए अपने phone पर आया OTP देकर हाँ कहा था। क्या यह सही है?",
            "digital_click": "आपने इस insurance के लिए phone या computer पर एक button click करके हाँ कहा था। क्या यह सही है?",
            "recorded_call": "आपने इस insurance के लिए एक recorded phone call पर हाँ कहा था। क्या यह सही है?"},
    },
}


def closed_script() -> dict[str, Any]:
    return {"about": "The ACQ closed call: one statement per field, rendered from the record, each ending "
                     "'क्या यह सही है?'. Display only: the closed arm is answered symbolically from the belief. "
                     "Adapted from data/p5/closed_script.json; model-written, no human review.",
            "fields": list(FIELDS), **CLOSED}


def render_closed(cid: str, record: CallRecord, language: str) -> dict[str, Any]:
    p = record.record.products[0]
    slots = {"provider": "नमूना लाइफ़" if language == "hi" else "Namoona Life",
             "premium_words": spoken_amount(p.premium_inr, Language(language)),
             "cover_words": spoken_amount(p.cover_inr, Language(language)),
             "term_words": term_words(p.term_months, language),
             "cancel_days_words": days_words(p.cancel_window_days, language)}
    pick = {"source": "from_loan" if p.paid_from_loan else "separately", "consent": p.consent.method.value}
    statements = []
    for field in FIELDS:
        template = CLOSED[language][field]
        if isinstance(template, dict):
            template = template[pick[field]]
        text = template.format(**slots)
        assert text.endswith("क्या यह सही है?") and not any(ch.isdigit() for ch in text), (cid, field, text)
        statements.append({"field": field, "text": text})
    return {"id": cid, "record_id": record.id, "language": language, "statements": statements}


# ---------------------------------------------------------------- the build


def build() -> tuple[dict[Path, str], list[str]]:
    """Every output file's text, and the exclusions (customers whose belief the engine disagreed with)."""
    rng = random.Random(SEED)
    all_slots = slots()
    rng.shuffle(all_slots)
    out: dict[Path, str] = {}
    customers, gold, closed, exclusions = [], [], [], []
    for n, slot in enumerate(all_slots, start=1):
        cid = f"ACQ-C{n:03d}"
        record = make_record(n, cid, slot, rng)
        _GENDER[record.id] = slot["gender"]
        p = record.record.products[0].model_dump(mode="json")
        belief = make_belief(cid, slot["kind"], p, record.record.tenure_months)
        g = gold_row(cid, slot["kind"], record, belief)
        if g["problems"]:
            exclusions.append(f"{cid} ({slot['kind']}): {'; '.join(g['problems'])}")
        gold.append(g["row"])
        customers.append({
            "id": cid, "record_id": record.id, "kind": slot["kind"], "language": slot["language"],
            "gender": slot["gender"], "writer_model": slot["writer_model"],
            "speaker": {"who": "borrower", "relation": None, "gender": slot["gender"]},
            "belief": belief, "fact_sheet": fact_sheet(cid, record, belief, slot["language"]),
        })
        closed.append(render_closed(cid, record, slot["language"]))
        out[RECORDS / f"{record.id}.json"] = json.dumps(record.model_dump(mode="json"), ensure_ascii=False,
                                                         indent=2, sort_keys=True) + "\n"
    out[DATA / "customers.jsonl"] = dump_jsonl(customers)
    out[DATA / "gold.jsonl"] = dump_jsonl(gold)
    out[DATA / "topics.json"] = json.dumps(build_topics(), ensure_ascii=False, indent=2) + "\n"
    out[DATA / "closed_statements.jsonl"] = dump_jsonl(closed)
    out[CLOSED_SCRIPT] = json.dumps(closed_script(), ensure_ascii=False, indent=2) + "\n"
    return out, exclusions


def counts(customers: list[dict[str, Any]]) -> Counter:
    return Counter((c["kind"], c["language"], c["writer_model"]) for c in customers)


def cmd_build(_: argparse.Namespace) -> None:
    out, exclusions = build()
    if exclusions:
        sys.exit("the engine disagrees with the gold rule; change the generator:\n  " + "\n  ".join(exclusions))
    RECORDS.mkdir(parents=True, exist_ok=True)
    for stale in set(RECORDS.glob("*.json")) - set(out):
        stale.unlink()
    for path, text in out.items():
        path.write_text(text, encoding="utf-8")
    customers = [json.loads(x) for x in out[DATA / "customers.jsonl"].splitlines()]
    print(f"wrote {len(out)} files under {DATA.relative_to(ROOT)}")
    for key, n in sorted(counts(customers).items()):
        print(f"  {key[0]:18} {key[1]:6} {key[2]:30} {n}")


def cmd_check(_: argparse.Namespace) -> None:
    out, exclusions = build()
    diffs = [str(p.relative_to(ROOT)) for p, text in out.items()
             if not p.exists() or p.read_text(encoding="utf-8") != text]
    extra = [str(p.relative_to(ROOT)) for p in RECORDS.glob("*.json") if p not in out]
    if exclusions or diffs or extra:
        print("exclusions:", exclusions, "\ndiffer:", diffs, "\nextra:", extra)
        sys.exit(1)
    print(f"ok: {len(out)} files match")


def input_digests() -> dict[str, str | None]:
    d: dict[str, str | None] = {n: sha256(DATA / n) if (DATA / n).exists() else None for n in FILES}
    d["records"] = records_digest(RECORDS) if RECORDS.is_dir() else None
    return d


WRITER_OUTPUTS = ("knowledge.jsonl", "writer_requests.jsonl")


def output_digests() -> dict[str, str]:
    """The writer's outputs, pinned once they exist so a later edit is caught."""
    return {n: sha256(DATA / n) for n in WRITER_OUTPUTS if (DATA / n).exists()}


def cmd_freeze(_: argparse.Namespace) -> None:
    frozen = {**input_digests(), **output_digests()}
    FROZEN_INPUTS.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    print(FROZEN_INPUTS.read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("freeze-inputs").set_defaults(fn=cmd_freeze)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
