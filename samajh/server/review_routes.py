"""The review pages' API: thin routes over `samajh.ops`. The contract is in `samajh/ops/views.py`.

The store is read on every request (the files are small), so a rerun of the batch shows up
without a restart.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from samajh.ops import views
from samajh.ops.batch import Batch, load_batch
from samajh.ops.model import Draw
from samajh.ops.report import build_report
from samajh.ops.store import NoBatch, OpsStore


def review_router(state: Path) -> APIRouter:
    router = APIRouter(prefix="/api/review")
    store = OpsStore(state / "ops")

    def no_batch() -> HTTPException:
        return HTTPException(409, "no review batch yet: run `uv run python -m samajh.ops demo` first")

    def batch() -> Batch:
        try:
            return load_batch(store)
        except NoBatch:
            raise no_batch() from None

    def not_a_referral(case_id: str) -> HTTPException:
        return HTTPException(404, f"no referred case {case_id!r}")

    @router.get("/batch")
    def get_batch() -> views.BatchView:
        return views.batch_view(batch())

    @router.get("/queue")
    def get_queue() -> views.QueueView:
        return views.queue_view(batch())

    @router.get("/cases/{case_id}")
    def get_case(case_id: str) -> views.CaseView:
        try:
            return views.case_view(batch(), case_id)
        except views.NotAReferral:
            raise not_a_referral(case_id) from None

    @router.post("/cases/{case_id}/disposition")
    def post_disposition(case_id: str, body: views.DispositionIn) -> views.CaseView:
        try:
            return views.record_disposition(store, case_id, body, datetime.now(UTC))
        except NoBatch:
            raise no_batch() from None
        except views.NotAReferral:
            raise not_a_referral(case_id) from None

    @router.get("/attempts")
    def get_attempts() -> views.AttemptLogView:
        return views.attempt_log_view(batch())

    @router.get("/draws")
    def get_draws() -> list[Draw]:
        return list(batch().draws)

    @router.get("/report")
    def get_report() -> views.ReportView:
        try:
            return build_report(store, datetime.now(UTC))
        except NoBatch:
            raise no_batch() from None

    return router
