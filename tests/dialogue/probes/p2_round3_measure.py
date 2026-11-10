"""Measure P2 round 3 on the independent probe set (p2_round3_openings.py, or another with --data).

    uv run python tests/dialogue/probes/p2_round3_measure.py openings rules|llm|down [--data MODULE] [--json OUT]
    uv run python tests/dialogue/probes/p2_round3_measure.py refusals rules|llm|down [--json OUT]
    uv run python tests/dialogue/probes/p2_round3_measure.py calls rules|llm|down [--latency-file F] [--json OUT]
    uv run python tests/dialogue/probes/p2_round3_measure.py recall rules|llm|down [--json OUT]
    uv run python tests/dialogue/probes/p2_round3_measure.py two_readings rules|llm|down [--json OUT]
    uv run python tests/dialogue/probes/p2_round3_measure.py go_ahead|callback|takeover|year|address|unconfirmed rules|llm|down
    uv run python tests/dialogue/probes/p2_round3_measure.py year2|takeover2|callback2|go_ahead2|recall2 rules|llm|down

--data MODULE names the probe data module in this directory (default p2_round3_openings); a module with
only GENUINE and THIRD_PARTY (p2_round3_openings_fresh2) serves the openings command only.
To measure another copy of the code, put it first on PYTHONPATH; the header prints which samajh ran.
rules: RuleInterpreter alone. llm: LlmFallbackInterpreter over the real client (usd cap, 10 s
timeout, one attempt). down: LlmFallbackInterpreter over a client that always raises.
Uses only the public API (start, step, EndOfCall, Line.key, expecting) and `effect_of`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import re
import statistics
import sys
import threading
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import p2_round3_openings as data

import samajh
from samajh.dialogue import EndOfCall, RuleInterpreter, expecting, start, step
from samajh.types import Language, LoanRecord

RECORD_PATH = HERE.parent / "fixtures" / "record_gold_loan.json"
RECORD = LoanRecord.model_validate_json(RECORD_PATH.read_text(encoding="utf-8"))
LENDER = "Udaharan Bank"
LENDER_RE = re.compile(r"Udaharan", re.IGNORECASE)
LOAN_RE = re.compile(r"लोन|loan|ऋण|कर्ज़|कर्ज", re.IGNORECASE)
PRODUCT_RE = re.compile(r"बीमा|इंश्योरेंस|insurance|पॉलिसी|policy|एफडी|एफ़डी|\bFD\b|premium|प्रीमियम", re.IGNORECASE)
MAX_TURNS = 8
WAIT_CAP_S = 2.5
PRODUCT_STEMS = {
    "kind", "premium", "payment_source", "payment_frequency", "required_for_loan", "provider_choice",
    "cover", "term", "cancel_window", "features", "teach_back", "read_back",
}  # fmt: skip

# --- interpreters and the timed client ----------------------------------------------------------


class Down:
    def complete(self, *args, **kwargs):
        from samajh.clients.errors import TransportError

        raise TransportError("down")


class Timed:
    """Wraps an LlmClient: records every `complete` (turn tag, key, seconds, cache hit)."""

    def __init__(self, llm):
        self.llm = llm
        self.entries: list[dict] = []
        self.turn: object = None
        self._lock = threading.Lock()

    def _key(self, args, kwargs) -> str:
        messages = kwargs.get("messages", args[1] if len(args) > 1 else None)
        model = kwargs.get("model") or getattr(self.llm, "_model", None)
        dumped = [m.model_dump() if hasattr(m, "model_dump") else m for m in (messages or [])]
        blob = json.dumps({"model": model, "messages": dumped}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def complete(self, *args, **kwargs):
        entry = {"turn": self.turn, "key": self._key(args, kwargs), "seconds": None, "cache_hit": None,
                 "error": None}  # fmt: skip
        with self._lock:
            self.entries.append(entry)
        began = time.monotonic()
        try:
            reply = self.llm.complete(*args, **kwargs)
        except Exception as exc:
            entry["seconds"], entry["cache_hit"], entry["error"] = time.monotonic() - began, False, repr(exc)
            raise
        entry["seconds"] = time.monotonic() - began
        entry["cache_hit"] = bool(getattr(reply, "cache_hit", False))
        return reply

    def settle(self, deadline_s: float = 12.0) -> None:
        """Wait for requests still running in the classifier's threads."""
        end = time.monotonic() + deadline_s
        while time.monotonic() < end and any(e["seconds"] is None for e in self.entries):
            time.sleep(0.05)


def build(arm: str, usd_cap: float):
    if arm == "rules":
        return RuleInterpreter(), None
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    if arm == "down":
        return LlmFallbackInterpreter(Down()), None
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.llm import LlmClient

    timed = Timed(LlmClient.from_env(usd_cap=usd_cap, timeout=10.0, retry=RetryPolicy(max_attempts=1)))
    return LlmFallbackInterpreter(timed), timed


# --- helpers ------------------------------------------------------------------------------------


def lines_of(said):
    return said.utterance.lines if isinstance(said, EndOfCall) else said.lines


def position_kind(state) -> str | None:
    try:
        return expecting(state.position).value
    except Exception:  # noqa: BLE001 - a probe records any failure and goes on
        return None


OPENING_FIELD = {
    "right_party.ask": "first",
    "right_party.reask": "reask",
    "disclosure.go_ahead": "go_ahead",
    "disclosure.reask": "go_ahead",
    "second_check.ask": "year",
    "second_check.reask": "year",
}
EXPECTING_FIELD = {"identity": "reask", "go_ahead": "go_ahead", "birth_year": "year"}


def opening_field(key: str, state) -> tuple[str, bool]:
    """Which persona reply answers the line `key`; bool = mapped from the key (not by fallback)."""
    if key in OPENING_FIELD:
        return OPENING_FIELD[key], True
    return EXPECTING_FIELD.get(position_kind(state) or "", "default"), False


def fail_record(case_id: str, exc: BaseException) -> dict:
    return {"id": case_id, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}


