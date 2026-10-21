"""Map ICIJ Offshore Leaks CSV rows to C1 records (PHASE-1.md M1.8c step 5).

Every node becomes one record `icij-node-<node_id>` (`make_id`), whatever file it came from, so
a relationship row maps without a lookup. Entities become `Company`; officers, intermediaries
and others `LegalEntity` (many officers are not people); addresses `Address`. Relationship rows
become `Ownership`, `Directorship`, `Representation` or `UnknownLink` records, or an
`addressEntity` reference with the role `registered`. `same_*` and `similar*` rows are
resolution hints for Phase 2: counted, never loaded.
"""

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from followthemoney import Schema, ValueEntity, model, registry

from neonradar_contracts.records import make_id

DATASET = "icij_offshore_leaks"
PREFIX = "icij"
NR_VERSION = "1.0"
ICIJ_DATE = "%d-%b-%Y"  # 23-MAR-2006
NODE_SCHEMA = {
    "nodes-entities.csv": "Company",
    "nodes-officers.csv": "LegalEntity",
    "nodes-intermediaries.csv": "LegalEntity",
    "nodes-others.csv": "LegalEntity",
    "nodes-addresses.csv": "Address",
}
# CSV column -> FtM property. A column is used only where the schema has the property.
NODE_COLUMNS = {
    "node_id": "icijId",
    "name": "name",
    "original_name": "alias",
    "former_name": "previousName",
    "jurisdiction_description": "jurisdiction",
    "jurisdiction": "jurisdiction",
    "company_type": "legalForm",
    "type": "legalForm",
    "address": "address",
    "status": "status",
    "ibcRUC": "registrationNumber",
    "country_codes": "country",
    "countries": "country",
    "note": "notes",
    "valid_until": "notes",
    "sourceID": "publisher",
}
DATE_COLUMNS = {
    "incorporation_date": "incorporationDate",
    "inactivation_date": "dissolutionDate",
    "struck_off_date": "dissolutionDate",
    "closed_date": "dissolutionDate",
}
ADDRESS_COLUMNS = {"address": "full", "name": "full", "country_codes": "country",
                   "countries": "country", "note": "notes", "valid_until": "notes",
                   "sourceID": "publisher"}  # fmt: skip
REL_COLUMNS = ("node_id_start", "node_id_end", "rel_type", "link", "status", "start_date",
               "end_date", "sourceID")  # fmt: skip
# officer_of `link` values, lower case: the first term found in the link decides the schema.
LINK_CLASSES: tuple[tuple[str, str], ...] = (
    ("shareholder", "Ownership"), ("beneficiary", "Ownership"), ("owner", "Ownership"),
    ("director", "Directorship"), ("secretary", "Directorship"), ("nominee", "Directorship"),
    ("signatory", "Directorship"), ("president", "Directorship"), ("treasurer", "Directorship"),
    ("chairman", "Directorship"), ("board member", "Directorship"), ("officer", "Directorship"),
    ("protector", "Directorship"), ("attorney", "Directorship"), ("manager", "Directorship"),
    ("representative", "Directorship"), ("liquidator", "Directorship"),
)  # fmt: skip
# registered_address `link` values name the kind of address; the first term found decides.
ADDRESS_ROLES = ("registered", "residential", "business", "service")
HINT_RE = re.compile(r"same|similar")
QUESTION_MARKS_RE = re.compile(r"^\?+\Z")
SKIP_NO_NAME = "nodes without a usable name"
SKIP_HINT = "resolution hints (same_*, similar*)"
SKIP_OUTSIDE = "relationships with an endpoint outside the slice"
SKIP_DUPLICATE = "duplicate rows"
SKIP_NODE_DUPLICATE = "node ids in more than one file (first kept)"


def node_id(native: str) -> str:
    return make_id(PREFIX, "node", native.strip())


def classify_link(rel_type: str, link: str) -> str | None:
    """The FtM schema for a relationship row, `address` for registered addresses, or None
    for a resolution hint. Unknown `officer_of` links and other types are `UnknownLink`."""
    rel, key = rel_type.strip().lower(), link.strip().lower()
    if HINT_RE.search(rel) or HINT_RE.search(key):
        return None
    if rel == "registered_address":
        return "address"
    if rel == "intermediary_of":
        return "Representation"
    if rel == "officer_of":
        return next((schema for term, schema in LINK_CLASSES if term in key), "UnknownLink")
    return "UnknownLink"


def clean(value: str | None) -> str:
    text = unicodedata.normalize("NFC", (value or "").strip())
    return "" if QUESTION_MARKS_RE.match(text) else text


