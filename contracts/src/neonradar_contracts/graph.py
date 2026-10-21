"""C2 graph schema v1.0.0: how C1 records become Neo4j nodes and relationships, as data (5.2).

The tables of docs/build/PHASE-1.md 5.2 and contracts/C2-graph-schema.md, written as data so
that the loader, the detectors, the API and the contract tests read one source. The code that
applies the mapping is `neonradar_graph.mapping`; the schema itself (constraints and indexes) is
`graph/schema/migrations/`. Property names on the left of a mapping are FtM properties, or
`nr.<key>` for the C1 `nr` extension; on the right are C2 graph properties.
"""

from dataclasses import dataclass, field
from typing import Final, Literal

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


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipMapping:
    """An FtM interval schema whose records become relationships.

    A schema with several mappings (Ownership) takes the first whose `condition` holds; None
    always holds. `asset_is_account`: the target record in the load is a BankAccount.
    `consolidation`: the record sets `nr.consolidation`.
    """

    type: str
    source_prop: str
    target_prop: str
    properties: dict[str, str]
    condition: Condition | None = None


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
_DATES = {"startDate": "start_date", "endDate": "end_date"}

NODE_MAPPINGS: Final[dict[str, NodeMapping]] = {
    "Person": NodeMapping(
        labels=("Entity", "LegalEntity", "Person"),
        properties={"birthDate": "birth_date", "nationality": "nationalities", "gender": "gender"},
    ),
    "Company": NodeMapping(
        labels=("Entity", "LegalEntity", "Organization", "Company"), properties=_ORGANIZATION
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
        },
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
                "percentage": "percentage_raw",
                "ownershipType": "ownership_type",
                "role": "role",
                "nr.natures_of_control": "natures_of_control",
                **_DATES,
                "status": "status",
            },
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
                **_DATES,
            },
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
    "FLAGS": ("Alert", "Entity"),
    "PRODUCED": ("DetectionRun", "Alert"),
}
RELATIONSHIP_TYPES: Final = tuple(RELATIONSHIP_ENDPOINTS)
# Written by entity resolution and detection, not built from records; they carry no `id`.
SUPPORT_RELATIONSHIPS: Final[dict[str, tuple[str, ...]]] = {
    "RESOLVED_TO": ("match_probability", "method", "resolver_version", "decided_at"),
    "FLAGS": ("role",),
    "PRODUCED": (),
}

# Support nodes (not :Entity) and their properties; the first is the unique key.
SUPPORT_NODES: Final[dict[str, tuple[str, ...]]] = {
    "SourceRecord": ("id",),  # the rest is defined in Phase 2
    "Alert": (
        "alert_id", "typology", "typology_version", "priority", "pattern_strength", "headline",
        "created_at", "run_id", "wording_class", "involves_real_entities", "synthetic_activity",
        "payload",
    ),
    "DetectionRun": (
        "run_id", "started_at", "finished_at", "typologies", "detectors", "alert_count", "status",
    ),
    "SchemaMigration": ("id", "checksum", "applied_at"),
}  # fmt: skip

# C2 properties no record sets in Phase 1: Phase 2 computes the normalised address key.
RESERVED_PROPERTIES: Final[dict[str, tuple[str, ...]]] = {"Address": ("address_key",)}

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
