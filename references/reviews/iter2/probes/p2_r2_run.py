"""P2 round-2 verifier probe: plays p2_r2_inputs.json and p2_r2_personas.json through samajh.dialogue start/step.

Arms:
  rules    word lists only (RuleInterpreter)
  live     LlmFallbackInterpreter wired as samajh/server/samajh_dialogue.py wires it
           (LlmClient.from_env(timeout=3.0, retry=RetryPolicy(max_attempts=1)), the dialogue's own model)
  failing  the same interpreter with a client whose complete() raises
  slow     the same interpreter with a client that sleeps 4.0 s, then answers (subset only: `slow`)

Usage (repo root):
  uv run python references/reviews/iter2/probes/p2_r2_run.py groups rules|live|failing
  uv run python references/reviews/iter2/probes/p2_r2_run.py calls rules|live|failing
  uv run python references/reviews/iter2/probes/p2_r2_run.py slow
Outputs go beside this file as p2_r2_<what>_<arm>.jsonl; an existing file is never overwritten (a rerun writes a
timestamped copy). Latencies of every classifier call go to p2_r2_latency_<arm>_<UTC timestamp>.jsonl.
No Gnani calls. LLM calls only through samajh/clients/llm.py with FALLBACK_MODEL.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language, LoanRecord

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LENDER = "Udaharan Bank"
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

_BASE = json.loads((ROOT / "tests/dialogue/fixtures/record_gold_loan.json").read_text())


def _record(name: str) -> LoanRecord:
    data = json.loads(json.dumps(_BASE))
    data["borrower"]["name"] = name
    return LoanRecord.model_validate(data)


RECORDS = {
    "ramesh": _record("Ramesh Namoona"),
    "ramesh_dev": _record("रमेश नमूना"),
    "sunita": _record("Sunita Namoona"),
    "irfan": _record("Irfan Namoona"),
    "gurpreet": _record("Gurpreet Namoona"),
    "lakshmi": _record("Lakshmi Namoona"),
}

# What a listener learns from a bot line.
LEAKS = {
    "lender": re.compile(r"Udaharan", re.I),
    "loan": re.compile(r"लोन|loan|ऋण|क़र्ज़|कर्ज़|कर्ज", re.I),
    "product": re.compile(r"बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|\bcover|एफ़डी|एफडी|\bFD\b|deposit", re.I),
    "value": re.compile(r"\d|बावन|fifty|पाँच लाख|paanch lakh|चौबीस|तीस दिन|Namoona|नमूना|चौरासी", re.I),
}
OLD_LEAK = re.compile(r"Udaharan|लोन|loan|बीमा|insurance|पैसे|रक़म|रुपये|rupees|\d", re.I)  # old verifier's

PREFIX = {
    "hi": {"claim": "हाँ जी, मैं ही बोल रहा हूँ", "yes": "हाँ", "year": "1984", "recall": "हाँ, एक चीज़ और ली थी"},
    "hi-en": {"claim": "haan ji, main hi bol raha hoon", "yes": "haan", "year": "1984", "recall": "haan, ek cheez aur li thi"},
}
POINT_PREFIX = {
    "opening": [], "go_ahead": ["claim"], "birth_year": ["claim", "yes"],
    "mid_recall": ["claim", "yes", "year"], "mid_kind": ["claim", "yes", "year", "recall"],
}
POINT_WANT = {"opening": "right_party.ask", "go_ahead": "disclosure.go_ahead", "birth_year": "second_check.ask",
              "mid_recall": "open_recall.ask", "mid_kind": "kind.ask"}


# ---------------------------------------------------------------- clients and interpreters


class Recorder:
    """Wraps an LlmClient; records each classifier call (latency, cache hit, cost, label)."""

    def __init__(self, inner, arm: str):
        self.inner, self.arm, self.rows, self.ctx = inner, arm, [], {}

    def complete(self, schema, messages, **kw):
        t0 = time.monotonic()
        row = {"arm": self.arm, **self.ctx, "reply": messages[-1].content.split("Reply: ", 1)[-1]}
        try:
            res = self.inner.complete(schema, messages, **kw)
        except Exception as e:  # noqa: BLE001
            row.update(seconds=round(time.monotonic() - t0, 3), error=type(e).__name__)
            self.rows.append(row)
            raise
        row.update(seconds=round(time.monotonic() - t0, 3), cache_hit=getattr(res, "cache_hit", None),
                   usd=getattr(res, "usd", None), label=str(res.value.label), late=time.monotonic() - t0 > 2.5)
        self.rows.append(row)
        return res


class Switch:
    """Live client until `raising` is set: the classifier fails on the turns under test only (arm failturn)."""

    def __init__(self, inner):
        self.inner, self.raising = inner, False

    def complete(self, schema, messages, **kw):
        if self.raising:
            raise RuntimeError("verifier: classifier down on this turn")
        return self.inner.complete(schema, messages, **kw)


class Raising:
    def complete(self, schema, messages, **kw):
        raise RuntimeError("verifier: classifier down")


class Sleeping:
    def __init__(self, seconds: float):
        self.seconds = seconds

    def complete(self, schema, messages, **kw):
        time.sleep(self.seconds)
        return SimpleNamespace(value=SimpleNamespace(label=schema.model_fields["label"].annotation("confirms_self")),
                               cache_hit=False, usd=0.0)


class Timed:
    """Times each interpret() and notes whether the classifier was consulted."""

    def __init__(self, inner, recorder: Recorder | None):
        self.inner, self.rec, self.turns = inner, recorder, []

    def interpret(self, text, *, language, expecting, question):
        before = len(self.rec.rows) if self.rec else 0
        t0 = time.monotonic()
        out = self.inner.interpret(text, language=language, expecting=expecting, question=question)
        dt = time.monotonic() - t0
        consulted = (len(self.rec.rows) > before) if self.rec else False
        # a late call has not returned yet when interpret() returns: count it as consulted
        if self.rec and not consulted and dt > 2.0:
            consulted = True
        self.turns.append({"expecting": str(expecting), "seconds": round(dt, 3), "consulted": consulted,
                           "degraded": out.degraded if hasattr(out, "degraded") else None})
        return out


def make(arm: str):
    rules = RuleInterpreter()
    if arm == "rules":
        return Timed(rules, None), None
    if arm in ("live", "failturn"):
        from samajh.clients._runtime import RetryPolicy
        from samajh.clients.llm import LlmClient

        client = LlmClient.from_env(timeout=3.0, retry=RetryPolicy(max_attempts=1), usd_cap=2.0)
        rec = Recorder(Switch(client) if arm == "failturn" else client, arm)
    elif arm == "failing":
        rec = Recorder(Raising(), arm)
    elif arm == "slow":
        rec = Recorder(Sleeping(4.0), arm)
    else:
        raise SystemExit(f"unknown arm {arm}")
    return Timed(LlmFallbackInterpreter(rec, rules), rec), rec


# ---------------------------------------------------------------- playing


def keys(utt):
    return [line.key for line in utt.lines]


def classify(prev_last: str, out) -> str:
    """END / STOP_CHECK / CALLBACK_ASK / ASK_SAME (same question family again) / ASK_NEXT."""
    if isinstance(out, EndOfCall):
        return "END"
    ks = keys(out)
    last = ks[-1]
    if last.startswith("stop_check."):
        return "STOP_CHECK"
    if last == "callback.when":
        return "CALLBACK_ASK"
    fam = lambda k: k.split(".")[0]  # noqa: E731
    same = {"right_party": {"right_party"}, "disclosure": {"disclosure"}, "second_check": {"second_check"}}
    if fam(last) == fam(prev_last) or fam(last) in same.get(fam(prev_last), set()):
        return "ASK_SAME"
    if prev_last == "read_back.confirm" and last.startswith("read_back"):
        return "ASK_SAME"
    return "ASK_NEXT"


class Call:
    def __init__(self, record: str, lang: str, interp: Timed, rec: Recorder | None, tag: str):
        self.interp, self.rec = interp, rec
        self.state, utt = start(RECORDS[record], Language(lang), lender_name=LENDER)
        self.log = [{"who": "BOT", "keys": keys(utt), "text": utt.text}]
        self.last = keys(utt)[-1]
        self.end: EndOfCall | None = None
        self.tag = tag

    def say(self, text: str):
        if self.rec:
            self.rec.ctx = {"case": self.tag, "turn": len(self.log)}
        prev = self.last
        self.state, out = step(self.state, text, interpreter=self.interp)
        self.log.append({"who": "CUST", "text": text})
        if isinstance(out, EndOfCall):
            self.end = out
            self.log.append({"who": "BOT", "keys": keys(out.utterance), "text": out.utterance.text,
                             "outcome": out.outcome.value})
        else:
            self.last = keys(out)[-1]
            self.log.append({"who": "BOT", "keys": keys(out), "text": out.text})
        return classify(prev, out)

    @property
    def outcome(self):
        return self.end.outcome.value if self.end else f"open@{self.state.position.at}"


def leaks_in(entries):
    found = {k: False for k in LEAKS}
    hits = []
    for e in entries:
        if e["who"] != "BOT":
            continue
        for k, rx in LEAKS.items():
            if rx.search(e["text"]):
                found[k] = True
                hits.append((k, e["keys"]))
    return found, hits


def run_prefix(call: Call, lang: str, point: str):
    for p in POINT_PREFIX[point]:
        call.say(PREFIX[lang][p])
        guard = 0
        while call.end is None and call.last.startswith("stop_check.") and guard < 2:
            call.say(PREFIX[lang]["yes"])
            guard += 1
        if call.end:
            return False
        # with the classifier down the recall answer is lost once (stop check, then the re-ask): say it again
        tries = 0
        while p == "recall" and call.end is None and call.last.startswith("open_recall") and tries < 2:
            call.say(PREFIX[lang][p])
            tries += 1
    return call.last == POINT_WANT[point]


def follow_reply(lang, last, category):
    if last == "callback.when":
        return "कल शाम को" if lang == "hi" else "kal shaam ko"
    if last.startswith("stop_check."):
        return "नहीं" if lang == "hi" else "nahi"
    return None


def play_case(case, arm, interp, rec):
    call = Call(case["record"], case["lang"], interp, rec, case["id"])
    first_line = call.log[0]["text"]
    if arm == "failturn":
        rec.inner.raising = False
    ok = run_prefix(call, case["lang"], case["point"])
    if arm == "failturn":
        rec.inner.raising = True
    row = {"id": case["id"], "group": case["group"], "category": case["category"], "point": case["point"],
           "lang": case["lang"], "record": case["record"], "arm": arm, "prefix_ok": ok, "first_line": first_line}
    if not ok:
        row.update(outcome=call.outcome, log=call.log, note="prefix did not reach the point")
        return row
    start_idx = len(call.log)
    pending = call.last
    g = case["group"]
    turns = case["turns"]
    classes = []
    if g == "third_party":
        for t in turns:
            if call.end:
                break
            classes.append(call.say(t))
        after = call.log[start_idx:]
        found, hits = leaks_in(after)
        row.update(classes=classes, leak=found, leak_hits=hits,
                   old_leak=any(OLD_LEAK.search(e["text"]) for e in after if e["who"] == "BOT"),
                   lines_after=[k for e in after if e["who"] == "BOT" for k in e["keys"]])
    elif g == "refusal":
        for t in turns:
            if call.end:
                break
            classes.append(call.say(t))
        extra = 0
        while call.end is None and extra < 2:
            r = follow_reply(case["lang"], call.last, case["category"])
            if r is None:
                break
            call.say(r)
            extra += 1
        row.update(classes=classes, immediate=classes[0] if classes else None, pending=pending,
                   last_class=classes[-1] if classes else None)
    elif g in ("genuine", "genuine_year", "nonrefusal"):
        c = call.say(turns[0])
        classes.append(c)
        row.update(classes=classes, immediate=c, pending=pending,
                   after_keys=call.log[-1]["keys"])
        if g == "genuine" and call.end is None and call.last == "right_party.reask":
            branches = {}
            for name, text in (("A_claim", {"hi": "हाँ हाँ, मैं ही हूँ", "hi-en": "haan haan main hi hoon"}),
                               ("B_plain", {"hi": "हाँ", "hi-en": "haan"})):
                saved = (call.state, call.log[:], call.last, call.end)
                cc = call.say(text[case["lang"]])
                branches[name] = {"text": text[case["lang"]], "class": cc, "outcome": call.outcome,
                                  "keys": call.log[-1]["keys"]}
                call.state, call.log, call.last, call.end = saved
            row["branches"] = branches
    row.update(outcome=call.outcome, log=call.log, degraded=list(call.state.degraded_turns))
    return row


def save_rows(name, rows):
    path = HERE / f"{name}.jsonl"
    if path.exists():
        path = HERE / f"{name}_{STAMP}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print("wrote", path.relative_to(ROOT))


def save_latency(arm, rec, interp):
    if rec is None:
        return
    path = HERE / f"p2_r2_latency_{arm}_{STAMP}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rec.rows))
    print("wrote", path.relative_to(ROOT), len(rec.rows), "classifier calls,",
          sum(1 for r in rec.rows if r.get("cache_hit")), "cache hits, usd",
          round(sum(r.get("usd") or 0 for r in rec.rows), 5))


def cmd_groups(arm):
    interp, rec = make(arm)
    cases = json.loads((HERE / "p2_r2_inputs.json").read_text())
    rows = []
    for i, case in enumerate(cases):
        rows.append(play_case(case, arm, interp, rec))
        if i % 25 == 0:
            print(i, case["id"], rows[-1]["outcome"], flush=True)
    time.sleep(3.5)  # let late classifier calls finish so their latencies are recorded
    save_rows(f"p2_r2_groups_{arm}", rows)
    save_latency(f"groups_{arm}", rec, interp)


# ---------------------------------------------------------------- whole calls


def persona_reply(p, last, counters, mode):
    m = p["then"] if mode == "then" else p["replies"]
    cand = [last, last.split(".")[0] + ".ask" if last.endswith(".reask") else None,
            "read_back" if last.startswith("read_back") else None,
            "stop_check" if last.startswith("stop_check") else None, "*"]
    for k in cand:
        if k and k in m:
            v = m[k]
            if isinstance(v, list):
                i = counters.get((mode, k), 0)
                counters[(mode, k)] = i + 1
                return v[min(i, len(v) - 1)]
            return v
    return None


PKG_FALLBACK = {
    "payment_frequency.ask": {"hi": "एक ही बार", "hi-en": "ek hi baar, one time"},
    "cover.say_again": {"hi": "पाँच लाख", "hi-en": "five lakh"},
    "premium.say_again": {"hi": "बावन हज़ार", "hi-en": "fifty two thousand"},
    "read_back.confirm": {"hi": "हाँ", "hi-en": "haan"},
    "read_back.cover_confirm": {"hi": "हाँ", "hi-en": "haan"},
    "stop_check.decline": {"hi": "हाँ", "hi-en": "haan"},
    "stop_check.disengaged": {"hi": "हाँ", "hi-en": "haan"},
    "right_party.reask": {"hi": "हाँ, मैं ही हूँ", "hi-en": "haan main hi hoon"},
}


def packaged():
    out = []
    for name in ("hero", "informed", "third-party"):
        call = json.loads((ROOT / f"tests/fixtures/server/calls/{name}/call.json").read_text())
        rec = json.loads((ROOT / f"samajh/server/records/{name}.json").read_text())
        replies = {}
        for t in call["turns"]:
            replies.setdefault(t["answers"], []).append(t["text"])
        out.append({"id": f"PKG-{name}", "lang": call["params"]["language"], "record_obj": rec["record"],
                    "lender": rec["lender_name"], "replies": replies, "packaged": True})
    return out


def play_persona(p, arm, interp, rec, max_turns=60):
    if "record_obj" in p:
        record, lender = LoanRecord.model_validate(p["record_obj"]), p["lender"]
    else:
        record, lender = RECORDS[p["record"]], LENDER
    state, utt = start(record, Language(p["lang"]), lender_name=lender)
    log = [{"who": "BOT", "keys": keys(utt), "text": utt.text}]
    last, counters, mode, outcome, n_cust = keys(utt)[-1], {}, "replies", None, 0
    t_start = len(interp.turns)
    while n_cust < max_turns:
        if p.get("switch_on") and last == p["switch_on"] and mode == "replies":
            mode = "then"
        if p.get("packaged"):
            lst = p["replies"].get(last) or p["replies"].get(last.replace(".reask", ".ask"))
            if not lst and last in PKG_FALLBACK:
                # the packaged script predates this question (P1 fixtures are stale); a neutral answer, noted
                lst = [PKG_FALLBACK[last][p["lang"]]]
                p.setdefault("filled", []).append(last)
            i = counters.get(last, 0)
            if not lst:
                outcome = f"persona_has_no_reply@{last}"
                break
            reply = lst[min(i, len(lst) - 1)]
            counters[last] = i + 1
        else:
            reply = persona_reply(p, last, counters, mode)
            if reply is None:
                outcome = f"persona_has_no_reply@{last}"
                break
        if rec:
            rec.ctx = {"case": p["id"], "turn": n_cust}
        state, out = step(state, reply, interpreter=interp)
        n_cust += 1
        log.append({"who": "CUST", "text": reply})
        if isinstance(out, EndOfCall):
            log.append({"who": "BOT", "keys": keys(out.utterance), "text": out.utterance.text})
            outcome = out.outcome.value
            break
        last = keys(out)[-1]
        log.append({"who": "BOT", "keys": keys(out), "text": out.text})
    turns = interp.turns[t_start:]
    from collections import Counter

    keyc = Counter(k for e in log if e["who"] == "BOT" for k in e["keys"])
    return {"id": p["id"], "arm": arm, "lang": p["lang"], "outcome": outcome or f"open@{last}", "customer_turns": n_cust,
            "classified_turns": sum(t["consulted"] for t in turns),
            "classifier_seconds": round(sum(t["seconds"] for t in turns if t["consulted"]), 3),
            "turn_seconds": [t["seconds"] for t in turns if t["consulted"]],
            "max_line_repeats": max(keyc.values()), "repeated": {k: v for k, v in keyc.items() if v > 2},
            "degraded": list(state.degraded_turns) if hasattr(state, "degraded_turns") else None,
            "filled_from_fallback": p.pop("filled", []), "log": log}


def cmd_calls(arm):
    interp, rec = make(arm)
    personas = packaged() + json.loads((HERE / "p2_r2_personas.json").read_text())
    rows = []
    for p in personas:
        r = play_persona(p, arm, interp, rec)
        rows.append(r)
        print(f"{r['id']:34s} {r['outcome']:28s} turns={r['customer_turns']:2d} classified={r['classified_turns']:2d} "
              f"clf_s={r['classifier_seconds']:6.2f} maxrep={r['max_line_repeats']}", flush=True)
    time.sleep(3.5)
    save_rows(f"p2_r2_calls_{arm}", rows)
    save_latency(f"calls_{arm}", rec, interp)


SLOW_IDS = ["tp-001", "tp-014", "tp-021", "tp-045", "tp-057", "rf-001", "rf-011", "rf-033", "rf-046",
            "gi-001", "gi-013", "gi-032", "nr-003", "nr-017", "nr-033"]


def cmd_slow():
    interp, rec = make("slow")
    cases = {c["id"]: c for c in json.loads((HERE / "p2_r2_inputs.json").read_text())}
    rows = []
    for cid in SLOW_IDS:
        n0 = len(interp.turns)
        row = play_case(cases[cid], "slow", interp, rec)
        t = interp.turns[n0:]
        row["max_interpret_seconds"] = max((x["seconds"] for x in t), default=0)
        row["interpret_seconds"] = [x["seconds"] for x in t]
        rows.append(row)
        print(cid, row["outcome"], row["max_interpret_seconds"], flush=True)
    save_rows("p2_r2_slow", rows)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "groups":
        cmd_groups(sys.argv[2])
    elif what == "calls":
        cmd_calls(sys.argv[2])
    elif what == "slow":
        cmd_slow()
    else:
        raise SystemExit(__doc__)
