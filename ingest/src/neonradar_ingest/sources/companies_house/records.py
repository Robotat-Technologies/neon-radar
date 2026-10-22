"""The `companies` step: `Company` and `Address` records for the slice (PHASE-2.md M2.3a 6, 7).

A second pass over the Free Company Data parts writes one `Company` per company in `slice.csv`
and one `Address` per distinct address key (`neonradar_keys.addresses`), shared by the three
Companies House sub-milestones. `nr.psc_statements` comes from the `statement` table of the
PSC index (M2.3b) when it exists.
"""

import hashlib
import json
import sqlite3
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from followthemoney import ValueEntity, model

from neonradar_contracts.records import Producer, Source, make_id, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.sources.companies_house import bulk
from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_keys.addresses import address_key_from_parts
from neonradar_keys.countries import country_code
from neonradar_keys.ids import has_ch_prefix
from neonradar_keys.postcodes import normalise_uk_postcode

PREFIX = "gbch"
NR_VERSION = "1.1"
RECORD_FILE = "companies.ftm.jsonl"
SOURCE_URL = "https://find-and-update.company-information.service.gov.uk/company/{}"
# Companies incorporated abroad and registered in the UK: FC overseas company, SF and NF
# overseas company registered in Scotland or Northern Ireland (before 1 October 2009; URI
# customer guide, note 2.6 source B16), OE overseas entity (community sources B25, B47).
OVERSEAS_PREFIXES = ("FC", "SF", "NF", "OE")


def address_id(key: str) -> str:
    return f"{PREFIX}-addr-{hashlib.sha1(key.encode(), usedforsecurity=False).hexdigest()[:20]}"


def jurisdiction(number: str, origin: str | None, stats: Counter[str]) -> str | None:
    """`gb`, or for an overseas prefix `country_code(CountryOfOrigin)` (counted when None)."""
    if number[:2] not in OVERSEAS_PREFIXES:
        stats["numbers_without_ch_prefix"] += not has_ch_prefix(number)
        return "gb"
    code = country_code(origin)
    stats["overseas_origin_unmapped"] += code is None
    return code


def read_statements(path: Path, numbers: set[str]) -> dict[str, list[str]] | None:
    """The `statement` table of `corporate_pscs.sqlite` for `numbers`, or None when absent."""
    if not path.is_file():
        return None
    connection = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True)
    try:
        values: dict[str, set[str]] = {}
        for number, value in connection.execute("SELECT company_number, value FROM statement"):
            if number in numbers and value:
                values.setdefault(number, set()).add(value)
    finally:
        connection.close()
    return {number: sorted(found) for number, found in values.items()}


