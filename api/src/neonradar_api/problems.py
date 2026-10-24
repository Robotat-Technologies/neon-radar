"""RFC 9457 problem details for every error the API returns (C3, contracts/C3-api.md).

Every error is `application/problem+json` with `type` `about:blank`, `title` the HTTP reason
phrase, `detail` a sentence for people and `instance` the request path. Validation errors list
`<location>: <message>` pairs in `detail` without echoing the input.
"""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Final, NoReturn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from neonradar_api.files import RepoRootNotFound
from neonradar_api.graph import GraphUnavailable
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


def install(app: FastAPI) -> None:
    """Answer every error with a problem."""

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
        route = getattr(request.scope.get("route"), "path", "?")  # the template, never an id
        logger.warning("A graph query ran out of time on %s %s", request.method, route)
        return problem_response(request, 503, str(error))

    @app.exception_handler(GraphUnavailable)
    async def on_unavailable(request: Request, error: GraphUnavailable) -> JSONResponse:
        logger.warning("Neo4j unavailable for %s %s: %s", request.method, request.url.path, error)
        return problem_response(request, 503, "The graph database is not available.")

    @app.exception_handler(RepoRootNotFound)
    async def on_no_repo(request: Request, error: RepoRootNotFound) -> JSONResponse:
        logger.error("repository files not found for %s %s", request.method, request.url.path)
        return problem_response(
            request, 500, "The repository files were not found: set NR_REPO_ROOT."
        )

    @app.exception_handler(Exception)
    async def on_error(request: Request, error: Exception) -> JSONResponse:
        logger.error("unhandled error on %s %s", request.method, request.url.path, exc_info=error)
        return problem_response(request, 500, "Internal error; the API log has the details.")
