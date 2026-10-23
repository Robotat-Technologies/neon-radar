"""The two Sources give the same detection results on a generated world (PHASE-3.md 7.1.5)."""

from datetime import date
from pathlib import Path

import pytest
from neonradar_cli import evaluate
from neonradar_detect import catalog
from neonradar_ingest.synth import world
from neonradar_ingest.synth.namesource import default_names

pytestmark = pytest.mark.integration

SETTINGS = evaluate.EvalSettings(
    "synth-eval",
    world.WorldConfig(companies=80, people=120, agent_every=40, professional_every=40),
    date(2025, 1, 1),
    date(2026, 7, 1),
    illicit=1,
    lookalikes=1,
    overrides={"mass_registration_address": {"top_share": 0.0}},
)


def test_alerts_and_counts_are_identical(tmp_path: Path, neo4j_source_factory) -> None:  # type: ignore[no-untyped-def]
    cat = catalog.load()
    mem = evaluate.run_seed(5, SETTINGS, default_names(), cat, "dev", tmp_path / "m")
    neo = evaluate.run_seed(
        5, SETTINGS, default_names(), cat, "dev", tmp_path / "n", neo4j_source_factory
    )
    assert neo.record_sha256 == mem.record_sha256
    assert neo.alert_ids == mem.alert_ids and mem.alert_ids
    assert neo.summary["typologies"] == mem.summary["typologies"]
    assert evaluate.baseline(neo) == evaluate.baseline(mem)
