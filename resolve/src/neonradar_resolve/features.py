"""Members and feature tables (PHASE-2.md 7.1.1 and 7.1.5, M2.10a deliverable 4).

`members(corpus)` gives one `cluster.Member` per resolvable record; `feature_tables(corpus,
members)` gives the person and organisation tables of 7.1.5, typed by `feature_schema.py`,
with every empty list written as NULL (Splink's null levels test `IS NULL`, and an empty
DuckDB list is not NULL). Names are keyed through `neonradar_keys`, from `name`, `alias` and
`previousName`, never from `weakAlias`; empty keys are dropped (`docs/er/keys.md`).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from neonradar_keys.addresses import address_key, address_key_from_parts
from neonradar_keys.companies_house import ch_same_as_key as _ch_same_as_key
from neonradar_keys.countries import country_code
from neonradar_keys.ids import has_ch_prefix, is_valid_lei, uk_company_number, un_reference
from neonradar_keys.names import OrgKey, PersonKey
from neonradar_keys.names import org_key as _org_key
from neonradar_keys.names import person_key as _person_key
from neonradar_keys.postcodes import find_uk_postcode, normalise_uk_postcode
from neonradar_resolve import policy
from neonradar_resolve.cluster import Member
from neonradar_resolve.feature_schema import ORG_SCHEMA, PERSON_SCHEMA, RARE_NAME_MAX
from neonradar_resolve.records import Corpus, Record

NAME_PROPS = ("name", "alias", "previousName")  # never weakAlias (M2.6)
LIST_CAP = 50  # name tokens, symbols and skeletons kept per record (7.1.5)
ISO_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")
UK_REGISTERS = ("gbch-co-",)  # a Companies House number whatever the company's jurisdiction
UK_PARTY_PREFIX = "uksl-g"  # UK designations grouped by OFSI Group ID (M2.6a): whole parties
SYNTHETIC_DATASET = "nr_synthetic"
FEATURES_FILE = "features.duckdb"


# The keys are pure functions; members and feature rows key the same names, so cache them.
@lru_cache(maxsize=200_000)
def person_key(name: str, given: str | None = None, family: str | None = None) -> PersonKey:
    return _person_key(name, given, family)


@lru_cache(maxsize=200_000)
def org_key(name: str) -> OrgKey:
    return _org_key(name)


@lru_cache(maxsize=200_000)
def ch_same_as_key(name: str) -> str:
    return _ch_same_as_key(name)


def _is_gb(record: Record) -> bool:
    return any(
        j.lower() == "gb" or j.lower().startswith("gb-") for j in record.values("jurisdiction")
    )


def company_numbers(record: Record) -> frozenset[str]:
    """The record's own UK company numbers (rule D1 normalisation, 7.1.2)."""
    if record.entity_class not in ("org", "legal_entity"):
        return frozenset()
    gleif = record.id.startswith("gleif-")
    if not (record.id.startswith(UK_REGISTERS) or _is_gb(record)):
        return frozenset()
    out = set()
    for raw in record.values("registrationNumber"):
        text = raw.strip().upper()
        if gleif and not (len(text) == 8 and has_ch_prefix(text)):
            continue  # only the three UK registration authorities write this form (M2.4)
        number = uk_company_number(raw, synthetic=record.synthetic)
        if number:
            out.add(number)
    return frozenset(out)


def leis(record: Record) -> frozenset[str]:
    return frozenset(v.strip().upper() for v in record.values("leiCode") if is_valid_lei(v))


def birth_dates(record: Record) -> frozenset[str]:
    """`birthDate` values as ISO prefixes: 1979, 1979-08 or 1979-08-23."""
    out = set()
    for value in record.values("birthDate"):
        match = ISO_DATE.match(value.strip())
        if match:
            out.add("-".join(part for part in match.groups() if part))
    return frozenset(out)


def _person_keys(record: Record) -> list[PersonKey]:
    return [person_key(v) for v in record.values(*NAME_PROPS)]


def name_keys(record: Record) -> frozenset[str]:
    """Person keys for people, org keys for organisations, both for legal entities."""
    names = record.values(*NAME_PROPS)
    keys: set[str] = set()
    if record.entity_class in ("person", "legal_entity"):
        keys.update(person_key(v).key for v in names)
    if record.entity_class in ("org", "legal_entity"):
        keys.update(org_key(v).key for v in names)
    return frozenset(k for k in keys if k)


def un_references(corpus: Corpus, record: Record) -> frozenset[str]:
    refs = (un_reference(s.unsc_id) for s in corpus.sanctions.get(record.id, ()))
    return frozenset(r for r in refs if r)


