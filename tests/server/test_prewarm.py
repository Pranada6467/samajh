"""Bot lines made before they are needed: at server start (static lines and the record book's
first-name lines) and inside session create (a session's missing first-name lines), never in the
background. Fake clients only; no network."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from serverkit import FakeSpeech, make_wav

from samajh.clients._runtime import cache_key
from samajh.clients.errors import ClientError, ConfigError
from samajh.clients.gnani import GnaniClient, Speech, Timbre
from samajh.clients.gnani.client import TTS_PATH
from samajh.server import app as app_module
from samajh.server import prompts, samajh_dialogue, speech
from samajh.server.app import create_app
from samajh.server.records import default_book
from samajh.server.samajh_dialogue import TTS_LANGUAGE
from samajh.server.settings import load_settings
from samajh.types import Language

BASE = load_settings()
SETTINGS = BASE.model_copy(update={"prewarm": BASE.prewarm.model_copy(update={"languages": (Language.hi,)})})
HI = speech.tts_options(SETTINGS.tts_for(Language.hi), TTS_LANGUAGE[Language.hi], 8000)


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("a test reached for the live Gnani client")

    def no_key(**overrides):
        raise ConfigError("OPENROUTER_API_KEY is not set")

    monkeypatch.setattr(speech, "live_client", refuse)
    monkeypatch.setattr(app_module, "live_client", refuse)  # app.py holds its own name for it
    monkeypatch.setattr(samajh_dialogue.LlmClient, "from_env", no_key)
    monkeypatch.delenv("SAMAJH_RECORDS_DIR", raising=False)


class Warmable(FakeSpeech):
    """FakeSpeech with `tts_cached`, a line that fails, and a gate that holds every TTS call."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_on: str | None = None
        self.tts_gate = threading.Event()
        self.tts_gate.set()
        self.stt_gate = threading.Event()
        self.stt_gate.set()
        self.stt_started = threading.Event()

    def _key(self, text: str, options: Timbre) -> str:
        return hashlib.sha256((text + options.model_dump_json()).encode()).hexdigest()

    def tts_cached(self, text: str, options: Timbre) -> bool:
        return self._key(text, options) in self._seen

    def tts(self, text: str, options: Timbre) -> Speech:
        if self.fail_on is not None and text == self.fail_on:
            raise ClientError("Timbre answered 500")
        self.tts_gate.wait(10)
        return super().tts(text, options)

    def stt(self, audio, options, **kwargs):
        self.stt_started.set()
        self.stt_gate.wait(10)
        return super().stt(audio, options, **kwargs)

    def made(self, text: str, options: Timbre = HI) -> bool:
        return self.tts_cached(text, options)


STATIC = [text for _, text in prompts.prewarm_lines(Language.hi, prompts.servable(default_book(), None))]
HI_EN = speech.tts_options(SETTINGS.tts_for(Language.hi_en), TTS_LANGUAGE[Language.hi_en], 8000)


def app_on(fake: Warmable, state: Path) -> TestClient:
    return TestClient(create_app(gnani=fake, state=state, settings=SETTINGS, web_dir=None, prewarm=True))


def seed_static(fake: Warmable, texts: list[str]) -> None:
    for text in texts:
        fake.tts(text, HI)
    fake.tts_calls.clear()


def first_name_lines(record_id: str, language: Language = Language.hi) -> list[str]:
    source = prompts.Slots.of(default_book().get(record_id))
    return [text for _, text in prompts.record_lines(language, source)]


def wait_for(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.02)


def start(phone: TestClient, record: str = "hero", language: str = "hi") -> dict:
    response = phone.post("/api/sessions", json={"params": {"record": record, "language": language}})
    assert response.status_code == 201, response.text
    return response.json()


def test_start_makes_the_missing_static_and_record_book_first_name_lines(state: Path) -> None:
    fake = Warmable()
    seed_static(fake, STATIC[::2])

    with app_on(fake, state) as phone:
        assert [text for text, _ in fake.tts_calls] == STATIC[1::2]
        for record_id in default_book().ids():
            assert all(fake.made(t) for t in first_name_lines(record_id))
        sid = start(phone)["session_id"]
        assert phone.get(f"/api/sessions/{sid}/audio/bot-000.wav").status_code == 200
        lines = phone.get(f"/api/sessions/{sid}").json()["events"][0]["lines"]

    assert lines and all(line["tts"]["cache_hit"] for line in lines)


def test_a_static_line_that_cannot_be_made_stops_the_start_and_is_named(state: Path) -> None:
    fake = Warmable()
    fake.fail_on = STATIC[3]

    with pytest.raises(prompts.PrewarmFailed) as refused, app_on(fake, state):
        pass

    assert [m.text for m in refused.value.missing] == [STATIC[3]]
    assert STATIC[3] in str(refused.value) and "ClientError" in str(refused.value)
    assert len(fake.tts_calls) == len(STATIC) - 1  # every other line was still tried


def test_no_prewarm_by_default_for_an_injected_client(state: Path) -> None:
    fake = Warmable()
    with TestClient(create_app(gnani=fake, state=state, settings=SETTINGS, web_dir=None)) as phone:
        opening = {line["text"] for line in start(phone)["bot"]["lines"]}
        time.sleep(0.2)
    # Only the opening's own reply job ran (it is not prewarming): no static or first-name line.
    assert {text for text, _ in fake.tts_calls} <= opening
    assert len(fake.tts_calls) <= len(opening)


