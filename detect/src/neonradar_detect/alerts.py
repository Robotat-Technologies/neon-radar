"""From a detector's finding to a C4 alert (PHASE-1.md 5.4, M1.9b; contracts/C4-alert.md).

A detector returns `Finding`s: the evidence as C2 ids with the facts the alert needs about each
entity and relationship (caption, `synthetic`, `datasets`), the subjects, the holders of the
evidence accounts, the metrics, the explanation texts and the query that reproduces it.
`build_alert` adds what is the same for every typology: the data flags and the wording class
from one helper (`classify`), the headline from the typology's templates, the 7.1 lint on the
rendered texts with source names masked, the alert id, and the C4 validation.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import JsonValue

from neonradar_contracts import versions
from neonradar_contracts.alert import (
    Alert,
    WordingClass,
    compute_alert_id,
    default_priority,
    query_sha256,
)
from neonradar_detect.catalog import TypologyFile
from neonradar_detect.wording import MetricValue, check_rendered, render_headline

UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DISCLAIMER_ID = "standing-v1"


class AlertError(ValueError):
    """A finding cannot become a valid C4 alert."""


@dataclass(frozen=True, slots=True)
class EntityFact:
    """What an alert needs to know about one C2 entity. `synthetic` is True only when the
    graph says so: a missing value counts as real data (guardrail G1)."""

    id: str
    caption: str
    synthetic: bool
    datasets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EdgeFact:
    """What an alert needs to know about one C2 relationship, with its end nodes' ids."""

    id: str
    source: str
    target: str
    synthetic: bool
    datasets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Step:
    """One explanation step and the evidence edges it describes."""

    text: str
    edge_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Finding:
    """One match of a typology's graph pattern, as a detector reports it."""

    nodes: tuple[EntityFact, ...]  # evidence nodes
    edges: tuple[EdgeFact, ...]  # evidence relationships
    subjects: tuple[tuple[str, EntityFact], ...]  # (role, entity), one per entity
    holders: tuple[EntityFact, ...]  # holders (HOLDS_ACCOUNT sources) of evidence accounts
    metrics: Mapping[str, MetricValue]
    pattern_strength: float
    cypher: str
    parameters: Mapping[str, JsonValue]
    window: tuple[datetime, datetime] | None
    summary: str
    steps: tuple[Step, ...]
    masked: tuple[str, ...] = ()  # other source values in the texts, such as account numbers


@dataclass(frozen=True, slots=True)
class Classification:
    """The wording class and data flags of an alert (5.4, C4 rules 1 to 7)."""

    wording_class: WordingClass
    involves_real_entities: bool
    synthetic_activity: bool
    datasets: tuple[str, ...]


def classify(
    nodes: Iterable[EntityFact],
    edges: Iterable[EdgeFact],
    subjects: Iterable[EntityFact],
    holders: Iterable[EntityFact],
) -> Classification:
    """The one helper for `wording_class`, `involves_real_entities`, `synthetic_activity` and
    `data_flags.datasets` (PHASE-1.md 5.4; contracts/C4-alert.md rules 1 to 7).

    - `involves_real_entities`: an evidence node, a subject or a holder of an evidence account
      is not synthetic. An evidence relationship that is not synthetic counts too: its record
      is real data, and C4 rule 2 then requires the flag.
    - `wording_class`: `synthetic_scenario` exactly when nothing real is involved.
    - `synthetic_activity`: every evidence relationship is synthetic; with no relationships,
      true only when every entity is synthetic (rules 3 and 6).
    - `datasets`: the distinct datasets of all of them, sorted.
    """
    items: list[EntityFact | EdgeFact] = [*nodes, *subjects, *holders]
    relationships = list(edges)
    items += relationships
    involves_real = any(not item.synthetic for item in items)
    if relationships:
        synthetic_activity = all(edge.synthetic for edge in relationships)
    else:
        synthetic_activity = not involves_real
    datasets = sorted({slug for item in items for slug in item.datasets})
    return Classification(
        wording_class="structural_pattern" if involves_real else "synthetic_scenario",
        involves_real_entities=involves_real,
        synthetic_activity=synthetic_activity,
        datasets=tuple(datasets),
    )


