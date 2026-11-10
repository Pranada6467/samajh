"""OpenRouter chat client with strict JSON-schema output validated into a caller's pydantic model.

Every call is cached by its exact request body, so the same request is never paid for twice.
Every HTTP attempt and every cache hit writes one ledger row. A USD cap per client instance stops
a run before it overspends.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from samajh.clients import _runtime
from samajh.clients._runtime import Attempt, Cache, Ledger, LedgerEntry, RetryPolicy
from samajh.clients.errors import BadResponse, CapExceeded, ConfigError, LlmOutputInvalid

T = TypeVar("T", bound=BaseModel)

_NAMESPACE = "openrouter.chat.v1"
_DEFAULT_RETRY = RetryPolicy()
_KEPT = frozenset({"type", "properties", "required", "additionalProperties", "items", "anyOf", "enum",
                   "const", "$ref", "$defs", "description"})
_DROPPED = frozenset({"title", "default"})
_FENCE = re.compile(r"\A\s*```[A-Za-z0-9_-]*[ \t]*\n(.*?)\n?[ \t]*```\s*\Z", re.DOTALL)


class Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str


class LlmResult(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)

    value: T
    model: str  # model id reported by the response
    prompt_tokens: int
    completion_tokens: int
    usd: float  # summed over all HTTP attempts of this call; 0.0 on a cache hit
    cache_hit: bool
    attempts: int  # output attempts (1 = first reply validated); 0 on a cache hit
    generation_id: str | None


class _Sampling(BaseModel):
    """`defaults.toml [llm.sampling]`: which sampling parameters each model is sent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    default: frozenset[Literal["temperature"]] = frozenset({"temperature"})
    by_model_prefix: dict[str, frozenset[Literal["temperature"]]] = {}

    def sent_to(self, model: str) -> frozenset[str]:
        matching = [prefix for prefix in self.by_model_prefix if model.startswith(prefix)]
        return self.by_model_prefix[max(matching, key=len)] if matching else self.default


def _load_sampling() -> _Sampling:
    try:
        return _Sampling.model_validate(_runtime.load_defaults().get("llm", {}).get("sampling", {}))
    except ValidationError as exc:
        raise ConfigError(f"defaults.toml [llm.sampling]: {_describe(exc)}") from None


# ---------------------------------------------------------------- response boundary


class _ErrorBody(BaseModel):
    code: int | str | None = None
    message: str = ""


class _ReplyMessage(BaseModel):
    content: str | None = None


class _Choice(BaseModel):
    message: _ReplyMessage | None = None
    finish_reason: str | None = None
    error: _ErrorBody | None = None


class _Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float | None = None


class _Reply(BaseModel):
    id: str | None = None
    model: str | None = None
    choices: list[_Choice] = []
    usage: _Usage | None = None
    error: _ErrorBody | None = None

    def body_error(self) -> _ErrorBody | None:
        """The error OpenRouter reports inside a 200 body, if any."""
        if self.error is not None and not self.choices:
            return self.error
        if self.choices and (self.choices[0].error is not None or self.choices[0].finish_reason == "error"):
            return self.choices[0].error or _ErrorBody()
        return None


def _parse_reply(body: bytes) -> _Reply | None:
    try:
        return _Reply.model_validate_json(body)
    except ValidationError:
        return None


def _error_status(error: _ErrorBody) -> int:
    # An in-body error with no usable HTTP code is an upstream failure: 502, which is retried.
    return error.code if isinstance(error.code, int) and 400 <= error.code <= 599 else 502


# ---------------------------------------------------------------- schema


def strict_json_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """The pydantic JSON schema of `schema`, made acceptable to strict structured output.

    Every object gets `additionalProperties: false` and all its properties in `required`; `title`
    and `default` are dropped. Raises `ConfigError` for anything that cannot be made strict: a
    non-object root, a free-form dict, or a keyword outside the portable subset (`pattern`,
    `minimum`, `minLength`, `allOf`, `format`, ...).
    """
    name = schema.__name__
    root = _strict(schema.model_json_schema(), name)
    if root.get("type") != "object":
        raise ConfigError(f"{name}: strict output needs an object at the root")
    return root


def _strict(node: Any, path: str) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ConfigError(f"{path}: not a schema object")
    unsupported = sorted(set(node) - _KEPT - _DROPPED)
    if unsupported:
        raise ConfigError(f"{path}: {', '.join(unsupported)} cannot be used with strict structured output")
    out = {k: v for k, v in node.items() if k in _KEPT}
    for key in ("properties", "$defs"):
        if key in out:
            out[key] = {name: _strict(sub, f"{path}.{name}") for name, sub in out[key].items()}
    if "items" in out:
        out["items"] = _strict(out["items"], f"{path}[]")
    if "anyOf" in out:
        out["anyOf"] = [_strict(sub, path) for sub in out["anyOf"]]
    if out.get("type") == "object":
        if "properties" not in out or out.get("additionalProperties") not in (None, False):
            raise ConfigError(f"{path}: an object with free-form keys cannot be made strict")
        out["additionalProperties"] = False
        out["required"] = list(out["properties"])
    return out


