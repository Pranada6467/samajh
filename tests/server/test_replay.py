"""The headless call runner, in process, with a fake Gnani client and a fake LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_casefile import BOOK, SETTINGS, FailingLlm
from test_samajh_dialogue import answer

from samajh.clients.errors import RateLimited
from samajh.server import create_app, replay
from samajh.server.dialogue import Heard, stub_factory
from samajh.server.replay import ReplayFailed, load_script, replay_call, turn_files
from samajh.server.samajh_dialogue import samajh_factory


@pytest.fixture
def phone(fake: FakeSpeech, state: Path) -> TestClient:
    """The Samajh call as the server runs it, and the stub beside it: test wiring only (the app
    `python -m samajh.server` builds has no stub)."""
    dialogues = {"samajh": samajh_factory(BOOK, SETTINGS), "stub": stub_factory}
    return TestClient(
        create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm, dialogues=dialogues,
                   records=BOOK, settings=SETTINGS)
    )  # fmt: skip


def call_dir(root: Path, names: list[str]) -> Path:
    root.mkdir(exist_ok=True)
    for i, name in enumerate(names):
        silent = name.endswith(".none") or name.startswith("empty")
        (root / name).write_bytes(b"" if silent else make_wav(0.3 + i / 10))
    return root


def stub(files: list[Path], **more):
    return replay.Script(
        tuple(replay.ScriptTurn(None if p.suffix == ".none" or not p.stat().st_size else p) for p in files),
        more.pop("params", {}),
        "stub",
    )


def samajh_script(root: Path, fake: FakeSpeech, record: str = "hero", language: str = "hi") -> Path:
    """A prepared call: one clip per turn and a call.json naming the line each answers. The fake
    STT hears each clip as the scripted customer's reply."""
    root.mkdir(exist_ok=True)
    fake.transcripts.clear()
    twin = samajh_factory(BOOK, SETTINGS)({"record": record, "language": language})
    step, turns = twin.start(), []
    while not step.say.end_call:
        reply = answer(language, step.say)
        name = f"{len(turns) + 1:02d}.wav"
        (root / name).write_bytes(make_wav(0.5 + len(turns) / 100, tone=200 + len(turns)))
        turns.append({"file": name, "answers": step.say.lines[-1].key, "text": reply})
        fake.transcripts.append(reply)
        step = twin.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
    params = {"record": record, "language": language, "fallback": "off"}
    (root / "call.json").write_text(json.dumps({"params": params, "turns": turns}, ensure_ascii=False))
    return root


def test_a_whole_call_ended_by_the_dialogue(
    phone: TestClient, fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["03.wav", "01.wav", "02.wav", ".DS_Store"]))
    assert [p.name for p in files] == ["01.wav", "02.wav", "03.wav"]
    result = replay_call(phone, stub(files))

    assert [(t.seq, t.file, t.transcript) for t in result.turns] == [
        (1, "01.wav", "पचास हज़ार"),
        (3, "02.wav", "दो हज़ार"),
        (5, "03.wav", "बीमा"),
    ]
    assert all([r["cache_hit"] for r in t.readings] == [False] and t.stt_ms >= 0 for t in result.turns[1:])
    log = result.log
    assert (log.status, log.ended_reason) == ("ended", "dialogue")
    assert all(e.audio for e in log.events) and len(log.events) == 7
    # the stub's replies are two lines (what it heard, the next question) joined by 0.15 s
    assert result.recording_seconds == pytest.approx(0.4 + 3 * 0.95 + 0.3 + 0.4 + 0.5 + 6 * 0.5)
    assert result.recording_seconds == log.events[-1].rec_end
    expected = 4 * 0.03 + sum(
        0.002 * len(line.text) for e in log.events if e.type == "bot" for line in e.lines
    )
    assert result.est_credits == pytest.approx(expected)  # the first turn is read twice
    assert (state / "sessions" / result.session_id / "call.wav").is_file()
    assert json.dumps(result.summary(), ensure_ascii=False)