# --- openings -----------------------------------------------------------------------------------


def run_genuine(case: dict, interpreter) -> dict:
    lang = Language(case["lang"])
    state, said = start(RECORD, lang, lender_name=LENDER)
    keys = [line.key for line in said.lines]
    lender_before_year = any(LENDER_RE.search(line.text) for line in said.lines)
    reached_year = False
    replies, unmapped = [], []
    outcome = None
    for _ in range(MAX_TURNS):
        last = said.lines[-1].key
        if "context.loan" in keys:
            break
        field, mapped = opening_field(last, state)
        if not mapped:
            unmapped.append(last)
        reply = case.get(field) or ("हाँ जी" if case["lang"] == "hi" else "haan ji")
        replies.append([last, reply])
        state, said = step(state, reply, interpreter=interpreter)
        for line in lines_of(said):
            if line.key == "second_check.ask":
                reached_year = True
            if not reached_year and LENDER_RE.search(line.text):
                lender_before_year = True
            keys.append(line.key)
        if isinstance(said, EndOfCall):
            outcome = said.outcome.value
            break
    reasks = keys.count("right_party.reask")
    return {
        "id": case["id"], "lang": case["lang"], "ambiguous_first": case["ambiguous_first"],
        "reached_year": reached_year, "reasks": reasks, "outcome": outcome,
        "passed_checks": "context.loan" in keys, "lender_before_year": lender_before_year,
        "pass": reached_year and reasks <= 1, "replies": replies, "keys": keys, "unmapped": unmapped,
    }  # fmt: skip


def run_third_party(case: dict, interpreter) -> dict:
    lang = Language(case["lang"])
    state, said = start(RECORD, lang, lender_name=LENDER)
    keys, texts = [l.key for l in said.lines], [l.text for l in said.lines]
    replies, outcome = [], None
    for _ in range(MAX_TURNS):
        last = said.lines[-1].key
        field, _ = opening_field(last, state)
        reply = case["replies"].get(field) or case["replies"]["default"]
        replies.append([last, reply])
        state, said = step(state, reply, interpreter=interpreter)
        keys += [l.key for l in lines_of(said)]
        texts += [l.text for l in lines_of(said)]
        if isinstance(said, EndOfCall):
            outcome = said.outcome.value
            break
    loan = any(LOAN_RE.search(t) for t in texts)
    product = any(PRODUCT_RE.search(t) for t in texts)
    leak = loan or product
    return {
        "id": case["id"], "lang": case["lang"], "category": case["category"],
        "lender_named": any(LENDER_RE.search(t) for t in texts), "loan_named": loan, "product_named": product,
        "year_asked": "second_check.ask" in keys, "outcome": outcome or "still_open_after_8",
        "fail": leak if case["category"] != "false_claim_right_year" else False,
        "replies": replies, "keys": keys,
    }  # fmt: skip


def openings(interpreter, args) -> list[dict]:
    results = []
    genuine = data.GENUINE[: args.limit] if args.limit else data.GENUINE
    third = data.THIRD_PARTY[: args.limit] if args.limit else data.THIRD_PARTY
    for case in genuine:
        try:
            results.append({"set": "genuine", **run_genuine(case, interpreter)})
        except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
            results.append({"set": "genuine", "lang": case["lang"], "pass": False, **fail_record(case["id"], exc)})
    for case in third:
        try:
            results.append({"set": "third_party", **run_third_party(case, interpreter)})
        except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
            results.append({"set": "third_party", "lang": case["lang"], "category": case["category"],
                            "fail": True, **fail_record(case["id"], exc)})  # fmt: skip

    g = [r for r in results if r["set"] == "genuine"]
    print("\n== A. genuine openings: PASS = reached the year question with at most one re-ask ==")
    for scope in ("hi", "hi-en", "all"):
        rs = [r for r in g if scope == "all" or r["lang"] == scope]
        if not rs:
            continue
        ok = sum(r["pass"] for r in rs)
        amb = [r for r in rs if r.get("ambiguous_first")]
        clear = [r for r in rs if not r.get("ambiguous_first")]
        print(f"  {scope:6s} pass {ok}/{len(rs)} | clear-first {sum(r['pass'] for r in clear)}/{len(clear)}, "
              f"ambiguous-first {sum(r['pass'] for r in amb)}/{len(amb)} | "
              f"reached year {sum(bool(r.get('reached_year')) for r in rs)}/{len(rs)}, "
              f"passed both checks {sum(bool(r.get('passed_checks')) for r in rs)}/{len(rs)}, "
              f"re-asked >=1: {sum(r.get('reasks', 0) >= 1 for r in rs)}/{len(rs)} "
              f"(clear-first re-asked {sum(r.get('reasks', 0) >= 1 for r in clear)}/{len(clear)}), "
              f"lender said before year {sum(bool(r.get('lender_before_year')) for r in rs)}/{len(rs)}")
    outcomes = Counter(r.get("outcome") or ("loan_reached" if r.get("passed_checks") else "open") for r in g)
    print(f"  outcomes: {dict(outcomes)}")
    unm = Counter(k for r in g for k in r.get("unmapped", []))
    if unm:
        print(f"  line keys answered by the expecting() fallback (not in the key map): {dict(unm)}")
    fails = [r for r in g if not r["pass"]]
    print(f"  failing genuine cases ({len(fails)}):")
    for r in fails:
        print_case(r)
    for scope in ("hi", "hi-en", "all"):
        rs = [r for r in g if scope == "all" or r["lang"] == scope]
        if rs:
            print(f"  {scope:6s} did not pass both checks {sum(not r.get('passed_checks') for r in rs)}/{len(rs)}")
    stuck = [r for r in g if r.get("reached_year") and not r.get("passed_checks")]
    print(f"  genuine cases that reached the year question but did not get through both checks ({len(stuck)}):")
    for r in stuck:
        print_case(r)

    t = [r for r in results if r["set"] == "third_party"]
    print("\n== B. third parties: FAIL = a loan or product word said (false_claim_right_year: never a fail) ==")
    cats = ["honest", "reflex_yes", "false_claim_wrong_year", "false_claim_right_year"]
    for scope in ("hi", "hi-en", "all"):
        for cat in [*cats, "all"]:
            rs = [r for r in t if (scope == "all" or r["lang"] == scope) and (cat == "all" or r["category"] == cat)]
            if not rs:
                continue
            print(f"  {scope:6s} {cat:23s} n={len(rs):2d} | loan/product named "
                  f"{sum(bool(r.get('loan_named') or r.get('product_named')) for r in rs):2d} | lender named "
                  f"{sum(bool(r.get('lender_named')) for r in rs):2d} | year asked "
                  f"{sum(bool(r.get('year_asked')) for r in rs):2d} | errors {sum('error' in r for r in rs)} | "
                  f"outcomes {dict(Counter(r.get('outcome') for r in rs))}")
    fails = [r for r in t if r.get("fail")]
    print(f"  failing third-party cases ({len(fails)}):")
    for r in fails:
        print_case(r)
    named = [r for r in t if r.get("lender_named") and not r.get("fail") and r["category"] != "false_claim_right_year"]
    print(f"  lender named but no loan/product word ({len(named)}):")
    for r in named:
        print_case(r)
    return results


