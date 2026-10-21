import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest import spikes

runner = CliRunner()


def test_synthetic_join_prints_counts_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spikes, "SPIKE_ROOT", tmp_path / "spikes")
    record = {
        "id": "gbch-co-T0000001", "schema": "Company", "datasets": ["gb_companies_house"],
        "properties": {"name": ["Test Holder Ltd"], "jurisdiction": ["gb"]},
    }  # fmt: skip
    entities = tmp_path / "in.ftm.jsonl"
    entities.write_text(json.dumps(record) + "\n")
    result = runner.invoke(app, ["spike", "synthetic-join", "--entities", str(entities)])
    assert result.exit_code == 0, result.output
    assert "holders: 1" in result.output and "payments in the scenario: 4" in result.output
    assert "scenario 0" in result.output and result.output.rstrip().endswith("OK")
    assert "Test Holder" not in result.output and "gbch-" not in result.output
    folder = tmp_path / "spikes" / "synthetic_join"
    assert len(list(folder.glob("*.ftm.jsonl"))) == 1
    assert {p.name for p in (folder / "labels").iterdir()} == {"transactions.csv", "scenarios.csv"}
