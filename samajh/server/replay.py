"""Run one whole call from audio files, through the HTTP API, exactly as the phone does.

    uv run python -m samajh.server.replay DIR [--url http://127.0.0.1:8085] [--dialogue stub]
        [--line-rate 8000] [--stt-model prisma-v3.0] [--param k=v ...]

The files of DIR are the customer's turns in name order; an empty file, or one named `*.none`,
is a turn in which nothing was said. Without `--url` the app runs in this process with the
patient client profile. Rerunning costs nothing: the Gnani client caches every call.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from samajh.server.sessionlog import BotEvent, CustomerEvent, SessionLog


class ReplayFailed(Exception):
    """A step of the call was refused. `error` is the server's error object."""

    def __init__(self, step: str, status: int, error: Mapping[str, Any]) -> None:
        self.step, self.status, self.error = step, status, dict(error)
        super().__init__(f"{step}: HTTP {status} {error.get('code')}: {error.get('message')}")


@dataclass(frozen=True)
class ReplayTurn:
    seq: int
    file: str
    transcript: str
    stt_ms: float
    cache_hit: bool | None  # None when nothing was said, so nothing was transcribed
    attempts: int | None


@dataclass(frozen=True)
class ReplayResult:
    session_id: str
    turns: tuple[ReplayTurn, ...]
    recording_seconds: float | None
    est_credits: float
    log: SessionLog

    def summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.log.status,
            "ended_reason": self.log.ended_reason,
            "turns": [asdict(turn) for turn in self.turns],
            "recording_seconds": self.recording_seconds,
            "est_credits": self.est_credits,
        }


def _checked(step: str, response: httpx.Response) -> httpx.Response:
    if response.is_success:
        return response
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = {"code": "not_json", "message": response.text[:200]}
    raise ReplayFailed(step, response.status_code, error)


def replay_call(
    http: httpx.Client,
    turns: Sequence[Path],
    *,
    dialogue: str = "stub",
    line_rate: int = 8000,
    stt_model: str = "prisma-v3.0",
    params: Mapping[str, str] | None = None,
) -> ReplayResult:
    """Raises `ReplayFailed` at the first step the server refuses. Files left over when the
    dialogue ends the call are not sent; if the files run out first, the caller hangs up."""
    body = {
        "dialogue": dialogue,
        "line_rate": line_rate,
        "stt_model": stt_model,
        "params": dict(params or {}),
    }
    created = _checked("create", http.post("/api/sessions", json=body)).json()
    session = f"/api/sessions/{created['session_id']}"
    bot = created["bot"]
    done: list[ReplayTurn] = []
    for path in turns:
        _checked(f"bot audio {bot['seq']}", http.get(bot["audio_url"]))
        audio = b"" if path.suffix == ".none" else path.read_bytes()
        source = "file" if audio else "none"
        step = f"turn {len(done) + 1} ({path.name})"
        sent = http.post(f"{session}/turns", params={"source": source, "reply_to": bot["seq"]}, content=audio)
        if not sent.is_success:
            # Do not leave a call that will never continue marked as in progress.
            http.post(f"{session}/end", json={"reason": "hangup"})
        answer = _checked(step, sent).json()
        customer, bot = answer["customer"], answer["bot"]
        stt = customer["stt"] or {}
        done.append(
            ReplayTurn(
                seq=customer["seq"],
                file=path.name,
                transcript=customer["transcript"],
                stt_ms=customer["latency"]["stt_ms"],
                cache_hit=stt.get("cache_hit"),
                attempts=stt.get("attempts"),
            )
        )
        if answer["ended"]:
            break
    _checked(f"bot audio {bot['seq']}", http.get(bot["audio_url"]))
    if not bot["end_call"]:
        _checked("end", http.post(f"{session}/end", json={"reason": "hangup"}))
    log = SessionLog.model_validate(_checked("log", http.get(session)).json())
    calls = [e.stt for e in log.events if isinstance(e, CustomerEvent)]
    calls += [e.tts for e in log.events if isinstance(e, BotEvent)]
    return ReplayResult(
        session_id=log.session_id,
        turns=tuple(done),
        recording_seconds=log.recording.seconds if log.recording else None,
        est_credits=round(sum(call.est_credits for call in calls if call is not None), 6),
        log=log,
    )


def turn_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.is_file() and not p.name.startswith("."))


def _param(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not (key and sep):
        raise argparse.ArgumentTypeError("expected k=v")
    return key, value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m samajh.server.replay", description=__doc__.split("\n")[0]
    )
    parser.add_argument("dir", type=Path, help="directory of turn audio files, sent in name order")
    parser.add_argument("--url", help="a running server; without it the app runs in this process")
    parser.add_argument("--dialogue", default="stub")
    parser.add_argument("--line-rate", type=int, default=8000)
    parser.add_argument("--stt-model", default="prisma-v3.0")
    parser.add_argument("--param", type=_param, action="append", default=[], metavar="k=v")
    args = parser.parse_args(argv)
    if not args.dir.is_dir():
        parser.error(f"{args.dir} is not a directory")

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
                turn_files(args.dir),
                dialogue=args.dialogue,
                line_rate=args.line_rate,
                stt_model=args.stt_model,
                params=dict(args.param),
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
