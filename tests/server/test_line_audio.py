"""Bot lines served one at a time while the rest are made, through the HTTP API, with a fake
Gnani client. Nothing here touches the network."""

from __future__ import annotations

import asyncio
import threading
import time
from collections import Counter
from pathlib import Path

import httpx
import pytest
from serverkit import FakeSpeech, make_wav, wav_shape
from starlette.testclient import TestClient

from samajh.clients.errors import ServerError
from samajh.clients.gnani import Speech, Timbre
from samajh.server import create_app
from samajh.server.app import sessions_of
from samajh.server.dialogue import StubDialogue, stub_factory

ANSWER = make_wav(0.5)
ECHO = "मैंने सुना: पचास हज़ार"  # line 0 of the stub's reply to the first turn
NEXT = StubDialogue.QUESTIONS[1]  # line 1


class Held(FakeSpeech):
    """FakeSpeech whose TTS for a chosen text waits on an event, and can fail a chosen text."""

    def __init__(self) -> None:
        super().__init__(["पचास हज़ार", "दो हज़ार", "बीमा"])
        self.hold: dict[str, threading.Event] = {}
        self.fail: dict[str, Exception] = {}
        self.lengths = {ECHO: 0.3, NEXT: 0.5}

    def tts(self, text: str, options: Timbre) -> Speech:
        gate = self.hold.get(text)
        if gate is not None:
            assert gate.wait(10)
        error = self.fail.pop(text, None)
        if error is not None:
            self.tts_calls.append((text, options))
            raise error
        speech = super().tts(text, options)
        seconds = self.lengths.get(text, 0.4)
        return speech.model_copy(
            update={"audio": make_wav(seconds, options.sample_rate, tone=200 + 100 * seconds)}
        )


def phone_on(fake: FakeSpeech, state: Path) -> TestClient:
    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues={"stub": stub_factory})
    return TestClient(app, raise_server_exceptions=False)


def answered(phone: TestClient) -> tuple[str, dict]:
    """A call whose open prompt is the two-line reply to the first turn."""
    sid = phone.post("/api/sessions", json={}).json()["session_id"]
    reply = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0&part=1", content=ANSWER)
    assert reply.status_code == 200, reply.text
    return sid, reply.json()["bot"]


def bot_event(phone: TestClient, sid: str, seq: int) -> dict:
    return phone.get(f"/api/sessions/{sid}").json()["events"][seq]


def settled(phone: TestClient, sid: str, seq: int) -> None:
    job = sessions_of(phone.app).live[sid].speech[seq]
    try:
        job.done.exception(timeout=10)
    except Exception:  # noqa: BLE001, S110 - only waiting for it to finish
        pass


@pytest.fixture
def fake() -> Held:
    return Held()


def test_the_utterance_lists_a_url_per_line_and_the_gap(fake: Held, state: Path) -> None:
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    assert [line["text"] for line in bot["lines"]] == [ECHO, NEXT]
    assert [line["audio_url"] for line in bot["lines"]] == [
        f"/api/sessions/{sid}/lines/{bot['seq']}/0.wav",
        f"/api/sessions/{sid}/lines/{bot['seq']}/1.wav",
    ]
    assert bot["line_gap_ms"] == 150
    assert bot["audio_url"] == f"/api/sessions/{sid}/audio/bot-{bot['seq']:03d}.wav"


def test_line_zero_plays_while_line_one_is_still_being_made(fake: Held, state: Path) -> None:
    fake.hold[NEXT] = threading.Event()
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    first = phone.get(bot["lines"][0]["audio_url"])
    assert first.status_code == 200 and first.headers["content-type"] == "audio/wav"
    assert wav_shape(first.content) == (1, 2, 8000, 2400)
    assert bot_event(phone, sid, bot["seq"])["audio"] is None  # not committed: line 1 is not made
    assert NEXT not in [text for text, _ in fake.tts_calls]
    fake.hold[NEXT].set()
    second = phone.get(bot["lines"][1]["audio_url"])
    assert wav_shape(second.content) == (1, 2, 8000, 4000)
    event = bot_event(phone, sid, bot["seq"])
    assert event["audio"] == f"audio/bot-{bot['seq']:03d}.wav"  # the last line's request committed it


def _shape(event: dict) -> dict:
    lines = [
        {**line, "tts": {k: v for k, v in line["tts"].items() if k != "synth_ms"}} for line in event["lines"]
    ]
    return {"audio": event["audio"], "audio_seconds": event["audio_seconds"], "lines": lines}


def test_lines_then_the_joined_file_equal_the_joined_file_alone(tmp_path: Path) -> None:
    alone = phone_on(Held(), tmp_path / "a")
    sid_a, bot_a = answered(alone)
    joined_alone = alone.get(bot_a["audio_url"])
    assert joined_alone.status_code == 200

    lined = phone_on(Held(), tmp_path / "b")
    sid_b, bot_b = answered(lined)
    for line in bot_b["lines"]:
        assert lined.get(line["audio_url"]).status_code == 200
    joined_after = lined.get(bot_b["audio_url"])
    assert joined_after.content == joined_alone.content
    a, b = bot_event(alone, sid_a, bot_a["seq"]), bot_event(lined, sid_b, bot_b["seq"])
    assert _shape(a) == _shape(b)
    assert [(line["start_s"], line["end_s"]) for line in b["lines"]] == [(0.0, 0.3), (0.45, 0.95)]
    assert b["synth_ms"] >= max(line["tts"]["synth_ms"] for line in b["lines"])
    # The lines cut out of the joined file after a restart are the lines served before it.
    restarted = phone_on(Held(), tmp_path / "b")
    assert (
        restarted.get(bot_b["lines"][1]["audio_url"]).content
        == lined.get(bot_b["lines"][1]["audio_url"]).content
    )


