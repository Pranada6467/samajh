"""P5 voice launcher: the real Samajh server app on the P5 records, Batch off, for eval/p5/voice_run.py.

    uv run python eval/p5/serve.py [--port 8095] [--state .samajh/p5-voice] [--ceiling 200] [--baseline S0]
        [--data data/p5]

What it changes against `python -m samajh.server`, and nothing else:
- records: the packaged ones plus `DATA/records` (`--data`, default `data/p5`; `SAMAJH_RECORDS_DIR` is set
  to it as well);
- its own `--state` directory for sessions and case files. The Gnani lock, cache and ledger stay the
  shared project ones (`SAMAJH_STATE_DIR` must not be set: the launcher refuses to start if it is);
- the patient client profile (the live profile's 5 s lock wait gives `gnani_busy` on a long run);
- a null Batch client: every case file gets a Batch step that returns 0 segments without a request,
  so the case is `ready` with no speaker labels (the tier does not depend on Batch);
- `GNANI_CREDIT_CAP` = the ledger now (or `--baseline`, the reading at the start of the run, when the
  server is restarted mid-run) + `--ceiling`, never above the project cap; `SAMAJH_LLM_USD_CAP` at
  least 3.0, so the turn classifier and the extractor do not hit the client's USD 1.0 default cap and
  degrade turns silently;
- the dialogue's turn interpreter is built exactly as `samajh_factory` builds it (LLM classifier over
  the word lists, the settings' timeout, one attempt), wrapped so that every reading it gives is kept
  in memory and served at `GET /p5/readings?since=N` (the voice player writes them into the call file,
  as the text run does);
- `GET /p5/sessions/{id}/state` serves the session's stored dialogue state (the HTTP log leaves it
  out), for the read-back figure and the unresolved list.
Port 8085 (the phone) is refused.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from functools import cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

P5_RECORDS = ROOT / "data" / "p5" / "records"
DEFAULT_PORT = 8095
PHONE_PORT = 8085
DEFAULT_STATE = ROOT / ".samajh" / "p5-voice"
DEFAULT_CEILING = 200.0
MIN_LLM_USD_CAP = 3.0


class NullBatch:
    """Batch off: a `batch_transcribe` that sends nothing and returns no segments."""

    def __init__(self) -> None:
        self.calls = 0

    def batch_transcribe(self, audio: bytes, options: Any, **kwargs: Any) -> Any:
        from samajh.clients.gnani import BatchTranscript, CallInfo, wav_seconds

        self.calls += 1
        return BatchTranscript(
            segments=(),
            text="",
            duration_seconds=wav_seconds(audio) or 0.0,
            language=None,
            model=options.model,
            job_id="p5-batch-off",
            file_id="p5-batch-off",
            call=CallInfo(cache_hit=True, cache_key="p5-batch-off", seconds=0.0, est_credits=0.0, attempts=0),
        )


class ReadingRecorder:
    """Wraps the dialogue's turn interpreter and keeps every reading it gives, in order."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._lock = threading.Lock()
        self.readings: list[dict[str, Any]] = []

    def begin(self, text: str, **kwargs: Any) -> None:
        begin = getattr(self._inner, "begin", None)
        if begin is not None:
            begin(text, **kwargs)

    def interpret(self, text: str, *, language: Any, expecting: Any, question: str) -> Any:
        try:
            heard = self._inner.interpret(text, language=language, expecting=expecting, question=question)
        except Exception as error:
            self._add({"text": text, "expecting": str(expecting), "raised": repr(error)})
            raise
        self._add({
            "text": text, "expecting": str(expecting), "intent": str(heard.intent),
            "settled": heard.settled, "degraded": heard.degraded,
            "classifier_label": getattr(heard, "classifier_label", None),
            "amount_inr": heard.amount_inr, "approx": heard.approx,
        })  # fmt: skip
        return heard

    def _add(self, row: dict[str, Any]) -> None:
        with self._lock:
            row["n"] = len(self.readings)
            self.readings.append(row)

    def since(self, n: int) -> tuple[int, list[dict[str, Any]]]:
        with self._lock:
            return len(self.readings), [dict(r) for r in self.readings[n:]]


def live_interpreter(settings: Any) -> Any:
    """The interpreter `samajh_factory` builds for a session without `fallback=off`."""
    from samajh import dialogue as core
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.errors import ConfigError
    from samajh.clients.llm import LlmClient
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    rules = core.RuleInterpreter()
    if not settings.fallback.enabled:
        return rules
    try:
        llm = LlmClient.from_env(timeout=settings.fallback.timeout_s, retry=RetryPolicy(max_attempts=1))
    except ConfigError as error:
        print(f"no LLM fallback, turns are read by the word lists alone: {error}", file=sys.stderr)
        return rules
    return LlmFallbackInterpreter(llm, rules)


def p5_records(records_dir: Path = P5_RECORDS) -> Any:
    from samajh.server.records import PACKAGED_DIR, load_book

    return load_book(PACKAGED_DIR, records_dir)


