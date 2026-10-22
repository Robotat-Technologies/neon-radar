"""C2 graph schema (`versions.GRAPH_SCHEMA`): how C1 records become Neo4j nodes and
relationships, as data (PHASE-1.md 5.2; 1.1.0 adds entity resolution, PHASE-2.md 5.2; 1.2.0
adds overlays, the bridge invariants and detection-run fields, PHASE-3.md 5.2).

The tables of docs/build/PHASE-1.md 5.2, docs/build/PHASE-2.md 5.2 and
contracts/C2-graph-schema.md, written as data so
that the loader, the detectors, the API and the contract tests read one source. The code that
applies the mapping is `neonradar_graph.mapping`; the schema itself (constraints and indexes) is
`graph/schema/migrations/`. Property names on the left of a mapping are FtM properties, or
`nr.<key>` for the C1 `nr` extension; on the right are C2 graph properties.
"""

from dataclasses import dataclass, field
from typing import Final, Literal, get_args

from neonradar_contracts import versions

SCHEMA_VERSION: Final = versions.GRAPH_SCHEMA

PropertyKind = Literal["string", "list", "float", "integer", "boolean", "datetime"]
Condition = Literal["asset_is_account", "consolidation"]


@dataclass(frozen=True, slots=True, kw_only=True)
class NodeMapping:
    """An FtM schema whose records become nodes. `labels[0]` is the label the loader MERGEs on."""

    labels: tuple[str, ...]
    properties: dict[str, str]
    extra_names: tuple[str, ...] = ()  # FtM properties added to `names` (Address: `full`)
    # LIST properties set to an empty list when the record has no value (1.2.0:
    # `Sanction.provisions`); every other absent value is left out.
    empty_lists: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipMapping:
    """An FtM interval schema whose records become relationships.

    A schema with several mappings (Ownership) takes the first whose `condition` holds; None
    always holds. `asset_is_account`: the target record in the load is a BankAccount.
    `consolidation`: the record sets `nr.consolidation`. `defaults` are set when the record
    has no value for them (1.1.0: on OWNS the two bound flags and `is_nominee`, on CONTROLS
    the two bound flags, all false).
    """

    type: str
    source_prop: str
    target_prop: str
    properties: dict[str, str]
    condition: Condition | None = None
    defaults: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReferenceMapping:
    """An entity-typed property of a node record that becomes one relationship per value.

    The record that holds the property is the relationship's source or target (`record_end`).
    The relationship id is `<source id>|<id_infix>|<target id>`. A `nr.<key>` property whose
    value is an object is read by the id of the referenced record (`nr.address_roles`).
    """

    schema: str
    prop: str
    type: str
    record_end: Literal["source", "target"]
    id_infix: str
    properties: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TopicFlag:
    """A flag label set from FtM topics; `subtopics` also matches `<topic>.<anything>`."""

    label: str
    topic: str
    subtopics: bool


# Properties every node built from a record carries (5.2, "Common properties").
COMMON_NODE_PROPERTIES: Final = (
    "id", "schema", "caption", "names", "names_text", "countries", "topics", "datasets",
    "referents", "synthetic", "first_seen", "last_seen", "source_url",
)  # fmt: skip
# Properties every record-built relationship carries (all types except the support ones).
COMMON_RELATIONSHIP_PROPERTIES: Final = ("id", "datasets", "synthetic", "source_url")
NAME_PROPERTIES: Final = ("name", "alias", "previousName", "abbreviation")
NAMES_SEPARATOR: Final = " | "

