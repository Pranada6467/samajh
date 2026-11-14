"""The review pages' API: thin routes over `samajh.ops`. The contract is in `samajh/ops/views.py`.

The store is read on every request (the files are small), so a rerun of the batch shows up
without a restart. Error messages never repeat what the client sent (never the token).

Every route needs `Authorization: Bearer <token>`, a token made on the server by
`python -m samajh.ops reviewer add NAME` (samajh.ops.reviewers). The recorded reviewer is the
token's name. A decision must send back the `case_digest` the case was opened with: a case that
changed since gives 409. The recording route (`/api/sessions/<id>/recording.wav`, in app.py) is
not behind the token.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from samajh.ops import reviewers, views
from samajh.ops.batch import Batch, load_batch
from samajh.ops.model import Draw
from samajh.ops.report import build_report
from samajh.ops.store import NoBatch, OpsStore

NO_BATCH = "no review batch yet: run `uv run python -m samajh.ops demo` first"
NOT_A_REFERRAL = "no referred case has that id"
BAD_DISPOSITION = (
    "a decision needs `decision` (one of the listed choices), `note` (1 to 2000 characters) "
    "and `case_digest` (from the case as it was opened)"
)
NO_REVIEWERS = (
    "no reviewer is set up on this server: run `uv run python -m samajh.ops reviewer add NAME` "
    "there and sign in with the token it prints"
)
NOT_SIGNED_IN = (
    "sign in with a reviewer token (`Authorization: Bearer <token>`); a token is made on the server "
    "with `uv run python -m samajh.ops reviewer add NAME`"
)
CASE_CHANGED = "the case has changed since it was opened: reload it"
TOO_LARGE = "a decision is at most 16 KiB"
MAX_BODY = 16 * 1024


async def _bounded_body(request: Request) -> bytes:
    """The request body, refused with 413 past MAX_BODY, read in chunks so nothing unbounded is held."""
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_BODY:
                raise HTTPException(413, TOO_LARGE)
        except ValueError:
            raise HTTPException(400, "bad Content-Length") from None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            raise HTTPException(413, TOO_LARGE)
    return bytes(body)


def review_router(state: Path) -> APIRouter:
    store = OpsStore(state / "ops")
    sessions = state / "sessions"

    def signed_in(request: Request) -> str:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        offered = token.strip() if scheme.lower() == "bearer" else ""
        try:
            name = reviewers.who(store.root, offered) if offered else reviewers.who(store.root, "") and None
        except reviewers.NoReviewers:
            raise HTTPException(401, NO_REVIEWERS) from None
        if name is None:
            raise HTTPException(401, NOT_SIGNED_IN)
        return name

    router = APIRouter(prefix="/api/review", dependencies=[Depends(signed_in)])

    @router.get("/whoami")
    def whoami(name: str = Depends(signed_in)) -> dict[str, str]:
        return {"reviewer": name}

    def batch() -> Batch:
        try:
            return load_batch(store)
        except NoBatch:
            raise HTTPException(409, NO_BATCH) from None

    @router.get("/batch")
    def get_batch() -> views.BatchView:
        return views.batch_view(batch())

    @router.get("/queue")
    def get_queue() -> views.QueueView:
        return views.queue_view(batch())

    @router.get("/cases/{case_id}")
    def get_case(case_id: str) -> views.CaseView:
        try:
            return views.case_view(batch(), case_id, sessions)
        except views.NotAReferral:
            raise HTTPException(404, NOT_A_REFERRAL) from None

    @router.post("/cases/{case_id}/disposition")
    async def post_disposition(
        case_id: str, request: Request, name: str = Depends(signed_in)
    ) -> views.CaseView:
        raw = await _bounded_body(request)
        try:
            body = views.DispositionIn.model_validate_json(raw)
        except ValidationError:
            raise HTTPException(422, BAD_DISPOSITION) from None
        try:
            return views.record_disposition(
                store, case_id, body, datetime.now(UTC), sessions, reviewer=name, reviewer_auth="token"
            )
        except views.CaseChanged:
            raise HTTPException(409, CASE_CHANGED) from None
        except NoBatch:
            raise HTTPException(409, NO_BATCH) from None
        except views.NotAReferral:
            raise HTTPException(404, NOT_A_REFERRAL) from None

    @router.get("/attempts")
    def get_attempts() -> views.AttemptLogView:
        return views.attempt_log_view(batch())

    @router.get("/draws")
    def get_draws() -> list[Draw]:
        return list(batch().draws)

    @router.get("/report")
    def get_report() -> views.ReportView:
        try:
            return build_report(store)
        except NoBatch:
            raise HTTPException(409, NO_BATCH) from None

    return router
