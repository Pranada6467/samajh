"""The HTTP API through TestClient, with a fake Gnani client."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import httpx
import pytest
from serverkit import FakeSpeech, make_speech, make_wav, wav_shape
from starlette.testclient import TestClient

from samajh.clients.errors import ServerError, TransportError
from samajh.clients.gnani import PrismaV25, PrismaV30, wav_seconds
from samajh.server import create_app
from samajh.server.app import MAX_JSON_BYTES, MAX_TURN_BYTES, MAX_TURNS, sessions_of
from samajh.server.dialogue import BotLine, BotUtterance, Heard, Step, StubDialogue, stub_factory
from samajh.server.sessionlog import SessionStore, SttSettings
from samajh.server.settings import load_settings

ERROR_KEYS = {"stage", "code", "message", "retryable", "upstream_status"}
ANSWER = make_wav(0.5)
STUB = {"stub": stub_factory}


def app_on(fake: FakeSpeech, state: Path, dialogues: Mapping = STUB, **more: object) -> TestClient:
    return TestClient(
        create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues=dialogues, **more)
    )


@pytest.fixture
def phone(fake: FakeSpeech, state: Path) -> TestClient:
    return app_on(fake, state)


def start(phone: TestClient, **body: object) -> dict:
    response = phone.post("/api/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def events(phone: TestClient, sid: str, kind: str | None = None) -> list[dict]:
    log = phone.get(f"/api/sessions/{sid}").json()
    return [e for e in log["events"] if kind in (None, e["type"])]


def open_prompt(phone: TestClient, sid: str) -> int:
    return [e["seq"] for e in events(phone, sid, "bot") if not e["superseded"]][-1]


def post_turn(
    phone: TestClient,
    sid: str,
    audio: bytes | None = ANSWER,
    source: str = "file",
    reply_to: int | None = None,
    part: int = 1,
    query: str = "",
) -> httpx.Response:
    if reply_to is None:
        reply_to = open_prompt(phone, sid)
    url = f"/api/sessions/{sid}/turns?source={source}&reply_to={reply_to}&part={part}{query}"
    return phone.post(url, content=audio)


def say(phone: TestClient, sid: str, audio: bytes | None = ANSWER, source: str = "file", **more) -> dict:
    response = post_turn(phone, sid, audio, source, **more)
    assert response.status_code == 200, response.text
    return response.json()


def error_of(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert set(error) == ERROR_KEYS
    assert error["code"] == code
    return error


def utter(*texts: str, language: str = "hi-IN", **more: object) -> BotUtterance:
    return BotUtterance(lines=tuple(BotLine(text=t) for t in texts), language=language, **more)


class Scripted:
    """Stateless, as the protocol asks: the state is the number of customer turns applied.
    `script(n, heard)` is what the bot says after turn `n`; `steps` lists every step taken."""

    def __init__(self, script: Callable[[int, Heard | None], object]) -> None:
        self.script = script
        self.steps: list[tuple[int, Heard]] = []

    def start(self) -> Step:
        return Step(state="0", say=self.script(0, None))

    def step(self, state: str, heard: Heard) -> Step:
        turn = int(state) + 1
        self.steps.append((turn, heard))
        return Step(state=str(turn), say=self.script(turn, heard))


def echo(n: int, heard: Heard | None) -> BotUtterance:
    """Never ends; asks for a second reading after odd turns."""
    return utter(f"q{n} after {heard.text if heard else '-'}", second_reading=n % 2 == 1)


def scripted(script=echo) -> tuple[Scripted, dict]:
    dialogue = Scripted(script)

    def factory(params: Mapping[str, str]) -> Scripted:
        if "bad" in params:
            raise ValueError("secret detail")
        return dialogue

    return dialogue, {"scripted": factory}


def test_a_full_stub_call(phone: TestClient, fake: FakeSpeech) -> None:
    created = start(phone)
    sid = created["session_id"]
    assert (created["dialogue"], created["line_rate"]) == ("stub", 8000)
    assert created["bot"] == {
        "seq": 0,
        "text": StubDialogue.QUESTIONS[0],
        "lines": [
            {
                "key": "stub.q1",
                "text": StubDialogue.QUESTIONS[0],
                "audio_url": f"/api/sessions/{sid}/lines/0/0.wav",
            }
        ],
        "line_gap_ms": 150,
        "language": "hi-IN",
        "end_call": False,
        "audio_url": f"/api/sessions/{sid}/audio/bot-000.wav",
        "listen": {"kind": "amount", "cut_ms": 1000, "grace_ms": 1600},
        "second_reading": True,
    }
    bots = [created["bot"]]
    heard = []
    for n in range(3):
        assert phone.get(bots[-1]["audio_url"]).status_code == 200
        turn = say(phone, sid, make_wav(0.5 + n / 10))
        heard.append(turn["customer"]["transcript"])
        bots.append(turn["bot"])
        assert turn["ended"] is (n == 2) and turn["bot"]["end_call"] is (n == 2)
    assert heard == ["पचास हज़ार", "दो हज़ार", "बीमा"]
    assert bots[1]["text"] == "मैंने सुना: पचास हज़ार " + StubDialogue.QUESTIONS[1]
    assert [line["key"] for line in bots[1]["lines"]] == [None, "stub.q2"]
    assert [b["seq"] for b in bots] == [0, 2, 4, 6]
    assert phone.get(bots[-1]["audio_url"]).status_code == 200

    log = phone.get(f"/api/sessions/{sid}").json()
    assert (log["version"], log["status"], log["ended_reason"]) == (2, "ended", "dialogue")
    assert "dialogue_state" not in log and "dialogue_undo" not in log
    assert (log["stt"], log["tts"]) == (
        load_settings().stt.model_dump(),
        {"model": "timbre-v3.0", "voice": "Shivani"},
    )
    assert [e["type"] for e in log["events"]] == ["bot", "customer"] * 3 + ["bot"]
    assert [e["seq"] for e in log["events"]] == list(range(7))
    assert all(e["audio"] and e["rec_end"] > e["rec_start"] for e in log["events"])
    spoken = [line for e in log["events"] if e["type"] == "bot" for line in e["lines"]]
    assert all(line["tts"]["voice"] == "Shivani" for line in spoken)
    first = log["events"][1]
    assert (first["reply_to"], first["part"], first["source"]) == (0, 1, "file")
    assert [(r["role"], r["model"], r["mode"]) for r in first["readings"]] == [
        ("primary", "prisma-v3.0", "rest"),
        ("second", "prisma-v2.5", "rest"),
    ]
    assert first["readings"][0]["params"] == {"language_code": "hi-IN", "format": "transcribe"}
    assert first["pauses"]["speech_ms"] == 500
    # Only the first stub question asks for a second reading: four Prisma calls for three turns.
    assert [options for _, options in fake.stt_calls] == [
        PrismaV30(language="hi-IN", format="transcribe"),
        PrismaV25(language="hi-IN", format="transcribe"),
        PrismaV30(language="hi-IN", format="transcribe"),
        PrismaV30(language="hi-IN", format="transcribe"),
    ]

    recording = phone.get(f"/api/sessions/{sid}/recording.wav")
    assert recording.headers["content-type"] == "audio/wav"
    total = log["events"][-1]["rec_end"]
    assert wav_seconds(recording.content) == pytest.approx(total, abs=1e-6)
    assert log["recording"]["seconds"] == pytest.approx(total, abs=1e-6)
    # Bot turns 2, 4 and 6 are two lines each, joined with 0.15 s of silence.
    assert total == pytest.approx(0.4 + 3 * 0.95 + 0.5 + 0.6 + 0.7 + 6 * 0.5)

    summary = phone.post(f"/api/sessions/{sid}/end", json={"reason": "hangup"}).json()
    assert summary == {
        "session_id": sid,
        "status": "ended",
        "ended_reason": "dialogue",
        "events": 7,
        "turns": 3,
        "recording_seconds": log["recording"]["seconds"],
    }


def test_the_turn_response_shape(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    turn = say(phone, sid, source="mic", query="&eos_wait_ms=412.5&mode=vad&cut_ms=1000&grace_ms=1600")
    assert set(turn) == {"customer", "bot", "ended", "outcome", "speaker_confirmed"}
    assert (turn["outcome"], turn["speaker_confirmed"]) == (None, None)  # the stub says neither
    customer = turn["customer"]
    assert set(customer) == {
        "seq", "part", "transcript", "acted_on", "literal", "detected_language", "readings",
        "audio_url", "audio_seconds", "latency", "pauses", "readings_agreed", "followed_by", "degraded",
    }  # fmt: skip
    assert (customer["seq"], customer["part"], customer["transcript"]) == (1, 1, "पचास हज़ार")
    # The stub dialogue does not say whether the readings agreed, and its lines are no read-back.
    assert (customer["readings_agreed"], customer["followed_by"]) == (None, "other")
    assert [set(r) for r in customer["readings"]] == [
        {"role", "model", "ok", "error", "text", "cache_hit", "seconds"}
    ] * 2
    assert customer["readings"][1] == {
        "role": "second",
        "model": "prisma-v2.5",
        "ok": True,
        "error": None,
        "text": "पचास हज़ार",
        "cache_hit": False,
        "seconds": 0.01,
    }
    assert customer["audio_url"] == f"/api/sessions/{sid}/audio/customer-001.wav"
    assert customer["audio_seconds"] == 0.5
    assert set(customer["latency"]) == {
        "normalise_ms", "stt_ms", "second_stt_ms", "dialogue_ms", "server_ms", "eos_wait_ms",
    }  # fmt: skip
    assert customer["latency"]["eos_wait_ms"] == 412.5
    assert all(v >= 0 for v in customer["latency"].values())
    assert customer["pauses"] == {
        "speech_ms": 500,
        "leading_ms": 0,
        "trailing_ms": 0,
        "pauses_ms": [],
        "longest_pause_ms": 0,
    }
    assert set(turn["bot"]) == {
        "seq", "text", "lines", "line_gap_ms", "language", "end_call", "audio_url", "listen", "second_reading",
    }  # fmt: skip
    assert phone.get(customer["audio_url"]).content == ANSWER  # a canonical upload keeps its bytes
    logged = events(phone, sid, "customer")[0]
    assert logged["source"] == "mic"
    assert logged["phone"] == {"mode": "vad", "cut_ms": 1000, "grace_ms": 1600}


def test_the_pauses_of_a_turn_are_measured_on_the_stored_audio(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    clip = make_speech([(0.2, False), (0.5, True), (0.6, False), (0.5, True), (0.2, False)])
    assert say(phone, sid, clip)["customer"]["pauses"] == {
        "speech_ms": 1600,
        "leading_ms": 200,
        "trailing_ms": 200,
        "pauses_ms": [600],
        "longest_pause_ms": 600,
    }


def test_a_browser_recording_is_stored_at_the_line_rate(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone, line_rate=16000)["session_id"]
    turn = say(phone, sid, make_wav(1.0, 48000, channels=2), source="mic")
    stored = phone.get(turn["customer"]["audio_url"]).content
    assert wav_shape(stored)[:3] == (1, 2, 16000)
    assert fake.stt_calls[0][0] == stored
    assert wav_shape(phone.get(turn["bot"]["audio_url"]).content)[2] == 16000


def test_the_voice_and_the_speech_models_come_from_the_settings(fake: FakeSpeech, state: Path) -> None:
    base = load_settings()
    settings = base.model_copy(
        update={
            "stt": SttSettings(model="prisma-v2.5", second_model="prisma-v3.0", format="verbatim"),
            "tts": base.tts.model_copy(update={"voice": base.tts.voice | {"ta": "Kalpana"}}),
        }
    )
    phone = app_on(fake, state, settings=settings)
    tamil = start(phone, params={"language": "ta"})
    phone.get(tamil["bot"]["audio_url"])
    assert fake.tts_calls[0][1].voice == "Kalpana"
    other = start(phone, params={"language": "not a language"})
    assert phone.get(f"/api/sessions/{other['session_id']}").json()["tts"]["voice"] == "Shivani"
    say(phone, tamil["session_id"])
    assert [options for _, options in fake.stt_calls] == [
        PrismaV25(language="hi-IN", format="verbatim"),
        PrismaV30(language="hi-IN", format="transcribe"),
    ]
    assert phone.post("/api/sessions", json={"stt_model": "prisma-v2.5"}).status_code == 422


# --- bot audio ----------------------------------------------------------------


def test_bot_audio_is_synthesised_on_first_fetch_and_then_served_from_the_session(
    phone: TestClient, fake: FakeSpeech
) -> None:
    created = start(phone)
    sid, url = created["session_id"], created["bot"]["audio_url"]
    # The opening's line may already be made in the background; nothing is committed until fetched.
    assert len(fake.tts_calls) <= 1
    before = events(phone, sid)[0]
    assert (before["audio"], before["synth_ms"], before["lines"][0]["tts"]) == (None, None, None)

    first = phone.get(url)
    assert first.status_code == 200 and first.headers["content-type"] == "audio/wav"
    text, options = fake.tts_calls[0]
    assert text == StubDialogue.QUESTIONS[0]
    assert (options.model, options.voice, options.language) == ("timbre-v3.0", "Shivani", "hi-IN")
    assert (options.sample_rate, options.container) == (8000, "wav")

    assert phone.get(url).content == first.content
    assert len(fake.tts_calls) == 1
    event = events(phone, sid)[0]
    assert event["audio"] == "audio/bot-000.wav" and event["audio_seconds"] == 0.4
    assert event["synth_ms"] >= 0
    line = event["lines"][0]
    assert (line["start_s"], line["end_s"]) == (0.0, 0.4)
    assert line["tts"]["cache_hit"] is False and line["tts"]["est_credits"] > 0


def test_a_long_utterance_is_spoken_line_by_line_and_joined(fake: FakeSpeech, state: Path) -> None:
    lines = ["क" * 320 + "।", "ख" * 280 + "।", "क्या यह ठीक है?"]
    tones = {lines[0]: 200.0, lines[1]: 300.0, lines[2]: 400.0}
    lengths = {lines[0]: 0.6, lines[1]: 0.5, lines[2]: 0.3}
    _, dialogues = scripted(lambda n, heard: utter(*lines, listen="yes_no"))
    phone = app_on(fake, state, dialogues)
    fake.tts = wrap_tts(fake, lambda text, o: make_wav(lengths[text], o.sample_rate, tone=tones[text]))

    created = start(phone, dialogue="scripted")
    bot = created["bot"]
    assert len(bot["text"]) > 600 and bot["text"] == " ".join(lines)
    assert [line["text"] for line in bot["lines"]] == lines
    assert bot["listen"] == {"kind": "yes_no", "cut_ms": 700, "grace_ms": 1000}

    audio = phone.get(bot["audio_url"]).content
    assert [text for text, _ in fake.tts_calls] == lines
    assert wav_seconds(audio) == pytest.approx(0.6 + 0.15 + 0.5 + 0.15 + 0.3)
    event = events(phone, created["session_id"])[0]
    assert event["audio_seconds"] == pytest.approx(1.7)
    spans = [(line["start_s"], line["end_s"]) for line in event["lines"]]
    assert spans == [(0.0, 0.6), (0.75, 1.25), (1.4, 1.7)]
    pcm = audio[44:]
    for text, (begin, end) in zip(lines, spans, strict=True):
        assert (
            pcm[round(begin * 8000) * 2 : round(end * 8000) * 2]
            == make_wav(lengths[text], tone=tones[text])[44:]
        )
    assert pcm[round(0.6 * 8000) * 2 : round(0.75 * 8000) * 2] == bytes(2400)


def wrap_tts(fake: FakeSpeech, audio: Callable) -> Callable:
    """The fake's `tts`, with the clip chosen by the text spoken."""
    plain = FakeSpeech.tts.__get__(fake)

    def tts(text: str, options):
        fake.tts_audio = lambda o: audio(text, o)
        return plain(text, options)

    return tts


