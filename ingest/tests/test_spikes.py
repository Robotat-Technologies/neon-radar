import json
import os
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from neonradar_contracts.records import Manifest, Source, manifest_path, validate_files
from neonradar_ingest import spikes


def test_entity_record_uses_value_entity_and_nfc() -> None:
    props = {"name": ["Café Example Ltd"], "jurisdiction": ["GB"], "alias": [None, ""]}
    record = spikes.entity_record("Company", "syn-co-0001", "nr_synthetic", props)
    assert record["datasets"] == ["nr_synthetic"]
    assert record["properties"] == {"name": ["Café Example Ltd"], "jurisdiction": ["gb"]}


def test_writes_records_and_a_manifest_in_the_spike_folder(tmp_path: Path) -> None:
    assert Path(__file__).resolve().parents[2] / "data/cache/spikes" == spikes.SPIKE_ROOT
    record = spikes.entity_record("Company", "syn-co-0001", "nr_synthetic", {"name": ["A Ltd"]})
    record["nr"] = {"v": "1.0", "synthetic": True}
    source = Source(urls=["https://api.example.test/"], retrieved_at=spikes.utc_timestamp())
    options = {"source": source, "skipped": {"Vessel": 1}, "notes": ["a note"], "root": tmp_path}
    path = spikes.write_output([record], "example", dataset="nr_synthetic", part="one", **options)
    assert path.parent == tmp_path / "example" and path.name.endswith("-one.ftm.jsonl")
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [record]
    manifest = Manifest.model_validate_json(manifest_path(path).read_text(encoding="utf-8"))
    assert manifest.producer.name == "neonradar_ingest.sources.example"
    assert (manifest.counts.by_schema, manifest.counts.skipped) == ({"Company": 1}, {"Vessel": 1})
    assert (manifest.source, manifest.notes) == (source, ["a note"])
    assert validate_files([path], strict=True)[1] == []


@pytest.mark.parametrize(
    ("spike", "dataset", "part"),
    [("../x", "nr_synthetic", "a"), ("x", "nr_synthetic", "a/b"), ("x", "no_such", "a")],
)
def test_write_output_refuses_bad_names_before_writing(
    tmp_path: Path, spike: str, dataset: str, part: str
) -> None:
    with pytest.raises(ValueError, match=r"must be letters|not in contracts/datasets\.yaml"):
        spikes.write_output([], spike, dataset=dataset, part=part, root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_write_output_leaves_no_record_file_without_a_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):  # a negative skipped count fails the manifest
        spikes.write_output(
            [], "x", dataset="nr_synthetic", part="a", skipped={"Vessel": -1}, root=tmp_path
        )
    assert list((tmp_path / "x").iterdir()) == []


def test_cache_days_reads_project_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project.yaml"
    project.write_text("access:\n  spike_cache_days: 3\n", encoding="utf-8")
    monkeypatch.setattr(spikes, "PROJECT_FILE", project)
    assert spikes.cache_days() == 3


@pytest.mark.parametrize("value", ["TODO", "-1", "true", "2.5"])
def test_cache_days_refuses_anything_but_whole_days(tmp_path: Path, value: str) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(f"access:\n  spike_cache_days: {value}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a whole number of days"):
        spikes.cache_days(project)


def touch(path: Path, age_days: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (time.time() - age_days * 86_400,) * 2)
    return path


def test_clean_expired_deletes_only_old_files_and_empty_folders(tmp_path: Path) -> None:
    old, new = touch(tmp_path / "gleif" / "old.json", 8), touch(tmp_path / "gleif" / "new.json", 1)
    deep = touch(tmp_path / "icij" / "deep" / "old.csv", 30)
    outside = touch(tmp_path.parent / f"{tmp_path.name}-outside" / "old.txt", 30)
    link = tmp_path / "link"
    link.symlink_to(outside.parent, target_is_directory=True)
    os.utime(link, (0, 0), follow_symlinks=False)
    assert spikes.clean_expired(7, tmp_path) == sorted([old, deep, link])
    assert new.exists() and outside.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["gleif"]
    assert spikes.clean_expired(7, tmp_path / "missing") == []
