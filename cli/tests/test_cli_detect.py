"""`neonradar detect run|list|verify-alert` without a database (PHASE-3.md M3.2 deliverable 5).

The memory engine runs for real on the committed demo-mini fixture; the Neo4j engine is checked
through what it hands to `runs.run`. The integration tests run both against Neo4j."""

import importlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from neonradar_cli import detect, graph
from neonradar_cli.main import app
from neonradar_detect import catalog, runner, runs
from neonradar_detect.source import Window
from neonradar_graph import instances
from neonradar_ingest.data import profiles
from neonradar_ingest.data.project import load_project

cli = CliRunner()
ROUND_TRIP = "Synthetic scenario: funds returned to the originating account through 4 transfers"


@pytest.fixture(autouse=True)
def fake_neo4j(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Never read the repository's real .env, never connect; runs go to a tmp folder."""
    for name in [key for key in os.environ if key.startswith("NEO4J_")]:
        monkeypatch.delenv(name)
    monkeypatch.setitem(graph.Neo4jSettings.model_config, "env_file", tmp_path / "missing.env")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")

    @contextmanager
    def fake_driver(*args: Any) -> Iterator[object]:
        yield object()

    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)
    monkeypatch.setattr(runs, "RUNS_DIR", tmp_path / "runs")


def invoke(*args: str) -> Any:
    return cli.invoke(app, ["detect", *args], env={"COLUMNS": "200"})


def test_memory_run_on_demo_mini_finds_the_round_trip(tmp_path: Path) -> None:
    result = invoke("run", "--engine", "memory", "--run-id", "run-20261021T101500-7f3a")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "run-20261021T101500-7f3a  1 alerts  (circular_flow)  engine memory"
    assert lines[1] == "  circular_flow: 1 findings, 1 alerts, 0 duplicates, 0 withheld"
    assert ROUND_TRIP in lines[2]
    folder = tmp_path / "runs" / "run-20261021T101500-7f3a"
    assert lines[-1] == f"wrote {folder}"
    meta = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    assert (meta["engine"], meta["profile"], meta["status"]) == ("memory", None, "ok")
    assert meta["window"] == {"start": "2026-01-05T00:00:00Z", "end": "2026-04-03T00:00:00Z"}
    assert (tmp_path / "runs" / "LATEST").read_text(encoding="utf-8").strip() == meta["run_id"]
    [alert] = (folder / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(alert)["alert_id"] == meta["alert_ids"][0]


def test_the_window_option_bounds_the_starts(tmp_path: Path) -> None:
    result = invoke("run", "--engine", "memory", "--window", "2026-01-01", "2026-01-02")
    assert result.exit_code == 0, result.output
    assert " 0 alerts " in result.output.splitlines()[0]
    result = invoke("run", "--engine", "memory", "--window", "2026-02-01", "2026-01-01")
    assert result.exit_code == 1 and "window start must be before its end" in result.output


@pytest.mark.parametrize(
    ("args", "code", "message"),
    [
        (["--profile", "uk-tiny"], 2, "is a real profile"),
        (["--profile", "demo", "--engine", "memory"], 2, "resolves entities"),
        (["--profile", "no-such-profile"], 2, "no profile"),
        (["--engine", "spark"], 2, "--engine must be neo4j or memory"),
        (["--typology", "nope"], 1, "unknown typology 'nope'"),
        (["--typology", "structuring"], 1, "has no detector yet"),
        (["--run-id", "run-1"], 1, "must look like run-"),
    ],
)
def test_refusals(args: list[str], code: int, message: str) -> None:
    result = invoke("run", "--engine", "memory", *args)
    assert result.exit_code == code, result.output
    assert message in result.output


def _profile(overrides: dict[str, Any], window: str = "overlay") -> profiles.Profile:
    data = yaml.safe_load((profiles.PROFILES_DIR / "synth-eval.yaml").read_text(encoding="utf-8"))
    data["detection"] = {"enabled": True, "window": window, "overrides": overrides}
    return profiles.Profile.model_validate(data)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"circular_flow": {"min_hops": 99}}, "outside"),
        ({"circular_flow": {"no_such": 1}}, "unknown parameter no_such"),
        ({"no_such_typology": {}}, "unknown typologies: no_such_typology"),
    ],
)
def test_profile_overrides_are_checked(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any], message: str
) -> None:
    monkeypatch.setattr(profiles, "load_profile", lambda name: _profile(overrides))
    result = invoke("run", "--profile", "synth-eval", "--engine", "memory")
    assert result.exit_code == 2, result.output
    assert message in result.output


