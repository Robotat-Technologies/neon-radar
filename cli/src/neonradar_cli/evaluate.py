"""The evaluation run behind `neonradar eval run` and `neonradar eval check` (PHASE-3.md 7.6.1).

For each seed: a world, its overlay, the label files written and read back, a Source over base
plus overlay, the catalog's detectors with the profile's parameters, and the matcher. The Source
comes from `source_factory`: in memory (`memory_source`, the oracle) by default, or the Neo4j
factory of the CLI, which writes the records, loads them and returns a `Neo4jSource`. Names never
change a structural draw (7.2.1), so the counts depend only on the code, the seed and the settings.

A holdout seed runs only with `allow_holdout=True`, which the CLI passes after its own checks (a
terminal, not CI, the freeze, M3.6 and M3.11): `run_seed` refuses the split `test`, and any seed
that `eval/seeds.yaml` lists under `test.seeds` whatever the split, so a caller that bypasses the
CLI cannot generate a holdout world by accident (G11).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from neonradar_detect import catalog as catalog_mod
from neonradar_detect import runner
from neonradar_detect.catalog import Typology
from neonradar_detect.evaluation import harness, metrics
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource
from neonradar_detect.source import Source, Window
from neonradar_ingest.synth import labels, overlay, world, writer
from neonradar_ingest.synth.background import BackgroundConfig
from neonradar_ingest.synth.ctx import NameSource

Record = dict[str, Any]
SourceFactory = Callable[[list[Record]], Source]


@dataclass(frozen=True, slots=True)
class EvalSettings:
    """What a synthetic evaluation profile fixes (`ingest/profiles/synth-eval.yaml`, 7.11)."""

    profile: str
    world: world.WorldConfig
    start: date
    end: date
    illicit: int
    lookalikes: int
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    typologies: tuple[str, ...] = tuple(overlay.SCENARIOS)
    overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    created_at: datetime = datetime(2026, 11, 2, tzinfo=UTC)

    @property
    def window(self) -> Window:
        return Window(
            datetime.combine(self.start, datetime.min.time(), UTC),
            datetime.combine(self.end, datetime.min.time(), UTC),
        )


@dataclass(slots=True)
class SeedRun:
    seed: int
    result: harness.WorldResult
    summary: dict[str, Any]
    record_sha256: str
    counts: dict[str, int]
    seconds: dict[str, float]
    alert_ids: tuple[str, ...] = ()
    alerts: tuple[dict[str, Any], ...] = ()


def memory_source(records: list[Record]) -> Source:
    return MemSource(from_records(records))


def overlay_config(settings: EvalSettings, seed: int, split: str) -> overlay.OverlayConfig:
    return overlay.OverlayConfig(
        seed,
        start=settings.start,
        end=settings.end,
        split=split,
        illicit=settings.illicit,
        lookalikes=settings.lookalikes,
        typologies=settings.typologies,
        background=settings.background,
    )


def detector_params(
    cat: Mapping[str, Typology], overrides: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        slug: catalog_mod.params_for(cat[slug], module, overrides.get(slug))
        for slug, module in runner.detectors(cat).items()
    }


def run_id(settings: EvalSettings, split: str, seed: int) -> str:
    """A C4 run id (`run-<UTC yyyymmddThhmmss>-<4 hex>`) fixed by the settings and the seed."""
    tag = hashlib.sha256(f"{settings.profile}|{split}|{seed}".encode()).hexdigest()[:4]
    return f"run-{settings.created_at:%Y%m%dT%H%M%S}-{tag}"


SEEDS_FILE = Path("eval/seeds.yaml")


def holdout_seeds(path: Path = SEEDS_FILE) -> frozenset[int]:
    """The seeds `eval/seeds.yaml` lists under `test.seeds` (none until M3.11 draws them)."""
    if not path.exists():
        return frozenset()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(int(s) for s in (data.get("test") or {}).get("seeds") or [])


def run_seed(
    seed: int,
    settings: EvalSettings,
    names: NameSource,
    cat: Mapping[str, Typology],
    split: str,
    workdir: Path,
    source_factory: SourceFactory = memory_source,
    *,
    allow_holdout: bool = False,
    seeds_file: Path = SEEDS_FILE,
) -> SeedRun:
    if split not in ("dev", "test"):
        raise ValueError(f"unknown split {split}")
    if (split == "test" or seed in holdout_seeds(seeds_file)) and not allow_holdout:
        raise PermissionError("a holdout seed runs only through `eval run --split test` (G11)")
    t0 = time.perf_counter()
    base = world.generate(seed, settings.world, names)
    ov = overlay.generate(
        base, {"nr_synthetic": "synthetic"}, overlay_config(settings, seed, split), names
    )
    records = base + ov.records
    text = writer.record_lines(records)
    digest = labels.sha256(text)
    label_dir = workdir / f"seed-{seed}" / "labels"
    labels.write(
        label_dir,
        labels.files(
            ov.labels,
            seed=seed,
            record_sha256={"records": digest},
            generator_version=writer.GENERATOR_VERSION,
        ),
    )
    scenarios = harness.scenario_views(label_dir)
    t1 = time.perf_counter()
    source = source_factory(records)
    t2 = time.perf_counter()
    params = detector_params(cat, settings.overrides)
    detection = runner.run_detection(
        source,
        params,
        settings.window,
        cat,
        run_id=run_id(settings, split, seed),
        created_at=settings.created_at,
    )
    t3 = time.perf_counter()
    payments = frozenset(ov.payments)
    result = harness.evaluate_world(
        seed, detection.alerts, scenarios, payments, list(runner.detectors(cat))
    )
    return SeedRun(
        seed,
        result,
        detection.summary,
        digest,
        {"records": len(records), "payments": len(payments), "alerts": len(detection.alerts)},
        {
            "generate": round(t1 - t0, 1),
            "graph": round(t2 - t1, 1),
            "detect": round(t3 - t2, 1),
        },
        tuple(a["alert_id"] for a in detection.alerts),
        tuple(detection.alerts),
    )


def figures(
    runs: Sequence[SeedRun], typologies: Sequence[str]
) -> tuple[list[metrics.Figures], dict[str, dict[str, tuple[int, int]]]]:
    per_seed = {r.seed: r.result.outcomes for r in runs}
    results = [r.result for r in runs]
    return (
        [metrics.figures(per_seed, slug) for slug in typologies],
        {slug: harness.pooled_bands(results, slug) for slug in typologies},
    )


def baseline(run: SeedRun) -> dict[str, Any]:
    """The CI baseline of one seed: exact counts per typology (`eval/baselines/ci.json`)."""
    return {
        "seed": run.seed,
        "rules_version": "1",
        "typologies": {
            slug: harness.counts(outcome) for slug, outcome in sorted(run.result.outcomes.items())
        },
    }


def compare(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(differences, pending). A difference is a count of a typology that ran which its baseline
    row does not have, or a typology that ran without a row (so a new detector lands with its
    row); `pending` lists the baseline rows whose typology has no detector yet (M3.5)."""
    out = []
    if actual.get("seed") != expected.get("seed"):
        out.append(f"seed {actual.get('seed')} != {expected.get('seed')}")
    got, want = actual["typologies"], expected["typologies"]
    for slug in sorted(got):
        if slug not in want:
            out.append(f"{slug}: no baseline row")
            continue
        for key in sorted(set(want[slug]) | set(got[slug])):
            if got[slug].get(key) != want[slug].get(key):
                out.append(f"{slug}.{key}: {got[slug].get(key)} != {want[slug].get(key)}")
    return out, sorted(set(want) - set(got))


def small(settings: EvalSettings, **world_changes: Any) -> EvalSettings:
    """The same settings with a smaller world (tests)."""
    return replace(settings, world=replace(settings.world, **world_changes))
