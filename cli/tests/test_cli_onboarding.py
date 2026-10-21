import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from neo4j.exceptions import ServiceUnavailable
from typer.testing import CliRunner

from neonradar_cli import onboarding
from neonradar_cli.main import app
from neonradar_graph.onboarding import Counts, Entry, QueryResult

runner = CliRunner()


@pytest.fixture(autouse=True)
def settings_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Never read the repository's real .env in these tests."""
    for name in [key for key in os.environ if key.startswith("NEO4J_")]:
        monkeypatch.delenv(name)
    monkeypatch.setitem(onboarding.Neo4jSettings.model_config, "env_file", tmp_path / "x.env")


@contextmanager
def fake_driver(*args: Any) -> Iterator[object]:
    yield object()


def use_fakes(
    monkeypatch: pytest.MonkeyPatch, counts: Counts, results: list[QueryResult]
) -> list[list[Entry]]:
    """Fake the database; return the list that collects the entries the command parsed."""
    seen: list[list[Entry]] = []
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(onboarding, "get_driver", fake_driver)
    monkeypatch.setattr(onboarding, "wait_until_ready", lambda driver, timeout_s: None)
    monkeypatch.setattr(onboarding, "load", lambda driver, rows, database: counts)
    monkeypatch.setattr(onboarding, "reset", lambda driver, database: 51)

    def check(driver: object, entries: list[Entry], database: str) -> list[QueryResult]:
        seen.append(entries)
        return results

    monkeypatch.setattr(onboarding, "check_queries", check)
    return seen


def test_check_prints_one_line_per_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = use_fakes(monkeypatch, Counts(20, 15, 16), [QueryResult("@example", rows=4)])
    result = runner.invoke(app, ["onboarding", "check"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "loaded companies-20.csv: 20 OnbCompany, 15 OnbPerson, 16 OnbAddress nodes in the graph",
        "OK    @example  ran, 4 rows returned",
        "1 queries: 1 ran, 0 failed",
    ]
    assert seen[0][0].handle == "@example"  # parsed from the committed first-queries.md


def test_check_fails_when_a_query_fails_and_warns_about_extra_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [QueryResult("@example", rows=4), QueryResult("@b", error="Neo.X: no")]
    use_fakes(monkeypatch, Counts(21, 15, 16), results)
    result = runner.invoke(app, ["onboarding", "check"])
    assert result.exit_code == 1
    assert "WARN  the CSV makes 20, 15 and 16: other Onb* nodes" in result.output
    assert "FAIL  @b  Neo.X: no" in result.output
    assert result.output.endswith("2 queries: 1 ran, 1 failed\n")


def test_check_fails_on_a_bad_csv_before_connecting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_fakes(monkeypatch, Counts(0, 0, 0), [])
    bad = tmp_path / "bad.csv"
    bad.write_text("company_id\nonb-co-01\n")
    result = runner.invoke(app, ["onboarding", "check", "--csv", str(bad)])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  ") and "header is ['company_id']" in result.output


def test_reset_reports_the_removed_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, Counts(0, 0, 0), [])
    result = runner.invoke(app, ["onboarding", "reset"])
    assert result.exit_code == 0
    assert result.output == "removed 51 Onb* nodes\n"


def test_without_a_password_both_commands_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    for command in ("check", "reset"):
        result = runner.invoke(app, ["onboarding", command])
        assert result.exit_code == 1
        assert "NEO4J_PASSWORD is not set" in result.output


def test_when_neo4j_is_down_the_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, Counts(0, 0, 0), [])

    def down(driver: object, timeout_s: float) -> None:
        raise ServiceUnavailable("connection refused")

    monkeypatch.setattr(onboarding, "wait_until_ready", down)
    result = runner.invoke(app, ["onboarding", "check", "--timeout", "1"])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  Neo4j at bolt://localhost:7687: connection refused")
    assert "test-password" not in result.output