def test_no_key_starts_with_a_warning(state: Path, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    def no_key(profile):
        raise ConfigError("GNANI_API_KEY is not set")

    monkeypatch.setattr(app_module, "live_client", no_key)
    monkeypatch.setattr(prompts, "offline_reader", lambda: Warmable())
    with TestClient(create_app(state=state, settings=SETTINGS, web_dir=None, prewarm=True)) as phone:
        assert phone.get("/api/health").json()["gnani_key_configured"] is False
    assert f"{len(STATIC)} static and first-name bot lines are not in the cache" in caplog.text


def test_a_session_makes_its_missing_first_name_lines_before_create_returns(state: Path) -> None:
    fake = Warmable()
    seed_static(fake, STATIC)
    with app_on(fake, state) as phone:
        names = first_name_lines("hero", Language.hi_en)  # hi-en is not prewarmed here
        assert names and not any(fake.made(t, HI_EN) for t in names)
        start(phone, language="hi-en")
        assert all(fake.made(t, HI_EN) for t in names)


def test_a_failing_first_name_line_does_not_fail_session_create(state: Path) -> None:
    fake = Warmable()
    seed_static(fake, STATIC)
    with app_on(fake, state) as phone:
        names = first_name_lines("hero", Language.hi_en)
        fake.fail_on = names[-1]
        phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi-en"}})
        assert all(fake.made(t, HI_EN) for t in names[:-1])


def test_nothing_is_synthesised_after_create_while_a_turn_could_be_in_progress(state: Path) -> None:
    fake = Warmable()
    seed_static(fake, STATIC)
    with app_on(fake, state) as phone:
        sid = start(phone, language="hi-en")["session_id"]
        made_at_create = len(fake.tts_calls)
        fake.stt_gate.clear()
        url = f"/api/sessions/{sid}/turns?source=file&reply_to=0&part=1"
        turn = threading.Thread(target=lambda: phone.post(url, content=make_wav(0.5)))
        turn.start()
        assert fake.stt_started.wait(5)
        time.sleep(0.4)
        # Only cache hits of the opening's own reply job may follow; no new line is made.
        after = fake.tts_calls[made_at_create:]
        opening = {line["text"] for line in phone.get(f"/api/sessions/{sid}").json()["events"][0]["lines"]}
        assert {text for text, _ in after} <= opening
        fake.stt_gate.set()
        turn.join(5)


# --- GnaniClient.tts_cached ------------------------------------------------------


def _client(state: Path, requests: list[httpx.Request]) -> GnaniClient:
    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=make_wav(0.2, 8000), headers={"content-type": "audio/wav"})

    return GnaniClient(
        api_key="test-key",
        credit_cap=10.0,
        state=state,
        http=httpx.Client(transport=httpx.MockTransport(answer)),
    )


def _ledger(state: Path) -> list[dict]:
    path = state / "ledger.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_tts_cached_agrees_with_tts_and_writes_no_ledger_row(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    client = _client(tmp_path, requests)

    assert client.tts_cached("नमस्ते", HI) is False
    assert _ledger(tmp_path) == [] and requests == []
    made = client.tts("नमस्ते", HI)
    rows = len(_ledger(tmp_path))
    assert made.call.cache_hit is False and client.tts_cached("नमस्ते", HI) is True
    assert len(_ledger(tmp_path)) == rows and len(requests) == 1
    assert client.tts("नमस्ते", HI).call.cache_hit is True
    assert client.tts_cached("नमस्ते", HI.model_copy(update={"sample_rate": 16000})) is False


def test_the_tts_cache_key_is_unchanged(tmp_path: Path) -> None:
    client = _client(tmp_path, [])
    body = {
        "text": "नमस्ते",
        "voice": HI.voice,
        "model": HI.model,
        "language": HI.language,
        "speed": HI.speed,
        "audio_config": {"sample_rate": HI.sample_rate, "container": HI.container},
    }
    old = cache_key(
        "gnani.tts.v1", {"base_url": "https://api.vachana.ai", "path": TTS_PATH, "body": body}, b""
    )
    assert client.tts("नमस्ते", HI).call.cache_key == old


def test_start_refuses_and_makes_nothing_when_missing_lines_cost_more_than_max_credits(
    state: Path,
) -> None:
    fake = Warmable()
    limited = SETTINGS.model_copy(
        update={"prewarm": SETTINGS.prewarm.model_copy(update={"max_credits": 0.5})}
    )

    app = create_app(gnani=fake, state=state, settings=limited, web_dir=None, prewarm=True)
    with pytest.raises(prompts.PrewarmOverBudget) as refused, TestClient(app):
        pass

    assert fake.tts_calls == []  # never silently skipped, never partly spent
    assert refused.value.est_credits > 0.5
    message = str(refused.value)
    assert (
        "max_credits = 0.5" in message and "uv run python -m samajh.server.prompts build --lang hi" in message
    )


def test_start_makes_the_lines_when_the_estimate_is_within_max_credits(state: Path) -> None:
    fake = Warmable()
    with TestClient(create_app(gnani=fake, state=state, settings=SETTINGS, web_dir=None, prewarm=True)):
        pass
    assert fake.made(STATIC[0])