# Graph property types; every property not listed is a STRING. A FtM property mapped to a
# STRING takes its first value in FtM's stored order; a LIST keeps every value. `datetime`
# values are sent as `<record value>Z` and converted by the loader with `datetime()`.
PROPERTY_KINDS: Final[dict[str, PropertyKind]] = {
    "names": "list", "countries": "list", "topics": "list", "datasets": "list",
    "referents": "list", "nationalities": "list", "natures_of_control": "list",
    "typologies": "list",
    "synthetic": "boolean", "is_nominee": "boolean", "involves_real_entities": "boolean",
    "synthetic_activity": "boolean",
    "share_pct_min": "float", "share_pct_max": "float", "amount": "float",
    "pattern_strength": "float", "match_probability": "float",
    "alert_count": "integer",
    "ts": "datetime",
    # 1.1.0 (PHASE-2.md 5.2)
    "psc_statements": "list", "names_latin": "list", "reasons": "list",
    "share_min_exclusive": "boolean", "share_max_exclusive": "boolean",
    "match_weight": "float",
    "cluster_size": "integer",
    # 1.2.0 (PHASE-3.md 5.2)
    "provisions": "list", "evidence_node_ids": "list", "evidence_edge_ids": "list",
}  # fmt: skip

_LEGAL_ENTITY = {
    "registrationNumber": "registration_number",
    "jurisdiction": "jurisdiction",
    "leiCode": "lei",
    "status": "status",
    "sector": "sector",
}
_ORGANIZATION = {
    "registrationNumber": "registration_number",
    "jurisdiction": "jurisdiction",
    "leiCode": "lei",
    "status": "status",
    "legalForm": "legal_form",
    "sector": "sector",
    "incorporationDate": "incorporation_date",
    "dissolutionDate": "dissolution_date",
}
_COMPANY = {
    **_ORGANIZATION,
    "nr.psc_statements": "psc_statements",  # 1.1.0
    "nr.accounts_category": "accounts_category",  # 1.1.0
}
_DATES = {"startDate": "start_date", "endDate": "end_date"}
# The open or closed bounds of a share band (1.1.0): absent flags mean a closed bound.
_BOUND_FLAGS = {
    "nr.share_pct_min_exclusive": "share_min_exclusive",
    "nr.share_pct_max_exclusive": "share_max_exclusive",
}
_BOUND_DEFAULTS = {"share_min_exclusive": False, "share_max_exclusive": False}

NODE_MAPPINGS: Final[dict[str, NodeMapping]] = {
    "Person": NodeMapping(
        labels=("Entity", "LegalEntity", "Person"),
        properties={"birthDate": "birth_date", "nationality": "nationalities", "gender": "gender"},
    ),
    "Company": NodeMapping(
        labels=("Entity", "LegalEntity", "Organization", "Company"), properties=_COMPANY
    ),
    "Organization": NodeMapping(
        labels=("Entity", "LegalEntity", "Organization"), properties=_ORGANIZATION
    ),
    "PublicBody": NodeMapping(
        labels=("Entity", "LegalEntity", "Organization", "PublicBody"), properties=_ORGANIZATION
    ),
    "LegalEntity": NodeMapping(labels=("Entity", "LegalEntity"), properties=_LEGAL_ENTITY),
    "Address": NodeMapping(
        labels=("Entity", "Address"),
        properties={
            "full": "full",
            "street": "street",
            "city": "city",
            "postalCode": "postal_code",
            "region": "region",
            "country": "country",
        },
        extra_names=("full",),
    ),
    "BankAccount": NodeMapping(
        labels=("Entity", "Account"),
        properties={
            "accountNumber": "account_number",
            "bankName": "bank_name",
            "currency": "currency",
            "accountType": "account_type",
            "nr.account_kind": "account_kind",
            "openingDate": "opening_date",
            "closingDate": "closing_date",
        },
    ),
    "Position": NodeMapping(labels=("Entity", "Position"), properties={"country": "country"}),
    "Sanction": NodeMapping(
        labels=("Sanction",),
        properties={
            "authority": "authority",
            "program": "program",
            "programId": "program_id",
            "listingDate": "listing_date",
            **_DATES,
            "reason": "reason",
            "country": "country",
            "provisions": "provisions",  # 1.2.0: every value, as published
        },
        empty_lists=("provisions",),
    ),
}

