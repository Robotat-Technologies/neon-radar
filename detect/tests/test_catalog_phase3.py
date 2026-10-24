"""The Phase 3 catalog (PHASE-3.md M3.2 deliverable 3, 7.5.2): shape names, variants, detail,
filters, list defaults, the frozen `Typology` view and `params_for`."""

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from neonradar_detect import catalog, wording
from neonradar_detect.catalog import CatalogError, TypologyFile, load, params_for, placeholders
from neonradar_detect.detectors import circular_flow

REPOSITORY_FILE = catalog.TYPOLOGY_DIR / "circular_flow.yaml"


def phase3() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(REPOSITORY_FILE.read_text(encoding="utf-8"))
    return data


def write(folder: Path, data: dict[str, Any]) -> Path:
    path = folder / f"{data['slug']}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_the_repository_catalog_loads_as_the_frozen_view() -> None:
    view = load()
    cf = view["circular_flow"]
    assert cf.shape_name == "funds returning to where they started"
    assert cf.detector == "neonradar_detect.detectors.circular_flow"
    assert cf.parameters["same_holder"] == {"default": True}
    assert cf.parameters["min_hops"] == {"default": 2, "min": 2, "max": 8}
    assert "variants" not in cf.wording and "detail" not in cf.wording
    assert view["trade_based_ml"].detector == "" and view["trade_based_ml"].shape_name == ""
    with pytest.raises(TypeError):
        cf.wording["headline_synthetic"] = "x"  # type: ignore[index]


@pytest.mark.parametrize(
    ("template", "names"),
    [
        ("{a} and {b|money}", ["a", "b"]),
        ("{a|pct} of {n|n:day} in {c|n:company:companies}", ["a", "n", "c"]),
        ("{a:.0f} hours", ["a"]),  # Phase 1's format spec still parses
    ],
)
def test_placeholders_accept_the_phase3_filters(template: str, names: list[str]) -> None:
    assert placeholders(template) == names


