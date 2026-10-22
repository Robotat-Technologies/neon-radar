"""The circular-flow fixture's known right answer is right for the right reason (M1.9b).

For every case in expected.json, the rules of the typology definition are checked here in
plain Python on the C1 records: cases A and B pass all of them, and cases C, D and E each fail
exactly the one rule they were built to break, so the detector's integration test cannot pass
by excluding them for another reason. The records stay synthetic (guardrail G1).

Case F (a real-looking holder of case A's origin account) runs in memory since M3.2: C2 L17
refuses to load it beside synthetic accounts, and under R-REAL its cycle is withheld (PHASE-3.md
M3.2 deliverable 6, decision 3)."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from neonradar_contracts.records import validate_batch, validate_record
from neonradar_detect import catalog, runner, runs
from neonradar_detect.detectors import circular_flow
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource

from .conftest import (
    CASE_A_ORIGIN,
    CIRCULAR_FLOW,
    EXPECTED,
    REAL_HOLDER,
    case_f_records,
    fixture_records,
    paid_ts,
)


def broken_rules(edge_ids: list[str]) -> set[str]:
    """The typology rules (detect/typologies/circular_flow.yaml, M1.9b) the cycle breaks."""
    by_id = {record["id"]: record for record in fixture_records()}
    payments = [by_id[edge_id]["properties"] for edge_id in edge_ids]
    times = [paid_ts(by_id[edge_id]) for edge_id in edge_ids]
    params = {name: spec.default for name, spec in CIRCULAR_FLOW.parameters.items()}
    accounts = [payment["payerAccount"][0] for payment in payments]
    chained = all(
        payment["beneficiaryAccount"][0] == accounts[(i + 1) % len(accounts)]
        for i, payment in enumerate(payments)
    )
    sent, returned = (float(payments[i]["amount"][0]) for i in (0, -1))
    rules = {
        "closed_chain": chained,
        "hops": params["min_hops"] <= len(payments) <= params["max_hops"],
        "simple": len(set(accounts)) == len(accounts),
        "time_order": all(a < b for a, b in pairwise(times)),
        "window": times[-1] - times[0] <= timedelta(days=params["max_window_days"]),
        "currency": payments[0]["currency"] == payments[-1]["currency"],
        "return_ratio": returned / sent >= params["min_return_ratio"],
    }
    return {name for name, holds in rules.items() if not holds}


def test_expected_parameters_are_the_catalog_defaults() -> None:
    """circular_flow 0.2.0 has more parameters; the four the fixture was built under keep their
    defaults (M3.2 deliverable 6: cases A to E keep their expectations)."""
    defaults = {name: spec.default for name, spec in CIRCULAR_FLOW.parameters.items()}
    assert EXPECTED["parameters"] == {name: defaults[name] for name in EXPECTED["parameters"]}


@pytest.mark.parametrize("case", sorted(EXPECTED["cases"]))
def test_each_case_breaks_only_its_own_rule(case: str) -> None:
    spec = EXPECTED["cases"][case]
    expected = set() if spec["fails"] is None else {spec["fails"]}
    assert broken_rules(spec["edge_ids"]) == expected
    assert spec["found"] == (spec["fails"] is None)


def test_found_lists_exactly_the_cases_that_pass() -> None:
    passing = [spec["edge_ids"] for spec in EXPECTED["cases"].values() if spec["found"]]
    assert sorted(EXPECTED["found"]) == sorted(passing)


def test_the_fixture_is_a_valid_synthetic_load_of_20_to_40_records() -> None:
    records = fixture_records()
    assert 20 <= len(records) <= 40
    assert all(record["id"].startswith("syn-") for record in records)
    issues = [issue for record in records for issue in validate_record(record)]
    assert issues + validate_batch(records, strict=True) == []


def test_case_f_is_a_valid_load_with_one_real_holder() -> None:
    records = case_f_records()
    assert [r["id"] for r in records if not r["id"].startswith("syn-")] == ["gbch-co-T0000001"]
    issues = [issue for record in records for issue in validate_record(record)]
    assert issues + validate_batch(records, strict=True) == []


def test_case_f_in_memory_is_withheld_under_r_real() -> None:
    """Case A's cycle through the real-looking holder is found and withheld (`activity_on_real`);
    case B and the same-holder return inside case A's accounts are all synthetic and emitted."""
    records = case_f_records()
    source = MemSource(from_records(records))
    found = source.paid_time_range()
    assert found is not None
    result = runner.run_detection(
        source,
        {"circular_flow": circular_flow.Params()},
        runs.day_window(*found),
        catalog.load(),
        run_id="run-20261021T101500-0f0f",
        created_at=datetime(2026, 10, 21, 10, 15, tzinfo=UTC),
        query_sha256={"circular_flow": runs.EVIDENCE_SHA256},
    )
    assert result.summary["withheld"]["activity_on_real"] == 1
    assert result.summary["typologies"]["circular_flow"]["findings"] == 3
    alerts = runs.validate(result.alerts)
    assert sorted(a.evidence.edge_ids for a in alerts) == sorted(
        [EXPECTED["cases"]["B"]["edge_ids"], ["syn-payment-cfa2", "syn-payment-cfa3"]]
    )
    named = {s.entity_id for a in alerts for s in a.subjects} | {
        n for a in alerts for n in a.evidence.node_ids
    }
    assert REAL_HOLDER["id"] not in named and CASE_A_ORIGIN not in named