RELATIONSHIP_MAPPINGS: Final[dict[str, tuple[RelationshipMapping, ...]]] = {
    "Ownership": (
        RelationshipMapping(
            type="HOLDS_ACCOUNT",
            source_prop="owner",
            target_prop="asset",
            properties={"role": "role", **_DATES},
            condition="asset_is_account",
        ),
        RelationshipMapping(
            type="CONSOLIDATES",
            source_prop="owner",
            target_prop="asset",
            properties={"nr.consolidation": "level", **_DATES, "status": "status"},
            condition="consolidation",
        ),
        RelationshipMapping(
            type="OWNS",
            source_prop="owner",
            target_prop="asset",
            properties={
                "nr.share_pct_min": "share_pct_min",
                "nr.share_pct_max": "share_pct_max",
                **_BOUND_FLAGS,
                "percentage": "percentage_raw",
                "ownershipType": "ownership_type",
                "role": "role",
                "nr.natures_of_control": "natures_of_control",
                "nr.is_nominee": "is_nominee",  # 1.1.0
                **_DATES,
                "status": "status",
            },
            defaults={**_BOUND_DEFAULTS, "is_nominee": False},
        ),
    ),
    "Control": (
        RelationshipMapping(
            type="CONTROLS",
            source_prop="controller",
            target_prop="controlled",
            properties={
                "controlType": "control_type",
                "legalBasis": "legal_basis",
                "nr.natures_of_control": "natures_of_control",
                # 1.1.0: the voting-rights band, a control and never a share (not OWNS)
                "nr.share_pct_min": "share_pct_min",
                "nr.share_pct_max": "share_pct_max",
                **_BOUND_FLAGS,
                **_DATES,
            },
            defaults=_BOUND_DEFAULTS,
        ),
    ),
    "Directorship": (
        RelationshipMapping(
            type="DIRECTOR_OF",
            source_prop="director",
            target_prop="organization",
            properties={"role": "role", "nr.is_nominee": "is_nominee", **_DATES},
        ),
    ),
    "Payment": (
        RelationshipMapping(
            type="PAID",
            source_prop="payerAccount",
            target_prop="beneficiaryAccount",
            properties={
                "amount": "amount",
                "currency": "currency",
                "date": "ts",
                "nr.channel": "channel",
                "purpose": "purpose",
            },
        ),
    ),
    "Representation": (
        RelationshipMapping(
            type="REPRESENTS",
            source_prop="agent",
            target_prop="client",
            properties={"role": "role"},
        ),
    ),
    "Family": (
        RelationshipMapping(
            type="FAMILY_OF",
            source_prop="person",
            target_prop="relative",
            properties={"relationship": "relationship"},
        ),
    ),
    "Associate": (
        RelationshipMapping(
            type="ASSOCIATE_OF",
            source_prop="person",
            target_prop="associate",
            properties={"relationship": "relationship"},
        ),
    ),
    "Membership": (
        RelationshipMapping(
            type="MEMBER_OF",
            source_prop="member",
            target_prop="organization",
            properties={"role": "role", **_DATES},
        ),
    ),
    "Employment": (
        RelationshipMapping(
            type="EMPLOYED_BY",
            source_prop="employee",
            target_prop="employer",
            properties={"role": "role", **_DATES},
        ),
    ),
    "UnknownLink": (
        RelationshipMapping(
            type="LINKED_TO",
            source_prop="subject",
            target_prop="object",
            properties={"role": "role"},
        ),
    ),
    "Succession": (
        RelationshipMapping(
            type="SUCCEEDED_BY",
            source_prop="predecessor",
            target_prop="successor",
            properties={"date": "date"},
        ),
    ),
    "Occupancy": (
        RelationshipMapping(
            type="HOLDS_POSITION",
            source_prop="holder",
            target_prop="post",
            properties={"status": "status", **_DATES},
        ),
    ),
}