def test_the_caller_hangs_up_when_the_files_run_out(phone: TestClient, tmp_path: Path) -> None:
    result = replay_call(phone, stub(turn_files(call_dir(tmp_path / "call", ["01.wav"]))))
    assert (result.log.status, result.log.ended_reason) == ("ended", "hangup")
    assert len(result.turns) == 1
    assert [e.type for e in result.log.events] == ["bot", "customer", "bot"]
    assert all(e.audio for e in result.log.events)
    assert result.recording_seconds == pytest.approx(0.4 + 0.3 + 0.95 + 2 * 0.5)


def test_no_files_is_a_call_with_only_the_greeting(phone: TestClient) -> None:
    result = replay_call(phone, stub([]))
    assert result.turns == () and result.log.ended_reason == "hangup"
    assert result.recording_seconds == 0.4


def test_an_empty_file_or_a_none_file_is_a_silent_turn(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    result = replay_call(
        phone, stub(turn_files(call_dir(tmp_path / "call", ["01.none", "02.wav", "empty-03.wav"])))
    )
    customers = [e for e in result.log.events if e.type == "customer"]
    assert [e.source for e in customers] == ["none", "file", "none"]
    assert [len(t.readings) for t in result.turns] == [0, 1, 0]
    assert len(fake.stt_calls) == 1


def test_files_left_over_after_the_dialogue_ends_are_not_sent(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    names = ["01.wav", "02.wav", "03.wav", "04.wav"]
    result = replay_call(phone, stub(turn_files(call_dir(tmp_path / "call", names))))
    assert len(result.turns) == 3 and len(fake.stt_calls) == 4  # the first turn is read twice


def test_a_rerun_repeats_no_gnani_call(phone: TestClient, tmp_path: Path) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["01.wav", "02.wav", "03.wav"]))
    first = replay_call(phone, stub(files))
    second = replay_call(phone, stub(files))
    assert second.session_id != first.session_id
    assert [t.transcript for t in second.turns] == [t.transcript for t in first.turns]
    assert all(r["cache_hit"] for t in second.turns for r in t.readings)
    assert second.est_credits == 0
    assert all(line.tts.cache_hit for e in second.log.events if e.type == "bot" for line in e.lines)
    assert second.recording_seconds == first.recording_seconds


def test_session_options_are_passed_on(phone: TestClient, fake: FakeSpeech, tmp_path: Path) -> None:
    files = turn_files(call_dir(tmp_path / "call", ["01.wav"]))
    result = replay_call(phone, stub(files, params={"scenario": "A1"}), line_rate=16000)
    assert (result.log.line_rate, result.log.params, result.log.dialogue) == (
        16000,
        {"scenario": "A1"},
        "stub",
    )


def test_a_refused_step_raises_with_the_mapped_error(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    fake.stt_error = RateLimited(status=429, code="RATE_LIMITED", message="Only 1 active request", attempts=4)
    with pytest.raises(ReplayFailed) as caught:
        replay_call(phone, stub(turn_files(call_dir(tmp_path / "call", ["01.wav"]))))
    failed = caught.value
    assert (failed.step, failed.status) == ("turn 1 (01.wav)", 503)
    assert failed.error["code"] == "gnani_rate_limited" and failed.error["upstream_status"] == 429
    with pytest.raises(ReplayFailed) as caught:
        replay_call(phone, [], dialogue="nope")  # a bare list of files works too
    assert (caught.value.step, caught.value.error["code"]) == ("create", "unknown_dialogue")


def test_a_prepared_samajh_call_runs_to_a_case_file(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    script = load_script(samajh_script(tmp_path / "hero", fake))

    result = replay_call(phone, script, case=True, out=tmp_path / "out")

    assert (result.log.status, result.log.ended_reason) == ("ended", "dialogue")
    assert len(result.turns) == len(script.turns)
    assert [t.transcript for t in result.turns] == [t.text for t in script.turns]
    case = json.loads((tmp_path / "out" / "case.json").read_text())
    assert case == result.case and case["status"] == "ready" and case["call_outcome"] == "completed"
    assert case["tier"] == "refer"  # the hero record lacks consent; the fake LLM decided nothing
    assert result.summary()["case"]["lines"]


def test_a_call_that_stops_midway_is_continued_by_a_rerun(
    fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    script = load_script(samajh_script(tmp_path / "hero", fake))
    out = tmp_path / "out"
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm))
    real_stt, failed = fake.stt, []

    def stt_failing_on_the_fourth_clip(audio, options, **kw):
        if audio == script.turns[3].file.read_bytes() and not failed:
            failed.append(audio)
            raise RateLimited(status=429, code="RATE_LIMITED", message="busy", attempts=1)
        return real_stt(audio, options, **kw)

    fake.stt = stt_failing_on_the_fourth_clip
    with pytest.raises(ReplayFailed):
        replay_call(phone, script, out=out)
    first = json.loads((out / "replay.json").read_text())["session_id"]

    restarted = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm))
    result = replay_call(restarted, script, out=out, case=True)

    assert result.session_id == first and result.log.ended_reason == "dialogue"
    assert [t.transcript for t in result.turns] == [t.text for t in script.turns]
    assert result.case["status"] == "ready"


