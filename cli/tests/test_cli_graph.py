import os
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from neo4j.exceptions import ClientError, ServiceUnavailable
from typer.testing import CliRunner

from neonradar_cli import graph
from neonradar_cli.main import app
from neonradar_contracts.records import RecordIssue
from neonradar_graph import loader
from neonradar_graph.loader import (
    DanglingReference,
    GraphStats,
    LoadError,
    LoadRefused,
    LoadReport,
)
from neonradar_graph.mapping import MappingIssue
from neonradar_graph.migrate import MIGRATIONS_DIR, Migration, MigrationError, MigrationReport
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


def use_migrate(monkeypatch: pytest.MonkeyPatch, outcome: MigrationReport | Exception) -> None:
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)

    def fake_migrate(driver: object, database: str, directory: Path) -> MigrationReport:
        assert (database, directory) == ("neo4j", MIGRATIONS_DIR)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(graph, "migrate", fake_migrate)


def test_migrate_prints_each_applied_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    init = Migration("0001_init", MIGRATIONS_DIR / "0001_init.cypher", "abc", ("RETURN 1",) * 29)
    use_migrate(monkeypatch, MigrationReport(applied=[init]))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 0
    assert result.output == "applied 0001_init (29 statements)\n"


def test_migrate_again_has_nothing_to_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, MigrationReport(already_applied=["0001_init"]))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 0
    assert result.output == "nothing to apply (1 migration already applied)\n"


def test_migrate_refuses_an_edited_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, MigrationError("add a new migration; never edit an applied one"))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 1
    assert result.output == "FAIL  add a new migration; never edit an applied one\n"


def test_migrate_reports_a_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, ClientError("Invalid input"))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  Neo4j  at bolt://localhost:7687 answered:")


def use_loader(
    monkeypatch: pytest.MonkeyPatch, outcome: LoadReport | Exception
) -> list[dict[str, Any]]:
    """Fake `loader.load_files`; returns the calls it received."""
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)

    def fake_load(driver: object, paths: list[Path], *, strict: bool, database: str) -> LoadReport:
        calls.append({"paths": paths, "strict": strict, "database": database})
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(loader, "load_files", fake_load)
    return calls


def load_report(**changes: Any) -> LoadReport:
    report = LoadReport(
        strict=True,
        files=[Path("a.ftm.jsonl")],
        records=3,
        nodes_by_label=Counter({"Entity": 2, "Company": 1}),
        relationships_by_type=Counter({"OWNS": 1}),
        written=Counter(nodes_created=2, relationships_created=1),
        duration_s=0.5,
    )
    for name, value in changes.items():
        setattr(report, name, value)
    return report


DANGLING = DanglingReference("PAID", "syn-payment-1", "syn-acct-1", "syn-acct-9", False, True)


def test_load_prints_counts_and_is_strict_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report())
    result = runner.invoke(app, ["graph", "load", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert calls == [{"paths": [tmp_path], "strict": True, "database": "neo4j"}]
    lines = result.output.splitlines()
    assert lines[0] == "3 records from 1 file(s), strict"
    assert lines[1:7] == [
        "nodes by label:",
        "  Company: 1",
        "  Entity: 2",
        "relationships by type:",
        "  OWNS: 1",
        "created 2 nodes and 1 relationships; moved 0 relationships; labels 0 added and 0 removed",
    ]
    assert "dangling references: 0" in lines
    assert lines[-1] == "OK in 0.5 s"


def test_a_non_strict_load_reports_dangling_references_and_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report(strict=False, dangling=[DANGLING]))
    result = runner.invoke(app, ["graph", "load", "--no-strict", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert calls[0]["strict"] is False
    assert "  DANGLING PAID syn-payment-1: no :Account node syn-acct-9" in result.output
    assert result.output.endswith("WARN in 0.5 s\n")


def test_an_empty_record_file_is_a_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_loader(monkeypatch, load_report(empty_files=[Path("empty.ftm.jsonl")]))
    result = runner.invoke(app, ["graph", "load", str(tmp_path)])
    assert result.exit_code == 0
    assert "WARN  empty.ftm.jsonl holds no records" in result.output.splitlines()
    assert result.output.endswith("WARN in 0.5 s\n")


def test_a_strict_load_with_dangling_references_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_loader(monkeypatch, load_report(dangling=[DANGLING]))
    result = runner.invoke(app, ["graph", "load", str(tmp_path)])
    assert result.exit_code == 1
    assert result.output.endswith(
        "FAILED (strict): 1 dangling reference(s); the rest of the load was written:"
        " fix the input and load again\n"
    )


def test_a_refused_load_lists_its_issues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    issues = [RecordIssue("R7", f"syn-payment-{n}", "amount must be above 0") for n in range(30)]
    use_loader(monkeypatch, LoadRefused(issues, [MappingIssue("syn-o-1", "two owners")]))
    result = runner.invoke(app, ["graph", "load", str(tmp_path)])
    assert result.exit_code == 1
    lines = result.output.splitlines()
    assert lines[0] == "  R7 syn-payment-0: amount must be above 0"
    assert lines[-2:] == [
        "  ... and 6 more",
        "REFUSED (strict): 31 issue(s); nothing was written",
    ]


def test_a_load_that_cannot_start_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_loader(monkeypatch, LoadError("FORMAT a.ftm.jsonl:2: invalid JSON"))
    result = runner.invoke(app, ["graph", "load", str(tmp_path)])
    assert (result.exit_code, result.output) == (1, "FAIL  FORMAT a.ftm.jsonl:2: invalid JSON\n")


def test_stats_prints_counts_by_label_and_type(monkeypatch: pytest.MonkeyPatch) -> None:
    use_loader(monkeypatch, load_report())
    counted = GraphStats(3, 1, {"Company": 1, "Entity": 2}, {"OWNS": 1})
    monkeypatch.setattr(loader, "stats", lambda driver, database: counted)
    result = runner.invoke(app, ["graph", "stats"])
    assert result.exit_code == 0
    assert result.output.splitlines() == [
        "nodes: 3",
        "  Company: 1",
        "  Entity: 2",
        "relationships: 1",
        "  OWNS: 1",
    ]


def test_wipe_refuses_without_yes_and_never_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_driver(*args: Any) -> None:
        raise AssertionError("wipe connected without --yes")

    monkeypatch.setattr(graph, "get_driver", no_driver)
    result = runner.invoke(app, ["graph", "wipe"])
    assert result.exit_code == 1
    assert result.output.startswith("REFUSED  graph wipe deletes every node except")


def test_wipe_with_yes_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    use_loader(monkeypatch, load_report())
    monkeypatch.setattr(loader, "wipe", lambda driver, database: 7)
    result = runner.invoke(app, ["graph", "wipe", "--yes"])
    assert result.exit_code == 0
    assert result.output == "deleted 7 nodes from bolt://localhost:7687 (database neo4j)\n"
    assert "test-password" not in result.output