REFERENCE_MAPPINGS: Final = (
    ReferenceMapping(
        schema="LegalEntity",
        prop="addressEntity",
        type="HAS_ADDRESS",
        record_end="source",
        id_infix="addr",
        properties={"nr.address_roles": "role"},
        defaults={"role": "unknown"},
    ),
    ReferenceMapping(
        schema="Sanction",
        prop="entity",
        type="SUBJECT_OF",
        record_end="target",
        id_infix="sanction",
    ),
)

# The From and To columns of the relationship table: the label each end must carry.
RELATIONSHIP_ENDPOINTS: Final[dict[str, tuple[str, str]]] = {
    "OWNS": ("LegalEntity", "LegalEntity"),
    "CONTROLS": ("LegalEntity", "LegalEntity"),
    "CONSOLIDATES": ("Organization", "Organization"),
    "DIRECTOR_OF": ("LegalEntity", "Organization"),
    "HOLDS_ACCOUNT": ("LegalEntity", "Account"),
    "PAID": ("Account", "Account"),
    "HAS_ADDRESS": ("LegalEntity", "Address"),
    "REPRESENTS": ("LegalEntity", "LegalEntity"),
    "FAMILY_OF": ("Person", "Person"),
    "ASSOCIATE_OF": ("Person", "Person"),
    "MEMBER_OF": ("LegalEntity", "Organization"),
    "EMPLOYED_BY": ("Person", "Organization"),
    "LINKED_TO": ("Entity", "Entity"),
    "SUCCEEDED_BY": ("LegalEntity", "LegalEntity"),
    "HOLDS_POSITION": ("Person", "Position"),
    "SUBJECT_OF": ("Entity", "Sanction"),
    "RESOLVED_TO": ("SourceRecord", "Entity"),
    "POSSIBLY_SAME_AS": ("LegalEntity", "LegalEntity"),  # 1.1.0
    "FLAGS": ("Alert", "Entity"),
    "PRODUCED": ("DetectionRun", "Alert"),
}
RELATIONSHIP_TYPES: Final = tuple(RELATIONSHIP_ENDPOINTS)
# Written by entity resolution and detection, not built from records. Only POSSIBLY_SAME_AS
# carries an `id` (`<smaller node id>|psa|<larger node id>`, unique through migration 0002).
SUPPORT_RELATIONSHIPS: Final[dict[str, tuple[str, ...]]] = {
    "RESOLVED_TO": (
        "match_probability", "method", "resolver_version", "decided_at",
        "rule", "run_id", "features",  # 1.1.0
    ),
    "POSSIBLY_SAME_AS": (  # 1.1.0: an unconfirmed possible match, read as undirected
        "id", "match_probability", "match_weight", "method", "rule", "reasons", "features",
        "run_id", "resolver_version", "datasets", "synthetic",
    ),
    "FLAGS": ("role",),
    "PRODUCED": (),
}  # fmt: skip
POSSIBLY_SAME_AS_ID_INFIX: Final = "psa"

# Support nodes (not :Entity) and their properties; the first is the unique key.
SUPPORT_NODES: Final[dict[str, tuple[str, ...]]] = {
    # 1.1.0: one per member record of an entity merged from two or more records
    "SourceRecord": (
        "id", "dataset", "schema", "caption", "names", "topics", "canonical_id", "synthetic",
        "retrieved_at", "source_url", "run_id",
    ),
    "Alert": (
        "alert_id", "typology", "typology_version", "priority", "pattern_strength", "headline",
        "created_at", "run_id", "wording_class", "involves_real_entities", "synthetic_activity",
        "payload",
        "evidence_node_ids", "evidence_edge_ids",  # 1.2.0: C4 evidence ids, for I17
    ),
    "DetectionRun": (
        "run_id", "started_at", "finished_at", "typologies", "detectors", "alert_count", "status",
        "profile", "params_sha256", "summary", "window_start", "window_end",  # 1.2.0 (L19)
    ),
    "SchemaMigration": ("id", "checksum", "applied_at"),
}  # fmt: skip

