"""The circular-flow detector without a database: query template, parameters, pattern
strength, and the finding and alert for each fixture case (PHASE-1.md M1.9b)."""

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from neonradar_contracts.alert import Alert, compute_alert_id, query_sha256
from neonradar_detect.alerts import build_alert
from neonradar_detect.detectors import circular_flow
from neonradar_detect.detectors.circular_flow import (
    finding,
    pattern_strength,
    query,
    resolve_parameters,
)

from .conftest import (
    CASE_A_ORIGIN,
    CIRCULAR_FLOW,
    EXPECTED,
    case_f_records,
    fixture_records,
    query_row,
)

RUN_ID = "run-20261021T101500-7f3a"
CREATED = datetime(2026, 10, 21, 10, 15, 2, tzinfo=UTC)
CASE_A = EXPECTED["cases"]["A"]["edge_ids"]
CASE_B = EXPECTED["cases"]["B"]["edge_ids"]


def alert_for(records: list[dict[str, Any]], edge_ids: list[str], **kwargs: Any) -> Alert:
    params = resolve_parameters(CIRCULAR_FLOW)
    cypher = query(params.min_hops, params.max_hops)
    run_parameters = {"origin": None, "max_window_days": 14, "min_return_ratio": 0.8, "limit": 1000}
    found = finding(query_row(records, edge_ids), cypher, run_parameters, params)
    options: dict[str, Any] = {
        "detector_name": circular_flow.NAME,
        "detector_version": circular_flow.VERSION,
        "run_id": RUN_ID,
        "created_at": CREATED,
    }
    return build_alert(found, CIRCULAR_FLOW, **(options | kwargs))


def test_query_writes_the_hop_bounds_into_the_fixed_template() -> None:
    text = query(2, 6)
    assert "MATCH p = (a:Account)-[t:PAID]->{2,6}(a)" in text
    assert "MIN_HOPS" not in text and "MAX_HOPS" not in text
    assert "LIMIT $limit" in text
    assert query(3, 8).count("->{3,8}(") == 1


@pytest.mark.parametrize(
    ("low", "high"), [(1, 6), (2, 9), (6, 2), (0, 0), (True, 6), ("2", 6), (2.0, 6)]
)
def test_query_refuses_bounds_outside_the_allowed_range(low: Any, high: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        query(low, high)


def test_query_reads_only_c2_labels_types_and_properties() -> None:
    text = query(2, 6)
    labels = set(re.findall(r"\(\w*:(\w+)", text)) | set(re.findall(r"\[\w*:(\w+)\]", text))
    assert labels == {"Account", "PAID", "LegalEntity", "HOLDS_ACCOUNT"}


def test_parameters_default_to_the_catalog_and_respect_its_ranges() -> None:
    params = resolve_parameters(CIRCULAR_FLOW)
    assert (params.min_hops, params.max_hops) == (2, 6)
    assert (params.max_window_days, params.min_return_ratio) == (14, 0.8)
    assert resolve_parameters(CIRCULAR_FLOW, {"max_hops": 8}).max_hops == 8
    for bad in ({"max_hops": 9}, {"max_window_days": 0}, {"min_return_ratio": 1.5}):
        with pytest.raises(ValueError, match="outside"):
            resolve_parameters(CIRCULAR_FLOW, bad)
    with pytest.raises(ValueError, match="unknown"):
        resolve_parameters(CIRCULAR_FLOW, {"origin": 1})
    with pytest.raises(ValueError, match="integers"):
        resolve_parameters(CIRCULAR_FLOW, {"min_hops": 2.5})
    with pytest.raises(ValueError, match="finite"):
        resolve_parameters(CIRCULAR_FLOW, {"max_window_days": float("nan")})


def test_pattern_strength_follows_the_documented_formula() -> None:
    # PHASE-1.md 5.4 example: 0.5 x 0.96 + 0.3 x (1 - 151.7 / 336) + 0.2 x 0.75
    assert pattern_strength(0.96, 151.7, 14, 4) == 0.79
    assert pattern_strength(1.0, 0.0, 14, 6) == 1.0
    assert pattern_strength(2.0, 0.0, 14, 8) == 1.0  # clipped
    assert pattern_strength(0.0, 336.0, 14, 2) == 0.05


def test_case_a_alert_matches_the_typology_and_the_contract() -> None:
    alert = alert_for(fixture_records(), CASE_A)
    assert alert.metrics == EXPECTED["cases"]["A"]["metrics"]
    assert alert.pattern_strength == EXPECTED["cases"]["A"]["pattern_strength"]
    assert alert.priority == "high"
    assert alert.wording_class == "synthetic_scenario"
    assert alert.headline == (
        "Synthetic scenario: funds returned to the originating account through 4 transfers"
        " within 6 days"
    )
    assert alert.evidence.edge_ids == CASE_A
    assert alert.evidence.node_ids == [f"syn-acct-cfa{n}" for n in (1, 2, 3, 4)]
    assert [(s.entity_id, s.role) for s in alert.subjects] == [
        (CASE_A_ORIGIN, "origin"),
        ("syn-co-cf01", "origin_holder"),
    ]
    assert alert.explanation.steps[0].text == (
        "NRSYN9100000001 sent EUR 120,000 to NRSYN9100000002 on 2 March 2026."
    )
    assert [step.edge_ids for step in alert.explanation.steps] == [[edge] for edge in CASE_A]
    assert alert.explanation.summary == (
        "EUR 120,000 left account NRSYN9100000001 and EUR 115,200 came back to it after"
        " passing through three other accounts in 6 days."
    )
    assert alert.evidence.query.parameters["origin"] == CASE_A_ORIGIN
    assert alert.detector.query_sha256 == query_sha256(query(2, 6))
    assert alert.evidence.window is not None
    assert (alert.evidence.window.start, alert.evidence.window.end) == (
        "2026-03-02T09:00:00Z",
        "2026-03-08T09:00:00Z",
    )
    assert alert.data_flags.model_dump() == {
        "involves_real_entities": False,
        "synthetic_activity": True,
        "datasets": ["nr_synthetic"],
    }


def test_case_b_is_a_synthetic_scenario_too() -> None:
    alert = alert_for(fixture_records(), CASE_B)
    assert alert.wording_class == "synthetic_scenario"
    assert alert.metrics["cycle_length"] == 3
    assert "two other accounts" in alert.explanation.summary


def test_alert_id_depends_on_the_evidence_only() -> None:
    first = alert_for(fixture_records(), CASE_A)
    later = alert_for(
        fixture_records(),
        CASE_A,
        run_id="run-20261022T080000-0b1c",
        created_at=datetime(2026, 10, 22, 8, tzinfo=UTC),
    )
    assert first.alert_id == later.alert_id
    assert first.alert_id == compute_alert_id(
        "circular_flow", "0.1.0", first.evidence.node_ids, first.evidence.edge_ids
    )


def test_case_f_real_holder_gives_a_structural_pattern() -> None:
    """M1.9b case F: the origin account's holder is not synthetic (guardrail G1)."""
    alert = alert_for(case_f_records(), CASE_A)
    assert alert.wording_class == "structural_pattern"
    assert alert.data_flags.involves_real_entities is True
    assert alert.data_flags.synthetic_activity is True
    assert alert.data_flags.datasets == ["gb_companies_house", "nr_synthetic"]
    assert alert.headline == (
        "Funds returned to the originating account through 4 transfers within 6 days"
    )
    assert ("gbch-co-T0000001", "origin_holder") in [
        (subject.entity_id, subject.role) for subject in alert.subjects
    ]
