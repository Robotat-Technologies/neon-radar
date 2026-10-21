"""The Companies House spike: one company, its officers and its PSCs to C1 records (M1.8a).

Output goes to the spike cache only (`data/cache/spikes/companies_house/`), as
`gb_companies_house-<yyyymmdd>-<number>.ftm.jsonl` plus its manifest. Earlier output for the
same company is replaced, so the cache never holds two copies of one record. The summary has
counts and field names only, never names or other values from the register.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neonradar_contracts.records import (
    Producer,
    Source,
    iter_records,
    manifest_path,
    write_manifest,
)
from neonradar_ingest import __version__
from neonradar_ingest.sources.companies_house.client import (
    BASE_URL,
    REQUESTS_PER_SECOND,
    CompaniesHouseClient,
    RequestLog,
)
from neonradar_ingest.sources.companies_house.mapping import (
    DATASET,
    Mapper,
    MappingStats,
    normalise_company_number,
)

logger = logging.getLogger(__name__)

PRODUCER = "neonradar_ingest.sources.companies_house"
DEFAULT_MAX_PAGES = 5


class CompanyNotFound(LookupError):
    """`/company/{number}` answered 404."""


@dataclass(frozen=True)
class SpikeResult:
    company_number: str
    records_path: Path
    manifest_path: Path
    by_schema: dict[str, int]
    stats: MappingStats
    log: RequestLog
    seconds: float
    notes: list[str]

    def summary(self) -> list[str]:
        """Printable lines: counts and field names only."""
        stats, log = self.stats, self.log
        natural = stats.natural_appointments
        surname_share = stats.surname_first_names / natural if natural else 0.0
        corporate_share = (
            stats.corporate_appointments / stats.appointments if stats.appointments else 0.0
        )
        lines = [
            f"company {self.company_number}: {sum(self.by_schema.values())} records",
            *(f"  {schema}: {count}" for schema, count in sorted(self.by_schema.items())),
            f"requests: {log.requests}; pages: "
            + ", ".join(f"{path.rsplit('/', 1)[-1]} {n}" for path, n in sorted(log.pages.items())),
            f"time: {self.seconds:.1f} s; at {REQUESTS_PER_SECOND:g} requests/s the company costs"
            f" {log.requests / REQUESTS_PER_SECOND:.1f} s",
            f"rate limit: {len(log.rate_limit_waits)} wait(s)"
            + (
                f" ({', '.join(f'{w:.0f} s' for w in log.rate_limit_waits)})"
                if log.rate_limit_waits
                else ""
            )
            + f"; headers seen: {', '.join(sorted(log.rate_limit_headers)) or 'none'}",
            f"officer appointments: {stats.appointments} ({stats.corporate_appointments} corporate,"
            f" {corporate_share:.0%}); natural names as 'SURNAME, Forenames':"
            f" {stats.surname_first_names} of {natural} ({surname_share:.0%})",
            "psc kinds: " + _counter(stats.psc_kinds),
            "natures of control: " + _counter(stats.natures),
            "skipped: " + _counter(stats.skipped),
            "values FtM could not parse: " + _counter(stats.dropped),
            "identity verification fields (not mapped): " + _counter(stats.identity_verification),
            "fields seen but not mapped: " + _counter(stats.unmapped_fields),
            *(f"note: {note}" for note in self.notes),
            f"records: {self.records_path}",
            f"manifest: {self.manifest_path}",
        ]
        return lines


def _counter(counter: dict[str, int]) -> str:
    return ", ".join(f"{key} {count}" for key, count in sorted(counter.items())) or "none"


def run_spike(
    client: CompaniesHouseClient,
    company: str,
    out_dir: Path,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    clock: Callable[[], float] = time.monotonic,
) -> SpikeResult:
    """Fetch the profile, officers and PSCs of one company and write C1 records plus manifest."""
    started, retrieved = clock(), now()
    number = normalise_company_number(company)
    profile = client.company(number)
    if profile is None:
        raise CompanyNotFound(f"company {number} not found (unknown, or dissolved before 2010)")
    mapper = Mapper()
    company_id = mapper.add_company(profile)
    notes: list[str] = []
    for label, pages, add in (
        ("officers", client.officers(number, max_pages), mapper.add_officer),
        ("persons with significant control", client.pscs(number, max_pages), mapper.add_psc),
    ):
        seen, total = 0, None
        for page in pages:
            items = page.get("items") or []
            seen += len(items)
            total = page.get("total_results", total)
            for item in items:
                if isinstance(item, dict):
                    add(item, company_id, number)
        if isinstance(total, int) and seen < total:
            notes.append(f"{label}: stopped after {max_pages} page(s), {seen} of {total} items")
    notes.append("identity_verification_details is counted, not mapped (Phase 2 decides)")
    records_path = _write_records(mapper, out_dir, number, retrieved)
    path = write_manifest(
        records_path,
        dataset=DATASET,
        producer=Producer(name=PRODUCER, version=__version__),
        source=Source(
            urls=[
                f"{BASE_URL}/company/{number}",
                f"{BASE_URL}/company/{number}/officers",
                f"{BASE_URL}/company/{number}/persons-with-significant-control",
            ],
            retrieved_at=retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
        skipped=dict(sorted(mapper.stats.skipped.items())),
        notes=notes,
    )
    by_schema: dict[str, int] = {}
    for record in iter_records(records_path):
        by_schema[record["schema"]] = by_schema.get(record["schema"], 0) + 1
    return SpikeResult(
        company_number=number,
        records_path=records_path,
        manifest_path=path,
        by_schema=by_schema,
        stats=mapper.stats,
        log=client.log,
        seconds=clock() - started,
        notes=notes,
    )


def _write_records(mapper: Mapper, out_dir: Path, number: str, retrieved: datetime) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{DATASET}-*-{number}.ftm.jsonl"):
        logger.info("replacing earlier spike output %s", old.name)
        manifest_path(old).unlink(missing_ok=True)
        old.unlink()
    path = out_dir / f"{DATASET}-{retrieved:%Y%m%d}-{number}.ftm.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in mapper.records():
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path