@dataclass
class Mapper:
    """Collects the records of one slice. Add nodes first, then relationships."""

    entities: dict[str, ValueEntity] = field(default_factory=dict)
    nr: dict[str, dict[str, Any]] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    dates: dict[str, int] = field(default_factory=lambda: {"seen": 0, "kept": 0})
    date_misses: Counter[str] = field(default_factory=Counter)  # shapes, e.g. 99/99/9999

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def _new(self, schema: str, rid: str) -> ValueEntity:
        return ValueEntity(model[schema], {"id": rid, "datasets": [DATASET]})

    def _add_date(self, entity: ValueEntity, prop: str, raw: str | None) -> None:
        """DD-MON-YYYY, else ISO 8601. FtM's format parser accepts years it then rejects
        (`21-AUG-0200`), so every value is checked before it is added."""
        value = clean(raw)
        if not value or prop not in entity.schema.properties:
            return
        self.dates["seen"] += 1
        date = registry.date.clean(value, format=ICIJ_DATE) or registry.date.clean(value)
        if date and registry.date.validate(date):
            entity.add(prop, date)
            self.dates["kept"] += 1
        else:
            self.date_misses[re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", value))] += 1

    def add_node(self, file_name: str, row: dict[str, str]) -> bool:
        schema = NODE_SCHEMA[file_name]
        rid = node_id(row["node_id"])
        if rid in self.entities:
            self.skip(SKIP_NODE_DUPLICATE)
            return False
        entity = self._new(schema, rid)
        columns = ADDRESS_COLUMNS if schema == "Address" else NODE_COLUMNS
        for column, prop in columns.items():
            values = clean(row.get(column))
            if prop == "alias" and values in entity.get("name"):
                continue  # original_name repeats name in most rows
            if values and prop in entity.schema.properties:
                split = column in ("country_codes", "countries")
                entity.add(prop, [clean(v) for v in values.split(";")] if split else values)
        for column, prop in DATE_COLUMNS.items():
            self._add_date(entity, prop, row.get(column))
        if entity.schema.required and not entity.get("name"):
            self.skip(SKIP_NO_NAME)
            return False
        self.entities[rid] = entity
        self.nr[rid] = {"v": NR_VERSION, "source_ref": row["node_id"].strip()}
        return True

    def add_relationship(self, row: dict[str, str]) -> None:
        kind = classify_link(row["rel_type"], row["link"])
        if kind is None:
            self.skip(SKIP_HINT)
            return
        start = self.entities.get(node_id(row["node_id_start"]))
        end = self.entities.get(node_id(row["node_id_end"]))
        if start is None or end is None or start.id is None or end.id is None:
            self.skip(SKIP_OUTSIDE)
            return
        if kind == "address":
            if start.schema.is_a("LegalEntity") and end.schema.is_a("Address"):
                key = row["link"].lower()
                role = next((term for term in ADDRESS_ROLES if term in key), "unknown")
                start.add("addressEntity", end.id)
                self.nr[start.id].setdefault("address_roles", {})[end.id] = role
                return
            kind = "UnknownLink"
        kind = _fit(kind, start.schema, end.schema)
        parts = "|".join(row.get(column) or "" for column in REL_COLUMNS)
        digest = hashlib.sha1(parts.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
        rid = f"{PREFIX}-{kind.lower()}-{digest}"
        if rid in self.entities:
            self.skip(SKIP_DUPLICATE)
            return
        link = self._new(kind, rid)
        source, target = link.schema.edge_source, link.schema.edge_target
        if source is None or target is None:  # every kind above is an FtM edge
            raise ValueError(f"{kind} is not an edge schema")
        link.add(source, start.id)
        link.add(target, end.id)
        is_intermediary = kind == "Representation" and row["rel_type"] == "intermediary_of"
        link.add(
            "role", "intermediary" if is_intermediary else clean(row["link"]) or row["rel_type"]
        )
        link.add("status", clean(row.get("status")))
        link.add("publisher", clean(row.get("sourceID")))
        self._add_date(link, "startDate", row.get("start_date"))
        self._add_date(link, "endDate", row.get("end_date"))
        self.entities[rid] = link
        if kind == "Directorship":
            self.nr[rid] = {"v": NR_VERSION, "is_nominee": "nominee" in row["link"].lower()}

    def records(self) -> list[dict[str, Any]]:
        """C1 records in id order."""
        out = []
        for rid in sorted(self.entities):
            data = self.entities[rid].to_dict()
            out.append({**data, "nr": self.nr[rid]} if rid in self.nr else data)
        return out


def _fit(kind: str, start: Schema, end: Schema) -> str:
    """Fall back to UnknownLink when the endpoints do not fit the schema's FtM ranges."""
    if not (start.is_a("LegalEntity") and end.is_a("LegalEntity")):
        return "UnknownLink"
    if kind == "Directorship" and not end.is_a("Organization"):
        return "UnknownLink"
    return kind