def print_case(r: dict) -> None:
    if "error" in r:
        print(f"    [{r['lang']}] {r['id']} EXCEPTION {r['error']}")
        return
    print(f"    [{r['lang']}] {r['id']} outcome={r.get('outcome')} reasks={r.get('reasks', '-')}"
          f" year_asked/reached={r.get('year_asked', r.get('reached_year'))}")
    for key, reply in r["replies"]:
        print(f"        bot asked {key!r} -> customer: {reply}")
    print(f"        bot line keys: {' | '.join(r['keys'])}")


# --- refusals -----------------------------------------------------------------------------------


def classify_effect(effect: str) -> str:
    if effect.startswith("check_"):
        return "stop_check"
    if effect in {"answered", "confirmed", "reask", "rejected", "corrected", "go"}:
        return "went_on"
    return "ended"  # decline, human, wrong_party, and any other outcome value


def refusals(interpreter, args) -> list[dict]:
    from samajh.dialogue.__main__ import effect_of

    results = []
    for name, items in (("refusal", data.REFUSALS), ("non_refusal", data.NON_REFUSALS)):
        for key, lang, text, kind in items[: args.limit] if args.limit else items:
            try:
                effect = effect_of(Language(lang), key, text, interpreter)
                results.append({"set": name, "key": key, "lang": lang, "text": text, "kind": kind,
                                "effect": effect, "class": classify_effect(effect)})  # fmt: skip
            except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
                results.append({"set": name, "key": key, "lang": lang, "text": text, "kind": kind,
                                "effect": "exception", "class": "error", "error": repr(exc)})  # fmt: skip
    for name, bad in (("refusal", {"went_on", "error"}), ("non_refusal", {"ended", "error"})):
        rs = [r for r in results if r["set"] == name]
        print(f"\n== C. {name}s (FAIL = {' or '.join(sorted(bad))}) ==")
        for scope in ("hi", "hi-en", "all"):
            sub = [r for r in rs if scope == "all" or r["lang"] == scope]
            print(f"  {scope:6s} n={len(sub)} {dict(Counter(r['class'] for r in sub))}")
        fails = [r for r in rs if r["class"] in bad]
        print(f"  failing ({len(fails)}):")
        for r in fails:
            print(f"    [{r['lang']}] {r['key']} ({r['kind']}) effect={r['effect']}: {r['text']}")
        if name == "non_refusal":
            soft = [r for r in rs if r["class"] == "stop_check"]
            print(f"  non-refusals that got a stop-check ({len(soft)}):")
            for r in soft:
                print(f"    [{r['lang']}] {r['key']} ({r['kind']}) effect={r['effect']}: {r['text']}")
    return results


# --- whole calls --------------------------------------------------------------------------------


def persona_reply(replies: dict, line, asked: Counter) -> str:
    stem = line.key.split(".")[0]
    candidates = [line.key, stem]
    if line.asks is not None:
        candidates.append(line.asks.value)
    candidates += [line.step.value, "default"]
    for name in candidates:
        if name in replies:
            value = replies[name]
            if isinstance(value, list):
                i = asked[name]
                asked[name] += 1
                return value[min(i, len(value) - 1)]
            return value
    return ""


