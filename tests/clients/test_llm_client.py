from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
import respx
from pydantic import BaseModel, ConfigDict, Field

from samajh.clients import _runtime
from samajh.clients._runtime import Ledger, RetryPolicy
from samajh.clients.errors import (
    ApiError,
    AuthError,
    CapExceeded,
    ConfigError,
    LlmOutputInvalid,
    ServerError,
)
from samajh.clients.llm import LlmClient, Message, strict_json_schema

FAKE_KEY = "sk-test-not-real"
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "test/model-a"


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["insurance", "other"]
    quote: str | None


class OtherAnswer(BaseModel):
    kind: Literal["insurance", "other"]


MESSAGES = [Message(role="system", content="Extract."), Message(role="user", content="बीमा था, 52,000 का")]
GOOD = '{"kind": "insurance", "quote": "52,000"}'


def completion(content: str | None, *, cost: float | None = 0.001, finish: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "gen-test-1",
            "model": MODEL,
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52, "cost": cost},
        },
    )


def api_error(status: int, message: str = "nope") -> httpx.Response:
    return httpx.Response(status, json={"error": {"code": status, "message": message, "metadata": {}}})


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def client(tmp_path: Path, sleeps: list[float]) -> LlmClient:
    return LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path, sleep=sleeps.append)


@pytest.fixture
def route():
    with respx.mock(assert_all_called=False) as router:
        yield router.post(URL)


def sent(route: respx.Route, index: int = -1) -> dict[str, Any]:
    return json.loads(route.calls[index].request.content)


def ledger_rows(state: Path) -> list[_runtime.LedgerEntry]:
    return list(Ledger(state / "ledger.jsonl").entries())


def test_valid_reply_is_parsed_and_returned(client: LlmClient, route: respx.Route) -> None:
    route.mock(return_value=completion(GOOD))
    result = client.complete(Answer, MESSAGES)

    assert result.value == Answer(kind="insurance", quote="52,000")
    assert (result.cache_hit, result.attempts, result.model, result.generation_id) == (False, 1, MODEL, "gen-test-1")
    assert (result.prompt_tokens, result.completion_tokens, result.usd) == (40, 12, 0.001)
    assert client.spent_usd == pytest.approx(0.001)

    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {FAKE_KEY}"
    assert "http-referer" not in request.headers and "x-title" not in request.headers
    body = sent(route)
    assert body["model"] == MODEL and body["temperature"] == 0.0 and body["max_tokens"] == 1024
    assert body["messages"] == [m.model_dump() for m in MESSAGES]
    assert body["provider"] == {"require_parameters": True}
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"] == {
        "name": "Answer",
        "strict": True,
        "schema": strict_json_schema(Answer),
    }


def test_temperature_none_is_omitted(client: LlmClient, route: respx.Route) -> None:
    route.mock(return_value=completion(GOOD))
    client.complete(Answer, MESSAGES, temperature=None)
    assert "temperature" not in sent(route)


def test_second_identical_call_is_a_cache_hit(client: LlmClient, route: respx.Route, tmp_path: Path) -> None:
    route.mock(return_value=completion(GOOD))
    first = client.complete(Answer, MESSAGES)
    second = client.complete(Answer, MESSAGES)

    assert route.call_count == 1
    assert second.cache_hit is True and second.usd == 0.0 and second.attempts == 0
    assert second.value == first.value and second.generation_id == first.generation_id
    assert client.spent_usd == pytest.approx(0.001)
    rows = ledger_rows(tmp_path)
    assert [(r.status, r.attempt, r.cache_hit, r.usd) for r in rows] == [
        (200, 1, False, 0.001),
        ("cache_hit", 0, True, 0.0),
    ]
    assert rows[0].cache_key == rows[1].cache_key


