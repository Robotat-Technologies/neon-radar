"""`neonradar spike opensanctions`: the licence gate decides (PHASE-1.md M1.8d)."""

from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.sources.opensanctions import access, spike
from neonradar_ingest.sources.opensanctions.mapping import MappingStats

runner = CliRunner()


def _route(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(f"access:\n  opensanctions: {value}\n", encoding="utf-8")
    monkeypatch.setattr(access, "PROJECT_FILE", project)


def _no_client(**_: Any) -> None:
    raise AssertionError("an HTTP client was created")


@pytest.mark.parametrize("value", ["none", "TODO", "evaluation"])
def test_refuses_with_exit_3_before_any_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    _route(monkeypatch, tmp_path, value)
    monkeypatch.setattr(access, "LICENCE_FILE", tmp_path / "missing.md")
    monkeypatch.setattr(spike, "make_client", _no_client)
    result = runner.invoke(app, ["spike", "opensanctions", "--collection", "peps"])
    assert result.exit_code == 3
    assert result.output.startswith(access.REFUSAL)


def test_prints_the_summary_when_allowed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _route(monkeypatch, tmp_path, "exempt")
    calls: list[dict[str, Any]] = []

    def run_spike(client: object, **options: Any) -> spike.SpikeResult:
        calls.append(options)
        index = spike.IndexInfo("u", (307,), "v1", "e", None)
        stats = MappingStats(lines=2)
        return spike.SpikeResult(options["access"], options["collection"], index, stats=stats)

    monkeypatch.setattr(spike, "run_spike", run_spike)
    result = runner.invoke(app, ["spike", "opensanctions", "--collection", "peps", "--rows", "2"])
    assert result.exit_code == 0, result.output
    assert calls == [{"access": access.Access.EXEMPT, "collection": "peps", "rows": 2}]
    assert "OpenSanctions spike: collection peps, access exempt" in result.output
    assert result.output.rstrip().endswith("wrote nothing (access exempt writes nothing)")


def test_unknown_collection_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _route(monkeypatch, tmp_path, "exempt")
    monkeypatch.setattr(spike, "make_client", nullcontext)  # never used: refused first
    result = runner.invoke(app, ["spike", "opensanctions", "--collection", "all"])
    assert result.exit_code == 1
    assert "unknown collection 'all'" in result.output
