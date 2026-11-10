"""P3a re-verification (round 2): the whole decision chain (extract -> to_beliefs -> evaluate) with a
scripted model, on fresh transcripts. Offline, no network, no LLM.

    uv run python references/reviews/iter2/probes/p3a_r2_chain.py

Reuses the iter1 extractor_attacks scaffolding (an informed Hindi customer on a compliant record:
insurance, premium 41,300 from the loan, cover 3,50,000, 36 months, 30-day window, OTP consent).
Each case swaps or inserts turns. Where the model's reading matters the scripted output is the
adversarial one (for a retraction: the model quotes the clause that was taken back), so the case
tests what the code does with it. `want` (tiers accepted) and, for recall cases, `recall` (the
recall flag reason accepted) were written before the first run. BAD = outside them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402

from samajh.clients.errors import LlmOutputInvalid  # noqa: E402
from samajh.extract import extract  # noqa: E402
from samajh.rules import evaluate, to_beliefs  # noqa: E402
from samajh.types import Tier  # noqa: E402

R, I, G, C = Tier.refer, Tier.incomplete, Tier.understanding_gap, Tier.clear
BASE = [r if r[0] != "open_recall" else (*r[:4], {**r[4], "took_nothing": False}) for r in ea.BASE]
KIND_Q, PREM_Q, PAY_Q, REQ_Q = (BASE[i][2] for i in (1, 2, 3, 4))
COVER_Q, FEAT_Q, CONS_Q = BASE[5][2], BASE[8][2], BASE[9][2]
RECALL_Q = BASE[0][2]


class Failing(ea.Scripted):
    def __init__(self, outputs, fail=()):
        super().__init__(outputs, None)
        self.fail = set(fail)

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        _q, reply = ea._USER.search(messages[1].content).groups()
        if schema.__name__ != "ScreenReply" and reply in self.fail:
            raise LlmOutputInvalid(model="scripted", attempts=3, last_error="x")
        return super().complete(schema, messages, model=model, max_tokens=max_tokens)


def kind(reply, value="insurance", clauses=(1,), status="stated"):
    return ("teach_back", "kind", KIND_Q, reply, {"status": status, "kind": value if status == "stated" else None,
                                                  "clauses": list(clauses)})


def kind_again(reply, value="insurance", clauses=(1,), status="stated"):
    row = kind(reply, value, clauses, status)
    return (row[0], row[1], "माफ़ कीजिए, फिर से बताइए: वह क्या है?", row[3], row[4])


def pay(reply, source, clauses=(1,), again=False):
    q = "एक बार फिर बताइए, वह रकम कैसे चुकाई गई?" if again else PAY_Q
    return ("teach_back", "payment_source", q, reply, {"status": "stated", "source": source, "clauses": list(clauses)})


def req(reply, yes, clauses=(1,), again=False):
    q = "फिर से पूछ रही हूँ, क्या उसे लेना ज़रूरी था?" if again else REQ_Q
    return ("teach_back", "required_for_loan", q, reply, {"status": "stated", "yes": yes, "clauses": list(clauses)})


def cover(reply, span, clauses=(1,), status="stated", q=COVER_Q):
    return ("teach_back", "cover", q, reply, {"status": status, "span": span, "clauses": list(clauses)})


def cover_rb(bot, reply, confirms, clauses=(1,), corrected=None):
    return ("read_back", "cover", bot, reply,
            {"status": "stated", "confirms": confirms, "clauses": list(clauses), "corrected_amount_span": corrected})


def recall(reply, items=(), took_nothing=False, q=RECALL_Q):
    return ("open_recall", None, q, reply,
            {"items": [{"span": s, "kind": k, "amount_span": None} for s, k in items], "took_nothing": took_nothing})


def replace(rows, asks, new, step="teach_back"):
    return [new if (r[1] == asks and r[0] == step) else r for r in rows]


def drop(rows, asks, step="teach_back"):
    return [r for r in rows if not (r[1] == asks and r[0] == step)]


def after(rows, asks, *extra, step="teach_back"):
    out = []
    for r in rows:
        out.append(r)
        if r[1] == asks and r[0] == step:
            out.extend(extra)
    return out


CASES = []


def case(group, name, rows, want, recall_ok=None, fail=()):
    CASES.append((group, name, rows, set(want), recall_ok, fail))


NOT_CLEAR = {R, I}
# ---------------------------------------------------------------- retraction, later clause
for reply in [
    "बीमा है, नहीं, एफ़डी है।",
    "बीमा है, ना ना, एफ़डी है।",
    "बीमा है, नहीं जी, गलती हो गई, एफ़डी है।",
    "insurance hai, no no, FD hai.",
    "insurance hai, nahi wait, FD hai.",
    "बीमा है, मैं गलत बोल गया, एफ़डी है।",
    "बीमा है, अरे नहीं, एफ़डी है।",
    "insurance hai, I mean FD hai.",
    "बीमा है, माफ़ कीजिए, एफ़डी है।",
    "बीमा है, रुकिए, वो एफ़डी थी।",
    "बीमा है, गलत बताया, एफ़डी है।",
    "बीमा है नहीं नहीं एफ़डी है",            # no punctuation, as speech-to-text may give it
    "बीमा है, ऐसा तो नहीं था।",              # listed form: control
    "बीमा है, नहीं नहीं, एफ़डी है।",          # listed form: control
    "insurance hai, galat bola, FD hai.",     # listed form: control
]:
    case("retract", f"kind {reply!r}, model quotes clause 1 (insurance)", replace(BASE, "kind", kind(reply)), NOT_CLEAR)
for reply, src in [
    ("लोन से कटा था, नहीं, अलग से नकद दिया था।", "from_loan"),
    ("loan se kata tha, no no, alag se diya tha.", "from_loan"),
    ("लोन से कटा था, सॉरी, अलग से दिया था।", "from_loan"),          # listed: control
]:
    case("retract", f"payment {reply!r}, model says from_loan (clause 1)", replace(BASE, "payment_source", pay(reply, src)), NOT_CLEAR)
for reply in [
    "नहीं, मर्ज़ी से लिया, नहीं, असल में ज़रूरी बोला था।",
    "nahi, apni marzi se, actually zaroori bola tha.",
    "नहीं, मर्ज़ी से लिया, गलत कहा, ज़रूरी था।",                      # listed: control
]:
    case("retract", f"required {reply!r}, model says no (clauses 1-2)", replace(BASE, "required_for_loan", req(reply, False, (1, 2))), NOT_CLEAR)
# over-firing: an informed reply with a listed phrase that takes nothing back (clear expected; incomplete is noise)
for asks, row in [
    ("features", ("teach_back", "features", FEAT_Q, "नहीं, वापस नहीं मिलता, नहीं नहीं, बिल्कुल नहीं।",
                  {"status": "stated", "claims": [], "clauses": [1, 2]})),
    ("kind", kind("बीमा है, सॉरी, आवाज़ कट रही थी।")),
    ("required_for_loan", req("नहीं, ज़रूरी नहीं था, नहीं नहीं, मर्ज़ी से लिया।", False, (1,))),
    # added after the first run (same expectation: an informed customer, nothing taken back)
    ("required_for_loan", req("नहीं, ज़रूरी नहीं था, वो नहीं था ज़रूरी।", False, (1,))),
    ("payment_source", pay("लोन में से कटा था, sorry, network problem था।", "from_loan")),
    ("features", ("teach_back", "features", FEAT_Q, "नहीं, वापस नहीं मिलता, ऐसा तो नहीं था कि वापस मिलेगा।",
                  {"status": "stated", "claims": [], "clauses": [1, 2]})),
    ("kind", kind("बीमा है, एफ़डी नहीं, वो नहीं था।", "insurance", (1,))),
]:
    case("overfire", f"{asks} {row[3]!r} (informed, nothing taken back)", replace(BASE, asks, row), {C})

# ---------------------------------------------------------------- denial persistence
DENY = recall("कुछ नहीं लिया, बस लोन लिया था।", took_nothing=True)
NAMES = recall("हाँ, एक बीमा लिया था।", items=[("एक बीमा", "insurance")], q="और कुछ याद आ रहा है, लोन के साथ?")
DENY2 = recall("नहीं, कुछ नहीं लिया, बस लोन।", took_nothing=True, q="और कुछ याद आ रहा है, लोन के साथ?")
REST = BASE[1:]
case("denial", "deny, then names insurance in a 2nd recall reply, kind insurance", [DENY, NAMES, *REST], {G}, {"recall_not_named"})
case("denial", "names insurance, then DENIES in a 2nd recall reply, no kind question",
     [recall("एक बीमा लिया था।", items=[("एक बीमा", "insurance")]), DENY2, *drop(REST, "kind")],
     {R, I}, {"recall_denied"})
case("denial", "names insurance, then DENIES in a 2nd recall reply, kind insurance (named after the denial)",
     [recall("एक बीमा लिया था।", items=[("एक बीमा", "insurance")]), DENY2, *REST], {G, R}, {"recall_not_named", "recall_denied"})
case("denial", "deny, kind 'शायद बीमा' (hedged naming)", [DENY, *replace(REST, "kind", kind("शायद बीमा है।"))],
     {G}, {"recall_not_named"})
case("denial", "deny, kind 'बीमा तो नहीं, एफ़डी है' (model: deposit)",
     [DENY, *replace(REST, "kind", kind("बीमा तो नहीं, एफ़डी है।", "deposit", (1, 2)))], {R}, {"recall_denied"})
case("denial", "deny, 2nd recall names an FD (off record), kind deposit",
     [DENY, recall("एक एफ़डी बनवाई थी।", items=[("एक एफ़डी", "deposit")], q=NAMES[2]),
      *replace(REST, "kind", kind("एफ़डी है।", "deposit"))], {R}, {"recall_denied"})
case("denial", "deny, 2nd recall 'बीमा लिया था, नहीं नहीं, कुछ नहीं' (model: item insurance), no kind question",
     [DENY, recall("बीमा लिया था, नहीं नहीं, कुछ नहीं लिया।", items=[("बीमा लिया था", "insurance")], q=NAMES[2]),
      *drop(REST, "kind")], {R, I}, {"recall_denied"})
case("denial", "deny, kind 'पता नहीं'", [DENY, *replace(REST, "kind", kind("पता नहीं।", status="dont_know"))],
     {R}, {"recall_denied"})
case("denial", "deny, kind question answer retracted 'बीमा है, नहीं नहीं, पता नहीं'",
     [DENY, *replace(REST, "kind", kind("बीमा है, नहीं नहीं, पता नहीं।"))], {R, I}, {"recall_denied"})
case("denial", "deny, kind question 'बीमा है, नहीं, कुछ नहीं लिया' (unlisted retraction; model: insurance)",
     [DENY, *replace(REST, "kind", kind("बीमा है, नहीं, कुछ नहीं लिया।"))], {R, I}, {"recall_denied"})
case("denial", "deny + 'अरे हाँ, बीमा' in the same reply (model: took_nothing true and an item)",
     [recall("कुछ नहीं लिया, अरे हाँ, एक बीमा लिया था।", items=[("एक बीमा", "insurance")], took_nothing=True), *REST],
     {C, G}, None)

# ---------------------------------------------------------------- cover read-back tier (record 3,50,000)
TEN = cover("दस लाख रुपये।", "दस लाख")
RB_TEN_YES = cover_rb("दस लाख, यानी 10,00,000 रुपये का कवर, सही है?", "हाँ, सही है।", True, (1, 2))
case("cover", "10 lakh plain, read back 10 lakh, yes", after(replace(BASE, "cover", TEN), "cover", RB_TEN_YES), {R})
case("cover", "10 lakh plain, no read-back", replace(BASE, "cover", TEN), {I})
case("cover", "'शायद दस लाख' hedged, read back yes", after(replace(BASE, "cover", cover("शायद दस लाख।", "दस लाख")), "cover",
     RB_TEN_YES), {G})
case("cover", "'करीब दस लाख' approximate, no read-back", replace(BASE, "cover", cover("करीब दस लाख।", "दस लाख")), {G})
case("cover", "'पता नहीं' cover", replace(BASE, "cover", cover("पता नहीं।", None, status="dont_know")), {G})
case("cover", "10 lakh plain, read back 10 lakh, 'नहीं' with no correction",
     after(replace(BASE, "cover", TEN), "cover", cover_rb(RB_TEN_YES[2], "नहीं।", False)), {I})
case("cover", "10 lakh plain, bot reads back 5 lakh (mismatch), yes",
     after(replace(BASE, "cover", TEN), "cover", cover_rb("पाँच लाख, यानी 5,00,000 रुपये, सही है?", "हाँ।", True)), {I})
case("cover", "10 lakh plain, read back yes, then cover re-asked: 'दस लाख' again",
     after(replace(BASE, "cover", TEN), "cover", RB_TEN_YES, cover("दस लाख ही है।", "दस लाख", q="कवर फिर से बताइए?")), {R, I})
case("cover", "10 lakh, read back yes, re-asked '5 lakh' (two wrong confident figures)",
     after(replace(BASE, "cover", TEN), "cover", RB_TEN_YES, cover("पाँच लाख।", "पाँच लाख", q="कवर फिर से बताइए?")), {R, I, G})
case("cover", "10 lakh, read back 'हाँ, नहीं नहीं, साढ़े तीन लाख' (retracted yes)",
     after(replace(BASE, "cover", TEN), "cover", cover_rb(RB_TEN_YES[2], "हाँ, नहीं नहीं, साढ़े तीन लाख।", True)), {I, G})
case("cover", "10 lakh, read back 'नहीं, साढ़े तीन लाख' (corrected to the record)",
     after(replace(BASE, "cover", TEN), "cover", cover_rb(RB_TEN_YES[2], "नहीं, साढ़े तीन लाख।", False, (1, 2),
                                                          corrected="साढ़े तीन लाख")), {C})
case("cover", "3.5 lakh (record), read back 3.5 lakh, 'नहीं' (rejected, no correction)",
     after(BASE, "cover", cover_rb("साढ़े तीन लाख, यानी 3,50,000 रुपये, सही है?", "नहीं।", False)), {G, I})
case("cover", "10 lakh plain, read back yes, term 5 years, window 15 days",
     replace(replace(after(replace(BASE, "cover", TEN), "cover", RB_TEN_YES), "term",
                     ("teach_back", "term", BASE[6][2], "पाँच साल।", {"status": "stated", "span": "पाँच साल", "clauses": [1]})),
             "cancel_window", ("teach_back", "cancel_window", BASE[7][2], "हाँ, पंद्रह दिन।",
                               {"allowed_status": "stated", "allowed": True, "allowed_clauses": [1], "window_status": "stated",
                                "window_span": "पंद्रह दिन", "window_clauses": [2]})), {R})
case("cover", "term wrong (5 years) only", replace(BASE, "term",
     ("teach_back", "term", BASE[6][2], "पाँच साल।", {"status": "stated", "span": "पाँच साल", "clauses": [1]})), {G})
case("cover", "window wrong (15 days) only", replace(BASE, "cancel_window",
     ("teach_back", "cancel_window", BASE[7][2], "हाँ, पंद्रह दिन।", {"allowed_status": "stated", "allowed": True,
      "allowed_clauses": [1], "window_status": "stated", "window_span": "पंद्रह दिन", "window_clauses": [2]})), {G})

# ---------------------------------------------------------------- conflicts and re-asks across turns
case("conflict", "payment: loan, re-ask: cash separately", after(BASE, "payment_source",
     pay("अलग से नकद दिया था।", "separately", again=True)), {R})
case("conflict", "kind: insurance, re-ask 'पता नहीं' (not a conflict by contract)",
     after(BASE, "kind", kind_again("पता नहीं।", status="dont_know")), {C, G})
case("conflict", "kind: 'पता नहीं', re-ask 'बीमा'",
     after(replace(BASE, "kind", kind("पता नहीं।", status="dont_know")), "kind", kind_again("बीमा है।")), {C, G})
case("conflict", "kind: insurance, re-ask 'शायद एफ़डी'", after(BASE, "kind", kind_again("शायद एफ़डी है।", "deposit")), {R})
case("conflict", "kind three times: insurance, FD, insurance",
     after(BASE, "kind", kind_again("एफ़डी है।", "deposit"), kind_again("नहीं, बीमा ही है।", "insurance", (1, 2))), {R})
case("conflict", "required: no, re-ask: yes", after(BASE, "required_for_loan", req("हाँ, ज़रूरी बताया था।", True, again=True)), {R})
case("conflict", "premium 41,300, re-ask 'करीब पचास हज़ार' (beyond 10%)",
     after(BASE, "premium", ("teach_back", "premium", "एक बार फिर बताइए, कितने दिए?", "करीब पचास हज़ार।",
                             {"status": "stated", "span": "पचास हज़ार", "clauses": [1]})), {R, I})
case("conflict", "premium 41,300, re-ask 41,000 (within 1%: not a conflict), read back 41,300 yes",
     after(BASE, "premium", ("teach_back", "premium", "एक बार फिर बताइए, कितने दिए?", "इकतालीस हज़ार।",
                             {"status": "stated", "span": "इकतालीस हज़ार", "clauses": [1]})), {C, I, R})
case("conflict", "kind asked twice, FIRST asking's model call fails, second 'बीमा'",
     after(BASE, "kind", kind_again("बीमा है जी।")), {I}, fail={"बीमा है।"})
case("conflict", "payment asked twice, second 'लोन से' and its call fails",
     after(BASE, "payment_source", pay("लोन से ही कटा।", "from_loan", again=True)), {I}, fail={"लोन से ही कटा।"})
case("conflict", "recall: insurance, 2nd recall names an FD as well (off record)",
     [BASE[0], recall("और एक एफ़डी भी बनी थी।", items=[("एक एफ़डी", "deposit")], q=NAMES[2]), *REST], {R})
case("conflict", "payment: loan, re-ask 'नहीं, अलग से' in a later turn, where 'नहीं' opens the reply",
     after(BASE, "payment_source", pay("नहीं, अलग से दिया था।", "separately", (1, 2), again=True)), {R})


def main() -> int:
    bad = 0
    by_group: dict[str, list[int]] = {}
    for group, name, rows, want, recall_ok, fail in CASES:
        transcript, outputs = ea.build(rows)
        rec = ea.record()
        raw = extract(transcript, rec, Failing(outputs, fail))
        res = evaluate(rec, to_beliefs(raw, rec, transcript))
        flags = [f for f in res.all_flags()]
        recall_reasons = {f.reason.value for f in flags if f.rule_id.value == "recall"}
        ok = res.tier in want and (recall_ok is None or (recall_reasons & recall_ok) or (not recall_reasons and "" in recall_ok))
        by_group.setdefault(group, [0, 0])
        by_group[group][0] += 1
        by_group[group][1] += not ok
        bad += not ok
        reasons = sorted({f"{f.rule_id.value}:{f.reason.value}" for f in flags}
                         | {f"gap {g.rule_id.value}:{g.reason.value}" for g in res.all_gaps()})
        extra = f" recall {sorted(recall_reasons)} want {sorted(recall_ok)}" if recall_ok else ""
        print(f"{'ok ' if ok else 'BAD'} [{group}] {res.tier.value:17} want {sorted(t.value for t in want)}{extra} | {name} | {reasons}")
    print()
    for g, (n, b) in by_group.items():
        print(f"{g:9} n={n} outside the verifier's reading: {b}")
    print(f"total {len(CASES)}, BAD {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
