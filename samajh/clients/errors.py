"""Typed errors raised by the API clients. No error message ever contains a key."""

from __future__ import annotations


class ClientError(Exception):
    """Base class for every error a client raises."""


class ConfigError(ClientError):
    """A required setting (API key, cap, model id) is missing or malformed."""


class InvalidRequest(ClientError):
    """The request breaks a known API limit (e.g. a clip over 30 s); refused before any network I/O."""


class LockTimeout(ClientError):
    """Could not get the single-flight lock in time: another process holds the key."""


class CapExceeded(ClientError):
    """The call was refused before any network I/O because it would cross the spend cap."""

    def __init__(self, *, unit: str, cap: float, spent: float, estimate: float) -> None:
        self.unit, self.cap, self.spent, self.estimate = unit, cap, spent, estimate
        super().__init__(f"refused: spent {spent:.4f} + estimated {estimate:.4f} {unit} would cross cap {cap:.4f}")


class TransportError(ClientError):
    """Network failure (timeout, connection reset) on every attempt."""


class BadResponse(ClientError):
    """The server answered 2xx but the body does not parse into the expected type."""


class ApiError(ClientError):
    """The server answered with an error status. `code` and `message` come from the error body."""

    def __init__(self, *, status: int, code: str | None, message: str, attempts: int = 1) -> None:
        self.status, self.code, self.message, self.attempts = status, code, message, attempts
        super().__init__(f"HTTP {status} {code or ''}: {message} (attempts={attempts})")


class AuthError(ApiError):
    """401 or 403: bad or missing key. Never retried."""


class RateLimited(ApiError):
    """Still 429 after the retry budget was spent."""


class ServerError(ApiError):
    """Still 5xx (or 408) after the retry budget was spent."""


class LlmOutputInvalid(ClientError):
    """The model's output failed schema validation on every attempt."""

    def __init__(self, *, model: str, attempts: int, last_error: str) -> None:
        self.model, self.attempts, self.last_error = model, attempts, last_error
        super().__init__(f"{model}: output invalid after {attempts} attempts: {last_error}")
