"""The API's Neo4j connection: one sync driver per app, created on first use (C3, ADR-0008).

Every query goes through `GraphConnection.read()`, which runs it as a READ transaction
(`routing_=RoutingControl.READ`), or through a `neonradar_graph.ownership` function that
`GraphConnection.call()` hands the driver to and that reads the same way (M2.12). Neo4j refuses
writes inside READ transactions, so the API is read-only by construction. Settings come from
`neonradar_graph.client.Neo4jSettings` (`neonradar api serve` passes an `Instance`'s settings).
"""

import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any, LiteralString

from fastapi import Request
from neo4j import Driver, Query, Record, RoutingControl
from neo4j.exceptions import AuthError, DriverError, Neo4jError, TransientError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver
from neonradar_graph.instances import Instance, InstanceRefused
from neonradar_graph.ownership import TIMED_OUT, TIMEOUT_DETAIL, QueryTimeout

# `execute_query` retries an unavailable database for 30 s by default; the API stops retrying
# after 1 s and answers 503 (or `degraded` for health). One connection attempt can still take up
# to the driver's 10 s connect timeout (neonradar_graph.client.get_driver).
RETRY_SECONDS = 1.0
DATABASE_NOT_FOUND = "Neo.ClientError.Database.DatabaseNotFound"


class GraphUnavailable(Exception):
    """Neo4j is not configured, not reachable or refuses the credentials (HTTP 503)."""


class GraphConnection:
    """A lazily created driver; nothing connects until the first query."""

    def __init__(self, settings: Callable[[], Neo4jSettings] = Instance.DEFAULT.settings) -> None:
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
                except InstanceRefused as error:  # NEO4J_DATABASE names the real-data database
                    raise GraphUnavailable("Neo4j is not configured (NEO4J_DATABASE)") from error
                try:
                    driver = get_driver(settings, max_transaction_retry_time=RETRY_SECONDS)
                except (DriverError, ValueError, ImportError) as error:  # e.g. NEO4J_URI=nonsense
                    raise GraphUnavailable("Neo4j is not configured (NEO4J_URI)") from error
                self._driver = driver
                self._database = settings.database
            return self._driver, self._database

    @contextmanager
    def _unavailable(self, database: str) -> Iterator[None]:
        try:
            yield
        except Neo4jError as error:
            if TIMED_OUT in (error.code or ""):  # the transaction timeout of `read`
                raise QueryTimeout(TIMEOUT_DETAIL) from error
            if isinstance(error, AuthError | TransientError):
                raise GraphUnavailable(f"Neo4j is not available: {error}") from error
            if error.code == DATABASE_NOT_FOUND:  # a wrong NEO4J_DATABASE
                raise GraphUnavailable(f"Neo4j has no database {database!r}") from error
            raise
        except DriverError as error:
            raise GraphUnavailable(f"Neo4j is not available: {error}") from error

    def read(
        self,
        query: LiteralString,
        parameters: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> list[Record]:
        """Run one parameterised query in a READ transaction (with a transaction timeout in
        seconds when given) and return its records."""
        driver, database = self._connect()
        with self._unavailable(database):
            records, _, _ = driver.execute_query(
                query if timeout is None else Query(query, timeout=timeout),
                dict(parameters or {}),
                database_=database,
                routing_=RoutingControl.READ,
            )
        return list(records)

    def call[T](self, work: Callable[[Driver, str], T]) -> T:
        """Run `work(driver, database)`, a graph function that reads through the driver in READ
        transactions (`neonradar_graph.ownership`), with the driver errors mapped as in `read`."""
        driver, database = self._connect()
        with self._unavailable(database):
            return work(driver, database)

    def close(self) -> None:
        with self._lock:
            if self._driver is not None:
                self._driver.close()
                self._driver = None


def get_graph(request: Request) -> GraphConnection:
    """FastAPI dependency: the app's connection (tests override it)."""
    graph: GraphConnection = request.app.state.graph
    return graph