def test_cache_survives_a_new_client_instance(client: LlmClient, route: respx.Route, tmp_path: Path) -> None:
    route.mock(return_value=completion(GOOD))
    client.complete(Answer, MESSAGES)
    fresh = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path)
    assert fresh.complete(Answer, MESSAGES).cache_hit is True
    assert route.call_count == 1 and fresh.spent_usd == 0.0


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.complete(Answer, [*MESSAGES[:1], Message(role="user", content="बीमा था, 53,000 का")]),
        lambda c: c.complete(Answer, MESSAGES, model="test/model-b"),
        lambda c: c.complete(Answer, MESSAGES, temperature=0.7),
        lambda c: c.complete(Answer, MESSAGES, max_tokens=99),
        lambda c: c.complete(OtherAnswer, MESSAGES),
    ],
    ids=["message", "model", "temperature", "max_tokens", "schema"],
)
def test_any_changed_input_is_a_cache_miss(client: LlmClient, route: respx.Route, change) -> None:
    route.mock(return_value=completion(GOOD))
    client.complete(Answer, MESSAGES)
    assert change(client).cache_hit is False
    assert route.call_count == 2


def test_cached_reply_that_no_longer_validates_is_a_miss(client: LlmClient, route: respx.Route) -> None:
    class Shape(BaseModel):
        kind: str

    route.mock(return_value=completion('{"kind": "x"}'))
    client.complete(Shape, MESSAGES)

    # Same class name and same JSON schema, so the same cache key, but a stricter validator.
    class Shape(BaseModel):
        kind: str

        def model_post_init(self, _: Any) -> None:
            if self.kind == "x":
                raise ValueError("x is no longer allowed")

    route.mock(return_value=completion('{"kind": "y"}'))
    result = client.complete(Shape, MESSAGES)
    assert result.cache_hit is False and result.value.kind == "y" and route.call_count == 2


def test_invalid_then_valid_output_retries_with_feedback(client: LlmClient, route: respx.Route, tmp_path: Path) -> None:
    route.mock(side_effect=[completion("the answer is insurance"), completion(GOOD)])
    result = client.complete(Answer, MESSAGES)

    assert result.attempts == 2 and result.value.quote == "52,000"
    assert result.usd == pytest.approx(0.002) and client.spent_usd == pytest.approx(0.002)
    retry_messages = sent(route)["messages"]
    assert retry_messages[:2] == [m.model_dump() for m in MESSAGES]
    assert retry_messages[2] == {"role": "assistant", "content": "the answer is insurance"}
    assert retry_messages[3]["role"] == "user"
    assert "Invalid JSON" in retry_messages[3]["content"] and "only the corrected JSON" in retry_messages[3]["content"]
    assert len(ledger_rows(tmp_path)) == 2

    assert client.complete(Answer, MESSAGES).cache_hit is True
    assert route.call_count == 2


def test_schema_violation_feedback_names_the_field(client: LlmClient, route: respx.Route) -> None:
    route.mock(side_effect=[completion('{"kind": "loan", "quote": null}'), completion(GOOD)])
    assert client.complete(Answer, MESSAGES).attempts == 2
    assert "kind" in sent(route)["messages"][3]["content"]


def test_invalid_on_every_attempt_raises_and_caches_nothing(
    client: LlmClient, route: respx.Route, tmp_path: Path
) -> None:
    route.mock(return_value=completion("not json"))
    with pytest.raises(LlmOutputInvalid) as err:
        client.complete(Answer, MESSAGES, max_output_retries=2)

    assert err.value.attempts == 3 and err.value.model == MODEL and err.value.last_error
    assert route.call_count == 3
    assert client.spent_usd == pytest.approx(0.003)
    assert not list((tmp_path / "cache").rglob("*.bin"))

    route.mock(return_value=completion(GOOD))
    assert client.complete(Answer, MESSAGES).cache_hit is False


def test_code_fence_around_json_is_stripped(client: LlmClient, route: respx.Route) -> None:
    route.mock(return_value=completion(f"```json\n{GOOD}\n```"))
    result = client.complete(Answer, MESSAGES)
    assert result.attempts == 1 and result.value.kind == "insurance"


def test_429_then_200_is_retried_with_one_sleep(client: LlmClient, route: respx.Route, sleeps: list[float]) -> None:
    route.mock(side_effect=[api_error(429, "slow down"), completion(GOOD)])
    result = client.complete(Answer, MESSAGES)
    assert result.attempts == 1 and route.call_count == 2 and len(sleeps) == 1


def test_500_on_every_attempt_raises_server_error(tmp_path: Path, route: respx.Route, sleeps: list[float]) -> None:
    client = LlmClient(
        api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path, sleep=sleeps.append,
        retry=RetryPolicy(max_attempts=3),
    )
    route.mock(return_value=api_error(500, "boom"))
    with pytest.raises(ServerError) as err:
        client.complete(Answer, MESSAGES)
    assert err.value.attempts == 3 and route.call_count == 3 and len(sleeps) == 2
    assert [r.status for r in ledger_rows(tmp_path)] == [500, 500, 500]


