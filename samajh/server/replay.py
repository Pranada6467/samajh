"""Run one whole call from audio files, through the HTTP API, as the phone does, to its case file.

    uv run python -m samajh.server.replay DIR [--url http://127.0.0.1:8085] [--out OUT]
        [--dialogue samajh] [--param k=v ...] [--line-rate 8000] [--no-case]

DIR holds the customer's turns. With a `call.json` in DIR the call is scripted:

    {"params": {"record": "hero", "language": "hi"},
     "turns": [{"file": "01.wav", "answers": "right_party.ask", "text": "हाँ जी, बोल रहा हूँ"}, ...]}

`answers` (optional) is the key of the bot line the turn replies to; when the bot asked something
else the replay stops with `script_drift` instead of answering the wrong question. `text` is
what the audio says, for the reader; the server never sees it. A turn with no `file` is silence.
Without `call.json` the files of DIR are the turns in name order (an empty file or one named
`*.none` is silence), and `--param` gives the session params.

With `--out` the run is resumable: `OUT/replay.json` names the session, and a rerun after a crash
or a stopped server continues that call where it stopped (a turn sent twice is answered once),
then waits for the case file and writes it to `OUT/case.json`. Without `--url` the app runs in
this process with the patient client profile. Every Gnani and LLM call is cached, so a rerun of a
finished call costs nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

from samajh.server.sessionlog import BotEvent, CustomerEvent, ErrorEvent, SessionLog


class ReplayFailed(Exception):
    """A step of the call was refused. `error` is the server's error object."""

    def __init__(self, step: str, status: int, error: Mapping[str, Any]) -> None:
        self.step, self.status, self.error = step, status, dict(error)
        super().__init__(f"{step}: HTTP {status} {error.get('code')}: {error.get('message')}")


@dataclass(frozen=True)
class ScriptTurn:
    file: Path | None  # None: the customer says nothing
    answers: str | None = None  # the key of the bot line this turn replies to, when checked
    text: str | None = None  # what the audio says; never sent


@dataclass(frozen=True)
class Script:
    turns: tuple[ScriptTurn, ...]
    params: dict[str, str] = field(default_factory=dict)
    dialogue: str | None = None  # None: the server's default

    def fingerprint(self) -> str:
        """Changes when a turn's audio, order or the params change, so a resume never mixes calls."""
        digest = hashlib.sha256(json.dumps([self.params, self.dialogue], sort_keys=True).encode())
        for turn in self.turns:
            digest.update(b"|" + (turn.file.read_bytes() if turn.file else b"none"))
        return digest.hexdigest()[:16]


def turn_files(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".") and p.name != "call.json"
    )


def load_script(
    directory: Path, *, params: Mapping[str, str] | None = None, dialogue: str | None = None
) -> Script:
    """`call.json` if DIR has one (its params win over `params`), else the files in name order."""
    manifest = directory / "call.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        turns = tuple(
            ScriptTurn(
                file=directory / t["file"] if t.get("file") else None,
                answers=t.get("answers"),
                text=t.get("text"),
            )
            for t in data["turns"]
        )
        return Script(
            turns, dict(params or {}) | dict(data.get("params", {})), data.get("dialogue", dialogue)
        )
    turns = tuple(
        ScriptTurn(file=None if p.suffix == ".none" or p.stat().st_size == 0 else p)
        for p in turn_files(directory)
    )
    return Script(turns, dict(params or {}), dialogue)


@dataclass(frozen=True)
class ReplayTurn:
    seq: int
    file: str | None
    transcript: str
    readings: tuple[dict[str, Any], ...]  # model, ok, text, cache_hit, seconds of each reading
    stt_ms: float | None
    dialogue_ms: float | None


