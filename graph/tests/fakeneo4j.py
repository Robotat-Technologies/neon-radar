"""A fake of the parts of the neo4j driver that `run_read` uses (PHASE-4.md M4.1).

It keeps the order rules of the real driver that matter to the read helper: rows cannot be
fetched once the result is consumed, and nothing runs once the transaction is closed (the driver
raises `ResultConsumedError` in both cases). `FakeDriver.steps` records the order of the calls.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Rows = Callable[[str, dict[str, Any]], list[dict[str, Any]]]


@dataclass
class Counters:
    contains_updates: bool = False
    contains_system_updates: bool = False


@dataclass
class Summary:
    query_type: str = "r"
    counters: Counters = field(default_factory=Counters)


class Record:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def data(self) -> dict[str, Any]:
        return dict(self._data)


class Consumed(RuntimeError):
    """What the real driver raises as `ResultConsumedError`."""


class Result:
    def __init__(self, tx: Tx, rows: list[dict[str, Any]], summary: Summary) -> None:
        self.tx, self.rows, self.summary = tx, rows, summary
        self.consumed = False

    def fetch(self, n: int) -> list[Record]:
        if self.consumed or self.tx.closed:
            raise Consumed("fetch after consume or close")
        self.tx.driver.steps.append("fetch")
        return [Record(r) for r in self.rows[:n]]

    def consume(self) -> Summary:
        if self.tx.closed:
            raise Consumed("consume after close")
        self.consumed = True
        self.tx.driver.steps.append("consume")
        return self.summary


class Tx:
    def __init__(self, driver: FakeDriver, metadata: dict[str, Any], timeout: float) -> None:
        self.driver, self.metadata, self.timeout = driver, metadata, timeout
        self.closed = False

    def run(self, text: str, parameters: dict[str, Any]) -> Result:
        if self.closed:
            raise Consumed("run after close")
        self.driver.calls.append((self.metadata["query"], text, parameters))
        self.driver.steps.append("run")
        if self.driver.error is not None:
            raise self.driver.error
        rows = self.driver.rows(self.metadata["query"], parameters)
        return Result(self, rows, self.driver.summary)

    def commit(self) -> None:  # pragma: no cover - must never be called
        raise AssertionError("a read must never commit")

    def close(self) -> None:
        self.closed = True
        self.driver.steps.append("close")


class Session:
    def __init__(self, driver: FakeDriver) -> None:
        self.driver = driver

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def begin_transaction(self, metadata: dict[str, Any], timeout: float) -> Tx:
        tx = Tx(self.driver, metadata, timeout)
        self.driver.transactions.append(tx)
        return tx


class FakeDriver:
    def __init__(self, rows: Rows | None = None, summary: Summary | None = None) -> None:
        self.rows: Rows = rows or (lambda name, parameters: [])
        self.summary = summary or Summary()
        self.error: Exception | None = None
        self.sessions: list[dict[str, Any]] = []
        self.transactions: list[Tx] = []
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.steps: list[str] = []

    def session(self, **options: Any) -> Session:
        self.sessions.append(options)
        return Session(self)