def test_a_line_shared_by_two_calls_is_synthesised_once(fake: FakeSpeech, state: Path) -> None:
    _, dialogues = scripted(lambda n, heard: utter("सबके लिए एक ही पंक्ति।", f"कॉल की अपनी पंक्ति {id(heard)}"))
    phone = app_on(fake, state, dialogues)
    logged = []
    for _ in range(2):
        created = start(phone, dialogue="scripted")
        assert phone.get(created["bot"]["audio_url"]).status_code == 200
        logged.append(events(phone, created["session_id"])[0]["lines"])
    assert [line["tts"]["cache_hit"] for line in logged[0]] == [False, False]
    assert [line["tts"]["cache_hit"] for line in logged[1]] == [True, True]
    assert logged[1][0]["tts"]["est_credits"] == 0
    shared = [options for text, options in fake.tts_calls if text == "सबके लिए एक ही पंक्ति।"]
    assert len(shared) == 2 and shared[0] == shared[1]  # the same request, so the client's cache hits


def test_timbre_audio_with_a_streaming_header_is_stored_repaired(phone: TestClient, fake: FakeSpeech) -> None:
    def streaming(options) -> bytes:
        wav = bytearray(make_wav(0.4, options.sample_rate))
        wav[4:8] = wav[40:44] = b"\xff\xff\xff\xff"
        return bytes(wav)

    fake.tts_audio = streaming
    stored = phone.get(start(phone)["bot"]["audio_url"]).content
    assert wav_shape(stored) == (1, 2, 8000, 3200)


