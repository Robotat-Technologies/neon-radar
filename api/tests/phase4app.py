"""An app for testing the Phase 4 router modules alone (PHASE-4.md M4.1, M4.2 and M4.5).

The routers and the hardening are mounted on a fresh FastAPI app with problem handlers like
PHASE-1.md M1.7d's (an `HTTPException` or a validation error becomes an RFC 9457 body), so these
tests depend on nothing but the modules they test. The repository's own app is tested by
`test_openapi_contract.py` and `test_routes.py` (Phases 1 and 2), which M4.1, M4.2 and M4.5 extend.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from neonradar_api.hardening import PROBLEM, harden, install_problem_openapi
from starlette.exceptions import HTTPException


def _problem(status: int, detail: str | None, headers: dict[str, str] | None) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": HTTPStatus(status).phrase}
    body["status"] = status
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type=PROBLEM, headers=headers)


def app_with(*routers: APIRouter, dev: bool = False, version: str = "1.2.0") -> FastAPI:
    app = FastAPI(
        title="NeonRadar API (test)", version=version, telemetry={"auto_configure": False}
    )

    @app.exception_handler(HTTPException)
    async def http_problem(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else None
        return _problem(exc.status_code, detail, dict(exc.headers or {}))

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(422, "The request is not valid.", None)

    for router in routers:
        app.include_router(router, prefix="/api/v1")
    harden(app, dev=dev)
    install_problem_openapi(app)
    return app
