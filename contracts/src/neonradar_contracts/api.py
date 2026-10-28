"""C3 API v1.2.0: every request and response model of the NeonRadar API (PHASE-1.md 5.3, with
the additions of PHASE-2.md 5.3: the resolution endpoint and open or closed effective shares;
and of PHASE-4.md 5.3: the copilot's request and answer, detection runs and shape names).

The FastAPI app (`neonradar_api.main.create_app`) declares its routes with these models; its
OpenAPI document is committed at contracts/openapi/v1.json, and the UI generates its TypeScript
types from that file. Field rules, sources in the graph (C2) and the values that stay null in v1
are in contracts/C3-api.md. Every object is closed and strict, like C4. A field that may be
empty is `T | None` and always present, so generated types say `field: T | null`. The response
fields that 1.2.0 adds have defaults, so 1.1.0 answers stay valid; the server always sends
them, and the OpenAPI document marks them required (`json_schema_serialization_defaults_required`).
"""

from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from neonradar_contracts.alert import (
    ENTITY_ID_PATTERN,
    HEADLINE_MAX,
    VERSION_PATTERN,
    Alert,
    AlertId,
    CitationKey,
    EntityId,
    FiniteJsonValue,
    Priority,
    Slug,
    Text,
    UtcTime,
)
from neonradar_contracts.graph import (
    NODE_MAPPINGS,
    POSSIBLY_SAME_AS_ID_INFIX,
    EntityResolution,
    PossibleMatchMethod,
)

API_PREFIX: Final = "/api/v1"
# C3 1.2.0 (PHASE-4.md 5.3): at most 5 context ids (20 in 1.1.0), still C1 node ids.
MAX_CONTEXT_ENTITIES: Final = 5
MAX_COPILOT_SLOTS: Final = 8
TEMPLATE_ID_PATTERN: Final = r"^[a-z][a-z0-9_]{1,63}$"
SLOT_NAME_PATTERN: Final = r"^[a-z][a-z0-9_]{1,31}$"
MAX_ENTITY_ALERTS: Final = 50
MAX_CURSOR_LENGTH: Final = 512
# PHASE-2.md 5.3: ownership and paths limits, the query timeout and the possible-match cap.
MAX_OWNERSHIP_PATHS: Final = 200
MAX_SHORTEST_PATHS: Final = 5
MAX_PATH_SUBGRAPH_NODES: Final = 500
QUERY_TIMEOUT_SECONDS: Final = 5.0
MAX_POSSIBLE_MATCHES: Final = 50
NOT_CONFIRMED: Final = "not confirmed"
EFFECTIVE_SHARE_NOTE: Final = (
    "An effective share is NeonRadar's calculation from the published bands, not a figure any "
    "register records, and not the result of a sanctions ownership test."
)

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
# The C2 relationship types C3 shows: the 16 built from records and, from 1.1.0, the unconfirmed
# POSSIBLY_SAME_AS, which the network returns like any other relationship (PHASE-2.md 5.2).
# FLAGS, PRODUCED and RESOLVED_TO never appear in C3.
RelationshipType = Literal[
    "OWNS", "CONTROLS", "CONSOLIDATES", "DIRECTOR_OF", "HOLDS_ACCOUNT", "PAID", "HAS_ADDRESS",
    "REPRESENTS", "FAMILY_OF", "ASSOCIATE_OF", "MEMBER_OF", "EMPLOYED_BY", "LINKED_TO",
    "SUCCEEDED_BY", "HOLDS_POSITION", "SUBJECT_OF", "POSSIBLY_SAME_AS",
]  # fmt: skip
# `GET /paths` without `rel_types` (PHASE-2.md 5.3): HAS_ADDRESS, LINKED_TO and POSSIBLY_SAME_AS
# are used only when asked for.
PATHS_DEFAULT_TYPES: Final[tuple[RelationshipType, ...]] = (
    "OWNS", "CONTROLS", "CONSOLIDATES", "DIRECTOR_OF", "REPRESENTS", "FAMILY_OF", "ASSOCIATE_OF",
    "MEMBER_OF", "EMPLOYED_BY", "SUCCEEDED_BY", "HOLDS_POSITION", "SUBJECT_OF", "HOLDS_ACCOUNT",
    "PAID",
)  # fmt: skip
# The typology catalog's tier and status (5.4); neonradar_detect.catalog uses these.
TypologyTier = Literal["core", "extended", "explainer_only"]
TypologyStatus = Literal["draft", "approved", "retired"]
OwnershipDirection = Literal["up", "down"]
# How a source record joined its entity (PHASE-2.md 5.3): `identity` for a single-record
# entity, else the method of its C2 RESOLVED_TO (graph.RESOLVED_TO_METHODS).
MemberMethod = Literal["identity", "anchor", "deterministic", "probabilistic", "human"]