def test_the_neo4j_engine_hands_the_store_to_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(source: Any, params: Any, window: Window, catalog: Any, **kw: Any) -> Any:
        seen.update(kw, window=window, params=params, source=type(source).__name__)
        return runs.RunRecord(kw["run_id"], Path("data/runs/x"), "2026-10-21T10:15:00Z", "neo4j")

    monkeypatch.setattr(runs, "run", fake_run)
    result = invoke("run", "--window", "2026-01-01", "2026-07-01", "--keep-previous")
    assert result.exit_code == 0, result.output
    assert seen["source"] == "Neo4jSource" and seen["engine"] == "neo4j"
    assert seen["load"].keywords == {"keep_previous": True}
    assert seen["window"] == Window(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC)
    )
    assert seen["window_known"] is True and seen["profile"] is None
    assert seen["real_registry_alerts"] is load_project().access.real_registry_alerts
    assert list(seen["params"]) == ["circular_flow"]


def test_the_overlay_window_comes_from_overlay_json(tmp_path: Path) -> None:
    (tmp_path / "overlay.json").write_text(
        json.dumps({"period": {"start": "2025-01-01", "end": "2026-07-01"}}), encoding="utf-8"
    )
    window, known = detect._window(object(), None, _profile({}), tmp_path)  # type: ignore[arg-type]
    assert known and (window.start.year, window.end.month) == (2025, 7)
    with pytest.raises(runs.RunError, match="has no overlay"):
        detect._window(object(), None, _profile({}), None)  # type: ignore[arg-type]


def test_list_shows_every_typology_with_its_tier_and_detector() -> None:
    result = invoke("list")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert (
        "circular_flow  0.2.0  draft  core  neonradar_detect.detectors.circular_flow 0.2.0" in lines
    )
    assert "trade_based_ml  0.1.0  draft  explainer_only  no detector" in lines
    assert lines[-1] == "1 of 15 typologies have a detector"


