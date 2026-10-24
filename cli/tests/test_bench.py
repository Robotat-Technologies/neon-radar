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
from neonradar_cli import bench
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
