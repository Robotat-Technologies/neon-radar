"""Contract tests for the dataset registry, contracts/datasets.yaml (PHASE-1.md 5.1, 5.5;
PHASE-2.md 5.1 and 5.4 for C1 1.1.0)."""

from collections.abc import Callable
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from neonradar_contracts.datasets import REGISTRY_PATH, Dataset, Registry, load_registry
from neonradar_contracts.records import SYNTHETIC_DATASET, SYNTHETIC_PREFIX

pytestmark = pytest.mark.contract


def _raw() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


ADDED_IN_1_1 = (
    "gb_fcdo_sanctions",
    "us_ofac_sdn",
    "un_sc_sanctions",
    "eu_fsf",
    "gb_parliament_members",
)
# PHASE-2.md 5.1: the kind and the anchor order of 7.1.6 (1 is first).
KINDS_AND_PRIORITIES = {
    "gb_companies_house": ("registry", 1),
    "gleif_lei": ("registry", 2),
    "gb_fcdo_sanctions": ("list", 3),
    "un_sc_sanctions": ("list", 4),
    "eu_fsf": ("list", 5),
    "us_ofac_sdn": ("list", 6),
    "gb_parliament_members": ("list", 7),
    "opensanctions_default": ("list", 8),
    "icij_offshore_leaks": ("leak", 9),
    "nr_synthetic": ("synthetic", 10),
}
CONVERTED = "Converted to FollowTheMoney records by NeonRadar."


def test_registry_loads_the_phase_1_and_1_1_datasets() -> None:
    registry = load_registry()
    assert registry.version == 1
    assert [dataset.slug for dataset in registry.datasets] == [
        "gb_companies_house",
        "gleif_lei",
        "icij_offshore_leaks",
        "opensanctions_default",
        "nr_synthetic",
        *ADDED_IN_1_1,
    ]
    assert registry.get("gleif_lei") is registry.datasets[1]
    assert registry.get("no_such_dataset") is None


def test_the_1_1_datasets_carry_the_spec_terms() -> None:
    registry = load_registry()
    added = {slug: registry.get(slug) for slug in ADDED_IN_1_1}
    assert {slug: d.id_prefix for slug, d in added.items() if d} == {
        "gb_fcdo_sanctions": "uksl",
        "us_ofac_sdn": "ofac",
        "un_sc_sanctions": "unsc",
        "eu_fsf": "eufsf",
        "gb_parliament_members": "ukparl",
    }
    licences = {slug: d.licence.id for slug, d in added.items() if d}
    assert licences == {
        "gb_fcdo_sanctions": "OGL-UK-3.0",
        "us_ofac_sdn": "CC0-1.0",
        "un_sc_sanctions": "LicenseRef-UN-Terms-of-Use",
        "eu_fsf": "LicenseRef-EC-Reuse-Decision-2011-833",
        "gb_parliament_members": "LicenseRef-Open-Parliament-Licence-3.0",
    }
    for dataset in added.values():
        assert dataset is not None
        assert (dataset.redistribution, dataset.synthetic, dataset.access) == (
            "loaders-only",
            False,
            "none",
        )
        assert dataset.status == "active", dataset.slug
    un = registry.get("un_sc_sanctions")
    assert un is not None and un.commercial_use == "permission-required"


def test_every_dataset_has_its_kind_and_anchor_priority() -> None:
    datasets = load_registry().datasets
    assert {d.slug: (d.kind, d.anchor_priority) for d in datasets} == KINDS_AND_PRIORITIES
    priorities = [d.anchor_priority for d in datasets]
    assert sorted(p for p in priorities if p is not None) == list(range(1, len(datasets) + 1))
    for entry in _raw()["datasets"]:  # in the file, not only through the model's defaults
        assert entry["kind"] in ("registry", "list", "leak", "synthetic"), entry["slug"]
        assert isinstance(entry["anchor_priority"], int), entry["slug"]