def test_401_raises_auth_error_after_one_request(client: LlmClient, route: respx.Route, sleeps: list[float]) -> None:
    route.mock(return_value=api_error(401, "User not found."))
    with pytest.raises(AuthError) as err:
        client.complete(Answer, MESSAGES)
    assert route.call_count == 1 and sleeps == []
    assert err.value.code == "401" and err.value.message == "User not found."


def test_402_is_not_retried(client: LlmClient, route: respx.Route, sleeps: list[float]) -> None:
    route.mock(return_value=api_error(402, "Insufficient credits"))
    with pytest.raises(ApiError) as err:
        client.complete(Answer, MESSAGES)
    assert err.value.status == 402 and route.call_count == 1 and sleeps == []


def test_error_inside_a_200_body_is_retried(
    client: LlmClient, route: respx.Route, sleeps: list[float], tmp_path: Path
) -> None:
    in_body = httpx.Response(200, json={"error": {"code": 502, "message": "upstream died", "metadata": {}}})
    route.mock(side_effect=[in_body, completion(GOOD)])
    result = client.complete(Answer, MESSAGES)
    assert result.value.kind == "insurance" and route.call_count == 2 and len(sleeps) == 1
    assert [(r.status, r.error_code) for r in ledger_rows(tmp_path)] == [(502, "502"), (200, None)]


def test_choice_level_error_with_non_retryable_code_raises(client: LlmClient, route: respx.Route) -> None:
    body = {"choices": [{"finish_reason": "error", "error": {"code": 400, "message": "bad schema"}}]}
    route.mock(return_value=httpx.Response(200, json=body))
    with pytest.raises(ApiError) as err:
        client.complete(Answer, MESSAGES)
    assert err.value.status == 400 and err.value.message == "bad schema" and route.call_count == 1


@pytest.mark.parametrize("raw", [b"<html>bad gateway</html>", b"[]", b'{"choices": "no"}', b"{}"])
def test_unparseable_200_body_is_bad_response(client: LlmClient, route: respx.Route, raw: bytes) -> None:
    from samajh.clients.errors import BadResponse

    route.mock(return_value=httpx.Response(200, content=raw))
    with pytest.raises(BadResponse):
        client.complete(Answer, MESSAGES)
    assert route.call_count == 1


def test_non_json_error_body_does_not_break_error_handling(client: LlmClient, route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(404, content=b"<html>not found</html>"))
    with pytest.raises(ApiError) as err:
        client.complete(Answer, MESSAGES)
    assert err.value.status == 404 and err.value.code is None


@pytest.mark.parametrize(
    "reply",
    [completion('{"kind": "insu', finish="length"), completion(GOOD, finish="content_filter"), completion(None),
     completion("  ")],
    ids=["length", "content_filter", "null-content", "blank-content"],
)
def test_unfixable_output_raises_after_one_request(client: LlmClient, route: respx.Route, reply: httpx.Response) -> None:
    route.mock(return_value=reply)
    with pytest.raises(LlmOutputInvalid) as err:
        client.complete(Answer, MESSAGES)
    assert err.value.attempts == 1 and route.call_count == 1


def test_cap_refuses_before_sending_but_cached_requests_still_return(
    tmp_path: Path, route: respx.Route
) -> None:
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=0.005, state=tmp_path)
    route.mock(return_value=completion(GOOD, cost=0.01))
    client.complete(Answer, MESSAGES)
    assert client.spent_usd == pytest.approx(0.01)

    with pytest.raises(CapExceeded) as err:
        client.complete(Answer, MESSAGES, temperature=0.5)
    assert (err.value.unit, err.value.cap) == ("USD", 0.005)
    assert err.value.spent == pytest.approx(0.01) and err.value.estimate == pytest.approx(0.01)
    assert route.call_count == 1

    assert client.complete(Answer, MESSAGES).cache_hit is True
    assert route.call_count == 1 and len(ledger_rows(tmp_path)) == 2


