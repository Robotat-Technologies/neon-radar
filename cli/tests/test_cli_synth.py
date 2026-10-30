import json
from pathlib import Path

from typer.testing import CliRunner

from neonradar_cli.main import app

runner = CliRunner()


def _record(rid: str, dataset: str, name: str) -> str:
    record = {"id": rid, "schema": "Company", "datasets": [dataset], "properties": {"name": [name]}}
    if dataset == "nr_synthetic":
        record["nr"] = {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"}
    return json.dumps(record, ensure_ascii=False) + "\n"


def test_demo_mini_writes_records_manifest_and_labels(tmp_path: Path) -> None:
    result = runner.invoke(app, ["synth", "demo-mini", "--seed", "5", "--out", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "records, seed 5" in result.output and "  Payment: " in result.output
    assert len(list(tmp_path.glob("*.ftm.jsonl"))) == len(list(tmp_path.glob("*.manifest.json")))
    assert {p.name for p in (tmp_path / "labels").iterdir()} == {
        "transactions.csv",
        "scenarios.csv",
    }


def test_check_names_lists_names_and_passes(tmp_path: Path) -> None:
    synthetic = tmp_path / "syn.ftm.jsonl"
    synthetic.write_text(_record("syn-co-0001", "nr_synthetic", "Ochre Tarn Freight Ltd"))
    result = runner.invoke(app, ["synth", "check-names", str(synthetic)])
    assert result.exit_code == 0, result.output
    assert "syn-co-0001\tOchre Tarn Freight Ltd" in result.output
    assert "1 names; 0 denylisted; 0 equal a name in 0 other file(s)" in result.output


def test_check_names_fails_on_a_collision_or_a_denylisted_name(tmp_path: Path) -> None:
    synthetic = tmp_path / "syn.ftm.jsonl"
    synthetic.write_text(
        _record("syn-co-0001", "nr_synthetic", "Ochre Tarn Freight Ltd")
        + _record("syn-co-0002", "nr_synthetic", "Kanoo Trading Ltd")
    )
    other = tmp_path / "other.ftm.jsonl"
    other.write_text(
        _record("gbch-co-T0000001", "gb_companies_house", "OCHRE TARN FREIGHT LIMITED")
    )
    result = runner.invoke(app, ["synth", "check-names", str(synthetic), "--against", str(other)])
    assert result.exit_code == 1
    assert "DENYLIST syn-co-0002" in result.output
    assert "COLLISION syn-co-0001" in result.output
    assert "OCHRE" not in result.output  # the other file's names are never printed


def test_er_bench_writes_records_manifest_and_truth(tmp_path: Path) -> None:
    result = runner.invoke(app, ["synth", "er-bench", "--seed", "5", "--out", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "records, seed 5" in result.output and "  Sanction: " in result.output
    assert len(list(tmp_path.glob("*.ftm.jsonl"))) == len(list(tmp_path.glob("*.manifest.json")))
    lines = (tmp_path / "labels" / "er_truth.csv").read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["# synthetic: true", "record_id,entity_id,class,style,twin_of"]


def test_er_bench_refuses_an_unknown_size(tmp_path: Path) -> None:
    result = runner.invoke(app, ["synth", "er-bench", "--size", "huge", "--out", str(tmp_path)])
    assert result.exit_code == 2 and not list(tmp_path.iterdir())
