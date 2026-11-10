"""The one table that maps a failure to what the phone sees."""

from __future__ import annotations

from typing import Literal

from samajh.clients.errors import (
    ApiError,
    AuthError,
    BadResponse,
    CapExceeded,
    ConfigError,
    InvalidRequest,
    LockTimeout,
    RateLimited,
    ServerError,
    TransportError,
)
from samajh.server.audio import AudioRejected

Stage = Literal["request", "session", "audio", "stt", "tts", "dialogue"]


class ApiProblem(Exception):
    def __init__(
        self,
        status: int,
        stage: Stage,
        code: str,
        message: str,
        retryable: bool = False,
        upstream_status: int | None = None,
    ) -> None:
        self.status, self.stage, self.code, self.message = status, stage, code, message
        self.retryable, self.upstream_status = retryable, upstream_status
        super().__init__(f"{status} {stage} {code}: {message}")

    def body(self) -> dict[str, object]:
        return {
            "error": {
                "stage": self.stage,
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "upstream_status": self.upstream_status,
            }
        }


_AUDIO_STATUS = {
    "audio_too_large": 413,
    "audio_unreadable": 422,
    "audio_too_long": 422,
    "audio_too_short": 422,
    "audio_decoder_failed": 500,
}
# First match wins, so subclasses come before ApiError. (class, status, code, retryable, fixed message)
_CLIENT: tuple[tuple[type[Exception], int, str, bool, str | None], ...] = (
    (InvalidRequest, 422, "gnani_refused_locally", False, None),
    # The client's own message names the lock file, and a path must not reach the phone.
    (LockTimeout, 503, "gnani_busy", True, "another Gnani request is holding the key; try again"),
    (CapExceeded, 503, "credit_cap_reached", False, None),
    (RateLimited, 503, "gnani_rate_limited", True, None),
    (ServerError, 502, "gnani_server_error", True, None),
    (TransportError, 504, "gnani_unreachable", True, None),
    (AuthError, 502, "gnani_auth_failed", False, None),
    (BadResponse, 502, "gnani_bad_response", True, None),
    (ApiError, 502, "gnani_rejected", False, None),
    (ConfigError, 500, "server_misconfigured", False, "the server's Gnani settings are missing or invalid"),
)


def problem_from(exc: Exception, stage: Stage) -> ApiProblem:
    if isinstance(exc, ApiProblem):
        return exc
    if isinstance(exc, AudioRejected):
        return ApiProblem(_AUDIO_STATUS[exc.code], "audio", exc.code, exc.message)
    if stage != "dialogue":
        for kind, status, code, retryable, fixed in _CLIENT:
            if not isinstance(exc, kind):
                continue
            if isinstance(exc, ApiError):
                message = f"{exc.code}: {exc.message}" if exc.code else exc.message
                return ApiProblem(status, stage, code, message, retryable, exc.status)
            return ApiProblem(status, stage, code, fixed or str(exc), retryable)
    # Only the class name: an arbitrary exception's text can hold anything.
    code = "dialogue_failed" if stage == "dialogue" else "internal_error"
    return ApiProblem(500, stage, code, type(exc).__name__)
