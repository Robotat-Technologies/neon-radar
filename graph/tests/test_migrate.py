"""Unit tests of the migration runner with a fake driver; test_migrations.py uses a real Neo4j."""

from pathlib import Path
from typing import Any, cast

import pytest
from neo4j import Driver

from neonradar_graph import migrate as m
from neonradar_graph.migrate import MigrationError, checksum, discover, migrate, parse_statements


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_the_init_migration_has_22_constraints_and_7_indexes() -> None:
    (init,) = discover()
    assert init.id == "0001_init"
    kinds = [" ".join(s.split()[:2]) for s in init.statements]
    assert kinds.count("CREATE CONSTRAINT") == 22
    assert kinds.count("CREATE INDEX") + kinds.count("CREATE FULLTEXT") == 7
    assert len(init.statements) == 29
    assert all(" IF NOT EXISTS " in statement for statement in init.statements)


def test_parse_skips_comments_and_blank_lines_and_strips_the_semicolon() -> None:
    text = "// header\n\nCREATE INDEX a IF NOT EXISTS FOR (n:A) ON (n.x);\n  // note\nRETURN 1 ;\n"
    assert parse_statements(text, "x.cypher") == (
        "CREATE INDEX a IF NOT EXISTS FOR (n:A) ON (n.x)",
        "RETURN 1",
    )


@pytest.mark.parametrize("text", ["CREATE INDEX a\nFOR (n:A) ON (n.x);\n", ";\n", "// only\n"])
def test_parse_refuses_multi_line_statements_and_empty_files(text: str) -> None:
    with pytest.raises(MigrationError, match=r"x\.cypher"):
        parse_statements(text, "x.cypher")


def test_checksum_ignores_crlf_line_endings() -> None:
    assert checksum("RETURN 1;\r\nRETURN 2;\r\n") == checksum("RETURN 1;\nRETURN 2;\n")
    assert checksum("RETURN 1;\n") != checksum("RETURN 1;\n// edited\n")


def test_discover_orders_by_number(tmp_path: Path) -> None:
    write(tmp_path, "0002_more.cypher", "RETURN 2;\n")
    write(tmp_path, "0001_init.cypher", "RETURN 1;\n")
    assert [migration.id for migration in discover(tmp_path)] == ["0001_init", "0002_more"]


@pytest.mark.parametrize(
    ("names", "message"),
    [
        ((), "no migrations"),
        (("1_init.cypher",), "NNNN_<name>.cypher"),
        (("0001_Init.cypher",), "NNNN_<name>.cypher"),
        (("0001_a.cypher", "0001_b.cypher"), "same number"),
    ],
)
def test_discover_refuses_bad_folders(tmp_path: Path, names: tuple[str, ...], message: str) -> None:
    for name in names:
        write(tmp_path, name, "RETURN 1;\n")
    with pytest.raises(MigrationError, match=message):
        discover(tmp_path)


class FakeSession:
    def __init__(self, driver: FakeDriver) -> None:
        self.driver = driver

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def run(self, query: str, **params: Any) -> Any:
        if query == m.APPLIED:
            return [{"id": key, "checksum": value} for key, value in self.driver.applied.items()]
        self.driver.log.append(query if not params else f"{query} {params}")
        return self

    def consume(self) -> None:
        return None


class FakeDriver:
    """Remembers SchemaMigration records and every statement it was sent."""

    def __init__(self, applied: dict[str, str] | None = None) -> None:
        self.applied = dict(applied or {})
        self.log: list[str] = []

    def session(self, database: str, **config: Any) -> FakeSession:
        assert database == "neo4j"
        assert config in ({}, {"notifications_min_severity": "OFF"})
        return FakeSession(self)

    def execute_query(self, query: str, **params: Any) -> tuple[list[Any], None, None]:
        assert query == m.RECORD
        assert params["applied_at"] == "2026-10-22T10:00:00Z"
        self.applied[params["id"]] = params["checksum"]
        self.log.append(f"record {params['id']}")
        return [], None, None


def run(driver: FakeDriver, directory: Path) -> m.MigrationReport:
    return migrate(cast(Driver, driver), "neo4j", directory, clock=lambda: "2026-10-22T10:00:00Z")


def test_applies_pending_migrations_in_order_then_is_a_no_op(tmp_path: Path) -> None:
    write(tmp_path, "0001_init.cypher", "// one\nRETURN 1;\n")
    write(tmp_path, "0002_more.cypher", "RETURN 2;\nRETURN 3;\n")
    driver = FakeDriver()
    report = run(driver, tmp_path)
    assert [migration.id for migration in report.applied] == ["0001_init", "0002_more"]
    assert report.already_applied == []
    wait = f"{m.AWAIT_INDEXES} {{'seconds': 300}}"
    assert driver.log == [
        *("RETURN 1", wait, "record 0001_init"),
        *("RETURN 2", "RETURN 3", wait, "record 0002_more"),
    ]
    driver.log.clear()
    again = run(driver, tmp_path)
    assert again.applied == []
    assert again.already_applied == ["0001_init", "0002_more"]
    assert driver.log == []


def test_applies_only_the_new_migration(tmp_path: Path) -> None:
    first = write(tmp_path, "0001_init.cypher", "RETURN 1;\n")
    write(tmp_path, "0002_more.cypher", "RETURN 2;\n")
    driver = FakeDriver({"0001_init": checksum(first.read_text())})
    report = run(driver, tmp_path)
    assert [migration.id for migration in report.applied] == ["0002_more"]
    assert report.already_applied == ["0001_init"]
    assert "RETURN 1" not in driver.log


def test_refuses_an_edited_migration_before_applying_anything(tmp_path: Path) -> None:
    write(tmp_path, "0001_init.cypher", "RETURN 1;\n// edited\n")
    write(tmp_path, "0002_more.cypher", "RETURN 2;\n")
    driver = FakeDriver({"0001_init": checksum("RETURN 1;\n")})
    with pytest.raises(MigrationError, match="never edit an applied one"):
        run(driver, tmp_path)
    assert driver.log == []


def test_refuses_a_database_with_an_unknown_migration(tmp_path: Path) -> None:
    write(tmp_path, "0001_init.cypher", "RETURN 1;\n")
    driver = FakeDriver({"0007_future": "f" * 64})
    with pytest.raises(MigrationError, match="0007_future"):
        run(driver, tmp_path)
    assert driver.log == []
