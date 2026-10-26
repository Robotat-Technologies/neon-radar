"""Helpers for the graph tests. The shared Neo4j (fixtures `neo4j`, `empty_neo4j` and
`graph_db`, `Neo4jTarget`, `pinned_gds`) lives in graph/tests/support/nr_test_neo4j.py, a
pytest plugin that the root conftest.py registers once for every suite; this file re-exports
the two names the graph tests import, never the fixtures.

`demo_resolution` (session) is a resolution run of the demo profile's fixtures, built with
`neonradar_resolve.run.run` and the deterministic rules only. The resolver is a test-only
dependency (graph's `dev` group); the graph package itself never imports it.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from nr_test_neo4j import Neo4jTarget, pinned_gds

from neonradar_graph.client import REPO_ROOT
from neonradar_graph.migrate import discover

__all__ = ["DEMO_DIRS", "FakeDriver", "Neo4jTarget", "pinned_gds", "record", "resolve"]

# The record folders of ingest/profiles/demo.yaml: demo-mini and the ER benchmark (M2.9).
DEMO_DIRS = [
    REPO_ROOT / "data" / "fixtures" / "demo-mini",
    REPO_ROOT / "data" / "fixtures" / "er-bench",
]
DEMO_RUN_ID = "er-20261023T120000-0d0e"


def resolve(record_dirs: list[Path], run_dir: Path) -> Path:
    """A resolution run of `record_dirs` into `run_dir` (deterministic rules only)."""
    from neonradar_resolve import run
    from neonradar_resolve.config import load_config

    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    spill = run_dir.parent / f"{run_dir.name}-spill"
    config = run.RunConfig(resolver, sha, temp_directory=spill, real_data=False)
    run.run(record_dirs, run_dir, config, probabilistic=False)
    return run_dir


@pytest.fixture(scope="session")
def demo_resolution(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The demo profile's records resolved once per session (read-only for the tests)."""
    return resolve(DEMO_DIRS, tmp_path_factory.mktemp("resolution") / DEMO_RUN_ID)


COUNTERS = (
    "nodes_created", "nodes_deleted", "relationships_created", "relationships_deleted",
    "labels_added", "labels_removed",
)  # fmt: skip


class FakeDriver:
    """Records every query and the database it names; answers the migration check (every
    migration applied), returns no dangling rows, and counts created nodes per node row."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], str | None]] = []

    @contextmanager
    def session(self, database: str | None = None, **kwargs: Any) -> Iterator[Any]:
        def run(query: str, parameters: dict[str, Any] | None = None) -> Any:
            self.calls.append((query, parameters or {}, database))
            if "SchemaMigration" in query:
                return [{"id": migration.id} for migration in discover()]
            return SimpleNamespace(consume=lambda: SimpleNamespace(counters=_counters()))

        yield SimpleNamespace(run=run)

    def execute_query(
        self, query: str, parameters: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        params = parameters or {}
        self.calls.append((query, params, kwargs.get("database_")))
        created = len(params.get("rows", [])) if "MERGE (n:" in query else 0
        records = [{"written": len(params.get("rows", []))}] if "AS written" in query else []
        return records, SimpleNamespace(counters=_counters(nodes_created=created)), []

    @property
    def queries(self) -> list[str]:
        return [query for query, _, _ in self.calls]


def _counters(**values: int) -> SimpleNamespace:
    return SimpleNamespace(**{name: values.get(name, 0) for name in COUNTERS})


def record(rid: str, schema: str, nr: dict[str, Any] | None = None, **props: Any) -> dict[str, Any]:
    """A C1-shaped record of nr_synthetic (prefix syn) or gb_companies_house (prefix gbch)."""
    synthetic = rid.startswith("syn-")
    data: dict[str, Any] = {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic" if synthetic else "gb_companies_house"],
        "properties": {
            key: value if isinstance(value, list) else [value] for key, value in props.items()
        },
    }
    if synthetic or nr:
        data["nr"] = {"v": "1.0", **({"synthetic": True} if synthetic else {}), **(nr or {})}
    return data
