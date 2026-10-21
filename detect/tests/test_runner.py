"""The detection runner without a database: selection, files, run status and what it sends to
Neo4j (a fake driver records the queries). The integration tests run it against Neo4j."""

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from neonradar_detect import runner
from neonradar_detect.alerts import Finding
from neonradar_detect.catalog import TypologyFile
from neonradar_detect.detectors import circular_flow
from neonradar_detect.detectors.circular_flow import finding, query, resolve_parameters

from .conftest import CIRCULAR_FLOW, EXPECTED, fixture_records, query_row

CLOCK = datetime(2026, 10, 21, 10, 15, 0, tzinfo=UTC)


class FakeResult:
    def __init__(self, record: dict[str, Any] | None = None) -> None:
        self.record = record

    def consume(self) -> None:
        return None

    def single(self, strict: bool = False) -> dict[str, Any] | None:
        return self.record


class FakeTx:
    def __init__(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = calls

    def run(self, cypher: str, **params: Any) -> FakeResult:
        self.calls.append((cypher, params))
        rows = params.get("rows", [])
        flagged = sum(len(row["subjects"]) for row in rows)
        return FakeResult({"alerts": len(rows), "flagged": flagged})


class FakeSession:
    def __init__(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = calls

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute_write(self, work: Any, *args: Any) -> Any:
        return work(FakeTx(self.calls), *args)


class FakeDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def session(self, database: str) -> FakeSession:
        return FakeSession(self.calls)


def findings(*cases: str) -> list[Finding]:
    params = resolve_parameters(CIRCULAR_FLOW)
    run_parameters = {"origin": None, "max_window_days": 14, "min_return_ratio": 0.8, "limit": 9}
    return [
        finding(
            query_row(fixture_records(), EXPECTED["cases"][case]["edge_ids"]),
            query(2, 6),
            run_parameters,
            params,
        )
        for case in cases
    ]


def use_detector(monkeypatch: pytest.MonkeyPatch, results: list[Finding]) -> None:
    fake = SimpleNamespace(
        NAME=circular_flow.NAME,
        VERSION=circular_flow.VERSION,
        detect=lambda driver, database, typology: results,
    )
    monkeypatch.setattr(runner, "DETECTORS", {circular_flow.NAME: fake})


def run(tmp_path: Path, driver: FakeDriver, **kwargs: Any) -> runner.RunReport:
    catalog: dict[str, TypologyFile] = {"circular_flow": CIRCULAR_FLOW}
    return runner.run(
        driver, "neo4j", runs_dir=tmp_path, catalog=catalog, clock=lambda: CLOCK, **kwargs
    )


def test_a_run_writes_its_audit_copy_and_loads_the_alerts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_detector(monkeypatch, findings("A", "B"))
    driver = FakeDriver()
    report = run(tmp_path, driver)
    assert report.status == "ok"
    assert report.run_id.startswith("run-20261021T101500-")
    lines = (report.directory / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["alert_id"] for line in lines] == [a.alert_id for a in report.alerts]
    meta = json.loads((report.directory / "run.json").read_text(encoding="utf-8"))
    assert meta | {"alert_ids": []} == {
        "run_id": report.run_id,
        "status": "ok",
        "started_at": "2026-10-21T10:15:00Z",
        "finished_at": "2026-10-21T10:15:00Z",
        "typologies": ["circular_flow"],
        "detectors": [{"name": circular_flow.NAME, "version": "0.1.0"}],
        "alert_count": 2,
        "alert_ids": [],
        "error": None,
    }
    (merge_run, run_params), (_, alert_params) = driver.calls
    assert merge_run == runner.MERGE_RUN
    detectors = [{"name": circular_flow.NAME, "version": "0.1.0"}]
    assert json.loads(run_params["run"]["detectors"]) == detectors
    assert run_params["run"]["alert_count"] == 2
    rows = alert_params["rows"]
    assert [row["props"]["alert_id"] for row in rows] == [a.alert_id for a in report.alerts]
    assert json.loads(rows[0]["props"]["payload"]) == report.alerts[0].model_dump(mode="json")
    assert rows[0]["subjects"] == [
        {"entity_id": "syn-acct-cfa1", "role": "origin"},
        {"entity_id": "syn-co-cf01", "role": "origin_holder"},
    ]


def test_alert_ids_are_stable_across_runs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_detector(monkeypatch, findings("A", "B"))
    first = run(tmp_path, FakeDriver(), run_id="run-20261021T101500-0001")
    second = run(tmp_path, FakeDriver(), run_id="run-20261021T101600-0002")
    assert [a.alert_id for a in first.alerts] == [a.alert_id for a in second.alerts]
    assert {a.run_id for a in second.alerts} == {"run-20261021T101600-0002"}


def test_a_wording_failure_fails_the_whole_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    good, bad = findings("A", "B")
    use_detector(monkeypatch, [good, dataclasses.replace(bad, summary="Funds were laundered.")])
    driver = FakeDriver()
    with pytest.raises(runner.RunError, match="wording lint"):
        run(tmp_path, driver, run_id="run-20261021T101500-0003")
    directory = tmp_path / "run-20261021T101500-0003"
    assert not (directory / "alerts.jsonl").exists()
    meta = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert (meta["status"], meta["alert_count"]) == ("failed", 0)
    assert "WordingError" in meta["error"]
    [(cypher, params)] = driver.calls  # only the failed :DetectionRun, no alerts
    assert cypher == runner.MERGE_RUN
    assert (params["run"]["status"], params["run"]["alert_count"]) == ("failed", 0)


def test_selection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_detector(monkeypatch, [])
    without = CIRCULAR_FLOW.model_copy(update={"slug": "layering_chain", "detector": None})
    catalog = {"circular_flow": CIRCULAR_FLOW, "layering_chain": without}
    assert runner.select(catalog, None) == [CIRCULAR_FLOW]
    with pytest.raises(runner.RunError, match="unknown typology 'nope'"):
        runner.select(catalog, "nope")
    with pytest.raises(runner.RunError, match="has no detector yet"):
        runner.select(catalog, "layering_chain")
    odd = CIRCULAR_FLOW.model_copy(update={"detector": "neonradar_detect.detectors.other"})
    with pytest.raises(runner.RunError, match="unknown detector"):
        runner.select({"circular_flow": odd}, None)


@pytest.mark.parametrize(
    "run_id", ["run-1", "../run-20261021T101500-7f3a", "run-20261021T101500-7F3A"]
)
def test_a_run_id_must_have_the_c4_form(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, run_id: str
) -> None:
    use_detector(monkeypatch, [])
    with pytest.raises(runner.RunError, match="must look like"):
        run(tmp_path, FakeDriver(), run_id=run_id)
    assert list(tmp_path.iterdir()) == []


def test_the_registry_holds_the_real_detector() -> None:
    assert runner.DETECTORS[circular_flow.NAME] is circular_flow
    assert CIRCULAR_FLOW.detector == circular_flow.NAME
