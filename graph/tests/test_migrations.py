"""Integration: `migrate` on a real Neo4j 5.26 Community (PHASE-1.md 5.2, 5.5; Gate 1 GC-02;
PHASE-2.md 5.2 and 5.4: 0001 then 0002 give 23 constraints and 9 own indexes)."""

import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from neonradar_graph.migrate import MIGRATIONS_DIR, MigrationError, discover, migrate

from .conftest import Neo4jTarget

pytestmark = pytest.mark.integration

MIGRATIONS = discover()
INIT = MIGRATIONS[0]
IDS = [migration.id for migration in MIGRATIONS]
CREATED = [s for migration in MIGRATIONS for s in migration.statements if s.startswith("CREATE")]
NAMES = [re.search(r"^CREATE (?:FULLTEXT )?\w+ (\w+) ", s)[1] for s in CREATED]  # type: ignore[index]
CONSTRAINTS = {name for name, s in zip(NAMES, CREATED, strict=True) if "CONSTRAINT" in s}
INDEXES = set(NAMES) - CONSTRAINTS


def query(neo4j: Neo4jTarget, cypher: str) -> list[dict[str, Any]]:
    records, _, _ = neo4j.driver.execute_query(cypher, database_=neo4j.database)
    return [record.data() for record in records]


def schema(neo4j: Neo4jTarget) -> dict[str, Any]:
    """Constraint names, own indexes (name, type, state, options) and SchemaMigration nodes."""
    constraints = {row["name"] for row in query(neo4j, "SHOW CONSTRAINTS YIELD name")}
    indexes = query(
        neo4j,
        "SHOW INDEXES YIELD name, type, state, owningConstraint, options"
        " WHERE owningConstraint IS NULL AND type <> 'LOOKUP'"
        " RETURN name, type, state, options ORDER BY name",
    )
    migrations = query(neo4j, "MATCH (m:SchemaMigration) RETURN properties(m) AS m ORDER BY m.id")
    return {"constraints": constraints, "indexes": indexes, "migrations": migrations}


def test_applies_on_an_empty_database(empty_neo4j: Neo4jTarget) -> None:
    report = migrate(empty_neo4j.driver, empty_neo4j.database)
    assert [migration.id for migration in report.applied] == ["0001_init", "0002_resolution"]
    assert report.already_applied == []
    after = schema(empty_neo4j)
    assert len(after["constraints"]) == 23 and after["constraints"] == CONSTRAINTS
    indexes = {row["name"]: row for row in after["indexes"]}
    assert len(indexes) == 9 and set(indexes) == INDEXES
    assert {row["state"] for row in indexes.values()} == {"ONLINE"}  # migrate waits for them
    names = indexes["entity_names"]
    assert names["type"] == "FULLTEXT"
    assert names["options"]["indexConfig"]["fulltext.analyzer"] == "standard-no-stop-words"
    assert indexes["paid_ts"]["type"] == "RANGE"
    assert indexes["source_record_canonical_id"]["type"] == "RANGE"
    full_text = query(
        empty_neo4j,
        "SHOW INDEXES YIELD name, labelsOrTypes, properties WHERE name = 'entity_names'"
        " RETURN labelsOrTypes, properties",
    )
    assert full_text == [
        {
            "labelsOrTypes": ["LegalEntity", "Address"],
            "properties": ["names_text", "names_latin_text"],
        }
    ]
    assert [row["m"]["id"] for row in after["migrations"]] == IDS
    for applied, migration in zip(after["migrations"], MIGRATIONS, strict=True):
        assert applied["m"]["checksum"] == migration.checksum
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", applied["m"]["applied_at"])


def test_0002_applies_on_a_1_0_database(empty_neo4j: Neo4jTarget, tmp_path: Path) -> None:
    """A database migrated with 0001 only (C2 1.0.0) takes 0002 and ends like a fresh one."""
    shutil.copy(INIT.path, tmp_path / INIT.path.name)
    migrate(empty_neo4j.driver, empty_neo4j.database, tmp_path)
    report = migrate(empty_neo4j.driver, empty_neo4j.database)
    assert [migration.id for migration in report.applied] == ["0002_resolution"]
    assert report.already_applied == ["0001_init"]
    after = schema(empty_neo4j)
    assert after["constraints"] == CONSTRAINTS
    assert {row["name"] for row in after["indexes"]} == INDEXES


def test_reapplying_is_a_no_op(empty_neo4j: Neo4jTarget) -> None:
    migrate(empty_neo4j.driver, empty_neo4j.database)
    before = schema(empty_neo4j)
    report = migrate(empty_neo4j.driver, empty_neo4j.database)
    assert report.applied == []
    assert report.already_applied == IDS
    assert schema(empty_neo4j) == before  # applied_at included: nothing was written


def test_an_edited_migration_is_refused(empty_neo4j: Neo4jTarget, tmp_path: Path) -> None:
    edited = tmp_path / INIT.path.name
    shutil.copy(MIGRATIONS_DIR / INIT.path.name, edited)
    migrate(empty_neo4j.driver, empty_neo4j.database, tmp_path)
    edited.write_text(edited.read_text(encoding="utf-8") + "// edited\n", encoding="utf-8")
    (tmp_path / "0002_more.cypher").write_text(
        "CREATE INDEX nr_test_more IF NOT EXISTS FOR (n:Entity) ON (n.caption);\n", encoding="utf-8"
    )
    with pytest.raises(MigrationError, match="never edit an applied one"):
        migrate(empty_neo4j.driver, empty_neo4j.database, tmp_path)
    after = schema(empty_neo4j)
    assert "nr_test_more" not in {row["name"] for row in after["indexes"]}
    assert [row["m"]["id"] for row in after["migrations"]] == ["0001_init"]
