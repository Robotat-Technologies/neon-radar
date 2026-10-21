"""The data manager's folders (PHASE-2.md 4.5, M2.2 deliverable 4)."""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import load_profile

RUN = "er-20261102T091500-3b7e"
# Every function that takes a profile, called for one.
PER_PROFILE: dict[str, Callable[[Any], Path]] = {
    "records_dir": lambda p: layout.records_dir(p, "nr_synthetic"),
    "work_dir": lambda p: layout.work_dir(p, "nr_synthetic"),
    "resolution_dir": lambda p: layout.resolution_dir(p, RUN),
    "labels_dir": lambda p: layout.labels_dir(p, RUN),
    "decisions_file": layout.decisions_file,
    "duckdb_tmp_dir": lambda p: layout.duckdb_tmp_dir(p, RUN),
    "reports_dir": layout.reports_dir,
}
PSEUDO = ("resolution_dir", "labels_dir", "decisions_file", "duckdb_tmp_dir", "reports_dir")


@pytest.mark.parametrize("function", sorted(PER_PROFILE))
@pytest.mark.parametrize("as_name", [True, False])
def test_a_synthetic_profile_never_gets_a_real_path(
    data_env: Any, function: str, as_name: bool
) -> None:
    profile = "demo" if as_name else load_profile("demo")
    path = PER_PROFILE[function](profile)
    assert path.is_relative_to(data_env.cache)
    assert not path.is_relative_to(data_env.cache / "real")
    if function != "reports_dir":
        assert path.is_relative_to(data_env.cache / "synthetic")


@pytest.mark.parametrize("function", sorted(PER_PROFILE))
def test_a_real_profile_gets_real_paths(data_env: Any, function: str) -> None:
    path = PER_PROFILE[function]("uk-tiny")
    expected = data_env.cache / ("reports" if function == "reports_dir" else "real")
    assert path.is_relative_to(expected)


@pytest.mark.parametrize("pseudo", ["er-bench-small", "er-bench-large"])
def test_the_benchmark_pseudo_profiles_are_synthetic(data_env: Any, pseudo: str) -> None:
    for function in PSEUDO:
        assert not PER_PROFILE[function](pseudo).is_relative_to(data_env.cache / "real")
    with pytest.raises(ValueError, match="only has resolution"):
        layout.records_dir(pseudo, "nr_synthetic")


def test_the_named_paths(data_env: Any) -> None:
    cache = data_env.cache
    assert layout.sources_dir("gb_companies_house", "psc", "2026-10-18") == (
        cache / "real/sources/gb_companies_house/psc/2026-10-18"
    )
    assert layout.records_dir("uk-tiny", "gleif_lei") == cache / "real/records/uk-tiny/gleif_lei"
    assert layout.resolution_dir("demo", RUN) == cache / f"synthetic/resolution/demo/{RUN}"
    assert layout.labels_dir("uk-sample", RUN) == cache / f"real/labels/uk-sample/{RUN}"
    assert layout.decisions_file("uk-sample") == cache / "real/decisions.jsonl"
    assert layout.duckdb_tmp_dir("uk-tiny", RUN) == cache / f"real/duckdb-tmp/{RUN}"
    assert layout.reports_dir("uk-tiny") == cache / "reports/uk-tiny"
    assert layout.logs_dir() == cache / "real/logs"
    assert layout.officer_cache_dir() == cache / "real/api/gb_companies_house/officers"
    assert layout.parliament_cache_dir() == cache / "real/api/gb_parliament_members"
    assert layout.bench_dir("small") == cache / "synthetic/er-bench-small"
    assert layout.real_decisions_file() == layout.decisions_file("uk-tiny")
    assert layout.spill_roots() == (cache / "real/duckdb-tmp", cache / "synthetic/duckdb-tmp")


def test_latest_run(data_env: Any) -> None:
    assert layout.latest_run("demo") is None
    latest = data_env.cache / "synthetic/resolution/demo/LATEST"
    latest.parent.mkdir(parents=True)
    latest.write_text(f"{RUN}\n", encoding="utf-8")
    assert layout.latest_run("demo") == RUN
    latest.write_text("../../real\n", encoding="utf-8")
    with pytest.raises(ValueError, match="run id"):
        layout.latest_run("demo")


@pytest.mark.parametrize(
    "call",
    [
        lambda: layout.sources_dir("gb_companies_house", "..", "x"),
        lambda: layout.sources_dir("gb_companies_house", "psc", "a/b"),
        lambda: layout.sources_dir("not_a_dataset", "main", "1"),
        lambda: layout.records_dir("../demo", "nr_synthetic"),
        lambda: layout.resolution_dir("demo", ".hidden"),
        lambda: layout.bench_dir("../x"),
    ],
)
def test_unsafe_parts_are_refused(data_env: Any, call: Callable[[], Path]) -> None:
    with pytest.raises(ValueError):
        call()


def test_run_ids_and_dataset_and_profile_folders(data_env: Any) -> None:
    assert re.fullmatch(r"build-\d{8}T\d{6}-[0-9a-f]{4}", layout.new_run_id("build"))
    real = data_env.cache / "real"
    for kind in ("records", "work"):
        (real / kind / "uk-tiny" / "gb_companies_house").mkdir(parents=True)
    assert layout.dataset_dirs("gb_companies_house") == [
        real / "sources/gb_companies_house",
        real / "records/uk-tiny/gb_companies_house",
        real / "work/uk-tiny/gb_companies_house",
        real / "api/gb_companies_house/officers",
    ]
    assert layout.dataset_dirs("gb_parliament_members")[-1] == layout.parliament_cache_dir()
    assert layout.profile_dirs("demo") == [
        data_env.cache / "synthetic" / kind / "demo"
        for kind in ("records", "work", "resolution", "labels")
    ]


def test_a_real_dataset_always_lands_under_real(data_env: Any) -> None:
    """Even for a profile that claims to be synthetic (the model refuses such a file)."""
    from neonradar_ingest.data.profiles import Profile, SourceConfig

    sources = {"gleif_lei": SourceConfig(enabled=True)}
    disguised = Profile.model_construct(profile="disguised", real_data=False, sources=sources)
    for function in (layout.records_dir, layout.work_dir):
        path = function(disguised, "gleif_lei")
        assert path.is_relative_to(data_env.cache / "real")
        assert not function(disguised, "nr_synthetic").is_relative_to(data_env.cache / "real")
    assert layout.reports_dir(layout.ALL_PROFILES) == data_env.cache / "reports" / "all-profiles"
