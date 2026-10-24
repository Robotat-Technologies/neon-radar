"""How an entity was resolved, and where its data came from (C3 1.1.0, PHASE-2.md 5.3, M2.12).

`resolution()` resolves the id (`queries/resolve_id.cypher`), then reads the entity with its
source records (`resolution_members.cypher`) and its possible matches
(`resolution_candidates.cypher`). Every text comes from `neonradar_graph.wording` (7.2): this
module adds no wording. `provenance()` gives entity detail one record per source record of a
merged entity, and the entity itself otherwise.
"""

from typing import Any, Final

from neonradar_api.graph import GraphConnection
from neonradar_contracts.api import (
    QUERY_TIMEOUT_SECONDS,
    PossibleMatch,
    ProvenanceRecord,
    ResolutionMember,
    ResolutionResponse,
)
from neonradar_graph import cypher, shapes
from neonradar_graph.ownership import pick_entity
from neonradar_graph.wording import evidence_lines, explain_member, explain_possible_match

RESOLVE_ID: Final = cypher.query("resolve_id.cypher")
MEMBERS: Final = cypher.query("resolution_members.cypher")
CANDIDATES: Final = cypher.query("resolution_candidates.cypher")


def resolve(graph: GraphConnection, entity_id: str) -> str:
    """The entity id for an entity id or the id of a record merged into it (404 otherwise)."""
    rows = graph.read(RESOLVE_ID, {"id": entity_id}, timeout=QUERY_TIMEOUT_SECONDS)
    return pick_entity(entity_id, [str(row["id"]) for row in rows])


def _members(graph: GraphConnection, entity_id: str) -> dict[str, Any]:
    (row,) = graph.read(MEMBERS, {"id": entity_id}, timeout=QUERY_TIMEOUT_SECONDS)
    return dict(row)


def _identity(entity: dict[str, Any], labels: list[str]) -> ResolutionMember:
    """The only member of a single-record entity: the record it keeps the id of."""
    node = shapes.summary({"props": entity, "labels": labels})
    dataset = str(entity["datasets"][0])
    return ResolutionMember.model_validate(
        {
            "record_id": node.id,
            "dataset": dataset,
            "schema": node.schema_,
            "caption": node.caption,
            "names": [str(name) for name in entity.get("names") or []],
            "method": "identity",
            "rule": None,
            "match_probability": None,
            "decided_at": None,
            "explanation": explain_member({"method": "identity", "dataset": dataset}),
        }
    )


def _member(record: dict[str, Any], link: dict[str, Any]) -> ResolutionMember:
    """A source record of a merged entity and its RESOLVED_TO (C2 1.1.0)."""
    fields = {
        "method": link["method"],
        "rule": link.get("rule"),
        "match_probability": link.get("match_probability"),
        "features": link.get("features"),
        "dataset": record["dataset"],
    }
    return ResolutionMember.model_validate(
        {
            "record_id": record["id"],
            "dataset": record["dataset"],
            "schema": record["schema"],
            "caption": record["caption"],
            "names": [str(name) for name in record.get("names") or []],
            "method": link["method"],
            "rule": link.get("rule"),
            "match_probability": link.get("match_probability"),
            "decided_at": link.get("decided_at"),
            "explanation": explain_member(fields),
        }
    )


def _possible_match(row: Any) -> PossibleMatch:
    link = dict(row["link"])
    method = link["method"]
    return PossibleMatch(
        entity=shapes.summary({"props": row["other"], "labels": row["labels"]}),
        match_probability=link.get("match_probability") if method == "probabilistic" else None,
        method=method,
        rule=link.get("rule"),
        reasons=[str(reason) for reason in link.get("reasons") or []],
        evidence=evidence_lines(link.get("features")),
        explanation=explain_possible_match(link),
    )


def resolution(graph: GraphConnection, entity_id: str) -> ResolutionResponse:
    canonical_id = resolve(graph, entity_id)
    row = _members(graph, canonical_id)
    entity, labels = dict(row["entity"]), list(row["labels"])
    found = [(dict(m["record"]), dict(m["link"])) for m in row["members"] if m is not None]
    members = [_member(record, link) for record, link in found] or [_identity(entity, labels)]
    candidates = graph.read(CANDIDATES, {"id": canonical_id}, timeout=QUERY_TIMEOUT_SECONDS)
    matches = [_possible_match(candidate) for candidate in candidates]
    # The run that built the graph, as its links record it: a single-record entity without a
    # possible match has neither, and C2 keeps no run on the entity itself.
    links = [link for _, link in found] + [dict(c["link"]) for c in candidates]
    run = next((link for link in links if link.get("run_id")), {})
    cluster_size = int(entity.get("cluster_size") or len(members))
    return ResolutionResponse(
        entity_id=canonical_id,
        canonical=cluster_size > 1,
        resolution=entity.get("resolution") or "identity",
        cluster_size=cluster_size,
        members=members,
        possible_matches=matches,
        resolver_version=run.get("resolver_version"),
        run_id=run.get("run_id"),
    )


def provenance(graph: GraphConnection, props: dict[str, Any]) -> list[ProvenanceRecord]:
    """One record per source record of a merged entity (its `:SourceRecord` nodes), and the
    entity itself otherwise (C3 1.1.0)."""
    if int(props.get("cluster_size") or 1) > 1:
        row = _members(graph, str(props["id"]))
        records = [dict(m["record"]) for m in row["members"] if m is not None]
        if records:
            return [
                ProvenanceRecord(
                    dataset=str(record["dataset"]),
                    record_id=str(record["id"]),
                    retrieved_at=record.get("retrieved_at"),
                    source_url=record.get("source_url"),
                )
                for record in records
            ]
    return [
        ProvenanceRecord(
            dataset=str(props["datasets"][0]),
            record_id=str(props["id"]),
            retrieved_at=None,
            source_url=props.get("source_url"),
        )
    ]