class Writer:
    """Collects the records of the slice; addresses are shared by key."""

    def __init__(self, statements: dict[str, list[str]] | None) -> None:
        self.statements = statements or {}
        self.stats: Counter[str] = Counter()
        self.addresses: dict[str, dict[str, Any]] = {}
        self.office_keys: Counter[str] = Counter()

    def _entity(self, schema: str, rid: str, values: dict[str, Any]) -> ValueEntity:
        entity = ValueEntity(model[schema], {"id": rid, "datasets": [bulk.DATASET]})
        for prop, raw in values.items():
            for value in raw if isinstance(raw, list) else [raw]:
                if not value:
                    continue
                cleaned = entity.schema.properties[prop].type.clean(value)
                if cleaned is None:
                    self.stats[f"values_dropped.{schema.lower()}.{prop.lower()}"] += 1
                else:
                    entity.add(prop, cleaned, cleaned=True)
        return entity

    def address(self, row: bulk.Row) -> str | None:
        """The registered office's `Address` id (one record per key), else None (counted)."""
        part = {name: bulk.address_part(row[name]) for name in bulk.ADDRESS}
        raw_postcode = part["RegAddress.PostCode"]
        postcode = normalise_uk_postcode(raw_postcode) if raw_postcode else None
        parts = [part[name] for name in bulk.ADDRESS[:5]] + [postcode or raw_postcode]
        parts.append(part["RegAddress.Country"])
        key = address_key_from_parts(parts)
        if key is None:
            self.stats["companies_without_address_key"] += 1
            return None
        self.office_keys[key] += 1
        rid = address_id(key)
        if key not in self.addresses:
            country = country_code(part["RegAddress.Country"]) or "gb"
            values = {
                "full": ", ".join(p for p in parts if p),
                "postOfficeBox": part["RegAddress.POBox"],
                "street": part["RegAddress.AddressLine1"],
                "street2": part["RegAddress.AddressLine2"],
                "city": part["RegAddress.PostTown"],
                "region": part["RegAddress.County"],
                "postalCode": postcode or raw_postcode,
                "country": country,
            }
            entity = self._entity("Address", rid, values)
            self.addresses[key] = {**entity.to_dict(), "nr": {"v": NR_VERSION}}
        return rid

    def company(self, row: bulk.Row) -> dict[str, Any]:
        number = row["CompanyNumber"].strip()
        stats = self.stats
        sectors = [sic.split(" - ", 1)[0].strip() for sic in map(bulk.text, map(row.get, bulk.SIC))
                   if sic and " - " in sic]  # fmt: skip
        stats["sic_without_code"] += sum(
            1 for s in map(bulk.text, map(row.get, bulk.SIC)) if s and " - " not in s
        )
        values: dict[str, Any] = {
            "name": bulk.text(row["CompanyName"]),
            "registrationNumber": number,
            "legalForm": bulk.text(row["CompanyCategory"]),
            "status": bulk.text(row["CompanyStatus"]),
            "jurisdiction": jurisdiction(number, bulk.text(row["CountryOfOrigin"]), stats),
            "incorporationDate": bulk.iso_date(row["IncorporationDate"], stats, "incorporation"),
            "dissolutionDate": bulk.iso_date(row["DissolutionDate"], stats, "dissolution"),
            "sector": sectors,
            "previousName": [bulk.text(row[name]) for name in bulk.PREVIOUS],
            "sourceUrl": SOURCE_URL.format(number),
        }
        rid = make_id(PREFIX, "co", number)
        entity = self._entity("Company", rid, values)
        nr: dict[str, Any] = {"v": NR_VERSION, "source_ref": number}
        if category := bulk.text(row["Accounts.AccountCategory"]):
            nr["accounts_category"] = category
        if address := self.address(row):
            entity.add("addressEntity", address)
            nr["address_roles"] = {address: "registered"}
        if statements := self.statements.get(number):
            nr["psc_statements"] = statements
        return {**entity.to_dict(), "nr": nr}


def write_companies(
    parts: Sequence[Path],
    slice_csv: Path,
    psc_index: Path,
    out_dir: Path,
    *,
    version: str,
    urls: Sequence[str],
) -> tuple[dict[str, Any], str]:
    """The `companies` step: records and manifest in `out_dir`; counts and `statements`."""
    numbers = {number for number, _, _ in slices.read(slice_csv)}
    statements = read_statements(psc_index, numbers)
    writer, read_stats = Writer(statements), Counter[str]()
    written: set[str] = set()
    path = out_dir / RECORD_FILE
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for part in parts:
            for row in bulk.iter_part(part, read_stats):
                number = row["CompanyNumber"].strip()
                if number not in numbers or number in written:
                    writer.stats["duplicate_numbers"] += number in written
                    continue
                if bulk.text(row["CompanyName"]) is None:
                    writer.stats["rows_without_name"] += 1  # a Company needs a name (R3)
                    continue
                written.add(number)
                handle.write(json.dumps(writer.company(row), ensure_ascii=False) + "\n")
        for key in sorted(writer.addresses):
            handle.write(json.dumps(writer.addresses[key], ensure_ascii=False) + "\n")
    producer = Producer(name="neonradar_ingest.sources.companies_house", version=__version__)
    write_manifest(path, dataset=bulk.DATASET, producer=producer,
                   source=Source(urls=list(urls), source_version=version))  # fmt: skip
    top10 = sum(count for _, count in writer.office_keys.most_common(10))
    counts: dict[str, Any] = {
        "records": {"company": len(written), "address": len(writer.addresses)},
        "slice_companies_not_in_file": len(numbers - written),
        "companies_with_statements": sum(1 for n in written if n in (statements or {})),
        "top10_address_share": round(top10 / len(written), 4) if written else None,
        **dict(sorted((read_stats | writer.stats).items())),
    }
    return counts, "absent" if statements is None else "present"
