"""The review pages' API: thin routes over `samajh.ops`. The contract is in `samajh/ops/views.py`.

The store is read on every request (the files are small), so a rerun of the batch shows up
without a restart. Error messages never repeat what the client sent. There is no sign-in: this is
a demo, and the reviewer's name is free text (the pages say so).
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from samajh.ops import views
from samajh.ops.batch import Batch, load_batch
from samajh.ops.model import Draw
from samajh.ops.report import build_report
from samajh.ops.store import NoBatch, OpsStore

NO_BATCH = "no review batch yet: run `uv run python -m samajh.ops demo` first"
NOT_A_REFERRAL = "no referred case has that id"
BAD_DISPOSITION = (
    "a decision needs `decision` (one of the listed choices), `note` (1 to 2000 characters) "
    "and `reviewer` (1 to 80 characters)"
)


def review_router(state: Path) -> APIRouter:
    router = APIRouter(prefix="/api/review")
    store = OpsStore(state / "ops")
    sessions = state / "sessions"

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
    async def post_disposition(case_id: str, request: Request) -> views.CaseView:
        try:
            body = views.DispositionIn.model_validate_json(await request.body())
        except ValidationError:
            raise HTTPException(422, BAD_DISPOSITION) from None
        try:
            return views.record_disposition(store, case_id, body, datetime.now(UTC), sessions)
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
