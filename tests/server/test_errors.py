"""Every row of the error table, built the way the client raises them."""

from __future__ import annotations

from pathlib import Path

import pytest

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
from samajh.server.errors import ApiProblem, problem_from

KEY = "test-key-not-real"
LOCK = Path("/Users/someone/project/.samajh/gnani.lock")

ROWS: list[tuple[Exception, int, str, bool, int | None]] = [
    (AudioRejected("audio_too_large", "x"), 413, "audio_too_large", False, None),
    (AudioRejected("audio_unreadable", "x"), 422, "audio_unreadable", False, None),
    (AudioRejected("audio_too_long", "x"), 422, "audio_too_long", False, None),
    (AudioRejected("audio_too_short", "x"), 422, "audio_too_short", False, None),
    (AudioRejected("audio_decoder_failed", "x"), 500, "audio_decoder_failed", False, None),
    (
        InvalidRequest("clip is 31.00s; Prisma REST takes at most 30s"),
        422,
        "gnani_refused_locally",
        False,
        None,
    ),
    (LockTimeout(f"no lock on {LOCK} within 5s"), 503, "gnani_busy", True, None),
    (
        CapExceeded(unit="credits", cap=1000, spent=999.9, estimate=0.3),
        503,
        "credit_cap_reached",
        False,
        None,
    ),
    (
        RateLimited(status=429, code="RATE_LIMITED", message="Only 1 active request", attempts=2),
        503,
        "gnani_rate_limited",
        True,
        429,
    ),
    (
        ServerError(status=503, code=None, message="upstream down", attempts=2),
        502,
        "gnani_server_error",
        True,
        503,
    ),
    (TransportError("ConnectTimeout on all 2 attempts"), 504, "gnani_unreachable", True, None),
    (
        AuthError(status=401, code="INVALID_API_KEY", message="Unauthorized"),
        502,
        "gnani_auth_failed",
        False,
        401,
    ),
    (BadResponse("SttWire: body does not parse (at: transcript)"), 502, "gnani_bad_response", True, None),
    (
        ApiError(status=400, code="MODEL_UNSUPPORTED_LANGUAGE", message="not supported"),
        502,
        "gnani_rejected",
        False,
        400,
    ),
    (ConfigError("GNANI_API_KEY is not set (put it in .env)"), 500, "server_misconfigured", False, None),
]


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row[2])
def test_table_row(row: tuple[Exception, int, str, bool, int | None]) -> None:
    exc, status, code, retryable, upstream = row
    stage = "audio" if isinstance(exc, AudioRejected) else "stt"
    problem = problem_from(exc, stage)
    assert (problem.status, problem.stage, problem.code) == (status, stage, code)
    assert (problem.retryable, problem.upstream_status) == (retryable, upstream)
    assert problem.message
    assert set(problem.body()) == {"error"}
    assert set(problem.body()["error"]) == {"stage", "code", "message", "retryable", "upstream_status"}


def test_the_stage_is_the_callers() -> None:
    assert problem_from(TransportError("x"), "tts").stage == "tts"


def test_api_error_message_is_upstream_code_and_message() -> None:
    with_code = ApiError(status=400, code="MAX_AUDIO_DURATION_EXCEEDED", message="too long")
    assert problem_from(with_code, "stt").message == "MAX_AUDIO_DURATION_EXCEEDED: too long"
    assert (
        problem_from(ServerError(status=502, code=None, message="Bad Gateway"), "stt").message
        == "Bad Gateway"
    )


def test_a_dialogue_exception_shows_its_class_name_only() -> None:
    problem = problem_from(RuntimeError(f"secret {KEY} at {LOCK}"), "dialogue")
    assert (problem.status, problem.code, problem.message) == (500, "dialogue_failed", "RuntimeError")
    assert not problem.retryable
    # Even a client error raised inside a dialogue is the dialogue's failure.
    assert problem_from(TransportError("x"), "dialogue").code == "dialogue_failed"


def test_an_unexpected_exception_outside_the_dialogue_shows_its_class_name_only() -> None:
    problem = problem_from(KeyError(f"{KEY} {LOCK}"), "stt")
    assert (problem.status, problem.code, problem.message) == (500, "internal_error", "KeyError")


def test_no_message_carries_a_path_or_the_key() -> None:
    for exc, *_ in ROWS:
        message = problem_from(exc, "stt").message
        assert "/" not in message.replace("GNANI_CREDIT_CAP / defaults", "")
        assert ".samajh" not in message and KEY not in message and ".env" not in message


def test_a_problem_passes_through_unchanged() -> None:
    problem = ApiProblem(409, "session", "session_not_active", "x")
    assert problem_from(problem, "stt") is problem