# The relationship ids C3 shows: C4's EdgeId forms plus, from 1.1.0, `<a>|psa|<b>` for
# POSSIBLY_SAME_AS (C2 1.1.0). C4 keeps EdgeId: detectors never use POSSIBLY_SAME_AS, so it is
# never alert evidence.
_ID = ENTITY_ID_PATTERN.removeprefix("^").removesuffix("$")
GRAPH_EDGE_ID_PATTERN: Final = rf"^{_ID}(\|(addr|sanction|{POSSIBLY_SAME_AS_ID_INFIX})\|{_ID})?$"
GraphEdgeId = Annotated[str, Field(pattern=GRAPH_EDGE_ID_PATTERN)]
Count = Annotated[int, Field(ge=0)]
Share = Annotated[float, Field(ge=0, le=100)]
Probability = Annotated[float, Field(ge=0, le=1)]
# A deterministic rule id (PHASE-2.md 7.1.2: D1 to D7).
RuleId = Annotated[str, Field(pattern=r"^D[1-9][0-9]*$")]
# A resolution run id (PHASE-2.md 4.4): `er-<UTC yyyymmddThhmmss>-<4 hex>`.
ResolutionRunId = Annotated[
    str, Field(pattern=r"^er-[0-9]{8}T[0-9]{6}-[0-9a-f]{4}$", min_length=23, max_length=23)
]
Version = Annotated[str, Field(pattern=VERSION_PATTERN)]
# A PEP 440 public version with an optional local part, for the API package (`0.1.0`,
# `1.0.0rc1`, `0.2.0.dev3+g1a2b3c`); contract versions stay MAJOR.MINOR.PATCH.
PackageVersion = Annotated[
    str,
    Field(
        pattern=(
            r"^[0-9]+(\.[0-9]+)*((a|b|rc)[0-9]+)?(\.post[0-9]+)?(\.dev[0-9]+)?"
            r"(\+[a-z0-9]+(\.[a-z0-9]+)*)?$"
        )
    ),
]

# C2 properties that never appear in a C3 property map: they are top-level fields (`id`,
# `schema`, `caption`), flags (`synthetic`), index plumbing (`names_text`), source topics that
# 7.1 keeps away from entities (`topics`), or Phase 2 merge history (`referents`, in provenance).
NODE_PROPERTIES_LEFT_OUT: Final = frozenset(
    {"id", "schema", "caption", "names_text", "synthetic", "topics", "referents"}
)
# EntityDetail also lifts `names`, `countries` and `datasets` into its own fields.
DETAIL_PROPERTIES_LEFT_OUT: Final = NODE_PROPERTIES_LEFT_OUT | {"names", "countries", "datasets"}
EDGE_PROPERTIES_LEFT_OUT: Final = frozenset({"id", "topics"})


class _Model(BaseModel):
    # A response field with a default (C3 1.2.0) is still always sent, so the OpenAPI document
    # (serialization mode) lists it as required; request models are unaffected.
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        allow_inf_nan=False,
        json_schema_serialization_defaults_required=True,
    )


