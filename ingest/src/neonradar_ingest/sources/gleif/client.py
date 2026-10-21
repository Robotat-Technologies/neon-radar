"""GLEIF API calls for the spike (PHASE-1.md M1.8b): one LEI record, its parents, the count of
its direct children, and the deterministic join to a Companies House number.

API `https://api.gleif.org/api/v1`: no key, 60 requests per minute (the limiter sends one per
second), `page[size]` at most 200, and page numbers only up to 10,000 results (cursor paging
beyond; docs/data/spikes/gleif.md).
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from neonradar_ingest.http import HttpClient, RateLimiter

API = "https://api.gleif.org/api/v1/"
CH_AUTHORITIES = ("RA000585", "RA000586", "RA000587")  # Companies House: E&W, NI, Scotland
LEVELS = ("direct", "ultimate")
LEI_RE = re.compile(r"[A-Z0-9]{18}[0-9]{2}\Z")
# GLEIF warned of interruptions from 19 October to 4 November 2026: a longer wait fails fast.
MAX_WAIT_S = 120.0
COVERAGE = {  # the GB coverage queries of the research note (sources-ch-gleif.md B4)
    "jurisdiction GB": {"filter[entity.jurisdiction]": "GB"},
    "jurisdiction GB, active and issued": {
        "filter[entity.jurisdiction]": "GB",
        "filter[entity.status]": "ACTIVE",
        "filter[registration.status]": "ISSUED",
    },
    "legal address country GB": {"filter[entity.legalAddress.country]": "GB"},
    "RA000585 (England and Wales)": {"filter[entity.registeredAt]": "RA000585"},
    "RA000587 (Scotland)": {"filter[entity.registeredAt]": "RA000587"},
    "RA000586 (Northern Ireland)": {"filter[entity.registeredAt]": "RA000586"},
    "all three CH codes, active and issued": {
        "filter[entity.registeredAt]": ",".join(CH_AUTHORITIES),
        "filter[entity.status]": "ACTIVE",
        "filter[registration.status]": "ISSUED",
    },
    "jurisdiction GB-ENG, GB-SCT, GB-WLS or GB-NIR": {
        "filter[entity.jurisdiction]": "GB-ENG,GB-SCT,GB-WLS,GB-NIR"
    },
}


def make_client(limiter: RateLimiter | None = None, **options: Any) -> HttpClient:
    """The GLEIF client: 1 request per second, JSON:API, redirects followed."""
    return HttpClient(
        API,
        follow_redirects=True,
        limiter=limiter or RateLimiter(1.0),
        max_hint=MAX_WAIT_S,
        headers={"Accept": "application/vnd.api+json"},
        **options,
    )


def normalise_company_number(number: str) -> str:
    """Companies House form (research note B4): upper case, no spaces, digits zero-padded to 8."""
    value = number.strip().upper().replace(" ", "")
    return value.zfill(8) if value.isdigit() else value


def expected_authority(number: str) -> str:
    """The research note's consistency check: SC is Scotland, NI Northern Ireland, else E&W."""
    return {"SC": "RA000587", "NI": "RA000586"}.get(number[:2], "RA000585")


@dataclass(frozen=True, slots=True)
class ParentLink:
    """A record's `direct-parent` or `ultimate-parent` link: a parent, an exception or nothing.

    `parent` and `relationship` are JSON:API `data` objects; `exception` holds the reporting
    exception's attributes. `reported` is true when GLEIF reports a parent with an LEI, even if
    it was not fetched (the parents' own parents are not).
    """

    child: str
    level: str
    reported: bool = False
    parent: dict[str, Any] | None = None
    relationship: dict[str, Any] | None = None
    exception: dict[str, Any] | None = None


@dataclass(slots=True)
class SpikeResult:
    """Everything one spike run fetched, in API form; `mapping` turns it into C1 records."""

    record: dict[str, Any]
    links: list[ParentLink] = field(default_factory=list)
    children: int = 0
    join_number: str | None = None
    join: list[dict[str, Any]] = field(default_factory=list)
    publish_date: str | None = None
    urls: list[str] = field(default_factory=list)

    def parents(self) -> Iterator[ParentLink]:
        """The links of the spike record itself whose parent was fetched."""
        lei = self.record["id"]
        return (link for link in self.links if link.child == lei and link.parent is not None)


