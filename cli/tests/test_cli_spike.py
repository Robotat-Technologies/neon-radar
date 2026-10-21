import json
import os
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from neonradar_cli import spike
from neonradar_cli.main import app

runner = CliRunner()


def test_spike_clean_deletes_expired_output(tmp_path: Path) -> None:
    old, new = tmp_path / "gleif" / "old.ftm.jsonl", tmp_path / "gleif" / "new.ftm.jsonl"
    old.parent.mkdir()
    for path in (old, new):
        path.write_text("{}\n", encoding="utf-8")
    os.utime(old, (0, 0))
    result = runner.invoke(app, ["spike", "clean", "--dir", str(tmp_path), "--days", "7"])
    assert result.exit_code == 0, result.output
    summary = f"1 file(s) older than 7 day(s) deleted from {tmp_path}"
    assert result.output.splitlines() == [f"deleted {old}", summary]
    assert new.exists() and not old.exists()
    result = runner.invoke(app, ["spike", "clean", "--dir", str(tmp_path)])
    assert result.output.endswith(f"older than 7 day(s) deleted from {tmp_path}\n")  # project.yaml


def test_report_output_prints_counts_and_fails_on_issues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "nr_synthetic-20261021-x.ftm.jsonl"
    record: dict[str, Any] = {"id": "syn-co-1", "schema": "Company", "datasets": ["nr_synthetic"]}
    record |= {"properties": {"name": ["A Ltd"]}, "nr": {"v": "1.0", "synthetic": True}}
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    spike.report_output(path)
    assert capsys.readouterr().out.splitlines()[1:] == ["  Company: 1", "OK, 0 issues (strict)"]
    record["properties"] = {"name": ["A Ltd"], "addressEntity": ["syn-addr-404"]}
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(typer.Exit):
        spike.report_output(path)
    assert capsys.readouterr().out.splitlines()[-1] == "FAILED, 1 issue(s)"
