"""`neonradar bench queries` (PHASE-2.md M2.13 deliverables 3 and 7): the graph and the API's
route functions are fakes, so no test reaches Neo4j."""

import json
from functools import partial
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_api import graph as api_graph
from neonradar_api import main as api_main
from neonradar_cli import bench, bench_report
from neonradar_cli.main import app

runner = CliRunner()
IDS = [f"syn-co-{number:04d}" for number in range(30)]


def test_pick_is_a_pure_function_of_the_ids_and_the_seed() -> None:
    first = bench.pick(IDS, 10, 7)
    assert first == bench.pick(list(reversed(IDS)), 10, 7) == bench.pick(IDS + IDS, 10, 7)
    assert len(set(first)) == 10 and set(first) <= set(IDS)
    assert bench.pick(IDS, 10, 8) != first
    assert sorted(bench.pick(IDS, 100, 7)) == IDS


def test_percentiles_are_nearest_rank_in_milliseconds() -> None:
    values = [0.001 * n for n in range(1, 21)]
    assert (bench.percentile(values, 0.5), bench.percentile(values, 0.95)) == (10.0, 19.0)
    assert (bench.percentile(values, 1.0), bench.percentile([], 0.5)) == (20.0, None)


class FakeGraph:
    created = 0

    def __init__(self, settings: Any) -> None:
        FakeGraph.created += 1

    def call(self, work: Any) -> list[dict[str, str]]:
        return [{"id": entity_id} for entity_id in IDS]

    def close(self) -> None:
        pass


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    answers = {"get_ownership": SimpleNamespace(paths=[1, 2], subgraph=None),
               "find_paths": SimpleNamespace(paths=[1, 2], subgraph=None),
               "get_network": SimpleNamespace(nodes=[1, 2, 3], edges=[1]),  # a Subgraph
               "search": SimpleNamespace(items=[1], query="")}  # fmt: skip

    def route(name: str, *args: Any) -> Any:
        calls.append(args)
        return answers[name]

    monkeypatch.setattr(api_graph, "GraphConnection", FakeGraph)
    for name in answers:
        monkeypatch.setattr(api_main, name, partial(route, name))
    caption = SimpleNamespace(entity=SimpleNamespace(caption="syn-co-0001 Holdings"))
    monkeypatch.setattr(api_main, "get_entity", lambda graph, entity_id: caption)  # token: an id
    return calls


def test_bench_queries_prints_latencies_and_never_an_id(data_env: Any, fake_api: Any) -> None:
    result = runner.invoke(app, ["bench", "queries", "--profile", "demo", "--n", "10"])
    assert result.exit_code == 0, result.output
    assert not any(entity_id in result.output for entity_id in IDS)
    (path,) = (data_env.cache / "reports" / "demo").glob("bench-queries-*.json")
    text = path.read_text(encoding="utf-8")
    assert not any(entity_id in text for entity_id in IDS)
    written = json.loads(text)
    assert (written["eligible"], written["picked"]) == (30, 10)
    endpoints = written["endpoints"]
    assert [endpoints[name]["calls"] for name in bench.ENDPOINTS] == [10, 10, 9, 10, 10]
    assert (endpoints["paths"]["results"], endpoints["network"]["results"]) == (18, 30)
    assert all(endpoints[name]["p95_ms"] is not None for name in bench.ENDPOINTS)


def test_the_instance_must_match_the_profile_and_real_runs_the_gate(
    data_env: Any, fake_api: Any
) -> None:
    FakeGraph.created = 0
    for args, code in ((["--profile", "uk-tiny"], 2), (["--profile", "demo", "--real"], 2),
                       (["--profile", "uk-tiny", "--real"], 3)):  # fmt: skip
        result = runner.invoke(app, ["bench", "queries", *args])
        assert result.exit_code == code, result.output
    assert FakeGraph.created == 0 and fake_api == []


