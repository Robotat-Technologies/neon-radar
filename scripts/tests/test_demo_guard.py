"""scripts/demo_guard.py: the check that keeps `make demo-mini` from wiping real data."""

from typing import Any, cast

import demo_guard
import pytest
from neo4j import Driver, RoutingControl


class FakeDriver:
    """Answers the guard's one query with a fixed count and records how it was called."""

    def __init__(self, real: int) -> None:
        self.real = real
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute_query(self, query: str, **kwargs: Any) -> tuple[list[dict[str, int]], None, None]:
        self.calls.append((query, kwargs))
        return [{"real": self.real}], None, None


def test_only_synthetic_entities_pass(capsys: pytest.CaptureFixture[str]) -> None:
    driver = FakeDriver(real=0)
    assert demo_guard.check(cast(Driver, driver), "neo4j") == 0
    assert capsys.readouterr().out.startswith("OK")


def test_any_real_entity_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    driver = FakeDriver(real=12)
    assert demo_guard.check(cast(Driver, driver), "neo4j") == demo_guard.REFUSED == 3
    err = capsys.readouterr().err
    assert "12 entities that are not synthetic" in err
    assert "CONFIRM=yes" in err


def test_query_reads_every_entity_not_marked_synthetic() -> None:
    driver = FakeDriver(real=0)
    demo_guard.count_not_synthetic(cast(Driver, driver), "demo")
    [(query, kwargs)] = driver.calls
    assert query.startswith("MATCH (n:Entity) WHERE n.synthetic IS NULL OR n.synthetic <> true")
    assert kwargs == {"database_": "demo", "routing_": RoutingControl.READ}


def test_missing_password_fails_before_connecting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setitem(demo_guard.Neo4jSettings.model_config, "env_file", None)
    monkeypatch.setattr(demo_guard, "get_driver", pytest.fail)
    assert demo_guard.main() == 1
    assert "NEO4J_PASSWORD is not set" in capsys.readouterr().err
