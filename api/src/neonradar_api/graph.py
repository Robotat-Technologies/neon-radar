"""The API's Neo4j connection: one sync driver per app, created on first use (C3, ADR-0008).

Every query goes through `GraphConnection.read()`, which runs it as a READ transaction
(`routing_=RoutingControl.READ`). Neo4j refuses writes inside READ transactions, so the API is
read-only by construction. Settings come from `neonradar_graph.client.Neo4jSettings`.
"""

import threading
from collections.abc import Callable, Mapping
from typing import Any, LiteralString

from fastapi import Request
from neo4j import Driver, Record, RoutingControl
from neo4j.exceptions import AuthError, DriverError, TransientError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver

# The driver retries an unavailable database for 30 s by default; a request should not hang that
# long, so the API gives up after a few seconds at most and answers 503 (or `degraded` for health).
RETRY_SECONDS = 1.0


class GraphUnavailable(Exception):
    """Neo4j is not configured, not reachable or refuses the credentials (HTTP 503)."""


class GraphConnection:
    """A lazily created driver; nothing connects until the first query."""

    def __init__(self, settings: Callable[[], Neo4jSettings] = Neo4jSettings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._driver: Driver | None = None
        self._database = "neo4j"

    def _connect(self) -> tuple[Driver, str]:
        with self._lock:
            if self._driver is None:
                try:
                    settings = self._settings()
                except ValidationError as error:
                    raise GraphUnavailable("Neo4j is not configured (NEO4J_PASSWORD)") from error
                self._driver = get_driver(settings, max_transaction_retry_time=RETRY_SECONDS)
                self._database = settings.database
            return self._driver, self._database

    def read(
        self, query: LiteralString, parameters: Mapping[str, Any] | None = None
    ) -> list[Record]:
        """Run one parameterised query in a READ transaction and return its records."""
        driver, database = self._connect()
        try:
            records, _, _ = driver.execute_query(
                query, dict(parameters or {}), database_=database, routing_=RoutingControl.READ
            )
        except (DriverError, AuthError, TransientError) as error:
            raise GraphUnavailable(f"Neo4j is not available: {error}") from error
        return list(records)

    def close(self) -> None:
        with self._lock:
            if self._driver is not None:
                self._driver.close()
                self._driver = None


def get_graph(request: Request) -> GraphConnection:
    """FastAPI dependency: the app's connection (tests override it)."""
    graph: GraphConnection = request.app.state.graph
    return graph