def test_a_tts_failure_is_logged_and_the_fetch_can_be_repeated(phone: TestClient, fake: FakeSpeech) -> None:
    fake.tts_error = TransportError("ConnectTimeout on all 2 attempts")  # before the line is made
    created = start(phone)
    sid, url = created["session_id"], created["bot"]["audio_url"]
    error = error_of(phone.get(url), 504, "gnani_unreachable")
    assert (error["stage"], error["retryable"]) == ("tts", True)
    assert [(e["stage"], e["audio"]) for e in events(phone, sid, "error")] == [("tts", None)]
    fake.tts_error = None
    assert phone.get(url).status_code == 200
    assert say(phone, sid)["customer"]["seq"] == 2


def test_a_failed_prompt_fetched_many_times_is_logged_once(phone: TestClient, fake: FakeSpeech) -> None:
    fake.tts_error = ServerError(status=503, code="DOWN", message="timbre is down", attempts=2)
    created = start(phone)  # the error is armed before the opening's line is made
    for _ in range(5):
        error_of(phone.get(created["bot"]["audio_url"]), 502, "gnani_server_error")
    assert len(events(phone, created["session_id"], "error")) == 1


def test_timbre_audio_that_is_not_a_wav_is_a_bad_response(phone: TestClient, fake: FakeSpeech) -> None:
    fake.tts_audio = lambda options: b"ID3 not a wav"
    error_of(phone.get(start(phone)["bot"]["audio_url"]), 502, "gnani_bad_response")


# --- turns: nothing said, limits, bad requests ---------------------------------


