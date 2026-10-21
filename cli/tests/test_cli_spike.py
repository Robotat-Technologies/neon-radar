import json
import os
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from neonradar_cli import spike
from neonradar_cli.main import app
from neonradar_ingest import spikes

runner = CliRunner()


def test_spike_clean_deletes_expired_output_only_in_the_spike_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project.yaml"
    project.write_text("access:\n  spike_cache_days: 3\n", encoding="utf-8")
    monkeypatch.setattr(spikes, "PROJECT_FILE", project)
    root = tmp_path / "spikes"
    monkeypatch.setattr(spikes, "SPIKE_ROOT", root)  # the command has no other folder option
    old, new = root / "gleif" / "old.ftm.jsonl", root / "gleif" / "new.ftm.jsonl"
    old.parent.mkdir(parents=True)
    for path in (old, new):
        path.write_text("{}\n", encoding="utf-8")
    os.utime(old, (0, 0))
    result = runner.invoke(app, ["spike", "clean", "--days", "7"])
    assert result.exit_code == 0, result.output
    summary = f"1 file(s) older than 7 day(s) deleted from {root}"
    assert result.output.splitlines() == [f"deleted {old}", summary]
    assert new.exists() and not old.exists()
    result = runner.invoke(app, ["spike", "clean"])  # the days from the tmp project.yaml
    assert result.output == f"0 file(s) older than 3 day(s) deleted from {root}\n"
    assert "--dir" not in runner.invoke(app, ["spike", "clean", "--help"]).output
    project.write_text("access:\n  spike_cache_days: TODO\n", encoding="utf-8")
    result = runner.invoke(app, ["spike", "clean"])
    assert (result.exit_code, result.output) == (
        1,
        "FAIL  access.spike_cache_days is 'TODO', not a whole number of days\n",
    )


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
    with pytest.raises(typer.Exit) as stopped:
        spike.report_output(path)
    assert stopped.value.exit_code == 1
    assert capsys.readouterr().out.splitlines()[-1] == "FAILED, 1 issue(s)"
    path.write_text("{oops\n", encoding="utf-8")
    with pytest.raises(typer.Exit) as stopped:
        spike.report_output(path)
    assert stopped.value.exit_code == 1
    assert capsys.readouterr().out.startswith(f"FORMAT {path}:1: invalid JSON")
