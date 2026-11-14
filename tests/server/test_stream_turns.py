"""Streaming STT for the primary reading (`samajh.server.stream`), with a fake stream: no network."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from samajh.clients._runtime import Ledger
from samajh.clients.gnani.stream import (
    PrismaStream,
    StreamBudgetExceeded,
    StreamError,
    StreamResult,
    StreamSession,
    StreamTimeout,
)
from samajh.server import create_app
from samajh.server.dialogue import BotLine, BotUtterance, Heard, Step
from samajh.server.settings import Streaming, load_settings
from samajh.server.stream import StreamFactory

ANSWER = make_wav(0.5)


class FakeStream:
    def __init__(self, options: PrismaStream, how: str, text: str) -> None:
        self.options, self.how, self.text = options, how, text
        self.sent = bytearray()
        self.opened = self.aborted = self.committed = False

    def open(self) -> FakeStream:
        if self.how == "budget":
            raise StreamBudgetExceeded(unit="stream_seconds", cap=1, spent=1, estimate=30)
        self.opened = True
        return self

    def send(self, pcm: bytes) -> None:
        self.sent += pcm

    def commit(self, timeout_s: float, *, close: bool = True) -> StreamResult:
        if self.how == "error":
            raise StreamError(code=1008, message="refused")
        if self.how == "timeout":
            raise StreamTimeout(code="commit_timeout", message="late")
        self.committed = True
        return StreamResult(
            text=self.text,
            segments=(self.text,),
            split=False,
            open_ms=5.0,
            first_byte_to_final_ms=300.0,
            commit_to_final_ms=200.0,
            audio_seconds=len(self.sent) / 2 / self.options.sample_rate,
        )

    def close(self) -> None:
        self.closed = True

    def abort(self) -> None:
        if not self.committed:
            self.aborted = True


class Streams:
    def __init__(self, how: str = "ok", text: str = "स्ट्रीम का जवाब") -> None:
        self.how, self.text = how, text
        self.made: list[FakeStream] = []

    def __call__(self, options: PrismaStream) -> FakeStream:
        self.made.append(FakeStream(options, self.how, self.text))
        return self.made[-1]


class Scripted:
    """Asks for a second reading after every turn when `figure`; records what it heard."""

    def __init__(self, figure: bool = False) -> None:
        self.figure = figure
        self.heard: list[Heard] = []

    def start(self) -> Step:
        return Step(state="0", say=self._say(0))

    def step(self, state: str, heard: Heard) -> Step:
        self.heard.append(heard)
        return Step(state=str(int(state) + 1), say=self._say(int(state) + 1))

    def _say(self, n: int) -> BotUtterance:
        return BotUtterance(lines=(BotLine(text=f"q{n}"),), language="hi-IN", second_reading=self.figure)


def make(
    state: Path,
    fake: FakeSpeech,
    streams: StreamFactory | None,
    *,
    enabled: bool = True,
    figure: bool = False,
    commit_timeout_s: float = 0.4,
) -> tuple[TestClient, Scripted]:
    dialogue = Scripted(figure)

    def factory(params: Mapping[str, str]) -> Scripted:
        return dialogue

    settings = load_settings().model_copy(
        update={"streaming": Streaming(enabled=enabled, commit_timeout_s=commit_timeout_s)}
    )
    app = create_app(
        gnani=fake,
        state=state,
        web_dir=None,
        clips_dir=None,
        dialogues={"s": factory},
        settings=settings,
        stream_factory=streams,
    )
    return TestClient(app), dialogue


def start(phone: TestClient, **body: object) -> dict:
    response = phone.post("/api/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def turn(phone: TestClient, sid: str, reply_to: int, part: int = 1, stream: bool = True) -> dict:
    url = f"/api/sessions/{sid}/turns?source=file&reply_to={reply_to}&part={part}&stream={int(stream)}"
    response = phone.post(url, content=ANSWER)
    assert response.status_code == 200, response.text
    return response.json()


def primary(phone: TestClient, sid: str) -> dict:
    log = phone.get(f"/api/sessions/{sid}").json()
    return [e for e in log["events"] if e["type"] == "customer"][-1]["readings"][0]


def stream_and_commit(phone: TestClient, sid: str, reply_to: int) -> dict:
    with phone.websocket_connect(f"/api/sessions/{sid}/stream?reply_to={reply_to}") as ws:
        ws.send_bytes(b"\x01\x00" * 4000)
        ws.send_text(json.dumps({"type": "commit"}))
        return ws.receive_json()


def refusal(phone: TestClient, url: str, **kwargs: object) -> WebSocketDisconnect:
    try:
        phone.websocket_connect(url, **kwargs).__enter__()
    except WebSocketDisconnect as refused:
        return refused
    raise AssertionError("the socket was accepted")


@pytest.fixture
def fake() -> FakeSpeech:
    return FakeSpeech(["रेस्ट का जवाब"] * 10)


def test_a_streamed_turn_is_read_by_the_stream_and_the_dialogue_hears_it(
    fake: FakeSpeech, state: Path
) -> None:
    streams = Streams()
    phone, dialogue = make(state, fake, streams)
    s = start(phone)
    assert s["streaming"] is True
    assert phone.get("/api/health").json()["streaming"] is True
    assert stream_and_commit(phone, s["session_id"], 0)["type"] == "final"
    turn(phone, s["session_id"], 0)
    reading = primary(phone, s["session_id"])
    assert reading["mode"] == "stream" and reading["text"] == "स्ट्रीम का जवाब"
    assert {k: v for k, v in reading["params"].items() if not k.endswith("_ms") or k == "min_silence_ms"} == {
        "language_code": "hi-IN",
        "format": "transcribe",
        "min_silence_ms": "2000",
        "sample_rate": "8000",
    }
    assert {"commit_rx_lag_ms", "final_wait_ms"} <= set(reading["params"])
    assert reading["seconds"] == 0.2 and reading["http_status"] is None and reading["est_credits"] > 0
    assert dialogue.heard[-1].text == "स्ट्रीम का जवाब"
    assert fake.stt_calls == []  # no REST primary
    assert bytes(streams.made[0].sent) == b"\x01\x00" * 4000


@pytest.mark.parametrize(
    ("how", "reason"), [("error", "error"), ("timeout", "timeout"), ("budget", "budget")]
)
def test_a_failed_stream_falls_back_to_rest(fake: FakeSpeech, state: Path, how: str, reason: str) -> None:
    phone, dialogue = make(state, fake, Streams(how))
    s = start(phone)
    assert stream_and_commit(phone, s["session_id"], 0) == {"type": "failed", "reason": reason}
    turn(phone, s["session_id"], 0)
    reading = primary(phone, s["session_id"])
    assert reading["mode"] == "rest" and reading["params"]["stream_fallback"] == reason
    assert dialogue.heard[-1].text == "रेस्ट का जवाब"


def test_a_turn_that_said_it_streamed_but_has_no_stream_falls_back(fake: FakeSpeech, state: Path) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone)
    turn(phone, s["session_id"], 0)
    assert primary(phone, s["session_id"])["params"]["stream_fallback"] == "no_stream"


def test_an_uncommitted_stream_times_out_the_turn_into_rest(fake: FakeSpeech, state: Path) -> None:
    streams = Streams()
    phone, _ = make(state, fake, streams)
    s = start(phone)
    with phone.websocket_connect(f"/api/sessions/{s['session_id']}/stream?reply_to=0") as ws:
        ws.send_bytes(b"\x00" * 2048)
        clock = time.monotonic()
        turn(phone, s["session_id"], 0)
        assert time.monotonic() - clock < 2
        assert ws.receive_json() == {"type": "failed", "reason": "timeout"}
    assert primary(phone, s["session_id"])["params"]["stream_fallback"] == "timeout"
    assert streams.made[0].aborted


def test_a_later_take_is_read_by_rest(fake: FakeSpeech, state: Path) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone)
    stream_and_commit(phone, s["session_id"], 0)
    turn(phone, s["session_id"], 0)
    turn(phone, s["session_id"], 0, part=2)
    reading = primary(phone, s["session_id"])
    assert reading["mode"] == "rest" and reading["params"]["stream_fallback"] == "later_take"


def test_streaming_off_refuses_the_socket_and_turns_are_plain_rest(fake: FakeSpeech, state: Path) -> None:
    streams = Streams()
    phone, _ = make(state, fake, streams, enabled=False)
    s = start(phone)
    assert s["streaming"] is False and phone.get("/api/health").json()["streaming"] is False
    refused = refusal(phone, f"/api/sessions/{s['session_id']}/stream?reply_to=0")
    assert refused.code == 1008
    turn(phone, s["session_id"], 0, stream=False)
    reading = primary(phone, s["session_id"])
    assert reading["mode"] == "rest" and "stream_fallback" not in reading["params"]
    assert streams.made == []


def test_a_session_can_turn_streaming_off(fake: FakeSpeech, state: Path) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone, streaming=False)
    assert s["streaming"] is False
    refusal(phone, f"/api/sessions/{s['session_id']}/stream?reply_to=0")


@pytest.mark.parametrize("headers", [{"origin": "https://evil.example"}, {"host": "evil.example"}])
def test_a_socket_from_another_site_is_refused(fake: FakeSpeech, state: Path, headers: dict) -> None:
    streams = Streams()
    phone, _ = make(state, fake, streams)
    s = start(phone)
    refused = refusal(phone, f"/api/sessions/{s['session_id']}/stream?reply_to=0", headers=headers)
    assert refused.code == 1008
    assert streams.made == []


def test_the_second_reading_stays_rest_on_a_figure_turn(fake: FakeSpeech, state: Path) -> None:
    phone, dialogue = make(state, fake, Streams(), figure=True)
    s = start(phone)
    stream_and_commit(phone, s["session_id"], 0)
    turn(phone, s["session_id"], 0)
    log = phone.get(f"/api/sessions/{s['session_id']}").json()
    readings = [e for e in log["events"] if e["type"] == "customer"][-1]["readings"]
    assert [(r["role"], r["mode"]) for r in readings] == [("primary", "stream"), ("second", "rest")]
    assert [o.model for _, o in fake.stt_calls] == ["prisma-v2.5"]
    assert dialogue.heard[-1].second == "रेस्ट का जवाब"


def test_a_new_stream_or_a_hang_up_aborts_the_open_one(fake: FakeSpeech, state: Path) -> None:
    streams = Streams()
    phone, _ = make(state, fake, streams)
    s = start(phone)
    sid = s["session_id"]
    with phone.websocket_connect(f"/api/sessions/{sid}/stream?reply_to=0") as first:
        first.send_bytes(b"\x00" * 1024)
        with phone.websocket_connect(f"/api/sessions/{sid}/stream?reply_to=0") as second:
            assert first.receive_json() == {"type": "failed", "reason": "superseded"}
            second.send_bytes(b"\x00" * 1024)
            assert phone.post(f"/api/sessions/{sid}/end", json={}).status_code == 200
            assert second.receive_json() == {"type": "failed", "reason": "ended"}
    assert [m.aborted for m in streams.made] == [True, True]
    refusal(phone, f"/api/sessions/{sid}/stream?reply_to=0")  # an ended session takes no stream


class SlowUpstream:
    """Prisma as the real stream client sees it: the final 150 ms after the commit, and a close
    handshake that takes 500 ms."""

    def __init__(self) -> None:
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.inbox.put_nowait(json.dumps({"type": "connected"}))

    async def send(self, message: str | bytes) -> None:
        if isinstance(message, str):

            async def later() -> None:
                await asyncio.sleep(0.15)
                await self.inbox.put(json.dumps({"type": "transcript", "text": "ठीक है"}))

            asyncio.get_running_loop().create_task(later())

    async def recv(self) -> str:
        return await self.inbox.get()

    async def close(self) -> None:
        await asyncio.sleep(0.5)


def test_a_commit_after_3_s_of_small_messages_reaches_the_turn_before_the_close_handshake(
    fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    def factory(options: PrismaStream) -> StreamSession:
        async def connect(url: str, headers: dict[str, str]) -> SlowUpstream:
            return SlowUpstream()

        ledger = Ledger(tmp_path / "ledger.jsonl")
        return StreamSession(
            url="ws://fake", options=options, api_key="k", ledger=ledger, stt_rate=0.01, connect=connect
        )

    phone, dialogue = make(state, fake, factory, commit_timeout_s=3.0)  # type: ignore[arg-type]
    sid = start(phone)["session_id"]
    with phone.websocket_connect(f"/api/sessions/{sid}/stream?reply_to=0") as ws:
        began = time.perf_counter()
        for n in range(1125):  # 375 messages of 42 bytes a second for 3 s
            ws.send_bytes(b"\x01\x00" * 21)
            pause = began + (n + 1) / 375 - time.perf_counter()
            if pause > 0:
                time.sleep(pause)
        ws.send_text(json.dumps({"type": "commit"}))
        clock = time.perf_counter()
        turn(phone, sid, 0)
        took = time.perf_counter() - clock
    reading = primary(phone, sid)
    assert reading["mode"] == "stream" and dialogue.heard[-1].text == "ठीक है"
    assert took < 0.3 + 0.0, reading["params"]
    assert float(reading["params"]["commit_queue_ms"]) < 100
    rows = [e for e in Ledger(tmp_path / "ledger.jsonl").entries() if e.kind == "stt.stream"]
    assert len(rows) == 1 and rows[0].error_code is None


def phone_turn(phone: TestClient, sid: str, reply_to: int, mode: str, source: str = "mic") -> None:
    url = f"/api/sessions/{sid}/turns?source={source}&reply_to={reply_to}&mode={mode}"
    response = phone.post(url, content=ANSWER)  # the phone sends no `stream` parameter
    assert response.status_code == 200, response.text


def test_a_hands_free_mic_take_with_no_socket_is_marked_no_stream(fake: FakeSpeech, state: Path) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone)
    phone_turn(phone, s["session_id"], 0, "vad")
    reading = primary(phone, s["session_id"])
    assert reading["mode"] == "rest" and reading["params"]["stream_fallback"] == "no_stream"


@pytest.mark.parametrize(("mode", "source"), [("ptt", "mic"), ("file", "file")])
def test_push_to_talk_and_file_turns_stay_unmarked_rest(
    fake: FakeSpeech, state: Path, mode: str, source: str
) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone)
    phone_turn(phone, s["session_id"], 0, mode, source)
    assert "stream_fallback" not in primary(phone, s["session_id"])["params"]


def test_a_hands_free_take_with_streaming_off_for_the_session_stays_unmarked(
    fake: FakeSpeech, state: Path
) -> None:
    phone, _ = make(state, fake, Streams())
    s = start(phone, streaming=False)
    phone_turn(phone, s["session_id"], 0, "vad")
    assert "stream_fallback" not in primary(phone, s["session_id"])["params"]


def test_a_socket_for_an_earlier_prompt_is_refused_and_leaves_the_live_stream(
    fake: FakeSpeech, state: Path
) -> None:
    streams = Streams()
    phone, _ = make(state, fake, streams)
    s = start(phone)
    sid = s["session_id"]
    next_prompt = turn(phone, sid, 0, stream=False)["bot"]["seq"]
    assert next_prompt > 0
    made = len(streams.made)
    assert refusal(phone, f"/api/sessions/{sid}/stream?reply_to=0").code == 1008
    assert len(streams.made) == made  # no stream opened for the stale prompt
    assert stream_and_commit(phone, sid, next_prompt)["type"] == "final"