def test_cap_uses_the_largest_attempt_cost_as_the_estimate(tmp_path: Path, route: respx.Route) -> None:
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=0.015, state=tmp_path)
    route.mock(return_value=completion(GOOD, cost=0.01))
    client.complete(Answer, MESSAGES)
    with pytest.raises(CapExceeded):  # 0.01 spent + 0.01 estimated > 0.015, though 0.01 < cap
        client.complete(Answer, MESSAGES, temperature=0.5)
    assert route.call_count == 1


def test_cap_stops_output_retries_mid_call(tmp_path: Path, route: respx.Route) -> None:
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=0.005, state=tmp_path)
    route.mock(return_value=completion("not json", cost=0.01))
    with pytest.raises(CapExceeded):
        client.complete(Answer, MESSAGES)
    assert route.call_count == 1


@pytest.mark.parametrize("usage", [{"prompt_tokens": 5, "completion_tokens": 3, "cost": None},
                                   {"prompt_tokens": 5, "completion_tokens": 3}])
def test_missing_cost_is_recorded_as_zero_and_flagged(
    client: LlmClient, route: respx.Route, tmp_path: Path, usage: dict[str, Any]
) -> None:
    body = {"id": "gen-x", "model": MODEL, "usage": usage,
            "choices": [{"message": {"content": GOOD}, "finish_reason": "stop"}]}
    route.mock(return_value=httpx.Response(200, json=body))
    result = client.complete(Answer, MESSAGES)
    assert result.usd == 0.0
    (row,) = ledger_rows(tmp_path)
    assert (row.usd, row.error_code, row.prompt_tokens, row.completion_tokens) == (0.0, "cost_missing", 5, 3)


def test_ledger_rows_carry_tokens_and_usd(client: LlmClient, route: respx.Route, tmp_path: Path) -> None:
    route.mock(side_effect=[api_error(503), completion(GOOD, cost=0.0042)])
    client.complete(Answer, MESSAGES)
    failed, ok = ledger_rows(tmp_path)
    assert (failed.status, failed.attempt, failed.usd, failed.prompt_tokens) == (503, 1, 0.0, None)
    assert (ok.provider, ok.kind, ok.model, ok.status, ok.attempt) == ("openrouter", "chat", MODEL, 200, 2)
    assert (ok.prompt_tokens, ok.completion_tokens, ok.usd, ok.cache_hit) == (40, 12, 0.0042, False)
    assert Ledger(tmp_path / "ledger.jsonl").total_usd() == pytest.approx(0.0042)


def test_api_key_never_reaches_disk_or_exception_messages(
    client: LlmClient, route: respx.Route, tmp_path: Path
) -> None:
    messages: list[str] = []
    route.mock(side_effect=[completion(GOOD), completion(GOOD)])
    client.complete(Answer, MESSAGES)
    client.complete(Answer, MESSAGES)
    for reply in [
        api_error(401, f"bad key {FAKE_KEY}"),
        api_error(402, f"no credits for {FAKE_KEY}"),
        httpx.ConnectError(f"cannot reach host with {FAKE_KEY}"),
        completion("not json"),
        completion(None),
    ]:
        route.mock(side_effect=[reply] * 10)
        with pytest.raises(Exception) as err:
            client.complete(Answer, [Message(role="user", content=f"case {len(messages)}")])
        messages.append(str(err.value) + repr(err.value))

    assert not any(FAKE_KEY in m for m in messages)
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert len(files) >= 3
    assert not any(FAKE_KEY.encode() in p.read_bytes() for p in files)


# ---------------------------------------------------------------- strict_json_schema


class Channel(str, Enum):
    branch = "branch"
    agent = "agent"


class Rider(BaseModel):
    name: str
    premium_quote: str | None = None


class Policy(BaseModel):
    kind: Literal["insurance", "fixed_deposit"]
    channel: Channel = Channel.branch
    riders: list[Rider] = []
    nominee: Rider | None = None
    title: str = "x"


