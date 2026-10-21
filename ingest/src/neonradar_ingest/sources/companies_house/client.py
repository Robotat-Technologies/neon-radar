"""Companies House Public Data REST API client (PHASE-1.md M1.8a steps 2 to 4).

The API key is the HTTP basic auth username with an empty password. The limit is 600 requests
per 5 minutes; a request over it gets 429 for the rest of the window, so on 429 the client
waits until `X-Ratelimit-Reset` (epoch seconds, community-reported) or 300 seconds, records
the wait and tries again. Lists page with `items_per_page` and `start_index`; the server may
return fewer items than asked for, so the next page starts after the items received.
"""

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.company-information.service.gov.uk"
# 600 requests per 5 minutes is 2 per second; the limiter runs at that rate (M1.8a step 3).
REQUESTS_PER_WINDOW = 600
WINDOW_SECONDS = 300.0
REQUESTS_PER_SECOND = REQUESTS_PER_WINDOW / WINDOW_SECONDS
PAGE_SIZE = 100  # the community-reported ceiling of the officers list
MAX_RATE_LIMIT_WAITS = 3


class CompaniesHouseError(RuntimeError):
    """The API answered with an error the client does not retry."""


@dataclass
class RequestLog:
    """What the spike report needs about the traffic; never keys, headers or bodies."""

    requests: int = 0
    pages: dict[str, int] = field(default_factory=dict)
    rate_limit_waits: list[float] = field(default_factory=list)
    rate_limit_headers: set[str] = field(default_factory=set)
    status_codes: dict[int, int] = field(default_factory=dict)


def reset_wait(headers: httpx.Headers, now: float) -> float:
    """Seconds until the rate limit window resets: `X-Ratelimit-Reset` if usable, else 300."""
    reset = headers.get("X-Ratelimit-Reset", "")
    if reset.isdigit():
        return min(max(float(reset) - now, 1.0), WINDOW_SECONDS)
    return WINDOW_SECONDS


class CompaniesHouseClient:
    """Typed reads of the three spike endpoints over an `httpx.Client`.

    `http` carries the base URL, the basic auth, timeouts, the User-Agent and the client-side
    rate limiter (see `neonradar_ingest.sources.companies_house.spike.open_client`).
    """

    def __init__(
        self,
        http: httpx.Client,
        *,
        page_size: int = PAGE_SIZE,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._http = http
        self._page_size = page_size
        self._sleep = sleep
        self._clock = clock
        self.log = RequestLog()

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """GET `path`; None on 404. Waits out a 429 window up to three times."""
        waits = 0
        while True:
            response = self._http.get(path, params=params)
            self.log.requests += 1
            code = response.status_code
            self.log.status_codes[code] = self.log.status_codes.get(code, 0) + 1
            self.log.rate_limit_headers.update(
                name for name in response.headers if name.lower().startswith("x-ratelimit-")
            )
            if code == 429 and waits < MAX_RATE_LIMIT_WAITS:
                waits += 1
                wait = reset_wait(response.headers, self._clock())
                self.log.rate_limit_waits.append(wait)
                logger.warning("Companies House rate limit reached; waiting %.0f s", wait)
                self._sleep(wait)
                continue
            if code == 404:
                return None
            if code >= 400:
                raise CompaniesHouseError(f"GET {path} answered HTTP {code}")
            body = response.json()
            if not isinstance(body, dict):
                raise CompaniesHouseError(f"GET {path} did not answer with a JSON object")
            return body

    def company(self, number: str) -> dict[str, Any] | None:
        """`/company/{number}`: the company profile, or None if the number is unknown."""
        return self.get_json(f"/company/{number}")

    def pages(self, path: str, max_pages: int) -> Iterator[dict[str, Any]]:
        """Each page of a list endpoint, at most `max_pages`; stops at `total_results`."""
        start = 0
        for _ in range(max_pages):
            page = self.get_json(path, {"items_per_page": self._page_size, "start_index": start})
            if page is None:
                return
            self.log.pages[path] = self.log.pages.get(path, 0) + 1
            yield page
            items = page.get("items") or []
            start += len(items)
            total = page.get("total_results")
            if not items or (isinstance(total, int) and start >= total):
                return

    def officers(self, number: str, max_pages: int) -> Iterator[dict[str, Any]]:
        return self.pages(f"/company/{number}/officers", max_pages)

    def pscs(self, number: str, max_pages: int) -> Iterator[dict[str, Any]]:
        return self.pages(f"/company/{number}/persons-with-significant-control", max_pages)
