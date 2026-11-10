"""The HTTP API through TestClient, with a fake Gnani client."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav, wav_shape
from starlette.testclient import TestClient

from samajh.clients.errors import ServerError, TransportError
from samajh.clients.gnani import PrismaV25, PrismaV30, wav_seconds
from samajh.server import create_app
from samajh.server.app import MAX_JSON_BYTES, MAX_TURN_BYTES, MAX_TURNS
from samajh.server.dialogue import BotUtterance, CallView, Heard, StubDialogue

ERROR_KEYS = {"stage", "code", "message", "retryable", "upstream_status"}
ANSWER = make_wav(0.5)


@pytest.fixture
def phone(fake: FakeSpeech, state: Path) -> TestClient:
    return TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None))


def start(phone: TestClient, **body: object) -> dict:
    response = phone.post("/api/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def say(phone: TestClient, sid: str, audio: bytes = ANSWER, source: str = "file") -> dict:
    response = phone.post(f"/api/sessions/{sid}/turns?source={source}", content=audio)
    assert response.status_code == 200, response.text
    return response.json()


def error_of(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert set(error) == ERROR_KEYS
    assert error["code"] == code
    return error


def events(phone: TestClient, sid: str, kind: str | None = None) -> list[dict]:
    log = phone.get(f"/api/sessions/{sid}").json()
    return [e for e in log["events"] if kind in (None, e["type"])]


def test_a_full_stub_call(phone: TestClient, fake: FakeSpeech) -> None:
    created = start(phone)
    sid = created["session_id"]
    assert (created["line_rate"], created["stt_model"]) == (8000, "prisma-v3.0")
    assert created["bot"] == {
        "seq": 0,
        "text": StubDialogue.QUESTIONS[0],
        "language": "hi-IN",
        "end_call": False,
        "audio_url": f"/api/sessions/{sid}/audio/bot-000.wav",
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
    assert [b["seq"] for b in bots] == [0, 2, 4, 6]
    assert phone.get(bots[-1]["audio_url"]).status_code == 200

    log = phone.get(f"/api/sessions/{sid}").json()
    assert (log["status"], log["ended_reason"]) == ("ended", "dialogue")
    assert [e["type"] for e in log["events"]] == ["bot", "customer"] * 3 + ["bot"]
    assert [e["seq"] for e in log["events"]] == list(range(7))
    assert all(e["audio"] and e["rec_end"] > e["rec_start"] for e in log["events"])
    assert all(e["tts"]["voice"] == "Shivani" for e in log["events"] if e["type"] == "bot")
    first = log["events"][1]
    assert first["stt"]["params"] == {"language_code": "hi-IN", "format": "transcribe"}
    assert first["stt"]["mode"] == "rest" and first["source"] == "file"
    assert set(first["latency"]) == {"normalise_ms", "stt_ms", "dialogue_ms", "server_ms", "eos_wait_ms"}
    assert fake.stt_calls[0][1] == PrismaV30(language="hi-IN", format="transcribe")

    recording = phone.get(f"/api/sessions/{sid}/recording.wav")
    assert recording.headers["content-type"] == "audio/wav"
    total = log["events"][-1]["rec_end"]
    assert wav_seconds(recording.content) == pytest.approx(total, abs=1e-6)
    assert log["recording"]["seconds"] == pytest.approx(total, abs=1e-6)
    assert total == pytest.approx(4 * 0.4 + 0.5 + 0.6 + 0.7 + 6 * 0.5)

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
    response = phone.post(f"/api/sessions/{sid}/turns?source=mic&eos_wait_ms=412.5", content=ANSWER)
    turn = response.json()
    assert set(turn) == {"customer", "bot", "ended"}
    customer = turn["customer"]
    assert set(customer) == {
        "seq", "transcript", "literal", "detected_language", "audio_url", "audio_seconds", "stt", "latency",
    }  # fmt: skip
    assert (customer["seq"], customer["detected_language"], customer["literal"]) == (1, "hi-IN", None)
    assert customer["audio_url"] == f"/api/sessions/{sid}/audio/customer-001.wav"
    assert customer["audio_seconds"] == 0.5
    assert customer["stt"] == {"model": "prisma-v3.0", "cache_hit": False, "attempts": 1}
    assert customer["latency"]["eos_wait_ms"] == 412.5
    assert all(customer["latency"][k] >= 0 for k in ("normalise_ms", "stt_ms", "dialogue_ms", "server_ms"))
    assert phone.get(customer["audio_url"]).content == ANSWER  # a canonical upload keeps its bytes
    assert events(phone, sid, "customer")[0]["source"] == "mic"


def test_a_browser_recording_is_stored_at_the_line_rate(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone, line_rate=16000)["session_id"]
    turn = say(phone, sid, make_wav(1.0, 48000, channels=2), source="mic")
    stored = phone.get(turn["customer"]["audio_url"]).content
    assert wav_shape(stored)[:3] == (1, 2, 16000)
    assert fake.stt_calls[0][0] == stored
    assert wav_shape(phone.get(turn["bot"]["audio_url"]).content)[2] == 16000


def test_v25_is_selected_per_session_and_returns_the_literal(phone: TestClient, fake: FakeSpeech) -> None:
    created = start(phone, stt_model="prisma-v2.5")
    turn = say(phone, created["session_id"])
    assert created["stt_model"] == "prisma-v2.5"
    assert fake.stt_calls[0][1] == PrismaV25(language="hi-IN", format="transcribe")
    assert turn["customer"]["literal"] == "शब्दों में"
    assert turn["customer"]["detected_language"] is None


def test_bot_audio_is_synthesised_on_first_fetch_and_then_served_from_the_session(
    phone: TestClient, fake: FakeSpeech
) -> None:
    created = start(phone)
    sid, url = created["session_id"], created["bot"]["audio_url"]
    assert fake.tts_calls == []
    assert events(phone, sid)[0]["audio"] is None and events(phone, sid)[0]["tts"] is None

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
    assert event["tts"]["cache_hit"] is False and event["tts"]["est_credits"] > 0


def test_timbre_audio_with_a_streaming_header_is_stored_repaired(phone: TestClient, fake: FakeSpeech) -> None:
    def streaming(options) -> bytes:
        wav = bytearray(make_wav(0.4, options.sample_rate))
        wav[4:8] = wav[40:44] = b"\xff\xff\xff\xff"
        return bytes(wav)

    fake.tts_audio = streaming
    stored = phone.get(start(phone)["bot"]["audio_url"]).content
    assert wav_shape(stored) == (1, 2, 8000, 3200)


def test_nothing_said(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    turn = phone.post(f"/api/sessions/{sid}/turns?source=none").json()
    customer = turn["customer"]
    assert (customer["transcript"], customer["audio_url"], customer["audio_seconds"]) == ("", None, None)
    assert customer["stt"] is None
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
    response = phone.post(f"/api/sessions/{sid}/turns?source=mic", content=b"\0" * (MAX_TURN_BYTES + 1))
    error = error_of(response, 413, "audio_too_large")
    assert (error["stage"], error["retryable"]) == ("audio", False)
    assert fake.stt_calls == []
    assert [e["code"] for e in events(phone, sid, "error")] == ["audio_too_large"]


def test_a_body_over_the_limit_is_refused_without_content_length(phone: TestClient) -> None:
    sid = start(phone)["session_id"]

    def chunks() -> Iterator[bytes]:
        for _ in range(MAX_TURN_BYTES // 65536 + 1):
            yield b"\0" * 65536

    response = phone.post(f"/api/sessions/{sid}/turns?source=mic", content=chunks())
    assert "content-length" not in response.request.headers
    error_of(response, 413, "audio_too_large")
    assert events(phone, sid, "customer") == []


def test_a_body_at_the_limit_is_read(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    response = phone.post(f"/api/sessions/{sid}/turns?source=mic", content=b"\0" * MAX_TURN_BYTES)
    error_of(response, 422, "audio_unreadable")


def test_a_json_body_over_its_limit_is_refused(phone: TestClient) -> None:
    big = {"params": {"k": "x" * MAX_JSON_BYTES}}
    error_of(phone.post("/api/sessions", json=big), 413, "body_too_large")
    chunked = phone.post("/api/sessions", content=iter([b" " * 4096] * 8))
    error_of(chunked, 413, "body_too_large")


@pytest.mark.parametrize(
    "body",
    [
        b"[",
        b"[]",
        b'{"line_rate": 44100}',
        b'{"stt_model": "whisper"}',
        b'{"nope": 1}',
        b'{"params": {"a": 1}}',
    ],
)
def test_a_bad_create_body_is_a_request_error(phone: TestClient, body: bytes) -> None:
    error = error_of(phone.post("/api/sessions", content=body), 422, "invalid_request")
    assert error["stage"] == "request"


def test_create_takes_an_empty_body_and_refuses_an_unknown_dialogue(phone: TestClient) -> None:
    assert phone.post("/api/sessions").status_code == 201
    error_of(phone.post("/api/sessions", json={"dialogue": "nope"}), 422, "unknown_dialogue")


def test_a_turn_needs_a_valid_source_and_wait(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    for query in ("", "?source=", "?source=tape", "?source=MIC"):
        error_of(phone.post(f"/api/sessions/{sid}/turns{query}", content=ANSWER), 422, "invalid_source")
    for wait in ("abc", "nan", "-1", "inf"):
        response = phone.post(f"/api/sessions/{sid}/turns?source=mic&eos_wait_ms={wait}", content=ANSWER)
        error_of(response, 422, "invalid_eos_wait_ms")
    assert len(events(phone, sid)) == 1


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
        phone.post(f"/api/sessions/{sid}/turns?source=none"),
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
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=clips))

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
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=tmp_path / "nope"))
    assert phone.get("/api/clips").json() == {"clips": []}
    assert phone.get("/api/clips/a.wav").status_code == 404


def test_clips_directory_from_the_environment(
    fake: FakeSpeech, state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.wav").write_bytes(make_wav(0.2))
    monkeypatch.setenv("SAMAJH_CLIPS_DIR", str(tmp_path))
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None))
    assert phone.get("/api/clips").json() == {"clips": [{"name": "a.wav", "seconds": 0.2}]}


def test_no_turn_after_the_end(phone: TestClient) -> None:
    sid = start(phone)["session_id"]
    for _ in range(3):
        say(phone, sid)
    error = error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=file", content=ANSWER), 409, "session_not_active"
    )
    assert error["stage"] == "session"
    assert len(events(phone, sid)) == 7


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
    error_of(phone.post(f"/api/sessions/{sid}/turns?source=none"), 409, "session_not_active")
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
    assert log["recording"]["seconds"] == pytest.approx(before + 0.5 + 0.4)
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == log["recording"]["seconds"]


def test_nothing_is_spoken_after_a_hang_up(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    turn = say(phone, sid)
    assert phone.post(f"/api/sessions/{sid}/end").json()["recording_seconds"] == 0.5
    error_of(phone.get(turn["bot"]["audio_url"]), 409, "session_not_active")
    assert fake.tts_calls == []
    assert phone.get(f"/api/sessions/{sid}").json()["recording"]["seconds"] == 0.5


def test_a_turn_sent_again_gets_the_stored_reply_and_does_not_advance(
    phone: TestClient, fake: FakeSpeech
) -> None:
    sid = start(phone)["session_id"]
    first = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0", content=ANSWER).json()
    again = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0", content=ANSWER)
    assert again.status_code == 200 and again.json() == first
    assert len(fake.stt_calls) == 1 and len(events(phone, sid)) == 3
    # The closing turn can be sent again too, although the call has ended by then.
    for prompt in (first["bot"]["seq"], first["bot"]["seq"] + 2):
        last = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={prompt}", content=ANSWER).json()
    assert last["ended"]
    again = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={prompt}", content=ANSWER)
    assert again.status_code == 200 and again.json() == last
    error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=1", content=ANSWER),
        409,
        "turn_out_of_order",
    )
    error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=x", content=ANSWER),
        422,
        "invalid_reply_to",
    )


def test_a_failed_prompt_fetched_many_times_is_logged_once(phone: TestClient, fake: FakeSpeech) -> None:
    created = start(phone)
    fake.tts_error = ServerError(status=503, code="DOWN", message="timbre is down", attempts=2)
    for _ in range(5):
        error_of(phone.get(created["bot"]["audio_url"]), 502, "gnani_server_error")
    assert len(events(phone, created["session_id"], "error")) == 1


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


def test_a_finished_call_is_dropped_before_one_in_progress(
    phone: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("samajh.server.app.MAX_LIVE_SESSIONS", 2)
    in_progress = start(phone)["session_id"]
    finished = start(phone)["session_id"]
    phone.post(f"/api/sessions/{finished}/end")
    start(phone)
    assert phone.post(f"/api/sessions/{in_progress}/turns?source=none").status_code == 200


def test_a_recording_of_a_call_in_progress_is_assembled_on_demand(phone: TestClient) -> None:
    created = start(phone)
    sid = created["session_id"]
    phone.get(created["bot"]["audio_url"])
    say(phone, sid)
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == pytest.approx(1.4)
    log = phone.get(f"/api/sessions/{sid}").json()
    assert log["status"] == "active" and log["recording"] is None


def test_a_session_of_an_earlier_server_run_can_be_read_but_not_continued(
    phone: TestClient, fake: FakeSpeech, state: Path
) -> None:
    created = start(phone)
    sid = created["session_id"]
    spoken = phone.get(created["bot"]["audio_url"]).content
    turn = say(phone, sid)
    log = phone.get(f"/api/sessions/{sid}").json()

    later = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None))
    assert later.get(f"/api/sessions/{sid}").json() == log
    assert later.get(created["bot"]["audio_url"]).content == spoken
    assert later.get(f"/api/sessions/{sid}/recording.wav").status_code == 200
    error_of(later.post(f"/api/sessions/{sid}/turns?source=none"), 409, "session_not_active")
    error_of(later.post(f"/api/sessions/{sid}/end"), 409, "session_not_active")
    # Its second prompt was never spoken, and only the run that owns the call may synthesise it.
    error_of(later.get(turn["bot"]["audio_url"]), 409, "session_not_active")
    assert len(fake.tts_calls) == 1

    phone.post(f"/api/sessions/{sid}/end")
    assert later.post(f"/api/sessions/{sid}/end").json()["ended_reason"] == "hangup"


def test_an_stt_failure_leaves_the_dialogue_where_it_was(phone: TestClient, fake: FakeSpeech) -> None:
    sid = start(phone)["session_id"]
    fake.stt_error = ServerError(status=503, code="UPSTREAM", message="down", attempts=2)
    response = phone.post(f"/api/sessions/{sid}/turns?source=mic", content=ANSWER)
    error = error_of(response, 502, "gnani_server_error")
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
    again = say(phone, sid)
    assert again["customer"]["seq"] == 2
    assert again["bot"]["text"] == "मैंने सुना: पचास हज़ार " + StubDialogue.QUESTIONS[1]
    assert [e["type"] for e in events(phone, sid)] == ["bot", "error", "customer", "bot"]
    # The failed attempt's audio stays out of the recording.
    assert wav_seconds(phone.get(f"/api/sessions/{sid}/recording.wav").content) == 0.5


def test_an_unreadable_upload_is_logged_and_the_turn_can_be_sent_again(
    phone: TestClient, fake: FakeSpeech
) -> None:
    sid = start(phone)["session_id"]
    error = error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=mic", content=b"junk"), 422, "audio_unreadable"
    )
    assert error["stage"] == "audio"
    error_of(phone.post(f"/api/sessions/{sid}/turns?source=mic"), 422, "audio_unreadable")
    error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=mic", content=make_wav(0.05)), 422, "audio_too_short"
    )
    error_of(
        phone.post(f"/api/sessions/{sid}/turns?source=mic", content=make_wav(30.5)), 422, "audio_too_long"
    )
    assert fake.stt_calls == []
    logged = events(phone, sid, "error")
    assert [e["stage"] for e in logged] == ["audio"] * 4 and all(e["audio"] is None for e in logged)
    assert say(phone, sid)["bot"]["text"].endswith(StubDialogue.QUESTIONS[1])


def test_a_tts_failure_is_logged_and_the_fetch_can_be_repeated(phone: TestClient, fake: FakeSpeech) -> None:
    created = start(phone)
    sid, url = created["session_id"], created["bot"]["audio_url"]
    fake.tts_error = TransportError("ConnectTimeout on all 2 attempts")
    error = error_of(phone.get(url), 504, "gnani_unreachable")
    assert (error["stage"], error["retryable"]) == ("tts", True)
    assert [(e["stage"], e["audio"]) for e in events(phone, sid, "error")] == [("tts", None)]
    fake.tts_error = None
    assert phone.get(url).status_code == 200
    assert say(phone, sid)["customer"]["seq"] == 2


def test_timbre_audio_that_is_not_a_wav_is_a_bad_response(phone: TestClient, fake: FakeSpeech) -> None:
    fake.tts_audio = lambda options: b"ID3 not a wav"
    error_of(phone.get(start(phone)["bot"]["audio_url"]), 502, "gnani_bad_response")


class Scripted:
    """Says whatever `script` returns for the number of exchanges so far."""

    def __init__(self, script) -> None:
        self.script = script

    def next(self, call: CallView, heard: Heard | None) -> object:
        return self.script(len(call.exchanges), heard)


def phone_with(script, fake: FakeSpeech, state: Path) -> TestClient:
    def factory(params: Mapping[str, str]) -> Scripted:
        if "bad" in params:
            raise ValueError("secret detail")
        return Scripted(script)

    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues={"scripted": factory})
    return TestClient(app)


def test_a_dialogue_exception_is_logged_by_class_name_and_does_not_advance(
    fake: FakeSpeech, state: Path
) -> None:
    broken = True

    def script(asked: int, heard: Heard | None) -> BotUtterance:
        if asked and broken:
            raise RuntimeError("secret /path/to/thing")
        return BotUtterance(text=f"question {asked}", language="en-IN")

    phone = phone_with(script, fake, state)
    sid = start(phone, dialogue="scripted")["session_id"]
    response = phone.post(f"/api/sessions/{sid}/turns?source=mic", content=ANSWER)
    error = error_of(response, 500, "dialogue_failed")
    assert (error["stage"], error["message"], error["retryable"]) == ("dialogue", "RuntimeError", False)
    failed = events(phone, sid)[-1]
    assert (failed["type"], failed["stage"], failed["audio"]) == (
        "error",
        "dialogue",
        "audio/customer-001.wav",
    )
    assert "secret" not in phone.get(f"/api/sessions/{sid}").text

    broken = False
    assert say(phone, sid)["bot"]["text"] == "question 1"
    assert len(fake.stt_calls) == 2 and fake.stt_calls[0][1].language == "en-IN"


def test_a_dialogue_that_fails_at_the_start_creates_no_session(fake: FakeSpeech, state: Path) -> None:
    def script(asked: int, heard: Heard | None) -> BotUtterance:
        raise RuntimeError("boom")

    phone = phone_with(script, fake, state)
    error = error_of(phone.post("/api/sessions", json={"dialogue": "scripted"}), 500, "dialogue_failed")
    assert error["message"] == "RuntimeError"
    assert not (state / "sessions").exists()
    bad = phone.post("/api/sessions", json={"dialogue": "scripted", "params": {"bad": "1"}})
    assert "secret" not in error_of(bad, 422, "invalid_params")["message"]
    assert phone.get("/api/health").json()["dialogues"] == ["scripted"]


@pytest.mark.parametrize("said", ["not an utterance", BotUtterance(text="any language", language="auto")])
def test_an_utterance_the_session_cannot_handle_is_a_dialogue_error(
    fake: FakeSpeech, state: Path, said
) -> None:
    phone = phone_with(lambda asked, heard: said, fake, state)
    response = phone.post("/api/sessions", json={"dialogue": "scripted", "stt_model": "prisma-v2.5"})
    error_of(response, 500, "dialogue_failed")


def test_the_dialogue_sees_the_call_so_far(fake: FakeSpeech, state: Path) -> None:
    views: list[CallView] = []

    class Watching:
        def next(self, call: CallView, heard: Heard | None) -> BotUtterance:
            views.append(call)
            return BotUtterance(text=f"q{len(call.exchanges)}", language="hi-IN", tags={"step": "s"})

    app = create_app(
        gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues={"w": lambda p: Watching()}
    )
    phone = TestClient(app)
    sid = start(phone, dialogue="w", params={"scenario": "A1"})["session_id"]
    say(phone, sid)
    phone.post(f"/api/sessions/{sid}/turns?source=none")
    last = views[-1]
    assert (last.session_id, dict(last.params)) == (sid, {"scenario": "A1"})
    assert [(x.bot.text, x.heard.text) for x in last.exchanges] == [("q0", "पचास हज़ार"), ("q1", "")]
    assert views[0].exchanges == ()
    assert events(phone, sid, "bot")[0]["tags"] == {"step": "s"}


def test_the_turn_limit(fake: FakeSpeech, state: Path) -> None:
    phone = phone_with(lambda asked, heard: BotUtterance(text="again", language="hi-IN"), fake, state)
    sid = start(phone, dialogue="scripted")["session_id"]
    for _ in range(MAX_TURNS):
        assert phone.post(f"/api/sessions/{sid}/turns?source=none").status_code == 200
    error = error_of(phone.post(f"/api/sessions/{sid}/turns?source=none"), 409, "turn_limit")
    assert error["stage"] == "session"
    assert phone.get("/api/health").json()["limits"]["max_turns"] == MAX_TURNS


def test_the_oldest_live_call_is_dropped_past_the_cap(
    phone: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("samajh.server.app.MAX_LIVE_SESSIONS", 2)
    first, second, third = (start(phone)["session_id"] for _ in range(3))
    error_of(phone.post(f"/api/sessions/{first}/turns?source=none"), 409, "session_not_active")
    assert phone.get(f"/api/sessions/{first}").json()["status"] == "active"  # still readable
    for sid in (second, third):
        assert phone.post(f"/api/sessions/{sid}/turns?source=none").status_code == 200


def test_health_without_a_key(state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set but empty: the client's .env loader leaves a variable that exists alone.
    monkeypatch.setenv("GNANI_API_KEY", "")
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    phone = TestClient(create_app(state=state, web_dir=None, clips_dir=None))
    assert phone.get("/api/health").json() == {
        "status": "ok",
        "gnani_key_configured": False,
        "dialogues": ["stub"],
        "line_rates": [8000, 16000],
        "stt_models": ["prisma-v3.0", "prisma-v2.5"],
        "streaming": False,
        "limits": {"max_turn_bytes": MAX_TURN_BYTES, "max_turn_seconds": 30, "max_turns": MAX_TURNS},
    }
    # The call starts without a key; speaking the prompt is what needs one.
    created = start(phone)
    error = error_of(phone.get(created["bot"]["audio_url"]), 500, "server_misconfigured")
    assert error["stage"] == "tts" and ".env" not in error["message"]


def test_health_reports_a_key_as_a_bool_and_nothing_else(
    state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GNANI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    response = TestClient(create_app(state=state, web_dir=None, clips_dir=None)).get("/api/health")
    assert response.json()["gnani_key_configured"] is True
    assert "test-key-not-real" not in response.text + str(response.headers)


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
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=web, clips_dir=None))
    assert phone.get("/").text == "<h1>phone</h1>"
    assert phone.get("/app.js").status_code == 200
    assert phone.get("/api/health").json()["status"] == "ok"
    for path in ("/..%2fsecret.txt", "/%2e%2e/secret.txt", "/../secret.txt", "/api/..%2f..%2fsecret.txt"):
        response = phone.get(path)
        assert response.status_code == 404 and "SECRET" not in response.text
    missing = TestClient(create_app(gnani=fake, state=state, web_dir=tmp_path / "nope", clips_dir=None))
    assert missing.get("/").status_code == 404 and missing.get("/api/health").status_code == 200
