"""The session log on disk, the recording layout, and call.wav assembly."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from serverkit import make_wav, wav_shape

from samajh.server.sessionlog import (
    SESSION_ID,
    BotEvent,
    CustomerEvent,
    ErrorEvent,
    SessionLog,
    SessionStore,
    SttSettings,
    TtsSettings,
    lay_out,
    new_session_id,
)

SID = "20261110T142233-9f2c4e1ab07d"


def bot(seq: int, seconds: float | None) -> BotEvent:
    audio = None if seconds is None else f"audio/bot-{seq:03d}.wav"
    return BotEvent(
        seq=seq, at=0.0, text="प्रश्न", language="hi-IN", end_call=False, audio=audio, audio_seconds=seconds
    )


def customer(seq: int, seconds: float | None) -> CustomerEvent:
    audio = None if seconds is None else f"audio/customer-{seq:03d}.wav"
    source = "none" if seconds is None else "file"
    return CustomerEvent(seq=seq, at=0.0, source=source, transcript="हाँ", audio=audio, audio_seconds=seconds)


def failed(seq: int, seconds: float) -> ErrorEvent:
    return ErrorEvent(
        seq=seq,
        at=0.0,
        stage="stt",
        status=502,
        code="gnani_server_error",
        message="x",
        audio=f"audio/customer-{seq:03d}.wav",
        audio_seconds=seconds,
    )


def log_of(events: list, line_rate: int = 8000) -> SessionLog:
    return SessionLog(
        session_id=SID,
        created_at="2026-11-10T14:22:33Z",
        dialogue="stub",
        params={},
        line_rate=line_rate,
        stt=SttSettings(),
        tts=TtsSettings(),
        events=events,
    )


def store_with_audio(root: Path, log: SessionLog) -> SessionStore:
    store = SessionStore(root)
    for event in log.events:
        if event.audio:
            name = event.audio.removeprefix("audio/")
            # A different pitch per event, so a wrong order changes the bytes.
            store.write_audio(
                SID, name, make_wav(event.audio_seconds, log.line_rate, tone=200 + 50 * event.seq)
            )
    return store


def test_new_ids_match_the_pattern_and_differ() -> None:
    ids = {new_session_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(SESSION_ID.fullmatch(i) for i in ids)


def test_lay_out_places_audio_in_seq_order_with_gaps() -> None:
    events = [bot(0, 1.0), customer(1, 2.0), bot(2, None), customer(3, None), bot(4, 0.5)]
    lay_out(events, gap_seconds=0.5)
    assert [(e.rec_start, e.rec_end) for e in events] == [
        (0.0, 1.0),
        (1.5, 3.5),
        (None, None),
        (None, None),
        (4.0, 4.5),
    ]


def test_lay_out_skips_error_events_and_clears_stale_positions() -> None:
    error = failed(1, 2.0)
    error.rec_start, error.rec_end = 9.0, 11.0
    events = [bot(0, 1.0), error, customer(2, 1.0)]
    lay_out(events)
    assert (error.rec_start, error.rec_end) == (None, None)
    assert (events[2].rec_start, events[2].rec_end) == (1.5, 2.5)


def test_save_then_load_round_trips_and_lays_out(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    log = log_of([bot(0, 1.0), customer(1, 2.0)])
    store.save(log)
    loaded = store.load(SID)
    assert loaded == log
    assert loaded.events[1].rec_start == 1.5
    assert [p.name for p in (tmp_path / SID).iterdir()] == ["session.json"]  # no temp file left


@pytest.mark.parametrize("bad", ["", "nope", "../" + SID, SID + "/..", SID.upper(), SID + "\n"])
def test_load_of_a_malformed_or_unknown_id_is_none(tmp_path: Path, bad: str) -> None:
    store = SessionStore(tmp_path)
    store.save(log_of([]))
    assert store.load(bad) is None
    assert store.load("20261110T142233-000000000000") is None


def test_load_of_a_corrupt_file_is_none(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    store.save(log_of([]))
    (tmp_path / SID / "session.json").write_text("{not json")
    assert store.load(SID) is None


@pytest.mark.parametrize("name", ["../x.wav", "bot-1.wav", "bot-000.wav/..", "call.wav", "bot-0000.wav", ""])
def test_audio_paths_are_built_only_from_valid_names(tmp_path: Path, name: str) -> None:
    store = SessionStore(tmp_path)
    with pytest.raises(ValueError):
        store.write_audio(SID, name, b"x")
    with pytest.raises(ValueError):
        store.read_audio(SID, name)
    with pytest.raises(ValueError):
        store.write_audio("../escape", "bot-000.wav", b"x")
    assert not any(tmp_path.parent.glob("escape*"))


def test_audio_round_trip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    wav = make_wav(0.2)
    assert store.write_audio(SID, "customer-001.wav", wav) == "audio/customer-001.wav"
    assert store.read_audio(SID, "customer-001.wav") == wav
    assert store.read_audio(SID, "customer-002.wav") is None


@pytest.mark.parametrize("rate", [8000, 16000])
def test_recording_is_the_events_in_order_with_gaps(tmp_path: Path, rate: int) -> None:
    log = log_of([bot(0, 1.0), customer(1, 2.0), bot(2, None), customer(3, None), bot(4, 0.5)], rate)
    store = store_with_audio(tmp_path, log)
    store.save(log)
    recording = store.assemble_recording(log)

    data = store.read_recording(SID)
    channels, width, got_rate, frames = wav_shape(data)
    assert (channels, width, got_rate) == (1, 2, rate)
    assert frames / rate == recording.seconds == log.events[-1].rec_end == 4.5
    assert (recording.sample_rate, recording.gap_seconds) == (rate, 0.5)
    assert recording.sha256 == hashlib.sha256(data).hexdigest()

    pcm = data[44:]
    for event in (log.events[0], log.events[1], log.events[4]):
        clip = store.read_audio(SID, event.audio.removeprefix("audio/"))[44:]
        start = round(event.rec_start * rate) * 2
        assert pcm[start : start + len(clip)] == clip
    gap = pcm[round(1.0 * rate) * 2 : round(1.5 * rate) * 2]
    assert gap == bytes(len(gap)) and len(gap) == rate  # half a second of 16-bit silence


def test_recording_leaves_out_error_events(tmp_path: Path) -> None:
    with_error = log_of([bot(0, 1.0), failed(1, 3.0), customer(2, 1.0)])
    store = store_with_audio(tmp_path, with_error)
    assert store.assemble_recording(with_error).seconds == 2.5


def test_recording_is_idempotent(tmp_path: Path) -> None:
    log = log_of([bot(0, 1.0), customer(1, 0.3)])
    store = store_with_audio(tmp_path, log)
    first = store.assemble_recording(log)
    first_bytes = store.read_recording(SID)
    assert store.assemble_recording(log) == first
    assert store.read_recording(SID) == first_bytes


def test_recording_refuses_audio_at_another_rate(tmp_path: Path) -> None:
    log = log_of([bot(0, 1.0)])
    store = SessionStore(tmp_path)
    store.write_audio(SID, "bot-000.wav", make_wav(1.0, 16000))
    with pytest.raises(ValueError):
        store.assemble_recording(log)


def test_no_recording_before_one_is_assembled(tmp_path: Path) -> None:
    assert SessionStore(tmp_path).read_recording(SID) is None
