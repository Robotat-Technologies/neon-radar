"""Hardening of the local API (PHASE-4.md 7.5.3).

The API has no login and serves one person on this machine, so its defences are about who can
reach it and what a request can carry, not about users:

- Only requests whose Host header names this machine reach the app (`TrustedHostMiddleware`):
  `127.0.0.1`, `localhost`, `[::1]` and `api`, the name nginx uses inside Compose. A web page that
  rebinds its own domain to 127.0.0.1 (DNS rebinding) is answered 400.
- Request bodies stop at 64 KiB (a copilot question is at most 500 characters).
- CORS headers only in development, only for the Vite dev server, never with credentials.
- One access log line per request: the method, the route's template, the status and the time. Never
  a query string, a path value or a body, so no searched name, entity id or question reaches a
  log (G15). `log_config` gives uvicorn a logging configuration in which these lines appear.
- An exception that no handler took becomes a fixed 500 problem, and the log names only its class
  and the route template: an exception's message or traceback can quote a request value.
- The database driver's and the HTTP client's loggers stay at WARNING whatever the root level,
  because their debug lines print query parameters (a name from a question, an entity id).

`install_problem_openapi` documents every 4xx and 5xx response as `application/problem+json` with
the `Problem` schema, the media type and body the error handlers send (RFC 9457).
"""

from __future__ import annotations

import copy
import json
import logging
import time
from typing import Any

from fastapi import FastAPI
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ALLOWED_HOSTS = ("127.0.0.1", "localhost", "[::1]", "api")
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
MAX_BODY_BYTES = 64 * 1024
PROBLEM = "application/problem+json"
QUIET_LOGGERS = ("neo4j", "httpx", "httpcore")
INTERNAL = "The API could not answer this request. Please report it to the maintainers."
access_log = logging.getLogger("neonradar.api.access")
error_log = logging.getLogger("neonradar.api.error")


def route_template(scope: Scope) -> str:
    """The matched route's path with every path value replaced by its name, for example
    `/api/v1/entities/{entity_id}`; `unmatched` when no route matched (the raw path could hold
    an id), and `redacted` when a path value is not exactly one segment of the path (a `:path`
    value with slashes, or a value equal to another segment), so a value never reaches the log."""
    if scope.get("route") is None:
        return "unmatched"
    segments = str(scope.get("path", "")).split("/")
    for name, value in (scope.get("path_params") or {}).items():
        if segments.count(str(value)) != 1:
            return "redacted"
        segments = ["{" + name + "}" if s == str(value) else s for s in segments]
    return "/".join(segments)


def log_config() -> dict[str, Any]:
    """uvicorn's default logging configuration, with the API's loggers (`neonradar.api` and its
    children: the access log, errors) at INFO on uvicorn's default handler, and the driver and
    HTTP client loggers held at WARNING. `api serve` passes it to uvicorn, and the Docker image's
    command uses `api serve`, so the access lines appear wherever the API runs."""
    from uvicorn.config import LOGGING_CONFIG

    config = copy.deepcopy(LOGGING_CONFIG)
    config["loggers"]["neonradar.api"] = {
        "handlers": ["default"],
        "level": "INFO",
        "propagate": False,
    }
    for name in QUIET_LOGGERS:
        config["loggers"][name] = {"handlers": ["default"], "level": "WARNING", "propagate": False}
    return config


def quiet_loggers() -> None:
    """Hold the driver and HTTP client loggers at WARNING (their debug lines quote parameters)."""
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


class Contain:
    """An exception no handler took: a fixed 500 problem, and a log line with the exception's
    class and the route template only."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def sending(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, sending)
        except Exception as error:
            error_log.error(
                "unhandled %s on %s %s",
                type(error).__name__,
                scope.get("method", ""),
                route_template(scope),
            )
            if started:
                return
            body = json.dumps(
                {
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": INTERNAL,
                }
            ).encode()
            headers = [
                (b"content-type", PROBLEM.encode()),
                (b"content-length", str(len(body)).encode()),
            ]
            await send({"type": "http.response.start", "status": 500, "headers": headers})
            await send({"type": "http.response.body", "body": body})


class AccessLog:
    """One line per request, from the route template."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.monotonic()
        status = 500

        async def sending(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, sending)
        finally:
            template = route_template(scope)
            elapsed = round((time.monotonic() - started) * 1000)
            access_log.info("%s %s %s %dms", scope.get("method", ""), template, status, elapsed)


def harden(app: FastAPI, *, dev: bool) -> None:
    """Add the middleware and quieten the loggers. The last one added runs first: trusted hosts,
    then the access log, then CORS (development only), then the body limit, then the containment
    of unhandled exceptions, closest to the routes."""
    quiet_loggers()
    app.add_middleware(Contain)
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_BODY_BYTES)
    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(DEV_ORIGINS),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )
    app.add_middleware(AccessLog)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))


PROBLEM_REF = {"$ref": "#/components/schemas/Problem"}
VALIDATION_SCHEMAS = ("HTTPValidationError", "ValidationError")


def problem_media_types(document: dict[str, Any]) -> dict[str, Any]:
    """Every 4xx and 5xx response as `application/problem+json` with the `Problem` schema (the
    handlers send a Problem, never FastAPI's validation error list); FastAPI's validation schemas
    are dropped once nothing refers to them. Running it twice changes nothing."""
    schemas = (document.get("components") or {}).get("schemas") or {}
    for path in (document.get("paths") or {}).values():
        for operation in path.values():
            for code, response in (operation.get("responses") or {}).items():
                content = response.get("content") or {}
                if str(code)[:1] not in ("4", "5"):
                    continue
                if "application/json" in content:
                    content[PROBLEM] = content.pop("application/json")
                if PROBLEM in content and "Problem" in schemas:
                    content[PROBLEM] = {"schema": dict(PROBLEM_REF)}
    if "Problem" in schemas and VALIDATION_SCHEMAS[0] not in json.dumps(document.get("paths")):
        for name in VALIDATION_SCHEMAS:
            schemas.pop(name, None)
    return document


def install_problem_openapi(app: FastAPI) -> None:
    """Post-process the app's OpenAPI document every time FastAPI hands it out (the step is
    idempotent, so a regenerated document is processed too)."""
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        return problem_media_types(generate())

    app.openapi = openapi  # type: ignore[method-assign]