def test_no_line_is_made_twice_when_the_phone_and_the_replay_tool_both_fetch(fake: Held, state: Path) -> None:
    fake.hold[ECHO] = threading.Event()
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    urls = [line["audio_url"] for line in bot["lines"]] + [bot["audio_url"]]

    async def fetch_all() -> list[int]:
        transport = httpx.ASGITransport(app=phone.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
            waiting = [asyncio.create_task(http.get(url)) for url in urls]
            await asyncio.sleep(0.2)
            assert not any(task.done() for task in waiting)  # all three wait for line 0
            fake.hold[ECHO].set()
            return [(await task).status_code for task in waiting]

    assert asyncio.run(fetch_all()) == [200, 200, 200]
    made = Counter(text for text, _ in fake.tts_calls)
    assert (made[ECHO], made[NEXT]) == (1, 1)
    assert bot_event(phone, sid, bot["seq"])["audio"] is not None


def test_a_hang_up_before_the_lines_are_made_commits_no_audio(fake: Held, state: Path) -> None:
    fake.hold[NEXT] = threading.Event()
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    assert phone.get(bot["lines"][0]["audio_url"]).status_code == 200
    assert phone.post(f"/api/sessions/{sid}/end", json={}).status_code == 200
    fake.hold[NEXT].set()
    settled(phone, sid, bot["seq"])
    for url in (bot["lines"][1]["audio_url"], bot["audio_url"]):
        response = phone.get(url)
        assert response.status_code == 409 and response.json()["error"]["code"] == "session_not_active"
    event = bot_event(phone, sid, bot["seq"])
    assert (event["audio"], event["synth_ms"], event["lines"][1]["tts"]) == (None, None, None)


def test_a_superseded_reply_is_refused(fake: Held, state: Path) -> None:
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    retake = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0&part=2", content=make_wav(0.9))
    assert retake.status_code == 200
    for url in (bot["lines"][0]["audio_url"], bot["audio_url"]):
        response = phone.get(url)
        assert response.status_code == 409 and response.json()["error"]["code"] == "turn_superseded"


def test_a_failed_line_is_logged_once_and_a_retry_makes_only_what_is_missing(fake: Held, state: Path) -> None:
    fake.fail[NEXT] = ServerError(status=503, code="DOWN", message="timbre is down", attempts=2)
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    assert phone.get(bot["lines"][0]["audio_url"]).status_code == 200
    failed = phone.get(bot["lines"][1]["audio_url"])
    assert failed.status_code == 502 and failed.json()["error"]["code"] == "gnani_server_error"
    errors = [e for e in phone.get(f"/api/sessions/{sid}").json()["events"] if e["type"] == "error"]
    assert len(errors) == 1 and errors[0]["stage"] == "tts"
    retry = phone.get(bot["lines"][1]["audio_url"])
    assert retry.status_code == 200
    made = Counter(text for text, _ in fake.tts_calls)
    assert (made[ECHO], made[NEXT]) == (1, 2)  # line 0 kept from the failed job
    assert bot_event(phone, sid, bot["seq"])["audio"] is not None


def test_a_bad_line_index_or_event_is_not_found(fake: Held, state: Path) -> None:
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    for path in (
        f"{bot['seq']}/2.wav",
        f"{bot['seq'] - 1}/0.wav",
        "999/0.wav",
        f"{bot['seq']}/x.wav",
        "0/0.mp3",
    ):
        assert phone.get(f"/api/sessions/{sid}/lines/{path}").status_code == 404, path
    assert phone.get(f"/api/sessions/{sid}/lines/0/0.wav", headers={"host": "evil.example"}).status_code in (
        400,
        403,
    )


def test_a_later_take_stops_the_earlier_replys_remaining_lines(fake: Held, state: Path) -> None:
    fake.hold[ECHO] = threading.Event()  # the earlier reply's job is inside line 0
    phone = phone_on(fake, state)
    sid, bot = answered(phone)
    retake = threading.Thread(
        target=lambda: phone.post(
            f"/api/sessions/{sid}/turns?source=file&reply_to=0&part=2", content=make_wav(0.9)
        )
    )
    retake.start()
    time.sleep(0.3)
    fake.hold[ECHO].set()
    retake.join(10)
    settled(phone, sid, bot["seq"])
    # Line 1 of the earlier reply was never started; NEXT was made once, for the later take's reply.
    made = Counter(text for text, _ in fake.tts_calls)
    assert made[NEXT] <= 1
    assert sessions_of(phone.app).live[sid].speech[bot["seq"]].cancelled
