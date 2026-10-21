import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli import graph
from neonradar_cli.main import app
from neonradar_detect import catalog, runner

cli = CliRunner()


@pytest.fixture(autouse=True)
def fake_neo4j(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Never read the repository's real .env, never connect."""
    for name in [key for key in os.environ if key.startswith("NEO4J_")]:
        monkeypatch.delenv(name)
    monkeypatch.setitem(graph.Neo4jSettings.model_config, "env_file", tmp_path / "missing.env")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")

    @contextmanager
    def fake_driver(*args: Any) -> Iterator[object]:
        yield object()

    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)


def test_run_prints_the_run_id_and_the_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None, str | None]] = []

    def fake_run(driver: object, database: str, **kwargs: Any) -> runner.RunReport:
        calls.append((database, kwargs["typology"], kwargs["run_id"]))
        return runner.RunReport(
            run_id="run-20261021T101500-7f3a",
            directory=Path("data/runs/run-20261021T101500-7f3a"),
            started_at="2026-10-21T10:15:00Z",
            status="ok",
            typologies=["circular_flow"],
        )

    monkeypatch.setattr(runner, "run", fake_run)
    result = cli.invoke(app, ["detect", "run", "--typology", "circular_flow"])
    assert result.exit_code == 0, result.output
    assert calls == [("neo4j", "circular_flow", None)]
    assert result.output.splitlines() == [
        "run-20261021T101500-7f3a  0 alerts  (circular_flow)",
        "wrote data/runs/run-20261021T101500-7f3a",
    ]


def test_a_failed_run_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(driver: object, database: str, **kwargs: Any) -> runner.RunReport:
        raise runner.RunError("unknown typology 'nope'")

    monkeypatch.setattr(runner, "run", failing)
    result = cli.invoke(app, ["detect", "run", "--typology", "nope"])
    assert result.exit_code == 1
    assert result.output == "FAIL  unknown typology 'nope'\n"


@pytest.mark.parametrize(
    "error",
    [catalog.CatalogError("circular_flow.yaml: not valid"), PermissionError("data/runs: denied")],
)
def test_catalog_and_file_errors_print_a_fail_line(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def failing(driver: object, database: str, **kwargs: Any) -> runner.RunReport:
        raise error

    monkeypatch.setattr(runner, "run", failing)
    result = cli.invoke(app, ["detect", "run"])
    assert result.exit_code == 1
    assert result.output == f"FAIL  {error}\n"


def test_run_help_explains_a_reused_run_id() -> None:
    result = cli.invoke(app, ["detect", "run", "--help"], env={"COLUMNS": "200"})
    assert "Given again" in result.output


def test_list_shows_the_typologies_with_a_detector() -> None:
    result = cli.invoke(app, ["detect", "list"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert "circular_flow  0.1.0  draft  neonradar_detect.detectors.circular_flow 0.1.0" in lines
    assert lines[-1].endswith("typologies have a detector")