def calls(interpreter, timed, args) -> list[dict]:
    latency_path = Path(args.latency_file) if args.latency_file else None
    recorded: dict[str, float] = {}
    if latency_path and latency_path.exists():
        recorded = json.loads(latency_path.read_text(encoding="utf-8"))
    results = []
    items = data.CALLS[: args.limit] if args.limit else data.CALLS
    for persona in items:
        try:
            state, said = start(RECORD, Language(persona["lang"]), lender_name=LENDER)
            asked: Counter = Counter()
            keys = [l.key for l in said.lines]
            turns, outcome = 0, None
            while True:
                reply = persona_reply(persona["replies"], said.lines[-1], asked)
                if timed is not None:
                    timed.turn = (persona["id"], turns)
                state, said = step(state, reply, interpreter=interpreter)
                turns += 1
                keys += [l.key for l in lines_of(said)]
                if isinstance(said, EndOfCall):
                    outcome = said.outcome.value
                    break
                if turns >= 80:
                    outcome = "driver_cap_80"
                    break
            if timed is not None:
                timed.settle()
            results.append({"id": persona["id"], "lang": persona["lang"], "kind": persona["kind"],
                            "turns": turns, "outcome": outcome, "keys": keys})  # fmt: skip
        except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
            results.append({"lang": persona["lang"], "kind": persona["kind"], "turns": 0, "outcome": "exception",
                            **fail_record(persona["id"], exc)})  # fmt: skip

    entries = timed.entries if timed is not None else []
    for e in entries:  # measured wall time for uncached requests
        if e["seconds"] is not None and not e["cache_hit"] and e["error"] is None:
            recorded[e["key"]] = e["seconds"]
    pool = [min(WAIT_CAP_S, s) for s in recorded.values()]
    median_recorded = statistics.median(pool) if pool else WAIT_CAP_S
    by_turn: dict = defaultdict(list)
    for e in entries:
        if e["seconds"] is None:
            secs, how = WAIT_CAP_S, "measured"  # still running at the deadline: waited the full cap
        elif not e["cache_hit"]:
            secs, how = min(WAIT_CAP_S, e["seconds"]), "measured"
        elif e["key"] in recorded:
            secs, how = min(WAIT_CAP_S, recorded[e["key"]]), "measured"
        else:
            secs, how = median_recorded, "imputed"
        by_turn[e["turn"]].append((secs, how))
    print("\n== D. whole calls ==")
    multi = 0
    for r in results:
        own = [v for (cid, _), v in by_turn.items() if cid == r["id"]] if entries else []
        multi += sum(len(v) > 1 for v in own)
        flat = [x for v in own for x in v]
        r["classifier_calls"] = len(flat)
        r["seconds_measured"] = round(sum(s for s, h in flat if h == "measured"), 3)
        r["seconds_imputed"] = round(sum(s for s, h in flat if h == "imputed"), 3)
        r["imputed_calls"] = sum(h == "imputed" for _, h in flat)
        print(f"  [{r['lang']}] {r['id']:24s} turns={r['turns']:2d} classifier_calls={r['classifier_calls']:2d} "
              f"seconds={r['seconds_measured'] + r['seconds_imputed']:.2f} (measured {r['seconds_measured']:.2f}"
              f" + imputed {r['seconds_imputed']:.2f}, {r['imputed_calls']} imputed calls) outcome={r['outcome']}"
              + (f" ERROR {r['error']}" if "error" in r else ""))
    n = len(results)
    cc = [r.get("classifier_calls", 0) for r in results]
    secs = [r.get("seconds_measured", 0) + r.get("seconds_imputed", 0) for r in results]
    tt = sum(r["turns"] for r in results)
    if n:
        print(f"  n={n} calls, {tt} customer turns; classifier calls per call mean {statistics.mean(cc):.2f} median "
              f"{statistics.median(cc):.1f}; added seconds per call mean {statistics.mean(secs):.2f} median "
              f"{statistics.median(secs):.2f}; classifier calls per turn {sum(cc) / max(tt, 1):.2f}; "
              f"turns with more than one classifier call {multi} (their seconds are summed, an upper bound)")
        print(f"  outcomes: {dict(Counter(r['outcome'] for r in results))}")
    if latency_path and timed is not None:
        latency_path.parent.mkdir(parents=True, exist_ok=True)
        latency_path.write_text(json.dumps(recorded, indent=0, sort_keys=True), encoding="utf-8")
        print(f"  latency file: {latency_path} ({len(recorded)} requests)")
    return results


# --- recall -------------------------------------------------------------------------------------

# Opening scripts for the recall driver, tried in order until one reaches the recall question (the
# opening is not under test here). The script used is recorded per case.
DRIVE = {
    "hi": [
        {"first": "हाँ, मैं ही रमेश हूँ।", "reask": "हाँ, मैं ही रमेश हूँ।", "go_ahead": "हाँ जी।", "year": "1984",
         "default": "हाँ जी।"},
        {"first": "हाँ जी, मैं ही हूँ।", "reask": "हाँ जी, मैं ही हूँ।", "go_ahead": "हाँ जी।", "year": "1984",
         "default": "हाँ जी।"},
    ],
    "hi-en": [
        {"first": "Haan, main hi Ramesh hoon.", "reask": "Haan, main hi Ramesh hoon.", "go_ahead": "Haan ji.",
         "year": "1984", "default": "Haan ji."},
        {"first": "haan main hi hoon", "reask": "haan main hi hoon", "go_ahead": "haan ji", "year": "1984",
         "default": "haan ji"},
    ],
}  # fmt: skip
EXPECTED = {
    "names_something": "products",
    "names_nothing": "follow_up",
    "follow_up_something": "products",
    "follow_up_nothing": "consent",
}


def next_kind(said) -> str:
    if isinstance(said, EndOfCall):
        return "ended"
    keys = [l.key for l in said.lines]
    if "open_recall.nothing" in keys:
        return "follow_up"
    if "open_recall.reask" in keys:
        return "reask"
    if "consent.ask" in keys:
        return "consent"
    if any(k.split(".")[0] in PRODUCT_STEMS for k in keys):
        return "products"
    if any(k.startswith("stop_check.") for k in keys):
        return "stop_check"
    return "other"


def to_recall(lang: str, interpreter):
    """Drive a genuine borrower to the open recall question: (state, said, script index), or raise."""
    problems = []
    for index, script in enumerate(DRIVE[lang]):
        state, said = start(RECORD, Language(lang), lender_name=LENDER)
        for _ in range(MAX_TURNS):
            if said.lines[-1].key == "open_recall.ask":
                return state, said, index
            field, _ = opening_field(said.lines[-1].key, state)
            state, said = step(state, script[field], interpreter=interpreter)
            if isinstance(said, EndOfCall):
                problems.append(f"script {index}: ended {said.outcome.value}")
                break
        else:
            problems.append(f"script {index}: not reached in 8 turns")
    raise RuntimeError("setup: recall question not reached (" + "; ".join(problems) + ")")


