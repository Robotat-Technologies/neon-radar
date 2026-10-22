"""Builders, the swap of record folders and the nr_synthetic builder (M2.2 deliverables 6, 12)."""

import json
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import validate_files
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.build import build_dataset
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.sources import BuildContext, Builder, BuildError, BuildResult


def record(record_id: str, name: str) -> dict[str, Any]:
    nr = {"v": "1.0", "synthetic": True}
    props = {"name": [name]}
    return {"id": record_id, "schema": "Company", "datasets": ["nr_synthetic"], "properties": props,
            "nr": nr}  # fmt: skip


def writer(*records: dict[str, Any], file: str = "out.ftm.jsonl") -> Builder:
    def build(profile: Any, context: BuildContext) -> BuildResult:
        lines = "".join(json.dumps(r) + "\n" for r in records)
        (context.out_dir / file).write_text(lines, encoding="utf-8")
        return BuildResult(counts={"records": len(records)})

    return Builder("gleif_lei", build)


def validate(paths: list[Path]) -> int:
    return len(validate_files(paths, strict=True)[1])


def run(builder: Builder, run_id: str) -> BuildResult:
    profile = load_profile("uk-tiny")
    return build_dataset(builder, profile, load_project(), validate, run_id=run_id)


def test_a_successful_build_replaces_the_folder_and_leaves_no_stale_file(data_env: Any) -> None:
    final = layout.records_dir("uk-tiny", "gleif_lei")
    run(writer(record("syn-co-1", "A Ltd"), file="old.ftm.jsonl"), "build-1")
    assert [p.name for p in final.iterdir()] == ["old.ftm.jsonl"]
    result = run(writer(record("syn-co-2", "B Ltd")), "build-2")
    assert result.counts == {"records": 1}
    assert [p.name for p in final.iterdir()] == ["out.ftm.jsonl"]
    assert [p.name for p in final.parent.iterdir()] == ["gleif_lei"]  # no .tmp or .old left


def test_a_failed_validation_leaves_the_old_folder_in_place(data_env: Any) -> None:
    final = layout.records_dir("uk-tiny", "gleif_lei")
    run(writer(record("syn-co-1", "A Ltd")), "build-1")
    broken = record("syn-co-2", "B Ltd") | {"properties": {"name": ["B"], "parent": ["syn-x-9"]}}
    with pytest.raises(BuildError, match="issue") as failed:
        run(writer(broken), "build-2")
    assert (failed.value.rule, failed.value.counts_only) == ("C1", True)
    assert "syn-co-1" in (final / "out.ftm.jsonl").read_text(encoding="utf-8")
    assert [p.name for p in final.parent.iterdir()] == ["gleif_lei"]


def test_a_builder_that_raises_leaves_the_old_folder_in_place(data_env: Any) -> None:
    final = layout.records_dir("uk-tiny", "gleif_lei")
    run(writer(record("syn-co-1", "A Ltd")), "build-1")

    def fail(profile: Any, context: BuildContext) -> BuildResult:
        (context.out_dir / "half.ftm.jsonl").write_text("{}\n", encoding="utf-8")
        raise RuntimeError("stopped")

    with pytest.raises(RuntimeError):
        run(Builder("gleif_lei", fail), "build-2")
    assert [p.name for p in final.iterdir()] == ["out.ftm.jsonl"]


def test_the_context_carries_the_build_settings(data_env: Any) -> None:
    seen: list[BuildContext] = []

    def build(profile: Any, context: BuildContext) -> BuildResult:
        seen.append(context)
        return BuildResult()

    profile = load_profile("uk-tiny")
    builder = Builder("gleif_lei", build, steps=("a", "b"))
    build_dataset(builder, profile, load_project(), validate, run_id="build-3", steps=("b",),
                  keep_work=True, accept_size=True)  # fmt: skip
    context = seen[0]
    assert (context.run_id, context.steps, context.keep_work, context.accept_size) == (
        "build-3", ("b",), True, True,
    )  # fmt: skip
    assert context.work_dir == layout.work_dir(profile, "gleif_lei")
    assert context.out_dir.parent == layout.records_dir(profile, "gleif_lei").parent
    assert not (data_env.cache / "real/records/uk-tiny").exists()  # nothing written, nothing left


def test_the_synthetic_builder_validates_the_fixtures_and_copies_nothing(data_env: Any) -> None:
    sources.load_plugins()
    builder = sources.builder_for("nr_synthetic")
    assert builder is not None
    profile = load_profile("demo")
    result = build_dataset(builder, profile, load_project(), validate, run_id="build-4")
    assert result.counts["fixture_folders"] == 2  # demo-mini and er-bench (M2.9)
    assert result.counts["records"] == sum(result.counts["schemas_by_value"].values()) > 100
    assert not [path for path in data_env.cache.rglob("*") if path.is_file()]


def test_the_synthetic_builder_stops_on_an_empty_or_broken_fixture(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from neonradar_ingest.data import synthetic

    sources.load_plugins()
    monkeypatch.setattr(synthetic, "REPO_ROOT", tmp_path)
    (tmp_path / "data/fixtures/demo-mini").mkdir(parents=True)
    profile = load_profile("demo")
    context = BuildContext(load_project(), "build-5", tmp_path / "out", tmp_path / "work")
    with pytest.raises(BuildError, match=r"holds no \.ftm\.jsonl file"):
        synthetic.build(profile, context)
    broken = record("syn-co-1", "A Ltd") | {"properties": {"name": ["A"], "parent": ["syn-x"]}}
    path = tmp_path / "data/fixtures/demo-mini/x.ftm.jsonl"
    path.write_text(json.dumps(broken) + "\n", encoding="utf-8")
    with pytest.raises(BuildError, match="1 C1 issue"):
        synthetic.build(profile, context)


def test_the_registry_knows_only_the_data_manager_datasets() -> None:
    with pytest.raises(ValueError, match="not a dataset"):
        sources.register_builder(Builder("gleif", lambda p, c: BuildResult()))
    with pytest.raises(ValueError, match="not a dataset"):
        sources.register_source(sources.SourceSpec("gleif", lambda client: []))
    assert set(sources.AVAILABLE_IN) == set(sources.DATASETS)


def test_a_failed_swap_restores_the_previous_records(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = layout.records_dir("uk-tiny", "gleif_lei")
    run(writer(record("syn-co-1", "A Ltd")), "build-1")
    real_rename = Path.rename

    def rename(self: Path, target: Any) -> Path:
        if self.name.endswith(".tmp"):
            raise OSError("synthetic rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(OSError, match="synthetic rename failure"):
        run(writer(record("syn-co-2", "B Ltd")), "build-2")
    assert "syn-co-1" in (final / "out.ftm.jsonl").read_text(encoding="utf-8")
    assert [p.name for p in final.parent.iterdir()] == ["gleif_lei"]
