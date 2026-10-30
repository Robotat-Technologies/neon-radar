"""One world's alerts against its labels (PHASE-3.md 7.6.2).

The harness reads label files v2 (7.2.8) with its own small reader, because `neonradar_detect`
never imports the generator (`synthetic-transactions.md` 6.2: generator and detectors stay
independent). `evaluate_world` matches every typology's alerts with `match.evaluate` and also
counts true alerts per priority band, so the report can show whether the queue order helps
(`evaluation-alerting.md` 0, answer 7).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_detect.evaluation.match import AlertView, Outcome, ScenarioView, evaluate

LABEL_SCHEMA_MAJOR = "2"
BANDS = ("high", "medium", "low")


def read_label_csv(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """The `# key: value` header lines of a label CSV, and its rows."""
    header: dict[str, str] = {}
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            key, _, value = line[1:].partition(":")
            header[key.strip()] = value.strip()
        else:
            lines.append(line)
    return header, list(csv.DictReader(lines))


def _flag(value: str) -> bool:
    if value not in ("true", "false"):
        raise ValueError(f"not a label boolean: {value!r}")
    return value == "true"


def scenario_views(label_dir: Path) -> list[ScenarioView]:
    """Scenarios with their labelled payments and participants, in scenario id order."""
    tables = {}
    for name in ("scenarios", "transactions", "participants"):
        header, rows = read_label_csv(label_dir / f"{name}.csv")
        if header.get("synthetic") != "true":
            raise ValueError(f"{name}.csv does not say it is synthetic")
        if header.get("label_schema", "").split(".")[0] != LABEL_SCHEMA_MAJOR:
            raise ValueError(f"{name}.csv has label schema {header.get('label_schema')!r}")
        tables[name] = rows
    tx: dict[str, set[str]] = {}
    for row in tables["transactions"]:
        tx.setdefault(row["scenario_id"], set()).add(row["tx_id"])
    members: dict[str, dict[str, str]] = {}
    core: dict[str, set[str]] = {}
    for row in tables["participants"]:
        members.setdefault(row["scenario_id"], {})[row["object_id"]] = row["role"]
        if _flag(row["is_core"]):
            core.setdefault(row["scenario_id"], set()).add(row["object_id"])
    return [
        ScenarioView(
            row["scenario_id"],
            row["typology"],
            _flag(row["is_lookalike"]),
            frozenset(tx.get(row["scenario_id"], ())),
            members.get(row["scenario_id"], {}),
            frozenset(core.get(row["scenario_id"], ())),
        )
        for row in sorted(tables["scenarios"], key=lambda r: r["scenario_id"])
    ]


def alert_views(alerts: Iterable[Mapping[str, Any]]) -> list[AlertView]:
    """C4 alerts as the matcher sees them."""
    return [
        AlertView(
            a["alert_id"],
            a["typology"],
            frozenset(a["evidence"]["edge_ids"]),
            frozenset(a["evidence"]["node_ids"]),
            {s["entity_id"]: s["role"] for s in a["subjects"]},
        )
        for a in alerts
    ]


@dataclass(slots=True)
class WorldResult:
    seed: int
    outcomes: dict[str, Outcome]
    bands: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)


def evaluate_world(
    seed: int,
    alerts: Sequence[Mapping[str, Any]],
    scenarios: Sequence[ScenarioView],
    payment_ids: frozenset[str],
    typologies: Sequence[str],
    min_iou: float = 0.5,
) -> WorldResult:
    """Outcomes per typology, and (true alerts, alerts) per priority band."""
    views = alert_views(alerts)
    priority = {a["alert_id"]: a["priority"] for a in alerts}
    result = WorldResult(seed, {})
    for slug in typologies:
        outcome = evaluate(slug, views, scenarios, payment_ids, min_iou)
        result.outcomes[slug] = outcome
        per_band = {}
        for band in BANDS:
            ids = [aid for aid in outcome.kinds if priority[aid] == band]
            per_band[band] = (sum(1 for aid in ids if outcome.kinds[aid] == "true"), len(ids))
        result.bands[slug] = per_band
    return result


def counts(outcome: Outcome) -> dict[str, int]:
    """The exact counts the CI baseline pins (`eval/baselines/ci.json`, M3.6)."""
    return {
        "alerts": outcome.alerts,
        "true": outcome.true,
        "duplicate": outcome.duplicate,
        "lookalike": outcome.lookalike,
        "partial": outcome.partial,
        "other": outcome.other,
        "background": outcome.background,
        "planted": outcome.planted,
        "detected": outcome.detected,
        "lookalikes": outcome.lookalikes,
        "lookalikes_alerted": outcome.lookalikes_alerted,
    }


def pooled_bands(results: Sequence[WorldResult], typology: str) -> dict[str, tuple[int, int]]:
    """(true alerts, alerts) per priority band, summed over seeds."""
    out = {}
    for band in BANDS:
        pairs = [r.bands[typology][band] for r in results if typology in r.bands]
        out[band] = (sum(k for k, _ in pairs), sum(n for _, n in pairs))
    return out