@dataclass
class ReplayResult:
    session_id: str
    turns: tuple[ReplayTurn, ...]
    log: SessionLog
    case: dict[str, Any] | None = None

    @property
    def recording_seconds(self) -> float | None:
        return self.log.recording.seconds if self.log.recording else None

    @property
    def est_credits(self) -> float:
        """Gnani credits the turns and the bot's lines cost (estimates; cache hits cost 0).
        Batch is not in the session log: see the case file and the client ledger."""
        total = sum(
            r.est_credits for e in self.log.events if isinstance(e, CustomerEvent) for r in e.readings
        )
        total += sum(
            line.tts.est_credits
            for e in self.log.events
            if isinstance(e, BotEvent)
            for line in e.lines
            if line.tts
        )
        return round(total, 6)

    def summary(self) -> dict[str, Any]:
        case = self.case or {}
        return {
            "session_id": self.session_id,
            "status": self.log.status,
            "ended_reason": self.log.ended_reason,
            "turns": [asdict(turn) for turn in self.turns],
            "recording_seconds": self.recording_seconds,
            "est_credits": self.est_credits,
            "case": None
            if not case
            else {
                "status": case.get("status"),
                "failed": case.get("failed"),
                "call_outcome": case.get("call_outcome"),
                "tier": case.get("tier"),
                "lines": [
                    {"tier": line["tier"], "title": line["title"], "quote": line["quote"]}
                    for line in (case.get("summary") or {}).get("lines", [])
                ],
            },
        }


def _checked(step: str, response: httpx.Response) -> httpx.Response:
    if response.is_success:
        return response
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = {"code": "not_json", "message": response.text[:200]}
    raise ReplayFailed(step, response.status_code, error)


def _log(http: httpx.Client, session: str) -> SessionLog:
    return SessionLog.model_validate(_checked("log", http.get(session)).json())


def _open_prompt(log: SessionLog) -> BotEvent:
    current = [e for e in log.events if not isinstance(e, ErrorEvent) and not e.superseded]
    last = current[-1]
    assert isinstance(last, BotEvent)
    return last


def _done(log: SessionLog) -> list[CustomerEvent]:
    return [e for e in log.events if isinstance(e, CustomerEvent) and not e.superseded]


def _turn(event: CustomerEvent, file: str | None) -> ReplayTurn:
    shown = ("role", "model", "ok", "error", "text", "cache_hit", "seconds")
    return ReplayTurn(
        seq=event.seq,
        file=file,
        transcript=event.transcript,
        readings=tuple({k: getattr(r, k) for k in shown} for r in event.readings),
        stt_ms=event.latency.stt_ms + event.latency.second_stt_ms if event.latency else None,
        dialogue_ms=event.latency.dialogue_ms if event.latency else None,
    )


def wait_for_case(
    http: httpx.Client,
    session_id: str,
    *,
    timeout: float = 900.0,
    poll: float = 1.0,
    sleep: Callable = time.sleep,
) -> dict[str, Any]:
    """Start the after-call job (or find it) and wait until it is ready or failed."""
    url = f"/api/sessions/{session_id}/case"
    case = _checked("case", http.post(url)).json()
    deadline = time.monotonic() + timeout
    while case["status"] == "running":
        if time.monotonic() > deadline:
            raise ReplayFailed(
                "case", 504, {"code": "case_timeout", "message": f"not ready after {timeout:g} s"}
            )
        sleep(poll)
        case = _checked("case", http.get(url)).json()
    return case


