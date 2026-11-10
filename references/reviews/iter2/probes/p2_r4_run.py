"""P2 round 4 narrow verifier harness. uv run python references/reviews/iter2/probes/p2_r4_run.py live|failing
Reuses p2_r3_run (make, Stats, P, REC). Writes p2_r4_out_<arm>.jsonl."""
from __future__ import annotations
import json, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2_r3_run as H
from samajh.dialogue import EndOfCall, start, step
from samajh.types import Language

HERE = Path(__file__).resolve().parent
INP = json.loads((HERE / "p2_r4_inputs.json").read_text())
# "Named": lender name, loan and product words, and these line keys.
TEXT_RX = {"lender": re.compile(r"Udaharan|उदाहरण", re.I),
           "loan": re.compile(r"लोन|\bloan\b|ऋण|क़र्ज़|कर्ज", re.I),
           "product": re.compile(r"बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|\bcover\b", re.I)}
KEY_RX = re.compile(r"^(context\.loan|teach_back\..*|verify\.after_loan|verify\.before_loan)$")
PRE = {"opening": [], "reask": ["weak"], "year": ["yes"], "go_ahead": ["yes", "year"],
       "recall": ["yes", "year", "go"], "kind": ["yes", "year", "go", "recall"]}


def named(bot_entries):
    out = set()
    for keys, text in bot_entries:
        out |= {n for n, rx in TEXT_RX.items() if rx.search(text)}
        out |= {f"key:{k}" for k in keys if KEY_RX.match(k)}
    return sorted(out)


class Call:
    def __init__(self, lang, interp):
        self.interp = interp; interp.local.flags = []
        self.st, said = start(H.REC, Language(lang), lender_name=H.LENDER)
        self.bot = [([l.key for l in said.lines], said.text)]; self.end = None; self.ec = None; self.deg = []

    def say(self, t):
        n = len(self.interp.local.flags)
        self.st, out = step(self.st, t, interpreter=self.interp)
        self.deg.append(any(self.interp.local.flags[n:]))
        if isinstance(out, EndOfCall):
            self.end = out.outcome.value; self.ec = out
            self.bot.append(([l.key for l in out.utterance.lines], out.utterance.text))
        else:
            self.bot.append(([l.key for l in out.lines], out.text))
        return self.end

    @property
    def pos(self):
        p = self.st.position; n = type(p).__name__
        return n + (f"(wish={p.wish})" if n == "AtStopCheck" else "")


def at_who(c): return c.end is None and c.pos == "AtStopCheck(wish=who)"


def prefix(c, lang, stage):
    p = H.P[lang]
    for k in PRE[stage]:
        if c.say(p[k]): return False
    return True


def g1(case, interp):
    route_used = None
    for r in INP["who_routes"]:
        c = Call(case["lang"], interp)
        if not prefix(c, case["lang"], "recall"): continue
        c.say(r["text"])
        if at_who(c): route_used = r["text"]; break
    row = dict(case, route=route_used)
    if not route_used: row.update(reached=False, last=c.bot[-1], end=c.end); return row
    n = len(c.bot); c.say(case["text"])
    row.update(reached=True, end=c.end, pos_after=None if c.end else c.pos, keys_after=c.bot[-1][0],
               text_after=c.bot[-1][1], named_after=named(c.bot[n:]), degraded=c.deg[-1],
               speaker_confirmed=getattr(c.ec, "speaker_confirmed", None))
    return row


def g2(case, interp):
    c = Call(case["lang"], interp)
    if not prefix(c, case["lang"], case["stage"]): return dict(case, reached=False, end=c.end)
    at = c.pos; n = len(c.bot); c.say(case["text"])
    row = dict(case, reached=True, at=at, end_now=c.end, next_keys=c.bot[-1][0], next_text=c.bot[-1][1],
               next_pos=None if c.end else c.pos, degraded=c.deg[-1])
    # named before any who-check passed: walk the follow-ups, cut at the first resume from a who-check
    before, after, passed_at = [c.bot[-1]], [], None
    follows = list(INP["g2_follow"]); i = 0
    while c.end is None and follows:
        was_who = at_who(c); t = follows.pop(0); i += 1; c.say(t)
        resumed = was_who and c.end is None and not at_who(c)
        if passed_at is None and resumed: passed_at = i
        (before if passed_at is None else after).append(c.bot[-1])
    row.update(named_before_pass=named(before), who_passed_on_follow=passed_at, named_after_follow=named(after),
               final_end=c.end, final_pos=None if c.end else c.pos,
               trace=[(k, t[:80]) for k, t in c.bot[n:]])
    return row


def g3(case, interp):
    c = Call(case["lang"], interp)
    if not prefix(c, case["lang"], "year"): return dict(case, reached=False, end=c.end)
    at = c.pos; n = len(c.bot); c.say(case["text"])
    row = dict(case, reached=at == "AtBirthYear", end=c.end, pos_after=None if c.end else c.pos,
               keys_after=c.bot[-1][0], text_after=c.bot[-1][1], degraded=c.deg[-1],
               speaker_confirmed=c.st.speaker_confirmed if c.end is None else c.ec.speaker_confirmed,
               reasked=c.end is None and c.pos == "AtBirthYear", named_after=named(c.bot[n:]))
    row["result"] = ("ended:" + c.end) if c.end else ("passed" if row["speaker_confirmed"] else
                                                      ("reasked" if row["reasked"] else "other:" + c.pos))
    return row


def g4(case, interp):
    c = Call(case["lang"], interp)
    if not prefix(c, case["lang"], case["stage"]): return dict(case, reached=False, end=c.end)
    at = c.pos; n = len(c.bot); c.say(case["text"])
    return dict(case, reached=at == "AtIdentity", end=c.end, pos_after=None if c.end else c.pos,
                speaker_confirmed=getattr(c.ec, "speaker_confirmed", None) if c.end else c.st.speaker_confirmed,
                keys_after=c.bot[-1][0], text_after=c.bot[-1][1], named_after=named(c.bot[n:]), degraded=c.deg[-1])


def main(arm):
    stats = H.Stats(); interp = H.make(arm, stats)
    jobs = [(g, c) for g, fn in (("g1", g1), ("g2", g2), ("g3", g3), ("g4", g4)) for c in INP[g]]
    fns = {"g1": g1, "g2": g2, "g3": g3, "g4": g4}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=3 if arm == "live" else 1) as ex:
        rows = list(ex.map(lambda j: dict(fns[j[0]](j[1], interp), group=j[0]), jobs))
    (HERE / f"p2_r4_out_{arm}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                               encoding="utf-8")
    print(json.dumps(dict(arm=arm, n=len(rows), seconds=round(time.time() - t0, 1), llm_calls=stats.calls,
                          cache_hits=stats.hits, errors=stats.errors, over_2_5s=stats.slow, usd=round(stats.usd, 5))))


if __name__ == "__main__":
    main(sys.argv[1])
