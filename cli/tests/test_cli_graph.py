import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from neo4j.exceptions import ServiceUnavailable
from typer.testing import CliRunner

from neonradar_cli import graph
from neonradar_cli.main import app
from neonradar_graph.smoke import SmokeReport

runner = CliRunner()


@pytest.fixture(autouse=True)
def settings_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Never read the repository's real .env in these tests."""
    for name in [key for key in os.environ if key.startswith("NEO4J_")]:
        monkeypatch.delenv(name)
    monkeypatch.setitem(graph.Neo4jSettings.model_config, "env_file", tmp_path / "missing.env")


@contextmanager
def fake_driver(*args: Any) -> Iterator[object]:
    yield object()


def use_fakes(monkeypatch: pytest.MonkeyPatch, report: SmokeReport) -> None:
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)
    monkeypatch.setattr(graph, "run_smoke", lambda driver, database: report)


@pytest.mark.parametrize(
    ("report", "exit_code"),
    [
        (SmokeReport("5.26.32 community", "5.26.32", "2.13.4"), 0),
        (SmokeReport("5.26.32 community", "5.26.32", None), 1),
    ],
)
def test_smoke_prints_one_line_per_component(
    monkeypatch: pytest.MonkeyPatch, report: SmokeReport, exit_code: int
) -> None:
    use_fakes(monkeypatch, report)
    result = runner.invoke(app, ["graph", "smoke"])
    assert result.exit_code == exit_code
    assert result.output.splitlines() == report.lines()


def test_smoke_without_a_password_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(app, ["graph", "smoke"])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD is not set" in result.output


def test_smoke_when_neo4j_is_down_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, SmokeReport(None, None, None))

    def down(driver: object, timeout_s: float) -> None:
        raise ServiceUnavailable("connection refused")

    monkeypatch.setattr(graph, "wait_until_ready", down)
    result = runner.invoke(app, ["graph", "smoke", "--timeout", "1"])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  Neo4j  not reachable at bolt://localhost:7687")
    assert "test-password" not in result.output