def list_source(corpus: Corpus, record: Record, kind: str) -> str | None:
    """The list a listed record comes from: its dataset, or `nr_synthetic:<authority>`."""
    if kind != "list":
        return None
    if record.dataset_kind == "list":
        return record.dataset
    authorities = sorted(s.authority for s in corpus.sanctions.get(record.id, ()) if s.authority)
    return f"{SYNTHETIC_DATASET}:{authorities[0]}" if authorities else record.dataset


def list_party(record: Record, source: str | None) -> str | None:
    """The list source when the record is a whole party of its list (7.1.1, X6)."""
    if source == "gb_fcdo_sanctions" and not record.id.startswith(UK_PARTY_PREFIX):
        return None
    return source


def member(corpus: Corpus, record: Record) -> Member:
    kind = policy.record_kind(record.dataset_kind, record.nr)
    source = list_source(corpus, record, kind)
    return Member(
        record_id=record.id,
        dataset=record.dataset,
        kind=kind,
        priority=record.priority,
        schema=record.schema,
        entity_class=record.entity_class,
        synthetic=record.synthetic,
        flag_topics=policy.flag_topics(record.values("topics")),
        list_source=source,
        list_party=list_party(record, source),
        company_numbers=company_numbers(record),
        leis=leis(record),
        birth_dates=birth_dates(record) if record.entity_class == "person" else frozenset(),
        name_keys=name_keys(record),
    )


def members(corpus: Corpus) -> dict[str, Member]:
    return {rid: member(corpus, corpus.records[rid]) for rid in sorted(corpus.records)}


# Feature tables (7.1.5) ---------------------------------------------------------------------


def _list(values: Iterable[Any], cap: int | None = None) -> list[Any] | None:
    """Sorted unique values, at most `cap`; NULL (None) instead of an empty list."""
    out = sorted(set(values))
    if cap is not None:
        out = out[:cap]
    return out or None


def _address_postcode(record: Record) -> str | None:
    for value in record.values("postalCode"):
        found = normalise_uk_postcode(value)
        if found:
            return found
    for value in record.values("full"):
        found, _ = find_uk_postcode(value)
        if found:
            return found
    return None


def postcode(corpus: Corpus, record: Record) -> str | None:
    """The first UK postcode: `addressEntity` records first, then `address` text."""
    for rid in record.values("addressEntity"):
        linked = corpus.records.get(rid)
        if linked is not None and linked.entity_class == "address":
            found = _address_postcode(linked)
            if found:
                return found
    for text in record.values("address"):
        found, _ = find_uk_postcode(text)
        if found:
            return found
    return None


def countries(record: Record) -> list[str] | None:
    codes = (country_code(v) for v in record.values("nationality", "citizenship", "country"))
    return _list(c.lower() for c in codes if c)


def _years(dates: Iterable[str]) -> list[int]:
    return sorted({int(d[:4]) for d in dates})


def linked_orgs(corpus: Corpus, record: Record, by_id: Mapping[str, Member]) -> list[str] | None:
    """`uk:<company number>` of each linked organisation that has one, else its record id."""
    out = []
    for rid in corpus.linked.get(record.id, ()):
        other = by_id.get(rid)
        if other is None or other.entity_class not in ("org", "legal_entity"):
            continue
        out.append(f"uk:{min(other.company_numbers)}" if other.company_numbers else rid)
    return _list(out)


def identifiers(record: Record) -> list[str] | None:
    def clean(value: str) -> str:
        return re.sub(r"\s+", "", value).upper()

    found = [f"passport:{clean(v)}" for v in record.values("passportNumber") if clean(v)]
    found += [f"id:{clean(v)}" for v in record.values("idNumber") if clean(v)]
    return _list(found)


def person_row(corpus: Corpus, record: Record, by_id: Mapping[str, Member]) -> dict[str, Any]:
    given, family = record.first("firstName"), record.first("lastName")
    name = record.first("name") or " ".join(v for v in (given, family) if v)
    first = person_key(name, given, family) if name else None
    keys = _person_keys(record)
    dates = birth_dates(record)
    ym = sorted({d[:7] for d in dates if len(d) >= 7})
    years = _years(dates)
    forename = first.given[0] if first and first.given else None
    return {
        "unique_id": record.id,
        "synthetic": record.synthetic,
        "name_key": (first.key or None) if first else None,
        "name_key_rare": None,  # filled once the table is complete
        "forename": forename,
        "surname": first.family[0] if first and first.family else None,
        "initial": forename[0] if forename else None,
        "name_tokens": _list((t for k in keys for t in k.tokens), LIST_CAP),
        "name_symbols": _list((s for k in keys for s in k.symbols), LIST_CAP),
        "skeletons": _list((s for k in keys for s in k.skeletons), LIST_CAP),
        "birth_full": _list(d for d in dates if len(d) == 10),
        "birth_ym": ym or None,
        "birth_years": years or None,
        "birth_year_min": years[0] if years else None,
        "birth_ym_min": ym[0] if ym else None,
        "countries": countries(record),
        "postcode": postcode(corpus, record),
        "linked_orgs": linked_orgs(corpus, record, by_id),
        "identifiers": identifiers(record),
    }


