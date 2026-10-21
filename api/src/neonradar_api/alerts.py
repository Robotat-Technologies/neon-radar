"""`GET /alerts` and `GET /alerts/{alert_id}` (contracts/C3-api.md, "Alerts").

Alerts come only from Neo4j (C2): the queue filters and orders on the `:Alert` scalar
properties, and the detail parses the `payload` property as a C4 `Alert`. The queue order is
priority (high, medium, low), then `pattern_strength` descending, then `alert_id`; pages are
keyset pages, and the opaque cursor holds the last row's sort key and a digest of the filters.
"""

import base64
import binascii
import hashlib
import json
import logging
import math
import re
from collections.abc import Mapping
from typing import Any, Final

from pydantic import ValidationError

from neonradar_api import shapes
from neonradar_api.graph import GraphConnection
from neonradar_api.problems import ProblemError
from neonradar_contracts.alert import ALERT_ID_PATTERN, Alert
from neonradar_contracts.api import AlertDetail, AlertPage, AlertSummary

logger = logging.getLogger(__name__)

BAD_CURSOR: Final = "query.cursor: the cursor is malformed or belongs to other filters"
NOT_FOUND: Final = "No alert has this id."
STALE: Final = (
    "The stored alert does not validate as a C4 alert; re-run detection (`neonradar detect run`)."
)
MISSING_EVIDENCE: Final = (
    "The alert's evidence is no longer in the graph; re-run detection (`neonradar detect run`)."
)
QUEUE: Final = """
MATCH (a:Alert)
WHERE ($typology IS NULL OR a.typology = $typology)
  AND ($priority IS NULL OR a.priority = $priority)
  AND ($entity_id IS NULL OR EXISTS { (a)-[:FLAGS]->(:Entity {id: $entity_id}) })
  AND ($run_id IS NULL OR EXISTS { (:DetectionRun {run_id: $run_id})-[:PRODUCED]->(a) })
WITH a, CASE a.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END AS rank
WHERE $after IS NULL OR rank > $after.rank
   OR (rank = $after.rank AND (a.pattern_strength < $after.strength
       OR (a.pattern_strength = $after.strength AND a.alert_id > $after.alert_id)))
WITH a, rank
ORDER BY rank, a.pattern_strength DESC, a.alert_id
LIMIT $limit
RETURN a {.alert_id, .typology, .priority, .pattern_strength, .headline, .created_at,
          .involves_real_entities, .synthetic_activity, .payload} AS alert,
       rank, [(a)-[:FLAGS]->(e:Entity) | e.id] AS flagged
"""
PAYLOAD: Final = "MATCH (a:Alert {alert_id: $alert_id}) RETURN a.payload AS payload"
# Every evidence node and subject (`:Entity` or `:Sanction`), the evidence relationships and
# the HOLDS_ACCOUNT relationships between those nodes. C4 puts both ends of every evidence
# edge among the evidence nodes, so the relationships are found from the nodes.
EVIDENCE: Final = """
OPTIONAL MATCH (e:Entity) WHERE e.id IN $node_ids
WITH collect(e) AS entities
OPTIONAL MATCH (s:Sanction) WHERE s.id IN $node_ids
WITH entities, collect(s) AS sanctions
WITH entities + sanctions AS nodes
CALL (nodes) {
  UNWIND nodes AS x
  MATCH (x)-[r]->(y)
  WHERE y IN nodes AND (r.id IN $edge_ids OR type(r) = 'HOLDS_ACCOUNT')
  RETURN collect(r) AS rels
}
RETURN [n IN nodes | {props: properties(n), labels: labels(n)}] AS nodes,
       [r IN rels | {props: properties(r), type: type(r), source: startNode(r).id,
                     target: endNode(r).id}] AS edges
"""


def _subject_ids(payload: object, flagged: list[str]) -> list[str]:
    """The C4 subjects in their payload order, each once (FLAGS carries no order); the FLAGS
    targets, sorted, only if the payload cannot be read."""
    try:
        order = [str(subject["entity_id"]) for subject in json.loads(str(payload))["subjects"]]
    except ValueError, KeyError, TypeError:
        order = sorted(flagged)
    return list(dict.fromkeys(order))


