import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest import spikes

runner = CliRunner()


def _company(rid: str, name: str, **extra: list[str]) -> str:
    props = {"name": [name], "jurisdiction": ["gb"], "incorporationDate": ["2001-05-04"], **extra}
    record = {
        "id": rid,
        "schema": "Company",
        "datasets": ["gb_companies_house"],
        "properties": props,
    }
    return json.dumps(record) + "\n"


def test_synthetic_join_prints_counts_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spikes, "SPIKE_ROOT", tmp_path / "spikes")
    stale = tmp_path / "spikes" / "synthetic_join" / "labels"
    stale.mkdir(parents=True)
    (stale / "old.csv").write_text("# synthetic: true\n")
    entities = tmp_path / "in.ftm.jsonl"  # the second record breaks R3 (unknown property)
    entities.write_text(
        _company("gbch-co-T0000001", "Test Holder Ltd")
        + _company("gbch-co-T0000002", "Secret Name Ltd", colour=["red"])
    )
    args = ["spike", "synthetic-join", "--entities", str(entities), "--seed", "3"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "holders: 2" in result.output and "payments in the scenario: 4" in result.output
    assert "1 in the input (rules: R3)" in result.output
    assert "scenario 0" in result.output and result.output.rstrip().endswith("OK")
    for secret in ("Test Holder", "Secret Name", "gbch-"):  # never an input name or id
        assert secret not in result.output
    folder = tmp_path / "spikes" / "synthetic_join"
    assert len(list(folder.glob("*.ftm.jsonl"))) == 1
    assert {p.name for p in (folder / "labels").iterdir()} == {"transactions.csv", "scenarios.csv"}
    manifest = json.loads(next(folder.glob("*.manifest.json")).read_text())
    assert manifest["seed"] == 3 and manifest["producer"]["name"] == "neonradar_ingest.synth"
    assert {"faker", "numpy", "followthemoney"} <= set(manifest["dependencies"])
