"""C3 API v1.0.0: every request and response model of the NeonRadar API (PHASE-1.md 5.3).

The FastAPI app (`neonradar_api.main.create_app`) declares its routes with these models; its
OpenAPI document is committed at contracts/openapi/v1.json, and the UI generates its TypeScript
types from that file. Field rules, sources in the graph (C2) and the values that stay null in v1
are in contracts/C3-api.md. Every object is closed and strict, like C4. Response fields have no
defaults: a field that may be empty is `T | None` and always present, so generated types say
`field: T | null`.
"""

from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from neonradar_contracts.alert import (
    ALERT_ID_PATTERN,
    HEADLINE_MAX,
    VERSION_PATTERN,
    Alert,
    CitationKey,
    EdgeId,
    EntityId,
    Priority,
    Slug,
    Text,
    UtcTime,
)

API_PREFIX: Final = "/api/v1"
MAX_CONTEXT_ENTITIES: Final = 20
MAX_ENTITY_ALERTS: Final = 50
MAX_CURSOR_LENGTH: Final = 512

# C2 node labels (flag labels excluded: they are in NodeFlags) and the FtM schemata of nodes.
NodeLabel = Literal[
    "Entity", "LegalEntity", "Person", "Organization", "Company", "PublicBody", "Address",
    "Account", "Position", "Sanction",
]  # fmt: skip
NodeSchema = Literal[
    "Person", "Company", "Organization", "PublicBody", "LegalEntity", "Address", "BankAccount",
    "Position", "Sanction",
]  # fmt: skip
# The labels `GET /search` filters on (5.3).
SearchLabel = Literal["Person", "Company", "Organization", "LegalEntity", "Address", "Account"]
# C2 relationship types built from records; FLAGS, PRODUCED and RESOLVED_TO never appear in C3.
RelationshipType = Literal[
    "OWNS", "CONTROLS", "CONSOLIDATES", "DIRECTOR_OF", "HOLDS_ACCOUNT", "PAID", "HAS_ADDRESS",
    "REPRESENTS", "FAMILY_OF", "ASSOCIATE_OF", "MEMBER_OF", "EMPLOYED_BY", "LINKED_TO",
    "SUCCEEDED_BY", "HOLDS_POSITION", "SUBJECT_OF",
]  # fmt: skip
# The typology catalog's tier and status (5.4); neonradar_detect.catalog uses these.
TypologyTier = Literal["core", "extended", "explainer_only"]
TypologyStatus = Literal["draft", "approved", "retired"]
OwnershipDirection = Literal["up", "down"]

