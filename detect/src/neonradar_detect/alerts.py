"""Findings to C4 1.0.0 alerts (PHASE-3.md 7.5.1).

The builder adds what a detector does not know: the alert id (C4's `compute_alert_id`, M1.7c), the
priority, the rendered text, the data flags, the notes a data source asks for and the evidence
query. Every alert's evidence query is
the generic `queries/evidence.cypher`, which re-selects the evidence nodes and relationships by id,
so `neonradar detect verify-alert` can check an alert against the graph.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from neonradar_contracts.alert import compute_alert_id

from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.policy import DataFlags
from neonradar_detect.wording import Rendered

EVIDENCE_QUERY = (
    (Path(__file__).parent / "queries" / "evidence.cypher").read_text(encoding="utf-8")
    if (Path(__file__).parent / "queries" / "evidence.cypher").exists()
    else "// queries/evidence.cypher"
)


# Notes a data source asks for wherever its records are shown (PHASE-1.md 5.1: "Show ICIJ's
# disclaimer with the data"; the wording is ICIJ's FAQ, `icij_faq`). Each passes the wording lint.
DATASET_NOTES = {
    "icij_offshore_leaks": (
        "Records from the ICIJ Offshore Leaks Database: ICIJ says there are legitimate uses for "
        "offshore companies and trusts, and recommends caution before drawing any conclusions, "
        "as many people and entities have the same or similar names."
    ),
}


def default_priority(strength: float) -> str:
    return "high" if strength >= 0.75 else ("medium" if strength >= 0.5 else "low")


def build(
    finding: Finding,
    rendered: Rendered,
    flags: DataFlags,
    nodes: Mapping[str, NodeInfo],
    *,
    detector_module: str,
    detector_version: str,
    typology_version: str,
    query_sha256: str,
    run_id: str,
    created_at: datetime,
    doc_path: str,
    citations: Sequence[str],
    false_positives: Sequence[str],
    priority_rule: Callable[[Finding], str | None] | None = None,
) -> dict[str, Any]:
    priority = (priority_rule(finding) if priority_rule else None) or default_priority(
        finding.pattern_strength
    )
    evidence: dict[str, Any] = {
        "node_ids": list(finding.node_ids),
        "edge_ids": list(finding.edge_ids),
        "query": {
            "cypher": EVIDENCE_QUERY,
            "parameters": {"node_ids": list(finding.node_ids), "edge_ids": list(finding.edge_ids)},
        },
    }
    if finding.window is not None:
        evidence["window"] = {"start": _utc(finding.window[0]), "end": _utc(finding.window[1])}
    return {
        "alert_id": compute_alert_id(
            finding.typology, detector_version, finding.node_ids, finding.edge_ids
        ),
        "contract_version": "1.0.0",
        "typology": finding.typology,
        "typology_version": typology_version,
        "detector": {
            "name": detector_module,
            "version": detector_version,
            "query_sha256": query_sha256,
        },
        "run_id": run_id,
        "created_at": _utc(created_at),
        "priority": priority,
        "pattern_strength": finding.pattern_strength,
        "headline": rendered.headline,
        "wording_class": flags.wording_class,
        "subjects": [
            {"entity_id": s.entity_id, "role": s.role, "caption": nodes[s.entity_id].caption}
            for s in finding.subjects
        ],
        "evidence": evidence,
        "metrics": dict(finding.metrics),
        "explanation": {
            "summary": rendered.summary,
            "steps": [
                {"order": i, "text": text, "edge_ids": list(edges)}
                for i, (text, edges) in enumerate(rendered.steps, 1)
            ],
            "typology_reference": {
                "slug": finding.typology,
                "doc_path": doc_path,
                "citations": list(citations),
            },
            "false_positive_notes": [
                *false_positives,
                *(DATASET_NOTES[d] for d in flags.datasets if d in DATASET_NOTES),
            ],
        },
        "data_flags": {
            "involves_real_entities": flags.involves_real_entities,
            "synthetic_activity": flags.synthetic_activity,
            "datasets": list(flags.datasets),
        },
        "disclaimer_id": "standing-v1",
    }


def _utc(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def edge_ends(edges: Mapping[str, EdgeInfo]) -> set[str]:
    return {x for e in edges.values() for x in (e.source, e.target)}