def test_list_imports_no_module_outside_the_detector_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A file's `detector` passes MODULE_PATTERN as `os.path`; `list` imports only
    neonradar_detect.detectors.<slug>, the module catalog.load() allows (reconciliation C5)."""
    data = yaml.safe_load((catalog.TYPOLOGY_DIR / "circular_flow.yaml").read_text(encoding="utf-8"))
    folder = tmp_path / "typologies"
    folder.mkdir()
    probe = yaml.safe_dump({**data, "detector": "os.path"}, sort_keys=False)
    (folder / "circular_flow.yaml").write_text(probe, encoding="utf-8")
    read_folder = catalog.load_catalog
    monkeypatch.setattr(catalog, "load_catalog", lambda: read_folder(folder))
    imported: list[str] = []
    real_import = importlib.import_module

    def recording(name: str, package: str | None = None) -> Any:
        imported.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", recording)
    result = invoke("list")
    assert result.exit_code == 0, result.output
    refused = "detector must be neonradar_detect.detectors.circular_flow"
    assert result.output.splitlines() == [
        f"circular_flow  0.2.0  draft  core  {refused}",
        "0 of 1 typologies have a detector",
    ]
    assert "os.path" not in imported


@pytest.mark.parametrize(
    "error",
    [
        ImportError("No module named 'neonradar_detect.detectors.circular_flow'"),
        ValueError("typologies outside ORDER: ['round_trip']"),
    ],
)
def test_detectors_that_cannot_load_print_a_fail_line(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def failing(catalog: Any) -> Any:
        raise error

    monkeypatch.setattr(runner, "detectors", failing)
    result = invoke("run", "--engine", "memory")
    assert result.exit_code == 1
    assert result.output == f"FAIL  cannot load the detectors: {error}\n"


@pytest.mark.parametrize("args", [[], ["alr-0123456789abcdef0123", "--run", "latest"]])
def test_verify_alert_needs_one_alert_or_one_run(args: list[str]) -> None:
    result = invoke("verify-alert", *args)
    assert result.exit_code == 2 and "give one ALERT_ID or --run" in result.output


def test_verify_alert_refuses_a_memory_run(tmp_path: Path) -> None:
    assert invoke("run", "--engine", "memory").exit_code == 0
    result = invoke("verify-alert", "--run", "latest")
    assert result.exit_code == 2 and "ran in memory" in result.output


def test_verify_alert_refuses_a_failed_run(tmp_path: Path) -> None:
    """LATEST names the last run even when it failed; a failed run has nothing to verify."""
    run_id = "run-20261021T101500-7f3a"
    runs.write_folder(runs.RunRecord(run_id, runs.RUNS_DIR / run_id, "", "neo4j"))  # failed
    result = invoke("verify-alert", "--run", "latest")
    assert result.exit_code == 1
    assert result.output == f"FAIL  run {run_id} failed: nothing to verify\n"


def test_a_failed_run_exits_1_with_one_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(*args: Any, **kwargs: Any) -> runs.RunRecord:
        raise runs.RunError("run run-20261021T101500-7f3a failed: the reason")

    monkeypatch.setattr(runs, "run", failing)
    result = invoke("run", "--engine", "memory")
    assert result.exit_code == 1
    assert result.output == "FAIL  run run-20261021T101500-7f3a failed: the reason\n"


@pytest.mark.parametrize(
    ("target", "error", "line"),
    [
        (
            "catalog",
            catalog.CatalogError("circular_flow.yaml: not valid"),
            "FAIL  cannot read the typology catalog: circular_flow.yaml: not valid\n",
        ),
        ("run", PermissionError("data/runs: denied"), "FAIL  data/runs: denied\n"),
    ],
)
def test_catalog_and_file_errors_print_a_fail_line(
    monkeypatch: pytest.MonkeyPatch, target: str, error: Exception, line: str
) -> None:
    def failing(*args: Any, **kwargs: Any) -> Any:
        raise error

    if target == "catalog":
        monkeypatch.setattr(catalog, "load", failing)
    else:
        monkeypatch.setattr(runs, "run", failing)
    result = invoke("run", "--engine", "memory")
    assert result.exit_code == 1
    assert result.output == line


def test_run_help_explains_a_reused_run_id() -> None:
    assert "Given again" in invoke("run", "--help").output


# Profiles' runs and real profiles (PHASE-3.md M3.4 deliverable 4) -----------------------------


def test_a_profile_s_run_goes_to_its_runs_folder(data_env: Any) -> None:
    sources = {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/demo-mini"]}}
    data_env.write_profile("syn-test", real_data=False, sources=sources)
    run_id = "run-20261023T101500-0a0b"
    result = invoke("run", "--engine", "memory", "--profile", "syn-test", "--run-id", run_id)
    assert result.exit_code == 0, result.output
    folder = data_env.cache / "synthetic" / "runs" / "syn-test" / run_id
    assert result.output.splitlines()[-1] == f"wrote {folder}"
    assert (folder / "run.json").is_file() and layout_latest("syn-test") == run_id
    result = invoke("verify-alert", "--run", "latest", "--profile", "uk-tiny")
    assert result.exit_code == 2 and "verify-alert prints alert ids" in result.output


def layout_latest(profile: str) -> str | None:
    from neonradar_ingest.data import layout

    return layout.latest_detection_run(profile)


def test_a_real_profile_runs_behind_the_gate_and_prints_counts_only(
    monkeypatch: pytest.MonkeyPatch, data_env: Any
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(source: Any, params: Any, window: Window, catalog: Any, **kw: Any) -> Any:
        seen.update(kw)
        record = runs.RunRecord(
            kw["run_id"], kw["runs_dir"] / kw["run_id"], "x", "neo4j", "uk-tiny"
        )
        record.summary = {"run_id": kw["run_id"], "alerts": 0, "withheld": {"activity_on_real": 2}}
        return record

    monkeypatch.setattr(runs, "run", fake_run)
    window = ["--window", "2025-01-01", "2026-07-01"]
    result = invoke("run", "--profile", "uk-tiny", *window)
    assert (result.exit_code, seen) == (3, {}), result.output
    assert "uk-tiny is not in access.real_data_profiles" in result.output
    data_env.allow_real("uk-tiny")
    for settings in (instances.RealNeo4jSettings, instances._DatabaseSetting):  # never .env
        monkeypatch.setitem(settings.model_config, "env_file", data_env.root / "missing.env")
    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")
    monkeypatch.setattr(detect, "_overlay_folder", lambda profile: None)
    result = invoke("run", "--profile", "uk-tiny", *window)
    assert result.exit_code == 0, result.output
    assert seen["runs_dir"] == data_env.cache / "real" / "runs" / "uk-tiny"
    printed = json.loads(result.output)
    assert (printed["profile"], printed["withheld"]) == ("uk-tiny", {"activity_on_real": 2})
