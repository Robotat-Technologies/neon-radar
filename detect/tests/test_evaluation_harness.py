from pathlib import Path

import pytest
from neonradar_detect.evaluation import harness, metrics, report

HEAD = "# synthetic: true\n# label_schema: 2.0.0\n"
SCENARIOS = (
    "scenario_id,typology,variant,is_lookalike,start_ts,end_ts,participants,difficulty,split,"
    "n_transactions,n_accounts,n_entities,n_relationships\n"
    "scn-000001,circular_flow,same_account,false,,,,easy,dev,3,3,3,0\n"
    "scn-000002,circular_flow,refund,true,,,,,dev,2,2,2,0\n"
)
TRANSACTIONS = (
    "tx_id,scenario_id,typology,step,role,is_illicit,variant,is_lookalike,is_core\n"
    "p1,scn-000001,circular_flow,1,hop,true,same_account,false,true\n"
    "p2,scn-000001,circular_flow,2,hop,true,same_account,false,true\n"
    "p3,scn-000001,circular_flow,3,hop,true,same_account,false,true\n"
    "r1,scn-000002,circular_flow,1,payment,false,refund,true,true\n"
    "r2,scn-000002,circular_flow,2,refund,false,refund,true,true\n"
)
PARTICIPANTS = (
    "scenario_id,object_kind,object_id,role,is_core\n"
    "scn-000001,account,a1,origin,true\n"
    "scn-000002,account,b1,origin,true\n"
)


def _labels(tmp_path: Path, schema: str = "2.0.0") -> Path:
    head = HEAD.replace("2.0.0", schema)
    for name, body in (
        ("scenarios", SCENARIOS),
        ("transactions", TRANSACTIONS),
        ("participants", PARTICIPANTS),
    ):
        (tmp_path / f"{name}.csv").write_text(head + body, encoding="utf-8")
    return tmp_path


def _alert(aid: str, edges: list[str], priority: str = "high") -> dict:
    return {
        "alert_id": aid,
        "typology": "circular_flow",
        "priority": priority,
        "evidence": {"edge_ids": edges, "node_ids": ["a1"]},
        "subjects": [{"entity_id": "a1", "role": "origin"}],
    }


def test_scenario_views_read_labels_v2(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    assert [v.scenario_id for v in views] == ["scn-000001", "scn-000002"]
    assert views[0].tx_ids == {"p1", "p2", "p3"} and views[0].core == {"a1"}
    assert views[1].is_lookalike and views[1].participants == {"b1": "origin"}


def test_labels_of_another_major_schema_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="label schema"):
        harness.scenario_views(_labels(tmp_path, "3.0.0"))


def test_evaluate_world_counts_kinds_and_bands(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    payments = frozenset({"p1", "p2", "p3", "r1", "r2", "x1", "x2"})
    alerts = [
        _alert("alr-a", ["p1", "p2", "p3"]),
        _alert("alr-b", ["p1", "p2", "p3", "x1"], "medium"),
        _alert("alr-c", ["r1", "r2"], "low"),
        _alert("alr-d", ["x1", "x2"], "low"),
    ]
    result = harness.evaluate_world(1, alerts, views, payments, ["circular_flow"])
    outcome = result.outcomes["circular_flow"]
    assert harness.counts(outcome) == {
        "alerts": 4,
        "true": 1,
        "duplicate": 1,
        "lookalike": 1,
        "partial": 0,
        "other": 0,
        "background": 1,
        "planted": 1,
        "detected": 1,
        "lookalikes": 1,
        "lookalikes_alerted": 1,
    }
    assert result.bands["circular_flow"] == {"high": (1, 1), "medium": (0, 1), "low": (0, 2)}
    pooled = harness.pooled_bands([result, result], "circular_flow")
    assert pooled["high"] == (2, 2) and pooled["low"] == (0, 4)


def test_report_renders_rates_intervals_and_fixed_text(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    payments = frozenset({"p1", "p2", "p3", "r1", "r2"})
    results = [
        harness.evaluate_world(
            seed, [_alert("alr-a", ["p1", "p2", "p3"])], views, payments, ["circular_flow"]
        )
        for seed in (1, 2)
    ]
    figures = [metrics.figures({r.seed: r.outcomes for r in results}, "circular_flow")]
    bands = {"circular_flow": harness.pooled_bands(results, "circular_flow")}
    meta = report.ReportMeta(
        "Detection evaluation (development)",
        "dev",
        (1, 2),
        "memory",
        "2026-11-02T09:00:00Z",
        "synth-eval",
        "1.0.0",
        "2.0.0",
        "1",
        "0" * 64,
        {"circular_flow": "0.2.0"},
    )
    text = report.markdown(figures, bands, meta)
    assert "| `circular_flow` | 1.00 (2/2) | [0.34, 1.00] | 1.00 (2/2) | [0.34, 1.00] |" in text
    assert "1.00 (2/2) | 2 / 0 / 0 / 0 / 0 / 0 | 0/2 |" in text
    assert report.READING_NOTES in text and report.LIMITATIONS in text
    data = report.to_json(figures, bands, meta)
    assert data["typologies"]["circular_flow"]["recall"]["k"] == 2
    assert data["typologies"]["circular_flow"]["bands"]["high"] == [2, 2]


def test_an_empty_rate_prints_n_zero() -> None:
    empty = metrics.rate([(0, 0), (0, 0)])
    assert report.fmt_rate(empty) == "n = 0" and report.fmt_interval(empty.headline) == ""