# C2 properties no record sets in Phase 1: Phase 2 computes the normalised address key.
RESERVED_PROPERTIES: Final[dict[str, tuple[str, ...]]] = {"Address": ("address_key",)}

# 1.1.0: properties of every :Entity that the resolution-aware loader computes (M2.11), never
# mapped from a record property. `names_latin` is a search aid, never shown as a name.
ENTITY_RESOLUTION_PROPERTIES: Final = (
    "cluster_size", "resolution", "names_latin", "names_latin_text",
)  # fmt: skip

# 1.1.0: the values of the resolution properties.
EntityResolution = Literal["identity", "deterministic", "probabilistic", "human", "mixed"]
ResolvedToMethod = Literal["anchor", "deterministic", "probabilistic", "human"]
PossibleMatchMethod = Literal["probabilistic", "deterministic", "source_hint"]
ENTITY_RESOLUTIONS: Final = get_args(EntityResolution)
RESOLVED_TO_METHODS: Final = get_args(ResolvedToMethod)
POSSIBLY_SAME_AS_METHODS: Final = get_args(PossibleMatchMethod)
# RESOLVED_TO.match_probability is 1.0 for these methods.
CERTAIN_METHODS: Final = ("anchor", "deterministic", "human")

# 1.1.0: the properties of the resolution nodes and relationships (:SourceRecord, RESOLVED_TO,
# POSSIBLY_SAME_AS) that may be null (absent in Neo4j); every other property of theirs is
# always set. POSSIBLY_SAME_AS: no probability or weight for `deterministic` and `source_hint`
# matches, a `rule` only for `deterministic` ones. RESOLVED_TO: a `rule` only for D-rule links,
# `features` only for probabilistic ones. :SourceRecord: the two source fields only when the
# source provides them. Record-built nodes and relationships leave out absent values instead.
NULLABLE_PROPERTIES: Final[dict[str, tuple[str, ...]]] = {
    "SourceRecord": ("retrieved_at", "source_url"),
    "RESOLVED_TO": ("rule", "features"),
    "POSSIBLY_SAME_AS": ("match_probability", "match_weight", "rule"),
    # 1.2.0: no profile for a run without one; no parameters hash or window for a failed run,
    # a graph with no window to read, or a run written under 1.1.0.
    "DetectionRun": ("profile", "params_sha256", "window_start", "window_end"),
}

# 1.2.0 (L18): every record of an overlay load has an id with this prefix and this dataset.
OVERLAY_ID_PREFIX: Final = "syn-ov-"
OVERLAY_DATASET: Final = "nr_synthetic"
# 1.2.0 (I15): the only relationship between a synthetic and a non-synthetic node, from a
# non-synthetic :Organization to a synthetic :Account.
BRIDGE_RELATIONSHIP: Final = ("Organization", "HOLDS_ACCOUNT", "Account")

SYNTHETIC_LABEL: Final = "Synthetic"
# Flags come only from source data, never from detections. :Synthetic goes on every node with
# `synthetic = true` (:Entity and :Sanction, invariant I2); the topic flags on :Entity only.
TOPIC_FLAGS: Final = (
    TopicFlag("Sanctioned", "sanction", subtopics=False),  # not sanction.linked or .counter
    TopicFlag("PEP", "role.pep", subtopics=True),
    TopicFlag("RCA", "role.rca", subtopics=True),
)
FLAG_LABELS: Final = (SYNTHETIC_LABEL, *(flag.label for flag in TOPIC_FLAGS))

NODE_LABELS: Final = (
    *dict.fromkeys(label for mapping in NODE_MAPPINGS.values() for label in mapping.labels),
    *SUPPORT_NODES,
)