def test_nothing_said(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    turn = say(phone, sid, None, "none")
    customer = turn["customer"]
    assert (customer["transcript"], customer["audio_url"], customer["audio_seconds"]) == ("", None, None)
    assert (customer["readings"], customer["pauses"]) == ([], None)
    assert turn["bot"]["text"].startswith(StubDialogue.NOTHING_HEARD)
    assert fake.stt_calls == []
    event = events(phone, sid, "customer")[0]
    assert (event["source"], event["audio"], event["rec_start"]) == ("none", None, None)


def test_empty_stt_text_is_passed_to_the_dialogue(phone: TestClient, fake: FakeSpeech) -> None:
    fake.transcripts = [""]
    turn = say(phone, start(phone)["session_id"])
    assert turn["customer"]["transcript"] == ""
    assert turn["bot"]["text"].startswith(StubDialogue.NOTHING_HEARD)


def test_a_body_over_the_limit_is_refused_with_content_length(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    response = post_turn(phone, sid, b"\0" * (MAX_TURN_BYTES + 1), "mic")
    error = error_of(response, 413, "audio_too_large")
    assert (error["stage"], error["retryable"]) == ("audio", False)
    assert fake.stt_calls == []
    assert [e["code"] for e in events(phone, sid, "error")] == ["audio_too_large"]


def test_a_body_over_the_limit_is_refused_without_content_length(phone: TestClient) -> None:
    sid = start(phone)["session_id"]

    def chunks() -> Iterator[bytes]:
        for _ in range(MAX_TURN_BYTES // 65536 + 1):
            yield b"\0" * 65536

    response = post_turn(phone, sid, chunks(), "mic", reply_to=0)
    assert "content-length" not in response.request.headers
    error_of(response, 413, "audio_too_large")
    assert events(phone, sid, "customer") == []


def test_a_body_at_the_limit_is_read(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    error_of(post_turn(phone, sid, b"\0" * MAX_TURN_BYTES, "mic"), 422, "audio_unreadable")


def test_a_json_body_over_its_limit_is_refused(phone: TestClient) -> None:
    big = {"params": {"k": "x" * MAX_JSON_BYTES}}
    error_of(phone.post("/api/sessions", json=big), 413, "body_too_large")
    chunked = phone.post("/api/sessions", content=iter([b" " * 4096] * 8))
    error_of(chunked, 413, "body_too_large")


@pytest.mark.parametrize(
    "body",
    [b"[", b"[]", b'{"line_rate": 44100}', b'{"dialogue": 3}', b'{"nope": 1}', b'{"params": {"a": 1}}'],
)
def test_a_bad_create_body_is_a_request_error(phone: TestClient, body: bytes) -> None:
    error = error_of(phone.post("/api/sessions", content=body), 422, "invalid_request")
    assert error["stage"] == "request"


def test_create_takes_an_empty_body_and_refuses_an_unknown_dialogue(phone: TestClient) -> None:
    assert phone.post("/api/sessions").status_code == 201
    error_of(phone.post("/api/sessions", json={"dialogue": "nope"}), 422, "unknown_dialogue")


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("reply_to=0", "invalid_source"),
        ("source=&reply_to=0", "invalid_source"),
        ("source=tape&reply_to=0", "invalid_source"),
        ("source=MIC&reply_to=0", "invalid_source"),
        ("source=mic", "reply_to_required"),
        ("source=mic&reply_to=x", "invalid_reply_to"),
        ("source=mic&reply_to=-1", "invalid_reply_to"),
        ("source=mic&reply_to=1000", "invalid_reply_to"),
        ("source=mic&reply_to=0&part=0", "invalid_part"),
        ("source=mic&reply_to=0&part=two", "invalid_part"),
        ("source=mic&reply_to=0&eos_wait_ms=abc", "invalid_eos_wait_ms"),
        ("source=mic&reply_to=0&eos_wait_ms=nan", "invalid_eos_wait_ms"),
        ("source=mic&reply_to=0&eos_wait_ms=-1", "invalid_eos_wait_ms"),
        ("source=mic&reply_to=0&eos_wait_ms=inf", "invalid_eos_wait_ms"),
        ("source=mic&reply_to=0&mode=guess", "invalid_mode"),
        ("source=mic&reply_to=0&cut_ms=700", "invalid_mode"),
        ("source=mic&reply_to=0&mode=vad&cut_ms=-5", "invalid_cut_ms"),
        ("source=mic&reply_to=0&mode=vad&grace_ms=1e9", "invalid_grace_ms"),
    ],
)
def test_a_turn_with_a_bad_query_is_refused_before_anything_happens(
    phone: TestClient, fake: FakeSpeech, query: str, code: str
) -> None:
    sid = start(phone)["session_id"]
    error = error_of(phone.post(f"/api/sessions/{sid}/turns?{query}", content=ANSWER), 422, code)
    assert error["stage"] == "request"
    assert len(events(phone, sid)) == 1 and fake.stt_calls == []


def test_the_turn_limit(fake: FakeSpeech, state: Path) -> None:
    _, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    for n in range(MAX_TURNS):
        assert post_turn(phone, sid, None, "none", reply_to=2 * n).status_code == 200
    assert MAX_TURNS == 60
    # The last turn can still be replaced by a later take; a turn past the limit cannot be added.
    assert post_turn(phone, sid, None, "none", reply_to=2 * MAX_TURNS - 2, part=2).status_code == 200
    error = error_of(post_turn(phone, sid, None, "none"), 409, "turn_limit")
    assert error["stage"] == "session"
    assert phone.get("/api/health").json()["limits"]["max_turns"] == MAX_TURNS


# --- exactly once ---------------------------------------------------------------


def test_a_turn_sent_again_gets_the_stored_reply_and_does_not_advance(fake: FakeSpeech, state: Path) -> None:
    dialogue, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    first = say(phone, sid, reply_to=0)
    again = post_turn(phone, sid, make_wav(0.9), reply_to=0)
    assert again.status_code == 200 and again.json() == first
    assert len(fake.stt_calls) == 1 and len(events(phone, sid)) == 3 and len(dialogue.steps) == 1
    second = say(phone, sid, reply_to=2)
    # An earlier turn that was answered can still be asked for again, and nothing moves.
    assert say(phone, sid, reply_to=0) == first and say(phone, sid, reply_to=2) == second
    assert [n for n, _ in dialogue.steps] == [1, 2] and len(events(phone, sid)) == 5
    for missing in (1, 3, 6, 40):
        error_of(post_turn(phone, sid, reply_to=missing), 409, "turn_out_of_order")


def test_the_closing_turn_can_be_sent_again_after_the_call_has_ended(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    for prompt in (0, 2, 4):
        last = say(phone, sid, reply_to=prompt)
    assert last["ended"]
    assert say(phone, sid, reply_to=4) == last
    error = error_of(post_turn(phone, sid, reply_to=6), 409, "session_not_active")
    assert error["stage"] == "session"
    assert len(events(phone, sid)) == 7


def test_eight_identical_requests_at_once_advance_the_dialogue_once(fake: FakeSpeech, state: Path) -> None:
    dialogue, dialogues = scripted()
    fake.model_delays["prisma-v3.0"] = 0.05
    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues=dialogues)

    async def call() -> tuple[str, list[httpx.Response], dict]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
            sid = (await http.post("/api/sessions", json={"dialogue": "scripted"})).json()["session_id"]
            url = f"/api/sessions/{sid}/turns?source=mic&reply_to=0&part=1"
            replies = await asyncio.gather(*(http.post(url, content=ANSWER) for _ in range(8)))
            return sid, replies, (await http.get(f"/api/sessions/{sid}")).json()

    _sid, replies, log = asyncio.run(call())
    assert [r.status_code for r in replies] == [200] * 8
    assert all(r.json() == replies[0].json() for r in replies)
    assert len(dialogue.steps) == 1 and len(fake.stt_calls) == 1
    assert [e["type"] for e in log["events"]] == ["bot", "customer", "bot"]


def test_a_turn_that_failed_before_its_save_is_replayed_cleanly(
    fake: FakeSpeech, state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialogue, dialogues = scripted()
    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues=dialogues)
    phone = TestClient(app, raise_server_exceptions=False)
    sid = start(phone, dialogue="scripted")["session_id"]
    say(phone, sid)
    before = phone.get(f"/api/sessions/{sid}").json()

    def killed(self, log) -> None:
        raise OSError("the process died here")

    with monkeypatch.context() as patch:
        patch.setattr(SessionStore, "save", killed)
        assert post_turn(phone, sid, make_wav(0.7), reply_to=2).status_code == 500
    # The turn's audio reached the disk, its events and the new state did not.
    assert (state / "sessions" / sid / "audio" / "customer-003.wav").exists()
    assert phone.get(f"/api/sessions/{sid}").json() == before

    for client in (phone, app_on(fake, state, dialogues)):  # the same run, and a later one
        turn = say(client, sid, make_wav(0.7), reply_to=2)
        assert (turn["customer"]["seq"], turn["bot"]["text"]) == (3, "q2 after दो हज़ार")
    assert [n for n, _ in dialogue.steps] == [1, 2, 2]  # stepped again from the same stored state
    assert [e["type"] for e in events(phone, sid)] == ["bot", "customer", "bot", "customer", "bot"]


# --- a later take of the same turn ---------------------------------------------


def test_a_later_take_replaces_the_earlier_one(fake: FakeSpeech, state: Path) -> None:
    dialogue, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    created = start(phone, dialogue="scripted")
    sid = created["session_id"]
    phone.get(created["bot"]["audio_url"])
    say(phone, sid, make_wav(0.5), reply_to=0)

    take_one = say(phone, sid, make_wav(0.6), reply_to=2)
    assert take_one["bot"]["text"] == "q2 after दो हज़ार"
    phone.get(take_one["bot"]["audio_url"])  # the phone had begun to play the reply
    take_two = say(phone, sid, make_wav(1.3), reply_to=2, part=2)
    assert (take_two["customer"]["seq"], take_two["customer"]["part"]) == (5, 2)
    assert take_two["customer"]["transcript"] == "बीमा"
    assert take_two["bot"]["seq"] == 6 and take_two["bot"]["text"] == "q2 after बीमा"
    # Both takes were turn 2 of the dialogue: the second was heard from the state before the first.
    assert [(n, heard.text) for n, heard in dialogue.steps] == [(1, "पचास हज़ार"), (2, "दो हज़ार"), (2, "बीमा")]

    log = phone.get(f"/api/sessions/{sid}").json()
    assert [(e["type"], e["superseded"]) for e in log["events"]] == [
        ("bot", False),
        ("customer", False),
        ("bot", False),
        ("customer", True),
        ("bot", True),
        ("customer", False),
        ("bot", False),
    ]
    assert [e["rec_start"] for e in log["events"]] == [0.0, 0.9, None, None, None, 1.9, None]
    recording = phone.get(f"/api/sessions/{sid}/recording.wav").content
    assert wav_seconds(recording) == pytest.approx(0.4 + 0.5 + 0.5 + 0.5 + 1.3)
    assert recording[44:][round(1.9 * 8000) * 2 :] == make_wav(1.3)[44:]

    assert say(phone, sid, make_wav(1.3), reply_to=2, part=2) == take_two  # a repeat of the later take
    error_of(post_turn(phone, sid, make_wav(0.6), reply_to=2, part=1), 409, "turn_superseded")
    error_of(phone.get(take_one["bot"]["audio_url"].replace("bot-004", "bot-009")), 404, "audio_not_found")
    # The call goes on from the later take, and the turn before it can no longer be replaced.
    assert say(phone, sid, reply_to=6)["bot"]["text"] == "q3 after पचास हज़ार"
    error_of(post_turn(phone, sid, reply_to=2, part=3), 409, "turn_out_of_order")
    error_of(post_turn(phone, sid, reply_to=4, part=1), 409, "turn_out_of_order")
    assert len(dialogue.steps) == 4


def test_a_reply_that_was_superseded_before_it_was_spoken_is_never_spoken(
    fake: FakeSpeech, state: Path
) -> None:
    _, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    take_one = say(phone, sid, reply_to=0)
    say(phone, sid, make_wav(0.9), reply_to=0, part=2)
    error_of(phone.get(take_one["bot"]["audio_url"]), 409, "turn_superseded")
    for line in take_one["bot"]["lines"]:
        error_of(phone.get(line["audio_url"]), 409, "turn_superseded")
    log = phone.get(f"/api/sessions/{sid}").json()
    superseded = log["events"][take_one["bot"]["seq"]]
    assert superseded["superseded"] and superseded["audio"] is None
    assert all(line["tts"] is None for line in superseded["lines"])
    # Bounded waste: at most that one utterance's lines were made for it, each once.
    wasted = [
        text for text, _ in fake.tts_calls if text in {line["text"] for line in take_one["bot"]["lines"]}
    ]
    assert len(wasted) <= len(take_one["bot"]["lines"])


def test_a_later_take_reopens_a_call_that_the_earlier_take_had_ended(fake: FakeSpeech, state: Path) -> None:
    def script(n: int, heard: Heard | None) -> BotUtterance:
        return utter(f"q{n}", end_call=heard is not None and heard.text == "बस")

    fake.transcripts = ["बस", "बस इतना ही नहीं, और भी है", "बस"]
    _, dialogues = scripted(script)
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    assert say(phone, sid, make_wav(0.4), reply_to=0)["ended"]
    ended = phone.get(f"/api/sessions/{sid}").json()
    assert (ended["status"], ended["ended_reason"]) == ("ended", "dialogue") and ended["recording"]

    take_two = say(phone, sid, make_wav(1.5), reply_to=0, part=2)
    assert not take_two["ended"]
    reopened = phone.get(f"/api/sessions/{sid}").json()
    assert (reopened["status"], reopened["ended_reason"], reopened["recording"]) == ("active", None, None)
    assert say(phone, sid, make_wav(0.3), reply_to=take_two["bot"]["seq"])["ended"]
    assert phone.get(f"/api/sessions/{sid}").json()["recording"]["seconds"] == pytest.approx(1.5 + 0.5 + 0.3)


def test_no_later_take_once_the_call_is_closed_or_hung_up(fake: FakeSpeech, state: Path) -> None:
    dialogue, dialogues = scripted(lambda n, heard: utter(f"q{n}", end_call=n == 1))
    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues=dialogues)
    phone = TestClient(app)
    closed = start(phone, dialogue="scripted")["session_id"]
    first = say(phone, closed, reply_to=0)

    async def close() -> None:  # what the after-call job does when it starts
        sessions = sessions_of(app)
        async with sessions.locked(closed) as log:
            log.closed = True
            sessions.save(log)

    asyncio.run(close())
    error = error_of(post_turn(phone, closed, make_wav(0.9), reply_to=0, part=2), 409, "turn_out_of_order")
    assert "closed" in error["message"]
    assert say(phone, closed, reply_to=0) == first  # the stored reply is still given
    error_of(phone.get(first["bot"]["audio_url"]), 409, "session_not_active")  # the recording is final
    assert SessionStore(state / "sessions").load(closed).closed is True

    _, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    hung_up = start(phone, dialogue="scripted")["session_id"]
    say(phone, hung_up, reply_to=0)
    phone.post(f"/api/sessions/{hung_up}/end")
    error_of(post_turn(phone, hung_up, make_wav(0.9), reply_to=0, part=2), 409, "session_not_active")
    assert len(dialogue.steps) == 1


def test_a_first_take_may_carry_any_part_number(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    turn = say(phone, sid, reply_to=0, part=3)  # takes 1 and 2 never reached the server
    assert turn["customer"]["part"] == 3
    error_of(post_turn(phone, sid, reply_to=0, part=2), 409, "turn_superseded")


# --- a call continues in a later server run -------------------------------------


def run_call(first: TestClient, later: TestClient, clips: list[bytes], switch_after: int) -> dict:
    """A whole stub call, the first `switch_after` turns on one server and the rest on another."""
    created = start(first)
    sid, bot = created["session_id"], created["bot"]
    texts = [bot["text"]]
    for n, clip in enumerate(clips):
        phone = first if n < switch_after else later
        assert phone.get(bot["audio_url"]).status_code == 200
        bot = say(phone, sid, clip, reply_to=bot["seq"])["bot"]
        texts.append(bot["text"])
    assert later.get(bot["audio_url"]).status_code == 200
    return {"texts": texts, "log": later.get(f"/api/sessions/{sid}").json(), "sid": sid}


def test_a_call_continues_in_a_later_server_run_as_if_uninterrupted(
    fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    clips = [make_wav(0.5), make_wav(0.6), make_wav(0.7)]
    whole_phone = app_on(fake, tmp_path / "uninterrupted")
    whole = run_call(whole_phone, whole_phone, clips, 3)

    resumed = run_call(app_on(fake, state), app_on(fake, state), clips, 1)
    assert resumed["texts"] == whole["texts"] and resumed["texts"][-1].endswith(StubDialogue.CLOSING)

    def shape(log: dict) -> list:
        return [
            (e["type"], e["seq"], e.get("text") or e.get("transcript"), e["audio_seconds"], e["rec_start"])
            for e in log["events"]
        ]

    log = resumed["log"]
    assert shape(log) == shape(whole["log"])
    assert (log["status"], log["ended_reason"]) == ("ended", "dialogue")
    assert log["recording"]["seconds"] == whole["log"]["recording"]["seconds"]
    at = [e["at"] for e in log["events"]]
    assert at == sorted(at)  # still seconds since the session was created

    third = app_on(fake, state)
    assert third.get(f"/api/sessions/{resumed['sid']}").json() == log
    recording = third.get(f"/api/sessions/{resumed['sid']}/recording.wav").content
    assert wav_seconds(recording) == log["recording"]["seconds"]
    assert third.post(f"/api/sessions/{resumed['sid']}/end").json()["ended_reason"] == "dialogue"


def test_a_later_run_gives_stored_replies_takes_later_takes_and_hangs_up(
    fake: FakeSpeech, state: Path
) -> None:
    dialogue, dialogues = scripted()
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    first = say(phone, sid, make_wav(0.5), reply_to=0)

    later = app_on(fake, state, dialogues)
    assert say(later, sid, make_wav(0.5), reply_to=0) == first
    take_two = say(later, sid, make_wav(1.1), reply_to=0, part=2)
    assert take_two["bot"]["text"] == "q1 after दो हज़ार"
    assert [n for n, _ in dialogue.steps] == [1, 1]
    # A prompt that an earlier run never spoke is spoken by whichever run is asked for it.
    assert later.get(take_two["bot"]["audio_url"]).status_code == 200

    last = app_on(fake, state, dialogues)
    summary = last.post(f"/api/sessions/{sid}/end").json()
    assert (summary["status"], summary["ended_reason"], summary["turns"]) == ("ended", "hangup", 1)
    assert last.post(f"/api/sessions/{sid}/end").json() == summary
    error_of(post_turn(last, sid, reply_to=take_two["bot"]["seq"]), 409, "session_not_active")


def test_a_session_of_a_dialogue_this_server_does_not_have_can_be_read_and_ended_only(
    fake: FakeSpeech, state: Path
) -> None:
    _, dialogues = scripted()
    sid = start(app_on(fake, state, dialogues), dialogue="scripted")["session_id"]
    later = app_on(fake, state)  # only the stub is registered
    assert later.get(f"/api/sessions/{sid}").json()["dialogue"] == "scripted"
    error_of(post_turn(later, sid, reply_to=0), 409, "session_not_active")
    assert later.post(f"/api/sessions/{sid}/end").json()["ended_reason"] == "hangup"


def test_a_log_that_does_not_parse_is_not_found(fake: FakeSpeech, state: Path) -> None:
    sid = start(app_on(fake, state))["session_id"]
    (state / "sessions" / sid / "session.json").write_text('{"version": 1}')
    later = app_on(fake, state)
    error_of(later.get(f"/api/sessions/{sid}"), 404, "session_not_found")
    error_of(post_turn(later, sid, reply_to=0), 404, "session_not_found")
    error_of(later.post(f"/api/sessions/{sid}/end"), 404, "session_not_found")


def test_sessions_dropped_from_memory_are_read_back_from_their_logs(
    phone: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("samajh.server.app.MAX_LIVE_SESSIONS", 2)
    sids = [start(phone)["session_id"] for _ in range(4)]
    for sid in sids:
        assert say(phone, sid, reply_to=0)["bot"]["seq"] == 2
    for sid in sids:
        assert say(phone, sid, None, "none", reply_to=2)["bot"]["seq"] == 4
        assert len(events(phone, sid)) == 5


# --- two readings ----------------------------------------------------------------


def heard_by(fake: FakeSpeech, state: Path, **more: object) -> tuple[TestClient, str, Scripted]:
    """A call whose opening prompt does not ask for a second reading and whose next one does."""
    dialogue, dialogues = scripted()
    phone = app_on(fake, state, dialogues, **more)
    sid = start(phone, dialogue="scripted")["session_id"]
    say(phone, sid, make_wav(0.3), reply_to=0)
    return phone, sid, dialogue


def test_a_turn_that_was_not_asked_for_a_second_reading_makes_one_stt_call(
    fake: FakeSpeech, state: Path
) -> None:
    phone, sid, dialogue = heard_by(fake, state)
    assert [options.model for _, options in fake.stt_calls] == ["prisma-v3.0"]
    assert dialogue.steps[0][1] == Heard(text="पचास हज़ार", detected_language="hi-IN", second=None)
    customer = events(phone, sid, "customer")[0]
    assert [r["role"] for r in customer["readings"]] == ["primary"]
    assert customer["latency"]["second_stt_ms"] == 0


def test_two_readings_that_agree(fake: FakeSpeech, state: Path) -> None:
    phone, sid, dialogue = heard_by(fake, state)
    turn = say(phone, sid, make_wav(0.8), reply_to=2)
    assert [(r["role"], r["model"], r["ok"], r["text"]) for r in turn["customer"]["readings"]] == [
        ("primary", "prisma-v3.0", True, "दो हज़ार"),
        ("second", "prisma-v2.5", True, "दो हज़ार"),
    ]
    assert dialogue.steps[1][1] == Heard(text="दो हज़ार", detected_language="hi-IN", second="दो हज़ार")
    assert [options.model for _, options in fake.stt_calls[1:]] == ["prisma-v3.0", "prisma-v2.5"]
    assert fake.stt_calls[1][0] == fake.stt_calls[2][0]  # the same audio, one model after the other
    logged = events(phone, sid, "customer")[1]["readings"][1]
    assert logged["params"] == {"language_code": "hi-IN", "format": "transcribe"}
    assert logged["literal"] == "शब्दों में"


def test_two_readings_that_disagree(fake: FakeSpeech, state: Path) -> None:
    fake.model_transcripts["prisma-v2.5"] = ["दो हज़ार पाँच सौ"]
    phone, sid, dialogue = heard_by(fake, state)
    turn = say(phone, sid, make_wav(0.8), reply_to=2)
    assert [r["text"] for r in turn["customer"]["readings"]] == ["दो हज़ार", "दो हज़ार पाँच सौ"]
    assert turn["customer"]["transcript"] == "दो हज़ार"  # the dialogue acts on the primary reading
    assert (dialogue.steps[1][1].text, dialogue.steps[1][1].second) == ("दो हज़ार", "दो हज़ार पाँच सौ")


def test_a_second_reading_that_fails_is_logged_and_does_not_fail_the_turn(
    fake: FakeSpeech, state: Path
) -> None:
    fake.model_errors["prisma-v2.5"] = ServerError(status=504, code="TIMEOUT", message="x", attempts=1)
    phone, sid, dialogue = heard_by(fake, state)
    turn = say(phone, sid, make_wav(0.8), reply_to=2)
    assert turn["customer"]["readings"][1] == {
        "role": "second",
        "model": "prisma-v2.5",
        "ok": False,
        "error": "gnani_server_error",
        "text": "",
        "cache_hit": False,
        "seconds": turn["customer"]["readings"][1]["seconds"],
    }
    assert (dialogue.steps[1][1].text, dialogue.steps[1][1].second) == ("दो हज़ार", "")
    assert turn["bot"]["text"] == "q2 after दो हज़ार" and events(phone, sid, "error") == []


def test_a_second_reading_that_is_late_is_given_up_at_the_bound(fake: FakeSpeech, state: Path) -> None:
    settings = load_settings().model_copy(update={"stt": SttSettings(second_timeout_s=0.2)})
    fake.model_delays["prisma-v2.5"] = 1.5
    phone, sid, dialogue = heard_by(fake, state, settings=settings)
    started = time.monotonic()
    turn = say(phone, sid, make_wav(0.8), reply_to=2)
    assert time.monotonic() - started < 1.0
    second = turn["customer"]["readings"][1]
    assert (second["ok"], second["error"], second["text"]) == (False, "timeout", "")
    assert 0.2 <= second["seconds"] < 1.0
    assert 200 <= turn["customer"]["latency"]["second_stt_ms"] < 1000
    assert dialogue.steps[1][1].second == ""
    assert turn["bot"]["text"] == "q2 after दो हज़ार"


def test_a_separate_client_can_serve_the_second_reading(fake: FakeSpeech, state: Path) -> None:
    other = FakeSpeech(["दूसरा"])
    phone, sid, dialogue = heard_by(fake, state, second=other)
    say(phone, sid, make_wav(0.8), reply_to=2)
    assert [options.model for _, options in other.stt_calls] == ["prisma-v2.5"]
    assert [options.model for _, options in fake.stt_calls] == ["prisma-v3.0"] * 2
    assert dialogue.steps[1][1].second == "दूसरा"


# --- failures -------------------------------------------------------------------


def test_an_stt_failure_leaves_the_dialogue_where_it_was(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    fake.stt_error = ServerError(status=503, code="UPSTREAM", message="down", attempts=2)
    error = error_of(post_turn(phone, sid, source="mic"), 502, "gnani_server_error")
    assert error == {
        "stage": "stt",
        "code": "gnani_server_error",
        "message": "UPSTREAM: down",
        "retryable": True,
        "upstream_status": 503,
    }
    logged = events(phone, sid)
    assert [e["type"] for e in logged] == ["bot", "error"]
    failed = logged[1]
    assert (failed["stage"], failed["status"], failed["code"]) == ("stt", 502, "gnani_server_error")
    assert (failed["audio"], failed["audio_seconds"], failed["rec_start"]) == (
        "audio/customer-001.wav",
        0.5,
        None,
    )
    assert phone.get(f"/api/sessions/{sid}/audio/customer-001.wav").content == ANSWER

    fake.stt_error = None
    again = say(phone, sid, reply_to=0)
    assert again["customer"]["seq"] == 2
    assert again["bot"]["text"] == "मैंने सुना: पचास हज़ार " + StubDialogue.QUESTIONS[1]
    assert [e["type"] for e in events(phone, sid)] == ["bot", "error", "customer", "bot"]
    # The failed attempt's audio stays out of the recording.
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == 0.5


def test_an_unreadable_upload_is_logged_and_the_turn_can_be_sent_again(
    phone: TestClient, fake: FakeSpeech
) -> None:
    sid = start(phone)["session_id"]
    error = error_of(post_turn(phone, sid, b"junk", "mic"), 422, "audio_unreadable")
    assert error["stage"] == "audio"
    error_of(post_turn(phone, sid, None, "mic"), 422, "audio_unreadable")
    error_of(post_turn(phone, sid, make_wav(0.05), "mic"), 422, "audio_too_short")
    error_of(post_turn(phone, sid, make_wav(30.5), "mic"), 422, "audio_too_long")
    assert fake.stt_calls == []
    logged = events(phone, sid, "error")
    assert [e["stage"] for e in logged] == ["audio"] * 4 and all(e["audio"] is None for e in logged)
    assert say(phone, sid)["bot"]["text"].endswith(StubDialogue.QUESTIONS[1])


def test_a_dialogue_exception_is_logged_by_class_name_and_does_not_advance(
    fake: FakeSpeech, state: Path
) -> None:
    broken = True

    def script(n: int, heard: Heard | None) -> BotUtterance:
        if n and broken:
            raise RuntimeError("secret /path/to/thing")
        return utter(f"question {n}", language="en-IN")

    dialogue, dialogues = scripted(script)
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted")["session_id"]
    error = error_of(post_turn(phone, sid, source="mic"), 500, "dialogue_failed")
    assert (error["stage"], error["message"], error["retryable"]) == ("dialogue", "RuntimeError", False)
    failed = events(phone, sid)[-1]
    assert (failed["type"], failed["stage"], failed["audio"]) == (
        "error",
        "dialogue",
        "audio/customer-001.wav",
    )
    assert "secret" not in phone.get(f"/api/sessions/{sid}").text

    broken = False
    assert say(phone, sid, reply_to=0)["bot"]["text"] == "question 1"
    assert [n for n, _ in dialogue.steps] == [1, 1]
    assert len(fake.stt_calls) == 2 and fake.stt_calls[0][1].language == "en-IN"


def test_a_dialogue_that_fails_at_the_start_creates_no_session(fake: FakeSpeech, state: Path) -> None:
    def script(n: int, heard: Heard | None) -> BotUtterance:
        raise RuntimeError("boom")

    _, dialogues = scripted(script)
    phone = app_on(fake, state, dialogues)
    error = error_of(phone.post("/api/sessions", json={"dialogue": "scripted"}), 500, "dialogue_failed")
    assert error["message"] == "RuntimeError"
    assert not (state / "sessions").exists()
    bad = phone.post("/api/sessions", json={"dialogue": "scripted", "params": {"bad": "1"}})
    assert "secret" not in error_of(bad, 422, "invalid_params")["message"]
    health = phone.get("/api/health").json()
    assert (health["dialogues"], health["default_dialogue"]) == (["scripted"], "scripted")


@pytest.mark.parametrize(
    "said",
    [
        "not an utterance",
        utter("any language", language="auto", second_reading=True),  # prisma-v2.5 has no auto
    ],
)
def test_an_utterance_the_session_cannot_handle_is_a_dialogue_error(
    fake: FakeSpeech, state: Path, said
) -> None:
    class Wrong:
        def start(self):
            return Step(state="0", say=said) if isinstance(said, BotUtterance) else said

    phone = app_on(fake, state, {"wrong": lambda params: Wrong()})
    error_of(phone.post("/api/sessions", json={"dialogue": "wrong"}), 500, "dialogue_failed")


def test_tags_and_params_reach_the_log(fake: FakeSpeech, state: Path) -> None:
    line = BotLine(text="प्रश्न", key="q.loan_amount", tags={"asks": "amount"})
    said = BotUtterance(lines=(line,), language="hi-IN", tags={"outcome": "open"}, listen="short")
    _, dialogues = scripted(lambda n, heard: said)
    phone = app_on(fake, state, dialogues)
    sid = start(phone, dialogue="scripted", params={"scenario": "A1"})["session_id"]
    log = phone.get(f"/api/sessions/{sid}").json()
    event = log["events"][0]
    assert (log["params"], event["tags"], event["listen"]) == (
        {"scenario": "A1"},
        {"outcome": "open"},
        "short",
    )
    assert (event["lines"][0]["key"], event["lines"][0]["tags"]) == ("q.loan_amount", {"asks": "amount"})


# --- hanging up, the recording --------------------------------------------------


def test_hanging_up_ends_the_call_and_is_idempotent(phone: TestClient) -> None:
    created = start(phone)
    sid = created["session_id"]
    phone.get(created["bot"]["audio_url"])
    say(phone, sid)
    first = phone.post(f"/api/sessions/{sid}/end", json={"reason": "hangup"})
    assert first.status_code == 200
    assert first.json() == {
        "session_id": sid,
        "status": "ended",
        "ended_reason": "hangup",
        "events": 3,
        "turns": 1,
        "recording_seconds": pytest.approx(0.4 + 0.5 + 0.5),
    }
    assert phone.post(f"/api/sessions/{sid}/end").json() == first.json()
    error_of(post_turn(phone, sid, None, "none"), 409, "session_not_active")
    error_of(phone.post(f"/api/sessions/{sid}/end", json={"reason": "bored"}), 422, "invalid_request")


def test_the_closing_prompt_fetched_after_the_end_refreshes_the_recording(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    for _ in range(3):
        last = say(phone, sid)
    assert last["ended"]
    before = phone.get(f"/api/sessions/{sid}").json()["recording"]["seconds"]
    assert before == pytest.approx(3 * 0.5 + 2 * 0.5)  # three answers, two gaps, no prompt fetched
    assert phone.get(last["bot"]["audio_url"]).status_code == 200
    log = phone.get(f"/api/sessions/{sid}").json()
    assert log["recording"]["seconds"] == pytest.approx(before + 0.5 + 0.95)
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == log["recording"]["seconds"]


def test_nothing_is_spoken_after_a_hang_up(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    turn = say(phone, sid)
    assert phone.post(f"/api/sessions/{sid}/end").json()["recording_seconds"] == 0.5
    error_of(phone.get(turn["bot"]["audio_url"]), 409, "session_not_active")
    for line in turn["bot"]["lines"]:
        error_of(phone.get(line["audio_url"]), 409, "session_not_active")
    log = phone.get(f"/api/sessions/{sid}").json()
    assert log["events"][turn["bot"]["seq"]]["audio"] is None
    assert log["recording"]["seconds"] == 0.5  # the customer's turn only: no bot audio was added
    # Bounded waste: nothing beyond the opening and the lines of the one reply, each once.
    allowed = [StubDialogue.QUESTIONS[0], *(line["text"] for line in turn["bot"]["lines"])]
    made = [text for text, _ in fake.tts_calls]
    assert set(made) <= set(allowed) and len(made) <= len(allowed)


def test_a_recording_of_a_call_in_progress_is_assembled_on_demand(phone: TestClient) -> None:
    created = start(phone)
    sid = created["session_id"]
    phone.get(created["bot"]["audio_url"])
    say(phone, sid)
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == pytest.approx(1.4)
    log = phone.get(f"/api/sessions/{sid}").json()
    assert log["status"] == "active" and log["recording"] is None


# --- what may be reached ---------------------------------------------------------

SID_ATTACKS = [
    "..",
    "%2e%2e",
    "..%2f..%2fetc",
    "..%2F20261110T142233-9f2c4e1ab07d",
    "20261110T142233-9f2c4e1ab07d%2f..",
    "20261110T142233-9F2C4E1AB07D",
    "20261110T142233-9f2c4e1ab07d%0a",
    "20261110T142233-000000000000",
    "x" * 300,
]


@pytest.mark.parametrize("sid", SID_ATTACKS)
def test_a_malformed_or_unknown_session_id_is_not_found(phone: TestClient, state: Path, sid: str) -> None:
    start(phone)
    state.parent.joinpath("secret.wav").write_bytes(b"SECRET")
    requests = [
        phone.get(f"/api/sessions/{sid}"),
        phone.get(f"/api/sessions/{sid}/recording.wav"),
        phone.get(f"/api/sessions/{sid}/audio/bot-000.wav"),
        phone.post(f"/api/sessions/{sid}/turns?source=none&reply_to=0"),
        phone.post(f"/api/sessions/{sid}/end"),
    ]
    for response in requests:
        assert response.status_code == 404, response.text
        assert set(response.json()["error"]) == ERROR_KEYS
        assert b"SECRET" not in response.content
    assert sorted(p.name for p in state.parent.iterdir()) == ["secret.wav", "state"]
    assert len(list((state / "sessions").iterdir())) == 1


@pytest.mark.parametrize(
    "name",
    [
        "session.json",
        "..%2fsession.json",
        "..%2f..%2f..%2fsecret.wav",
        "%2e%2e%2fcall.wav",
        "call.wav",
        "bot-000.wav%00",
        "bot-000.wav%2f..%2f..%2fsession.json",
        "customer-001.wav",  # well formed, but the log does not refer to it
        "bot-002.wav",
        "bot-0.wav",
    ],
)
def test_audio_is_served_only_by_a_name_the_log_refers_to(phone: TestClient, state: Path, name: str) -> None:
    sid = start(phone)["session_id"]
    assert phone.get(f"/api/sessions/{sid}/audio/bot-000.wav").status_code == 200
    state.parent.joinpath("secret.wav").write_bytes(b"SECRET")
    # A file planted in the session's audio directory is not served either.
    (state / "sessions" / sid / "audio" / "customer-001.wav").write_bytes(b"SECRET")
    response = phone.get(f"/api/sessions/{sid}/audio/{name}")
    assert response.status_code == 404, response.text
    assert set(response.json()["error"]) == ERROR_KEYS
    assert b"SECRET" not in response.content and b"session_id" not in response.content


def test_the_dialogue_state_is_never_served(fake: FakeSpeech, state: Path) -> None:
    class Secretive(StubDialogue):
        def start(self) -> Step:
            return Step(state="STATE-NOT-FOR-THE-PHONE", say=super().start().say)

        def step(self, state: str, heard: Heard) -> Step:
            return Step(state=state + "-2", say=StubDialogue().step('{"asked": 1}', heard).say)

    phone = app_on(fake, state, {"s": lambda params: Secretive()})
    created = phone.post("/api/sessions", json={"dialogue": "s"})
    sid = created.json()["session_id"]
    turn = post_turn(phone, sid, reply_to=0)
    served = [created, turn, phone.get(f"/api/sessions/{sid}"), phone.post(f"/api/sessions/{sid}/end")]
    assert all("STATE-NOT-FOR-THE-PHONE" not in r.text for r in served)
    stored = SessionStore(state / "sessions").load(sid)
    assert (stored.dialogue_state, stored.dialogue_undo) == (
        "STATE-NOT-FOR-THE-PHONE-2",
        "STATE-NOT-FOR-THE-PHONE",
    )


def test_clips_are_listed_and_served_by_listed_name_only(
    fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    clips = tmp_path / "clips"
    (clips / "sub").mkdir(parents=True)
    (clips / "hi-02.wav").write_bytes(make_wav(1.25))
    (clips / "hi-01.wav").write_bytes(make_wav(0.5, 16000))
    (clips / "notes.txt").write_text("x")
    (clips / "broken.wav").write_bytes(b"not a wav")
    (clips / ".hidden.wav").write_bytes(make_wav(0.5))
    (clips / "sub" / "deep.wav").write_bytes(make_wav(0.5))
    (tmp_path / "secret.wav").write_bytes(make_wav(0.3))
    os.symlink(tmp_path / "secret.wav", clips / "link.wav")
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=clips, dialogues=STUB))

    assert phone.get("/api/clips").json() == {
        "clips": [{"name": "hi-01.wav", "seconds": 0.5}, {"name": "hi-02.wav", "seconds": 1.25}]
    }
    served = phone.get("/api/clips/hi-02.wav")
    assert served.headers["content-type"] == "audio/wav" and served.content == make_wav(1.25)
    for name in ("link.wav", "..%2fsecret.wav", "sub%2fdeep.wav", "sub/deep.wav", ".hidden.wav",
                 "notes.txt", "%2e%2e%2fsecret.wav", "nope.wav", "hi-02.wav%00"):  # fmt: skip
        response = phone.get(f"/api/clips/{name}")
        assert response.status_code == 404, name
        assert set(response.json()["error"]) == ERROR_KEYS


def test_a_missing_clips_directory_is_an_empty_list(fake: FakeSpeech, state: Path, tmp_path: Path) -> None:
    phone = TestClient(
        create_app(gnani=fake, state=state, web_dir=None, clips_dir=tmp_path / "nope", dialogues=STUB)
    )
    assert phone.get("/api/clips").json() == {"clips": []}
    assert phone.get("/api/clips/a.wav").status_code == 404


def test_clips_directory_from_the_environment(
    fake: FakeSpeech, state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.wav").write_bytes(make_wav(0.2))
    monkeypatch.setenv("SAMAJH_CLIPS_DIR", str(tmp_path))
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, dialogues=STUB))
    assert phone.get("/api/clips").json() == {"clips": [{"name": "a.wav", "seconds": 0.2}]}


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({"host": "evil.example"}, "host_not_allowed"),
        ({"host": "127.0.0.1.evil.example:8085"}, "host_not_allowed"),
        ({"origin": "https://evil.example"}, "foreign_origin"),
        ({"origin": "http://testserver:9999"}, "foreign_origin"),
        ({"origin": "null"}, "foreign_origin"),
    ],
)
def test_a_request_for_another_host_or_from_another_site_is_refused(
    phone: TestClient, headers: dict[str, str], code: str
) -> None:
    error_of(phone.post("/api/sessions", content=b"{}", headers=headers), 403, code)
    error_of(phone.get("/api/health", headers=headers), 403, code)
    assert phone.post("/api/sessions", json={}, headers={"origin": "http://testserver"}).status_code == 201


LANGUAGES = [
    {"id": "hi", "label": "Hindi", "experimental": False},
    {"id": "hi-en", "label": "Hinglish", "experimental": False},
    {"id": "ta", "label": "Tamil", "experimental": True},
    {"id": "kn", "label": "Kannada", "experimental": True},
]


def test_health_without_a_key(state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set but empty: the client's .env loader leaves a variable that exists alone.
    monkeypatch.setenv("GNANI_API_KEY", "")
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    phone = TestClient(create_app(state=state, web_dir=None, clips_dir=None, dialogues=STUB))
    assert phone.get("/api/health").json() == {
        "status": "ok",
        "gnani_key_configured": False,
        "dialogues": ["stub"],
        "default_dialogue": "stub",
        "line_rates": [8000, 16000],
        "stt_models": ["prisma-v3.0", "prisma-v2.5"],
        "models": {
            "stt_primary": {"model": "prisma-v3.0", "format": "transcribe"},
            "stt_second": {"model": "prisma-v2.5", "format": "transcribe"},
            "tts": {"model": "timbre-v3.0"},
            "batch": {"model": "prisma-v3.0"},
        },
        "streaming": False,
        "languages": LANGUAGES,
        "turn_taking": {
            "yes_no": {"cut_ms": 700, "grace_ms": 1000},
            "short": {"cut_ms": 800, "grace_ms": 1200},
            "amount": {"cut_ms": 1000, "grace_ms": 1600},
            "open": {"cut_ms": 1100, "grace_ms": 1800},
        },
        "limits": {"max_turn_bytes": MAX_TURN_BYTES, "max_turn_seconds": 30, "max_turns": MAX_TURNS},
    }
    assert phone.get("/api/records").json() == {"records": [], "languages": LANGUAGES}
    # The call starts without a key; speaking the prompt is what needs one.
    created = start(phone)
    error = error_of(phone.get(created["bot"]["audio_url"]), 500, "server_misconfigured")
    assert error["stage"] == "tts" and ".env" not in error["message"]


def test_health_names_the_models_of_the_settings_it_runs_with(fake: FakeSpeech, state: Path) -> None:
    """The phone's model strip reads these; they follow the settings, not a fixed text."""
    settings = load_settings()
    other = settings.model_copy(
        update={
            "stt": settings.stt.model_copy(update={"model": "prisma-v2.5", "second_model": "prisma-v3.0"}),
            "tts": settings.tts.model_copy(update={"model": "timbre-v2.5"}),
            "batch": settings.batch.model_copy(update={"model": "prisma-v2.5"}),
        }
    )
    phone = TestClient(
        create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, settings=other, dialogues=STUB)
    )
    assert phone.get("/api/health").json()["models"] == {
        "stt_primary": {"model": "prisma-v2.5", "format": "transcribe"},
        "stt_second": {"model": "prisma-v3.0", "format": "transcribe"},
        "tts": {"model": "timbre-v2.5"},
        "batch": {"model": "prisma-v2.5"},
    }


def test_health_reports_a_key_as_a_bool_and_nothing_else(
    state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GNANI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    phone = TestClient(create_app(state=state, web_dir=None, clips_dir=None, dialogues=STUB))
    response = phone.get("/api/health")
    assert response.json()["gnani_key_configured"] is True
    assert "test-key-not-real" not in response.text + str(response.headers)


def test_the_default_app_runs_the_samajh_dialogue_on_a_listed_record(fake: FakeSpeech, state: Path) -> None:
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None))
    health = phone.get("/api/health").json()
    assert (health["dialogues"], health["default_dialogue"]) == (["samajh"], "samajh")
    listed = phone.get("/api/records").json()
    assert listed["languages"] == LANGUAGES
    shown = {"id", "label", "description", "first_name", "language"}
    assert all(shown <= set(r) <= shown | {"readings_note"} for r in listed["records"])
    created = start(phone, params={"record": listed["records"][0]["id"], "language": "hi"})
    assert created["dialogue"] == "samajh"
    bot = created["bot"]
    assert bot["lines"] and bot["language"] == "hi-IN" and not bot["end_call"]
    error_of(
        phone.post("/api/sessions", json={"params": {"record": "no-such-record"}}), 422, "invalid_params"
    )


@pytest.mark.parametrize("name", ["stub", "scripted", "SAMAJH"])
def test_the_default_app_refuses_a_session_naming_any_other_dialogue(
    fake: FakeSpeech, state: Path, name: str
) -> None:
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None))
    error_of(phone.post("/api/sessions", json={"dialogue": name}), 422, "unknown_dialogue")
    error_of(phone.post("/api/sessions", json={"dialogue": name, "params": {"record": "hero", "language": "hi"}}),
             422, "unknown_dialogue")  # fmt: skip
    assert not (state / "sessions").exists() and not fake.tts_calls and not fake.stt_calls


