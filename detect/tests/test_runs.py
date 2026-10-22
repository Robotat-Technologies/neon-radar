"""A detection run without a database: the run folder, the run status and what the L19 load sends
to Neo4j (a fake driver records the statements). Phase 1's runner tests of file writing and
alert loading (PHASE-1.md M1.9b) carried over to the Phase 3 run (M3.2 deliverable 5); the
integration tests run it against Neo4j (`test_detection_store.py`)."""

import dataclasses
import json
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from kit import WINDOW, Kit

from neonradar_detect import catalog, runner, runs
from neonradar_detect.detectors import circular_flow
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource

CLOCK = datetime(2026, 10, 21, 10, 15, 0, tzinfo=UTC)
STATEMENTS = {
    name: runs._store_text(name)
    for name in ("delete_detections", "merge_run", "prune_run", "merge_alerts")
}


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

    def names(self) -> list[str]:
        by_text = {text: name for name, text in STATEMENTS.items()}
        return [by_text[cypher] for cypher, _ in self.calls]


def two_cycles() -> list[dict[str, Any]]:
    k = Kit()
    for tag in ("a", "b"):
        accts = [k.account(f"{tag}{i}", k.company(f"{tag}{i}")) for i in range(4)]
        for i, (src, dst) in enumerate(zip(accts, accts[1:] + accts[:1], strict=True)):
            k.pay(src, dst, 50000 - 500 * i, f"2026-03-0{2 + i}T1{int(tag == 'b')}:00")
    return k.records


def run(
    tmp_path: Path, driver: FakeDriver | None = None, *, cat: Any = None, **kwargs: Any
) -> runs.RunRecord:
    params = {"circular_flow": circular_flow.Params()}
    load = partial(runs.store, driver, "neo4j", keep_previous=False) if driver else None
    return runs.run(
        MemSource(from_records(two_cycles())),
        params,
        WINDOW,
        cat or catalog.load(),
        run_id=kwargs.pop("run_id", "run-20261021T101500-0001"),
        engine="neo4j" if driver else "memory",
        runs_dir=tmp_path,
        clock=lambda: CLOCK,
        load=kwargs.pop("load", load),
        **kwargs,
    )


def test_a_run_writes_its_folder_and_loads_the_alerts(tmp_path: Path) -> None:
    driver = FakeDriver()
    record = run(tmp_path, driver, profile="synth-eval")
    ids = [alert.alert_id for alert in record.alerts]
    assert record.status == "ok" and len(ids) == 2
    lines = (record.directory / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["alert_id"] for line in lines] == ids
    assert all(list(json.loads(line)) == sorted(json.loads(line)) for line in lines)
    summary = json.loads((record.directory / "summary.json").read_text(encoding="utf-8"))
    assert summary["alerts"] == 2 and summary["typologies"]["circular_flow"]["findings"] == 2
    meta = json.loads((record.directory / "run.json").read_text(encoding="utf-8"))
    assert meta | {"alert_ids": [], "params_sha256": ""} == {
        "run_id": "run-20261021T101500-0001",
        "status": "ok",
        "started_at": "2026-10-21T10:15:00Z",
        "finished_at": "2026-10-21T10:15:00Z",
        "typologies": ["circular_flow"],
        "detectors": [{"name": circular_flow.__name__, "version": "0.2.0"}],
        "alert_count": 2,
        "alert_ids": [],
        "error": None,
        "profile": "synth-eval",
        "params_sha256": "",
        "window": {"start": "2026-01-01T00:00:00Z", "end": "2026-07-01T00:00:00Z"},
        "engine": "neo4j",
        "queries_sha256": {"circular_flow": runs.queries_sha256(circular_flow)},
    }
    assert meta["params_sha256"] == runner.params_sha256({"circular_flow": circular_flow.Params()})
    assert (tmp_path / "LATEST").read_text(encoding="utf-8") == f"{record.run_id}\n"
    assert driver.names() == ["delete_detections", "merge_run", "prune_run", "merge_alerts"]
    (_, _), (_, run_params), (_, prune_params), (_, alert_params) = driver.calls
    node = run_params["run"]
    assert (node["profile"], node["alert_count"], node["status"]) == ("synth-eval", 2, "ok")
    assert (node["window_start"], node["window_end"]) == (
        meta["window"]["start"],
        meta["window"]["end"],
    )
    assert json.loads(node["summary"]) == summary and node["params_sha256"] == meta["params_sha256"]
    assert json.loads(node["detectors"]) == meta["detectors"]
    assert prune_params["alert_ids"] == ids
    rows = alert_params["rows"]
    assert [row["props"]["alert_id"] for row in rows] == ids
    first = record.alerts[0]
    assert json.loads(rows[0]["props"]["payload"]) == first.model_dump(mode="json")
    assert rows[0]["props"]["evidence_node_ids"] == first.evidence.node_ids
    assert rows[0]["props"]["evidence_edge_ids"] == first.evidence.edge_ids
    assert [s["role"] for s in rows[0]["subjects"]] == ["origin", "origin_holder"]


def test_every_alert_carries_the_evidence_query_hash(tmp_path: Path) -> None:
    record = run(tmp_path)
    assert {a.detector.query_sha256 for a in record.alerts} == {runs.EVIDENCE_SHA256}
    assert runs.queries_sha256(circular_flow) != runs.EVIDENCE_SHA256


