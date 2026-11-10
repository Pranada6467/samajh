"""P2 round 3 verifier harness. uv run python references/reviews/iter2/probes/p2_r3_run.py rules|failing|live
Writes p2_r3_out_<arm>.jsonl (one row per case)."""
from __future__ import annotations
import json, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language, LoanRecord

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REC = LoanRecord.model_validate_json((ROOT / "tests/dialogue/fixtures/record_gold_loan.json").read_text())
LENDER = "Udaharan Bank"
LEAK = {"lender": re.compile(r"Udaharan", re.I), "loan": re.compile(r"लोन|loan|ऋण|क़र्ज़|कर्ज", re.I),
        "product": re.compile(r"बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|\bcover\b|एफ़डी|\bFD\b|deposit", re.I),
        "value": re.compile(r"\d|बावन|baavan|पाँच हज़ार|paanch|Namoona|नमूना|चौरासी|chaurasi|तीस दिन", re.I)}
P = {"hi": dict(yes="हाँ जी", year="1984", go="हाँ", recall="हाँ, एक बीमा लिया था", kind="बीमा है", prem="बावन सौ",
                weak="हम्म", busy="बाद में बात करते हैं", strong="हाँ जी, मैं ही रमेश बोल रहा हूँ"),
     "hi-en": dict(yes="haan ji", year="1984", go="haan", recall="haan, ek insurance liya tha", kind="insurance hai",
                   prem="5200", weak="hmm", busy="baad mein baat karte hain", strong="haan ji, main hi ramesh bol raha hoon")}
PREFIX = {"opening": [], "reask": ["weak"], "year": ["yes"], "go_ahead": ["yes", "year"], "recall": ["yes", "year", "go"],
          "kind": ["yes", "year", "go", "recall"], "premium": ["yes", "year", "go", "recall", "kind"],
          "read_back": ["yes", "year", "go", "recall", "kind", "prem"], "callback_q": ["yes", "year", "busy"]}
WANT = {"opening": "AtIdentity", "reask": "AtIdentity", "year": "AtBirthYear", "go_ahead": "AtGoAhead", "recall": "AtRecall",
        "kind": "AtTeachBack", "premium": "AtTeachBack", "read_back": "AtReadBack", "callback_q": "AtCallbackTime"}


class Stats:
    def __init__(self): self.lock = threading.Lock(); self.calls = 0; self.hits = 0; self.usd = 0.0; self.errors = 0; self.slow = 0


class Counting:
    def __init__(self, inner, stats): self.inner, self.s = inner, stats
    def complete(self, schema, messages, **kw):
        t0 = time.monotonic()
        try:
            r = self.inner.complete(schema, messages, **kw)
        except Exception:
            with self.s.lock: self.s.calls += 1; self.s.errors += 1
            raise
        with self.s.lock:
            self.s.calls += 1; self.s.hits += bool(getattr(r, "cache_hit", False)); self.s.usd += getattr(r, "usd", 0.0) or 0.0
            self.s.slow += (time.monotonic() - t0) > 2.5
        return r


class Raising:
    def complete(self, *a, **k): raise RuntimeError("verifier: classifier down")


class Watch:
    """Records degraded flags per interpret() call (per thread)."""
    def __init__(self, inner): self.inner, self.local = inner, threading.local()
    def interpret(self, text, **kw):
        out = self.inner.interpret(text, **kw)
        self.local.flags.append(bool(getattr(out, "degraded", False)))
        return out


def make(arm, stats):
    rules = RuleInterpreter()
    if arm == "rules": return Watch(rules)
    if arm == "failing": return Watch(LlmFallbackInterpreter(Raising(), rules))
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.llm import LlmClient
    client = LlmClient.from_env(timeout=3.0, retry=RetryPolicy(max_attempts=1), usd_cap=2.0)
    return Watch(LlmFallbackInterpreter(Counting(client, stats), rules))


def keys(u): return [l.key for l in u.lines]


def run_case(c, interp):
    interp.local.flags = []
    p = P[c["lang"]]
    st, said = start(REC, Language(c["lang"]), lender_name=LENDER)
    log = [("BOT", keys(said), said.text)]
    pre = [p[k] for k in PREFIX[c["stage"]]]
    if c.get("first"): pre = [c["first"]] + pre[1:]
    row = dict(id=c["id"], group=c["group"], stage=c["stage"], kind=c["kind"], text=c["text"], second=c.get("second"))
    def say(t, second=None):
        nonlocal st
        st, out = step(st, t, second_reading=second, interpreter=interp)
        log.append(("YOU", [], t))
        if isinstance(out, EndOfCall):
            log.append(("BOT", keys(out.utterance), out.utterance.text)); return out.outcome.value
        log.append(("BOT", keys(out), out.text)); return None
    for t in pre:
        o = say(t)
        if o: row.update(reached=False, prefix_end=o, log=log); return row
    row["reached"] = type(st.position).__name__ == WANT[c["stage"]]
    row["at"] = type(st.position).__name__
    n_before = len(log); flags_before = len(interp.local.flags)
    end = say(c["text"], c.get("second"))
    row["test_degraded"] = any(interp.local.flags[flags_before:])
    row["after_pos"] = None if end else type(st.position).__name__
    row["after_keys"] = log[-1][1]
    row["after_text"] = log[-1][2]
    rp_reasks = sum("right_party.reask" in k for w, k, _ in log if w == "BOT")
    follows = list(c.get("follow", []))
    turns = 0
    while not end and turns < 4:
        pos = type(st.position).__name__
        if c["group"] == "g1":
            if pos == "AtIdentity": t = p["strong"]
            elif pos == "AtBirthYear": t = follows.pop(0) if follows else p["year"]
            else: break
        else:
            if not follows: break
            t = follows.pop(0)
        end = say(t); turns += 1
    row["end"] = end
    row["final_pos"] = None if end else type(st.position).__name__
    later = [x for x in log[n_before:] if x[0] == "BOT"]
    row["leaks"] = sorted({n for _, _, txt in later for n, rx in LEAK.items() if rx.search(txt)})
    row["leak_first"] = sorted({n for n, rx in LEAK.items() if later and rx.search(later[0][2])})
    row["rp_reasks"] = sum("right_party.reask" in k for w, k, _ in log if w == "BOT")
    row["year_reasks"] = sum(any(x.startswith("second_check.") and x != "second_check.ask" for x in k) for w, k, _ in log if w == "BOT")
    row["passed_identity"] = any("disclosure.go_ahead" in k for w, k, _ in log if w == "BOT")
    row["degraded_any"] = any(interp.local.flags)
    row["log"] = log
    return row


def main(arm):
    cases = json.loads((HERE / "p2_r3_inputs.json").read_text())
    stats = Stats(); interp = make(arm, stats)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=3 if arm == "live" else 1) as ex:
        rows = list(ex.map(lambda c: run_case(c, interp), cases))
    (HERE / f"p2_r3_out_{arm}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(json.dumps(dict(arm=arm, n=len(rows), seconds=round(time.time() - t0, 1), llm_calls=stats.calls, cache_hits=stats.hits,
                          errors=stats.errors, over_2_5s=stats.slow, usd=round(stats.usd, 5))))


if __name__ == "__main__":
    main(sys.argv[1])