def build_app(
    state: Path,
    *,
    gnani: Any = None,
    records: Any = None,
    settings: Any = None,
    interpreter: Any = None,
    llm: Any = None,
    batch: Any = None,
):
    """The Samajh app as the P5 voice run uses it. `gnani`, `interpreter` and `llm` are for tests;
    left None they are the real clients, built as the server builds them (lazily for Gnani)."""
    from fastapi import HTTPException

    from samajh.server.app import create_app
    from samajh.server.samajh_dialogue import samajh_factory
    from samajh.server.sessionlog import SESSION_ID
    from samajh.server.settings import load_settings

    settings = settings or load_settings()
    records = records if records is not None else p5_records()

    @cache
    def recorder() -> ReadingRecorder:
        return ReadingRecorder(interpreter if interpreter is not None else live_interpreter(settings))

    class _Lazy:
        """Builds the interpreter (and its LLM client) on the first turn, as the factory does."""

        def begin(self, text: str, **kwargs: Any) -> None:
            recorder().begin(text, **kwargs)

        def interpret(self, text: str, **kwargs: Any) -> Any:
            return recorder().interpret(text, **kwargs)

    dialogues = {"samajh": samajh_factory(records, settings, interpreter=_Lazy())}
    app = create_app(
        gnani=gnani,
        state=state,
        dialogues=dialogues,
        records=records,
        settings=settings,
        web_dir=None,
        clips_dir=None,
        profile="patient",
        batch=batch if batch is not None else NullBatch(),
        llm=llm,
    )

    @app.get("/p5/readings")
    def readings(since: int = 0) -> dict[str, Any]:
        upto, rows = recorder().since(max(0, since))
        return {"next": upto, "readings": rows}

    @app.get("/p5/sessions/{session_id}/state")
    def session_state(session_id: str) -> dict[str, Any]:
        if not SESSION_ID.fullmatch(session_id):
            raise HTTPException(404, "no such session")
        path = state / "sessions" / session_id / "session.json"
        if not path.is_file():
            raise HTTPException(404, "no such session")
        stored = json.loads(path.read_text(encoding="utf-8")).get("dialogue_state")
        return {"state": json.loads(stored) if stored else None}

    return app


def ledger_spent() -> float:
    from samajh.clients._runtime import Ledger, state_dir

    return Ledger(state_dir() / "ledger.jsonl").total_credits()


def set_env(*, ceiling: float, baseline: float | None, records_dir: Path = P5_RECORDS) -> dict[str, Any]:
    """The environment the server's clients read when they are first built. Returns what was set."""
    if os.environ.get("SAMAJH_STATE_DIR"):
        raise SystemExit("SAMAJH_STATE_DIR is set: it would give this run its own ledger and cap. Unset it.")
    from samajh.clients.gnani.client import credit_cap_from_env

    project_cap = credit_cap_from_env()
    spent = ledger_spent()
    start = spent if baseline is None else baseline
    cap = round(min(start + ceiling, project_cap), 4)
    if cap <= spent:
        raise SystemExit(f"the ledger ({spent:.2f}) is already at the cap this run would set ({cap:.2f})")
    os.environ["GNANI_CREDIT_CAP"] = str(cap)
    os.environ["SAMAJH_RECORDS_DIR"] = str(records_dir)
    try:
        usd = float(os.environ.get("SAMAJH_LLM_USD_CAP") or 0)
    except ValueError:
        usd = 0.0
    os.environ["SAMAJH_LLM_USD_CAP"] = str(max(usd, MIN_LLM_USD_CAP))
    return {
        "ledger_spent": round(spent, 4), "baseline": round(start, 4), "ceiling": ceiling,
        "GNANI_CREDIT_CAP": cap, "project_cap": project_cap,
        "SAMAJH_LLM_USD_CAP": os.environ["SAMAJH_LLM_USD_CAP"], "SAMAJH_RECORDS_DIR": str(records_dir),
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument(
        "--ceiling", type=float, default=DEFAULT_CEILING, help="estimated credits for this run"
    )
    parser.add_argument("--baseline", type=float, default=None,
                        help="the ledger reading at the start of the run (the manifest's), on a restart")  # fmt: skip
    parser.add_argument(
        "--data", default="data/p5", help="the frozen data directory whose records are served"
    )
    args = parser.parse_args(argv)
    if args.port == PHONE_PORT:
        parser.error("port 8085 belongs to the phone; use another (default 8095)")
    if args.state.resolve() == (ROOT / ".samajh").resolve():
        parser.error("--state must be its own directory, not .samajh")
    data = Path(args.data) if Path(args.data).is_absolute() else ROOT / args.data
    records_dir = (data / "records").resolve()
    if not records_dir.is_dir():
        parser.error(f"{records_dir} is not a directory")
    env = set_env(ceiling=args.ceiling, baseline=args.baseline, records_dir=records_dir)
    args.state.mkdir(parents=True, exist_ok=True)
    app = build_app(args.state, records=p5_records(records_dir))
    print(json.dumps({"p5_serve": env | {"port": args.port, "state": str(args.state)}}), flush=True)

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port, limit_concurrency=32)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
