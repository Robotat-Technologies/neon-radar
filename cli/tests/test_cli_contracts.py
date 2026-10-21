import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app

runner = CliRunner()


def _company(**nr: Any) -> str:
    record = {
        "id": "syn-co-0099",
        "schema": "Company",
        "datasets": ["nr_synthetic"],
        "properties": {"name": ["Example Holdings Ltd"]},
        "nr": {"v": "1.0", "synthetic": True, **nr},
    }
    return json.dumps(record) + "\n"


def test_validate_records_prints_counts_and_ok(tmp_path: Path) -> None:
    path = tmp_path / "ok.ftm.jsonl"
    path.write_text(_company(), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path), "--strict"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == ["1 records in 1 file(s)", "  Company: 1", "OK, 0 issues"]


def test_validate_records_prints_each_issue_and_exits_1(tmp_path: Path) -> None:
    path = tmp_path / "bad.ftm.jsonl"
    path.write_text(_company(scenario="round_trip"), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path)])
    assert result.exit_code == 1
    assert "R9 syn-co-0099: nr key 'scenario' looks like a ground-truth label" in result.output
    assert result.output.splitlines()[-1] == "FAILED, 1 issue(s)"


def test_validate_records_reports_a_bad_line(tmp_path: Path) -> None:
    path = tmp_path / "broken.ftm.jsonl"
    path.write_text(_company() + "{oops\n", encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path)])
    assert result.exit_code == 1
    assert result.output.startswith(f"FORMAT {path}:2: invalid JSON")


def test_validate_records_reports_a_file_that_is_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "latin1.ftm.jsonl"
    path.write_bytes(_company().replace("Example", "Caf\xe9").encode("latin-1"))
    result = runner.invoke(app, ["contracts", "validate-records", str(path)])
    assert result.exit_code == 1
    assert result.output.startswith(f"FORMAT {path}:1: not UTF-8")


def test_validate_records_accepts_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.ftm.jsonl"
    path.write_bytes(b"")
    result = runner.invoke(app, ["contracts", "validate-records", str(path), "--strict"])
    assert result.exit_code == 0
    assert result.output.splitlines() == ["0 records in 1 file(s)", "OK, 0 issues"]


def test_export_prints_each_file(monkeypatch: pytest.MonkeyPatch) -> None:
    from neonradar_contracts import schemas

    written = [schemas.CONTRACTS_DIR / "schemas" / "alert.v1.json"]
    seen: list[set[str]] = []

    def export(docs: dict[str, str]) -> list[Path]:
        seen.append(set(docs))
        return written

    monkeypatch.setattr(schemas, "export", export)
    result = runner.invoke(app, ["contracts", "export"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == ["wrote contracts/schemas/alert.v1.json"]
    assert seen == [{*schemas.documents(), "openapi/v1.json"}]  # the C3 snapshot joins


def test_check_passes_on_the_committed_files() -> None:
    result = runner.invoke(app, ["contracts", "check"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("OK, 4 generated files match the models")


def test_check_reports_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    from neonradar_contracts import schemas

    drift = ["schemas/alert.v1.json: differs from the models; run `make contracts`"]
    monkeypatch.setattr(schemas, "check", lambda docs: drift)
    result = runner.invoke(app, ["contracts", "check"])
    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "DRIFT contracts/schemas/alert.v1.json: differs from the models; run `make contracts`",
        "FAILED, 1 difference(s)",
    ]
