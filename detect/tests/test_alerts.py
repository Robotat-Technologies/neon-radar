"""Building C4 alerts from findings: the one data-flag helper and the wording checks (M1.9b)."""

import dataclasses
from datetime import UTC, datetime

import pytest

from neonradar_contracts.alert import Alert
from neonradar_detect.alerts import (
    AlertError,
    EdgeFact,
    EntityFact,
    Finding,
    build_alert,
    classify,
)
from neonradar_detect.detectors import circular_flow
from neonradar_detect.detectors.circular_flow import finding, query, resolve_parameters
from neonradar_detect.wording import WordingError, cycle_summary, format_amount, format_duration

from .conftest import CIRCULAR_FLOW, EXPECTED, fixture_records, query_row

SYN = EntityFact("syn-co-1", "Synthetic Co", True, ("nr_synthetic",))
REAL = EntityFact("gbch-co-T0000001", "Test Holder Ltd", False, ("gb_companies_house",))
ACCOUNT = EntityFact("syn-acct-1", "NRSYN0000000001", True, ("nr_synthetic",))
SYN_EDGE = EdgeFact("syn-payment-1", "syn-acct-1", "syn-acct-2", True, ("nr_synthetic",))
REAL_EDGE = EdgeFact("gbch-own-1", "gbch-co-1", "gbch-co-2", False, ("gb_companies_house",))


@pytest.mark.parametrize(
    ("holders", "edges", "expected"),
    [
        ([SYN], [SYN_EDGE], ("synthetic_scenario", False, True)),
        ([REAL], [SYN_EDGE], ("structural_pattern", True, True)),  # case F
        ([SYN], [SYN_EDGE, REAL_EDGE], ("structural_pattern", True, False)),
        ([SYN], [], ("synthetic_scenario", False, True)),  # C4 rule 3
        ([REAL], [], ("structural_pattern", True, False)),  # C4 rule 6
    ],
)
def test_classify(
    holders: list[EntityFact], edges: list[EdgeFact], expected: tuple[str, bool, bool]
) -> None:
    flags = classify([ACCOUNT], edges, [ACCOUNT], holders)
    assert (flags.wording_class, flags.involves_real_entities, flags.synthetic_activity) == expected


def test_classify_counts_a_holder_that_is_not_a_subject() -> None:
    """An intermediate account's holder decides the wording class too (5.4)."""
    flags = classify([ACCOUNT], [SYN_EDGE], [ACCOUNT, SYN], [SYN, REAL])
    assert flags.wording_class == "structural_pattern"
    assert flags.datasets == ("gb_companies_house", "nr_synthetic")


def test_a_missing_synthetic_flag_counts_as_real() -> None:
    from neonradar_detect.alerts import entity_fact

    fact = entity_fact({"id": "syn-co-9", "caption": "X", "datasets": ["nr_synthetic"]})
    assert fact.synthetic is False


def case_a() -> Finding:
    params = resolve_parameters(CIRCULAR_FLOW)
    row = query_row(fixture_records(), EXPECTED["cases"]["A"]["edge_ids"])
    run_parameters = {"origin": None, "max_window_days": 14, "min_return_ratio": 0.8, "limit": 1}
    return finding(row, query(2, 6), run_parameters, params)


def build(found: Finding) -> Alert:
    return build_alert(
        found,
        CIRCULAR_FLOW,
        detector_name=circular_flow.NAME,
        detector_version=circular_flow.VERSION,
        run_id="run-20261021T101500-7f3a",
        created_at=datetime(2026, 10, 21, tzinfo=UTC),
    )


def test_source_names_are_masked_before_the_wording_lint() -> None:
    """A holder caption is source data: a forbidden word in it does not fail the alert."""
    found = case_a()
    holder = dataclasses.replace(found.holders[0], caption="Fraud Prevention Services Ltd")
    summary = found.summary + " Fraud Prevention Services Ltd holds the origin account."
    alert = build(dataclasses.replace(found, holders=(holder,), summary=summary))
    assert "Fraud Prevention" in alert.explanation.summary


def test_neonradar_wording_that_fails_the_lint_fails_the_alert() -> None:
    found = case_a()
    with pytest.raises(WordingError, match=r"explanation\.summary"):
        build(dataclasses.replace(found, summary="These funds look laundered."))
    steps = (dataclasses.replace(found.steps[0], text="A suspicious payment."), *found.steps[1:])
    with pytest.raises(WordingError, match="step 1"):
        build(dataclasses.replace(found, steps=steps))


def test_masking_is_by_whole_token_only() -> None:
    """A caption inside a longer word is not masked, so it cannot hide NeonRadar's words."""
    found = case_a()
    holder = dataclasses.replace(found.holders[0], caption="launder")
    with pytest.raises(WordingError):
        build(dataclasses.replace(found, holders=(holder,), summary="It was laundered."))


def test_evidence_edges_must_end_at_evidence_nodes() -> None:
    found = case_a()
    stray = dataclasses.replace(found.edges[0], target="syn-acct-elsewhere")
    with pytest.raises(AlertError, match="outside the evidence"):
        build(dataclasses.replace(found, edges=(stray, *found.edges[1:])))


def test_metrics_must_be_finite() -> None:
    found = case_a()
    with pytest.raises(AlertError, match="finite"):
        build(dataclasses.replace(found, metrics={**found.metrics, "return_ratio": float("nan")}))


@pytest.mark.parametrize(
    ("amount", "text"), [(120000.0, "120,000"), (141968.95, "141,968.95"), (0.5, "0.50")]
)
def test_format_amount(amount: float, text: str) -> None:
    assert format_amount(amount) == text


@pytest.mark.parametrize(
    ("hours", "text"), [(1.2, "1 hour"), (30.4, "30 hours"), (144.0, "6 days"), (151.7, "6.3 days")]
)
def test_format_duration(hours: float, text: str) -> None:
    assert format_duration(hours) == text


def test_cycle_summary_counts_the_other_accounts() -> None:
    text = cycle_summary("NRSYN0000000001", "GBP", 10.0, 9.5, 1, 50.0)
    assert text == (
        "GBP 10 left account NRSYN0000000001 and GBP 9.50 came back to it after passing"
        " through one other account in 2.1 days."
    )