def replay_call(
    http: httpx.Client,
    script: Script | Sequence[Path],
    *,
    line_rate: int = 8000,
    dialogue: str | None = None,
    params: Mapping[str, str] | None = None,
    out: Path | None = None,
    case: bool = False,
    case_timeout: float = 900.0,
) -> ReplayResult:
    """Raises `ReplayFailed` at the first step the server refuses. Turns left over when the
    dialogue ends the call are not sent; if the turns run out first, the caller hangs up.
    With `out`, a rerun continues the call `out/replay.json` names."""
    if not isinstance(script, Script):
        script = Script(
            tuple(ScriptTurn(None if p.suffix == ".none" or p.stat().st_size == 0 else p) for p in script),
            dict(params or {}),
            dialogue,
        )
    progress = out / "replay.json" if out else None
    fingerprint = script.fingerprint()
    session_id: str | None = None
    if progress is not None and progress.is_file():
        saved = json.loads(progress.read_text())
        if saved.get("fingerprint") == fingerprint:
            session_id = saved["session_id"]
    if session_id is None:
        body: dict[str, Any] = {"line_rate": line_rate, "params": script.params}
        if script.dialogue is not None:
            body["dialogue"] = script.dialogue
        session_id = _checked("create", http.post("/api/sessions", json=body)).json()["session_id"]
        if progress is not None:
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(json.dumps({"session_id": session_id, "fingerprint": fingerprint}))
    session = f"/api/sessions/{session_id}"

    log = _log(http, session)
    taken = len(_done(log))
    for index in range(taken, len(script.turns)):
        if log.status != "active":
            break
        asked = _open_prompt(log)
        _checked(f"bot audio {asked.seq}", http.get(f"{session}/audio/bot-{asked.seq:03d}.wav"))
        turn = script.turns[index]
        name = turn.file.name if turn.file else "silence"
        step = f"turn {index + 1} ({name})"
        key = asked.lines[-1].key if asked.lines else None
        if turn.answers is not None and turn.answers != key:
            http.post(f"{session}/end", json={"reason": "hangup"})
            raise ReplayFailed(
                step,
                409,
                {
                    "code": "script_drift",
                    "message": f"the bot asked {key!r}, the script answers {turn.answers!r}",
                },
            )
        audio = turn.file.read_bytes() if turn.file else b""
        source = "file" if audio else "none"
        sent = http.post(f"{session}/turns", params={"source": source, "reply_to": asked.seq}, content=audio)
        if not sent.is_success and progress is None:
            # Without a progress file nobody can continue this call: do not leave it in progress.
            http.post(f"{session}/end", json={"reason": "hangup"})
        _checked(step, sent)
        log = _log(http, session)
    if log.status == "active":
        asked = _open_prompt(log)
        _checked(f"bot audio {asked.seq}", http.get(f"{session}/audio/bot-{asked.seq:03d}.wav"))
        _checked("end", http.post(f"{session}/end", json={"reason": "hangup"}))
    else:
        last = _open_prompt(log)
        if last.audio is None and not log.closed and log.ended_reason == "dialogue":
            _checked(f"bot audio {last.seq}", http.get(f"{session}/audio/bot-{last.seq:03d}.wav"))
    log = _log(http, session)
    files = [t.file.name if t.file else None for t in script.turns]
    turns = tuple(_turn(e, files[i] if i < len(files) else None) for i, e in enumerate(_done(log)))
    result = ReplayResult(session_id=session_id, turns=turns, log=log)
    if case:
        result.case = wait_for_case(http, session_id, timeout=case_timeout)
        result.log = _log(http, session)
        if out is not None:
            (out / "case.json").write_text(json.dumps(result.case, ensure_ascii=False, indent=2))
    return result


def _param(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not (key and sep):
        raise argparse.ArgumentTypeError("expected k=v")
    return key, value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m samajh.server.replay", description=__doc__.split("\n")[0]
    )
    parser.add_argument("dir", type=Path, help="directory of turn audio, with an optional call.json")
    parser.add_argument("--url", help="a running server; without it the app runs in this process")
    parser.add_argument(
        "--out", type=Path, help="where replay.json and case.json go; makes the run resumable"
    )
    parser.add_argument("--dialogue", default=None, help="default: call.json's, else the server's default")
    parser.add_argument("--line-rate", type=int, default=8000)
    parser.add_argument("--param", type=_param, action="append", default=[], metavar="k=v")
    parser.add_argument("--no-case", action="store_true", help="stop when the call ends; make no case file")
    parser.add_argument("--case-timeout", type=float, default=900.0)
    args = parser.parse_args(argv)
    if not args.dir.is_dir():
        parser.error(f"{args.dir} is not a directory")
    script = load_script(args.dir, params=dict(args.param), dialogue=args.dialogue)

    session_root: Path | None = None
    if args.url:
        http = httpx.Client(base_url=args.url, timeout=300.0)
    else:
        from starlette.testclient import TestClient

        from samajh.clients._runtime import state_dir
        from samajh.server.app import create_app

        session_root = state_dir() / "sessions"
        http = TestClient(create_app(profile="patient", web_dir=None))
    try:
        with http:
            result = replay_call(
                http,
                script,
                line_rate=args.line_rate,
                out=args.out,
                case=not args.no_case,
                case_timeout=args.case_timeout,
            )
    except ReplayFailed as failed:
        print(
            json.dumps({"failed": failed.step, "status": failed.status, "error": failed.error}),
            file=sys.stderr,
        )
        return 1
    except httpx.HTTPError as exc:
        print(json.dumps({"failed": "http", "error": type(exc).__name__}), file=sys.stderr)
        return 1
    summary = result.summary()
    # Only known when the app ran here; a remote server keeps its sessions under its own state.
    summary["session_dir"] = str(session_root / result.session_id) if session_root else None
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.case is None or result.case.get("status") == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
