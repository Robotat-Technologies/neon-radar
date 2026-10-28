"""The copilot's routes (PHASE-4.md 5.3 and 7.5.4): `POST /copilot/ask` and `GET /copilot`.

Every outcome of a question, a refusal and a clarifying question included, is a 200 with a
`CopilotAnswer`; the error statuses are for requests the copilot could not take: 422 for an
invalid body, 503 when the copilot is busy or the database is unreachable or too slow, 500 when a
query file failed the read check or the database refused a query (a defect), 501 until the
service is configured (M4.5). The handlers look the service up after FastAPI has validated the
body, so an invalid body is a 422 whether or not the service exists. No error detail and no log
line ever contains the question, a name from it or a query parameter: a database error is logged
by its code only. At most `slots` questions run at once (2 by default): a laptop's Neo4j runs
each query on one thread, and a third question waits a second for a slot, then gets a 503.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, Request
from neo4j.exceptions import (
    ClientError,
    DatabaseError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)
from neonradar_contracts.api import CopilotAnswer, CopilotInfo, CopilotRequest, Problem
from neonradar_graph.readonly import ReadRefused

router = APIRouter(tags=["copilot"])
log = logging.getLogger("neonradar.api.copilot")
PROBLEMS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (422, 500, 501, 503)
}
BUSY = "The copilot is answering other questions. Try again in a moment."
UNREACHABLE = "The graph database is not reachable. Check that Neo4j is running."
SLOW = "The question took too long to answer. Try a narrower question, or fewer steps."
DEFECT = "A copilot query failed its read-only check. Please report it to the maintainers."
FAILED = "The graph database could not run a query. Please report it to the maintainers."
# a transaction ended by the server's time or memory limit (PHASE-4.md 7.5.2 layer 8)
SLOW_CODES = ("TransactionTimedOut", "MemoryLimit", "MemoryPoolOutOfMemory", "OutOfMemory")


class Copilot(Protocol):
    """What the routes need from `neonradar_copilot.copilot.Copilot` (M4.3b). The route modules
    import nothing from the copilot package, so they type-check and load before M4.3."""

    def ask(self, request: CopilotRequest) -> CopilotAnswer: ...

    def info(self) -> CopilotInfo: ...


class Busy(RuntimeError):
    """No slot became free in time."""


@dataclass
class CopilotService:
    copilot: Copilot
    slots: int = 2
    wait_s: float = 1.0
    _gate: threading.BoundedSemaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._gate = threading.BoundedSemaphore(self.slots)

    def ask(self, request: CopilotRequest) -> CopilotAnswer:
        if not self._gate.acquire(timeout=self.wait_s):
            raise Busy
        try:
            return self.copilot.ask(request)
        finally:
            self._gate.release()


@contextmanager
def read_errors() -> Iterator[None]:
    """Database errors as the fixed problems of 7.5.4, logged by code only (an error's message
    can quote a query parameter)."""
    try:
        yield
    except (ServiceUnavailable, SessionExpired) as error:
        raise HTTPException(503, detail=UNREACHABLE) from error
    except ReadRefused as error:
        log.error("read check failed: %s", error)  # names the query file, never a value
        raise HTTPException(500, detail=DEFECT) from error
    except (ClientError, TransientError, DatabaseError) as error:
        code = error.code or type(error).__name__
        if any(word in code for word in SLOW_CODES):
            raise HTTPException(503, detail=SLOW) from error
        if "DatabaseUnavailable" in code:
            raise HTTPException(503, detail=UNREACHABLE) from error
        log.error("database error %s", code)
        raise HTTPException(500, detail=FAILED) from error


def copilot_service(request: Request) -> CopilotService:
    service = getattr(request.app.state, "copilot", None)
    if not isinstance(service, CopilotService):
        raise HTTPException(501, detail="The copilot is not configured yet (PHASE-4.md M4.5).")
    return service


@router.post(
    "/copilot/ask", response_model=CopilotAnswer, responses=PROBLEMS, operation_id="copilot_ask"
)
def copilot_ask(body: CopilotRequest, request: Request) -> CopilotAnswer:
    """Answer one question from the template catalog, with its evidence, or refuse."""
    service = copilot_service(request)
    with read_errors():
        try:
            return service.ask(body)
        except Busy as error:
            raise HTTPException(503, detail=BUSY) from error


@router.get("/copilot", response_model=CopilotInfo, responses=PROBLEMS, operation_id="copilot_info")
def copilot_info(request: Request) -> CopilotInfo:
    """The copilot's mode, its standing notice and badge, and its question templates."""
    return copilot_service(request).copilot.info()