def test_a_script_that_answers_another_question_stops_with_script_drift(
    phone: TestClient, fake: FakeSpeech, tmp_path: Path
) -> None:
    root = samajh_script(tmp_path / "hero", fake)
    manifest = json.loads((root / "call.json").read_text())
    manifest["turns"][1]["answers"] = "consent.ask"
    (root / "call.json").write_text(json.dumps(manifest, ensure_ascii=False))

    with pytest.raises(ReplayFailed) as caught:
        replay_call(phone, load_script(root))

    assert caught.value.error["code"] == "script_drift" and caught.value.step.startswith("turn 2")


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
        assert kwargs.pop("state") == state  # without --state: the state directory of the clients
        return create_app(gnani=fake, state=state, llm=FailingLlm, **kwargs)

    monkeypatch.setattr("samajh.server.app.create_app", app_with_fake)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(state))
    directory = samajh_script(tmp_path / "call", fake)

    assert replay.main([str(directory), "--out", str(tmp_path / "out")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert profiles == ["patient"]
    assert set(out) == {
        "session_id", "session_dir", "status", "ended_reason", "turns", "recording_seconds", "est_credits", "case",
    }  # fmt: skip
    assert out["session_dir"] == str(state / "sessions" / out["session_id"])
    assert (Path(out["session_dir"]) / "case.json").is_file()
    assert out["case"]["status"] == "ready" and out["status"] == "ended" and out["est_credits"] > 0
    assert set(out["turns"][0]) == {"seq", "file", "transcript", "readings", "stt_ms", "dialogue_ms"}

    fake.tts_error = RateLimited(status=429, code="RATE_LIMITED", message="busy", attempts=4)
    assert replay.main([str(call_dir(tmp_path / "stub", ["01.wav"])), "--dialogue", "stub", "--no-case"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "gnani_rate_limited"


def test_cli_runs_the_stub_only_in_this_process(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    directory = call_dir(tmp_path / "stub", ["01.wav"])
    with pytest.raises(SystemExit) as caught:
        replay.main([str(directory), "--dialogue", "stub", "--url", "http://127.0.0.1:9"])
    assert caught.value.code == 2 and "drop --url" in capsys.readouterr().err


def test_a_running_server_refuses_the_stub_by_request(fake: FakeSpeech, state: Path, tmp_path: Path) -> None:
    default = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm))
    with pytest.raises(ReplayFailed) as caught:
        replay_call(default, stub(turn_files(call_dir(tmp_path / "call", ["01.wav"]))))
    assert (caught.value.step, caught.value.error["code"]) == ("create", "unknown_dialogue")
    assert not (state / "sessions").exists() and not fake.tts_calls


def test_cli_refuses_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as caught:
        replay.main([str(tmp_path / "nope")])
    assert caught.value.code == 2