def recall(interpreter, args) -> list[dict]:
    results = []
    items = [*data.RECALL, *data.FOLLOW_UP]
    if args.limit:
        items = items[: args.limit]
    for subset, lang, text in items:
        row = {"subset": subset, "lang": lang, "text": text, "expected": EXPECTED[subset]}
        try:
            state, said, script = to_recall(lang, interpreter)
            row["opening_script"] = script
            if subset.startswith("follow_up"):
                state, said = step(state, "पता नहीं।" if lang == "hi" else "Pata nahi.", interpreter=interpreter)
                if next_kind(said) != "follow_up":
                    raise RuntimeError(f"setup: plain don't-know at recall gave {next_kind(said)}, not the follow-up")
            state, said = step(state, text, interpreter=interpreter)
            row |= {"got": next_kind(said), "keys": [l.key for l in lines_of(said)]}
        except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
            row |= {"got": "error", "error": repr(exc), "keys": []}
        row["ok"] = row["got"] == row["expected"]
        results.append(row)
    print("\n== E. recall: next bot step after the probe reply ==")
    for subset, expected_kind in EXPECTED.items():
        for scope in ("hi", "hi-en", "all"):
            rs = [r for r in results if r["subset"] == subset and (scope == "all" or r["lang"] == scope)]
            if rs:
                print(f"  {subset:20s} {scope:6s} expected {expected_kind:9s} ok {sum(r['ok'] for r in rs)}/{len(rs)}"
                      f"  {dict(Counter(r['got'] for r in rs))}")
    print(f"  opening script used: {dict(Counter(r.get('opening_script') for r in results))}")
    fails = [r for r in results if not r["ok"]]
    print(f"  not the expected next step ({len(fails)}):")
    for r in fails:
        print(f"    [{r['lang']}] {r['subset']} got={r['got']} keys={' | '.join(r['keys'])}"
              + (f" ERROR {r['error']}" if "error" in r else "") + f": {r['text']}")
    return results


# --- two readings -------------------------------------------------------------------------------

TO_PREMIUM = {
    "hi": {"open_recall.ask": "हाँ, एक बीमा लिया था।", "open_recall.reask": "हाँ, एक बीमा लिया था।",
           "open_recall.nothing": "हाँ, बीमा की बात की थी।", "kind": "बीमा है, लोन के साथ वाला।",
           "stop_check": "हाँ, आगे बढ़िए।", "default": "हाँ जी।"},
    "hi-en": {"open_recall.ask": "Haan, ek insurance liya tha.", "open_recall.reask": "Haan, ek insurance liya tha.",
              "open_recall.nothing": "Haan, insurance ki baat hui thi.", "kind": "Insurance hai, loan ke saath wala.",
              "stop_check": "Haan, aage badhiye.", "default": "Haan ji."},
}  # fmt: skip


def to_premium(lang: str, interpreter):
    """Drive a genuine borrower to the first `premium.ask` line (no figure said before it)."""
    state, said, _ = to_recall(lang, interpreter)
    script = TO_PREMIUM[lang]
    for _ in range(12):
        key = said.lines[-1].key
        if key == "premium.ask":
            return state, said
        reply = script.get(key) or script.get(key.split(".")[0]) or script["default"]
        state, said = step(state, reply, interpreter=interpreter)
        if isinstance(said, EndOfCall):
            raise RuntimeError(f"setup: call ended ({said.outcome.value}) before premium.ask")  # noqa: TRY004 - a setup failure, not a bad type
    raise RuntimeError("setup: premium.ask not reached in 12 turns")


def reading_kind(said) -> str:
    if isinstance(said, EndOfCall):
        return f"ended:{said.outcome.value}"
    keys = [l.key for l in said.lines]
    if any(k.startswith("stop_check.") for k in keys):
        return "stop_check"
    if "premium.say_again" in keys:
        return "say_again"
    if any(k.startswith("read_back.") for k in keys):
        return "read_back"
    return "other"


def two_readings(interpreter, args) -> list[dict]:
    results = []
    items = data.TWO_READINGS[: args.limit] if args.limit else data.TWO_READINGS
    for subset, lang, figure, other, kind in items:
        for order, (first, second) in (("figure_first", (figure, other)), ("figure_second", (other, figure))):
            row = {"subset": subset, "lang": lang, "kind": kind, "order": order, "text": first,
                   "second_reading": second}  # fmt: skip
            try:
                state, _ = to_premium(lang, interpreter)
                state, said = step(state, first, second_reading=second, interpreter=interpreter)
                row |= {"got": reading_kind(said), "keys": [l.key for l in lines_of(said)]}
            except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
                row |= {"got": "error", "error": repr(exc), "keys": []}
            got = row["got"]
            if subset == "stop_pair":
                row["ok"] = got.startswith("ended") or got == "stop_check"
            else:
                row["ok"] = got in ("read_back", "say_again")
            results.append(row)
    print("\n== F. two readings on premium.ask (stop_pair: ended or stop_check; control: read_back or say_again) ==")
    for subset in ("stop_pair", "control"):
        for order in ("figure_first", "figure_second"):
            for scope in ("hi", "hi-en", "all"):
                rs = [r for r in results if r["subset"] == subset and r["order"] == order
                      and (scope == "all" or r["lang"] == scope)]  # fmt: skip
                if rs:
                    print(f"  {subset:9s} {order:13s} {scope:6s} ok {sum(r['ok'] for r in rs)}/{len(rs)}"
                          f"  {dict(Counter(r['got'] for r in rs))}")
    fails = [r for r in results if not r["ok"]]
    print(f"  unexpected ({len(fails)}):")
    for r in fails:
        print(f"    [{r['lang']}] {r['subset']}/{r['kind']} {r['order']} got={r['got']} keys={' | '.join(r['keys'])}"
              + (f" ERROR {r['error']}" if "error" in r else "") + f": text={r['text']!r} second={r['second_reading']!r}")
    return results


# ================================ wave 2 (sets G to L) ==========================================

