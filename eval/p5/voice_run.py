"""P5 voice run: the open arm at level 0, each customer's frozen replies voiced by Timbre and sent to the
Samajh server (eval/p5/serve.py) through the phone's HTTP routes, to a case file. Resumable.

    uv run python eval/p5/serve.py --ceiling 200 &           # first, in another shell
    uv run python eval/p5/voice_run.py --out eval/p5/runs/voice-L0 [--url http://127.0.0.1:8095]
        [--customers P5-C001,...] [--ceiling 200] [--smoke] [--dry-run]

For each customer: open a session for its record and language; after each bot utterance read the last
current bot event from the session log (line keys and tags, listen, second_reading, end_call, outcome)
and, for a read-back, the figure from the stored dialogue state; choose the reply with
`player.choose_open` (level 0, condition `disposition`: the chooser the text run uses); voice it with the
shared Gnani client (Timbre v3.0, the seeded voice of `voices.py`, 8 kHz) and send it as the turn. The
reply is the `silence_prompt` text only after a turn whose transcript came back empty. At the end of the
call the case file is requested (Batch is off in the launcher) and one call file is written to
OUT/calls/, with the keys `text_run.run_open` writes plus the voice fields (module `CALL_KEYS`).

- Resumable: a customer whose call file exists is skipped. OUT/progress/<id>.json names the session and
  the turns so far; a rerun after a crash continues that session (a turn sent twice is answered once).
- A call that fails (a refused step, a case file that is not `ready`, a dialogue that does not end) is
  written as `status: "no_result"` with the error and never rerun. A run-level stop (the server is
  unreachable, the credit cap, the key busy) writes no call file, so the rerun continues the call.
- Refuses to start unless every digest in data/p5/FROZEN.json matches, the phone port 8085 is free, no
  process holds .samajh/gnani.lock and the ledger rows do not change over 30 s (RUNNER-PLAN Part 2 §4).
- Stops before the next customer once the ledger has grown by `--ceiling` since the run's first start.
- `--dry-run`: no network. The planned customers, voices, the replies the chooser gives on the text path
  with the word lists alone (an approximation of the live path), which bot lines and replies are not in
  the local Timbre cache, and an estimated credit total.
- `--smoke`: 4 customers (hi and hi-en, a female and a male voice, one third party), ceiling 30.
"""

from __future__ import annotations

import argparse
import json
import random
import socket
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from bank import (
    Customer,
    Topics,
    check_frozen,
    harness_hashes,
    load_customers,
    load_record,
    load_topics,
    resolve_data,
)
from player import BotLineView, Choice, Said, choose_open
from voices import TTS_LANGUAGE, assign_voices

LEVEL = 0.0
CONDITION = "disposition"
LINE_RATE = 8000
TTS_MODEL = "timbre-v3.0"
MAX_CUSTOMER_TURNS = 80  # above the server's 60: a guard against a loop
ORDER_SEED = "samajh-p5-2026-11-10:voice-order"
DEFAULT_URL = "http://127.0.0.1:8095"
DEFAULT_CEILING = 200.0
SMOKE_CEILING = 30.0
CHARS_PER_SECOND = 12.0  # assumed speaking rate for the STT estimate (no audio measured)
SILENCE = "silence_prompt"
# Server error codes that stop the run without a call file, so a rerun continues the call.
RUN_STOPPING = frozenset({"credit_cap_reached", "gnani_busy", "gnani_unreachable", "gnani_rate_limited"})
PHONE_PORT = 8085

# The keys of a voice call file: `text_run.run_open`'s (with `finished_utc` from run.py), then the voice ones.
TEXT_KEYS = (
    "customer_id", "arm", "condition", "level", "language", "kind", "gold_class", "record_id", "writer_model",
    "second_reading", "status", "turns", "unmapped", "errors", "final_bot", "outcome", "speaker_confirmed",
    "degraded_turns", "unresolved", "tier", "flags", "gaps", "referral_basis", "summary", "transcript",
    "finished_utc",
)  # fmt: skip
VOICE_KEYS = (
    "path", "session_id", "voice", "tts", "batch", "case_status", "case_failed", "case_steps",
    "degraded_turn_ids", "models", "recording_seconds", "ended_reason", "ledger", "resumed",
)  # fmt: skip
CALL_KEYS = TEXT_KEYS + VOICE_KEYS


class RunStopped(Exception):
    """Stop the whole run here and write no call file for this customer (a rerun continues it)."""


class StepRefused(Exception):
    def __init__(self, step: str, status: int, error: Mapping[str, Any]) -> None:
        self.step, self.status, self.error = step, status, dict(error)
        super().__init__(f"{step}: HTTP {status} {error.get('code')}: {error.get('message')}")


def call_name(customer_id: str) -> str:
    """As `run.call_name(customer_id, "open", 0.0)`."""
    return f"{customer_id}__open__L0.json"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


# --- the session log, read back ---------------------------------------------------------------------


def _checked(step: str, response: Any) -> Any:
    if 200 <= response.status_code < 300:
        return (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response
        )
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = {"code": "not_json", "message": response.text[:200]}
    if error.get("code") in RUN_STOPPING:
        raise RunStopped(f"{step}: {error.get('code')}: {error.get('message')}")
    raise StepRefused(step, response.status_code, error)


