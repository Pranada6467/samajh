"""The session hash chain: saves append, verification names the first tampering."""

from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import pytest

from samajh.evidence.session import chain_entries, entry_index, verify_session_dir
from samajh.server.sessionlog import (
    BotEvent,
    BrowserPlayback,
    CustomerEvent,
    SessionLog,
    SessionStore,
    SttSettings,
    TtsSettings,
)

SID = "20261110T142233-9f2c4e1ab07d"
SECRET = "उन्नीस सौ अस्सी"  # stands in for a birth-year reply


def wav(seq: int) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(bytes([seq % 256, 1]) * 800)
    return out.getvalue()


def new_log() -> SessionLog:
    return SessionLog(
        session_id=SID,
        created_at="2026-11-10T14:22:33Z",
        dialogue="stub",
        params={},
        line_rate=8000,
        stt=SttSettings(),
        tts=TtsSettings(),
    )


def add_turn(store: SessionStore, log: SessionLog, text: str = "हाँ") -> None:
    seq = len(log.events)
    if seq % 2 == 0:
        name = f"bot-{seq:03d}.wav"
        ev = BotEvent(seq=seq, at=seq, text="प्रश्न", language="hi-IN", end_call=False)
    else:
        name = f"customer-{seq:03d}.wav"
        ev = CustomerEvent(seq=seq, at=seq, source="file", transcript=text)
    ev.audio = store.write_audio(SID, name, wav(seq))
    ev.audio_seconds = 0.1
    log.events.append(ev)
    log.dialogue_state = f"state {seq} {text}"
    store.save(log)


def session(tmp_path: Path, turns: int = 4, end: bool = True) -> tuple[SessionStore, SessionLog, Path]:
    store, log = SessionStore(tmp_path), new_log()
    store.save(log)
    for k in range(turns):
        add_turn(store, log, SECRET if k == 1 else "हाँ")
    if end:
        log.status = "ended"
        log.recording = store.assemble_recording(log)
        store.save(log)
    return store, log, tmp_path / SID


def edit_json(path: Path, change) -> None:
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def rewrite_chain(d: Path, lines: list[str]) -> None:
    (d / "chain.jsonl").write_text("".join(line + "\n" for line in lines))


def chain_lines(d: Path) -> list[str]:
    return (d / "chain.jsonl").read_text().splitlines()


def test_a_session_saved_over_several_turns_verifies(tmp_path: Path) -> None:
    _store, log, d = session(tmp_path)
    check = verify_session_dir(d)
    assert check.status == "verified", check.problem
    assert check.seal is not None and check.head == log.chain.head
    assert check.entries == log.chain.entries == len(chain_entries(d))
    assert entry_index(d, log.chain.head) == check.entries - 1


def test_repeated_save_with_no_change_appends_nothing(tmp_path: Path) -> None:
    store, log, d = session(tmp_path)
    before = (d / "chain.jsonl").read_bytes()
    store.save(log)
    store.save(store.load(SID))
    assert (d / "chain.jsonl").read_bytes() == before
    assert verify_session_dir(d).status == "verified"


def test_supersede_and_browser_report_append_and_still_verify(tmp_path: Path) -> None:
    store, log, d = session(tmp_path, end=False)
    n = log.chain.entries
    log.events[0].browser = BrowserPlayback(bot_start_ms=900.0, completed=True)
    store.save(log)
    assert log.chain.entries == n + 1
    log.events[3].superseded = True
    store.save(log)
    assert log.chain.entries > n + 1
    assert verify_session_dir(d).status == "verified"


