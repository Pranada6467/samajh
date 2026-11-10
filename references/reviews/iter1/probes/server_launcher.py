"""Reviewer's offline launcher for the Samajh voice transport. Never reaches Gnani.

    SAMAJH_STATE_DIR=<scratch>/state uv run python references/reviews/iter1/probes/server_launcher.py \
        --port 8191 --state <scratch>/state --ctl <scratch>/ctl

What makes it offline:
  * GNANI_API_KEY and OPENROUTER_API_KEY are set to "" before any samajh import, so the client's
    .env loader (override=False) leaves them empty;
  * `samajh.server.app.live_client` is replaced by a function that raises;
  * socket.connect to anything but loopback raises (belt and braces);
  * `create_app(gnani=<fake>)` gets a fake speech client (tests/server/serverkit.FakeSpeech subclass).

Control files under --ctl (read on every fake call, so a probe can flip behaviour at run time):
  stt_delay   seconds to sleep inside the fake STT call (float)
  tts_delay   seconds to sleep inside the fake TTS call
  stt_error   if present, fake STT raises ServerError(503)
  tts_error   if present, fake TTS raises ServerError(503)
Counters are appended to <ctl>/calls.log, one line per fake call or dialogue.next call.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path

os.environ["GNANI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""

REPO = Path(os.environ.get("SAMAJH_REVIEW_REPO") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests" / "server"))

_real_connect = socket.socket.connect


def _loopback_only(self, address):  # type: ignore[no-untyped-def]
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
        raise OSError(f"reviewer launcher: outbound connection to {host!r} refused")
    return _real_connect(self, address)


socket.socket.connect = _loopback_only  # type: ignore[method-assign]

import uvicorn  # noqa: E402
from serverkit import FakeSpeech, make_wav  # noqa: E402

import samajh.server.app as app_module  # noqa: E402
from samajh.clients.errors import ServerError  # noqa: E402
from samajh.server.dialogue import BotUtterance, CallView, Heard, stub_factory  # noqa: E402


def _no_live_client(*args, **kwargs):  # type: ignore[no-untyped-def]
    raise RuntimeError("reviewer launcher: the real Gnani client is disabled")


app_module.live_client = _no_live_client  # type: ignore[assignment]

_log_lock = threading.Lock()


class Controlled(FakeSpeech):
    def __init__(self, ctl: Path, transcripts: list[str]) -> None:
        super().__init__(transcripts)
        self.ctl = ctl
        # A prompt's fake audio grows with its text so recording arithmetic is not all 0.4 s.
        self._tts_text = ""
        self.tts_audio = lambda o: make_wav(0.4 + 0.01 * len(self._tts_text), o.sample_rate)

    def _note(self, line: str) -> None:
        with _log_lock, (self.ctl / "calls.log").open("a") as f:
            f.write(f"{time.time():.3f} {line}\n")

    def _float(self, name: str) -> float:
        try:
            return float((self.ctl / name).read_text().strip())
        except (OSError, ValueError):
            return 0.0

    def stt(self, audio, options, *, audio_format="wav"):  # type: ignore[no-untyped-def]
        self._note(f"stt model={options.model} lang={options.language} fmt={options.format} bytes={len(audio)}")
        time.sleep(self._float("stt_delay"))
        if (self.ctl / "stt_error").exists():
            raise ServerError(status=503, code="UPSTREAM", message="down", attempts=2)
        return super().stt(audio, options, audio_format=audio_format)

    def tts(self, text, options):  # type: ignore[no-untyped-def]
        self._note(f"tts chars={len(text)} rate={options.sample_rate} lang={options.language}")
        time.sleep(self._float("tts_delay"))
        if (self.ctl / "tts_error").exists():
            raise ServerError(status=503, code="DOWN", message="timbre is down", attempts=2)
        self._tts_text = text
        return super().tts(text, options)


class Counting:
    """Never ends the call; every utterance says how many times next() has run on this object."""

    def __init__(self, ctl: Path, params: Mapping[str, str]) -> None:
        self.calls, self.ctl, self.params = 0, ctl, dict(params)

    def next(self, call: CallView, heard: Heard | None) -> BotUtterance:
        self.calls += 1
        with _log_lock, (self.ctl / "calls.log").open("a") as f:
            f.write(f"{time.time():.3f} dialogue.next session={call.session_id} calls={self.calls}\n")
        if self.params.get("boom") and heard is not None:
            raise RuntimeError("SECRET-DETAIL /Users/secret/path token=abc123")
        language = self.params.get("language", "hi-IN")
        return BotUtterance(text=f"q{len(call.exchanges)} calls={self.calls}", language=language)  # type: ignore[arg-type]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ctl", type=Path, required=True)
    parser.add_argument("--allow-host", action="append", default=[])
    args = parser.parse_args()
    args.ctl.mkdir(parents=True, exist_ok=True)
    os.environ["SAMAJH_STATE_DIR"] = str(args.state)
    fake = Controlled(
        args.ctl,
        [
            "मैंने 5,00,000 रुपये का लोन लिया था।",
            "हर महीने की किस्त 11,500 रुपये है।",
            "बस एक FD ली थी loan security के लिए 52,000 की।",
        ],
    )
    app = app_module.create_app(
        gnani=fake,
        state=args.state,
        dialogues={"stub": stub_factory, "count": lambda params: Counting(args.ctl, params)},
        allowed_hosts=(*app_module.LOCAL_HOSTS, *args.allow_host),
    )
    print(f"samajh module: {app_module.__file__}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, limit_concurrency=32, log_level="warning")


if __name__ == "__main__":
    main()