def _current(log: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [e for e in log["events"] if e["type"] != "error" and not e.get("superseded")]


def _last_bot(log: Mapping[str, Any]) -> dict[str, Any]:
    last = _current(log)[-1]
    if last["type"] != "bot":
        raise RuntimeError(f"the last current event is not the bot's (seq {last['seq']})")
    return last


def _customer_events(log: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [e for e in _current(log) if e["type"] == "customer"]


def _event(log: Mapping[str, Any], seq: int) -> dict[str, Any]:
    return log["events"][seq]


def dialogue_lines(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The dialogue's lines of a bot event: a line spoken as several clips (`piece` k/n) joined again."""
    out: list[dict[str, Any]] = []
    for line in event["lines"]:
        piece = line.get("tags", {}).get("piece")
        if piece and not piece.startswith("1/") and out:
            out[-1]["text"] += " " + line["text"]
            continue
        tags = line.get("tags", {})
        out.append({"key": line.get("key"), "text": line["text"], "step": tags.get("step"),
                    "asks": tags.get("asks"), "product_id": tags.get("product_id")})  # fmt: skip
    return out


def readback_words(state: Mapping[str, Any] | None) -> str | None:
    """The `amount_words` slot of the read-back line the call is waiting on, rebuilt from the stored state
    as the dialogue builds it (`machine._read_back_line`); None when the state is not at a read-back."""
    position = (state or {}).get("position") or {}
    if position.get("at") != "read_back":
        return None
    from samajh.amounts import spoken_amount
    from samajh.dialogue import load_prompts
    from samajh.types import Language

    language = Language(state["language"])
    amount, low = int(position["amount_inr"]), position.get("low")
    words = spoken_amount(amount, language)
    if low is not None and int(low) != amount:
        words = f"{spoken_amount(int(low), language)} {load_prompts(language).range_word} {words}"
    return words


def views(lines: Sequence[Mapping[str, Any]], amount_words: str | None) -> list[BotLineView]:
    out = []
    for k, ln in enumerate(lines):
        last = k == len(lines) - 1
        slots = {"amount_words": amount_words} if last and amount_words and ln["key"] and \
            ln["key"].startswith("read_back.") else {}  # fmt: skip
        out.append(
            BotLineView(key=ln["key"] or "", text=ln["text"], step=ln["step"], asks=ln["asks"], slots=slots)
        )
    return out


def _stt(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    shown = ("role", "model", "params", "ok", "error", "text", "literal", "cache_hit", "seconds", "attempts",
             "est_credits")  # fmt: skip
    return [{k: r.get(k) for k in shown} for r in event.get("readings", [])]


def _acted_model(event: Mapping[str, Any]) -> str | None:
    role = event.get("acted_on")
    return next((r["model"] for r in event.get("readings", []) if r["role"] == role), None) if role else None


# --- one customer -----------------------------------------------------------------------------------


def choose(customer: Customer, topics: Topics, lines: list[BotLineView], history: Sequence[Said],
           previous_empty: bool) -> Choice:  # fmt: skip
    """The player's choice, or `silence_prompt` right after a turn whose transcript came back empty."""
    if previous_empty and SILENCE in customer.open:
        return Choice(SILENCE, "own", customer.open[SILENCE]["own"], lines[-1].key, True,
                      "the previous turn's transcript came back empty")  # fmt: skip
    return choose_open(customer, topics, LEVEL, CONDITION, lines, history)


def _base(customer: Customer, voice: str) -> dict[str, Any]:
    return {
        "customer_id": customer.id, "arm": "open", "condition": CONDITION, "level": LEVEL,
        "language": customer.language, "kind": customer.kind, "gold_class": customer.gold["class"],
        "record_id": customer.record_id, "writer_model": customer.writer_model_by_arm["open"],
        "second_reading": None, "status": "running", "turns": [], "unmapped": [], "errors": [],
        "final_bot": [], "outcome": None, "speaker_confirmed": None, "degraded_turns": None,
        "unresolved": None, "tier": None, "flags": [], "gaps": [], "referral_basis": None, "summary": None,
        "transcript": None, "finished_utc": None,
        "path": "voice", "session_id": None, "voice": voice,
        "tts": {"model": TTS_MODEL, "language": TTS_LANGUAGE[customer.language], "sample_rate": LINE_RATE},
        "batch": "off: the launcher's null Batch client (0 segments, no request)",
        "case_status": None, "case_failed": [], "case_steps": [], "degraded_turn_ids": [], "models": None,
        "recording_seconds": None, "ended_reason": None, "ledger": None, "resumed": 0,
    }  # fmt: skip


class Caller:
    """One customer's call over HTTP. `http` is an httpx.Client or a Starlette TestClient."""

    def __init__(self, http: Any, speech: Any, customer: Customer, topics: Topics, voice: str,
                 progress: Path, ledger_total: Callable[[], float]) -> None:  # fmt: skip
        self.http, self.speech, self.customer, self.topics, self.voice = http, speech, customer, topics, voice
        self.progress, self.ledger_total = progress, ledger_total
        from samajh.clients.gnani import Timbre

        self.timbre = Timbre(model=TTS_MODEL, voice=voice, language=TTS_LANGUAGE[customer.language],
                             sample_rate=LINE_RATE, container="wav")  # fmt: skip

    def _get(self, step: str, url: str, **kw: Any) -> Any:
        return _checked(step, self.http.get(url, **kw))

    def _post(self, step: str, url: str, **kw: Any) -> Any:
        return _checked(step, self.http.post(url, **kw))

    def _readings_cursor(self) -> int | None:
        r = self.http.get("/p5/readings", params={"since": 10**9})
        return r.json()["next"] if r.status_code == 200 else None

    def _readings_since(self, cursor: int | None) -> list[dict[str, Any]] | None:
        if cursor is None:
            return None
        r = self.http.get("/p5/readings", params={"since": cursor})
        return r.json()["readings"] if r.status_code == 200 else None

    def _state(self, session_id: str) -> dict[str, Any] | None:
        r = self.http.get(f"/p5/sessions/{session_id}/state")
        return r.json().get("state") if r.status_code == 200 else None

    def _voice(self, text: str) -> tuple[bytes, dict[str, Any]]:
        from samajh.clients.errors import CapExceeded, LockTimeout
        from samajh.server.audio import to_line_pcm

        try:
            spoken = self.speech.tts(text, self.timbre)
        except (CapExceeded, LockTimeout) as error:
            raise RunStopped(f"customer tts: {type(error).__name__}") from error
        audio, seconds = to_line_pcm(spoken.audio, LINE_RATE, 30)
        return audio, {"cache_hit": spoken.call.cache_hit, "est_credits": spoken.call.est_credits,
                       "audio_seconds": round(seconds, 3)}  # fmt: skip

    def _turn_record(self, log: Mapping[str, Any], event: Mapping[str, Any], choice: Choice,
                     readings: list[dict[str, Any]] | None, tts: dict[str, Any] | None) -> dict[str, Any]:  # fmt: skip
        asked = _event(log, event["reply_to"])
        return {
            "bot": [{k: ln[k] for k in ("key", "text", "step", "asks")} for ln in dialogue_lines(asked)],
            "reply": asdict(choice), "readings": readings, "degraded": bool(event.get("degraded")),
            "seq": event["seq"], "reply_to": event["reply_to"], "listen": asked.get("listen"),
            "second_reading_asked": asked.get("second_reading"), "transcript": event.get("transcript"),
            "acted_on": event.get("acted_on"), "acted_on_model": _acted_model(event), "stt": _stt(event),
            "readings_agreed": event.get("readings_agreed"), "followed_by": event.get("followed_by"),
            "voiced": tts,
        }  # fmt: skip

    def run(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = json.loads(self.progress.read_text()) if self.progress.is_file() else None
        if saved is None:
            body = {"line_rate": LINE_RATE, "params": {"record": self.customer.record_id,
                                                        "language": self.customer.language}}  # fmt: skip
            saved = {"session_id": None, "turns": [], "unmapped": [], "ledger_before": self.ledger_total(),
                     "resumed": 0}  # fmt: skip
            saved["session_id"] = self._post("create", "/api/sessions", json=body)["session_id"]
            _write_json(self.progress, saved)
        else:
            saved["resumed"] += 1
            _write_json(self.progress, saved)
        sid = saved["session_id"]
        record["session_id"], record["resumed"] = sid, saved["resumed"]
        record["turns"], record["unmapped"] = saved["turns"], saved["unmapped"]
        session = f"/api/sessions/{sid}"
        history = [
            Said(t["reply"]["topic"], t["reply"]["variant"], t["reply"]["text"]) for t in record["turns"]
        ]

        log = self._get("log", session)
        while True:
            done = _customer_events(log)
            # A turn the server took before a crash but the progress file does not hold: recover its record.
            while len(record["turns"]) < len(done):
                event = done[len(record["turns"])]
                prev_empty = bool(record["turns"]) and not (record["turns"][-1]["transcript"] or "").strip()
                lines = views(dialogue_lines(_event(log, event["reply_to"])), None)
                choice = choose(self.customer, self.topics, lines, history, prev_empty)
                turn = self._turn_record(log, event, choice, None, None)
                turn["recovered"] = (
                    "taken by the server before a crash; readings not kept, read-back slot from text"
                )
                record["turns"].append(turn)
                history.append(Said(choice.topic, choice.variant, choice.text))
            if log["status"] != "active":
                break
            if len(record["turns"]) >= MAX_CUSTOMER_TURNS:
                raise RuntimeError(f"the call did not end after {MAX_CUSTOMER_TURNS} customer turns")
            asked = _last_bot(log)
            self._get(f"bot audio {asked['seq']}", f"{session}/audio/bot-{asked['seq']:03d}.wav")
            lines = dialogue_lines(asked)
            words = (
                readback_words(self._state(sid))
                if (lines[-1]["key"] or "").startswith("read_back.")
                else None
            )
            prev_empty = bool(record["turns"]) and not (record["turns"][-1]["transcript"] or "").strip()
            choice = choose(self.customer, self.topics, views(lines, words), history, prev_empty)
            if not choice.mapped:
                record["unmapped"].append({"line_key": choice.line_key, "note": choice.note})
            audio, tts = self._voice(choice.text)
            cursor = self._readings_cursor()
            self._post(f"turn {len(record['turns']) + 1} ({choice.topic})", f"{session}/turns",
                       params={"source": "file", "reply_to": asked["seq"]}, content=audio)  # fmt: skip
            log = self._get("log", session)
            event = _customer_events(log)[len(record["turns"])]
            record["turns"].append(self._turn_record(log, event, choice, self._readings_since(cursor), tts))
            history.append(Said(choice.topic, choice.variant, choice.text))
            saved["turns"], saved["unmapped"] = record["turns"], record["unmapped"]
            _write_json(self.progress, saved)

        last = _last_bot(log)
        if last.get("audio") is None and not log.get("closed") and log.get("ended_reason") == "dialogue":
            self._get(f"bot audio {last['seq']}", f"{session}/audio/bot-{last['seq']:03d}.wav")
        record["final_bot"] = [
            {k: ln[k] for k in ("key", "text", "step", "asks")} for ln in dialogue_lines(last)
        ]
        record["ended_reason"] = log.get("ended_reason")
        state = self._state(sid)
        record["unresolved"] = (state or {}).get("unresolved")
        stt = log.get("stt") or {}
        record["second_reading"] = (
            f"{stt.get('second_model')} {stt.get('second_format')} within {stt.get('second_timeout_s')} s "
            "on turns that may carry a figure"
        )
        case = wait_for_case(self.http, sid)
        self._case_fields(record, case, last)
        record["ledger"] = {
            "before": round(saved["ledger_before"], 6),
            "after": round(self.ledger_total(), 6),
        }
        record["ledger"]["delta"] = round(record["ledger"]["after"] - record["ledger"]["before"], 6)
        return record

    def _case_fields(self, record: dict[str, Any], case: Mapping[str, Any], last: Mapping[str, Any]) -> None:
        record["case_status"] = case.get("status")
        record["case_failed"] = case.get("failed", [])
        record["case_steps"] = case.get("steps", [])
        record["outcome"] = case.get("call_outcome") or last.get("tags", {}).get("outcome")
        record["speaker_confirmed"] = case.get("speaker_confirmed")
        record["degraded_turn_ids"] = case.get("degraded_turns", [])
        record["degraded_turns"] = len(record["degraded_turn_ids"])
        record["models"] = case.get("models")
        record["recording_seconds"] = (case.get("recording") or {}).get("seconds")
        record["transcript"] = case.get("transcript")
        record["summary"] = case.get("summary")
        record["tier"] = case.get("tier")
        if case.get("result"):
            from samajh.types import CaseResult

            result = CaseResult.model_validate(case["result"])
            record["flags"] = [
                {"rule_id": str(f.rule_id), "reason": str(f.reason), "tier": str(f.tier), "basis": str(f.basis),
                 "product_id": f.product_id, "quote": f.quote}
                for f in result.all_flags()
            ]  # fmt: skip
            record["gaps"] = [
                {"rule_id": str(g.rule_id), "reason": str(g.reason), "tier": str(g.tier)}
                for g in result.all_gaps()
            ]
            basis = result.referral_basis
            record["referral_basis"] = str(basis) if basis is not None else None
        if case.get("status") != "ready":
            raise RuntimeError(f"case file {case.get('status')}: failed steps {case.get('failed')}")


def wait_for_case(http: Any, session_id: str, *, timeout: float = 900.0, poll: float = 1.0) -> dict[str, Any]:
    """As `samajh.server.replay.wait_for_case`, with this module's error handling."""
    url = f"/api/sessions/{session_id}/case"
    case = _checked("case", http.post(url))
    deadline = time.monotonic() + timeout
    while case["status"] == "running":
        if time.monotonic() > deadline:
            raise RuntimeError(f"case file not ready after {timeout:g} s")
        time.sleep(poll)
        case = _checked("case", http.get(url))
    return case


def run_customer(http: Any, speech: Any, customer: Customer, topics: Topics, voice: str, out: Path,
                 ledger_total: Callable[[], float]) -> dict[str, Any] | None:  # fmt: skip
    """One call to its call file. Returns the record written, or None when the call file already exists.
    Raises `RunStopped` (no file written) for a run-level stop."""
    path = out / "calls" / call_name(customer.id)
    if path.exists():
        return None
    record = _base(customer, voice)
    caller = Caller(
        http, speech, customer, topics, voice, out / "progress" / f"{customer.id}.json", ledger_total
    )
    try:
        caller.run(record)
        record["status"] = "ok"
    except RunStopped:
        raise
    except Exception as error:
        if _transport_error(error):
            raise RunStopped(f"server unreachable: {type(error).__name__}") from error
        record["status"] = "no_result"
        record["errors"].append({"error": repr(error), "traceback": traceback.format_exc()})
        try:
            if record["session_id"] and record["ledger"] is None:
                progress = json.loads(caller.progress.read_text())
                before = progress["ledger_before"]
                record["ledger"] = {
                    "before": before,
                    "after": ledger_total(),
                    "delta": ledger_total() - before,
                }
        except (OSError, ValueError, KeyError):
            pass
    record["finished_utc"] = _now()
    _write_json(path, record)
    return record


def _transport_error(error: BaseException) -> bool:
    try:
        import httpx
    except ImportError:
        return False
    return isinstance(error, httpx.TransportError)


# --- the run ----------------------------------------------------------------------------------------


def ordered(customers: Mapping[str, Customer]) -> list[str]:
    ids = sorted(customers)
    random.Random(ORDER_SEED).shuffle(ids)
    return ids


def smoke_ids(customers: Mapping[str, Customer], voices: Mapping[str, str]) -> list[str]:
    """hi and hi-en, a female and a male voice, one third party: the first in id order of each slot."""
    by_id = sorted(customers.values(), key=lambda c: c.id)
    talk = [c for c in by_id if not c.procedural]

    def first(pred: Callable[[Customer], bool]) -> str:
        return next(c.id for c in talk if pred(c))

    picks = [
        first(lambda c: c.language == "hi" and c.speaker["gender"] == "f"),
        first(lambda c: c.language == "hi-en" and c.speaker["gender"] == "m"),
        first(lambda c: c.language == "hi" and c.speaker["gender"] == "m"),
        next(c.id for c in by_id if c.kind == "third_party" and c.language == "hi-en"),
    ]
    return picks


def ledger_rows_and_total(path: Path | None = None) -> tuple[int, float]:
    from samajh.clients._runtime import Ledger, state_dir

    # Gnani rows only, as `python -m samajh.clients.gnani ledger` counts them: an LLM-only run beside
    # this one writes OpenRouter rows and does not use the account's slot.
    rows = [e for e in Ledger(path or state_dir() / "ledger.jsonl").entries() if e.provider == "gnani"]
    return len(rows), sum(e.est_credits for e in rows)


def lock_held(lock_path: Path) -> bool:
    import filelock

    lock = filelock.FileLock(lock_path, thread_local=False, fallback_to_soft=False)
    try:
        lock.acquire(timeout=0)
    except filelock.Timeout:
        return True
    lock.release()
    return False


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def idle_check(*, lock_path: Path, rows: Callable[[], int], wait: float = 30.0,
               sleep: Callable[[float], None] = time.sleep, phone_port: int | None = PHONE_PORT) -> list[str]:  # fmt: skip
    """Why the account is not idle (RUNNER-PLAN Part 2 §4 item 2); [] when it is."""
    problems = []
    if phone_port is not None and port_open(phone_port):
        problems.append(f"something listens on port {phone_port} (the phone)")
    if lock_held(lock_path):
        problems.append(f"a process holds {lock_path}")
    before = rows()
    sleep(wait)
    after = rows()
    if after != before:
        problems.append(f"the ledger grew from {before} to {after} rows in {wait:g} s")
    return problems


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.rstrip("\n")


def run(http: Any, speech: Any, ids: Sequence[str], *, out: Path, ceiling: float, baseline: float,
        ledger_total: Callable[[], float], customers: Mapping[str, Customer] | None = None,
        topics: Topics | None = None, voices: Mapping[str, str] | None = None,
        log: Callable[[str], None] = print) -> dict[str, Any]:  # fmt: skip
    """Every customer in `ids`, in order, until done or the ledger has grown by `ceiling` since `baseline`."""
    customers = customers or load_customers()
    topics = topics or load_topics()
    voices = voices or assign_voices(customers)
    counts = {"done": 0, "skipped": 0, "no_result": 0, "not_started": 0, "stopped": None}
    for k, cid in enumerate(ids):
        if (out / "calls" / call_name(cid)).exists():
            counts["skipped"] += 1
            continue
        spent = ledger_total() - baseline
        if spent >= ceiling:
            counts["stopped"] = f"ceiling: the ledger grew by {spent:.2f} >= {ceiling:g}"
            counts["not_started"] = len(ids) - k
            break
        try:
            record = run_customer(http, speech, customers[cid], topics, voices[cid], out, ledger_total)
        except RunStopped as stop:
            counts["stopped"] = str(stop)
            counts["not_started"] = len(ids) - k
            break
        counts["done"] += 1
        counts["no_result"] += record["status"] != "ok"
        delta = (record.get("ledger") or {}).get("delta")
        log(f"{cid} {record['language']} {record['voice']}: outcome={record['outcome']} tier={record['tier']} "
            f"status={record['status']} turns={len(record['turns'])} credits={delta}")  # fmt: skip
    return counts


# --- dry run ----------------------------------------------------------------------------------------


def _tts_cached(text: str, voice: str, language: str) -> bool:
    """Whether the shared Gnani cache already holds this Timbre request (the client's key, read locally)."""
    from samajh.clients._runtime import cache_key, state_dir
    from samajh.clients.gnani.client import TTS_PATH

    body = {"text": text, "voice": voice, "model": TTS_MODEL, "language": language, "speed": 1.0,
            "audio_config": {"sample_rate": LINE_RATE, "container": "wav"}}  # fmt: skip
    key = cache_key(
        "gnani.tts.v1", {"base_url": "https://api.vachana.ai", "path": TTS_PATH, "body": body}, b""
    )
    return (state_dir() / "cache" / "gnani" / key[:2] / f"{key}.json").is_file()


def simulate(customer: Customer, topics: Topics) -> dict[str, Any]:
    """The call on text with the word lists alone (no network): the replies the chooser gives, the bot
    lines, and which turns ask for a second reading. The live call reads with the LLM classifier too and
    hears STT text, so its path can differ: an approximation for the estimate."""
    from samajh import dialogue as core
    from samajh.server.samajh_dialogue import spoken_pieces
    from samajh.types import Language

    call = load_record(customer.record_id, customer.data_dir)
    language = Language(customer.language)
    state, said = core.start(
        call.record, language, lender_name=call.lender_name, call_id=f"dry-{customer.id}"
    )
    interpreter = core.RuleInterpreter()
    history: list[Said] = []
    replies, bot = [], []
    for _ in range(MAX_CUSTOMER_TURNS):
        bot += [p for ln in said.lines for p in spoken_pieces(ln.text)]
        lines = [BotLineView(key=ln.key, text=ln.text, step=str(ln.step),
                             asks=str(ln.asks) if ln.asks is not None else None, slots=dict(ln.slots))
                 for ln in said.lines]  # fmt: skip
        second = str(core.expecting(state.position).value) in ("amount", "confirmation")
        choice = choose_open(customer, topics, LEVEL, CONDITION, lines, history)
        replies.append({"line_key": choice.line_key, "topic": choice.topic, "variant": choice.variant,
                        "text": choice.text, "second_reading": second, "mapped": choice.mapped})  # fmt: skip
        history.append(Said(choice.topic, choice.variant, choice.text))
        state, nxt = core.step(state, choice.text, second_reading=None, interpreter=interpreter)
        if isinstance(nxt, core.EndOfCall):
            bot += [p for ln in nxt.utterance.lines for p in spoken_pieces(ln.text)]
            return {"replies": replies, "bot": bot, "outcome": str(nxt.outcome)}
        said = nxt
    return {"replies": replies, "bot": bot, "outcome": "no end"}


# The `own` replies a static estimate voices, by gold outcome (used when neither a text-run call file nor
# the word-list simulation reaches the customer's expected outcome).
STATIC_TOPICS: dict[str, tuple[str, ...]] = {
    "completed": ("is_this_you", "can_we_talk", "year_of_birth", "what_did_you_take", "what_is_it", "how_much",
                  "figure_read_back_right", "how_paid", "how_often", "needed_or_choice", "where_to_take_it_from",
                  "what_it_gives", "how_long", "can_cancel", "money_back", "what_you_agreed_to"),
    "wrong_party": ("is_this_you", "is_this_you_again"),
    "declined": ("is_this_you", "can_we_talk", "year_of_birth"),
    "call_back_later": ("is_this_you", "can_we_talk", "when_to_call"),
    "language_switch": ("is_this_you", "can_we_talk"),
}  # fmt: skip
FIGURE_TOPICS_DRY = frozenset({"how_much", "figure_read_back_right", "what_it_gives", "say_amount_again"})
STATIC_BOT_CREDITS = 0.33  # RUNNER-PLAN Part 2 §3: a new name's lines, per customer, for a static row
LENDER_LINES_CREDITS = 4.0  # RUNNER-PLAN Part 1: the second lender name, once, if any row is static


def _from_text_run(path: Path) -> dict[str, Any]:
    call = json.loads(path.read_text(encoding="utf-8"))
    replies = [{"line_key": t["reply"]["line_key"], "topic": t["reply"]["topic"], "variant": t["reply"]["variant"],
                "text": t["reply"]["text"], "mapped": t["reply"]["mapped"],
                "second_reading": t["bot"][-1]["key"].startswith(("premium.", "cover.", "read_back."))}
               for t in call["turns"]]  # fmt: skip
    bot = [ln["text"] for t in call["turns"] for ln in t["bot"]] + [
        ln["text"] for ln in call.get("final_bot", [])
    ]
    return {
        "replies": replies,
        "bot": bot,
        "outcome": call.get("outcome"),
        "source": f"text run {path.parent.parent.name}",
    }


def _static(c: Customer) -> dict[str, Any]:
    topics = STATIC_TOPICS[c.gold["expected_outcome"]]
    replies = [{"line_key": "?", "topic": t, "variant": "own", "text": c.open[t]["own"], "mapped": True,
                "second_reading": t in FIGURE_TOPICS_DRY} for t in topics if t in c.open]  # fmt: skip
    return {"replies": replies, "bot": [], "outcome": "static", "source": "static own texts"}


def dry_run(ids: Sequence[str], ceiling: float, show_texts: bool = True,
            text_runs: Sequence[Path] = (), data: Path | None = None) -> dict[str, Any]:  # fmt: skip
    from samajh.clients._runtime import load_defaults

    rates = load_defaults()["gnani"]
    tts_rate, stt_rate = rates["tts_credits_per_char"], rates["stt_credits_per_second"]
    data = data or resolve_data(None)
    customers, topics = load_customers(data), load_topics(data)
    voices = assign_voices(customers)
    bot_voice, bot_seen = "Shivani", set()
    total = {"customer_tts_chars": 0, "customer_tts_chars_uncached": 0, "bot_tts_chars_uncached": 0,
             "stt_seconds": 0.0, "replies": 0, "unmapped": 0, "simulation_failed": [],
             "sources": {}, "static_bot_allowance": 0.0, "static_rows": 0}  # fmt: skip
    rows = []
    for cid in ids:
        c = customers[cid]
        lang = TTS_LANGUAGE[c.language]
        sim = None
        for run_dir in text_runs:
            path = run_dir / "calls" / call_name(cid)
            if path.is_file() and json.loads(path.read_text()).get("status") == "ok":
                sim = _from_text_run(path)
                break
        if sim is None:
            try:
                sim = simulate(c, topics) | {"source": "word-list simulation"}
            except Exception as error:  # noqa: BLE001 - the dialogue may be mid-edit: fall back and say so
                total["simulation_failed"].append(f"{cid}: {error!r}"[:200])
            if sim is None or sim["outcome"] != c.gold["expected_outcome"]:
                opening_bot = sim["bot"] if sim else []
                sim = _static(c)
                sim["bot"] = opening_bot  # the simulated opening's lines (the name lines) are still voiced
                total["static_rows"] += 1
                if not opening_bot:  # no simulated opening: the plan's allowance for the name lines
                    total["static_bot_allowance"] += STATIC_BOT_CREDITS
        total["sources"][sim["source"]] = total["sources"].get(sim["source"], 0) + 1
        chars = sum(len(r["text"]) for r in sim["replies"])
        uncached = sum(
            len(r["text"]) for r in sim["replies"] if not _tts_cached(r["text"], voices[cid], lang)
        )
        seconds = sum(
            len(r["text"]) / CHARS_PER_SECOND * (2 if r["second_reading"] else 1) for r in sim["replies"]
        )
        bot_new = 0
        for text in sim["bot"]:
            if (text, lang) not in bot_seen and not _tts_cached(text, bot_voice, lang):
                bot_new += len(text)
            bot_seen.add((text, lang))
        credits = (uncached + bot_new) * tts_rate + seconds * stt_rate
        rows.append({"customer_id": cid, "language": c.language, "kind": c.kind,
                     "gender": c.speaker["gender"], "voice": voices[cid], "turns": len(sim["replies"]),
                     "outcome_on_text": sim["outcome"], "reply_chars": chars, "reply_chars_uncached": uncached,
                     "bot_chars_uncached": bot_new, "stt_seconds_assumed": round(seconds, 1),
                     "est_credits": round(credits, 3), "replies": sim["replies"]})  # fmt: skip
        total["customer_tts_chars"] += chars
        total["customer_tts_chars_uncached"] += uncached
        total["bot_tts_chars_uncached"] += bot_new
        total["stt_seconds"] += seconds
        total["replies"] += len(sim["replies"])
        total["unmapped"] += sum(not r["mapped"] for r in sim["replies"])
    tts_credits = (total["customer_tts_chars_uncached"] + total["bot_tts_chars_uncached"]) * tts_rate
    stt_credits = total["stt_seconds"] * stt_rate
    allowance = total["static_bot_allowance"] + (LENDER_LINES_CREDITS if total["static_rows"] else 0.0)
    summary = total | {
        "customers": len(ids), "stt_seconds": round(total["stt_seconds"], 1),
        "static_bot_allowance": round(allowance, 2),
        "est_tts_credits": round(tts_credits, 2), "est_stt_credits": round(stt_credits, 2),
        "est_credits_total": round(tts_credits + stt_credits + allowance, 2), "ceiling": ceiling,
        "rates": {"tts_per_char": tts_rate, "stt_per_second": stt_rate, "chars_per_second": CHARS_PER_SECOND},
        "batch": "off (0 credits)",
        "notes": "replies per customer from, in order: a text-run call file (--text-run), the word-list "
                 "simulation when it reaches the gold outcome, else the static own texts of STATIC_TOPICS "
                 "(plus the plan's allowance for name and lender lines). The live path (LLM classifier, STT "
                 "text) can differ. STT assumed uncached at 12 characters a second, both readings counted on "
                 "figure turns.",
    }  # fmt: skip
    for r in rows:
        print(f"{r['customer_id']} {r['language']:5} {r['kind']:17} {r['gender']} {r['voice']:8} "
              f"turns={r['turns']:2} chars={r['reply_chars']:4} new_bot_chars={r['bot_chars_uncached']:4} "
              f"est={r['est_credits']:.2f} text_outcome={r['outcome_on_text']}")  # fmt: skip
        if show_texts:
            for rep in r["replies"]:
                print(f"    {rep['line_key']:28} {rep['topic']}/{rep['variant']}: {rep['text']}")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return {"summary": summary, "rows": rows}


# --- main -------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--customers", default="", help="comma-separated ids; all 60 when empty")
    parser.add_argument(
        "--ceiling", type=float, default=None, help=f"default {DEFAULT_CEILING:g}, smoke {SMOKE_CEILING:g}"
    )
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-texts", action="store_true", help="dry run: print the summary rows only")
    parser.add_argument(
        "--text-run",
        type=Path,
        action="append",
        default=[],
        help="dry run: take each customer's replies from this text run's call files when present",
    )
    parser.add_argument("--data", default="data/p5", help="the frozen data directory (data/p5, data/p5b)")
    args = parser.parse_args(argv)
    if ":8085" in args.url:
        parser.error("port 8085 belongs to the phone; the P5 launcher runs on 8095")

    data = resolve_data(args.data)
    frozen = check_frozen(data)  # fails closed before anything else
    customers = load_customers(data)
    voices = assign_voices(customers)
    ceiling = args.ceiling if args.ceiling is not None else (SMOKE_CEILING if args.smoke else DEFAULT_CEILING)
    if args.smoke:
        ids = smoke_ids(customers, voices)
    elif args.customers:
        ids = [x for x in args.customers.split(",") if x]
        unknown = sorted(set(ids) - set(customers))
        if unknown:
            parser.error(f"unknown customers {unknown}")
    else:
        ids = ordered(customers)
    if args.dry_run:
        dry_run(ids, ceiling, show_texts=not args.no_texts, text_runs=args.text_run, data=data)
        return 0
    if args.out is None:
        parser.error("--out is required unless --dry-run")

    from samajh.clients._runtime import state_dir

    problems = idle_check(lock_path=state_dir() / "gnani.lock", rows=lambda: ledger_rows_and_total()[0])
    if problems:
        print(json.dumps({"refused": problems}), file=sys.stderr)
        return 3

    import httpx

    from samajh.server.speech import PATIENT, live_client

    manifest_path = args.out / "manifest.json"
    runs = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    _, before = ledger_rows_and_total()
    baseline = runs[0]["ledger_before"] if runs else before
    # This process's own Timbre calls stop at the same cap the launcher sets.
    import os

    from samajh.clients.gnani.client import credit_cap_from_env

    os.environ["GNANI_CREDIT_CAP"] = str(round(min(baseline + ceiling, credit_cap_from_env()), 4))
    speech = live_client(PATIENT)
    http = httpx.Client(base_url=args.url, timeout=600.0)
    health = _checked("health", http.get("/api/health"))
    if "samajh" not in health.get("dialogues", []):
        print(json.dumps({"refused": ["the server at --url has no samajh dialogue"]}), file=sys.stderr)
        return 3
    if http.get("/p5/readings").status_code != 200:
        print(json.dumps({"refused": ["the server at --url is not eval/p5/serve.py"]}), file=sys.stderr)
        return 3
    manifest: dict[str, Any] = {
        "started_utc": _now(), "path": "voice", "arm": "open", "level": LEVEL, "condition": CONDITION,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_status_samajh_prompts": _git("status", "--porcelain", "samajh", "data/prompts"),
        "data_dir": str(data), "harness_sha256": harness_hashes(),
        "frozen_digests": frozen, "url": args.url, "server_models": health.get("models"),
        "customers": list(ids), "order_seed": None if (args.smoke or args.customers) else ORDER_SEED,
        "smoke": args.smoke, "voices": {cid: voices[cid] for cid in ids},
        "voice_rule": "voices.py (RUNNER-PLAN Part 1 'Voices')", "tts_model": TTS_MODEL,
        "ledger_before": round(before, 6), "run_baseline": round(baseline, 6), "credit_ceiling": ceiling,
        "client_credit_cap": float(os.environ["GNANI_CREDIT_CAP"]), "batch": "off (null client in serve.py)",
    }  # fmt: skip
    try:
        counts = run(http, speech, ids, out=args.out, ceiling=ceiling, baseline=baseline,
                     ledger_total=lambda: ledger_rows_and_total()[1], customers=customers,
                     topics=load_topics(data), voices=voices)  # fmt: skip
    finally:
        http.close()
        _, after = ledger_rows_and_total()
        manifest["ledger_after"] = round(after, 6)
        manifest["ledger_delta_this_invocation"] = round(after - before, 6)
        manifest["ledger_delta_run"] = round(after - baseline, 6)
        manifest["finished_utc"] = _now()
        first_case = next((json.loads(p.read_text()) for p in sorted((args.out / "calls").glob("*.json"))
                           if json.loads(p.read_text()).get("models")), None) if (args.out / "calls").is_dir() else None  # fmt: skip
        manifest["models"] = {"dialogue_reads_first": ((first_case or {}).get("models") or {}).get("dialogue_reads_first"),
                              "case_models": (first_case or {}).get("models")}  # fmt: skip
        runs.append(manifest)
        _write_json(manifest_path, runs)
    manifest.update(counts)
    _write_json(manifest_path, runs)
    print(json.dumps({k: manifest.get(k) for k in ("done", "skipped", "no_result", "not_started", "stopped",
                                                    "ledger_delta_this_invocation", "ledger_delta_run")}))  # fmt: skip
    return 2 if counts["stopped"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