class _WithSchema(_Model):
    """Models with an FtM `schema` field: the attribute is `schema_` (BaseModel has `schema`)."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        allow_inf_nan=False,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=False,
    )


def _distinct(values: list[str], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} must not repeat a value")


def _no_reserved(
    properties: dict[str, FiniteJsonValue], reserved: frozenset[str], what: str
) -> None:
    found = sorted(reserved & set(properties))
    if found:
        raise ValueError(f"{what} must not hold {found} (C3: top-level fields or left out)")


def _mapping_labels(labels: list[NodeLabel], schema: NodeSchema) -> None:
    expected = list(NODE_MAPPINGS[schema].labels)
    if labels != expected:
        raise ValueError(f"labels of a {schema} node are {expected} (C2 mapping)")


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
    properties: dict[str, FiniteJsonValue]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _mapping_labels(self.labels, self.schema_)
        _no_reserved(self.properties, NODE_PROPERTIES_LEFT_OUT, "node properties")
        return self


class GraphEdge(_Model):
    """A C2 relationship built from a record; `id` is its C2 id, never a Neo4j elementId."""

    id: GraphEdgeId
    type: RelationshipType
    source: EntityId
    target: EntityId
    properties: dict[str, FiniteJsonValue]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _no_reserved(self.properties, EDGE_PROPERTIES_LEFT_OUT, "edge properties")
        return self


class SubgraphLimits(_Model):
    """The caps applied when the subgraph was built; `max_edges` is twice `max_nodes`."""

    max_nodes: Annotated[int, Field(ge=1)]
    max_edges: Annotated[int, Field(ge=2)]

    @model_validator(mode="after")
    def _ratio(self) -> Self:
        if self.max_edges != 2 * self.max_nodes:
            raise ValueError("limits.max_edges must be 2 x limits.max_nodes")
        return self


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

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _mapping_labels(self.labels, self.schema_)
        return self


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

    alert_id: AlertId
    typology: Slug
    priority: Priority
    pattern_strength: Annotated[float, Field(ge=0, le=1)]
    headline: Annotated[str, Field(min_length=1, max_length=HEADLINE_MAX)]
    created_at: UtcTime
    # In the order of the C4 subjects, each once.
    subject_ids: Annotated[
        list[EntityId], Field(min_length=1, json_schema_extra={"uniqueItems": True})
    ]
    involves_real_entities: bool
    synthetic_activity: bool
    # 1.2.0 (PHASE-4.md 5.3; PHASE-3.md R9): the typology's neutral shape name, null when the
    # typology has none; `display_name` is the name the queue shows: the shape name when the
    # alert involves a real entity, the typology's name otherwise (`neonradar_api.alert_names`).
    shape_name: str | None = None
    display_name: str

    @model_validator(mode="after")
    def _distinct_subjects(self) -> Self:
        _distinct(self.subject_ids, "subject_ids")
        return self


class EntityDetail(_Model):
    """One node with its names, properties, identifiers, provenance and alerts."""

    entity: EntitySummary
    names: list[str]
    properties: dict[str, FiniteJsonValue]
    identifiers: dict[str, Annotated[list[Text], Field(min_length=1)]]
    provenance: Annotated[list[ProvenanceRecord], Field(min_length=1)]
    relationship_counts: dict[RelationshipType, Annotated[int, Field(ge=1)]]
    alerts: Annotated[list[AlertSummary], Field(max_length=MAX_ENTITY_ALERTS)]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        for key, values in self.identifiers.items():
            _distinct(values, f"identifiers.{key}")
        _no_reserved(self.properties, DETAIL_PROPERTIES_LEFT_OUT, "entity properties")
        return self


class PathRef(_Model):
    """A path as C2 ids: `edge_ids[i]` joins `node_ids[i]` and `node_ids[i + 1]`. The effective
    share range is the product of the OWNS share bands along an ownership path (PHASE-2.md 5.3);
    each bound's flag says whether it is open ("more than", "less than") or closed ("at least",
    "at most"), and is null exactly when the bound is."""

    node_ids: Annotated[list[EntityId], Field(min_length=1)]
    edge_ids: list[GraphEdgeId]
    effective_share_min: Annotated[
        Share | None,
        Field(
            description="The product of the lower share bounds (each / 100) along the path, "
            "times 100, rounded to 4 decimals; null when a relationship has no lower bound. "
            + EFFECTIVE_SHARE_NOTE
        ),
    ]
    effective_share_max: Annotated[
        Share | None,
        Field(
            description="The product of the upper share bounds (each / 100) along the path, "
            "times 100, rounded to 4 decimals; null when a relationship has no upper bound. "
            + EFFECTIVE_SHARE_NOTE
        ),
    ]
    effective_share_min_exclusive: Annotated[
        bool | None,
        Field(
            description="True when any relationship's lower bound is exclusive (say \"more "
            'than"), false when all are inclusive (say "at least"); null when '
            "effective_share_min is null. " + EFFECTIVE_SHARE_NOTE
        ),
    ]
    effective_share_max_exclusive: Annotated[
        bool | None,
        Field(
            description="True when any relationship's upper bound is exclusive (say \"less "
            'than"), false when all are inclusive (say "at most"); null when '
            "effective_share_max is null. " + EFFECTIVE_SHARE_NOTE
        ),
    ]

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if len(self.edge_ids) != len(self.node_ids) - 1:
            raise ValueError("a path has one edge fewer than it has nodes")
        low, high = self.effective_share_min, self.effective_share_max
        if low is not None and high is not None and low > high:
            raise ValueError("effective_share_min must not exceed effective_share_max")
        for bound, flag, name in (
            (low, self.effective_share_min_exclusive, "min"),
            (high, self.effective_share_max_exclusive, "max"),
        ):
            if (bound is None) != (flag is None):
                raise ValueError(
                    f"effective_share_{name}_exclusive is null exactly when "
                    f"effective_share_{name} is"
                )
        return self


def _paths_in(paths: list[PathRef], subgraph: Subgraph, start: str, end: str | None) -> None:
    """Every path starts at `start` (and ends at `end`), and its ids are in the subgraph."""
    nodes = {node.id for node in subgraph.nodes}
    edges = {edge.id: edge for edge in subgraph.edges}
    for path in paths:
        if path.node_ids[0] != start or (end is not None and path.node_ids[-1] != end):
            raise ValueError(f"every path runs from {start}" + (f" to {end}" if end else ""))
        missing = sorted(set(path.node_ids) - nodes) + sorted(set(path.edge_ids) - set(edges))
        if missing:
            raise ValueError(f"path ids missing from the subgraph: {missing}")
        for i, edge_id in enumerate(path.edge_ids):
            ends = {edges[edge_id].source, edges[edge_id].target}
            if ends != {path.node_ids[i], path.node_ids[i + 1]}:
                raise ValueError(f"edge {edge_id} does not join path nodes {i} and {i + 1}")


class OwnershipResponse(_Model):
    root_id: EntityId
    direction: OwnershipDirection
    paths: Annotated[list[PathRef], Field(max_length=MAX_OWNERSHIP_PATHS)]
    subgraph: Subgraph

    @model_validator(mode="after")
    def _paths(self) -> Self:
        _paths_in(self.paths, self.subgraph, self.root_id, None)
        return self


class PathsResponse(_Model):
    from_id: EntityId
    to_id: EntityId
    paths: Annotated[list[PathRef], Field(max_length=MAX_SHORTEST_PATHS)]
    subgraph: Subgraph

    @model_validator(mode="after")
    def _paths(self) -> Self:
        _paths_in(self.paths, self.subgraph, self.from_id, self.to_id)
        return self


# Entity resolution (PHASE-2.md 5.3) --------------------------------------------------------


class ResolutionMember(_WithSchema):
    """One source record of an entity and how it joined: a single-record entity has one member
    with method `identity`; a merged entity has one `anchor` and members joined by a D rule
    (`deterministic`, `human` for D7), or by `probabilistic` matching."""

    record_id: EntityId
    dataset: Slug
    schema_: Annotated[NodeSchema, Field(alias="schema")]
    caption: Text
    names: list[str]
    method: MemberMethod
    rule: RuleId | None
    match_probability: Probability | None
    decided_at: UtcTime | None
    explanation: Text

    @model_validator(mode="after")
    def _method(self) -> Self:
        if self.method == "deterministic" and self.rule is None:
            raise ValueError("a deterministic member names its D rule")
        if self.method == "probabilistic" and self.match_probability is None:
            raise ValueError("a probabilistic member has a match_probability")
        return self


class PossibleMatch(_Model):
    """Another entity that may describe the same person or company: never confirmed, never
    merged, and flags never cross it (PHASE-2.md 0.5 item 3, guardrail G8)."""

    entity: EntitySummary
    match_probability: Probability | None
    method: PossibleMatchMethod
    rule: RuleId | None
    reasons: list[str]
    evidence: list[str]
    explanation: Text

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if (self.method == "probabilistic") != (self.match_probability is not None):
            raise ValueError(
                "match_probability is set for probabilistic possible matches and null for "
                "deterministic and source_hint ones"
            )
        if self.method == "deterministic" and self.rule is None:
            raise ValueError("a deterministic possible match names its D rule")
        if NOT_CONFIRMED not in self.explanation:
            raise ValueError(f'a possible-match explanation says "{NOT_CONFIRMED}"')
        return self


class ResolutionResponse(_Model):
    """How an entity was resolved: its source records and its possible matches. `canonical` is
    true for an entity merged from two or more records (`cluster_size`, one member each)."""

    entity_id: EntityId
    canonical: bool
    resolution: EntityResolution
    cluster_size: Annotated[int, Field(ge=1)]
    members: Annotated[list[ResolutionMember], Field(min_length=1)]
    possible_matches: Annotated[list[PossibleMatch], Field(max_length=MAX_POSSIBLE_MATCHES)]
    resolver_version: Text | None
    run_id: ResolutionRunId | None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len(self.members) != self.cluster_size:
            raise ValueError("an entity has one member per source record (cluster_size)")
        _distinct([member.record_id for member in self.members], "member record ids")
        if self.canonical != (self.cluster_size > 1):
            raise ValueError("canonical is true exactly for entities merged from two or more")
        if (self.resolution == "identity") == self.canonical:
            raise ValueError("resolution is identity exactly for single-record entities")
        methods = [member.method for member in self.members]
        if self.canonical and (methods.count("anchor") != 1 or "identity" in methods):
            raise ValueError("a merged entity has exactly one anchor and no identity member")
        if not self.canonical and methods != ["identity"]:
            raise ValueError("a single-record entity has one member with method identity")
        others = [match.entity.id for match in self.possible_matches]
        _distinct(others, "possible match entities")
        if self.entity_id in others:
            raise ValueError("an entity is not a possible match of itself")
        return self


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
        if self.evidence.truncated:
            raise ValueError("an alert's evidence subgraph is never truncated")
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
    # 1.2.0: the typology file's neutral shape name (PHASE-3.md R9), null when it has none.
    shape_name: str | None = None


class TypologyDetail(TypologySummary):
    """The catalog file's definition; `definition_markdown` is the explainer, null if absent."""

    definition_markdown: str | None
    graph_pattern: Text
    citations: list[Citation]
    parameters: dict[str, FiniteJsonValue]
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
    """The texts of contracts/wording/, verbatim: PHASE-1.md 7.1, and from C3 1.1.0 the real
    data notice version 2 (`real-data-v2`, PHASE-2.md 5.3)."""

    standing: Text
    synthetic_demo: Text
    real_data: Text