@pytest.mark.parametrize(
    ("template", "message"),
    [
        ("{a|euros}", "a filter is money, pct or n"),
        ("{a|n}", "a filter is money, pct or n"),
        ("{a|money:.0f}", "a filter is money, pct or n"),
        ("{a.b|money}", "must be a metric name"),
    ],
)
def test_unknown_filters_are_refused(template: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        placeholders(template)


def test_the_renderers_placeholder_pattern_is_the_catalogs() -> None:
    assert catalog.RENDERED.pattern == wording.PLACEHOLDER.pattern


def test_variants_and_detail_follow_the_main_pairs_rules() -> None:
    data = phase3()
    pair = {
        "headline_structural": "Funds back at {return_point} after {cycle_length} transfers",
        "headline_synthetic": "Synthetic scenario: funds back after {cycle_length} transfers",
        "detail": "The return was {return_ratio|pct} of the amount sent.",
    }
    data["wording"]["variants"] = {"same_holder": pair}
    typology = TypologyFile.model_validate(data)
    assert typology.wording is not None
    assert typology.wording.variants["same_holder"].detail == pair["detail"]
    for key, value, message in [
        ("headline_structural", "{nope} transfers", "not metrics"),
        ("headline_synthetic", "Funds back", "must start with 'Synthetic scenario'"),
        ("detail", "A synthetic scenario of {cycle_length}", "must not say 'synthetic scenario'"),
        ("detail", "Funds were laundered", "wording lint"),
    ]:
        bad = phase3()
        bad["wording"]["variants"] = {"same_holder": {**pair, key: value}}
        with pytest.raises(ValueError, match=message):
            TypologyFile.model_validate(bad)


def test_money_needs_a_currency_metric() -> None:
    data = phase3()
    data["metrics"] = [m for m in data["metrics"] if m != "currency"]
    data["wording"]["headline_structural"] = "{sent_amount|money} returned"
    with pytest.raises(ValueError, match="currency must be a metric"):
        TypologyFile.model_validate(data)


def test_the_shape_name_passes_the_lint() -> None:
    with pytest.raises(ValueError, match="shape_name"):
        TypologyFile.model_validate({**phase3(), "shape_name": "laundering loops"})


def test_a_detector_is_the_packages_module_for_the_slug(tmp_path: Path) -> None:
    write(tmp_path, {**phase3(), "detector": "os.path"})
    with pytest.raises(CatalogError, match=r"detector must be neonradar_detect\.detectors"):
        load(tmp_path)


def test_list_and_boolean_defaults_need_no_bounds() -> None:
    data = phase3()
    data["parameters"]["exclude"] = {"default": ["QQ1 1QQ", "QQ2 2QQ"]}
    assert TypologyFile.model_validate(data).parameters["exclude"].default == ["QQ1 1QQ", "QQ2 2QQ"]


def test_load_refuses_what_the_phase3_renderer_cannot_render(tmp_path: Path) -> None:
    without = phase3()
    del without["shape_name"]
    write(tmp_path, without)
    with pytest.raises(CatalogError, match="needs shape_name"):
        load(tmp_path)
    spec = phase3()
    spec["wording"]["headline_structural"] = "Funds returned within {duration_hours:.0f} hours"
    write(tmp_path, spec)
    with pytest.raises(CatalogError, match="has a format spec"):
        load(tmp_path)
    brace = phase3()
    brace["wording"]["headline_structural"] = "Funds returned {{literally}} {cycle_length}"
    write(tmp_path, brace)
    with pytest.raises(CatalogError, match="brace"):
        load(tmp_path)


@pytest.mark.parametrize(
    ("where", "text", "pattern"),
    [
        ("shape_name", "funds layering through accounts", r"\blayering\b"),
        ("wording.headline_structural", "Funds returned via {cycle_length} smurfs", r"\bsmurf\w*"),
        (
            "wording.detail",
            "The account is blocked after {cycle_length} transfers",
            r"\bis blocked\b",
        ),
        (
            "wording.variants.same_holder.headline_structural",
            "A shell held {cycle_length} accounts",
            r"\bshell\b",
        ),
    ],
)
def test_load_applies_the_run_time_lint_to_shape_names_and_templates(
    tmp_path: Path, where: str, text: str, pattern: str
) -> None:
    """Phase 1's lint in `TypologyFile` does not know Phase 2's phrases or Phase 3's conduct words,
    so `load()` applies `wording_lint.violations`: such a file fails when it loads, not mid-run."""
    data = phase3()
    data["wording"]["variants"] = {
        "same_holder": {
            "headline_structural": "Funds back after {cycle_length} transfers",
            "headline_synthetic": "Synthetic scenario: funds back after {cycle_length} transfers",
        }
    }
    *parents, key = where.split(".")
    target: dict[str, Any] = data
    for part in parents:
        target = target[part]
    target[key] = text
    TypologyFile.model_validate(data)  # Phase 1's lint lets it through
    write(tmp_path, data)
    with pytest.raises(CatalogError) as raised:
        load(tmp_path)
    assert f"{where} fails the wording lint (7.5.2): {pattern}" in str(raised.value)


def test_load_applies_the_run_time_lint_to_false_positive_notes(tmp_path: Path) -> None:
    """The notes go unchanged into every alert's `explanation.false_positive_notes`."""
    data = phase3()
    data["false_positives"] = ["Refunds between related accounts", "The account is blocked"]
    TypologyFile.model_validate(data)  # Phase 1's lint lets it through
    write(tmp_path, data)
    with pytest.raises(CatalogError) as raised:
        load(tmp_path)
    assert r"false_positives[1] fails the wording lint (7.5.2): \bis blocked\b" in str(raised.value)


@dataclass(frozen=True)
class _Params:
    hops: int = 2
    ratio: float = 0.8
    on: bool = True
    codes: tuple[str, ...] = ()


def _typology() -> catalog.Typology:
    parameters = {
        "hops": {"default": 2, "min": 1, "max": 8},
        "ratio": {"default": 0.8, "min": 0.0, "max": 1.0},
        "on": {"default": True},
        "codes": {"default": ["a"]},
    }
    return dataclasses.replace(load()["circular_flow"], parameters=parameters)


def test_params_for_applies_overrides_within_bounds_and_types() -> None:
    module = SimpleNamespace(Params=_Params)
    t = _typology()
    assert params_for(t, module) == _Params(2, 0.8, True, ("a",))  # type: ignore[arg-type]
    got = params_for(t, module, {"hops": 3, "ratio": 1, "codes": ["x", "y"]})  # type: ignore[arg-type]
    assert got == _Params(3, 1, True, ("x", "y"))
    for overrides, error, message in [
        ({"nope": 1}, KeyError, "unknown parameter nope"),
        ({"hops": 9}, ValueError, "outside"),
        ({"hops": 2.0}, ValueError, "type of its default"),
        ({"hops": True}, ValueError, "type of its default"),
        ({"on": "yes"}, ValueError, "type of its default"),
        ({"codes": "a"}, ValueError, "type of its default"),
    ]:
        with pytest.raises(error, match=message):
            params_for(t, module, overrides)  # type: ignore[arg-type]


def test_params_for_the_real_detector_are_its_defaults() -> None:
    view = load()["circular_flow"]
    assert params_for(view, circular_flow) == circular_flow.Params()
    assert params_for(view, circular_flow, {"min_hops_same_account": 2}).min_hops_same_account == 2