def test_errors_have_one_shape_on_every_route(phone: TestClient) -> None:
    error = error_of(phone.get("/api/nope"), 404, "not_found")
    assert error["stage"] == "request"
    error_of(phone.delete("/api/health"), 405, "method_not_allowed")
    error_of(phone.get("/"), 404, "not_found")


def test_no_cors_headers(phone: TestClient) -> None:
    response = phone.get("/api/health", headers={"Origin": "http://evil.example"})
    assert not [h for h in response.headers if h.lower().startswith("access-control")]


def test_the_phone_page_is_served_after_the_api(fake: FakeSpeech, state: Path, tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>phone</h1>")
    (web / "app.js").write_text("// js")
    (tmp_path / "secret.txt").write_text("SECRET")
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=web, clips_dir=None, dialogues=STUB))
    assert phone.get("/").text == "<h1>phone</h1>"
    assert phone.get("/app.js").status_code == 200
    assert phone.get("/api/health").json()["status"] == "ok"
    for path in ("/..%2fsecret.txt", "/%2e%2e/secret.txt", "/../secret.txt", "/api/..%2f..%2fsecret.txt"):
        response = phone.get(path)
        assert response.status_code == 404 and "SECRET" not in response.text
    missing = TestClient(
        create_app(gnani=fake, state=state, web_dir=tmp_path / "nope", clips_dir=None, dialogues=STUB)
    )
    assert missing.get("/").status_code == 404 and missing.get("/api/health").status_code == 200
