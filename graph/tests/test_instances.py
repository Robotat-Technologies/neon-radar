"""The two Neo4j instances (C2 L17, PHASE-2.md M2.11 deliverable 7), with a fake driver that
records every query: the default instance refuses non-synthetic records before any query, the
real-data instance refuses synthetic ones, a mixed load is refused by both, each instance names
its own database, and the loader needs none of the resolver's libraries. The non-synthetic
look-alikes are built here at run time (PHASE-2.md 2.9), never committed."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import iter_records
from neonradar_graph import instances
from neonradar_graph.instances import REAL_DATABASE, Instance, InstanceRefused
from neonradar_graph.loader import LoadReport, execute_plan, load, load_records, plan_load

from .conftest import FakeDriver, record

FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"
NAMES = ("Test Holder Ltd", "Test Holder T0000002 Ltd", "Test Person")


def look_alikes() -> list[dict[str, Any]]:
    """Records that look like Companies House records (ids gbch-..., test names)."""
    return [
        record("gbch-co-T0000001", "Company", name=NAMES[0], jurisdiction="gb"),
        record("gbch-co-T0000002", "Company", name=NAMES[1], jurisdiction="gb"),
        record("gbch-psc-T0000001", "Person", name=NAMES[2]),
        record(
            "gbch-ownership-T1", "Ownership", owner="gbch-psc-T0000001", asset="gbch-co-T0000002"
        ),
    ]


def write(folder: Path, name: str, rows: list[dict[str, Any]]) -> Path:
    path = folder / f"{name}.ftm.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def no_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Never read the repository's .env in these tests."""
    for settings in (instances.RealNeo4jSettings, instances._DatabaseSetting):
        monkeypatch.setitem(settings.model_config, "env_file", tmp_path / "missing.env")
    for name in ("NEO4J_DATABASE", "NR_NEO4J_REAL_URI", "NEO4J_REAL_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def refused(driver: FakeDriver, paths: list[Path], instance: Instance) -> str:
    with pytest.raises(InstanceRefused) as caught:
        load(paths, instance=instance, driver=driver)  # type: ignore[arg-type]
    assert caught.value.exit_code == 2
    assert driver.calls == []  # before any query
    return str(caught.value)


def test_the_default_instance_refuses_non_synthetic_records_before_any_query(
    tmp_path: Path,
) -> None:
    message = refused(FakeDriver(), [write(tmp_path, "real", look_alikes())], Instance.DEFAULT)
    assert "4 record(s) or manifest(s) are not synthetic" in message
    assert not any(text in message for text in (*NAMES, "gbch-"))  # counts only
    # The driver-level functions take the database's instance and refuse the same way.
    driver = FakeDriver()
    with pytest.raises(InstanceRefused):
        load_records(driver, look_alikes(), database="neo4j")  # type: ignore[arg-type]
    assert driver.calls == []


def test_a_plan_with_real_rows_never_reaches_the_default_instance() -> None:
    plan = plan_load(look_alikes(), strict=True)
    driver = FakeDriver()
    with pytest.raises(InstanceRefused, match="do not belong to the default instance"):
        execute_plan(driver, plan, LoadReport(strict=True), database="neo4j")  # type: ignore[arg-type]
    assert driver.calls == []


def test_a_manifest_that_says_real_is_refused_too(tmp_path: Path) -> None:
    path = write(tmp_path, "records", list(iter_records(FIXTURE)))
    manifest = next(
        (Path(__file__).parents[2] / "data" / "fixtures" / "demo-mini").glob("*.manifest.json")
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data |= {"dataset": "gb_companies_house", "synthetic": False}
    data["licence"] = {"id": "OGL-UK-3.0", "attribution": None}
    (tmp_path / "records.manifest.json").write_text(json.dumps(data), encoding="utf-8")
    message = refused(FakeDriver(), [path], Instance.DEFAULT)
    assert message.startswith("1 record(s) or manifest(s) are not synthetic")


def test_the_real_instance_refuses_synthetic_records(tmp_path: Path) -> None:
    message = refused(FakeDriver(), [FIXTURE], Instance.REAL)
    assert "are synthetic or of no known dataset" in message


def test_a_mixed_load_is_refused_by_both_instances(tmp_path: Path) -> None:
    mixed = write(tmp_path, "mixed", [*iter_records(FIXTURE), *look_alikes()])
    for instance in Instance:
        refused(FakeDriver(), [mixed], instance)
    unknown = record("syn-co-0901", "Company", name="Syn Company 0901 Ltd")
    unknown["datasets"] = ["no_such_dataset"]  # no known dataset: neither instance takes it
    for instance in Instance:
        refused(FakeDriver(), [write(tmp_path, f"unknown-{instance}", [unknown])], instance)


def test_each_instance_names_its_own_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    default, real = FakeDriver(), FakeDriver()
    load([FIXTURE], instance=Instance.DEFAULT, driver=default)  # type: ignore[arg-type]
    load([write(tmp_path, "real", look_alikes())], instance=Instance.REAL, driver=real)  # type: ignore[arg-type]
    assert {database for _, _, database in default.calls} == {"neo4j"}
    assert {database for _, _, database in real.calls} == {REAL_DATABASE}
    assert (Instance.DEFAULT.database, Instance.REAL.database) == ("neo4j", "realdata")
    monkeypatch.setenv("NEO4J_DATABASE", "graph")
    assert Instance.DEFAULT.database == "graph"
    monkeypatch.setenv("NEO4J_DATABASE", REAL_DATABASE)  # never the real-data database's name
    with pytest.raises(InstanceRefused):
        _ = Instance.DEFAULT.database
    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")
    settings = Instance.REAL.settings()
    assert (settings.uri, settings.database) == (instances.REAL_URI, REAL_DATABASE)
    monkeypatch.setenv("NR_NEO4J_REAL_URI", "bolt://127.0.0.1:17688")
    assert Instance.REAL.settings().uri == "bolt://127.0.0.1:17688"


def test_importing_the_loader_needs_no_resolver_library() -> None:
    """The graph package never imports PyArrow, DuckDB or Splink (PHASE-2.md 4.2). The neo4j
    driver imports PyArrow by itself when it is installed (its optional Arrow support), so the
    subprocess blocks the three, as an image without them would, and imports every module."""
    script = textwrap.dedent(
        """
        import sys
        BLOCKED = {"pyarrow", "duckdb", "splink"}
        class Block:
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in BLOCKED:
                    raise ImportError(name)
        sys.meta_path.insert(0, Block())
        import neonradar_graph.loader, neonradar_graph.verify, neonradar_graph.instances
        print(sorted(name for name in BLOCKED if name in sys.modules))
        """
    )
    blocked = subprocess.run(  # noqa: S603 (this interpreter, a fixed script)
        [sys.executable, "-c", script], capture_output=True, text=True, check=True, timeout=120
    )
    assert blocked.stdout.strip() == "[]"
    script = (
        "import sys, neonradar_graph.loader; print(sorted({'duckdb', 'splink'} & set(sys.modules)))"
    )
    free = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=True, timeout=120
    )
    assert free.stdout.strip() == "[]"
