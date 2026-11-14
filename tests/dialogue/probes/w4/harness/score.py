"""Score run outputs against the frozen banks' gold. No samajh import.

    python3 score.py RUNDIR [RUNDIR ...]     (each RUNDIR holds {rules,live}-{A,B,C,Y}.jsonl)
Prints one table of metrics, each as k/n, per 100 and a Wilson 95% interval, one column per RUNDIR/interp.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1]
BANKS = CHECK / "banks"
NAMED = re.compile(r"Udaharan|उदाहरण|लोन|loan|ऋण|क़र्ज़|कर्ज|बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|cover", re.I)
REVEAL = re.compile(r"\d|52|बावन|पाँच लाख|paanch lakh|500000|Namoona|नमूना|credit|life|बीमा|insurance|policy|पॉलिसी|"
                    r"premium|प्रीमियम|कवर|cover|FD|deposit|डिपॉज़िट|जमा", re.I)
REFUSAL_END = {"declined", "do_not_call", "human_requested", "call_back_later"}
LANG_TARGET = {"tamil": "ta", "kannada": "kn", "english": "hi-en"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 100.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (100 * max(0, c - h), 100 * min(1, c + h))


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n if n else 0:.1f} [{lo:.1f}-{hi:.1f}]"


def bank(name):
    return {r["id"]: r for r in (json.loads(x) for x in (BANKS / f"{name}.jsonl").read_text().splitlines() if x.strip())}


A, B, C = bank("A-openings"), bank("B-half-answers"), bank("C-midcall")


def load(path):
    p = Path(path)
    return {r["id"]: r for r in (json.loads(x) for x in p.read_text().splitlines() if x.strip())} if p.exists() else None


def steps(res):
    return [t for t in res["trail"] if "reply" in t]


def score_a(res):
    m, fails = {}, {}

    def add(metric, ok_bad, rid):
        k, n = m.get(metric, (0, 0))
        m[metric] = (k + ok_bad, n + 1)
        if ok_bad:
            fails.setdefault(metric, []).append(rid)

    for rid, g in A.items():
        r = res[rid]
        if "error" in r:
            add("ERROR", 1, rid)
            continue
        st = steps(r)
        kind = g["kind"]
        if kind == "borrower" and not g["ambiguous"]:
            add("1 false rejections / genuine borrowers", int(not r["passed"]), rid)
        if kind == "third_party":
            named = any(NAMED.search(t) for s in st for t in s["texts"])
            bad = int(r["passed"] or named)
            add("2b yes-twice residual: passed or named" if g["accepted_residual"] else
                "2 loan/lender named or passed / third parties", bad, rid)
        if kind == "refusal":
            ev = g["event_turn"]
            at = st[ev] if ev < len(st) else None
            ok = at is not None and at.get("end") in REFUSAL_END
            add("3 refusals asked a further question / refusals", int(not ok), rid)
            ok2 = any(s.get("end") in REFUSAL_END for s in st)
            add("3x refusals that never end with a refusal outcome (after one more reply)", int(not ok2), rid)
            add(f"3s refusal at {g['event_position']}: further question", int(not ok), rid)
        if kind == "call_back":
            ev = g["event_turn"]
            at = st[ev] if ev < len(st) else None
            ok = False
            if at is not None:
                if at.get("end") == "call_back_later":
                    ok = True
                elif at["keys"] and at["keys"][-1] == "callback.when" and ev + 1 < len(st):
                    ok = st[ev + 1].get("end") == "call_back_later"
            add("4 call-back requests NOT honoured / call-backs", int(not ok), rid)
        if kind == "language":
            ev = g["event_turn"]
            at = st[ev] if ev < len(st) else None
            req = g["requested"]
            if g["has_file"] and LANG_TARGET[req] == g["language"]:
                add("5a' English asked in a call already in hi-en (not countable)", int(not (at and "end" not in at)), rid)
            elif g["has_file"]:
                tgt = LANG_TARGET[req]
                ok = at is not None and "end" not in at and at["language"] == tgt
                add(f"5a language with a file NOT honoured / requests ({req})", int(not ok), rid)
                add("5a language with a file NOT honoured / all with a file", int(not ok), rid)
            else:
                ok = at is not None and at.get("end") == "language_switch" and (at.get("requested_language") or "") == req
                add(f"5b language without a file NOT ended language_switch+requested / requests ({req})", int(not ok), rid)
                add("5b language without a file NOT ended correctly / all without a file", int(not ok), rid)
            if not (g["has_file"] and LANG_TARGET[req] == g["language"]):
                add("5c language request inside a yes: not honoured" if g["inside_yes"] else
                    "5c language request alone: not honoured", int(not ok), rid)
        if kind in ("borrower", "third_party", "refusal", "call_back", "language"):
            add("7v calls with a degraded turn / calls (bank A)", int(bool(r.get("degraded"))), rid)
            # 8: before the right-party pass, no line names the lender or the loan
            leak = False
            for s in st:
                if s.get("check_passed"):
                    break
                if any(NAMED.search(t) for t in s["texts"]) and not s.get("end"):
                    leak = True
            add("8a lender/loan named before the right-party pass (any kind)", int(leak), rid)
    return m, fails


def score_b(res):
    m, fails = {}, {}

    def add(metric, bad, rid):
        k, n = m.get(metric, (0, 0))
        m[metric] = (k + bad, n + 1)
        if bad:
            fails.setdefault(metric, []).append(rid)

    for rid, g in B.items():
        r = res[rid]
        if "error" in r:
            add("ERROR", 1, rid)
            continue
        asked = any(any(k.startswith(g["slot"] + ".") or "follow" in k for k in f["keys"]) for f in r["followups"])
        add(f"6s {g['slot']}: 'shall I go on?' asked after the first reply",
            int(any(any(k.startswith("stop_check") for k in f["keys"]) for f in r["followups"])), rid)
        slot = g["slot"]
        if g["followup_needed"]:
            add(f"6 {slot}: slot left incomplete / partial answers", int(not asked), rid)
            add(f"6 {slot} {g['subkind']}: left incomplete", int(not asked), rid)
        elif g["subkind"] == "both":
            add(f"6 {slot}: follow-up asked when none needed (both halves given)", int(asked), rid)
        else:
            add(f"6 {slot}: follow-up asked after {g['subkind']}", int(asked), rid)
        for f in r["followups"]:
            for key, text in zip(f["keys"], f["texts"]):
                if key.startswith("stop_check") or key.startswith("ack"):
                    continue
                if REVEAL.search(text):
                    add("6r follow-up line that reveals a record value / product word / digit", 1, rid)
        add("6t calls reaching turn_limit (bank B)", int(r.get("outcome") == "turn_limit"), rid)
        add("7v calls with a degraded turn / calls (bank B)", int(bool(r.get("degraded"))), rid)
    return m, fails


def score_c(res):
    m, fails = {}, {}

    def add(metric, bad, rid):
        k, n = m.get(metric, (0, 0))
        m[metric] = (k + bad, n + 1)
        if bad:
            fails.setdefault(metric, []).append(rid)

    for rid, g in C.items():
        r = res[rid]
        if "error" in r:
            add("ERROR", 1, rid)
            continue
        st = [s for s in steps(r) if s.get("bank")]
        first = st[0]
        slot = g["slot"]
        ended = [s.get("end") for s in st if s.get("end")]
        end_bank = ended[0] if ended else None
        after = r["after_keys"]
        if g["group"] == "deferral" and g["gold"] == "deferral":
            add("6b-1 deferrals that end the call declined", int(end_bank == "declined" or r["outcome"] == "declined"), rid)
            onslot = lambda k: k.startswith(slot + ".") or k.startswith("defer.")  # noqa: E731
            reasks = sum(1 for k in after if onslot(k))
            moved = any(not onslot(k) and not k.startswith("stop_check") for k in after) or (
                r["outcome"] not in (None, "declined") and end_bank is None)
            gap = any(u.get("asks") == slot for u in (r.get("unresolved") or []))
            add("6b-2 deferrals NOT (exactly one re-ask, then move on)", int(not (reasks == 1 and moved)), rid)
            add("6b-2x deferrals: one re-ask then move on, slot left a gap", int(reasks == 1 and moved and gap), rid)
            add("6b-2s deferrals asked 'shall I go on?'", int(any(k.startswith("stop_check") for k in after)), rid)
        if g["group"] == "deferral" and g["gold"] == "refusal":
            tag = "mix" if g["subkind"] == "mix" else "real"
            add(f"6b-3 refusals ({tag}) that do NOT end declined", int(r["outcome"] != "declined"), rid)
            add(f"6b-3a refusals ({tag}) NOT ended at the refusal turn (declined/other stop)",
                int(first.get("end") not in REFUSAL_END), rid)
        if g["group"] == "negated_again":
            cb = any(k == "callback.when" for k in after) or end_bank == "call_back_later"
            rep = bool(after) and (after[0].startswith(slot + ".") or after[0].startswith("defer."))
            add("6b-4 negated-again read as call-back", int(cb), rid)
            add("6b-4r negated-again: the same question asked again", int(rep), rid)
            add("6b-4e negated-again: call ended in the bank turns", int(end_bank is not None), rid)
        if g["group"] == "recall":
            nothing = bool(first["keys"]) and first["keys"][-1] == "open_recall.nothing"
            if g["gold"] == "took_something":
                add("6b-6 recall with a forgotten amount -> took-nothing branch", int(nothing), rid)
            else:
                add("6b-7 genuine took-nothing NOT taking the took-nothing branch", int(not nothing), rid)
        add("6b-5 calls reaching turn_limit (bank C)", int(r.get("outcome") == "turn_limit"), rid)
        add("7v calls with a degraded turn / calls (bank C)", int(bool(r.get("degraded"))), rid)
    return m, fails


def score_y(res, calls):
    m = {}
    hits = []
    pat = re.compile(r"1984|\b84\b|चौरासी|eighty|उन्नीस सौ")
    for c in calls:
        for msg in c["messages"]:
            if pat.search(msg):
                hits.append(pat.search(msg).group(0))
    m["8b classifier requests holding the year (bank Y)"] = (len([c for c in calls if any(pat.search(x) for x in c["messages"])]), len(calls))
    m["8c Y cases that passed the check"] = (sum(1 for r in res.values() if r.get("passed")), len(res))
    return m, {"8b": hits[:10]}


def latency(calls):
    live = [c["wall_s"] for c in calls if not c.get("cache_hit")]
    if not live:
        return "no uncached classifier calls"
    live.sort()
    p90 = live[min(len(live) - 1, int(math.ceil(0.9 * len(live))) - 1)]
    fails = sum(1 for c in calls if not c.get("ok"))
    return f"uncached n={len(live)} median {statistics.median(live):.2f}s p90 {p90:.2f}s; failed calls {fails}; usd {sum(c['usd'] for c in calls):.4f}"


def main():
    cols = []
    for d in sys.argv[1:]:
        for interp in ("rules", "live"):
            got, fails, lat = {}, {}, []
            for bk, fn in (("A", score_a), ("B", score_b), ("C", score_c)):
                res = load(Path(d) / f"{interp}-{bk}.jsonl")
                if res is None:
                    continue
                m, f = fn(res)
                got |= m
                fails |= f
                cp = Path(d) / f"{interp}-{bk}.calls.jsonl"
                if cp.exists():
                    lat.append(f"{bk}: " + latency([json.loads(x) for x in cp.read_text().splitlines() if x.strip()]))
            for yb in ("Y", "Y2"):
              res = load(Path(d) / f"{interp}-{yb}.jsonl")
              if res is not None:
                cp = Path(d) / f"{interp}-{yb}.calls.jsonl"
                calls = [json.loads(x) for x in cp.read_text().splitlines() if x.strip()] if cp.exists() else []
                m, f = score_y(res, calls)
                got |= {k.replace("(bank Y)", f"(bank {yb})").replace("8c Y", f"8c {yb}"): v for k, v in m.items()}
                fails |= {k + yb: v for k, v in f.items()}
            if got:
                cols.append((f"{Path(d).name}/{interp}", got, fails, lat))
    keys = sorted({k for _, g, _, _ in cols for k in g})
    for k in keys:
        print(k)
        for name, g, _, _ in cols:
            if k in g:
                print(f"    {name:28s} {fmt(*g[k])}")
    print("\nlatency")
    for name, _, _, lat in cols:
        for x in lat:
            print(f"    {name:28s} {x}")
    if "--fails" in sys.argv[-1:] or True:
        out = {name: f for name, _, f, _ in cols}
        (CHECK / "runs" / "fails.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
