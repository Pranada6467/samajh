"""Streaming STT for the primary reading of a customer turn (setting `[streaming]`, off by default).

The phone opens `/api/sessions/{id}/stream?reply_to=N` when it starts listening for a reply,
sends PCM s16le mono at the call's line rate from the pre-roll on, and sends `{"type": "commit"}`
at its VAD cut, when it also uploads the take's WAV as before. The socket here forwards the frames
to one Prisma `StreamSession` and, on commit, stores the final transcript (or why there is none) in
a future for that session and `reply_to`. `Sessions.turn` waits for that future instead of the REST
primary; on any failure it falls back to REST and marks the reading `stream_fallback`.

Bounds: a stream with no commit within `NO_COMMIT_S` is aborted; one stream per session (a new one
aborts the old); hanging up aborts it. A stream holds no REST slot and no lock, and writes its own
`stt.stream` ledger row (`samajh.clients.gnani.stream`); nothing else here spends credits.

Whether a session streams lives in memory only (`StreamHub.off`): after a server restart an
opted-out session that is still active would stream again.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Protocol, get_args

import anyio
from starlette.websockets import WebSocket, WebSocketDisconnect

from samajh.clients.gnani.stream import (
    PrismaStream,
    StreamBudgetExceeded,
    StreamError,
    StreamResult,
    StreamTimeout,
    stream_language,
)
from samajh.clients.gnani.types import SttLanguage
from samajh.server.sessionlog import SttReading
from samajh.server.settings import Streaming

NO_COMMIT_S = 35.0  # a stream that is not committed within this is aborted
MAX_PENDING_BYTES = 16000 * 2 * 10  # frames held while the upstream socket opens: 10 s at 16 kHz
TURN_MARGIN_S = 0.5  # the turn waits commit_timeout_s plus this: the commit can start a little later


class Stream(Protocol):
    def open(self) -> Any: ...
    def send(self, pcm: bytes) -> None: ...
    def commit(self, timeout_s: float, *, close: bool = True) -> StreamResult: ...
    def close(self) -> None: ...
    def abort(self) -> None: ...


StreamFactory = Callable[[PrismaStream], Stream]


class _Failed(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Slot:
    reply_to: int
    options: PrismaStream
    result: Future[StreamResult] = field(default_factory=Future)
    stop: threading.Event = field(default_factory=threading.Event)
    stop_reason: str = "superseded"
    # perf_counter stamps (the clock of the turn's `received`): commit message from the phone,
    # the commit call starting on its worker thread, the result set on the future
    commit_rx: float | None = None
    commit_call: float | None = None
    resolved: float | None = None

    def cancel(self, reason: str) -> None:
        self.stop_reason = reason
        self.stop.set()


def _reason(exc: BaseException) -> str:
    if isinstance(exc, _Failed):
        return exc.reason
    if isinstance(exc, StreamBudgetExceeded):
        return "budget"
    if isinstance(exc, StreamTimeout):
        return "timeout"
    if isinstance(exc, StreamError):
        return "error"
    return "error"


class StreamHub:
    """The live streams of this server run, one per session, and their results."""

    def __init__(self, config: Streaming, factory: StreamFactory | None, stt_rate: float) -> None:
        self.config, self.factory, self.stt_rate = config, factory, stt_rate
        self.off: set[str] = set()  # sessions that asked not to stream
        self._slots: dict[str, _Slot] = {}
        self._lock = threading.Lock()

    def enabled_for(self, session_id: str) -> bool:
        return self.config.enabled and self.factory is not None and session_id not in self.off

    def options(self, language: str, line_rate: int) -> PrismaStream:
        """`language` is the bot line's (a locale, or `hi-en`, which streams as `hi-IN`:
        `stream_language`). ValueError for one streaming cannot take (`auto`)."""
        if language == "hi-en":
            base = stream_language("hi-en", model=self.config.model)
        elif language in get_args(SttLanguage):
            base = PrismaStream(model=self.config.model, language=language)
        else:
            raise ValueError(f"no stream language for {language!r}")
        return base.model_copy(
            update={
                "sample_rate": line_rate,
                "min_silence_ms": self.config.min_silence_ms,
                "idle_timeout_s": self.config.idle_timeout_s,
            }
        )

    def cancel(self, session_id: str, reason: str = "ended") -> None:
        with self._lock:
            slot = self._slots.pop(session_id, None)
        if slot is not None:
            slot.cancel(reason)

    def _begin(self, session_id: str, reply_to: int, options: PrismaStream) -> _Slot:
        slot = _Slot(reply_to, options)
        with self._lock:
            old, self._slots[session_id] = self._slots.get(session_id), slot
        if old is not None:
            old.cancel("superseded")
        return slot

    # ---------------------------------------------------------------- the browser's socket

    async def serve(self, ws: WebSocket, session_id: str, reply_to: int, options: PrismaStream) -> None:
        """Run one accepted socket to its end. Never raises."""
        assert self.factory is not None
        slot = self._begin(session_id, reply_to, options)
        stream = self.factory(options)
        opening = asyncio.ensure_future(anyio.to_thread.run_sync(stream.open))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + NO_COMMIT_S
        # The stop and no-commit checks run beside the receive loop, not as a `wait_for` per
        # message: the phone can send hundreds of small messages a second.
        why: list[str] = []
        me = asyncio.current_task()
        assert me is not None

        async def watch() -> None:
            while True:
                await asyncio.sleep(0.05)
                if slot.stop.is_set() or loop.time() >= deadline:
                    why.append(slot.stop_reason if slot.stop.is_set() else "no_commit")
                    me.cancel()
                    return

        watcher = asyncio.ensure_future(watch())
        pending: list[bytes] = []
        held = 0
        opened = False
        committed = False
        try:
            try:
                while True:
                    if not opened and opening.done():
                        opening.result()
                        opened = True
                        for chunk in pending:
                            stream.send(chunk)
                        pending.clear()
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        raise _Failed("disconnected")
                    data = message.get("bytes")
                    if data:
                        if opened:
                            stream.send(data)
                        elif held + len(data) <= MAX_PENDING_BYTES:
                            pending.append(data)
                            held += len(data)
                        continue
                    if _is_commit(message.get("text")):
                        break
                slot.commit_rx = time.perf_counter()
                watcher.cancel()
                if why:  # the watcher fired as the commit came: its cancel is still pending
                    me.uncancel()
                    raise _Failed(why[0])
                if not opened:
                    await opening
                    opened = True
                    for chunk in pending:
                        stream.send(chunk)
            except asyncio.CancelledError:
                if not why:
                    raise
                me.uncancel()  # our own watcher's cancel, handled here
                raise _Failed(why[0]) from None
            finally:
                watcher.cancel()

            def commit() -> StreamResult:
                slot.commit_call = time.perf_counter()
                return stream.commit(self.config.commit_timeout_s, close=False)

            result = await anyio.to_thread.run_sync(commit)
            committed = True
            slot.resolved = time.perf_counter()
            slot.result.set_result(result)
            await _send(ws, {"type": "final", "text": result.text, "split": result.split})
            await anyio.to_thread.run_sync(stream.close)  # the close handshake, after the turn has the text
            return
        except (Exception, WebSocketDisconnect) as exc:  # noqa: BLE001 - every failure is a fallback reason
            if not slot.result.done():
                slot.result.set_exception(_Failed(_reason(exc)))
            await _send(ws, {"type": "failed", "reason": _reason(exc)})
        finally:
            if not slot.result.done():  # cancelled from outside
                slot.result.set_exception(_Failed("error"))
            if not opening.done():
                try:
                    await opening
                except Exception:  # noqa: BLE001, S110 - the open failed: nothing to abort
                    pass
            if not committed:
                await anyio.to_thread.run_sync(stream.abort)  # a no-op after a failed open
            try:
                await ws.close()
            except Exception:  # noqa: BLE001, S110 - already closed
                pass

    # ---------------------------------------------------------------- the turn

    def take(
        self,
        session_id: str,
        reply_to: int,
        part: int,
        *,
        requested: bool,
        wait_s: float,
        received: float | None = None,
    ) -> SttReading | str | None:
        """For `Sessions.turn`: the stream's primary reading, a fallback reason (the caller reads
        REST and marks it), or None when this turn never streamed (plain REST, unmarked)."""
        with self._lock:
            slot = self._slots.get(session_id)
            if slot is not None and slot.reply_to != reply_to:
                slot = None
            if slot is not None and part > 1:
                del self._slots[session_id]
        if part > 1:
            if slot is not None:
                slot.cancel("later_take")
            return "later_take" if requested or slot is not None else None
        if slot is None:
            return "no_stream" if requested else None
        waiting = time.perf_counter()
        try:
            result = slot.result.result(timeout=wait_s)
        except FutureTimeout:
            slot.cancel("timeout")
            return "timeout"
        except _Failed as failed:
            return failed.reason
        options = slot.options
        timing = _timing(slot, result, received, waiting)
        return SttReading(
            role="primary",
            mode="stream",
            model=options.model,
            params={
                "language_code": options.language,
                "format": options.format,
                "min_silence_ms": str(options.min_silence_ms),
                "sample_rate": str(options.sample_rate),
                **({"stream_split": "true"} if result.split else {}),
                **timing,
            },
            text=result.text,
            cache_hit=False,
            seconds=round((result.commit_to_final_ms or 0.0) / 1000, 3),
            attempts=1,
            est_credits=round(result.audio_seconds * self.stt_rate, 6),
            http_status=None,
        )


def _ms(a: float | None, b: float | None) -> str | None:
    return None if a is None or b is None else f"{(b - a) * 1000:.1f}"


def _timing(slot: _Slot, result: StreamResult, received: float | None, waiting: float) -> dict[str, str]:
    """Where the time of a streamed primary reading went, in ms (strings for `params`):
    `commit_rx_lag_ms` the phone's commit arriving after the turn POST (negative: before);
    `commit_queue_ms` commit arriving to the commit leaving upstream (thread hop and queued frames);
    `commit_flush_ms` the client's share of that; `upstream_final_ms` commit leaving to the final;
    `final_wait_ms` the turn starting to wait to having the reading (0 when it was already there)."""
    flush = result.flush_ms
    upstream = (
        None if flush is None or result.commit_to_final_ms is None else result.commit_to_final_ms - flush
    )
    queue = None
    hop = _ms(slot.commit_rx, slot.commit_call)
    if hop is not None and flush is not None:
        queue = f"{float(hop) + flush:.1f}"
    out = {
        "commit_rx_lag_ms": _ms(received, slot.commit_rx),
        "commit_queue_ms": queue,
        "commit_flush_ms": None if flush is None else f"{flush:.1f}",
        "upstream_final_ms": None if upstream is None else f"{upstream:.1f}",
        "final_wait_ms": f"{max(0.0, ((slot.resolved or waiting) - waiting) * 1000):.1f}",
    }
    return {k: v for k, v in out.items() if v is not None}


def _is_commit(text: str | None) -> bool:
    if not text:
        return False
    try:
        message = json.loads(text)
    except ValueError:
        return False
    return isinstance(message, dict) and message.get("type") == "commit"


async def _send(ws: WebSocket, message: dict[str, Any]) -> None:
    try:
        await ws.send_json(message)
    except Exception:  # noqa: BLE001, S110 - the phone may have gone
        pass
