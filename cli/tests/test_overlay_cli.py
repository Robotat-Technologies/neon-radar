"""`neonradar synth overlay` on a real profile (PHASE-3.md M3.4 deliverable 3, 7.7 rule 1).

It stops with exit 3 before any record is read while the machine is not approved, and while the
profile is not in `access.real_overlay_profiles` (a test project file through `NR_PROJECT_FILE`),
so no acceptance command ever touches real data (G9). With both open, a profile of look-alike
records built here gets its overlay under its real-data folder, and the command prints counts
only. Every folder lives in the `data_env` tmp tree."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import layout
from neonradar_ingest.synth import commands

runner = CliRunner()
LOOK_ALIKES = [  # names already in the graph and detect tests
    ("gbch-co-T0000001", "Test Holder Ltd"),
    ("gbch-co-T0000005", "Test Trading Ltd"),
]


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every base file `synth overlay` opens."""
    opened: list[Path] = []
    original = commands.BaseIndex.read

    def read(self: commands.BaseIndex, files: Any) -> Any:
        files = list(files)
        opened.extend(files)
        return original(self, files)

    monkeypatch.setattr(commands.BaseIndex, "read", read)
    return opened


def overlay(profile: str) -> Any:
    return runner.invoke(app, ["synth", "overlay", "--profile", profile])


def test_a_real_overlay_stops_with_exit_3_before_a_record_is_read(
    data_env: Any, reads: list[Path]
) -> None:
    data_env.write_project(real_data_profiles=["uk-tiny"], data_protection_filed=True)
    result = overlay("uk-tiny")  # the machine is not approved
    assert result.exit_code == 3 and "NR_REAL_DATA_MACHINE is not approved" in result.output
    data_env.allow_real("uk-tiny")  # approved, but not in access.real_overlay_profiles
    result = overlay("uk-tiny")
    assert result.exit_code == 3 and "not in access.real_overlay_profiles" in result.output
    assert reads == [] and not (data_env.cache / "real").exists()


def test_a_listed_real_profile_gets_its_overlay_with_counts_only(
    data_env: Any, reads: list[Path]
) -> None:
    data = yaml.safe_load((data_env.profiles / "uk-tiny.yaml").read_text(encoding="utf-8"))
    data |= {"profile": "uk-test", "resolution": {"enabled": False}}
    data["overlay"] |= {"end": "2025-02-01", "illicit": 0, "lookalikes": 0}
    data["overlay"]["typologies"] = ["circular_flow"]
    (data_env.profiles / "uk-test.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    folder = layout.records_dir("uk-test", "gb_companies_house")
    folder.mkdir(parents=True)
    records = [
        {"id": rid, "schema": "Company", "datasets": ["gb_companies_house"],
         "properties": {"name": [name], "jurisdiction": ["gb"], "status": ["active"]}}
        for rid, name in LOOK_ALIKES
    ]  # fmt: skip
    lines = "".join(json.dumps(record) + "\n" for record in records)
    (folder / "look-alikes.ftm.jsonl").write_text(lines, encoding="utf-8")
    data_env.allow_real("uk-test", real_overlay_profiles=["uk-test"])
    result = overlay("uk-test")
    assert result.exit_code == 0, result.output
    printed = json.loads(result.output)
    assert (printed["eligible_organisations"], printed["active_organisations"]) == (2, 2)
    assert "T000000" not in result.output and "Test " not in result.output
    assert reads == [folder / "look-alikes.ftm.jsonl"]
    overlay_id = layout.latest_overlay("uk-test")
    assert overlay_id is not None
    written = layout.overlay_dir("uk-test", overlay_id)
    assert written.is_relative_to(data_env.cache / "real" / "overlay" / "uk-test")
    assert (written / "overlay.json").is_file() and (written / "labels").is_dir()