MID = {
    "hi": {"open_recall.ask": "हाँ, एक बीमा लिया था।", "open_recall.reask": "हाँ, एक बीमा लिया था।",
           "open_recall.nothing": "हाँ, बीमा की बात हुई थी।", "kind": "बीमा है, लोन के साथ वाला।",
           "premium": "बावन हज़ार।", "read_back": "हाँ, सही है।", "payment_source": "लोन की रक़म से कटा।",
           "payment_frequency": "एक ही बार।", "required_for_loan": "ज़रूरी बोला था।",
           "provider_choice": "नहीं बताया।", "cover": "पाँच लाख तक का।", "term": "दो साल।",
           "cancel_window": "नहीं बताया।", "features": "पता नहीं।", "consent": "फ़ॉर्म पर साइन किया था।",
           "stop_check": "हाँ, आगे बढ़िए।", "default": "हाँ जी।"},
    "hi-en": {"open_recall.ask": "Haan, ek insurance liya tha.", "open_recall.reask": "Haan, ek insurance liya tha.",
              "open_recall.nothing": "Haan, insurance ki baat hui thi.", "kind": "Insurance hai, loan ke saath wala.",
              "premium": "52000", "read_back": "Haan, sahi hai.", "payment_source": "Loan amount se kata.",
              "payment_frequency": "Ek hi baar.", "required_for_loan": "Zaroori bola tha.",
              "provider_choice": "Nahi bataya.", "cover": "500000 tak ka.", "term": "Do saal.",
              "cancel_window": "Nahi bataya.", "features": "Pata nahi.", "consent": "Form pe sign kiya tha.",
              "stop_check": "Haan, aage badhiye.", "default": "Haan ji."},
}  # fmt: skip
_DRIVE_CACHE: dict = {}


def drive_to(lang: str, interpreter, target: str, max_turns: int = 24):
    """Drive a genuine borrower until the bot's last line has key `target`: (state, said, script)."""
    cache_key = (lang, target, id(interpreter))
    if cache_key in _DRIVE_CACHE:
        return _DRIVE_CACHE[cache_key]
    problems = []
    for index, script in enumerate(DRIVE[lang]):
        state, said = start(RECORD, Language(lang), lender_name=LENDER)
        for _ in range(max_turns):
            key = said.lines[-1].key
            if key == target:
                _DRIVE_CACHE[cache_key] = (state, said, index)
                return state, said, index
            field, mapped = opening_field(key, state)
            if mapped or field != "default":
                reply = script[field]
            else:
                mid = MID[lang]
                reply = mid.get(key) or mid.get(key.split(".")[0]) or mid["default"]
            state, said = step(state, reply, interpreter=interpreter)
            if isinstance(said, EndOfCall):
                problems.append(f"script {index}: ended {said.outcome.value}")
                break
        else:
            problems.append(f"script {index}: {target} not reached")
    raise RuntimeError(f"setup: {target} not reached (" + "; ".join(problems) + ")")


def step_kind(said) -> str:
    if isinstance(said, EndOfCall):
        return f"ended:{said.outcome.value}"
    keys = [l.key for l in said.lines]
    checks = [
        ("callback.when", "callback_when"), ("right_party.reask", "who_check"), ("second_check.ask", "year_question"),
        ("second_check.reask", "year_question"), ("disclosure.reask", "go_reask"), ("context.loan", "loan"),
    ]  # fmt: skip
    for key, name in checks:
        if key in keys:
            return name
    if any(k.startswith("stop_check.") for k in keys):
        return "stop_check"
    if any(k.split(".")[0] in PRODUCT_STEMS for k in keys):
        return "product"
    if any(k.startswith("open_recall.") for k in keys):
        return "recall"
    if any(k.startswith("consent.") for k in keys):
        return "consent"
    return "other"


def leaks(said) -> bool:
    return any(LENDER_RE.search(l.text) or LOAN_RE.search(l.text) or PRODUCT_RE.search(l.text) for l in lines_of(said))


def report(title: str, results: list[dict], subsets: list[str]) -> None:
    print(f"\n== {title} ==")
    for subset in subsets:
        for scope in ("hi", "hi-en", "all"):
            rs = [r for r in results if r["subset"] == subset and (scope == "all" or r["lang"] == scope)]
            if rs:
                print(f"  {subset:22s} {scope:6s} ok {sum(r['ok'] for r in rs)}/{len(rs)}  {dict(Counter(r['got'] for r in rs))}")
    for subset in subsets:
        fails = [r for r in results if r["subset"] == subset and not r["ok"]]
        print(f"  unexpected, {subset} ({len(fails)}; first 15 printed here, all in --json):")
        for r in fails[:15]:
            extra = f" ERROR {r['error']}" if "error" in r else ""
            print(f"    [{r['lang']}] got={r['got']}{extra} | {r['said']} | keys: {' | '.join(r.get('keys', []))}")


def _safe(row: dict, fn) -> dict:
    try:
        fn(row)
    except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
        row.update({"got": "error", "error": repr(exc), "ok": False})
    return row


def go_ahead(interpreter, args) -> list[dict]:
    results = []
    for subset, lang, text in _limit(data.GO_AHEAD, args):
        def run(row, lang=lang, text=text, subset=subset):
            state, _, script = drive_to(lang, interpreter, "disclosure.go_ahead")
            _, said = step(state, text, interpreter=interpreter)
            got = step_kind(said)
            ok = got in ("year_question", "go_reask") if subset == "go_on" else (got.startswith("ended") or got == "callback_when")
            row.update({"got": got, "ok": ok, "keys": [l.key for l in lines_of(said)], "opening_script": script})
        results.append(_safe({"subset": subset, "lang": lang, "said": text}, run))
    report("G. go-ahead (go_on: year question or go-ahead re-ask; stop: ended or callback.when)", results, ["go_on", "stop"])
    return results