class GraphCounts(_Model):
    """Node counts by label and relationship counts by type; both empty when unreadable."""

    nodes_by_label: dict[str, Count]
    relationships_by_type: dict[str, Count]


class MetaResponse(_Model):
    app_version: PackageVersion
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


# Detection runs (1.2.0) -------------------------------------------------------------------


class DetectorVersion(_Model):
    name: str
    version: str


class RunSummary(_Model):
    """A `:DetectionRun` node (C2 1.2.0): `detectors` parsed from its JSON list; the times are
    UTC ISO strings whether the node stores strings or temporal values."""

    run_id: str
    status: Literal["ok", "failed"]
    started_at: str | None
    finished_at: str | None
    profile: str | None
    window_start: str | None
    window_end: str | None
    typologies: list[str]
    detectors: list[DetectorVersion]
    alert_count: int
    params_sha256: str | None


class TypologyRunCounts(_Model):
    """One typology's counts in a run summary (PHASE-3.md 7.5.3): counts only, on every profile."""

    findings: int
    alerts: int
    duplicates: int
    withheld: dict[str, int]
    stats: dict[str, FiniteJsonValue]


class RunDetail(_Model):
    run: RunSummary
    typologies: dict[str, TypologyRunCounts]
    alerts: int
    withheld: dict[str, int]


