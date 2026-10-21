"""Retention, purge and status on a temporary tree (PHASE-2.md M2.2 deliverables 8 and 11)."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from neonradar_ingest.data import layout, purge, retention, status
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.purge import Scope

NOW = time.time()
DAY = 86_400


def put(path: Path, days_old: float = 0, size: int = 10) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    os.utime(path, (NOW - days_old * DAY, NOW - days_old * DAY))
    return path


@pytest.fixture
def tree(data_env: Any) -> dict[str, Path]:
    """One file in every kind of folder the purge knows, all synthetic bytes."""
    real, cache = data_env.cache / "real", data_env.cache
    return {
        "psc": put(real / "sources/gb_companies_house/psc/2026-10-18/psc.zip", 31),
        "companies": put(real / "sources/gb_companies_house/companies/2026-10-01/c.zip", 2),
        "lists": put(real / "sources/us_ofac_sdn/main/2026-10-18/sdn.xml", 1),
        "records": put(real / "records/uk-tiny/gb_companies_house/a.ftm.jsonl", 1),
        "work": put(real / "work/uk-tiny/gb_companies_house/slice.csv", 1),
        "other_profile": put(real / "records/uk-sample/gb_companies_house/b.ftm.jsonl", 1),
        "officers": put(real / "api/gb_companies_house/officers/page.json", 1),
        "parliament": put(real / "api/gb_parliament_members/page.json", 1),
        "resolution": put(real / "resolution/uk-tiny/er-1/canonical.csv", 1),
        "labels": put(real / "labels/uk-tiny/er-1/sample.jsonl", 45),
        "decisions": put(real / "decisions.jsonl", 1),
        "logs": put(real / "logs/ingest-build-1.log", 40),
        "spike": put(cache / "spikes/gleif/out.ftm.jsonl", 8),
        "spill": put(real / "duckdb-tmp/er-2/spill.tmp", 0),
        "synthetic_spill": put(cache / "synthetic/duckdb-tmp/er-3/spill.tmp", 0),
        "synthetic_records": put(cache / "synthetic/records/demo/nr_synthetic/x.ftm.jsonl", 90),
        "report": put(cache / "reports/uk-tiny/data-fetch-1.json", 90),
    }


def left(tree: dict[str, Path]) -> set[str]:
    return {name for name, path in tree.items() if path.exists()}


def test_retention_follows_the_three_day_settings_and_spill_folders(
    data_env: Any, tree: dict[str, Path]
) -> None:
    data_env.write_project(real_data_days=30, label_days=60, spike_cache_days=7)
    found = retention.expired(load_project(), NOW)
    assert found == sorted(
        [tree["psc"], tree["logs"], tree["spike"], tree["spill"].parent,
         tree["synthetic_spill"].parent]
    )  # fmt: skip
    data_env.write_project(real_data_days=50, label_days=40, spike_cache_days=10)
    found = retention.expired(load_project(), NOW)
    assert tree["labels"] in found and tree["psc"] not in found and tree["spike"] not in found


def test_a_running_spill_folder_is_not_a_leftover(data_env: Any, tree: dict[str, Path]) -> None:
    with retention.spill_dir("uk-tiny", "er-9") as folder:
        assert folder == layout.duckdb_tmp_dir("uk-tiny", "er-9")
        assert folder not in retention.leftover_spill_dirs()
        put(folder / "spill.tmp")
    assert not folder.exists()  # deleted when the run ends
    finished = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"],
                              capture_output=True, text=True, check=True)  # fmt: skip
    put(layout.duckdb_tmp_dir("demo", "er-8") / "run.pid").write_text(finished.stdout)
    assert layout.duckdb_tmp_dir("demo", "er-8") in retention.leftover_spill_dirs()


@pytest.mark.parametrize(
    ("scope", "options", "deleted"),
    [
        (Scope.DATASET, {"dataset": "gb_companies_house"},
         {"psc", "companies", "records", "work", "other_profile", "officers"}),
        (Scope.DATASET, {"dataset": "gb_parliament_members"}, {"parliament"}),
        (Scope.PROFILE, {"profile": "uk-tiny"}, {"records", "work", "resolution", "labels"}),
        (Scope.PROFILE, {"profile": "demo"}, {"synthetic_records"}),
        (Scope.LABELS, {}, {"labels"}),
        (Scope.DECISIONS, {}, {"decisions"}),
        (Scope.LOGS, {}, {"logs"}),
        (Scope.EXPIRED, {}, {"psc", "logs", "labels", "spike", "spill", "synthetic_spill"}),
    ],
)  # fmt: skip
def test_purge_by_scope(
    data_env: Any, tree: dict[str, Path], scope: Scope, options: dict[str, Any], deleted: set[str]
) -> None:
    if "profile" in options:
        options = {"profile": load_profile(options["profile"])}
    paths = purge.targets(scope, load_project(), now=NOW, **options)
    result = purge.delete(paths)
    assert left(tree) == set(tree) - deleted
    assert (result.files, result.bytes) == (len(deleted), 10 * len(deleted))


def test_purge_all_real_leaves_nothing_real(data_env: Any, tree: dict[str, Path]) -> None:
    result = purge.delete(purge.targets(Scope.ALL_REAL, load_project()))
    assert left(tree) == {"synthetic_spill", "synthetic_records", "report"}
    assert not (data_env.cache / "real").exists() and not (data_env.cache / "spikes").exists()
    assert result.files == len(tree) - 3


def test_purge_through_a_linked_real_folder_empties_its_target(
    data_env: Any, tmp_path: Path
) -> None:
    volume = tmp_path / "encrypted-volume"
    put(volume / "sources/x/main/1/a.zip")
    (volume / "elsewhere").symlink_to(tmp_path / "outside", target_is_directory=True)
    put(tmp_path / "outside/keep.txt")
    data_env.cache.mkdir(parents=True)
    (data_env.cache / "real").symlink_to(volume, target_is_directory=True)
    result = purge.delete(purge.targets(Scope.ALL_REAL, load_project()))
    assert result.files == 2  # the file and the link inside, never the link's target
    assert list(volume.iterdir()) == [] and (tmp_path / "outside/keep.txt").exists()
    assert (data_env.cache / "real").is_symlink()


def test_purge_refuses_paths_outside_the_cache(data_env: Any, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside"):
        purge.delete([tmp_path / "project.yaml"])
    assert (tmp_path / "project.yaml").exists()


def test_status_counts_without_reading_contents(data_env: Any, tree: dict[str, Path]) -> None:
    put(tree["lists"].parent / "big.xml.part", 1)
    versions = {f"{v.dataset}/{v.product}/{v.version}": v for v in status.downloads(load_project())}
    assert sorted(versions) == [
        "gb_companies_house/companies/2026-10-01",
        "gb_companies_house/psc/2026-10-18",
        "us_ofac_sdn/main/2026-10-18",
    ]
    psc, lists = (
        versions["gb_companies_house/psc/2026-10-18"],
        versions["us_ofac_sdn/main/2026-10-18"],
    )
    assert (psc.files, psc.bytes, psc.age_days, psc.past_retention) == (1, 10, 31, True)
    assert (lists.files, lists.partial, lists.past_retention) == (2, 1, False)
    tiny = status.profile_status(load_profile("uk-tiny"))
    assert (tiny.record_folders, tiny.record_files, tiny.resolution_runs, tiny.label_files) == (
        1, 1, 1, 1,
    )  # fmt: skip
    assert status.spill_leftovers() == {"real": 1, "synthetic": 1}