class Gleif:
    """The calls of one spike run over an `HttpClient`; it keeps every URL it fetched."""

    def __init__(self, client: HttpClient) -> None:
        self.client = client
        self.urls: list[str] = []
        self.publish_date: str | None = None

    def get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """JSON:API body, or None on 404; HttpError on any other error status."""
        self.urls.append(str(self.client.build_request("GET", url, params=params).url))
        body = self.client.get_json(url, params)
        if isinstance(body, dict) and self.publish_date is None:
            self.publish_date = body.get("meta", {}).get("goldenCopy", {}).get("publishDate")
        return body

    def data(self, url: str, params: dict[str, Any] | None = None) -> Any:
        body = self.get(url, params)
        return None if body is None else body["data"]

    def total(self, url: str, params: dict[str, Any]) -> int:
        """`meta.pagination.total` of a list query, fetched with one record per page."""
        body = self.get(url, {**params, "page[size]": 1})
        return int(body["meta"]["pagination"]["total"]) if body else 0

    def link(self, record: dict[str, Any], level: str, follow: bool) -> ParentLink:
        """Branch on the link GLEIF gives: a parent record, a reporting exception, or none."""
        child = record["id"]
        links = record.get("relationships", {}).get(f"{level}-parent", {}).get("links", {})
        if "reporting-exception" in links:
            exception = self.data(links["reporting-exception"])
            attributes = exception["attributes"] if exception else None
            return ParentLink(child, level, exception=attributes)
        if "lei-record" not in links and "relationship-record" not in links:
            return ParentLink(child, level)
        if not follow:
            return ParentLink(child, level, reported=True)
        parent = self.data(links["lei-record"]) if "lei-record" in links else None
        relationship = (
            self.data(links["relationship-record"]) if "relationship-record" in links else None
        )
        return ParentLink(child, level, True, parent, relationship)

    def join(self, number: str) -> list[dict[str, Any]]:
        """LEI records at a Companies House authority whose `registeredAs` is this number."""
        params = {
            "filter[entity.registeredAs]": number,
            "filter[entity.registeredAt]": ",".join(CH_AUTHORITIES),
            "page[size]": 200,
        }
        return list(self.data("lei-records", params) or [])

    def coverage(self) -> dict[str, int]:
        """The research note's GB coverage counts, one request each."""
        return {label: self.total("lei-records", params) for label, params in COVERAGE.items()}


def run_spike(client: HttpClient, lei: str, ch_number: str | None = None) -> SpikeResult:
    """Fetch the record, both parents (and the parents' own exceptions), children and the join.

    The join uses `ch_number`, else the record's `registeredAs` when it is registered at a
    Companies House authority. Raises LookupError for an unknown LEI, ValueError for a
    malformed one and HttpError when GLEIF fails.
    """
    if not LEI_RE.fullmatch(lei):
        raise ValueError(f"{lei!r} is not an LEI (18 letters or digits, then 2 check digits)")
    gleif = Gleif(client)
    record = gleif.data(f"lei-records/{lei}")
    if record is None:
        raise LookupError(f"GLEIF has no LEI record {lei}")
    result = SpikeResult(record)
    result.links = [gleif.link(record, level, follow=True) for level in LEVELS]
    seen = {lei}
    for link in list(result.links):
        if link.parent is not None and link.parent["id"] not in seen:
            seen.add(link.parent["id"])
            result.links += [gleif.link(link.parent, level, follow=False) for level in LEVELS]
    result.children = gleif.total(f"lei-records/{lei}/direct-children", {})
    entity = record["attributes"]["entity"]
    registered_at = (entity.get("registeredAt") or {}).get("id")
    own_number = entity.get("registeredAs") if registered_at in CH_AUTHORITIES else None
    number = ch_number or own_number
    if number:
        result.join_number = normalise_company_number(number)
        result.join = gleif.join(result.join_number)
    result.publish_date, result.urls = gleif.publish_date, gleif.urls
    return result


def coverage(client: HttpClient) -> dict[str, int]:
    """The GB coverage counts (8 requests)."""
    return Gleif(client).coverage()