def test_strict_json_schema_on_nested_optional_list_enum() -> None:
    schema = strict_json_schema(Policy)

    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert schema["required"] == ["kind", "channel", "riders", "nominee", "title"]
    assert schema["properties"]["kind"]["enum"] == ["insurance", "fixed_deposit"]
    assert schema["properties"]["title"] == {"type": "string"}  # a field named like a dropped keyword survives
    assert schema["properties"]["riders"]["items"] == {"$ref": "#/$defs/Rider"}
    assert {"type": "null"} in schema["properties"]["nominee"]["anyOf"]
    rider = schema["$defs"]["Rider"]
    assert rider["additionalProperties"] is False and rider["required"] == ["name", "premium_quote"]
    assert rider["properties"]["premium_quote"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    assert schema["$defs"]["Channel"] == {"enum": ["branch", "agent"], "type": "string"}

    def keys(node: Any) -> set[str]:
        if isinstance(node, dict):
            return set(node) | {k for v in node.values() for k in keys(v)}
        if isinstance(node, list):
            return {k for v in node for k in keys(v)}
        return set()

    assert "default" not in keys(schema)


def test_strict_json_schema_rejects_what_cannot_be_strict() -> None:
    class Bounded(BaseModel):
        n: int = Field(ge=0)

    class Patterned(BaseModel):
        s: str = Field(pattern="^a")

    class FreeForm(BaseModel):
        extra: dict[str, int]

    for bad in (Bounded, Patterned, FreeForm):
        with pytest.raises(ConfigError):
            strict_json_schema(bad)


def test_schema_name_is_sanitised(client: LlmClient, route: respx.Route) -> None:
    Odd = type("Ödd Name!" + "x" * 80, (Answer,), {})
    route.mock(return_value=completion(GOOD))
    client.complete(Odd, MESSAGES)
    name = sent(route)["response_format"]["json_schema"]["name"]
    assert len(name) == 64 and name.startswith("_dd_Name_x")


# ---------------------------------------------------------------- from_env


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    monkeypatch.setattr(_runtime, "load_env", lambda: None)
    for name in ("OPENROUTER_API_KEY", "SAMAJH_LLM_MODEL", "SAMAJH_LLM_USD_CAP"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path))
    return monkeypatch


def test_from_env_without_key_raises_config_error(clean_env: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError):
        LlmClient.from_env()


def test_from_env_reads_model_and_cap_from_env(
    clean_env: pytest.MonkeyPatch, route: respx.Route, tmp_path: Path
) -> None:
    clean_env.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    clean_env.setenv("SAMAJH_LLM_MODEL", "test/from-env")
    clean_env.setenv("SAMAJH_LLM_USD_CAP", "0.005")
    client = LlmClient.from_env()
    route.mock(return_value=completion(GOOD, cost=0.01))
    client.complete(Answer, MESSAGES)

    assert sent(route)["model"] == "test/from-env"
    assert (tmp_path / "ledger.jsonl").exists() and (tmp_path / "cache" / "openrouter").is_dir()
    with pytest.raises(CapExceeded):
        client.complete(Answer, MESSAGES, temperature=0.3)


def test_from_env_falls_back_to_defaults_toml(clean_env: pytest.MonkeyPatch, route: respx.Route) -> None:
    clean_env.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    defaults = _runtime.load_defaults()["llm"]
    route.mock(return_value=completion(GOOD))
    LlmClient.from_env().complete(Answer, MESSAGES)
    assert sent(route)["model"] == defaults["model"] and defaults["usd_cap"] == 1.0


