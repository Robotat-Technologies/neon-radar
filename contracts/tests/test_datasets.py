"""Contract tests for the dataset registry, contracts/datasets.yaml (PHASE-1.md 5.1, 5.5)."""

from collections.abc import Callable
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from neonradar_contracts.datasets import REGISTRY_PATH, Registry, load_registry
from neonradar_contracts.records import SYNTHETIC_DATASET, SYNTHETIC_PREFIX

pytestmark = pytest.mark.contract


def _raw() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_registry_loads_the_phase_1_datasets() -> None:
    registry = load_registry()
    assert registry.version == 1
    assert [dataset.slug for dataset in registry.datasets] == [
        "gb_companies_house",
        "gleif_lei",
        "icij_offshore_leaks",
        "opensanctions_default",
        "nr_synthetic",
    ]
    assert registry.get("gleif_lei") is registry.datasets[1]
    assert registry.get("no_such_dataset") is None


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