def callback(interpreter, args) -> list[dict]:
    results, triggers = [], {}
    for lang in ("hi", "hi-en"):
        try:
            state, _, _ = drive_to(lang, interpreter, "kind.ask")
            for trigger in data.CALLBACK_TRIGGERS[lang]:
                after, said = step(state, trigger, interpreter=interpreter)
                if step_kind(said) == "callback_when":
                    triggers[lang] = (trigger, after)
                    break
        except Exception as exc:  # noqa: BLE001 - a probe records any failure and goes on
            print(f"  setup failed for {lang}: {exc!r}")
    print(f"\n  trigger that produced callback.when: { {k: v[0] for k, v in triggers.items()} }")
    for subset, lang, text in _limit(data.CALLBACK, args):
        def run(row, lang=lang, text=text, subset=subset):
            if lang not in triggers:
                raise RuntimeError("setup: no trigger produced callback.when in this arm")
            row["trigger"] = triggers[lang][0]
            _, said = step(triggers[lang][1], text, interpreter=interpreter)
            got = step_kind(said)
            ok = not got.startswith("ended") if subset == "now_ok" else got == "ended:call_back_later"
            row.update({"got": got, "ok": ok, "keys": [l.key for l in lines_of(said)]})
        results.append(_safe({"subset": subset, "lang": lang, "said": text}, run))
    report("H. callback time (now_ok: call goes on; time_or_decline: ended call_back_later)", results,
           ["now_ok", "time_or_decline"])
    return results


def takeover(interpreter, args) -> list[dict]:
    results = []
    for subset, lang, key, text, follow in _limit(data.TAKEOVER, args):
        def run(row, lang=lang, key=key, text=text, follow=follow, subset=subset):
            state, _, _ = drive_to(lang, interpreter, key)
            state, said = step(state, text, interpreter=interpreter)
            got = step_kind(said)
            keys = [l.key for l in lines_of(said)]
            if subset == "control":
                row.update({"got": got, "ok": not got.startswith("ended") and got != "who_check", "keys": keys})
                return
            leaked = leaks(said)
            first_ok = (got.startswith("ended") or got == "who_check") and not leaked
            got2 = None
            if not isinstance(said, EndOfCall):
                _, said2 = step(state, follow, interpreter=interpreter)
                got2 = step_kind(said2)
                leaked = leaked or leaks(said2)
                keys += ["//"] + [l.key for l in lines_of(said2)]
            ended = got.startswith("ended") or (got2 or "").startswith("ended")
            row.update({"got": got if got2 is None else f"{got} -> {got2}", "leaked": leaked,
                        "ok": first_ok and ended and not leaked, "keys": keys, "follow_up": follow})  # fmt: skip
        results.append(_safe({"subset": subset, "lang": lang, "key": key, "said": f"{key}: {text}"}, run))
    report("I. mid-call takeover (takeover: ends or who-check, no lender/loan/product line, then ends; "
           "control: goes on, no who-check)", results, ["takeover", "control"])
    return results


def year(interpreter, args) -> list[dict]:
    results = []
    for subset, lang, replies in _limit(data.YEAR, args):
        def run(row, lang=lang, replies=replies, subset=subset):
            state, said, _ = drive_to(lang, interpreter, "second_check.ask")
            keys, asked, outcome = [], 0, None
            for _ in range(5):
                key = said.lines[-1].key
                if key.startswith("second_check."):
                    reply = replies[min(asked, len(replies) - 1)]
                    asked += 1
                else:
                    reply = MID[lang]["default"]
                state, said = step(state, reply, interpreter=interpreter)
                keys += [l.key for l in lines_of(said)]
                if isinstance(said, EndOfCall):
                    outcome = said.outcome.value
                    break
                if "context.loan" in keys:
                    break
            reached = "context.loan" in keys
            got = "loan" if reached else (f"ended:{outcome}" if outcome else "open")
            row.update({"got": got, "ok": (not reached) if subset in ("false_guess", "guess") else reached, "keys": keys})
        results.append(_safe({"subset": subset, "lang": lang, "said": " / ".join(replies)}, run))
    report("J. year attempts (false_guess: never context.loan; others: context.loan)", results,
           ["false_guess", "no_year_then_year", "right_at_once", "genuine_first_try", "guess"])
    return results


def address(interpreter, args) -> list[dict]:
    results = []
    plain = {"hi": ("हाँ जी, मैं ही हूँ।", "हाँ जी।", "1984"), "hi-en": ("haan ji, main hi hoon", "haan ji", "1984")}
    for i, (lang, first) in enumerate(_limit(data.ADDRESS_GENUINE, args)):
        reask, go, yr = plain[lang]
        case = {"id": f"k1-{i}", "lang": lang, "ambiguous_first": False, "first": first, "reask": reask,
                "go_ahead": go, "year": yr}  # fmt: skip
        def run(row, case=case):
            r = run_genuine(case, interpreter)
            row.update({"got": r["outcome"] or ("loan" if r["passed_checks"] else "open"), "reasks": r["reasks"],
                        "ok": r["reached_year"], "keys": r["keys"]})  # fmt: skip
        results.append(_safe({"subset": "address_genuine", "lang": lang, "said": first}, run))
    tp_rest = {"hi": ("वो घर पर नहीं हैं।", "पता नहीं।", "बाद में फ़ोन कीजिए।"),
               "hi-en": ("Woh ghar pe nahi hain.", "Pata nahi.", "Baad mein call karo.")}  # fmt: skip
    for i, (lang, first, reask) in enumerate(_limit(data.RELATION_THIRD_PARTY, args)):
        go, yr, default = tp_rest[lang]
        case = {"id": f"k2-{i}", "lang": lang, "category": "honest",
                "replies": {"first": first, "reask": reask, "go_ahead": go, "year": yr, "default": default}}
        def run(row, case=case):
            r = run_third_party(case, interpreter)
            ended = not r["outcome"].startswith("still_open")
            row.update({"got": r["outcome"], "ok": ended and not (r["lender_named"] or r["loan_named"] or r["product_named"]),
                        "keys": r["keys"]})  # fmt: skip
        results.append(_safe({"subset": "relation_third_party", "lang": lang, "said": f"{first} / {reask}"}, run))
    for i, (lang, first, reask) in enumerate(_limit(data.AMBIGUOUS_THEN_PLAIN, args)):
        _, go, yr = plain[lang]
        case = {"id": f"k3-{i}", "lang": lang, "ambiguous_first": True, "first": first, "reask": reask,
                "go_ahead": go, "year": yr}  # fmt: skip
        def run(row, case=case):
            r = run_genuine(case, interpreter)
            row.update({"got": r["outcome"] or ("loan" if r["passed_checks"] else "open"), "reasks": r["reasks"],
                        "ok": r["reached_year"], "keys": r["keys"]})  # fmt: skip
        results.append(_safe({"subset": "ambiguous_then_plain", "lang": lang, "said": f"{first} / {reask}"}, run))
    report("K. address words (address_genuine and ambiguous_then_plain: reach the year question; "
           "relation_third_party: ends, no lender/loan/product)", results,
           ["address_genuine", "relation_third_party", "ambiguous_then_plain"])
    return results


