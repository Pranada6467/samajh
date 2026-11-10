"""P3a re-verification (round 3): cover/premium read-back orders and denial orders, scripted model.

    uv run python references/reviews/iter2/probes/p3a_r3_orders.py

Offline. The model is scripted (the correct reading of each reply; the change check says "none"
unless scripted), so this tests the CODE: extract assembly + to_beliefs + the rules. Record: the
iter1 informed BASE (cover 3,50,000, premium 41,300, credit-life insurance). Gold before the run.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402

from samajh.clients.llm import LlmResult  # noqa: E402
from samajh.extract import extract  # noqa: E402
from samajh.rules import evaluate, to_beliefs  # noqa: E402

_USER = re.compile(r"Assistant's question: <<<(.*?)>>>\nCustomer's reply: <<<(.*?)>>>", re.DOTALL)
RANK = {"clear": 0, "understanding_gap": 1, "incomplete": 2, "refer": 3}


class Scripted:
    def __init__(self, outputs, changes=None):
        self.outputs, self.changes = outputs, changes or {}

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        q, r = _USER.search(messages[1].content).groups()
        if schema.__name__ == "ScreenReply":
            out = {"claims": [], "concerns": []}
        elif schema.__name__ == "ChangeReply":
            out = self.changes.get(r, {"change": "none", "first_clauses": [], "final_clauses": []})
        else:
            out = self.outputs[(q, r)]
            if schema.__name__ == "RecallReply":
                out = {"took_nothing": False, **out}
        return LlmResult(value=schema.model_validate(out), model="scripted", prompt_tokens=0,
                         completion_tokens=0, usd=0.0, cache_hit=True, attempts=0, generation_id=None)


def run(rows, changes=None):
    transcript, outputs = ea.build(rows)
    rec = ea.record()
    raw = extract(transcript, rec, Scripted(outputs, changes))
    res = evaluate(rec, to_beliefs(raw, rec, transcript))
    rs = sorted({f.reason.value for f in res.all_flags()} | {f"gap:{g.rule_id.value}:{g.reason.value}"
                                                            for g in res.all_gaps()})
    return res.tier.value, rs


def span(text):
    return {"status": "stated", "span": text, "clauses": [1]}


def without(rows, pred):
    return [r for r in rows if not pred(r)]


COVER_Q = "उसमें कितनी रकम का कवर है?"
FIG = {  # reply, span, hedged?
    "right": ("साढ़े तीन लाख रुपये।", "साढ़े तीन लाख"),
    "wrong": ("दस लाख रुपये।", "दस लाख"),
    "hedged": ("शायद दस लाख रुपये।", "दस लाख"),
}
SAY = {"साढ़े तीन लाख": "साढ़े तीन लाख, यानी 3,50,000 रुपये, सही है?", "दस लाख": "दस लाख, यानी 10,00,000 रुपये, सही है?",
       "पाँच लाख": "पाँच लाख, यानी 5,00,000 रुपये, सही है?"}


def rb(reply, confirms, corrected=None, n=(1,)):
    return {"status": "stated", "confirms": confirms, "clauses": list(n), "corrected_amount_span": corrected}


def cover_rows(fig, order):
    reply, sp = FIG[fig]
    base = [r for r in ea.BASE if r[1] != "cover"]
    rows = base + [("teach_back", "cover", COVER_Q, reply, span(sp))]
    q = SAY[sp]
    if order == "none":
        pass
    elif order == "yes":
        rows.append(("read_back", "cover", q, "हाँ जी।", rb("हाँ जी।", True)))
    elif order == "no":
        rows.append(("read_back", "cover", q, "नहीं जी।", rb("", False)))
    elif order == "no+corr_record":
        rows.append(("read_back", "cover", q, "नहीं, साढ़े तीन लाख है।", rb("", False, "साढ़े तीन लाख", (1, 2))))
    elif order == "no+corr_wrong":
        rows.append(("read_back", "cover", q, "नहीं, पाँच लाख है।", rb("", False, "पाँच लाख", (1, 2))))
    elif order == "mismatch":
        other = SAY["पाँच लाख"] if sp != "पाँच लाख" else SAY["दस लाख"]
        rows.append(("read_back", "cover", other, "हाँ जी।", rb("", True)))
    elif order == "yes_restated":
        rows.append(("read_back", "cover", q, "हाँ जी।", rb("", True)))
        rows.append(("teach_back", "cover", "एक बार फिर, कवर कितने का है?", reply.replace("रुपये", "ही है"),
                     span(sp)))
    return rows


# gold written before the run
COVER_GOLD = {
    ("right", "none"): "clear", ("right", "yes"): "clear", ("right", "no"): "understanding_gap",
    ("right", "no+corr_record"): "clear", ("right", "no+corr_wrong"): "incomplete",
    ("right", "mismatch"): "understanding_gap", ("right", "yes_restated"): "clear",
    ("wrong", "none"): "incomplete", ("wrong", "yes"): "refer", ("wrong", "no"): "incomplete",
    ("wrong", "no+corr_record"): "clear", ("wrong", "no+corr_wrong"): "incomplete",
    ("wrong", "mismatch"): "incomplete", ("wrong", "yes_restated"): "refer",
    ("hedged", "none"): "understanding_gap", ("hedged", "yes"): "understanding_gap",
    ("hedged", "no"): "understanding_gap", ("hedged", "no+corr_record"): "clear",
    ("hedged", "no+corr_wrong"): "incomplete", ("hedged", "mismatch"): "understanding_gap",
    ("hedged", "yes_restated"): "understanding_gap",
}

PREM_Q = "उसके लिए आपने कितने रुपये दिए?"
PFIG = {"right": ("इकतालीस हज़ार तीन सौ रुपये।", "इकतालीस हज़ार तीन सौ"), "wrong": ("साठ हज़ार रुपये।", "साठ हज़ार")}
PSAY = {"इकतालीस हज़ार तीन सौ": "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?",
        "साठ हज़ार": "साठ हज़ार, यानी 60,000 रुपये, सही है?", "सत्तर हज़ार": "सत्तर हज़ार, यानी 70,000 रुपये, सही है?"}


def prem_rows(fig, order):
    reply, sp = PFIG[fig]
    rows = [r for r in ea.BASE if r[1] != "premium"]
    rows.insert(2, ("teach_back", "premium", PREM_Q, reply, span(sp)))
    q = PSAY[sp]
    if order == "yes":
        rows.append(("read_back", "premium", q, "हाँ जी।", rb("", True)))
    elif order == "no":
        rows.append(("read_back", "premium", q, "नहीं जी।", rb("", False)))
    elif order == "no+corr_record":
        rows.append(("read_back", "premium", q, "नहीं, इकतालीस हज़ार तीन सौ।",
                     rb("", False, "इकतालीस हज़ार तीन सौ", (1, 2))))
    elif order == "mismatch":
        rows.append(("read_back", "premium", PSAY["सत्तर हज़ार"], "हाँ जी।", rb("", True)))
    return rows


PREM_GOLD = {("right", "none"): "incomplete", ("right", "yes"): "clear", ("right", "no"): "incomplete",
             ("right", "no+corr_record"): {"incomplete", "clear"}, ("right", "mismatch"): "incomplete",
             ("wrong", "none"): "incomplete", ("wrong", "yes"): "refer", ("wrong", "no"): "incomplete",
             ("wrong", "no+corr_record"): {"incomplete", "clear"}, ("wrong", "mismatch"): "incomplete"}

# --- denial orders ---
RECALL_Q = "लोन के साथ आपने क्या-क्या लिया, और कितने का?"
RECALL_Q2 = "और कुछ याद आता है, लोन के साथ क्या लिया?"
DENY = ("open_recall", None, RECALL_Q2, "नहीं, कुछ नहीं लिया, बस लोन।", {"items": [], "took_nothing": True})


def item(text, kind):
    return {"items": [{"span": text, "kind": kind, "amount_span": None}]}


def denial_cases():
    base = [r for r in ea.BASE if r[0] != "open_recall"]
    named = ("open_recall", None, RECALL_Q, "एक बीमा लिया था।", item("एक बीमा", "insurance"))
    deny1 = ("open_recall", None, RECALL_Q, "कुछ नहीं लिया, सिर्फ़ लोन।", {"items": [], "took_nothing": True})
    later_ins = ("open_recall", None, RECALL_Q2, "अच्छा हाँ, एक बीमा भी था।", item("एक बीमा", "insurance"))
    later_fd = ("open_recall", None, RECALL_Q2, "अच्छा हाँ, एक एफ़डी भी थी।", item("एक एफ़डी", "deposit"))
    kind_fd = [("teach_back", "kind", r[2], "एफ़डी है।", {"status": "stated", "kind": "deposit", "clauses": [1]})
               if r[1] == "kind" else r for r in base]
    named_back = ("open_recall", None, RECALL_Q, "बीमा लिया था, नहीं नहीं, कुछ नहीं लिया।",
                  {"items": [{"span": "बीमा", "kind": "insurance", "amount_span": None}], "took_nothing": True})
    nb_change = {"बीमा लिया था, नहीं नहीं, कुछ नहीं लिया।": {"change": "withdrawn", "first_clauses": [1],
                                                          "final_clauses": []}}
    no_kind = [r for r in base if r[1] != "kind"]
    return [
        ("named, then denial (2nd recall), kind q answered insurance after both -> retracted by the kind answer",
         [named, DENY, *base], None, {"understanding_gap"}),
        ("named, then denial (2nd recall reply), NO kind question -> denial stands", [named, DENY, *no_kind], None,
         {"refer"}),
        ("denial, then named as insurance (2nd recall) -> retracted", [deny1, later_ins, *base], None,
         {"understanding_gap"}),
        ("denial, then 'एक एफ़डी' (2nd recall), kind q says FD -> refer", [deny1, later_fd, *kind_fd], None, {"refer"}),
        ("denial, then kind question answered insurance -> retracted", [deny1, *base], None, {"understanding_gap"}),
        ("denial, no kind question, nothing else -> refer", [deny1, *no_kind], None, {"refer"}),
        ("one recall reply names and takes back ('बीमा लिया था, नहीं नहीं, कुछ नहीं लिया'), no kind q",
         [named_back, *no_kind], nb_change, {"refer", "incomplete"}),
        ("denial, then kind answered as FD (misdescription) -> refer", [deny1, *kind_fd], None, {"refer"}),
    ]


def main() -> int:
    bad = 0
    print("== cover grid ==")
    tiers = {}
    for (fig, order), want in COVER_GOLD.items():
        tier, rs = run(cover_rows(fig, order))
        tiers[(fig, order)] = tier
        ok = tier == want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} cover {fig:6} {order:15} {tier:17} want {want:17} {rs}")
    for fig in FIG:
        base = RANK[tiers[(fig, "none")]]
        low = [o for (f, o), t in tiers.items() if f == fig and o in ("yes", "no", "mismatch", "yes_restated")
               and RANK[t] < base and not (fig != "hedged" and o in ("yes", "yes_restated") and t == "clear")]
        print(f"   monotonic check {fig}: read-back orders below no-read-back ({tiers[(fig, 'none')]}): {low}")
    print("== premium grid ==")
    for (fig, order), want in PREM_GOLD.items():
        rows = prem_rows(fig, order)
        tier, rs = run(rows)
        want = want if isinstance(want, set) else {want}
        ok = tier in want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} premium {fig:6} {order:15} {tier:17} want {sorted(want)} {rs}")
    print("== denial orders ==")
    for name, rows, changes, want in denial_cases():
        tier, rs = run(rows, changes)
        ok = tier in want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {tier:17} want {sorted(want)} | {name}\n      {rs}")
    print(f"\n{bad} outside gold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
