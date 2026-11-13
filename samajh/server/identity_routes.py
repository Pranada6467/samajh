"""The identity setting's routes for the phone's demo page (P8 contract section 7).

    GET /api/identity/menu                         the options a lender may set, each with `describe`
    GET /api/identity/notice?record=ID&lang=hi     the prior notice for that record's lender (mocked)
    GET /api/identity/notice?loan=ID&lang=hi       the same for a loan of the loan book

Neither route reads or returns anything of the record but the lender's name: no expected answer, no
borrower name. Error messages never repeat what the client sent.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from samajh.identity import MENU, CheckKind, IdentityPolicy, describe
from samajh.identity.notice import render_notice
from samajh.server.errors import ApiProblem
from samajh.server.loanbook import LoanBook, LoanRefused, resolve_record
from samajh.server.records import RecordBook
from samajh.server.settings import Settings
from samajh.types import Language

_LABELS = {"none": "No second check", CheckKind.year_of_birth.value: "Year of birth"}
ATTEMPTS = (1, 2)


def _policy(option: str, attempts: int, default: IdentityPolicy) -> IdentityPolicy:
    second = None if option == "none" else CheckKind(option)
    return default.model_copy(update={"second_check": second, "attempts": attempts if second else 1})


def menu(settings: Settings) -> dict[str, Any]:
    """Every option with the description of each attempt count it allows, and the server's default."""
    default = settings.identity
    options = []
    for option in MENU:
        counts = ATTEMPTS if option != "none" else (1,)
        options.append(
            {
                "id": option,
                "label": _LABELS.get(option, option),
                "attempts": list(counts),
                "descriptions": {str(n): describe(_policy(option, n, default)) for n in counts},
            }
        )
    return {
        "options": options,
        "default": {
            **default.model_dump(mode="json"),
            "second_check": default.second_check.value if default.second_check else "none",
            "description": describe(default),
        },
    }


def identity_router(settings: Settings, records: RecordBook | None, loans: LoanBook | None) -> APIRouter:
    router = APIRouter(prefix="/api/identity")

    @router.get("/menu")
    def get_menu() -> dict[str, Any]:
        return menu(settings)

    @router.get("/notice")
    def get_notice(request: Request) -> dict[str, Any]:
        query = request.query_params
        unknown = set(query) - {"record", "loan", "lang"}
        if unknown or ("record" in query) == ("loan" in query):
            raise ApiProblem(422, "request", "invalid_params", "name a record or a loan, and lang")
        try:
            language = Language(query.get("lang", ""))
        except ValueError:
            raise ApiProblem(422, "request", "invalid_language", "lang must be hi, hi-en, ta or kn") from None
        params = {key: query[key] for key in ("record", "loan") if key in query}
        try:
            if "loan" in params:  # the link a call on the loan would get; nothing is written
                if loans is None:
                    raise ValueError("no loan book")
                params |= loans.open_call(params["loan"]).params()
            record, _ = resolve_record(params, records, loans)
        except LoanRefused as refused:
            raise ApiProblem(refused.status, "request", refused.code, refused.message) from None
        except ValueError:
            raise ApiProblem(404, "request", "not_found", "no record or loan has that id") from None
        notice = render_notice(record.lender_name, language)
        return {
            **notice.model_dump(mode="json"),
            "shown": settings.identity.prior_notice,
            "label": "SMS, mocked: not sent",
        }

    return router