def _schema_name(schema: type[BaseModel]) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", schema.__name__)[:64] or "schema"


def _validate(schema: type[T], content: str) -> T:
    fenced = _FENCE.match(content)
    return schema.model_validate_json(fenced.group(1) if fenced else content)


def _describe(exc: ValidationError) -> str:
    lines = [f"{'.'.join(str(p) for p in e['loc']) or '(root)'}: {e['msg']}" for e in exc.errors()]
    return "; ".join(lines)[:1000]


# ---------------------------------------------------------------- client


class LlmClient:
    """Chat completions on OpenRouter with a strict JSON schema, cache, ledger and USD cap.

    The cap is per client instance: each instance starts at zero spent and knows nothing of other
    instances, processes or earlier runs. The ledger total (`Ledger.total_usd()`) is the only
    cross-run number, and nothing enforces a cap on it. Before every HTTP attempt the client
    refuses with `CapExceeded` when `spent >= usd_cap` or `spent + estimate > usd_cap`, where
    `estimate` is the largest single-attempt cost this instance has seen (0.0 before the first).
    The cost of an attempt is only known after it returns, so the worst overshoot is one call (one
    per thread when several threads call at once). A 200 reply without `usage.cost` is charged that
    same largest cost seen so far (0.0 if none yet) and its ledger row is flagged `cost_missing`,
    so that row's `usd` is an estimate. Cache hits cost nothing and are never refused.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        usd_cap: float,
        state: Path | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        http: httpx.Client | None = None,
        retry: RetryPolicy = _DEFAULT_RETRY,
        timeout: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        _runtime.check_api_key(api_key, "OpenRouter")
        if not model:
            raise ConfigError("LLM model id is empty")
        if not (math.isfinite(usd_cap) and usd_cap >= 0):
            raise ConfigError(f"usd_cap must be a finite number >= 0, got {usd_cap!r}")
        state = state if state is not None else _runtime.state_dir()
        self._api_key = api_key
        self._model = model
        self._usd_cap = usd_cap
        self._base_url = base_url.rstrip("/")
        self._url = self._base_url + "/chat/completions"
        self._http = http if http is not None else httpx.Client()
        self._retry = retry
        self._timeout = timeout
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()
        self._sampling = _load_sampling()
        self._cache = Cache(state / "cache" / "openrouter")
        self._ledger = Ledger(state / "ledger.jsonl")
        self._lock = threading.Lock()
        self._spent = 0.0
        self._largest = 0.0

    @classmethod
    def from_env(cls, **overrides: Any) -> LlmClient:
        """Key from `OPENROUTER_API_KEY`; model and cap from `SAMAJH_LLM_MODEL` / `SAMAJH_LLM_USD_CAP`,
        else from `defaults.toml [llm]`. `overrides` are passed to the constructor and win."""
        _runtime.load_env()
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ConfigError("OPENROUTER_API_KEY is not set")
        defaults = _runtime.load_defaults().get("llm", {})
        model = overrides.pop("model", None) or os.environ.get("SAMAJH_LLM_MODEL") or defaults.get("model")
        if not isinstance(model, str) or not model:
            raise ConfigError("no LLM model: set SAMAJH_LLM_MODEL or [llm].model in defaults.toml")
        raw_cap = overrides.pop("usd_cap", None)
        if raw_cap is None:
            raw_cap = os.environ.get("SAMAJH_LLM_USD_CAP") or defaults.get("usd_cap")
        try:
            usd_cap = float(raw_cap)
        except (TypeError, ValueError):
            raise ConfigError(f"LLM USD cap is not a number: {raw_cap!r}") from None
        return cls(api_key=api_key, model=model, usd_cap=usd_cap, **overrides)

    @property
    def spent_usd(self) -> float:
        with self._lock:
            return self._spent

    def complete(
        self,
        schema: type[T],
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float | None = 0.0,
        max_tokens: int = 1024,
        max_output_retries: int = 2,
    ) -> LlmResult[T]:
        """Return `schema` filled by the model, from the cache when this exact request was answered
        before. Raises `CapExceeded`, `LlmOutputInvalid`, `BadResponse` or an `ApiError`.

        `temperature` is sent only to a model that `defaults.toml [llm.sampling]` lists it for; for
        any other model it is left out of the request and of the cache key."""
        model = model or self._model
        original = [m.model_dump() for m in messages]
        body: dict[str, Any] = {
            "model": model,
            "messages": original,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": _schema_name(schema),
                    "strict": True,
                    "schema": strict_json_schema(schema),
                },
            },
            # Without this a provider that ignores response_format may be chosen.
            "provider": {"require_parameters": True},
        }
        if temperature is not None and "temperature" in self._sampling.sent_to(model):
            body["temperature"] = float(temperature)  # 0 and 0.0 must give one cache key
        key = _runtime.cache_key(_NAMESPACE, {"base_url": self._base_url, "body": body}, b"")

        started = time.monotonic()
        cached = self._from_cache(schema, key, model)
        if cached is not None:
            self._ledger.append(
                LedgerEntry(
                    ts=_now(), provider="openrouter", kind="chat", model=model, status="cache_hit", attempt=0,
                    seconds=time.monotonic() - started, cache_hit=True, cache_key=key,
                    prompt_tokens=cached.prompt_tokens, completion_tokens=cached.completion_tokens,
                )
            )
            return cached

        usd = 0.0

        def on_attempt(attempt: Attempt) -> None:
            nonlocal usd
            reply = _parse_reply(attempt.response.content) if attempt.response is not None else None
            usage = reply.usage if reply is not None else None
            cost = (usage.cost if usage is not None else None) or 0.0
            error_code = attempt.error_code
            missing = attempt.status == 200 and (usage is None or usage.cost is None)
            if missing:
                error_code = "cost_missing"
            with self._lock:
                if missing:
                    cost = self._largest
                self._spent += cost
                self._largest = max(self._largest, cost)
            usd += cost
            self._ledger.append(
                LedgerEntry(
                    ts=_now(), provider="openrouter", kind="chat", model=model, status=attempt.status,
                    attempt=attempt.number, seconds=attempt.seconds, cache_hit=False, cache_key=key, usd=cost,
                    prompt_tokens=usage.prompt_tokens if usage is not None else None,
                    completion_tokens=usage.completion_tokens if usage is not None else None,
                    error_code=error_code,
                )
            )

        last_error = ""
        for output_attempt in range(1, max_output_retries + 2):
            response = _runtime.send_with_retry(
                partial(self._send, body),
                policy=self._retry,
                parse_error=self._parse_error,
                on_attempt=on_attempt,
                sleep=self._sleep,
                rng=self._rng,
            )
            reply = _parse_reply(response.content)
            if reply is None or not reply.choices:
                raise BadResponse("OpenRouter answered 200 with a body that is not a chat completion")
            choice = reply.choices[0]
            content = choice.message.content if choice.message is not None else None
            if choice.finish_reason in ("length", "content_filter") or not content or not content.strip():
                reason = f"finish_reason={choice.finish_reason}" + ("" if content else ", empty content")
                raise LlmOutputInvalid(model=model, attempts=output_attempt, last_error=reason)
            try:
                value = _validate(schema, content)
            except ValidationError as exc:
                last_error = _describe(exc)
                feedback = (
                    "Your reply was not valid for the required JSON schema. Validation error: "
                    f"{last_error}\nReply with only the corrected JSON object."
                )
                body = {
                    **body,
                    "messages": [
                        *original,
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": feedback},
                    ],
                }
                continue
            usage = reply.usage or _Usage()
            result = LlmResult(
                value=value, model=reply.model or model, prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens, usd=usd, cache_hit=False, attempts=output_attempt,
                generation_id=reply.id,
            )
            self._cache.put(key, {"ns": _NAMESPACE, "model": result.model, "ts": _now()}, response.content)
            return result
        raise LlmOutputInvalid(model=model, attempts=max_output_retries + 1, last_error=last_error)

    def _from_cache(self, schema: type[T], key: str, model: str) -> LlmResult[T] | None:
        entry = self._cache.get(key)
        reply = _parse_reply(entry.body) if entry is not None else None
        if reply is None or not reply.choices or reply.choices[0].message is None:
            return None
        try:
            value = _validate(schema, reply.choices[0].message.content or "")
        except ValidationError:
            return None
        usage = reply.usage or _Usage()
        return LlmResult(
            value=value, model=reply.model or model, prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens, usd=0.0, cache_hit=True, attempts=0,
            generation_id=reply.id,
        )

    def _send(self, body: dict[str, Any]) -> httpx.Response:
        with self._lock:
            spent, estimate = self._spent, self._largest
        if spent >= self._usd_cap or spent + estimate > self._usd_cap:
            raise CapExceeded(unit="USD", cap=self._usd_cap, spent=spent, estimate=estimate)
        response = self._http.post(
            self._url,
            json=body,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
            follow_redirects=False,
        )
        if response.status_code == 200:
            reply = _parse_reply(response.content)
            error = reply.body_error() if reply is not None else None
            if error is not None:
                # OpenRouter reports some upstream failures inside a 200 body. Re-status the
                # response so the retry loop treats it exactly like that HTTP status.
                # Not the original headers: `content` is already decoded, and a content-encoding
                # header would make httpx decompress it a second time.
                retry_after = response.headers.get("retry-after")
                headers = {"retry-after": retry_after} if retry_after is not None else {}
                return httpx.Response(_error_status(error), content=response.content, headers=headers)
        return response

    def _parse_error(self, response: httpx.Response) -> tuple[str | None, str]:
        try:
            data = json.loads(response.content)
            error = data.get("error") or data["choices"][0].get("error") or {}
            code, message = error.get("code"), str(error.get("message") or "")
        except Exception:  # noqa: BLE001 - the retry loop requires that this never raises
            code, message = None, ""
        message = (message or f"HTTP {response.status_code}").replace(self._api_key, "[redacted]")[:300]
        return (str(code).replace(self._api_key, "[redacted]") if code is not None else None), message


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["LlmClient", "LlmResult", "Message", "strict_json_schema"]
