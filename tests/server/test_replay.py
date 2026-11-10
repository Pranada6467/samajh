"""The headless call runner, in process, with a fake Gnani client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient

from samajh.clients.errors import RateLimited
from samajh.server import create_app, replay
from samajh.server.replay import ReplayFailed, replay_call, turn_files


@pytest.fixture
def phone(fake: FakeSpeech, state: Path) -> TestClient:
    return TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None))


def call_dir(root: Path, names: list[str]) -> Path:
    root.mkdir(exist_ok=True)
    for i, name in enumerate(names):
        silent = name.endswith(".none") or name.startswith("empty")
        (root / name).write_bytes(b"" if silent else make_wav(0.3 + i / 10))
    return root


def test_a_whole_call_ended_by_the_dialogue(
    phone: TestClient, fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["03.wav", "01.wav", "02.wav", ".DS_Store"]))
    assert [p.name for p in files] == ["01.wav", "02.wav", "03.wav"]
    result = replay_call(phone, files)

    assert [(t.seq, t.file, t.transcript) for t in result.turns] == [
        (1, "01.wav", "पचास हज़ार"),
        (3, "02.wav", "दो हज़ार"),
        (5, "03.wav", "बीमा"),
    ]
    assert all(t.cache_hit is False and t.attempts == 1 and t.stt_ms >= 0 for t in result.turns)
    log = result.log
    assert (log.status, log.ended_reason) == ("ended", "dialogue")
    assert all(e.audio for e in log.events) and len(log.events) == 7
    assert result.recording_seconds == pytest.approx(4 * 0.4 + 0.3 + 0.4 + 0.5 + 6 * 0.5)
    assert result.recording_seconds == log.events[-1].rec_end
    expected = 3 * 0.03 + sum(0.002 * len(e.text) for e in log.events if e.type == "bot")
    assert result.est_credits == pytest.approx(expected)
    assert (state / "sessions" / result.session_id / "call.wav").is_file()
    assert json.dumps(result.summary(), ensure_ascii=False)


def test_the_caller_hangs_up_when_the_files_run_out(phone: TestClient, tmp_path: Path) -> None:
    result = replay_call(phone, turn_files(call_dir(tmp_path / "call", ["01.wav"])))
    assert (result.log.status, result.log.ended_reason) == ("ended", "hangup")
    assert len(result.turns) == 1
    assert [e.type for e in result.log.events] == ["bot", "customer", "bot"]
    assert all(e.audio for e in result.log.events)
    assert result.recording_seconds == pytest.approx(0.4 + 0.3 + 0.4 + 2 * 0.5)


def test_no_files_is_a_call_with_only_the_greeting(phone: TestClient) -> None:
    result = replay_call(phone, [])
    assert result.turns == () and result.log.ended_reason == "hangup"
    assert result.recording_seconds == 0.4


def test_an_empty_file_or_a_none_file_is_a_silent_turn(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    result = replay_call(
        phone, turn_files(call_dir(tmp_path / "call", ["01.none", "02.wav", "empty-03.wav"]))
    )
    customers = [e for e in result.log.events if e.type == "customer"]
    assert [e.source for e in customers] == ["none", "file", "none"]
    assert [(t.cache_hit, t.attempts) for t in result.turns] == [(None, None), (False, 1), (None, None)]
    assert len(fake.stt_calls) == 1


def test_files_left_over_after_the_dialogue_ends_are_not_sent(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    names = ["01.wav", "02.wav", "03.wav", "04.wav"]
    result = replay_call(phone, turn_files(call_dir(tmp_path / "call", names)))
    assert len(result.turns) == 3 and len(fake.stt_calls) == 3


def test_a_rerun_repeats_no_gnani_call(phone: TestClient, tmp_path: Path) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["01.wav", "02.wav", "03.wav"]))
    first = replay_call(phone, files)
    second = replay_call(phone, files)
    assert second.session_id != first.session_id
    assert [t.transcript for t in second.turns] == [t.transcript for t in first.turns]
    assert all(t.cache_hit for t in second.turns)
    assert second.est_credits == 0
    assert all(e.tts.cache_hit for e in second.log.events if e.type == "bot")
    assert second.recording_seconds == first.recording_seconds


def test_session_options_are_passed_on(phone: TestClient, fake: FakeSpeech, tmp_path: Path) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["01.wav"]))
    result = replay_call(phone, files, line_rate=16000, stt_model="prisma-v2.5", params={"scenario": "A1"})
    assert (result.log.line_rate, result.log.stt.model, result.log.params) == (
        16000,
        "prisma-v2.5",
        {"scenario": "A1"},
    )
    assert fake.stt_calls[0][1].model == "prisma-v2.5"


def test_a_refused_step_raises_with_the_mapped_error(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    fake.stt_error = RateLimited(status=429, code="RATE_LIMITED", message="Only 1 active request", attempts=4)
    with pytest.raises(ReplayFailed) as caught:
        replay_call(phone, turn_files(call_dir(tmp_path / "call", ["01.wav"])))
    failed = caught.value
    assert (failed.step, failed.status) == ("turn 1 (01.wav)", 503)
    assert failed.error["code"] == "gnani_rate_limited" and failed.error["upstream_status"] == 429
    with pytest.raises(ReplayFailed) as caught:
        replay_call(phone, [], dialogue="nope")
    assert (caught.value.step, caught.value.error["code"]) == ("create", "unknown_dialogue")


def test_cli_prints_one_json_summary(
    fake: FakeSpeech,
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    profiles = []

    def app_with_fake(**kwargs: object):
        profiles.append(kwargs.pop("profile"))
        return create_app(gnani=fake, state=state, **kwargs)

    monkeypatch.setattr("samajh.server.app.create_app", app_with_fake)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    directory = call_dir(tmp_path / "call", ["01.wav", "02.none", "03.wav"])

    assert replay.main([str(directory), "--param", "scenario=A1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert profiles == ["patient"]
    assert set(out) == {
        "session_id", "session_dir", "status", "ended_reason", "turns", "recording_seconds", "est_credits",
    }  # fmt: skip
    assert out["session_dir"] == str(state / "sessions" / out["session_id"])
    assert (Path(out["session_dir"]) / "session.json").is_file()
    assert [t["file"] for t in out["turns"]] == ["01.wav", "02.none", "03.wav"]
    assert set(out["turns"][0]) == {"seq", "file", "transcript", "stt_ms", "cache_hit", "attempts"}
    assert out["status"] == "ended" and out["est_credits"] > 0

    fake.tts_error = RateLimited(status=429, code="RATE_LIMITED", message="busy", attempts=4)
    assert replay.main([str(directory), "--dialogue", "stub"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "gnani_rate_limited"


def test_cli_refuses_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as caught:
        replay.main([str(tmp_path / "nope")])
    assert caught.value.code == 2
