"""Run the detectors of a profile, apply R-REAL and build the alerts (PHASE-3.md 7.5.3).

`run_detection` is the one path every caller uses: `neonradar detect run`, `make load`, the
evaluation harness and the tests. It never writes; the CLI writes `alerts.jsonl` and
`summary.json` and loads them (C2 1.2.0, L19). Withheld findings are counted by typology and
reason and never kept. The detectors are the modules the catalog names, run in ORDER. Rendering
lints every text (`wording.render` raises `WordingError`), so a run never emits text that names
conduct.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from types import ModuleType
from typing import Any

from neonradar_detect import alerts, policy, wording
from neonradar_detect.catalog import Typology
from neonradar_detect.source import Source, Window

# PHASE-1.md 7.2 order; a typology runs when its catalog file names a detector (PHASE-1.md 5.4)
ORDER = (
    "structuring",
    "rapid_pass_through",
    "layering_chain",
    "circular_flow",
    "fan_in_collection",
    "fan_out_distribution",
    "dormant_reactivation",
    "shell_chain",
    "mass_registration_address",
    "sanctions_exposure",
    "formation_agent_cluster",
    "recycled_directors",
    "pep_exposure",
    "cash_commingling",
    "trade_based_ml",
)


def detectors(catalog: Mapping[str, Typology]) -> dict[str, ModuleType]:
    """Slug to detector module, in ORDER, for every catalog typology that names a detector."""
    out: dict[str, ModuleType] = {}
    for slug in ORDER:
        typology = catalog.get(slug)
        if typology is None or not typology.detector:
            continue
        module = importlib.import_module(typology.detector)
        if slug != module.SLUG:
            raise ValueError(f"{typology.detector} declares {module.SLUG}, not {slug}")
        out[slug] = module
    unknown = sorted(set(catalog) - set(ORDER))
    if unknown:
        raise ValueError(f"typologies outside ORDER: {unknown}")
    return out


@dataclass(slots=True)
class RunResult:
    alerts: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)


def params_sha256(params: Mapping[str, Any]) -> str:
    """SHA-256 of the parameters actually used, as canonical JSON (sorted keys, no spaces)."""
    body = {
        slug: (asdict(p) if hasattr(p, "__dataclass_fields__") else dict(p))
        for slug, p in sorted(params.items())
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_detection(
    source: Source,
    params: Mapping[str, Any],
    window: Window,
    catalog: Mapping[str, Typology],
    *,
    run_id: str,
    created_at: datetime,
    query_sha256: Mapping[str, str] | None = None,
    real_registry_alerts: bool = True,
) -> RunResult:
    """Run every typology in `params` (slug to its Params) in catalog order.
    `real_registry_alerts` is `access.real_registry_alerts` (G12, rule (c) in `policy`)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_typology: dict[str, dict[str, Any]] = {}
    for slug, module in detectors(catalog).items():
        if slug not in params:
            continue
        result = module.run(source, params[slug], window)
        withheld = {d.value: 0 for d in policy.Decision if d is not policy.Decision.EMIT}
        emitted = duplicates = 0
        for finding in result.findings:
            edges = source.edge_info(finding.edge_ids)
            ends = alerts.edge_ends(edges)
            nodes = source.node_info(
                set(finding.node_ids) | {s.entity_id for s in finding.subjects} | ends
            )
            flags = policy.data_flags(finding, nodes, edges)
            decision = policy.decide(
                finding, flags, nodes, edges, registry_on_real=real_registry_alerts
            )
            if decision is not policy.Decision.EMIT:
                withheld[decision.value] += 1
                continue
            typology = catalog[slug]
            alert = alerts.build(
                finding,
                wording.render(finding, typology, flags.wording_class, nodes, edges),
                flags,
                nodes,
                detector_module=module.__name__,
                detector_version=module.VERSION,
                typology_version=typology.version,
                query_sha256=(query_sha256 or {}).get(slug, ""),
                run_id=run_id,
                created_at=created_at,
                doc_path=typology.doc,
                citations=typology.citations,
                false_positives=typology.false_positives,
                priority_rule=getattr(module, "priority", None),
            )
            if alert["alert_id"] in seen:
                duplicates += 1
                continue
            seen.add(alert["alert_id"])
            out.append(alert)
            emitted += 1
        per_typology[slug] = {
            "findings": len(result.findings),
            "alerts": emitted,
            "duplicates": duplicates,
            "withheld": withheld,
            "stats": dict(result.stats),
        }
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda a: (order[a["priority"]], -a["pattern_strength"], a["alert_id"]))
    summary = {
        "run_id": run_id,
        "window": {
            "start": window.start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": window.end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "params_sha256": params_sha256(params),
        "typologies": per_typology,
        "alerts": len(out),
        "withheld": {
            reason: sum(c["withheld"][reason] for c in per_typology.values())
            for reason in (d.value for d in policy.Decision if d is not policy.Decision.EMIT)
        },
    }
    return RunResult(out, summary)