# Copilot (Phase 4; 1.2.0) -----------------------------------------------------------------

TemplateId = Annotated[str, Field(pattern=TEMPLATE_ID_PATTERN)]
SlotName = Annotated[str, Field(pattern=SLOT_NAME_PATTERN)]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
# Why the copilot refused (PHASE-4.md 7.4.1 and 7.4.2).
RefusalCode = Literal[
    "judgement",
    "scoring",
    "decision",
    "write_request",
    "query_text",
    "instructions",
    "personal_details",
    "real_person",
    "real_payments",
    "wording_check",
]


class CopilotRequest(_Model):
    """A question; `template_id` and `slots` name a template and its grounded values directly
    (the menu, the answer to a clarifying question, the confirmation of a reading)."""

    question: Annotated[str, Field(min_length=1, max_length=500)]
    context_entity_ids: Annotated[list[EntityId], Field(max_length=MAX_CONTEXT_ENTITIES)] = []
    template_id: TemplateId | None = None
    slots: Annotated[dict[SlotName, ShortText], Field(max_length=MAX_COPILOT_SLOTS)] = {}


class CopilotModel(_Model):
    name: str
    digest: str


class CopilotQuery(_Model):
    """One query an answer ran: the query file's name, its exact text and its parameters."""

    name: str
    cypher: str
    parameters: dict[str, FiniteJsonValue]