def test_the_synthetic_dataset_keeps_kind_synthetic() -> None:
    synthetic = load_registry().get(SYNTHETIC_DATASET)
    assert synthetic is not None and synthetic.kind == "synthetic"


def test_every_list_dataset_holds_personal_data() -> None:
    lists = [d for d in load_registry().datasets if d.kind == "list"]
    assert len(lists) == 6
    assert all(d.personal_data for d in lists)


def test_the_1_1_list_attributions_end_with_the_conversion_line() -> None:
    for slug in ADDED_IN_1_1:
        dataset = load_registry().get(slug)
        assert dataset is not None and dataset.kind == "list"
        assert dataset.attribution is not None and dataset.attribution.endswith(CONVERTED), slug


def test_phase_1_spike_datasets_are_active_and_opensanctions_stays_blocked() -> None:
    registry = load_registry()
    status = {d.slug: d.status for d in registry.datasets}
    for slug in ("gb_companies_house", "gleif_lei", "icij_offshore_leaks", "nr_synthetic"):
        assert status[slug] == "active", slug
    assert status["opensanctions_default"] == "blocked"


def test_kind_and_anchor_priority_are_optional() -> None:
    entry = {k: v for k, v in _raw()["datasets"][0].items() if k not in {"kind", "anchor_priority"}}
    dataset = Dataset.model_validate(entry)
    assert (dataset.kind, dataset.anchor_priority) == (None, None)


def test_slugs_and_prefixes_are_unique() -> None:
    datasets = load_registry().datasets
    assert len({dataset.slug for dataset in datasets}) == len(datasets)
    assert len({dataset.id_prefix for dataset in datasets}) == len(datasets)


def test_reserved_prefixes_are_unused() -> None:
    registry = load_registry()
    assert "nr" in registry.reserved_prefixes
    assert not {d.id_prefix for d in registry.datasets} & set(registry.reserved_prefixes)


def test_every_dataset_has_licence_attribution_policy_and_status() -> None:
    for entry in _raw()["datasets"]:
        assert entry["licence"]["id"], entry["slug"]
        assert entry["licence"]["url"].startswith("https://"), entry["slug"]
        assert "attribution" in entry, entry["slug"]  # null is a policy: none needed
        assert entry["status"], entry["slug"]


def test_only_the_synthetic_dataset_is_synthetic() -> None:
    synthetic = [dataset for dataset in load_registry().datasets if dataset.synthetic]
    assert [(d.slug, d.id_prefix) for d in synthetic] == [(SYNTHETIC_DATASET, SYNTHETIC_PREFIX)]
    assert synthetic[0].personal_data is False


def _set(index: int, key: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        data["datasets"][index][key] = value

    return change


def _drop_attribution(data: dict[str, Any]) -> None:
    del data["datasets"][0]["attribution"]


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (_set(1, "id_prefix", "gbch"), "duplicate id_prefix: gbch"),
        (_set(1, "slug", "gb_companies_house"), "duplicate slug: gb_companies_house"),
        (_set(1, "id_prefix", "nr"), "reserved prefixes used by a dataset: nr"),
        (_set(1, "status", "approved"), "status"),
        (_set(1, "kind", "register"), "kind"),
        (_set(1, "anchor_priority", 1), "duplicate anchor_priority: 1"),
        (_set(1, "anchor_priority", 0), "anchor_priority"),
        (_set(1, "commercial_use", "ask"), "commercial_use"),
        (_set(1, "licence_note", "x"), "licence_note"),
        (_drop_attribution, "attribution"),
    ],
)
def test_registry_rejects_broken_entries(
    change: Callable[[dict[str, Any]], None], error: str
) -> None:
    data = _raw()
    change(data)
    with pytest.raises(ValidationError, match=error):
        Registry.model_validate(data)


def test_load_registry_is_cached() -> None:
    assert load_registry() is load_registry()