def utc_text(moment: datetime) -> str:
    """A C4 time: UTC, `YYYY-MM-DDTHH:MM:SSZ` (`isoformat()` would give `+00:00`)."""
    return moment.astimezone(UTC).strftime(UTC_FORMAT)


def _check_endpoints(finding: Finding) -> None:
    """C4: both ends of every evidence edge are evidence nodes; for plain interval ids the
    detector checks it (the model checks composite ids only)."""
    node_ids = {node.id for node in finding.nodes}
    missing = sorted(
        {end for edge in finding.edges for end in (edge.source, edge.target)} - node_ids
    )
    if missing:
        raise AlertError(f"evidence edges end at nodes outside the evidence: {missing}")


def _metrics(metrics: Mapping[str, MetricValue]) -> dict[str, MetricValue]:
    bad = [
        key
        for key, value in metrics.items()
        if isinstance(value, float) and not math.isfinite(value)
    ]
    if bad:
        raise AlertError(f"metrics must be finite numbers: {bad}")
    return dict(metrics)


def build_alert(
    finding: Finding,
    typology: TypologyFile,
    *,
    detector_name: str,
    detector_version: str,
    run_id: str,
    created_at: datetime,
) -> Alert:
    """The C4 alert for one finding; raises `AlertError`, `WordingError` or a pydantic
    `ValidationError` instead of producing an alert that breaks the contract or the wording
    rules."""
    _check_endpoints(finding)
    subjects = [entity for _, entity in finding.subjects]
    flags = classify(finding.nodes, finding.edges, subjects, finding.holders)
    headline = render_headline(typology, flags.wording_class, finding.metrics)
    texts = {"headline": headline, "explanation.summary": finding.summary}
    texts |= {f"step {order}": step.text for order, step in enumerate(finding.steps, start=1)}
    captions = [item.caption for item in (*finding.nodes, *subjects, *finding.holders)]
    check_rendered(texts, mask=[*captions, *finding.masked])
    node_ids = [node.id for node in finding.nodes]
    edge_ids = [edge.id for edge in finding.edges]
    window = finding.window
    data = {
        "alert_id": compute_alert_id(typology.slug, detector_version, node_ids, edge_ids),
        "contract_version": versions.ALERT,
        "typology": typology.slug,
        "typology_version": typology.version,
        "detector": {
            "name": detector_name,
            "version": detector_version,
            "query_sha256": query_sha256(finding.cypher),
        },
        "run_id": run_id,
        "created_at": utc_text(created_at),
        "priority": default_priority(finding.pattern_strength),
        "pattern_strength": finding.pattern_strength,
        "headline": headline,
        "wording_class": flags.wording_class,
        "subjects": [
            {"entity_id": entity.id, "role": role, "caption": entity.caption or entity.id}
            for role, entity in finding.subjects
        ],
        "evidence": {
            "node_ids": node_ids,
            "edge_ids": edge_ids,
            "query": {"cypher": finding.cypher, "parameters": dict(finding.parameters)},
            "window": None
            if window is None
            else {"start": utc_text(window[0]), "end": utc_text(window[1])},
        },
        "metrics": _metrics(finding.metrics),
        "explanation": {
            "summary": finding.summary,
            "steps": [
                {"order": order, "text": step.text, "edge_ids": list(step.edge_ids)}
                for order, step in enumerate(finding.steps, start=1)
            ],
            "typology_reference": {
                "slug": typology.slug,
                "doc_path": typology.doc,
                "citations": list(typology.citations),
            },
            "false_positive_notes": list(typology.false_positives),
        },
        "data_flags": {
            "involves_real_entities": flags.involves_real_entities,
            "synthetic_activity": flags.synthetic_activity,
            "datasets": list(flags.datasets),
        },
        "disclaimer_id": DISCLAIMER_ID,
    }
    return Alert.model_validate(data)


def entity_fact(row: Mapping[str, object]) -> EntityFact:
    """An `EntityFact` from a query row with `id`, `caption`, `synthetic` and `datasets`."""
    return EntityFact(
        id=str(row["id"]),
        caption=str(row.get("caption") or row["id"]),
        synthetic=row.get("synthetic") is True,
        datasets=_strings(row.get("datasets")),
    )


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return tuple(str(item) for item in value)
    return ()
