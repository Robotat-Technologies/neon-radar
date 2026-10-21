"""scripts/demo_guard.py: the check that keeps `make demo-mini` from wiping real data.

What the query counts is tested on Neo4j in test_demo_guard_neo4j.py."""

from types import TracebackType
from typing import Any, Self, cast

import demo_guard
import pytest
from neo4j import READ_ACCESS, Driver, NotificationMinimumSeverity


class FakeResult:
    def __init__(self, real: int) -> None:
        self.real = real

    def single(self, *, strict: bool) -> dict[str, int]:
        assert strict
        return {"real": self.real}


class FakeSession:
    def __init__(self, driver: "FakeDriver") -> None:
        self.driver = driver

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: type[BaseException] | BaseException | TracebackType | None) -> None:
        return None

    def run(self, query: str) -> FakeResult:
        self.driver.queries.append(query)
        return FakeResult(self.driver.real)


class FakeDriver:
    """Answers the guard's one query with a fixed count and records how it was called."""

    def __init__(self, real: int) -> None:
        self.real = real
        self.sessions: list[dict[str, Any]] = []
        self.queries: list[str] = []

    def session(self, **config: Any) -> FakeSession:
        self.sessions.append(config)
        return FakeSession(self)


def test_only_synthetic_data_passes(capsys: pytest.CaptureFixture[str]) -> None:
    driver = FakeDriver(real=0)
    assert demo_guard.check(cast(Driver, driver), "neo4j") == 0
    assert capsys.readouterr().out.startswith("OK")


def test_anything_else_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    driver = FakeDriver(real=12)
    assert demo_guard.check(cast(Driver, driver), "neo4j") == demo_guard.REFUSED == 3
    err = capsys.readouterr().err
    assert "12 nodes that are not synthetic demo data" in err
    assert "CONFIRM=yes" in err


def test_one_node_is_named_in_the_singular(capsys: pytest.CaptureFixture[str]) -> None:
    assert demo_guard.check(cast(Driver, FakeDriver(real=1)), "neo4j") == demo_guard.REFUSED
    assert "holds 1 node that is not synthetic demo data" in capsys.readouterr().err


def test_the_query_runs_read_only_without_notifications() -> None:
    driver = FakeDriver(real=0)
    demo_guard.count_not_synthetic(cast(Driver, driver), "demo")
    assert driver.queries == [demo_guard.QUERY]
    # Read access, and no warning on a new graph where `synthetic` is not a known key yet.
    assert driver.sessions == [
        {
            "database": "demo",
            "default_access_mode": READ_ACCESS,
            "notifications_min_severity": NotificationMinimumSeverity.OFF,
        }
    ]


def test_missing_password_fails_before_connecting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setitem(demo_guard.Neo4jSettings.model_config, "env_file", None)
    monkeypatch.setattr(demo_guard, "get_driver", pytest.fail)
    assert demo_guard.main() == 1
    assert "NEO4J_PASSWORD is not set" in capsys.readouterr().err
