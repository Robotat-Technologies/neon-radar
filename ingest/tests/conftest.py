"""Shared fixtures for the synthetic generator tests: one demo-mini generation per session."""

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import iter_records
from neonradar_ingest.synth import DEMO_SEED
from neonradar_ingest.synth.demo import write_demo_mini

# test helpers sit next to the tests (pytest runs with --import-mode=importlib)
sys.path.insert(0, str(Path(__file__).resolve().parent))


@dataclass(frozen=True)
class Load:
    path: Path
    records: list[dict[str, Any]]
    by_id: dict[str, dict[str, Any]]
    transactions: list[dict[str, str]]
    scenarios: list[dict[str, str]]

    def schema(self, name: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r["schema"] == name]

    def prop(self, record_id: str, name: str) -> str:
        return str(self.by_id[record_id]["properties"][name][0])


def read_labels(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# synthetic: true"
    return list(csv.DictReader(lines[1:]))


def load(path: Path) -> Load:
    records = list(iter_records(path))
    labels = path.parent / "labels"
    return Load(
        path,
        records,
        {r["id"]: r for r in records},
        read_labels(labels / "transactions.csv"),
        read_labels(labels / "scenarios.csv"),
    )


@pytest.fixture(scope="session")
def demo_mini(tmp_path_factory: pytest.TempPathFactory) -> Load:
    return load(write_demo_mini(tmp_path_factory.mktemp("demo-mini"), DEMO_SEED))
