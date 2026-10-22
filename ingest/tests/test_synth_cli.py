"""`neonradar synth world` and `synth overlay` (PHASE-3.md M3.3 deliverables 4 and 5)."""

import hashlib
import json
import resource
from itertools import chain
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_contracts.records import iter_records, validate_batch
from neonradar_ingest.data import layout
from neonradar_ingest.synth import commands
from neonradar_ingest.synth.names import is_denied

runner = CliRunner()


def synth(*args: str | Path) -> Any:
    return runner.invoke(app, ["synth", *map(str, args)])


def cpu_seconds() -> float:
    """CPU time of this process and its finished workers: the 30-second budget measures the
    work, so a busy shared machine cannot fail the test (wall time varies with load)."""
    own, workers = (
        resource.getrusage(who) for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)
    )
    return own.ru_utime + own.ru_stime + workers.ru_utime + workers.ru_stime


def one(folder: Path, pattern: str) -> Path:
    (found,) = folder.glob(pattern)
    return found


def label_texts(folder: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((folder / "labels").iterdir())}


def test_world_and_overlay_are_deterministic_and_valid(data_env: Any, tmp_path: Path) -> None:
    """synth-demo twice with the same seed: the same record and label files, valid in strict
    mode once the base counts as part of the load (L18)."""
    worlds, overlays = [tmp_path / "w1", tmp_path / "w2"], [tmp_path / "o1", tmp_path / "o2"]
    for world, out in zip(worlds, overlays, strict=True):
        result = synth("world", "--profile", "synth-demo", "--out", world)
        assert result.exit_code == 0, result.output
        result = synth("overlay", "--profile", "synth-demo", "--base", world, "--out", out)
        assert result.exit_code == 0, result.output
    world_files = [one(w, "*.ftm.jsonl") for w in worlds]
    overlay_files = [one(o, "*.ftm.jsonl") for o in overlays]
    assert world_files[0].name == "nr_synthetic-20260701-world.ftm.jsonl"
    assert world_files[0].read_bytes() == world_files[1].read_bytes()
    assert overlay_files[0].read_bytes() == overlay_files[1].read_bytes()
    assert label_texts(overlays[0]) == label_texts(overlays[1])
    assert sorted(label_texts(overlays[0])) == [
        "manifest.json", "participants.csv", "scenario_params.jsonl", "scenarios.csv",
        "transactions.csv",
    ]  # fmt: skip

    manifest = json.loads((overlays[0] / "labels" / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(overlay_files[0].read_bytes()).hexdigest()
    assert manifest["records"] == {overlay_files[0].name: digest}
    meta = json.loads((overlays[0] / "overlay.json").read_text(encoding="utf-8"))
    assert (meta["profile"], meta["seed"], meta["split"], meta["records_sha256"]) == (
        "synth-demo", 20261103, "dev", digest,
    )  # fmt: skip
    assert meta["base"]["datasets"] == ["nr_synthetic"]
    assert meta["counts"]["scenarios"]["structuring"] == {"illicit": 3, "lookalike": 3}
    assert not (tmp_path / "LATEST").exists()  # --out writes into its folder and nothing else

    # The overlay alone names world ids; with the world, strict validation is clean.
    alone = validate_batch(iter_records(overlay_files[0]), strict=True)
    assert alone and {issue.rule for issue in alone} <= {"R4", "R8"}
    both = chain(iter_records(world_files[0]), iter_records(overlay_files[0]))
    assert validate_batch(both, strict=True) == []

    # Names: nothing on the denylist, and never the OD-12 company name.
    for path in (world_files[0], overlay_files[0]):
        for record in iter_records(path):
            for name in record["properties"].get("name", []):
                assert not is_denied(name), record["id"]


def test_a_small_world_in_the_profile_folders_runs_quickly(data_env: Any) -> None:
    """A world of 30 companies with synth-demo's other settings, into the default folders."""
    data = yaml.safe_load((data_env.profiles / "synth-demo.yaml").read_text(encoding="utf-8"))
    data["profile"] = "synth-small"
    data["sources"]["nr_synthetic"]["world"].update(name="small", companies=30, seed=3)
    (data_env.profiles / "synth-small.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    started = cpu_seconds()
    result = synth("world", "--profile", "synth-small")
    assert result.exit_code == 0, result.output
    assert one(layout.worlds_dir("small", 3), "*.ftm.jsonl").stat().st_size > 0
    result = synth("overlay", "--profile", "synth-small")
    assert result.exit_code == 0, result.output
    assert cpu_seconds() - started < 30
    overlay_id = layout.latest_overlay("synth-small")
    assert overlay_id is not None and overlay_id.startswith("ov-")
    folder = layout.overlay_dir("synth-small", overlay_id)
    assert (folder / "overlay.json").is_file() and (folder / "labels" / "manifest.json").is_file()
    assert folder.is_relative_to(data_env.cache / "synthetic")
    reports = list(layout.reports_dir("synth-small").glob("synth-*.json"))
    assert len(reports) == 2


def test_an_overlay_without_its_world_stops(data_env: Any) -> None:
    result = synth("overlay", "--profile", "synth-demo", "--seed", "4")
    assert result.exit_code == 2
    assert "no world for seed 4: run `neonradar synth world --profile synth-demo --seed 4`" in (
        result.output
    )


def test_a_holdout_seed_is_refused(
    data_env: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seeds = tmp_path / "seeds.yaml"
    seeds.write_text(yaml.safe_dump({"dev": {"seeds": [1]}, "test": {"seeds": [777]}}), "utf-8")
    monkeypatch.setattr(commands, "SEEDS_FILE", seeds)
    out = tmp_path / "out"
    result = synth("world", "--profile", "synth-demo", "--seed", "777", "--out", out)
    assert result.exit_code == 2 and "holdout seed" in result.output
    result = synth(
        "overlay", "--profile", "synth-demo", "--seed", "777", "--base", tmp_path, "--out", out
    )
    assert result.exit_code == 2 and "holdout seed" in result.output
    assert not out.exists()


def test_real_profiles_are_refused(data_env: Any) -> None:
    result = synth("overlay", "--profile", "uk-tiny")
    assert result.exit_code == 3 and "comes with M3.4" in result.output
    assert synth("world", "--profile", "uk-tiny").exit_code == 2
    assert synth("world", "--profile", "demo").exit_code == 2
    assert not (data_env.cache / "real").exists()


def test_a_real_record_in_the_base_stops_the_overlay(data_env: Any, tmp_path: Path) -> None:
    """B1: a look-alike real record passed with --base: exit 3, nothing written, no id shown."""
    base, out = tmp_path / "base", tmp_path / "out"
    base.mkdir()
    lookalike = {
        "id": "gbch-co-T0000001",
        "schema": "Company",
        "datasets": ["gb_companies_house"],
        "properties": {"name": ["Test Holder Ltd"], "jurisdiction": ["gb"]},
    }
    (base / "test.ftm.jsonl").write_text(json.dumps(lookalike) + "\n", encoding="utf-8")
    result = synth("overlay", "--profile", "synth-demo", "--base", base, "--out", out)
    assert result.exit_code == 3 and "not synthetic" in result.output
    assert "T0000001" not in result.output and "Test Holder" not in result.output
    assert not out.exists()


@pytest.mark.parametrize("folder", ["real", "spikes", "holdout", "heldout"])
def test_protected_folders_are_refused(data_env: Any, tmp_path: Path, folder: str) -> None:
    """B1 and S10: --base and --out never lie in a protected data/cache folder."""
    inside = data_env.cache / folder / "x"
    inside.mkdir(parents=True)
    result = synth("overlay", "--profile", "synth-demo", "--base", inside, "--out", tmp_path / "o")
    assert result.exit_code == 3 and "protected" in result.output
    result = synth("world", "--profile", "synth-demo", "--out", inside)
    assert result.exit_code == 3 and not list(inside.iterdir())
    elsewhere = tmp_path / "other" / "data" / "cache" / folder  # another checkout's cache
    elsewhere.mkdir(parents=True)
    assert synth("overlay", "--profile", "synth-demo", "--base", elsewhere).exit_code == 3


def test_a_base_made_from_a_holdout_seed_is_refused(
    data_env: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S10: a base whose manifest names a holdout seed (exit 2, as the seed refusal)."""
    seeds = tmp_path / "seeds.yaml"
    seeds.write_text(yaml.safe_dump({"test": {"seeds": [778]}}), encoding="utf-8")
    monkeypatch.setattr(commands, "SEEDS_FILE", seeds)
    base = tmp_path / "base"
    base.mkdir()
    (base / "w.ftm.jsonl").write_text("", encoding="utf-8")
    (base / "w.manifest.json").write_text(json.dumps({"seed": 778}), encoding="utf-8")
    result = synth("overlay", "--profile", "synth-demo", "--base", base, "--out", tmp_path / "o")
    assert result.exit_code == 2 and "holdout seed" in result.output


def mixed_case(data_env: Any, tmp_path: Path, variant: str) -> Path:
    """A protected folder spelled in another case: refused on any file system (B-1)."""
    return {
        "Real": data_env.cache / "Real" / "x",
        "HOLDOUT": data_env.cache / "HOLDOUT" / "x",
        "Data/Cache/real": tmp_path / "Data" / "Cache" / "real" / "x",
    }[variant]


@pytest.mark.parametrize("variant", ["Real", "HOLDOUT", "Data/Cache/real"])
def test_protected_folders_are_refused_in_any_case(
    data_env: Any, tmp_path: Path, variant: str
) -> None:
    folder = mixed_case(data_env, tmp_path, variant)
    result = synth("world", "--profile", "synth-demo", "--out", folder)
    assert result.exit_code == 3 and not folder.exists()
    result = synth("overlay", "--profile", "synth-demo", "--base", tmp_path, "--out", folder)
    assert result.exit_code == 3 and not folder.exists()
    folder.mkdir(parents=True)
    result = synth("overlay", "--profile", "synth-demo", "--base", folder, "--out", tmp_path / "o")
    assert result.exit_code == 3 and not (tmp_path / "o").exists()


SYNTHETIC = {"id": "syn-w-co-000001", "schema": "Company", "datasets": ["nr_synthetic"],
             "properties": {"name": ["Test Holder Ltd"], "jurisdiction": ["gb"]}}  # fmt: skip


@pytest.mark.parametrize("linked", ["w.ftm.jsonl", "w.manifest.json"])
def test_a_base_file_linked_into_a_protected_folder_is_refused(
    data_env: Any, tmp_path: Path, linked: str
) -> None:
    """S-1: a record file or manifest symlinked into the real-data cache is never opened."""
    protected = data_env.cache / "real"  # a tmp folder of the test, never the real cache
    protected.mkdir(parents=True)
    (protected / linked).write_text(json.dumps(SYNTHETIC) + "\n", encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    (base / "w.ftm.jsonl").write_text(json.dumps(SYNTHETIC) + "\n", encoding="utf-8")
    (base / linked).unlink(missing_ok=True)
    (base / linked).symlink_to(protected / linked)
    result = synth("overlay", "--profile", "synth-demo", "--base", base, "--out", tmp_path / "o")
    assert result.exit_code == 3 and "protected" in result.output
    assert not (tmp_path / "o").exists()


def test_a_synthetic_dataset_record_with_another_id_is_refused(
    data_env: Any, tmp_path: Path
) -> None:
    """S-2: a record claiming nr_synthetic must carry a syn- id."""
    base = tmp_path / "base"
    base.mkdir()
    claimed = {**SYNTHETIC, "id": "gbch-co-T0000002"}
    (base / "w.ftm.jsonl").write_text(json.dumps(claimed) + "\n", encoding="utf-8")
    result = synth("overlay", "--profile", "synth-demo", "--base", base, "--out", tmp_path / "o")
    assert result.exit_code == 3 and "not synthetic" in result.output
    assert "T0000002" not in result.output and not (tmp_path / "o").exists()


def resolved_overlay(data_env: Any, tmp_path: Path, link_run: bool) -> Any:
    """synth overlay of a resolving copy of synth-demo, optionally with a run linked elsewhere."""
    data = yaml.safe_load((data_env.profiles / "synth-demo.yaml").read_text(encoding="utf-8"))
    data["profile"] = "synth-resolved"
    data["resolution"] = {"enabled": True, "config": "resolve/config/er.yaml"}
    (data_env.profiles / "synth-resolved.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    if link_run:
        run_id = "er-20261022T000000-abcd"
        protected = data_env.cache / "real" / "resolution" / run_id  # the test's own tmp copy
        protected.mkdir(parents=True)
        (protected / "canonical.csv").write_text("record_id,canonical_id\n", encoding="utf-8")
        runs = layout.resolution_dir("synth-resolved", run_id).parent
        runs.mkdir(parents=True)
        (runs / run_id).symlink_to(protected)
        (runs / layout.LATEST).write_text(run_id + "\n", encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    (base / "w.ftm.jsonl").write_text(json.dumps(SYNTHETIC) + "\n", encoding="utf-8")
    return synth("overlay", "--profile", "synth-resolved", "--base", base, "--out", tmp_path / "o")


def test_a_resolving_profile_without_a_resolution_run_stops(data_env: Any, tmp_path: Path) -> None:
    """#78 review: with resolution enabled, no run or no canonical.csv is exit 3."""
    result = resolved_overlay(data_env, tmp_path, link_run=False)
    assert result.exit_code == 3 and "no resolution run" in result.output
    assert not (tmp_path / "o").exists()


def test_a_resolution_run_linked_into_a_protected_folder_is_refused(
    data_env: Any, tmp_path: Path
) -> None:
    """Delta review of #72: the resolution run's canonical.csv goes through the same check."""
    result = resolved_overlay(data_env, tmp_path, link_run=True)
    assert result.exit_code == 3 and "the resolution run" in result.output
    assert not (tmp_path / "o").exists()
