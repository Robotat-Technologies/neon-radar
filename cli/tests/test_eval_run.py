import re
from datetime import date
from pathlib import Path

import pytest
from neonradar_cli import evaluate
from neonradar_detect import catalog, runner
from neonradar_ingest.synth import world
from neonradar_ingest.synth.namesource import default_names

SETTINGS = evaluate.EvalSettings(
    "synth-eval",
    world.WorldConfig(companies=60, people=90, agent_every=30, professional_every=30),
    date(2025, 1, 1),
    date(2026, 7, 1),
    illicit=1,
    lookalikes=1,
    overrides={"mass_registration_address": {"top_share": 0.0}},
)


def test_a_seed_run_is_deterministic_and_complete(tmp_path: Path) -> None:
    cat = catalog.load()
    a = evaluate.run_seed(3, SETTINGS, default_names(), cat, "dev", tmp_path / "a")
    b = evaluate.run_seed(3, SETTINGS, default_names(), cat, "dev", tmp_path / "b")
    assert a.record_sha256 == b.record_sha256
    assert evaluate.baseline(a) == evaluate.baseline(b)
    assert [x["alert_id"] for x in a.alerts] == list(a.alert_ids)
    assert re.fullmatch(r"run-\d{8}T\d{6}-[0-9a-f]{4}", a.alerts[0]["run_id"])
    slugs = list(runner.detectors(cat))
    assert list(a.result.outcomes) == slugs
    assert all(o.planted == 1 and o.lookalikes == 1 for o in a.result.outcomes.values())
    assert (tmp_path / "a" / "seed-3" / "labels" / "manifest.json").exists()
    figures, bands = evaluate.figures([a], slugs)
    assert [f.typology for f in figures] == slugs and set(bands) == set(slugs)


def test_holdout_seeds_need_the_cli(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="G11"):
        evaluate.run_seed(3, SETTINGS, default_names(), catalog.load(), "test", tmp_path)
    seeds = tmp_path / "seeds.yaml"  # once M3.11 has drawn them, the split no longer matters
    seeds.write_text("test:\n  seeds: [3]\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="G11"):
        evaluate.run_seed(
            3, SETTINGS, default_names(), catalog.load(), "dev", tmp_path, seeds_file=seeds
        )
    assert not (tmp_path / "seed-3").exists()


def test_compare_reports_every_difference(tmp_path: Path) -> None:
    run = evaluate.run_seed(4, SETTINGS, default_names(), catalog.load(), "dev", tmp_path)
    base = evaluate.baseline(run)
    assert evaluate.compare(base, base) == ([], [])
    slug = sorted(base["typologies"])[0]  # whichever detectors have merged
    changed = {**base, "typologies": {**base["typologies"]}}
    changed["typologies"][slug] = {**base["typologies"][slug], "true": -1}
    assert evaluate.compare(base, changed) == (
        [f"{slug}.true: {base['typologies'][slug]['true']} != -1"],
        [],
    )
    first = sorted(base["typologies"])[0]
    missing = {**base, "typologies": dict(list(base["typologies"].items())[1:])}
    assert evaluate.compare(base, missing) == ([f"{first}: no baseline row"], [])
    fewer = {**base, "typologies": dict(list(base["typologies"].items())[1:])}
    assert evaluate.compare(fewer, base) == ([], [first])
