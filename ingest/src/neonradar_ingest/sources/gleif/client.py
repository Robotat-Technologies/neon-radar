"""GLEIF API calls for the spike (PHASE-1.md M1.8b): one LEI record, its parents, the count of
its direct children, and the deterministic join to a Companies House number.

API `https://api.gleif.org/api/v1`: no key, 60 requests per minute (the limiter sends one per
second), `page[size]` at most 200, and page numbers only up to 10,000 results (cursor paging
beyond; docs/data/spikes/gleif.md). Redirects are never followed, and every path is built
here from a checked LEI, so the spike only ever talks to api.gleif.org.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from neonradar_ingest.http import HttpClient, HttpError, RateLimiter, redact, retry_after_seconds

API = "https://api.gleif.org/api/v1/"
CH_AUTHORITIES = ("RA000585", "RA000586", "RA000587")  # Companies House: E&W, NI, Scotland
LEVELS = ("direct", "ultimate")
LEI_RE = re.compile(r"[A-Z0-9]{18}[0-9]{2}\Z")
# GLEIF warned of interruptions from 19 October to 4 November 2026: a longer wait fails fast.
MAX_WAIT_S = 120.0
THROTTLE_WAIT_S = 60.0  # after a 429 without Retry-After: GLEIF counts requests per minute
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


def retry_hint(response: httpx.Response) -> float | None:
    """`Retry-After` when GLEIF sends one, else 60 s after a 429; None means backoff."""
    hint = retry_after_seconds(response)
    if hint is None and response.status_code == 429:
        return THROTTLE_WAIT_S
    return hint


def make_client(limiter: RateLimiter | None = None, **options: Any) -> HttpClient:
    """The GLEIF client: 1 request per second, JSON:API; redirects are never followed."""
    return HttpClient(
        API,
        follow_redirects=False,
        limiter=limiter or RateLimiter(1.0),
        retry_hint=retry_hint,
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


def _dig(value: Any, *keys: str) -> Any:
    """`value[k1][k2]...`, or None as soon as a level is missing or not an object."""
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _record(data: Any) -> dict[str, Any] | None:
    """An LEI record `data` object with `attributes.entity`, or HttpError; None stays None."""
    if data is None:
        return None
    if not isinstance(_dig(data, "attributes", "entity"), dict) or not data.get("id"):
        raise HttpError("unexpected response shape: an LEI record without id or entity")
    return dict(data)


def _checked(lei: str) -> str:
    if not LEI_RE.fullmatch(lei):
        raise ValueError(f"{lei!r} is not an LEI (18 letters or digits, then 2 check digits)")
    return lei


@dataclass(frozen=True, slots=True)
class ParentLink:
    """A record's `direct-parent` or `ultimate-parent` link: a parent, an exception or nothing.

    `parent` and `relationship` are JSON:API `data` objects; `exception` holds the reporting
    exception's attributes. `reported` is true when GLEIF reports a parent with an LEI, even if
    it was not fetched (the parents' own parents are not). `missing` is true when a linked
    record, relationship or exception answered 404.
    """

    child: str
    level: str
    reported: bool = False
    parent: dict[str, Any] | None = None
    relationship: dict[str, Any] | None = None
    exception: dict[str, Any] | None = None
    missing: bool = False


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


class Gleif:
    """The calls of one spike run over an `HttpClient`; it keeps every URL it fetched."""

    def __init__(self, client: HttpClient) -> None:
        self.client = client
        self.urls: list[str] = []
        self.publish_date: str | None = None

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """The JSON:API body, or None on 404. HttpError on a redirect, any other error status
        or a body that is not a JSON object."""
        response = self.client.get(url, params=params)
        self.urls.append(str(response.request.url))
        where = f"GET {redact(response.request.url)}"
        if response.is_redirect:
            target = redact(response.headers.get("Location", ""))
            message = f"{where}: HTTP {response.status_code} redirect to {target!r}"
            raise HttpError(f"{message}; GLEIF redirects are never followed", response.status_code)
        if response.status_code == 404:
            return None
        if response.is_error:
            raise HttpError(f"{where}: HTTP {response.status_code}", response.status_code)
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise HttpError(f"{where}: the response is not a JSON:API object")
        if self.publish_date is None:
            self.publish_date = _dig(body, "meta", "goldenCopy", "publishDate")
        return body

    def data(self, url: str, params: dict[str, Any] | None = None, many: bool = False) -> Any:
        """`data` of the body (a list with `many`), or None on 404; HttpError on another shape."""
        body = self.get(url, params)
        if body is None:
            return None
        data = body.get("data")
        if many:
            ok = isinstance(data, list) and all(isinstance(item, dict) for item in data)
        else:
            ok = isinstance(data, dict)
        if not ok:
            raise HttpError(f"GET {redact(url)}: unexpected response shape (no JSON:API data)")
        return data

    def total(self, url: str, params: dict[str, Any]) -> int:
        """`meta.pagination.total` of a list query, fetched with one record per page."""
        body = self.get(url, {**params, "page[size]": 1})
        total = _dig(body or {}, "meta", "pagination", "total")
        if body is not None and not isinstance(total, int):
            raise HttpError(f"GET {redact(url)}: unexpected response shape (no pagination total)")
        return total if isinstance(total, int) else 0

    def link(self, record: dict[str, Any], level: str, follow: bool) -> ParentLink:
        """Branch on the link GLEIF gives: a parent record, a reporting exception, or none.

        Only the presence of a link counts; the paths are built here from the checked LEI, so
        a URL inside a response is never followed.
        """
        child = _checked(str(record.get("id")))
        links = _dig(record, "relationships", f"{level}-parent", "links")
        links = links if isinstance(links, dict) else {}
        path = f"lei-records/{child}/{level}-parent"
        if "reporting-exception" in links:
            exception = self.data(f"{path}-reporting-exception")
            if exception is None:
                return ParentLink(child, level, missing=True)
            return ParentLink(child, level, exception=_dig(exception, "attributes") or {})
        if "lei-record" not in links and "relationship-record" not in links:
            return ParentLink(child, level)
        if not follow:
            return ParentLink(child, level, reported=True)
        parent = _record(self.data(path)) if "lei-record" in links else None
        relationship = self.data(f"{path}-relationship") if "relationship-record" in links else None
        missing = ("lei-record" in links and parent is None) or (
            "relationship-record" in links and relationship is None
        )
        return ParentLink(child, level, True, parent, relationship, missing=missing)

    def join(self, number: str) -> list[dict[str, Any]]:
        """LEI records at a Companies House authority whose `registeredAs` is this number."""
        params = {
            "filter[entity.registeredAs]": number,
            "filter[entity.registeredAt]": ",".join(CH_AUTHORITIES),
            "page[size]": 200,
        }
        found = (_record(data) for data in self.data("lei-records", params, many=True) or [])
        return [record for record in found if record is not None]

    def coverage(self) -> dict[str, int]:
        """The research note's GB coverage counts, one request each."""
        return {label: self.total("lei-records", params) for label, params in COVERAGE.items()}


def run_spike(client: HttpClient, lei: str, ch_number: str | None = None) -> SpikeResult:
    """Fetch the record, both parents (and the parents' own exceptions), children and the join.

    The join uses `ch_number`, else the record's `registeredAs` when it is registered at a
    Companies House authority. Raises LookupError for an unknown LEI, ValueError for a
    malformed one and HttpError when GLEIF fails.
    """
    gleif = Gleif(client)
    record = _record(gleif.data(f"lei-records/{_checked(lei)}"))
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