def _jurisdiction(record: Record) -> str | None:
    value = record.first("jurisdiction")
    if not value:
        return None
    value = value.strip().lower()
    return "gb" if value.startswith("gb-") else value or None


def registration_numbers(record: Record, mem: Member) -> list[str] | None:
    found = [f"uk:{n}" for n in mem.company_numbers] + [f"lei:{x}" for x in mem.leis]
    jurisdiction = _jurisdiction(record) or ""
    for raw in record.values("registrationNumber"):
        if uk_company_number(raw, synthetic=record.synthetic) in mem.company_numbers:
            continue
        value = re.sub(r"[\s.\-]", "", raw).upper()
        if value:
            found.append(f"reg:{jurisdiction}:{value}")
    return _list(found)


def org_row(corpus: Corpus, record: Record, mem: Member) -> dict[str, Any]:
    name = record.first("name")
    first = org_key(name) if name else None
    key = first.key if first and first.key else None
    year = next(
        (int(m.group(1)) for v in record.values("incorporationDate") if (m := ISO_DATE.match(v))),
        None,
    )
    same_as = ch_same_as_key(name) if name else ""
    return {
        "unique_id": record.id,
        "synthetic": record.synthetic,
        "name_key": key,
        "name_key_rare": None,
        "name_prefix": key[:4] if key else None,
        "aliases": _list(k for v in record.values(*NAME_PROPS) if (k := org_key(v).key)),
        "ch_same_as": same_as or None,
        "name_tokens": _list(key.split()) if key else None,
        "jurisdiction": _jurisdiction(record),
        "registration_numbers": registration_numbers(record, mem),
        "incorporation_year": year,
        "postcode": postcode(corpus, record),
        "legal_forms": _list(first.legal_forms) if first else None,
    }


def _fill_rare(rows: list[dict[str, Any]]) -> None:
    counts = Counter(r["name_key"] for r in rows if r["name_key"])
    for row in rows:
        key = row["name_key"]
        row["name_key_rare"] = key if key and counts[key] <= RARE_NAME_MAX else None


def feature_tables(corpus: Corpus, by_id: Mapping[str, Member]) -> tuple[pa.Table, pa.Table]:
    """The person and organisation feature tables; `legal_entity` records are in both."""
    people, orgs = [], []
    for rid in sorted(corpus.records):
        record = corpus.records[rid]
        if record.entity_class in ("person", "legal_entity"):
            people.append(person_row(corpus, record, by_id))
        if record.entity_class in ("org", "legal_entity"):
            orgs.append(org_row(corpus, record, by_id[rid]))
    _fill_rare(people)
    _fill_rare(orgs)
    return (
        pa.Table.from_pylist(people, schema=PERSON_SCHEMA),
        pa.Table.from_pylist(orgs, schema=ORG_SCHEMA),
    )


def write_features(
    path: Path, person: pa.Table, org: pa.Table, temp_directory: Path | None = None
) -> None:
    """`features.duckdb` with the tables `person_features` and `org_features`."""
    config: dict[str, str | bool | int | float | list[str]] = {"threads": 1}
    if temp_directory is not None:
        config["temp_directory"] = str(temp_directory)
    path.unlink(missing_ok=True)
    with duckdb.connect(str(path), config=config) as con:
        for name, table in (("person_features", person), ("org_features", org)):
            con.register("incoming", table)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM incoming")  # noqa: S608
            con.unregister("incoming")


def address_keys(corpus: Corpus) -> dict[str, str]:
    """Rule D6: each Address record's key (from `full`, else from its parts), when it has one."""
    out = {}
    for rid, record in corpus.records.items():
        if record.entity_class != "address":
            continue
        full = record.first("full")
        if full:
            key = address_key(full)
        else:
            parts = record.values("street", "street2", "city", "region", "state", "postalCode")
            key = address_key_from_parts([*parts, record.first("country")])
        if key:
            out[rid] = key
    return out