def test_keep_previous_skips_the_delete(tmp_path: Path) -> None:
    driver = FakeDriver()
    load = partial(runs.store, driver, "neo4j", keep_previous=True)
    run(tmp_path, load=load)
    assert driver.names() == ["merge_run", "prune_run", "merge_alerts"]


def test_alert_ids_are_stable_across_runs(tmp_path: Path) -> None:
    first = run(tmp_path, run_id="run-20261021T101500-0001")
    second = run(tmp_path, run_id="run-20261021T101600-0002")
    assert [a.alert_id for a in first.alerts] == [a.alert_id for a in second.alerts]
    assert {a.run_id for a in second.alerts} == {"run-20261021T101600-0002"}
    assert runs.latest(tmp_path) == "run-20261021T101600-0002"


def test_a_wording_failure_fails_the_whole_run(tmp_path: Path) -> None:
    cat = catalog.load()
    bad = dict(cat["circular_flow"].wording, headline_synthetic="Synthetic scenario: layering")
    broken = {**cat, "circular_flow": dataclasses.replace(cat["circular_flow"], wording=bad)}
    driver = FakeDriver()
    with pytest.raises(
        runs.RunError, match=r"circular_flow: the headline matches \['\\\\blayering"
    ):
        run(tmp_path, driver, cat=broken, run_id="run-20261021T101500-0003")
    directory = tmp_path / "run-20261021T101500-0003"
    assert not (directory / "alerts.jsonl").exists() and not (directory / "summary.json").exists()
    meta = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert (meta["status"], meta["alert_count"]) == ("failed", 0)
    assert "Synthetic scenario" not in meta["error"]  # the pattern, never the text
    # only the failed :DetectionRun, after the delete
    assert driver.names() == ["delete_detections", "merge_run", "prune_run", "merge_alerts"]
    node = driver.calls[1][1]["run"]
    assert (node["status"], node["alert_count"], node["params_sha256"]) == ("failed", 0, None)
    assert json.loads(node["summary"])["alerts"] == 0
    assert driver.calls[3][1]["rows"] == []


def test_an_alert_that_fails_c4_names_the_typology_and_fields_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = runner.run_detection

    def doctored(*args: Any, **kwargs: Any) -> runner.RunResult:
        result = real(*args, **kwargs)
        result.alerts[0]["headline"] = "Funds went to Secret Name Ltd" + "!" * 140
        return result

    monkeypatch.setattr(runner, "run_detection", doctored)
    with pytest.raises(runs.RunError) as raised:
        run(tmp_path)
    assert "a circular_flow alert does not validate against C4: headline" in str(raised.value)
    assert "Secret Name" not in str(raised.value)
    assert not (tmp_path / "run-20261021T101500-0001" / "alerts.jsonl").exists()


@pytest.mark.parametrize(
    "run_id",
    [
        "run-1",
        "../run-20261021T101500-7f3a",
        "run-20261021T101500-7F3A",
        "run-٢٠٢٦١٠٢١T101500-7f3a",  # Arabic-Indic
    ],
)
def test_a_run_id_must_have_the_c4_form(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(runs.RunError, match="must look like"):
        run(tmp_path, FakeDriver(), run_id=run_id)
    assert list(tmp_path.iterdir()) == []


def test_an_unwritable_runs_folder_fails_the_run_cleanly(tmp_path: Path) -> None:
    blocked = tmp_path / "runs"
    blocked.write_text("a file, not a folder", encoding="utf-8")
    driver = FakeDriver()
    with pytest.raises(runs.RunError, match="failed"):
        run(blocked, driver, run_id="run-20261021T101500-0004")
    node = driver.calls[1][1]["run"]  # the failed run still reaches Neo4j
    assert node["status"] == "failed"


def test_a_graph_without_a_window_records_none(tmp_path: Path) -> None:
    record = run(tmp_path, FakeDriver(), window_known=False)
    assert record.as_json()["window"] is None
    props = record.node_properties()
    assert props["window_start"] is None and props["window_end"] is None
    assert json.loads(props["summary"])["window"]["start"] == "2026-01-01T00:00:00Z"


def test_windows_from_days_and_the_overlay(tmp_path: Path) -> None:
    first = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
    last = datetime(2026, 3, 8, 16, 40, tzinfo=UTC)
    window = runs.day_window(first, last)
    assert (window.start, window.end) == (
        datetime(2026, 3, 2, tzinfo=UTC),
        datetime(2026, 3, 9, tzinfo=UTC),
    )
    meta = tmp_path / "overlay.json"
    meta.write_text(json.dumps({"period": {"start": "2025-01-01", "end": "2026-07-01"}}))
    window = runs.overlay_window(meta)
    assert (window.start, window.end) == (
        datetime(2025, 1, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC),
    )
    assert runs.window_of("2026-01-01", "2026-02-01T12:00:00Z").end.hour == 12
    for bad in (("2026-02-01", "2026-01-01"), ("2026-1-1", "2026-02-01"), ("x", "y")):
        with pytest.raises(runs.RunError):
            runs.window_of(*bad)
