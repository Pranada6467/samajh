"""Play the frozen banks through whatever `samajh` is on PYTHONPATH and write one JSON row per case, with every bot
utterance (keys, language, text) and every classifier request. Scoring is separate (score.py) and imports no samajh.

    cd /tmp && PYTHONPATH=<arm dir or empty> SAMAJH_STATE_DIR=<repo>/.samajh \
      uv run --project <repo> python <check>/harness/run.py --bank A|B|C|Y --interp live|rules --out OUT.jsonl

The live interpreter is built as the server builds it: LlmFallbackInterpreter(LlmClient.from_env(timeout=3.0,
retry=RetryPolicy(max_attempts=1))). Each classifier request is timed by wrapping the client's `complete`.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)

import samajh  # noqa: E402
from samajh.dialogue import EndOfCall, RuleInterpreter, start, step  # noqa: E402
from samajh.types import Language, LoanRecord  # noqa: E402

CHECK = Path(__file__).resolve().parents[1]
BANKS = CHECK / "banks"
LENDER = "Udaharan Bank"
RECORD = {
    "loan_id": "LN-NAMES-0001", "lender_type": "bank", "loan_kind": "gold", "sanctioned_inr": 500000,
    "disbursed_inr": 448000, "disbursed_on": "2026-10-20",
    "products": [{
        "id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
        "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
        "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30, "features": [],
        "consent": None,
    }],
}
MAX_STEPS = 80

CALLS: list[dict] = []
_calls_lock = threading.Lock()


def record_for(first_name: str) -> LoanRecord:
    borrower = {"name": f"{first_name} Kalpit", "dob": "1984-06-15", "language": "hi"}
    return LoanRecord.model_validate(RECORD | {"borrower": borrower})


def make_interp(kind: str):
    if kind == "rules":
        return RuleInterpreter(), None
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.llm import LlmClient
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    client = LlmClient.from_env(timeout=3.0, retry=RetryPolicy(max_attempts=1), usd_cap=1.0)
    inner = client.complete

    def timed(schema, messages, **kw):
        t0 = time.monotonic()
        row = {"messages": [m.content for m in messages], "model": kw.get("model")}
        try:
            res = inner(schema, messages, **kw)
            row |= {"wall_s": time.monotonic() - t0, "usd": res.usd, "cache_hit": res.cache_hit, "ok": True,
                    "value": json.loads(res.value.model_dump_json())}
            return res
        except Exception as e:  # noqa: BLE001
            row |= {"wall_s": time.monotonic() - t0, "usd": 0.0, "cache_hit": False, "ok": False,
                    "error": f"{type(e).__name__}: {str(e)[:200]}"}
            raise
        finally:
            with _calls_lock:
                CALLS.append(row)

    client.complete = timed  # type: ignore[method-assign]
    return LlmFallbackInterpreter(client), client


def utt(said) -> dict:
    u = said.utterance if isinstance(said, EndOfCall) else said
    d = {"language": u.language.value, "keys": [ln.key for ln in u.lines], "texts": [ln.text for ln in u.lines]}
    if isinstance(said, EndOfCall):
        d |= {"end": said.outcome.value, "requested_language": said.requested_language,
              "unresolved": [json.loads(x.model_dump_json()) for x in said.unresolved],
              "degraded": list(said.degraded_turns)}
    return d


def snapshot(state) -> dict:
    return {"check_passed": getattr(state, "check_passed", None), "position": type(state.position).__name__,
            "degraded": list(getattr(state, "degraded_turns", ())), "language": state.language.value}


# --- fixed plain answers for reaching a slot and for playing the rest of the call
PLAIN = {
    "hi": {
        "right_party": "हाँ, मैं ही रमेश हूँ", "disclosure": "हाँ, बोलिए", "open_recall": "हाँ, एक बीमा लिया था",
        "kind": "बीमा है, कुछ हो जाए तो लोन चुक जाएगा", "premium": "पचास हज़ार रुपये", "read_back": "हाँ, सही है",
        "payment_source": "लोन में से कट गया था", "payment_frequency": "एक ही बार", "required_for_loan": "बोले थे ज़रूरी है",
        "provider_choice": "नहीं, ऐसा नहीं बताया", "cover": "कुछ हो जाए तो लोन चुक जाएगा, पाँच लाख तक", "term": "दो साल",
        "cancel_window": "कुछ नहीं बताया", "features": "पता नहीं", "consent": "लोन और बीमा के लिए हाँ कहा था, फ़ॉर्म पर साइन किया था",
        "stop_check": "हाँ, आगे पूछिए", "callback": "नहीं नहीं, अभी बात कर लीजिए", "_": "जी, पता नहीं",
    },
    "hi-en": {
        "right_party": "haan, main hi Ramesh hoon", "disclosure": "haan, boliye", "open_recall": "haan, ek insurance liya tha",
        "kind": "insurance hai, kuch ho jaye to loan chuk jayega", "premium": "pachaas hazaar rupaye",
        "read_back": "haan, sahi hai", "payment_source": "loan mein se kat gaya tha", "payment_frequency": "ek hi baar",
        "required_for_loan": "bole the zaroori hai", "provider_choice": "nahi, aisa nahi bataya",
        "cover": "kuch ho jaye to loan chuk jayega, paanch lakh tak", "term": "do saal", "cancel_window": "kuch nahi bataya",
        "features": "pata nahi", "consent": "loan aur insurance ke liye haan bola tha, form pe sign kiya tha",
        "stop_check": "haan, aage poochiye", "callback": "nahi nahi, abhi baat kar lo", "_": "ji, pata nahi",
    },
}


def plain(lang: str, key: str) -> str:
    table = PLAIN["hi-en" if lang == "hi-en" else "hi"]
    return table.get(key.split(".")[0], table["_"])


def play_to(record, language: Language, target: tuple[str, ...], interp, **start_kw):
    """Play plain answers (word lists for the prefix, so every arm reaches the same position) until the bot's last line
    key is one of `target`."""
    rules = RuleInterpreter()
    state, said = start(record, language, lender_name=LENDER, **start_kw)
    trail = [utt(said)]
    for _ in range(40):
        key = said.lines[-1].key
        if key in target:
            return state, said, trail
        state, said = step(state, plain(language.value, key), interpreter=rules)
        trail.append(utt(said))
        if isinstance(said, EndOfCall):
            return state, said, trail
    return state, said, trail


def finish(state, said, lang, interp, trail, budget=MAX_STEPS):
    """Play the rest of the call with plain answers, so a loop shows up as turn_limit."""
    n = 0
    while not isinstance(said, EndOfCall) and n < budget:
        reply = plain(lang, said.lines[-1].key)
        state, said = step(state, reply, interpreter=interp)
        trail.append({"reply": reply} | utt(said))
        n += 1
    return state, said


# --- bank A: the opening, replies in order (score_openings.py approach), recording every utterance
def run_a(row, interp):
    state, said = start(record_for(row["first_name"]), Language(row["language"]), lender_name=LENDER)
    trail = [utt(said)]
    passed_at = None
    for i, reply in enumerate(row["replies"]):
        state, said = step(state, reply, interpreter=interp)
        trail.append({"reply": reply, "i": i} | utt(said) | snapshot(state))
        if state.check_passed and passed_at is None:
            passed_at = i
        if isinstance(said, EndOfCall):
            break
        if row["kind"] in ("borrower", "third_party") and state.check_passed:
            break
        if row["kind"] == "language" and i == row["event_turn"]:
            break
    return {"trail": trail, "passed": bool(state.check_passed), "passed_at": passed_at,
            "outcome": said.outcome.value if isinstance(said, EndOfCall) else None,
            "degraded": list(getattr(state, "degraded_turns", ()))}


# --- bank B: half answers at consent / kind
def run_b(row, interp):
    lang = Language(row["language"])
    target = ("consent.ask",) if row["slot"] == "consent" else ("kind.ask", "kind.ask_named")
    state, said, trail = play_to(record_for("Ramesh"), lang, target, interp)
    if isinstance(said, EndOfCall) or said.lines[-1].key not in target:
        return {"error": "did not reach slot", "trail": trail}
    asked_key = said.lines[-1].key
    state, said = step(state, row["first"], interpreter=interp)
    trail.append({"reply": row["first"], "bank": "first"} | utt(said))
    followups = []
    used_followup = False
    while not isinstance(said, EndOfCall):
        key = said.lines[-1].key
        on_slot = key.startswith(row["slot"] + ".") or "follow" in key or key.startswith("stop_check")
        if not on_slot:
            break
        followups.append({"keys": [ln.key for ln in said.lines], "texts": [ln.text for ln in said.lines]})
        if len(followups) > 3:
            break
        reply = row["followup"] if not used_followup and not key.startswith("stop_check") else plain(lang.value, key)
        used_followup = used_followup or reply == row["followup"]
        state, said = step(state, reply, interpreter=interp)
        trail.append({"reply": reply, "bank": "followup" if reply == row["followup"] else "plain"} | utt(said))
    moved_to = None if isinstance(said, EndOfCall) else said.lines[-1].key
    state, said = finish(state, said, lang.value, interp, trail)
    return {"asked_key": asked_key, "followups": followups, "moved_to": moved_to, "trail": trail,
            "outcome": said.outcome.value if isinstance(said, EndOfCall) else None,
            "unresolved": utt(said).get("unresolved") if isinstance(said, EndOfCall) else None,
            "degraded": list(getattr(state, "degraded_turns", ())),
            "transcript": json.loads(state.transcript().model_dump_json())}


# --- bank C: mid-call
def run_c(row, interp):
    lang = Language(row["language"])
    target = (f"{row['slot']}.ask",)
    state, said, trail = play_to(record_for("Ramesh"), lang, target, interp)
    if isinstance(said, EndOfCall) or said.lines[-1].key not in target:
        return {"error": "did not reach slot", "trail": trail}
    state, said = step(state, row["first"], interpreter=interp)
    trail.append({"reply": row["first"], "bank": "first"} | utt(said))
    after = [] if isinstance(said, EndOfCall) else [said.lines[-1].key]
    used = set()
    for _ in range(4):
        if isinstance(said, EndOfCall):
            break
        key = said.lines[-1].key
        if key.startswith("stop_check") and "stop" not in used:
            reply, tag = row["if_stop_check"], "stop"
        elif key.startswith("callback.when") and "when" not in used:
            reply, tag = row["if_when"], "when"
        elif (key.startswith(row["slot"] + ".") or key.startswith("defer.")) and "reask" not in used:
            reply, tag = row["if_reask"], "reask"
        else:
            break
        used.add(tag)
        state, said = step(state, reply, interpreter=interp)
        trail.append({"reply": reply, "bank": tag} | utt(said))
        if not isinstance(said, EndOfCall):
            after.append(said.lines[-1].key)
    state, said = finish(state, said, lang.value, interp, trail)
    return {"after_keys": after, "trail": trail, "outcome": said.outcome.value if isinstance(said, EndOfCall) else None,
            "unresolved": utt(said).get("unresolved") if isinstance(said, EndOfCall) else None,
            "degraded": list(getattr(state, "degraded_turns", ()))}


# --- bank Y: year of birth
def run_y(row, interp):
    from samajh.identity import CheckKind, IdentityPolicy

    lang = Language(row["language"])
    state, said = start(record_for(row["first_name"]), lang, lender_name=LENDER,
                        identity=IdentityPolicy(second_check=CheckKind.year_of_birth))
    trail = [utt(said)]
    for _ in range(8):
        if isinstance(said, EndOfCall):
            break
        key = said.lines[-1].key
        if key.startswith("right_party"):
            reply = row["self_claim"]
        elif key.startswith("second_check"):
            reply = row["year_reply"]
        elif key.startswith("disclosure"):
            reply = plain(lang.value, key)
        else:
            break
        state, said = step(state, reply, interpreter=interp)
        trail.append({"reply": reply} | utt(said) | snapshot(state))
    return {"trail": trail, "passed": bool(state.check_passed),
            "outcome": said.outcome.value if isinstance(said, EndOfCall) else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True, choices=["A", "B", "C", "Y", "Y2"])
    ap.add_argument("--interp", required=True, choices=["live", "rules"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    files = {"A": "A-openings", "B": "B-half-answers", "C": "C-midcall", "Y": "Y-birth-year", "Y2": "Y2-birth-year-chatty"}
    rows = [json.loads(x) for x in (BANKS / f"{files[args.bank]}.jsonl").read_text().splitlines() if x.strip()]
    fn = {"A": run_a, "B": run_b, "C": run_c, "Y": run_y, "Y2": run_y}[args.bank]
    interp, client = make_interp(args.interp)

    def one(row):
        try:
            return {"id": row["id"]} | fn(row, interp)
        except Exception as e:  # noqa: BLE001
            import traceback

            return {"id": row["id"], "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-1500:]}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, rows))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    calls_path = out.with_suffix(".calls.jsonl")
    calls_path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in CALLS), encoding="utf-8")
    meta = {"samajh": samajh.__file__, "bank": args.bank, "interp": args.interp, "n": len(rows),
            "errors": sum(1 for r in results if "error" in r), "classifier_calls": len(CALLS),
            "usd": sum(c["usd"] for c in CALLS), "seconds": time.time() - t0}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
