"""The P5 voice player and launcher, offline: the real Samajh app in process (eval/p5/serve.build_app) with
a fake Gnani client whose STT hears exactly the text its TTS voiced, the word lists as the turn reader
(plus a lenient reading of the opening, below), a failing extraction LLM and the null Batch client."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import struct
import wave
from collections import Counter
from pathlib import Path

import filelock
import pytest
import serve
import voice_run
from bank import load_customers, load_topics
from starlette.testclient import TestClient
from voices import POOLS, TTS_LANGUAGE, assign_voices

from samajh.clients.errors import BadResponse, LockTimeout
from samajh.clients.gnani import CallInfo, Speech, Transcript
from samajh.dialogue import Expecting, Intent, RuleInterpreter
from samajh.dialogue.interpret import Interpretation
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.settings import load_settings

P5_CODE = Path(__file__).resolve().parents[2] / "eval" / "p5"
CUSTOMER = "P5-C029"  # well informed, Hindi: talks through the whole call
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)


def _frames(audio: bytes) -> bytes:
    with wave.open(io.BytesIO(audio)) as f:
        return f.readframes(f.getnframes())


class VoiceFake:
    """TTS makes a clip unique to its text; STT hears a clip as the text that made it ("" if unknown).
    Every miss counts toward `credits` as the real client's estimates would; a repeat is a cache hit."""

    def __init__(self) -> None:
        self.heard: dict[str, str] = {}
        self.seen: set[str] = set()
        self.tts_calls: list[tuple[str, str]] = []
        self.stt_calls = 0
        self.credits = 0.0
        self.tts_error: Exception | None = None
        self.fail_on_tts_call: int | None = None

    def _info(self, key: str, credits: float) -> CallInfo:
        hit = key in self.seen
        self.seen.add(key)
        self.credits += 0.0 if hit else credits
        return CallInfo(cache_hit=hit, cache_key=key, seconds=0.0, est_credits=0.0 if hit else credits,
                        attempts=0 if hit else 1)  # fmt: skip

    def tts(self, text: str, options) -> Speech:
        self.tts_calls.append((text, options.voice))
        if self.fail_on_tts_call is not None and len(self.tts_calls) == self.fail_on_tts_call:
            raise LockTimeout("no lock within 120s")
        digest = hashlib.sha256(f"{text}|{options.voice}".encode()).digest()
        tone = 200 + digest[0] * 4
        n = 2400 + digest[1] * 8
        pcm = b"".join(
            struct.pack("<h", int(6000 * math.sin(2 * math.pi * tone * i / 8000))) for i in range(n)
        )
        pcm += digest  # 16 samples that make the clip unique to its text
        out = io.BytesIO()
        with wave.open(out, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(options.sample_rate)
            f.writeframes(pcm)
        self.heard[hashlib.sha256(pcm).hexdigest()] = text
        key = hashlib.sha256((text + options.model_dump_json()).encode()).hexdigest()
        return Speech(audio=out.getvalue(), content_type="audio/wav", container="wav",
                      sample_rate=options.sample_rate, audio_seconds=n / 8000, request_id=None,
                      call=self._info(key, 0.002 * len(text)))  # fmt: skip

    def stt(self, audio: bytes, options, *, audio_format: str = "wav") -> Transcript:
        self.stt_calls += 1
        frames = _frames(audio)
        key = hashlib.sha256(audio + options.model_dump_json().encode()).hexdigest()
        return Transcript(text=self.heard.get(hashlib.sha256(frames).hexdigest(), ""), literal=None,
                          model=options.model, detected_language=None, request_id=None, truncated=False,
                          call=self._info(key, 0.01 * len(frames) / 16000))  # fmt: skip

    def batch_transcribe(self, *args, **kwargs):
        raise AssertionError("Batch must be off: the launcher's null client answers instead")


class Lenient:
    """The word lists, except that an unsettled reply to the name or go-ahead question reads as yes
    (the live call asks its LLM classifier there; this test has none)."""

    def __init__(self) -> None:
        self.rules = RuleInterpreter()

    def interpret(self, text, *, language, expecting, question):
        heard = self.rules.interpret(text, language=language, expecting=expecting, question=question)
        if expecting in (Expecting.identity, Expecting.go_ahead) and not heard.settled:
            return Interpretation(intent=Intent.yes)
        return heard


class FailingLlm:
    def complete(self, schema, messages, **options):
        raise BadResponse("the fake model answered nothing usable")


@pytest.fixture
def fake() -> VoiceFake:
    return VoiceFake()


def _app(state: Path, fake: VoiceFake, records=None, batch=None):
    return serve.build_app(state, gnani=fake, records=records if records is not None else serve.p5_records(),
                           settings=SETTINGS, interpreter=Lenient(), llm=FailingLlm, batch=batch)  # fmt: skip


def _call(http, fake: VoiceFake, out: Path, cid: str = CUSTOMER):
    customers = load_customers()
    voice = assign_voices(customers)[cid]
    return voice_run.run_customer(http, fake, customers[cid], load_topics(), voice, out, lambda: fake.credits)


def _run_open_keys() -> set[str]:
    """The keys `text_run.run_open` writes (its `_base` dict and every `record["..."] =`), and run.py's
    `finished_utc`: read from the source, so a change there fails this test."""
    source = (P5_CODE / "text_run.py").read_text(encoding="utf-8")
    base = source[source.index("def _base(") : source.index("def _opening(")]
    keys = set(re.findall(r'"([a-z_]+)":', base)) | set(re.findall(r'record\["([a-z_]+)"\] =', source))
    keys -= {"closed"}  # the closed arm's only
    return keys | {"finished_utc"}


def test_a_whole_call_reaches_a_ready_case_file_with_batch_off(fake: VoiceFake, tmp_path: Path) -> None:
    batch = serve.NullBatch()
    http = TestClient(_app(tmp_path / "state", fake, batch=batch))
    record = _call(http, fake, tmp_path / "out")

    saved = json.loads((tmp_path / "out" / "calls" / f"{CUSTOMER}__open__L0.json").read_text())
    assert saved == json.loads(json.dumps(record, ensure_ascii=False))
    assert set(saved) == set(voice_run.CALL_KEYS) and _run_open_keys() <= set(saved)
    assert (saved["status"], saved["case_status"], saved["path"]) == ("ok", "ready", "voice"), saved["errors"]
    assert batch.calls == 1 and "batch" not in saved["case_failed"]
    assert saved["outcome"] == "completed" and saved["tier"] in (
        "refer",
        "incomplete",
        "understanding_gap",
        "clear",
    )
    assert saved["speaker_confirmed"] is True and saved["degraded_turns"] == 0
    assert len(saved["turns"]) >= 10 and saved["final_bot"]
    for turn in saved["turns"]:
        assert turn["transcript"] == turn["reply"]["text"]  # the fake line hears what was voiced
        assert turn["readings"] and all("intent" in r for r in turn["readings"])
        assert turn["stt"][0]["role"] == "primary" and turn["bot"][-1]["key"] == turn["reply"]["line_key"]
        assert set(turn["reply"]) >= {"topic", "variant", "text"}
    assert any(len(t["stt"]) == 2 for t in saved["turns"])  # figure turns are read twice
    voices = {v for _, v in fake.tts_calls}
    assert voices == {"Shivani", saved["voice"]}
    assert saved["ledger"]["delta"] == pytest.approx(saved["ledger"]["after"] - saved["ledger"]["before"])


def test_the_voice_call_answers_as_the_text_chooser_does(
    fake: VoiceFake, tmp_path: Path, monkeypatch
) -> None:
    """With a line that hears every reply as written, the voice path gives the same replies as the
    word-list simulation of the same chooser (given the same reader)."""
    from samajh import dialogue as core

    http = TestClient(_app(tmp_path / "state", fake))
    record = _call(http, fake, tmp_path / "out")
    monkeypatch.setattr(core, "RuleInterpreter", Lenient)  # the simulation builds core.RuleInterpreter()
    sim = voice_run.simulate(load_customers()[CUSTOMER], load_topics())
    assert [t["reply"]["text"] for t in record["turns"]] == [r["text"] for r in sim["replies"]]
    assert record["outcome"] == sim["outcome"]


def test_a_done_customer_is_skipped_on_rerun(fake: VoiceFake, tmp_path: Path) -> None:
    http = TestClient(_app(tmp_path / "state", fake))
    _call(http, fake, tmp_path / "out")
    calls = len(fake.tts_calls), fake.stt_calls
    counts = voice_run.run(http, fake, [CUSTOMER], out=tmp_path / "out", ceiling=10, baseline=0.0,
                           ledger_total=lambda: fake.credits, log=lambda _: None)  # fmt: skip
    assert counts["skipped"] == 1 and counts["done"] == 0
    assert (len(fake.tts_calls), fake.stt_calls) == calls


def test_a_crash_mid_call_resumes_the_same_session(fake: VoiceFake, tmp_path: Path) -> None:
    out = tmp_path / "out"
    fake.fail_on_tts_call = 9  # the key is busy partway through: a run-level stop
    http = TestClient(_app(tmp_path / "state", fake))
    with pytest.raises(voice_run.RunStopped):
        _call(http, fake, out)
    assert not (out / "calls").exists()
    progress = json.loads((out / "progress" / f"{CUSTOMER}.json").read_text())
    taken = len(progress["turns"])
    assert taken >= 1

    fake.fail_on_tts_call = None
    restarted = TestClient(_app(tmp_path / "state", fake))  # a new server run on the same state
    record = _call(restarted, fake, out)
    assert record["session_id"] == progress["session_id"] and record["resumed"] == 1
    assert record["status"] == "ok" and record["case_status"] == "ready"
    assert record["turns"][:taken] == progress["turns"]


def test_a_call_that_errors_becomes_a_no_result_file(fake: VoiceFake, tmp_path: Path) -> None:
    packaged_only = load_book(PACKAGED_DIR)  # the P5 record is not on this server
    http = TestClient(_app(tmp_path / "state", fake, records=packaged_only))
    record = _call(http, fake, tmp_path / "out")
    saved = json.loads((tmp_path / "out" / "calls" / f"{CUSTOMER}__open__L0.json").read_text())
    assert record["status"] == saved["status"] == "no_result"
    assert saved["errors"][0]["error"].startswith("StepRefused('create")
    assert set(saved) == set(voice_run.CALL_KEYS)
    # and it is never rerun
    counts = voice_run.run(http, fake, [CUSTOMER], out=tmp_path / "out", ceiling=10, baseline=0.0,
                           ledger_total=lambda: 0.0, log=lambda _: None)  # fmt: skip
    assert counts["skipped"] == 1


def test_the_run_stops_at_the_ceiling(fake: VoiceFake, tmp_path: Path) -> None:
    http = TestClient(_app(tmp_path / "state", fake))
    counts = voice_run.run(http, fake, [CUSTOMER, "P5-C047"], out=tmp_path / "out", ceiling=5.0, baseline=0.0,
                           ledger_total=lambda: 5.0, log=lambda _: None)  # fmt: skip
    assert counts["done"] == 0 and counts["not_started"] == 2 and counts["stopped"].startswith("ceiling")
    assert fake.tts_calls == []


def test_the_voice_rule_is_deterministic() -> None:
    customers = load_customers()
    first, again = assign_voices(customers), assign_voices(customers)
    assert first == again and set(first) == set(customers)
    for cid, voice in first.items():
        assert voice in POOLS[customers[cid].speaker["gender"]]
    per_voice = Counter(first.values())
    assert max(per_voice.values()) - min(per_voice.values()) <= 1 + 1  # pools of 6 per gender, ~5 each
    # the smoke preset: both languages, a female and a male voice, one third party
    smoke = voice_run.smoke_ids(customers, first)
    assert len(set(smoke)) == 4
    assert {customers[c].language for c in smoke} == {"hi", "hi-en"}
    assert {customers[c].speaker["gender"] for c in smoke} == {"f", "m"}
    assert sum(customers[c].kind == "third_party" for c in smoke) == 1


def test_customer_tts_language_is_the_servers_code() -> None:
    from samajh.server.samajh_dialogue import TTS_LANGUAGE as SERVER
    from samajh.types import Language

    assert TTS_LANGUAGE == {lang: SERVER[Language(lang)] for lang in ("hi", "hi-en")}


def test_the_idle_check_refuses_when_the_lock_is_held(tmp_path: Path) -> None:
    lock_path = tmp_path / "gnani.lock"
    quiet = {"rows": lambda: 7, "wait": 0, "sleep": lambda _: None, "phone_port": None}
    assert voice_run.idle_check(lock_path=lock_path, **quiet) == []
    holder = filelock.FileLock(lock_path, thread_local=False)
    with holder:
        problems = voice_run.idle_check(lock_path=lock_path, **quiet)
    assert len(problems) == 1 and "holds" in problems[0]
    growing = iter([10, 11])
    problems = voice_run.idle_check(lock_path=lock_path, rows=lambda: next(growing), wait=0,
                                    sleep=lambda _: None, phone_port=None)  # fmt: skip
    assert problems == ["the ledger grew from 10 to 11 rows in 0 s"]


def test_the_launcher_refuses_the_phone_port_and_a_separate_ledger(monkeypatch, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        serve.main(["--port", "8085", "--state", str(tmp_path)])
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path))
    with pytest.raises(SystemExit):
        serve.set_env(ceiling=10, baseline=None)
