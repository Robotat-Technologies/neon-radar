"""`neonradar load` (PHASE-2.md M2.13 deliverables 1 and 7): every step replaced by a fake, so
no test fetches, builds, resolves or reaches Neo4j or Docker."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from neonradar_cli import er, graph, ingest, load
from neonradar_cli.main import app
from neonradar_graph import loader
from neonradar_ingest.data.profiles import load_profile

runner = CliRunner()
ALL = ["gate", "data fetch", "ingest build", "er run", "graph migrate", "graph load",
       "graph verify"]  # fmt: skip
SYNTHETIC = {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/demo-mini"]}}


@pytest.fixture
def ran(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, load.Run]]:
    """Every step a fake that records its name and run."""
    calls: list[tuple[str, load.Run]] = []

    def fake(name: str) -> load.Step:
        return lambda run: calls.append((name, run))

    for name in load.STEPS:
        monkeypatch.setitem(load.STEPS, name, fake(name))
    return calls


def summaries(data_env: Any, profile: str) -> list[dict[str, Any]]:
    folder = data_env.cache / "reports" / profile
    paths = sorted(folder.glob("load-*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def test_a_synthetic_profile_runs_its_steps_in_order_without_fetch_or_real(
    ran: list[tuple[str, load.Run]], data_env: Any
) -> None:
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    assert [name for name, _ in ran] == ALL[2:]  # no gate, no data fetch
    assert not any(run.real for _, run in ran)  # so no step passes --real
    (written,) = summaries(data_env, "demo")
    assert written["status"] == "ok"
    assert list(written["steps"]) == [name.replace(" ", "_") for name in ALL[2:]]


def test_the_first_failing_step_stops_the_load_and_is_named(
    ran: list[tuple[str, load.Run]], data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fails(run: load.Run) -> None:
        ran.append(("er run", run))
        raise typer.Exit(code=3)

    monkeypatch.setitem(load.STEPS, "er run", fails)
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert result.exit_code == 1
    assert "load stopped at step er run" in result.output
    assert [name for name, _ in ran] == ["ingest build", "er run"]
    (written,) = summaries(data_env, "demo")
    assert (written["status"], written["failed_step"]) == ("failed", "er run")
    assert written["steps"]["er_run"]["status"] == "failed"


def test_a_real_profile_gates_fetches_and_uses_real_unless_skip_fetch(
    ran: list[tuple[str, load.Run]], data_env: Any
) -> None:
    tiny = load_profile("uk-tiny")
    assert load.plan(tiny, skip_fetch=False) == ALL
    assert load.plan(tiny, skip_fetch=True) == [name for name in ALL if name != "data fetch"]
    data_env.allow_real("uk-tiny")
    result = runner.invoke(app, ["load", "--profile", "uk-tiny", "--skip-fetch"])
    assert result.exit_code == 0, result.output
    assert [name for name, _ in ran] == [name for name in ALL if name != "data fetch"]
    assert all(run.real for _, run in ran)


def test_a_profile_without_resolution_skips_er_run(data_env: Any) -> None:
    data_env.write_profile("plain", real_data=False, sources=SYNTHETIC)
    assert "er run" not in load.plan(load_profile("plain"), skip_fetch=False)


def test_skip_officers_sets_the_budget_to_0_for_the_run_only(
    ran: list[tuple[str, load.Run]], data_env: Any
) -> None:
    profile_file = data_env.profiles / "uk-tiny.yaml"
    before = profile_file.read_bytes()
    data_env.allow_real("uk-tiny")
    budgets = []
    for flags in (["--skip-officers"], []):
        ran.clear()
        result = runner.invoke(app, ["load", "--profile", "uk-tiny", "--skip-fetch", *flags])
        assert result.exit_code == 0, result.output
        built = dict(ran)["ingest build"].profile
        budgets.append(built.options("gb_companies_house").officers.request_budget)
    assert budgets == [0, 1500]
    assert profile_file.read_bytes() == before
    assert load_profile("uk-tiny").options("gb_companies_house").officers.request_budget == 1500


def test_the_summary_has_every_field_and_passes_emit(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real step functions, with the commands they call replaced."""
    datasets = {"nr_synthetic": {"status": "ok", "records": 4850, "files": ["a.ftm.jsonl"]}}
    monkeypatch.setattr(ingest, "run_build", lambda profile: {"datasets": datasets})
    counts = {"records": 4850, "merges": 665, "run_note": "text left out"}
    monkeypatch.setattr(er, "run_command", lambda profile: {"counts": counts, "seed": 7})
    monkeypatch.setattr(graph, "migrate_command", lambda real: None)
    loaded = {"records": 4850, "nodes_by_label": {"company": 2}, "dangling_references": 0}
    monkeypatch.setattr(graph, "load_command", lambda profile, resolution: loaded)
    monkeypatch.setattr(graph, "verify_command", lambda real: {f"I{n}": 0 for n in range(1, 15)})
    monkeypatch.setattr(graph, "_settings", lambda instance: type("S", (), {"database": "neo4j"}))

    @contextmanager
    def connected(*args: Any, **kwargs: Any) -> Iterator[object]:
        yield object()

    monkeypatch.setattr(graph, "_connected", connected)
    stats = loader.GraphStats(10, 7, {"Company": 4, "SourceRecord": 6}, {"OWNS": 7})
    monkeypatch.setattr(loader, "stats", lambda driver, database: stats)
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    (written,) = summaries(data_env, "demo")
    assert {"profile", "run_id", "steps", "build", "resolution", "graph_load", "graph",
            "invariants", "status"} <= set(written)  # fmt: skip
    assert all(step["duration_s"] >= 0 for step in written["steps"].values())
    assert written["build"] == {"nr_synthetic": {"status": "ok", "records": 4850}}
    assert written["resolution"] == {"counts": {"records": 4850, "merges": 665}, "seed": 7}
    assert written["invariants"] == {f"i{n}": 0 for n in range(1, 15)}
    assert written["graph"]["nodes_by_label"] == {"company": 4, "sourcerecord": 6}


def test_counts_keep_numbers_and_status_only() -> None:
    value = {"status": "ok", "n": 2, "name": "x", "items": ["a"], "nested": {"m": 1.5}}
    assert load.counts(value) == {"status": "ok", "n": 2, "nested": {"m": 1.5}}
