"""Measurement fields of the session log and the phone's browser reports (additive, W2 schema)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from serverkit import FakeSpeech
from starlette.testclient import TestClient
from test_app import app_on, say, start
from test_casefile import wait_case
from test_two_readings import Call, phone_for

from samajh.clients.errors import ServerError
from samajh.server.app import position_of
from samajh.server.sessionlog import BotEvent, CustomerEvent, SessionLog, SessionStore

V25 = "prisma-v2.5"
LISTEN = {
    "mode": "vad",
    "cut_ms": 1100,
    "grace_ms": 1800,
    "marks": [
        {"type": "speech_start", "at_ms": 400},
        {"type": "pause", "at_ms": 900, "ms": 210},
        {"type": "cut", "at_ms": 2600, "ms": 1100},
        {"type": "send", "at_ms": 2610},
    ],
    "takes": 1,
    "grace_used": False,
    "eos_wait_ms": 1150,
    "post_ms": 820,
    "echo_cancellation": True,
}
PLAYBACK = {
    "bot_start_ms": 1900,
    "output_latency_ms": 12.5,
    "played_ms": 3000,
    "completed": True,
    "talk_over": [{"start_ms": 500, "ms": 240}],
}


def load(state: Path, sid: str) -> SessionLog:
    log = SessionStore(state / "sessions").load(sid)
    assert log is not None
    return log


def report(phone: TestClient, sid: str, seq: int, body: object):
    return phone.post(f"/api/sessions/{sid}/events/{seq}/browser", json=body)


def test_a_samajh_call_logs_cache_keys_status_positions_and_line_timing(
    fake: FakeSpeech, state: Path
) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.say("हाँ")
    call.say("हाँ")
    customers = [e for e in call.log().events if isinstance(e, CustomerEvent)]
    assert len(customers) == 2
    for c in customers:
        assert c.readings and all(r.cache_key for r in c.readings)
        assert all(r.http_status == 200 for r in c.readings)
        assert isinstance(c.state_before, dict) and "at" in c.state_before
        assert isinstance(c.state_after, dict) and "at" in c.state_after
        assert all(
            not isinstance(v, dict | list) for v in [*c.state_before.values(), *c.state_after.values()]
        )
    assert customers[1].state_before == customers[0].state_after
    phone = call.phone
    assert phone.get(f"/api/sessions/{call.sid}/audio/bot-000.wav").status_code == 200
    first = call.log().events[0]
    assert isinstance(first, BotEvent)
    assert all(line.tts and line.tts.synth_ms is not None and line.tts.synth_ms >= 0 for line in first.lines)


def test_a_cache_hit_has_no_http_status(fake: FakeSpeech, state: Path) -> None:
    phone = app_on(fake, state)
    sid = start(phone)["session_id"]
    say(phone, sid)
    say(phone, sid)  # the same clip again: the fake's cache answers
    readings = [e.readings[0] for e in load(state, sid).events if isinstance(e, CustomerEvent)]
    assert [r.http_status for r in readings] == [200, None]
    assert readings[1].cache_hit and readings[1].cache_key == readings[0].cache_key


def test_a_second_reading_that_answers_504_logs_its_status(fake: FakeSpeech, state: Path) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()
    fake.model_errors[V25] = ServerError(status=504, code="TIMEOUT", message="v2.5 answered 504", attempts=1)
    call.say("पचास हज़ार")
    last = [e for e in call.log().events if isinstance(e, CustomerEvent)][-1]
    second = last.readings[1]
    assert (second.role, second.ok, second.http_status) == ("second", False, 504)


@pytest.fixture
def called(fake: FakeSpeech, state: Path) -> tuple[TestClient, str, int, int]:
    phone = app_on(fake, state)
    sid = start(phone)["session_id"]
    turn = say(phone, sid)
    return phone, sid, turn["customer"]["seq"], turn["bot"]["seq"]


def test_reports_are_stored_on_their_events_and_never_in_turn_json(called, state: Path) -> None:
    phone, sid, customer, bot = called
    before = load(state, sid)
    assert report(phone, sid, customer, LISTEN).json() == {"ok": True}
    assert report(phone, sid, bot, PLAYBACK).json() == {"ok": True}
    assert report(phone, sid, 0, {**PLAYBACK, "bot_start_ms": None}).status_code == 200
    log = load(state, sid)
    c, b = log.events[customer], log.events[bot]
    assert isinstance(c, CustomerEvent) and c.browser is not None
    assert c.browser.model_dump(mode="json", exclude_none=True) == {
        **LISTEN,
        "marks": [{k: v for k, v in m.items()} for m in LISTEN["marks"]],
    }
    assert isinstance(b, BotEvent) and b.browser is not None and b.browser.talk_over[0].ms == 240
    assert log.dialogue_state == before.dialogue_state and log.status == before.status
    # The stored reply to a repeated turn never carries the report.
    again = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={customer - 1}&part=1", content=b"")
    assert "browser" not in json.dumps(again.json())


@pytest.mark.parametrize(
    ("which", "body"),
    [
        ("customer", PLAYBACK),  # a playback report on a customer turn
        ("bot", LISTEN),
        ("customer", {**LISTEN, "post_ms": float("nan")}),
        ("customer", {**LISTEN, "post_ms": 700000}),
        ("customer", {**LISTEN, "extra": 1}),
        ("customer", {**LISTEN, "marks": [{"type": "speech_start", "at_ms": -1}]}),
        ("bot", {**PLAYBACK, "talk_over": [{"start_ms": 1, "ms": 1}] * 201}),
    ],
)
def test_bad_reports_are_422(called, which: str, body: dict) -> None:
    phone, sid, customer, bot = called
    seq = customer if which == "customer" else bot
    raw = json.dumps(body, allow_nan=True)
    response = phone.post(
        f"/api/sessions/{sid}/events/{seq}/browser", content=raw, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422, response.text


def test_an_oversize_report_or_unknown_event_is_refused(called) -> None:
    phone, sid, customer, _ = called
    big = json.dumps({**LISTEN, "mode": "vad" + " " * 17000})
    assert phone.post(f"/api/sessions/{sid}/events/{customer}/browser", content=big).status_code == 413
    response = report(phone, sid, 99, LISTEN)
    assert response.status_code == 404 and response.json()["error"]["code"] == "event_not_found"


def test_an_error_event_takes_no_report(fake: FakeSpeech, state: Path) -> None:
    phone = app_on(fake, state)
    sid = start(phone)["session_id"]
    fake.stt_error = ServerError(status=503, code=None, message="down", attempts=1)
    assert (
        phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0", content=b"x" * 2000).status_code
        >= 400
    )
    errors = [e for e in load(state, sid).events if e.type == "error"]
    assert errors
    response = report(phone, sid, errors[0].seq, LISTEN)
    assert response.status_code == 422 and response.json()["error"]["code"] == "wrong_event"


def test_an_old_log_without_the_new_fields_still_loads(called, state: Path) -> None:
    _, sid, customer, _ = called
    raw = json.loads((state / "sessions" / sid / "session.json").read_text())
    for event in raw["events"]:
        for key in ("browser", "classifier", "state_before", "state_after"):
            event.pop(key, None)
        for reading in event.get("readings", []):
            reading.pop("cache_key", None)
            reading.pop("http_status", None)
        for line in event.get("lines", []):
            if line.get("tts"):
                line["tts"].pop("synth_ms", None)
    log = SessionLog.model_validate_json(json.dumps(raw))
    assert log.events[customer].browser is None  # type: ignore[union-attr]


def test_reports_after_the_end_and_after_the_case_started_change_no_recording(
    fake: FakeSpeech, state: Path
) -> None:
    call = Call(phone_for(fake, state), fake, state)
    phone, sid = call.phone, call.sid
    call.say("हाँ")
    customer = next(e.seq for e in call.log().events if isinstance(e, CustomerEvent))
    assert report(phone, sid, customer, LISTEN).status_code == 200  # active
    assert phone.post(f"/api/sessions/{sid}/end", json={}).status_code == 200
    wav = (state / "sessions" / sid / "call.wav").read_bytes()
    ended = call.log()
    assert report(phone, sid, customer + 1, PLAYBACK).status_code == 200  # ended
    assert phone.post(f"/api/sessions/{sid}/case").status_code == 200
    case = wait_case(phone, sid)  # the case file builds from a log holding reports
    assert case["status"] != "failed"
    assert report(phone, sid, customer, {**LISTEN, "takes": 2}).status_code == 200  # closed
    log = call.log()
    assert log.closed and log.events[customer].browser.takes == 2  # type: ignore[union-attr]
    assert log.events[customer + 1].browser is not None  # type: ignore[union-attr]
    assert (log.dialogue_state, log.status) == (ended.dialogue_state, ended.status)
    assert (state / "sessions" / sid / "call.wav").read_bytes() == wav


@pytest.mark.parametrize(
    "state_text",
    [None, "", "not json", "[1, 2]", '{"position": "at"}', '{"turns": ["मेरा जन्म 1990"]}', '"x"'],
)
def test_position_of_bad_input_is_none(state_text: str | None) -> None:
    assert position_of(state_text) is None


def test_position_of_keeps_only_scalars() -> None:
    text = json.dumps(
        {
            "turns": [{"text": "मेरा जन्म 1990"}],
            "position": {
                "at": "read_back",
                "amount_inr": 5,
                "low": None,
                "nested": {"text": "secret"},
                "list": ["secret"],
            },
        }
    )
    assert position_of(text) == {"at": "read_back", "amount_inr": 5, "low": None}


def test_a_second_reading_that_failed_after_two_attempts_logs_them(fake: FakeSpeech, state: Path) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()
    fake.model_errors[V25] = ServerError(status=504, code="TIMEOUT", message="v2.5 answered 504", attempts=2)
    call.say("पचास हज़ार")
    second = [e for e in call.log().events if isinstance(e, CustomerEvent)][-1].readings[1]
    assert (second.ok, second.http_status, second.attempts, second.cache_key) == (False, 504, 2, None)


@pytest.mark.parametrize("body", [{"completed": "yes"}, {"bot_start_ms": True}, {"bot_start_ms": "12"}])
def test_lax_playback_values_are_422(called, body: dict) -> None:
    phone, sid, _, bot = called
    assert report(phone, sid, bot, {**PLAYBACK, **body}).status_code == 422


def test_integer_ms_values_pass(called, state: Path) -> None:
    phone, sid, customer, bot = called
    assert report(phone, sid, bot, {**PLAYBACK, "bot_start_ms": 12}).status_code == 200
    assert (
        report(phone, sid, customer, {**LISTEN, "marks": [{"type": "send", "at_ms": 3}]}).status_code == 200
    )
    assert load(state, sid).events[bot].browser.bot_start_ms == 12  # type: ignore[union-attr]
