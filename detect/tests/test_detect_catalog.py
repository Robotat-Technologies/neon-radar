"""The typology catalog shape and rules (PHASE-1.md 5.4, M1.7c)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from neonradar_detect.catalog import (
    TYPOLOGY_DIR,
    CatalogError,
    TypologyFile,
    load_catalog,
    load_typology,
    placeholders,
    render_index,
)

FIXTURES = Path(__file__).parent / "fixtures" / "typologies"
CIRCULAR_FLOW = FIXTURES / "circular_flow.yaml"


def spec_example() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(CIRCULAR_FLOW.read_text(encoding="utf-8"))
    return data


def write(folder: Path, data: dict[str, Any], name: str | None = None) -> Path:
    path = folder / f"{name or data['slug']}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def without_detector() -> dict[str, Any]:
    """The shape 5.4 allows for a typology that has no detector yet."""
    data = spec_example()
    data.update(detector=None, parameters={}, metrics=[], wording=None, generator_scenario=None)
    return data


def test_spec_example_loads_as_a_draft() -> None:
    typology = load_typology(CIRCULAR_FLOW)
    assert typology.slug == "circular_flow"
    assert typology.status == "draft"
    assert typology.approved_by is None
    assert typology.detector == "neonradar_detect.detectors.circular_flow"
    assert typology.parameters["min_return_ratio"].default == 0.8
    assert placeholders(typology.wording.headline_synthetic) == [  # type: ignore[union-attr]
        "cycle_length",
        "duration_days",
    ]


def test_catalog_by_slug(tmp_path: Path) -> None:
    write(tmp_path, spec_example())
    second = {**without_detector(), "slug": "fan_in_collection"}
    write(tmp_path, {**second, "doc": "docs/typologies/fan-in-collection.md"})
    (tmp_path / "notes.txt").write_text("not a typology", encoding="utf-8")
    assert list(load_catalog(tmp_path)) == ["circular_flow", "fan_in_collection"]


def test_empty_or_missing_folder_is_an_empty_catalog(tmp_path: Path) -> None:
    assert load_catalog(tmp_path) == {}
    assert load_catalog(tmp_path / "missing") == {}


def test_repository_catalog_loads() -> None:
    assert all(t.status in {"draft", "approved", "retired"} for t in load_catalog().values())
    assert TYPOLOGY_DIR.parts[-2:] == ("detect", "typologies")


def test_typology_without_a_detector_may_leave_fields_empty() -> None:
    typology = TypologyFile.model_validate(without_detector())
    assert typology.wording is None
    assert typology.parameters == {}


def test_approved_needs_approved_by() -> None:
    data = {**spec_example(), "status": "approved"}
    with pytest.raises(ValueError, match="approved needs approved_by"):
        TypologyFile.model_validate(data)
    assert TypologyFile.model_validate({**data, "approved_by": "@researcher"}).approved_by


@pytest.mark.parametrize("field", ["parameters", "metrics", "wording"])
def test_a_detector_needs_parameters_metrics_and_wording(field: str) -> None:
    data = spec_example()
    data[field] = None if field == "wording" else type(data[field])()
    if field == "metrics":
        data["wording"] = None
    with pytest.raises(ValueError, match=f"a typology with a detector needs .*{field}"):
        TypologyFile.model_validate(data)


@pytest.mark.parametrize(
    ("template", "message"),
    [
        ("{cycle_length} transfers in {window_days} days", "not metrics: \\['window_days'\\]"),
        ("{} transfers", "must be a metric name"),
        ("{0} transfers", "must be a metric name"),
        ("{metrics.cycle_length} transfers", "must be a metric name"),
        ("{cycle_length!r} transfers", "must be a metric name"),
        ("{cycle_length transfers", "expected '}'"),
    ],
)
def test_placeholders_must_be_listed_metrics(template: str, message: str) -> None:
    data = spec_example()
    data["wording"]["headline_structural"] = template
    with pytest.raises(ValueError, match=message):
        TypologyFile.model_validate(data)


def test_format_specs_are_allowed() -> None:
    data = spec_example()
    data["wording"]["headline_structural"] = "Funds returned within {duration_hours:.0f} hours"
    TypologyFile.model_validate(data)


def test_structural_template_never_says_synthetic_scenario() -> None:
    data = spec_example()
    data["wording"]["headline_structural"] = data["wording"]["headline_synthetic"]
    with pytest.raises(ValueError, match="must not say 'synthetic scenario'"):
        TypologyFile.model_validate(data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"citations": []}, "at least 1 item"),
        ({"citations": ["fatf"]}, "citations"),
        ({"doc": "docs/typologies/circular_flow.md"}, "doc"),
        ({"doc": "docs/typologies/round-trip.md"}, "doc must be docs/typologies/circular-flow.md"),
        ({"version": 1.0}, "version"),
        ({"owner": "robotat-com"}, "owner"),
        ({"tier": "optional"}, "tier"),
        ({"metrics": ["cycle_length", "cycle_length"]}, "must not repeat"),
        ({"detector": "circular_flow"}, "detector"),
        ({"labels": ["x"]}, "Extra inputs are not permitted"),
    ],
)
def test_shape_rules(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TypologyFile.model_validate({**spec_example(), **changes})


@pytest.mark.parametrize(
    "parameter",
    [
        {"default": 9, "min": 2, "max": 8},
        {"default": 1, "min": 2},
        {"default": "x", "min": 3, "max": 1},
    ],
)
def test_parameter_defaults_stay_in_range(parameter: dict[str, Any]) -> None:
    data = spec_example()
    data["parameters"]["max_hops"] = parameter
    with pytest.raises(ValueError, match=r"outside|must not exceed"):
        TypologyFile.model_validate(data)


def test_errors_name_the_file(tmp_path: Path) -> None:
    write(tmp_path, {**spec_example(), "status": "approved"})
    with pytest.raises(CatalogError, match=r"^circular_flow\.yaml: "):
        load_catalog(tmp_path)


def test_slug_must_match_the_file_name(tmp_path: Path) -> None:
    write(tmp_path, spec_example(), name="round_trip")
    with pytest.raises(CatalogError, match="must match the file name"):
        load_catalog(tmp_path)


def test_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("slug: [unclosed\n", encoding="utf-8")
    with pytest.raises(CatalogError, match=r"^broken\.yaml: "):
        load_catalog(tmp_path)


def test_render_index_of_an_empty_catalog() -> None:
    text = render_index({})
    assert text.startswith("# Typology catalog\n")
    assert "No typology files yet." in text
    assert text.endswith("\n")


def test_render_index_lists_each_typology() -> None:
    first = TypologyFile.model_validate(spec_example())
    second = TypologyFile.model_validate(
        {**without_detector(), "slug": "fan_in_collection", "name": "Fan-in | collection",
         "doc": "docs/typologies/fan-in-collection.md"}
    )  # fmt: skip
    lines = render_index({"fan_in_collection": second, "circular_flow": first}).splitlines()
    rows = [line for line in lines if line.startswith("| [")]
    assert rows == [
        "| [`circular_flow`](circular-flow.md) | Round-tripping or circular flows | core | draft "
        "| @TODO | yes |",
        "| [`fan_in_collection`](fan-in-collection.md) | Fan-in \\| collection | core | draft "
        "| @TODO | no |",
    ]
