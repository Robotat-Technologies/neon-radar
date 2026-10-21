"""GLEIF LEI records to C1 (PHASE-1.md M1.8b step 5; contracts/C1-record.md).

- Each LEI record becomes a `Company` `gleif-lei-<LEI>` with `leiCode`, `name` (legal name),
  `alias` (other names and preferred transliterations), `previousName`, `jurisdiction`,
  `registrationNumber` (`registeredAs`) and `status`; its legal and headquarters addresses
  become `Address` records with the roles `registered` and `business`.
- A reported parent becomes an `Ownership` (owner the parent, asset the child) with
  `nr.consolidation` `direct` or `ultimate`: accounting consolidation, which C2 loads as
  CONSOLIDATES, never OWNS. Reporting exceptions go to the manifest notes (category and
  reason only; the free-text reference is left out).
- GLEIF's automatic transliterations are not written (R10: no machine transliterations).
"""

from collections import Counter
from typing import Any

from neonradar_contracts.records import make_id
from neonradar_ingest.sources.gleif.client import CH_AUTHORITIES, SpikeResult, expected_authority
from neonradar_ingest.spikes import entity_record

DATASET = "gleif_lei"
PREFIX = "gleif"
NR_VERSION = "1.0"
# GLEIF name types (LEI-CDF 3.1) to FtM properties; AUTO_ASCII_TRANSLITERATED_LEGAL_NAME is
# a machine transliteration and is skipped.
NAME_PROPERTY = {
    "ALTERNATIVE_LANGUAGE_LEGAL_NAME": "alias",
    "TRADING_OR_OPERATING_NAME": "alias",
    "PREFERRED_ASCII_TRANSLITERATED_LEGAL_NAME": "alias",
    "PREVIOUS_LEGAL_NAME": "previousName",
}
ADDRESSES = (("legalAddress", "legal", "registered"), ("headquartersAddress", "hq", "business"))


def entity_id(lei: str) -> str:
    return make_id(PREFIX, "lei", lei)


def address_id(lei: str, kind: str) -> str:
    return make_id(PREFIX, "addr", f"{lei}-{kind}")


def ownership_id(child: str, parent: str, level: str) -> str:
    """`gleif-ownership-<20 hex>`: make_id hashes the `|`-joined key (PHASE-1.md 4.4 edges)."""
    return make_id(PREFIX, "ownership", f"{child}|{parent}|{level}")


def _day(value: str | None) -> str | None:
    """`2023-06-23T00:00:00Z` to `2023-06-23` (FtM would keep a minute-precision time)."""
    return value[:10] if value else None


def address_record(lei: str, kind: str, address: dict[str, Any] | None) -> dict[str, Any] | None:
    """One GLEIF address as an `Address`, or None when it has no lines, city or postcode."""
    if not address:
        return None
    lines = [line for line in address.get("addressLines") or [] if line]
    number = address.get("addressNumber")
    if number:  # GLEIF may give the house number apart from the first line
        lines = [f"{number} {lines[0]}", *lines[1:]] if lines else [number]
    street = ", ".join(lines)
    city: str | None = address.get("city")
    postcode: str | None = address.get("postalCode")
    full = ", ".join(part for part in (street, city, postcode, address.get("country")) if part)
    if not (street or city or postcode):
        return None
    properties: dict[str, list[str | None]] = {
        "full": [full],
        "street": [street],
        "city": [city],
        "postalCode": [postcode],
        "region": [address.get("region")],
        "country": [address.get("country")],
    }
    return entity_record("Address", address_id(lei, kind), DATASET, properties)


def company_records(data: dict[str, Any], skipped_names: Counter[str]) -> list[dict[str, Any]]:
    """The `Company` and its `Address` records for one LEI record (`data` object)."""
    attributes = data["attributes"]
    entity, lei = attributes["entity"], attributes["lei"]
    addresses: list[dict[str, Any]] = []
    roles: dict[str, str] = {}
    for key, kind, role in ADDRESSES:
        address = address_record(lei, kind, entity.get(key))
        if address is not None:
            addresses.append(address)
            roles[address["id"]] = role
    names: dict[str, list[str | None]] = {"alias": [], "previousName": []}
    for other in [
        *(entity.get("otherNames") or []),
        *(entity.get("transliteratedOtherNames") or []),
    ]:
        prop = NAME_PROPERTY.get(other.get("type") or "")
        if prop is None:
            skipped_names[other.get("type") or "no type"] += 1
        else:
            names[prop].append(other.get("name"))
    properties = {
        "name": [(entity.get("legalName") or {}).get("name")],
        "leiCode": [lei],
        **names,
        "jurisdiction": [entity.get("jurisdiction")],
        "registrationNumber": [entity.get("registeredAs")],
        "status": [entity.get("status")],
        "addressEntity": [address["id"] for address in addresses],
    }
    company = entity_record("Company", entity_id(lei), DATASET, properties)
    company["nr"] = {"v": NR_VERSION, "source_ref": lei}
    if roles:
        company["nr"]["address_roles"] = roles
    return [company, *addresses]


