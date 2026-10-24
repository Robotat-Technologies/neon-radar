"""RFC 9457 problem details for every error the API returns (C3, contracts/C3-api.md).

Every error is `application/problem+json` with `type` `about:blank`, `title` the HTTP reason
phrase, `detail` a sentence for people and `instance` the request path. Validation errors list
`<location>: <message>` pairs in `detail` without echoing the input (pydantic's `input` and
`ctx` never reach a response). An exception no handler takes is `hardening.Contain`'s fixed 500
problem (PHASE-4.md M4.1). Log lines name the route template, never the request path, which can
hold an entity id (G15). The real-data app (`api serve --real`, PHASE-2.md G9) passes `report`:
`Reported`, inside `Contain`, hands such an exception to it, and `report` keeps its traceback in
the redacted log.
"""

import logging
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Any, Final, NoReturn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from neonradar_api.files import RepoRootNotFound
from neonradar_api.graph import GraphUnavailable
from neonradar_api.hardening import route_template
from neonradar_contracts.api import Problem
from neonradar_graph.ownership import QueryTimeout, UnknownId

logger = logging.getLogger(__name__)

MEDIA_TYPE: Final = "application/problem+json"
PROBLEM_REF: Final = "#/components/schemas/Problem"


NOT_FOUND: Final = "No entity has this id."


class ProblemError(Exception):
    """Raise in a route to answer with a problem (404, 501, ...)."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def not_implemented(request: Request, arrives_in: str) -> NoReturn:
    """Answer 501, naming the milestone or phase that implements the route."""
    route = getattr(request.scope.get("route"), "path", request.url.path)
    raise ProblemError(
        501, f"{request.method} {route} is not implemented yet: it arrives in {arrives_in}."
    )


def responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI entries: each status answers with a Problem, as application/problem+json only."""
    return {
        status: {
            "description": HTTPStatus(status).phrase,
            "content": {MEDIA_TYPE: {"schema": {"$ref": PROBLEM_REF}}},
        }
        for status in statuses
    }


def problem_response(
    request: Request, status: int, detail: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    problem = Problem(
        type="about:blank",
        title=HTTPStatus(status).phrase,
        status=status,
        detail=detail,
        instance=request.url.path,
    )
    return JSONResponse(
        problem.model_dump(), status_code=status, media_type=MEDIA_TYPE, headers=headers
    )


def _validation_detail(error: RequestValidationError) -> str:
    """`<location>: <message>` per failed check. Never echoes input: an unknown body key is
    reported at its parent, because the key itself is the caller's text."""
    parts: list[str] = []
    for item in error.errors():
        location = [str(part) for part in item.get("loc", ())]
        message = item.get("msg", "invalid value")
        if item.get("type") == "extra_forbidden":
            location, message = location[:-1], "unknown keys are not permitted"
        part = f"{'.'.join(location)}: {message}"
        if part not in parts:
            parts.append(part)
    return "; ".join(parts) or "The request is not valid."


class Reported:
    """The real-data app's innermost layer: an exception no handler took goes to `report`, which
    keeps its traceback in the redacted log, then on to `hardening.Contain`, which answers the
    fixed 500 problem and logs only the class and the route template."""

    def __init__(self, app: ASGIApp, report: Callable[[Exception], None]) -> None:
        self.app = app
        self.report = report

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception as error:
            self.report(error)
            raise


def install(app: FastAPI, report: Callable[[Exception], None] | None = None) -> None:
    """Answer every error with a problem. Call it before `hardening.harden`, so that `Reported`
    (real data only) sits inside `Contain`."""
    if report is not None:
        app.add_middleware(Reported, report=report)

    @app.exception_handler(ProblemError)
    async def on_problem(request: Request, error: ProblemError) -> JSONResponse:
        return problem_response(request, error.status, error.detail)

    @app.exception_handler(HTTPException)
    async def on_http(request: Request, error: HTTPException) -> JSONResponse:
        detail = str(error.detail)
        if error.status_code == 404 and detail == HTTPStatus.NOT_FOUND.phrase:
            detail = f"No route matches {request.method} {request.url.path}."
        elif error.status_code == 405:
            detail = (
                f"{request.method} is not allowed on {request.url.path}; "
                "the Allow header lists the methods it accepts."
            )
        return problem_response(request, error.status_code, detail, error.headers)

    @app.exception_handler(RequestValidationError)
    async def on_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        return problem_response(request, 422, _validation_detail(error))

    @app.exception_handler(UnknownId)
    async def on_unknown(request: Request, error: UnknownId) -> JSONResponse:
        return problem_response(request, 404, NOT_FOUND)

    @app.exception_handler(QueryTimeout)
    async def on_timeout(request: Request, error: QueryTimeout) -> JSONResponse:
        logger.warning(
            "A graph query ran out of time on %s %s", request.method, route_template(request.scope)
        )
        return problem_response(request, 503, str(error))

    @app.exception_handler(GraphUnavailable)
    async def on_unavailable(request: Request, error: GraphUnavailable) -> JSONResponse:
        logger.warning(
            "Neo4j unavailable for %s %s: %s",
            request.method,
            route_template(request.scope),
            type(error.__cause__ or error).__name__,  # the class: a message can quote a query
        )
        return problem_response(request, 503, "The graph database is not available.")

    @app.exception_handler(RepoRootNotFound)
    async def on_no_repo(request: Request, error: RepoRootNotFound) -> JSONResponse:
        logger.error(
            "repository files not found for %s %s", request.method, route_template(request.scope)
        )
        return problem_response(
            request, 500, "The repository files were not found: set NR_REPO_ROOT."
        )