def test_birth_year_reply_never_appears_in_the_chain(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    assert SECRET in (d / "session.json").read_text()
    assert SECRET not in (d / "chain.jsonl").read_text(encoding="utf-8")


def test_one_byte_changed_in_event_audio(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    f = d / "audio" / "customer-003.wav"
    data = bytearray(f.read_bytes())
    data[-1] ^= 1
    f.write_bytes(bytes(data))
    check = verify_session_dir(d)
    assert check.status == "mismatch" and check.problem.startswith("audio of event seq 3")


def test_one_byte_changed_in_call_wav(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    data = bytearray((d / "call.wav").read_bytes())
    data[-1] ^= 1
    (d / "call.wav").write_bytes(bytes(data))
    assert verify_session_dir(d).problem == "call.wav does not match recording.sha256"


def test_event_edited_in_session_json(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    edit_json(d / "session.json", lambda s: s["events"][1].update(transcript="नहीं"))
    assert verify_session_dir(d).problem.startswith("event seq 1 in session.json does not match")


def test_two_events_swapped(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)

    def swap(s):
        s["events"][1], s["events"][3] = s["events"][3], s["events"][1]

    edit_json(d / "session.json", swap)
    assert verify_session_dir(d).problem == "session.json event at position 1 has seq 3"


def test_chain_line_deleted(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    lines = chain_lines(d)
    del lines[2]
    rewrite_chain(d, lines)
    assert verify_session_dir(d).problem == "chain line 2: has i=3, expected 2"


def test_two_chain_lines_swapped(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    lines = chain_lines(d)
    lines[2], lines[3] = lines[3], lines[2]
    rewrite_chain(d, lines)
    assert verify_session_dir(d).problem == "chain line 2: has i=3, expected 2"


def test_entry_edited_with_its_own_hash_recomputed_breaks_the_next_prev(tmp_path: Path) -> None:
    from samajh.evidence.digest import digest

    _, _, d = session(tmp_path)
    lines = chain_lines(d)
    entry = json.loads(lines[2])
    entry["sha256"] = "f" * 64
    entry["hash"] = digest({k: v for k, v in entry.items() if k != "hash"})
    lines[2] = json.dumps(entry)
    rewrite_chain(d, lines)
    problem = verify_session_dir(d).problem
    assert problem.startswith("chain entry 3:") and "prev does not match entry 2's hash" in problem


def test_entry_edited_without_rehash(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    lines = chain_lines(d)
    entry = json.loads(lines[1])
    entry["at"] = "2020-01-01T00:00:00.000+00:00"
    lines[1] = json.dumps(entry)
    rewrite_chain(d, lines)
    assert (
        "entry 1" in verify_session_dir(d).problem
        and "hash does not recompute" in verify_session_dir(d).problem
    )


def test_chain_head_edited_in_session_json(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    edit_json(d / "session.json", lambda s: s["chain"].update(head="0" * 64))
    assert "does not match chain.jsonl" in verify_session_dir(d).problem


def test_missing_chain_file_with_chain_in_session_json_is_a_mismatch(tmp_path: Path) -> None:
    _, _, d = session(tmp_path)
    (d / "chain.jsonl").unlink()
    assert verify_session_dir(d).status == "mismatch"


def test_torn_last_line_is_moved_aside_on_the_next_save(tmp_path: Path) -> None:
    store, log, d = session(tmp_path, end=False)
    with (d / "chain.jsonl").open("ab") as f:
        f.write(b'{"i": 99, "pre')
    assert verify_session_dir(d).status == "mismatch"
    add_turn(store, log)
    assert (d / "chain.jsonl.torn").read_bytes() == b'{"i": 99, "pre\n'
    assert verify_session_dir(d).status == "verified"


def legacy(tmp_path: Path) -> Path:
    _store, _log, d = session(tmp_path, turns=2, end=False)
    (d / "chain.jsonl").unlink()
    edit_json(d / "session.json", lambda s: s.pop("chain"))
    return d


def test_a_legacy_session_loads_and_is_unverifiable(tmp_path: Path) -> None:
    d = legacy(tmp_path)
    assert SessionStore(tmp_path).load(SID) is not None
    check = verify_session_dir(d)
    assert (check.status, check.problem) == ("unverifiable", "written before the evidence chain")


def test_a_legacy_session_saved_again_is_adopted_and_verifies(tmp_path: Path) -> None:
    legacy(tmp_path)
    store = SessionStore(tmp_path)
    log = store.load(SID)
    add_turn(store, log)
    entries = chain_entries(tmp_path / SID)
    assert entries[0].get("adopted") is True
    assert not any("adopted" in e for e in entries[1:])
    check = verify_session_dir(tmp_path / SID)
    assert check.status == "verified" and check.adopted


@pytest.mark.parametrize("missing", [True])
def test_missing_audio_file_is_null_and_its_return_is_caught(tmp_path: Path, missing: bool) -> None:
    store, log, d = session(tmp_path, end=False)
    (d / "audio" / "bot-002.wav").unlink()
    store.save(log)  # the chain records the audio as gone
    assert chain_entries(d)[-1]["audio_sha256"] is None
    assert verify_session_dir(d).status == "verified"
    (d / "audio" / "bot-002.wav").write_bytes(wav(2))
    assert verify_session_dir(d).problem.startswith("audio of event seq 2")
