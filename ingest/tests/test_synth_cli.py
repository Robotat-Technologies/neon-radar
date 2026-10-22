"""`neonradar synth world` and `synth overlay` (PHASE-3.md M3.3 deliverables 4 and 5)."""

import hashlib
import json
import time
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
    started = time.monotonic()
    result = synth("world", "--profile", "synth-small")
    assert result.exit_code == 0, result.output
    assert one(layout.worlds_dir("small", 3), "*.ftm.jsonl").stat().st_size > 0
    result = synth("overlay", "--profile", "synth-small")
    assert result.exit_code == 0, result.output
    assert time.monotonic() - started < 30
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
