"""Headline rendering from wording templates (PHASE-1.md 5.4, 7.1)."""

import json
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.alert import Alert
from neonradar_detect.catalog import TypologyFile, Wording, load_typology
from neonradar_detect.wording import WordingError, format_metric, render_headline

ROOT = Path(__file__).resolve().parents[2]
CIRCULAR_FLOW = load_typology(
    Path(__file__).parent / "fixtures" / "typologies" / "circular_flow.yaml"
)
EXAMPLE = Alert.model_validate_json(
    (ROOT / "contracts" / "examples" / "c4" / "circular_flow.json").read_text(encoding="utf-8")
)


def with_template(template: str) -> TypologyFile:
    data: dict[str, Any] = CIRCULAR_FLOW.model_dump()
    data["wording"]["headline_structural"] = template
    data["metrics"] = [*data["metrics"], "count"]
    return TypologyFile.model_validate(data)


def test_synthetic_headline_matches_the_c4_example() -> None:
    headline = render_headline(CIRCULAR_FLOW, "synthetic_scenario", EXAMPLE.metrics)
    assert headline == EXAMPLE.headline


def test_structural_headline() -> None:
    headline = render_headline(CIRCULAR_FLOW, "structural_pattern", EXAMPLE.metrics)
    assert headline == "Funds returned to the originating account through 4 transfers within 7 days"


def test_missing_metric() -> None:
    with pytest.raises(WordingError, match="metric 'duration_days' is missing"):
        render_headline(CIRCULAR_FLOW, "structural_pattern", {"cycle_length": 4})


def test_typology_without_wording() -> None:
    data = CIRCULAR_FLOW.model_dump()
    data.update(detector=None, wording=None)
    with pytest.raises(WordingError, match="has no wording templates"):
        render_headline(TypologyFile.model_validate(data), "structural_pattern", {})


def test_output_that_fails_the_lint_is_refused() -> None:
    """The catalog rejects such a template; render_headline still checks its own output."""
    wording = Wording.model_construct(
        headline_structural="{cycle_length} suspicious transfers", headline_synthetic="x"
    )
    typology = CIRCULAR_FLOW.model_copy(update={"wording": wording})
    with pytest.raises(WordingError, match="refused by the wording lint"):
        render_headline(typology, "structural_pattern", {"cycle_length": 3})


def test_structural_headline_never_says_synthetic_scenario() -> None:
    """B1: a metric value cannot carry the phrase into a structural_pattern headline."""
    typology = with_template("Funds returned in {currency}")
    metrics = {"currency": "a synthetic scenario", "count": 1}
    with pytest.raises(WordingError, match="only a synthetic_scenario headline"):
        render_headline(typology, "structural_pattern", metrics)


def test_structural_headline_phrase_check_reads_normalised_text() -> None:
    """A fullwidth "s" does not hide the phrase (NFKC before SYNTHETIC_PHRASE)."""
    typology = with_template("Funds returned in {currency}")
    metrics = {"currency": "a \uff53ynthetic scenario", "count": 1}
    with pytest.raises(WordingError, match="only a synthetic_scenario headline"):
        render_headline(typology, "structural_pattern", metrics)


def test_a_metric_value_cannot_smuggle_in_forbidden_wording() -> None:
    typology = with_template("Funds returned in {currency}")
    with pytest.raises(WordingError, match="refused by the wording lint"):
        render_headline(typology, "structural_pattern", {"currency": "laundered EUR", "count": 1})


def test_headline_longer_than_c4_allows_is_refused() -> None:
    typology = with_template("{count}" + " transfers" * 14)
    with pytest.raises(WordingError, match="C4 allows 140"):
        render_headline(typology, "structural_pattern", {"count": 12})


@pytest.mark.parametrize(
    ("value", "spec", "text"),
    [
        (4, "", "4"),
        (1234567, "", "1,234,567"),
        (120000.0, "", "120,000"),
        (151.7, "", "151.7"),
        (0.96, "", "0.96"),
        (0.125, "", "0.12"),
        (151.666, ".0f", "152"),
        ("EUR", "", "EUR"),
    ],
)
def test_format_metric(value: int | float | str, spec: str, text: str) -> None:
    assert format_metric(value, spec) == text


def test_format_spec_on_a_string_metric_is_a_wording_error() -> None:
    with pytest.raises(WordingError, match="does not fit metric value 'EUR'"):
        format_metric("EUR", ".0f")
    typology = with_template("Funds returned in {currency:.0f}")
    with pytest.raises(WordingError):
        render_headline(typology, "structural_pattern", {"currency": "EUR", "count": 1})


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_format_metric_refuses_odd_values(value: float) -> None:
    with pytest.raises(WordingError):
        format_metric(value)


def test_render_uses_the_placeholder_format_spec() -> None:
    typology = with_template("Funds returned within {duration_hours:.0f} hours")
    assert (
        render_headline(typology, "structural_pattern", {"duration_hours": 151.7})
        == "Funds returned within 152 hours"
    )


def test_example_metrics_round_trip() -> None:
    assert json.loads(json.dumps(EXAMPLE.metrics)) == EXAMPLE.metrics