Count = Annotated[int, Field(ge=0)]
Share = Annotated[float, Field(ge=0, le=100)]
Version = Annotated[str, Field(pattern=VERSION_PATTERN)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class _WithSchema(_Model):
    """Models with an FtM `schema` field: the attribute is `schema_` (BaseModel has `schema`)."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=False,
    )


def _distinct(values: list[str], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} must not repeat a value")


# Graph shapes -----------------------------------------------------------------------------


class NodeFlags(_Model):
    """The C2 flag labels: facts a source published, never findings of NeonRadar."""

    synthetic: bool
    sanctioned: bool
    pep: bool
    rca: bool


class GraphNode(_WithSchema):
    """A C2 node (`:Entity` or `:Sanction`); `properties` holds its other C2 properties."""

    id: EntityId
    labels: Annotated[list[NodeLabel], Field(min_length=1)]
    schema_: Annotated[NodeSchema, Field(alias="schema")]
    caption: Text
    flags: NodeFlags
    properties: dict[str, JsonValue]


class GraphEdge(_Model):
    """A C2 relationship built from a record; `id` is its C2 id, never a Neo4j elementId."""

    id: EdgeId
    type: RelationshipType
    source: EntityId
    target: EntityId
    properties: dict[str, JsonValue]


class SubgraphLimits(_Model):
    """The caps applied when the subgraph was built."""

    max_nodes: Annotated[int, Field(ge=1)]
    max_edges: Annotated[int, Field(ge=1)]


class Subgraph(_Model):
    """Nodes and edges, one to one with Cytoscape elements; `truncated` when a cap cut it."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool
    limits: SubgraphLimits

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        node_ids = [node.id for node in self.nodes]
        _distinct(node_ids, "subgraph node ids")
        _distinct([edge.id for edge in self.edges], "subgraph edge ids")
        known = set(node_ids)
        loose = sorted({end for edge in self.edges for end in (edge.source, edge.target)} - known)
        if loose:
            raise ValueError(f"edges point to nodes outside the subgraph: {loose}")
        if len(self.nodes) > self.limits.max_nodes or len(self.edges) > self.limits.max_edges:
            raise ValueError("the subgraph is larger than its limits")
        return self


# Entities and search ----------------------------------------------------------------------


class EntitySummary(_WithSchema):
    """What a list or a search hit shows about a node."""

    id: EntityId
    schema_: Annotated[NodeSchema, Field(alias="schema")]
    caption: Text
    labels: Annotated[list[NodeLabel], Field(min_length=1)]
    flags: NodeFlags
    countries: list[str]
    datasets: Annotated[list[Slug], Field(min_length=1)]


class SearchHit(_Model):
    """`score` orders the hits of one response only; it is never a risk measure."""

    entity: EntitySummary
    score: Annotated[float, Field(ge=0)]
    matched_name: Text


class SearchResponse(_Model):
    query: str
    items: list[SearchHit]
    total_estimate: Count

    @model_validator(mode="after")
    def _estimate(self) -> Self:
        if self.total_estimate < len(self.items):
            raise ValueError("total_estimate must be at least the number of items")
        return self


class ProvenanceRecord(_Model):
    """Where a node's data came from; v1 has one per referent and `retrieved_at` null."""

    dataset: Slug
    record_id: EntityId
    retrieved_at: UtcTime | None
    source_url: str | None


class AlertSummary(_Model):
    """One row of the alert queue, from the `:Alert` scalar properties (C2) and its subjects."""

    alert_id: Annotated[str, Field(pattern=ALERT_ID_PATTERN)]
    typology: Slug
    priority: Priority
    pattern_strength: Annotated[float, Field(ge=0, le=1)]
    headline: Annotated[str, Field(min_length=1, max_length=HEADLINE_MAX)]
    created_at: UtcTime
    subject_ids: Annotated[list[EntityId], Field(min_length=1)]
    involves_real_entities: bool
    synthetic_activity: bool


class EntityDetail(_Model):
    """One node with its names, properties, identifiers, provenance and alerts."""

    entity: EntitySummary
    names: list[str]
    properties: dict[str, JsonValue]
    identifiers: dict[str, Annotated[list[Text], Field(min_length=1)]]
    provenance: Annotated[list[ProvenanceRecord], Field(min_length=1)]
    relationship_counts: dict[RelationshipType, Annotated[int, Field(ge=1)]]
    alerts: Annotated[list[AlertSummary], Field(max_length=MAX_ENTITY_ALERTS)]

    @model_validator(mode="after")
    def _identifiers(self) -> Self:
        for key, values in self.identifiers.items():
            _distinct(values, f"identifiers.{key}")
        return self


class PathRef(_Model):
    """A path as C2 ids; the effective share is the product of OWNS share bands (Phase 2)."""

    node_ids: Annotated[list[EntityId], Field(min_length=1)]
    edge_ids: list[EdgeId]
    effective_share_min: Share | None
    effective_share_max: Share | None

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        low, high = self.effective_share_min, self.effective_share_max
        if low is not None and high is not None and low > high:
            raise ValueError("effective_share_min must not exceed effective_share_max")
        return self


class OwnershipResponse(_Model):
    root_id: EntityId
    direction: OwnershipDirection
    paths: list[PathRef]
    subgraph: Subgraph


class PathsResponse(_Model):
    from_id: EntityId
    to_id: EntityId
    paths: list[PathRef]
    subgraph: Subgraph


# Alerts -----------------------------------------------------------------------------------


class AlertPage(_Model):
    """One page of the alert queue; pass `next_cursor` back unchanged, null on the last page."""

    items: list[AlertSummary]
    next_cursor: Annotated[str, Field(min_length=1, max_length=MAX_CURSOR_LENGTH)] | None


class AlertDetail(_Model):
    """The complete C4 alert and its evidence as a subgraph."""

    alert: Alert
    evidence: Subgraph

    @model_validator(mode="after")
    def _evidence(self) -> Self:
        nodes = {node.id for node in self.evidence.nodes}
        edges = {edge.id for edge in self.evidence.edges}
        wanted = set(self.alert.evidence.node_ids)
        wanted |= {subject.entity_id for subject in self.alert.subjects}
        missing = sorted(wanted - nodes) + sorted(set(self.alert.evidence.edge_ids) - edges)
        if missing:
            raise ValueError(f"evidence subgraph lacks alert evidence or subjects: {missing}")
        return self


# Typologies -------------------------------------------------------------------------------


class Citation(_Model):
    """A bibliography entry (docs/sources/bibliography.yaml); `year` is null for living sources."""

    key: CitationKey
    title: Text
    publisher: Text
    year: int | None
    url: Text


class TypologySummary(_Model):
    slug: Slug
    name: Text
    tier: TypologyTier
    status: TypologyStatus
    summary: Text
    detector_available: bool


class TypologyDetail(TypologySummary):
    """The catalog file's definition; `definition_markdown` is the explainer, null if absent."""

    definition_markdown: str | None
    graph_pattern: Text
    citations: list[Citation]
    parameters: dict[str, JsonValue]
    false_positives: list[Text]


# Meta and health --------------------------------------------------------------------------


class DatasetInfo(_Model):
    """A dataset of contracts/datasets.yaml; `record_count` is null when the graph is unreadable,
    `loaded_at` is null in v1 (C2 records no load)."""

    slug: Slug
    title: Text
    licence_id: Text
    licence_url: Text
    attribution: str | None
    synthetic: bool
    personal_data: bool
    record_count: Count | None
    loaded_at: UtcTime | None


class Disclaimers(_Model):
    """The texts of contracts/wording/ (PHASE-1.md 7.1, verbatim)."""

    standing: Text
    synthetic_demo: Text
    real_data: Text


class GraphCounts(_Model):
    """Node counts by label and relationship counts by type; both empty when unreadable."""

    nodes_by_label: dict[str, Count]
    relationships_by_type: dict[str, Count]


class MetaResponse(_Model):
    app_version: Version
    contracts_version: Version
    schema_version: Version
    datasets: list[DatasetInfo]
    disclaimers: Disclaimers
    counts: GraphCounts


class Neo4jStatus(_Model):
    connected: bool
    version: str | None
    edition: str | None


class HealthResponse(_Model):
    """`ok` exactly when Neo4j answers and both APOC and GDS are present."""

    status: Literal["ok", "degraded"]
    neo4j: Neo4jStatus
    apoc_version: str | None
    gds_version: str | None

    @model_validator(mode="after")
    def _status(self) -> Self:
        complete = self.neo4j.connected and None not in (self.apoc_version, self.gds_version)
        if (self.status == "ok") != complete:
            raise ValueError("status is ok exactly when Neo4j, APOC and GDS all answer")
        return self


# Copilot (Phase 4) ------------------------------------------------------------------------


class CopilotRequest(_Model):
    question: Annotated[str, Field(min_length=1, max_length=500)]
    context_entity_ids: Annotated[list[EntityId], Field(max_length=MAX_CONTEXT_ENTITIES)] = []


class CopilotAnswer(_Model):
    """An answer always carries its query and evidence subgraph; a refusal carries a reason."""

    status: Literal["answered", "refused", "unsupported"]
    answer_text: str | None
    template_id: str | None
    cypher: str | None
    parameters: dict[str, JsonValue] | None
    subgraph: Subgraph | None
    refusal_reason: str | None

    @model_validator(mode="after")
    def _complete(self) -> Self:
        if self.status == "answered":
            needed = ("answer_text", "cypher", "parameters", "subgraph")
            missing = [name for name in needed if getattr(self, name) is None]
            if missing or self.refusal_reason is not None:
                raise ValueError(
                    "an answered question needs answer_text, cypher, parameters and subgraph, "
                    "and no refusal_reason"
                )
        elif not self.refusal_reason or self.answer_text is not None:
            raise ValueError(f"a {self.status} question needs a refusal_reason and no answer_text")
        return self


# Errors -----------------------------------------------------------------------------------


class Problem(_Model):
    """RFC 9457 problem details (`application/problem+json`); `type` is `about:blank` in v1."""

    type: Text
    title: Text
    status: Annotated[int, Field(ge=400, le=599)]
    detail: str
    instance: str