class CopilotChoice(_Model):
    """One entity or alert a question could mean; send `value` back in `slots[slot]`."""

    slot: str
    value: str
    label: str
    detail: str | None = None


class CopilotAnswer(_Model):
    """Every outcome of a question. Only an answer carries queries and evidence: a refusal, an
    unsupported question and a clarifying question carry none, because the search for a name
    that did not ground would repeat the person's words (PHASE-4.md 5.3)."""

    status: Literal["answered", "refused", "unsupported", "needs_clarification"]
    answer_text: str | None
    template_id: str | None
    cypher: str | None
    parameters: dict[str, FiniteJsonValue] | None
    subgraph: Subgraph | None
    refusal_reason: str | None
    template_version: str | None = None
    interpretation: str | None = None
    router: Literal["pattern", "model", "direct"] | None = None
    model: CopilotModel | None = None
    slots: dict[str, str] = {}
    facts: list[dict[str, FiniteJsonValue]] = []
    queries: list[CopilotQuery] = []
    refusal_code: RefusalCode | None = None
    choices: list[CopilotChoice] = []
    notices: list[str] = []
    suggestions: list[str] = []

    @model_validator(mode="after")
    def _complete(self) -> Self:
        if self.status == "answered":
            if self.answer_text is None or self.refusal_reason is not None:
                raise ValueError("an answered question needs answer_text and no refusal_reason")
        elif self.queries or any(
            getattr(self, name) is not None for name in ("cypher", "parameters", "subgraph")
        ):
            raise ValueError(
                "only an answered question carries queries, cypher, parameters or a subgraph"
            )
        if self.status == "refused":
            if not self.refusal_reason:
                raise ValueError("a refused question needs a refusal_reason")
        elif self.refusal_code is not None:
            raise ValueError("only a refused question carries a refusal_code")
        return self


class CopilotSlot(_Model):
    name: str
    kind: Literal["entity", "alert", "percent", "period", "direction"]
    required: bool
    description: str
    labels: list[str] = []
    values: list[str] = []


class CopilotTemplate(_Model):
    id: str
    version: str
    title: str
    category: Literal["records", "connections", "patterns", "payments", "meta"]
    description: str
    examples: list[str]
    slots: list[CopilotSlot]


class CopilotInfo(_Model):
    """What `GET /copilot` returns: the mode, the standing notice
    (`contracts/wording/copilot-notice-v1.txt`), the badge and the template catalog."""

    catalog_version: str
    router: Literal["pattern", "pattern+model"]
    model: CopilotModel | None
    badge: str
    notice: str
    templates: list[CopilotTemplate]


# Errors -----------------------------------------------------------------------------------


class Problem(_Model):
    """RFC 9457 problem details (`application/problem+json`); `type` is `about:blank` in v1."""

    type: Text
    title: Text
    status: Annotated[int, Field(ge=400, le=599)]
    detail: str
    instance: str