def test_bench_report_renders_the_newest_summaries_with_targets_and_footer(
    data_env: Any, tmp_path: Any
) -> None:
    from neonradar_cli import summary

    steps = {"ingest_build": {"status": "ok", "duration_s": 430.0},
             "graph_load": {"status": "ok", "duration_s": 300.0}}  # fmt: skip
    records = {"nr_synthetic": {"records": 454, "by_schema": {"payment": 243}, "version": None}}
    load = {"run_id": "load-1", "status": "ok", "real_data": False, "steps": steps,
            "records": records, "invariants": {"i1": 0}, "hardware": {"cpu_cores": 4}}  # fmt: skip
    summary.emit("demo", "load", load)
    endpoints = {
        name: {
            "calls": 3,
            "p50_ms": 4.0,
            "p95_ms": 1990.0,
            "max_ms": 3810.0,
            "results": 3,
            "timeouts": 0,
            "errors": 0,
        }
        for name in bench.ENDPOINTS
    }
    endpoints["search"] |= {"p95_ms": 9.0, "max_ms": 12.5}  # fmt: skip
    summary.emit("demo", "bench queries", {"picked": 3, "eligible": 9, "seed": 1,
                                            "endpoints": endpoints})  # fmt: skip
    out = tmp_path / "demo-bench.md"
    result = runner.invoke(app, ["bench", "report", "--profile", "demo", "--out", str(out)])
    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert "| graph load | ok | 300.0 |" in text and "| nr_synthetic | - | payment | 243 |" in text
    assert ("Targets (G2-09): graph load 5.0 min, under 10 minutes: met; ownership and paths p95"
            " 1.99 s, under 2 seconds: met. Information only: whole load 12.2 min; slowest call"
            " 3.81 s.") in text  # fmt: skip
    assert "| search | 3 | 4.0 | 9.0 | 12.5 | 3 | 0 | 0 |" in text
    assert "Possible matches are not confirmed and were not merged." in text
    assert "minutes: not met." in bench_report.targets({"status": "failed", "steps": {}}, None)
    slow = {"status": "ok", "steps": {"graph_load": {"status": "ok", "duration_s": 600.0}}}
    assert "graph load 10.0 min, under 10 minutes: not met" in bench_report.targets(slow, None)
    endpoints["network"]["timeouts"] = 1  # a timeout anywhere: the query target is not met
    line = bench_report.targets(None, {"endpoints": endpoints})
    assert "under 2 seconds: not met (1 calls timed out or failed)" in line
    assert text.rstrip().splitlines()[-1].startswith("Sources and licences: NeonRadar synthetic")


def test_bench_report_without_summaries_fails(data_env: Any, tmp_path: Any) -> None:
    result = runner.invoke(app, ["bench", "report", "--profile", "demo", "--out", str(tmp_path)])
    assert result.exit_code == 1 and "no load or bench-queries summary" in result.output


def test_bench_report_refuses_an_edited_summary_and_attributes_the_profile(
    data_env: Any, tmp_path: Any
) -> None:
    from neonradar_cli import summary

    out = tmp_path / "report.md"
    summary.emit("uk-tiny", "bench queries", {"picked": 0, "eligible": 0, "endpoints": {}})
    result = runner.invoke(app, ["bench", "report", "--profile", "uk-tiny", "--out", str(out)])
    assert result.exit_code == 0, result.output  # no load summary: the profile's sources
    assert "Companies House" in out.read_text(encoding="utf-8").splitlines()[-1]
    (data_env.cache / "reports" / "demo").mkdir(parents=True)
    edited = {"status": "ok", "steps": {}, "note": "Test Holder Ltd"}  # a string under no key
    (data_env.cache / "reports" / "demo" / "load-20261102T000000.json").write_text(
        json.dumps(edited), encoding="utf-8"
    )
    result = runner.invoke(app, ["bench", "report", "--profile", "demo", "--out", str(out)])
    assert result.exit_code == 1 and "Test Holder" not in result.output


def test_eligible_reads_once_with_its_own_timeout() -> None:
    from neo4j import RoutingControl

    seen: dict[str, Any] = {}

    class Driver:
        def execute_query(self, query: Any, parameters: Any, **options: Any) -> Any:
            seen.update(timeout=query.timeout, routing=options["routing_"], **parameters)
            return SimpleNamespace(records=[{"id": "syn-co-0001"}])

    graph = SimpleNamespace(call=lambda work: work(Driver(), "neo4j"))
    assert bench.eligible(graph) == ["syn-co-0001"]  # type: ignore[arg-type]
    assert seen == {"timeout": bench.ELIGIBLE_TIMEOUT_S, "routing": RoutingControl.READ,
                    "limit": bench.ELIGIBLE_LIMIT}  # fmt: skip


def test_bench_queries_gates_each_enabled_dataset_before_connecting(
    data_env: Any, fake_api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neonradar_ingest.data import gate

    checked: list[str | None] = []

    def check(project: Any, profile: Any, dataset: str | None = None) -> None:
        checked.append(dataset)
        if dataset == "gleif_lei":  # as if its access had been withdrawn after the load
            raise gate.RealDataRefused("access.test", "refused for the test")

    monkeypatch.setattr(gate, "check_real_data", check)
    FakeGraph.created = 0
    result = runner.invoke(app, ["bench", "queries", "--profile", "uk-tiny", "--real"])
    assert (result.exit_code, FakeGraph.created, fake_api) == (3, 0, []), result.output
    assert checked[0] is None and checked[-1] == "gleif_lei" and "gb_companies_house" in checked
