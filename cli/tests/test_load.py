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
from neonradar_graph import loader, verify
from neonradar_ingest.data.profiles import load_profile

runner = CliRunner()
ALL = ["gate", "data fetch", "ingest build", "er run", "graph migrate", "graph load",
       "graph verify"]  # fmt: skip
SYNTHETIC = {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/demo-mini"]}}


@pytest.fixture
def ran(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, load.Run]]:
    """Every step a fake that records its name and run; no hardware probe runs a tool."""
    calls: list[tuple[str, load.Run]] = []

    def fake(name: str) -> load.Step:
        return lambda run: calls.append((name, run))

    for name in load.STEPS:
        monkeypatch.setitem(load.STEPS, name, fake(name))
    monkeypatch.setattr(load, "_command", lambda *args: None)
    return calls


def summaries(data_env: Any, profile: str) -> list[dict[str, Any]]:
    paths = sorted((data_env.cache / "reports" / profile).glob("load-*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def test_a_synthetic_profile_runs_its_steps_in_order_without_fetch_or_real(
    ran: list[tuple[str, load.Run]], data_env: Any
) -> None:
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    assert [name for name, _ in ran] == ALL[2:]  # no gate, no data fetch
    assert not any(run.real for _, run in ran)  # so no step passes --real
    (written,) = summaries(data_env, "demo")
    steps = [name.replace(" ", "_") for name in ALL[2:]]
    assert (written["status"], list(written["steps"])) == ("ok", steps)


def test_the_first_failing_step_stops_the_load_and_is_named(
    ran: list[tuple[str, load.Run]], data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fails(run: load.Run) -> None:
        ran.append(("er run", run))
        raise typer.Exit(code=3)

    monkeypatch.setitem(load.STEPS, "er run", fails)
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert (result.exit_code, [name for name, _ in ran]) == (1, ["ingest build", "er run"])
    assert "load stopped at step er run" in result.output
    (written,) = summaries(data_env, "demo")
    assert (written["failed_step"], written["steps"]["er_run"]["status"]) == ("er run", "failed")


def test_a_real_profile_gates_fetches_and_uses_real_unless_skip_fetch(
    ran: list[tuple[str, load.Run]], data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    tiny = load_profile("uk-tiny")
    assert load.plan(tiny, skip_fetch=False) == ALL
    assert load.plan(tiny, skip_fetch=True) == [name for name in ALL if name != "data fetch"]
    gate = load.STEPS["gate"]
    monkeypatch.setitem(load.STEPS, "gate", load.gate_step)  # the real gate: no approvals yet
    refused = runner.invoke(app, ["load", "--profile", "uk-tiny"])
    assert (refused.exit_code, ran) == (1, []) and "load stopped at step gate" in refused.output
    assert summaries(data_env, "uk-tiny")[0]["failed_step"] == "gate"
    monkeypatch.setitem(load.STEPS, "gate", gate)
    data_env.allow_real("uk-tiny")
    result = runner.invoke(app, ["load", "--profile", "uk-tiny", "--skip-fetch"])
    assert result.exit_code == 0, result.output
    assert [name for name, _ in ran] == [name for name in ALL if name != "data fetch"]
    assert all(run.real for _, run in ran)
    data_env.write_profile("plain", real_data=False, sources=SYNTHETIC)  # resolution.enabled false
    assert "er run" not in load.plan(load_profile("plain"), skip_fetch=False)


def test_graph_migrate_passes_real_only_for_a_real_profile(
    ran: list[tuple[str, load.Run]], data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real `migrate_step`, with `graph.migrate_command` recording its `real` argument."""
    migrated: list[bool] = []
    monkeypatch.setattr(graph, "migrate_command", lambda real: migrated.append(real))
    monkeypatch.setitem(load.STEPS, "graph migrate", load.migrate_step)
    data_env.allow_real("uk-tiny")
    for profile in ("demo", "uk-tiny"):
        result = runner.invoke(app, ["load", "--profile", profile, "--skip-fetch"])
        assert result.exit_code == 0, result.output
    assert migrated == [False, True]


def test_skip_officers_sets_the_budget_to_0_for_the_run_only(
    ran: list[tuple[str, load.Run]], data_env: Any
) -> None:
    before = (profile_file := data_env.profiles / "uk-tiny.yaml").read_bytes()
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


class FakeDriver:
    def execute_query(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, str]], None, None]:
        rows = [{"name": "server.memory.heap.max_size", "value": "1G"},
                {"name": "server.memory.pagecache.size", "value": "512M"}]  # fmt: skip
        return rows, None, None


def test_the_summary_has_every_field_and_passes_emit(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real step functions, with the commands they call replaced."""
    monkeypatch.setattr(load, "_command", lambda *args: "8589934592" if "docker" in args else None)
    datasets = {"nr_synthetic": {"status": "ok", "records": 4850, "files": ["a.ftm.jsonl"]}}
    monkeypatch.setattr(ingest, "run_build", lambda profile: {"datasets": datasets})
    counts = {"records": 4850, "merges": 665, "run_note": "text left out"}
    monkeypatch.setattr(er, "run_command", lambda profile: {"counts": counts, "seed": 7})
    monkeypatch.setattr(graph, "migrate_command", lambda real: None)
    loaded = {"records": 4850, "nodes_by_label": {"company": 2}, "dangling_references": 0}
    monkeypatch.setattr(graph, "load_command", lambda profile, resolution: loaded)
    found = {f"I{n}": 0 for n in range(1, 15)}
    monkeypatch.setattr(verify, "verify", lambda driver, database: found)
    monkeypatch.setattr(graph, "_settings", lambda instance: type("S", (), {"database": "neo4j"}))

    @contextmanager
    def connected(*args: Any, **kwargs: Any) -> Iterator[FakeDriver]:
        yield FakeDriver()

    monkeypatch.setattr(graph, "_connected", connected)
    stats = loader.GraphStats(10, 7, {"Company": 4, "SourceRecord": 6}, {"OWNS": 7})
    monkeypatch.setattr(loader, "stats", lambda driver, database: stats)
    result = runner.invoke(app, ["load", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    (written,) = summaries(data_env, "demo")
    assert {"profile", "run_id", "steps", "records", "build", "resolution", "graph_load", "graph",
            "invariants", "hardware", "status"} <= set(written)  # fmt: skip
    assert all(step["duration_s"] >= 0 for step in written["steps"].values())
    mini = written["records"]["nr_synthetic"]  # from the fixtures' manifests
    assert mini["by_schema"]["payment"] > 0 and mini["records"] > 0
    assert written["build"] == {"nr_synthetic": {"status": "ok", "records": 4850}}
    assert written["resolution"] == {"counts": {"records": 4850, "merges": 665}, "seed": 7}
    assert written["invariants"] == {f"i{n}": 0 for n in range(1, 15)}
    assert written["graph"]["nodes_by_label"] == {"company": 4, "sourcerecord": 6}
    hardware = written["hardware"]
    assert {"cpu_model", "cpu_cores", "ram_bytes", "os", "docker_memory_bytes"} <= set(hardware)
    assert (hardware["docker_memory_bytes"], hardware["neo4j_heap"]) == (8589934592, "1G")
    assert hardware["neo4j_pagecache"] == "512M"
    found["I3"] = 1  # a violation fails the step and stays in the summary
    assert runner.invoke(app, ["load", "--profile", "demo"]).exit_code == 1
    (failed,) = (item for item in summaries(data_env, "demo") if item["status"] == "failed")
    assert (failed["failed_step"], failed["invariants"]["i3"]) == ("graph verify", 1)


def test_record_counts_skip_datasets_without_a_record_folder(data_env: Any) -> None:
    from neonradar_ingest.data.project import load_project

    assert load.record_counts(load.Run(load_profile("uk-tiny"), load_project())) == {}