def _summary(row: Mapping[str, Any]) -> AlertSummary:
    alert = row["alert"]
    return AlertSummary(
        alert_id=alert["alert_id"],
        typology=alert["typology"],
        priority=alert["priority"],
        pattern_strength=float(alert["pattern_strength"]),
        headline=alert["headline"],
        created_at=alert["created_at"],
        subject_ids=_subject_ids(alert["payload"], list(row["flagged"])),
        involves_real_entities=alert["involves_real_entities"],
        synthetic_activity=alert["synthetic_activity"],
    )


def _digest(filters: Mapping[str, str | None]) -> str:
    text = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def encode_cursor(rank: int, strength: float, alert_id: str, digest: str) -> str:
    text = json.dumps([rank, strength, alert_id, digest], separators=(",", ":"))
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, digest: str) -> dict[str, Any]:
    """The sort key after which the page starts; a 422 problem for any other cursor."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        rank, strength, alert_id, given = json.loads(
            base64.b64decode(padded, altchars=b"-_", validate=True)
        )
        valid = (
            given == digest
            and type(rank) is int
            and rank in (0, 1, 2)
            and type(strength) in (int, float)
            and math.isfinite(strength)
            and re.fullmatch(ALERT_ID_PATTERN, alert_id) is not None
        )
    except (binascii.Error, ValueError, TypeError) as error:
        raise ProblemError(422, BAD_CURSOR) from error
    if not valid:
        raise ProblemError(422, BAD_CURSOR)
    return {"rank": rank, "strength": float(strength), "alert_id": alert_id}


def queue(
    graph: GraphConnection,
    *,
    typology: str | None = None,
    priority: str | None = None,
    entity_id: str | None = None,
    run_id: str | None = None,
    limit: int,
    cursor: str | None = None,
) -> AlertPage:
    """One page of the alert queue; filters combine with AND."""
    filters = {"typology": typology, "priority": priority, "entity_id": entity_id, "run_id": run_id}
    digest = _digest(filters)
    after = decode_cursor(cursor, digest) if cursor is not None else None
    rows = graph.read(QUEUE, {**filters, "after": after, "limit": limit + 1})
    items = [_summary(row) for row in rows[:limit]]
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        alert = last["alert"]
        next_cursor = encode_cursor(
            last["rank"], float(alert["pattern_strength"]), alert["alert_id"], digest
        )
    return AlertPage(items=items, next_cursor=next_cursor)


def detail(graph: GraphConnection, alert_id: str) -> AlertDetail:
    """The complete C4 alert from `payload` and its evidence subgraph."""
    records = graph.read(PAYLOAD, {"alert_id": alert_id})
    if not records:
        raise ProblemError(404, NOT_FOUND)
    try:
        alert = Alert.model_validate_json(records[0]["payload"])
    except ValidationError as error:
        logger.error("alert %s does not validate as C4: %s", alert_id, error)
        raise ProblemError(500, STALE) from error
    node_ids = list(
        dict.fromkeys([*alert.evidence.node_ids, *(s.entity_id for s in alert.subjects)])
    )
    row = graph.read(EVIDENCE, {"node_ids": node_ids, "edge_ids": alert.evidence.edge_ids})[0]
    order = {node_id: index for index, node_id in enumerate(node_ids)}
    nodes = sorted(map(shapes.graph_node, row["nodes"]), key=lambda node: order[node.id])
    hops = {edge_id: index for index, edge_id in enumerate(alert.evidence.edge_ids)}
    edges = sorted(
        map(shapes.graph_edge, row["edges"]),
        key=lambda edge: (hops.get(edge.id, len(hops)), edge.id),
    )
    size = max(1, len(nodes), math.ceil(len(edges) / 2))  # never truncated: limits fit it
    evidence = shapes.subgraph(nodes, edges, truncated=False, max_nodes=size)
    try:
        return AlertDetail(alert=alert, evidence=evidence)
    except ValidationError as error:
        logger.error("alert %s: evidence missing from the graph: %s", alert_id, error)
        raise ProblemError(500, MISSING_EVIDENCE) from error