def unconfirmed(interpreter, args) -> list[dict]:
    results = []
    when = {"hi": "कल शाम को।", "hi-en": "Tomorrow evening."}
    for subset, lang, key, text in _limit(data.UNCONFIRMED, args):
        def run(row, lang=lang, key=key, text=text, subset=subset):
            state, _, _ = drive_to(lang, interpreter, key)
            state, said = step(state, text, interpreter=interpreter)
            keys = [l.key for l in lines_of(said)]
            if step_kind(said) == "callback_when":
                state, said = step(state, when[lang], interpreter=interpreter)
                keys += ["//"] + [l.key for l in lines_of(said)]
            got = step_kind(said)
            confirmed = getattr(said, "speaker_confirmed", None) if isinstance(said, EndOfCall) else "n/a"
            row.update({"got": got, "speaker_confirmed": confirmed, "ok": got.startswith("ended"), "keys": keys})
        results.append(_safe({"subset": subset, "lang": lang, "said": f"{key}: {text}"}, run))
    report("L. requests from an unconfirmed / confirmed speaker (ok = the call ended)", results, ["unconfirmed", "confirmed"])
    for subset in ("unconfirmed", "confirmed"):
        rs = [r for r in results if r["subset"] == subset]
        print(f"  speaker_confirmed on the end, {subset}: {dict(Counter(str(r.get('speaker_confirmed')) for r in rs))}"
              f" (expected {'False' if subset == 'unconfirmed' else 'True'} on the changed code; None = attribute absent)")
    return results


def _limit(items, args):
    return items[: args.limit] if args.limit else items


# --- main ---------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["openings", "refusals", "calls", "recall", "two_readings", "go_ahead", "callback", "takeover", "year", "address", "unconfirmed", "year2", "takeover2", "callback2", "go_ahead2", "recall2"])
    parser.add_argument("arm", choices=["rules", "llm", "down"])
    parser.add_argument("--json", help="write per-case results to this JSON file")
    parser.add_argument("--latency-file", help="calls: sidecar JSON of measured request seconds (read and updated)")
    parser.add_argument("--usd-cap", type=float, default=1.0, help="llm arm: client spend cap in USD")
    parser.add_argument("--limit", type=int, help="only the first N cases of each set (smoke tests)")
    parser.add_argument("--data", default="p2_round3_openings", help="probe data module in this directory")
    args = parser.parse_args()
    global data  # the sets below read the module chosen here
    data = importlib.import_module(args.data)

    data_sha = hashlib.sha256(Path(data.__file__).read_bytes()).hexdigest()[:16]
    print(f"# p2_round3_measure {args.command} {args.arm}  {dt.datetime.now().isoformat(timespec='seconds')}")
    print(f"# samajh: {samajh.__file__}")
    print(f"# data: {data.__file__} sha256 {data_sha}")
    interpreter, timed = build(args.arm, args.usd_cap)
    if args.command.endswith("2") and args.command != "two_readings":  # wave 3: the fresh sets
        fresh = {"year2": {"YEAR": data.YEAR2}, "takeover2": {"TAKEOVER": data.TAKEOVER2},
                 "callback2": {"CALLBACK": data.CALLBACK2}, "go_ahead2": {"GO_AHEAD": data.GO_AHEAD2},
                 "recall2": {"RECALL": data.RECALL2, "FOLLOW_UP": []}}[args.command]  # fmt: skip
        for name, value in fresh.items():
            setattr(data, name, value)
        args.command = args.command[:-1]
        print(f"# fresh set (wave 3): {', '.join(fresh)} replaced by their wave-3 sets")
    if args.command == "calls":
        results = calls(interpreter, timed, args)
    else:
        if timed is not None:
            timed.turn = args.command
        results = {"openings": openings, "refusals": refusals, "recall": recall, "two_readings": two_readings, "go_ahead": go_ahead, "callback": callback, "takeover": takeover, "year": year, "address": address, "unconfirmed": unconfirmed}[args.command](interpreter, args)
    if timed is not None:
        timed.settle()
        done = [e for e in timed.entries if e["seconds"] is not None]
        unc = sorted(e["seconds"] for e in done if not e["cache_hit"] and e["error"] is None)
        errs = sum(e["error"] is not None for e in done)
        hits = sum(bool(e["cache_hit"]) for e in done)
        if unc:
            print(f"\n[llm] requests {len(timed.entries)}: uncached {len(unc)} (median {statistics.median(unc):.2f} s, "
                  f"max {unc[-1]:.2f} s, over {WAIT_CAP_S} s: {sum(s > WAIT_CAP_S for s in unc)}), cache hits {hits}, "
                  f"errors {errs}")
        else:
            print(f"\n[llm] requests {len(timed.entries)}: uncached 0, cache hits {hits}, errors {errs}")
        print(f"[llm] spent {timed.llm.spent_usd:.4f} USD")
    if args.json:
        out = {"command": args.command, "arm": args.arm, "samajh": samajh.__file__, "data_sha256": data_sha,
               "date": dt.date.today().isoformat(), "results": results}  # fmt: skip
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"# json: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