def ownership_record(
    child: str, parent: str, level: str, relationship: dict[str, Any] | None
) -> dict[str, Any]:
    """The consolidation link as an `Ownership` with `nr.consolidation` (`direct`, `ultimate`)."""
    detail = (relationship or {}).get("attributes", {}).get("relationship", {})
    periods: list[dict[str, Any]] = detail.get("periods") or []
    period = next((p for p in periods if p.get("type") == "RELATIONSHIP_PERIOD"), {})
    properties = {
        "owner": [entity_id(parent)],
        "asset": [entity_id(child)],
        "role": [detail.get("type")],
        "status": [detail.get("status")],
        "startDate": [_day(period.get("startDate"))],
        "endDate": [_day(period.get("endDate"))],
    }
    record = entity_record("Ownership", ownership_id(child, parent, level), DATASET, properties)
    record["nr"] = {"v": NR_VERSION, "consolidation": level}
    if relationship is not None:
        record["nr"]["source_ref"] = relationship["id"]
    return record


def build_records(result: SpikeResult) -> tuple[list[dict[str, Any]], list[str]]:
    """C1 records (each id once) and the manifest notes for one spike run."""
    records: dict[str, dict[str, Any]] = {}
    skipped_names: Counter[str] = Counter()
    notes: list[str] = []

    def add(new: list[dict[str, Any]]) -> None:
        for record in new:
            records.setdefault(record["id"], record)

    add(company_records(result.record, skipped_names))
    for link in result.links:
        where = f"{link.child} {link.level} parent"
        if link.parent is not None:
            add(company_records(link.parent, skipped_names))
            add([ownership_record(link.child, link.parent["id"], link.level, link.relationship)])
        elif link.exception is not None:
            exception = link.exception
            notes.append(
                f"{where}: reporting exception {exception.get('category')},"
                f" reason {exception.get('reason')}"
            )
        elif link.reported:
            notes.append(f"{where}: reported with an LEI, not fetched (beyond the spike's depth)")
        else:
            notes.append(f"{where}: neither a parent nor a reporting exception")
    for data in result.join:
        add(company_records(data, skipped_names))
    notes.append(f"{result.record['id']} direct children: {result.children}")
    if result.join_number is None:
        notes.append("join: skipped (no Companies House number)")
    else:
        found = ", ".join(data["id"] for data in result.join) or "none"
        notes.append(
            f"join: registeredAs {result.join_number} at {'/'.join(CH_AUTHORITIES)}: {found}"
        )
    for name_type, count in sorted(skipped_names.items()):
        notes.append(f"names not written: {count} {name_type}")
    return list(records.values()), notes


def summary_lines(result: SpikeResult) -> list[str]:
    """What the command prints: the record, each parent or exception with its reason, the join."""
    attributes = result.record["attributes"]
    entity, registration = attributes["entity"], attributes["registration"]
    registered_at = (entity.get("registeredAt") or {}).get("id")
    lines = [
        f"record {attributes['lei']}: {(entity.get('legalName') or {}).get('name')}",
        f"  registeredAs {entity.get('registeredAs')} at {registered_at};"
        f" jurisdiction {entity.get('jurisdiction')}; entity {entity.get('status')};"
        f" registration {registration.get('status')}",
    ]
    for link in result.links:
        prefix = f"  {link.child} {link.level} parent:"
        if link.parent is not None:
            parent = link.parent["attributes"]
            detail = (link.relationship or {}).get("attributes", {}).get("relationship", {})
            lines.append(
                f"{prefix} {parent['lei']} {(parent['entity'].get('legalName') or {}).get('name')}"
                f" ({detail.get('type')}, {detail.get('status')})"
            )
        elif link.exception is not None:
            lines.append(f"{prefix} reporting exception, reason {link.exception.get('reason')}")
        elif link.reported:
            lines.append(f"{prefix} reported with an LEI (not fetched)")
        else:
            lines.append(f"{prefix} none")
    lines.append(f"  direct children: {result.children}")
    if result.join_number is None:
        lines.append("join: skipped (no Companies House number)")
    else:
        found = [
            f"{data['id']} at {(data['attributes']['entity'].get('registeredAt') or {}).get('id')}"
            for data in result.join
        ]
        matched = attributes["lei"] in {data["id"] for data in result.join}
        lines.append(
            f"join: Companies House {result.join_number} -> {', '.join(found) or 'no LEI'};"
            f" spike record matched: {'yes' if matched else 'no'};"
            f" expected authority {expected_authority(result.join_number)}"
        )
    return lines
