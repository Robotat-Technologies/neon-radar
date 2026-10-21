"""The Companies House spike: one company, its officers and its PSCs to C1 records (M1.8a).

Output goes through `neonradar_ingest.spikes.write_output` to the spike cache only
(`data/cache/spikes/companies_house/gb_companies_house-<yyyymmdd>-<number>.ftm.jsonl` plus
its manifest). Output of earlier days for the same company is removed first, so the cache
never holds two copies of one record. The summary has counts and field names only, never
names or other values from the register.
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neonradar_contracts.records import Source, manifest_path
from neonradar_ingest import spikes
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

SPIKE = "companies_house"
DEFAULT_MAX_PAGES = 5
COMPANY_NUMBER_RE = re.compile(r"^[A-Z0-9]{1,10}\Z")  # goes into a URL path and a file name


class CompanyNotFound(LookupError):
    """`/company/{number}` answered 404."""


@dataclass(frozen=True)
class SpikeResult:
    company_number: str
    records_path: Path
    records: int
    stats: MappingStats
    log: RequestLog
    requests: int
    seconds: float
    notes: list[str]

    def summary(self) -> list[str]:
        """Printable lines: counts and field names only."""
        stats, log = self.stats, self.log
        natural, appointments = stats.natural_appointments, stats.appointments
        surname_share = stats.surname_first_names / natural if natural else 0.0
        corporate_share = stats.corporate_appointments / appointments if appointments else 0.0
        pages = {path.rsplit("/", 1)[-1]: count for path, count in log.pages.items()}
        waits = ", ".join(f"{wait:.0f} s" for wait in log.rate_limit_waits) or "none"
        return [
            f"company {self.company_number}: {self.records} records",
            f"requests: {self.requests}; pages: {_counter(pages)};"
            f" status codes: {_counter({str(k): v for k, v in log.status_codes.items()})}",
            f"time: {self.seconds:.1f} s; at {REQUESTS_PER_SECOND:g} requests/s the company costs"
            f" {self.requests / REQUESTS_PER_SECOND:.1f} s",
            f"rate limit waits: {waits};"
            f" headers seen: {', '.join(sorted(log.rate_limit_headers)) or 'none'}",
            f"officer appointments: {appointments} ({stats.corporate_appointments} corporate,"
            f" {corporate_share:.0%}); natural names as 'SURNAME, Forenames':"
            f" {stats.surname_first_names} of {natural} ({surname_share:.0%})",
            "psc kinds: " + _counter(stats.psc_kinds),
            "natures of control: " + _counter(stats.natures),
            "skipped: " + _counter(stats.skipped),
            "values FtM could not parse: " + _counter(stats.dropped),
            "identity verification fields (not mapped): " + _counter(stats.identity_verification),
            "fields seen but not mapped: " + _counter(stats.unmapped_fields),
            *(f"note: {note}" for note in self.notes),
        ]


def _counter(counter: dict[str, int]) -> str:
    return ", ".join(f"{key} {count}" for key, count in sorted(counter.items())) or "none"


def run_spike(
    client: CompaniesHouseClient,
    company: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    root: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    clock: Callable[[], float] = time.monotonic,
) -> SpikeResult:
    """Fetch the profile, officers and PSCs of one company and write C1 records plus manifest.

    `root` is the spike cache (default `data/cache/spikes`); output goes to its
    `companies_house/` folder.
    """
    started, retrieved = clock(), now()
    number = normalise_company_number(company)
    if not COMPANY_NUMBER_RE.fullmatch(number):
        raise ValueError(f"company number {company!r} must be letters and digits only")
    profile = client.company(number)
    if profile is None:
        raise CompanyNotFound(f"company {number} not found (unknown, or dissolved before 2010)")
    mapper = Mapper()
    company_id = mapper.add_company(profile, number)
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
    _remove_earlier_output((root or spikes.SPIKE_ROOT) / SPIKE, number)
    records = mapper.records()
    path = spikes.write_output(
        records,
        SPIKE,
        dataset=DATASET,
        part=number,
        source=Source(
            urls=[
                f"{BASE_URL}/company/{number}",
                f"{BASE_URL}/company/{number}/officers",
                f"{BASE_URL}/company/{number}/persons-with-significant-control",
            ],
            retrieved_at=spikes.utc_timestamp(retrieved),
        ),
        skipped=dict(sorted(mapper.stats.skipped.items())),
        notes=notes,
        root=root,
    )
    return SpikeResult(
        company_number=number,
        records_path=path,
        records=len(records),
        stats=mapper.stats,
        log=client.log,
        requests=client.requests,
        seconds=clock() - started,
        notes=notes,
    )


def _remove_earlier_output(folder: Path, number: str) -> None:
    for old in folder.glob(f"{DATASET}-*-{number}.ftm.jsonl"):
        logger.info("replacing earlier spike output %s", old.name)
        manifest_path(old).unlink(missing_ok=True)
        old.unlink()