def test_from_env_rejects_a_malformed_cap(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    clean_env.setenv("SAMAJH_LLM_USD_CAP", "lots")
    with pytest.raises(ConfigError):
        LlmClient.from_env()


# ---------------------------------------------------------------- review fixes


def test_error_inside_a_gzip_200_body_is_retried_and_its_cost_counted(
    client: LlmClient, route: respx.Route, tmp_path: Path
) -> None:
    import gzip

    body = json.dumps({"error": {"code": 502, "message": "upstream died"}, "usage": {"cost": 0.0007}})
    in_body = httpx.Response(200, content=gzip.compress(body.encode()), headers={"content-encoding": "gzip"})
    route.mock(side_effect=[in_body, completion(GOOD)])
    result = client.complete(Answer, MESSAGES)
    assert result.value.kind == "insurance" and route.call_count == 2
    first, second = ledger_rows(tmp_path)
    assert (first.status, first.usd, second.status) == (502, 0.0007, 200)
    assert result.usd == pytest.approx(0.0017)


def slices(key: str, n: int = 12) -> list[str]:
    return [key[i : i + n] for i in range(len(key) - n + 1)]


def test_key_echoed_in_the_error_code_is_redacted(client: LlmClient, route: respx.Route, tmp_path: Path) -> None:
    echo = {"error": {"code": f"bad_key_{FAKE_KEY}", "message": "x" * 290 + FAKE_KEY}}
    route.mock(return_value=httpx.Response(400, json=echo))
    with pytest.raises(ApiError) as err:
        client.complete(Answer, MESSAGES)
    text = str(err.value) + repr(err.value) + str(err.value.code) + err.value.message
    assert not any(part in text for part in slices(FAKE_KEY))
    for path in (p for p in tmp_path.rglob("*") if p.is_file()):
        assert not any(part.encode() in path.read_bytes() for part in slices(FAKE_KEY)), path


@pytest.mark.parametrize("bad", ["", " ", FAKE_KEY + "\n", " " + FAKE_KEY, "sk test", "sk\ttest", "sk-\x00x", "sk-क"])
def test_malformed_key_is_refused_without_showing_it(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ConfigError) as err:
        LlmClient(api_key=bad, model=MODEL, usd_cap=1.0, state=tmp_path)
    assert not bad.strip() or bad.strip() not in str(err.value)


def test_from_env_strips_the_key(clean_env: pytest.MonkeyPatch, route: respx.Route) -> None:
    clean_env.setenv("OPENROUTER_API_KEY", f" {FAKE_KEY}\n")
    route.mock(return_value=completion(GOOD))
    LlmClient.from_env().complete(Answer, MESSAGES)
    assert route.calls.last.request.headers["authorization"] == f"Bearer {FAKE_KEY}"
    clean_env.setenv("OPENROUTER_API_KEY", " \n")
    with pytest.raises(ConfigError):
        LlmClient.from_env()


def test_a_redirect_is_not_followed_even_by_an_injected_client(tmp_path: Path) -> None:
    http = httpx.Client(follow_redirects=True)
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path, http=http)
    with respx.mock(assert_all_called=False) as router:
        router.post(URL).respond(307, headers={"location": "https://elsewhere.example/chat"})
        other = router.route(host="elsewhere.example").respond(json={})
        with pytest.raises(ApiError) as err:
            client.complete(Answer, MESSAGES)
    assert err.value.status == 307 and other.call_count == 0


def test_temperature_0_and_0_0_share_a_cache_entry(client: LlmClient, route: respx.Route) -> None:
    route.mock(return_value=completion(GOOD))
    client.complete(Answer, MESSAGES, temperature=0)
    assert client.complete(Answer, MESSAGES, temperature=0.0).cache_hit is True
    assert route.call_count == 1


def test_cache_key_covers_the_base_url(tmp_path: Path) -> None:
    other_url = "http://mock.invalid/v1"
    with respx.mock(assert_all_called=False) as router:
        real = router.post(URL).mock(return_value=completion(GOOD))
        mock = router.post(f"{other_url}/chat/completions").mock(return_value=completion(GOOD))
        LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path, base_url=other_url).complete(
            Answer, MESSAGES
        )
        result = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path).complete(Answer, MESSAGES)
    assert result.cache_hit is False and (real.call_count, mock.call_count) == (1, 1)
    assert "base_url" not in json.loads(real.calls.last.request.content)


def test_cap_of_zero_sends_nothing(tmp_path: Path, route: respx.Route) -> None:
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=0.0, state=tmp_path)
    route.mock(return_value=completion(GOOD))
    with pytest.raises(CapExceeded):
        client.complete(Answer, MESSAGES)
    assert route.call_count == 0


def test_missing_cost_is_charged_the_largest_cost_seen(tmp_path: Path, route: respx.Route) -> None:
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=0.025, state=tmp_path)
    route.mock(side_effect=[completion(GOOD, cost=0.01), completion(GOOD, cost=None), completion(GOOD)])
    client.complete(Answer, MESSAGES)
    second = client.complete(Answer, MESSAGES, temperature=0.5)
    assert second.usd == pytest.approx(0.01) and client.spent_usd == pytest.approx(0.02)
    row = ledger_rows(tmp_path)[-1]
    assert (row.usd, row.error_code) == (0.01, "cost_missing")
    with pytest.raises(CapExceeded):  # 0.02 spent + 0.01 estimated > 0.025
        client.complete(Answer, MESSAGES, temperature=0.6)
    assert route.call_count == 2
