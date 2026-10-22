"""Companies House Public Data REST API client (PHASE-1.md M1.8a steps 2 to 4).

The API key is the HTTP basic auth username with an empty password. The limit is 600 requests
per 5 minutes; a request over it gets 429 for the rest of the window, so after a 429 the
shared `HttpClient` waits until `X-Ratelimit-Reset` (epoch seconds, community-reported) or
300 seconds, and this client records the wait. Lists page with `items_per_page` and
`start_index`; the server may return fewer items than asked for, so the next page starts
after the items received.
"""

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Self

import httpx

from neonradar_ingest.http import HttpClient, HttpError, RateLimiter

BASE_URL = "https://api.company-information.service.gov.uk"
# 600 requests per 5 minutes is 2 per second; the limiter runs at that rate (M1.8a step 3).
REQUESTS_PER_WINDOW = 600
WINDOW_SECONDS = 300.0
REQUESTS_PER_SECOND = REQUESTS_PER_WINDOW / WINDOW_SECONDS
PAGE_SIZE = 100  # the community-reported ceiling of the officers list


@dataclass
class RequestLog:
    """What the spike report needs about the traffic; never keys, header values or bodies."""

    pages: dict[str, int] = field(default_factory=dict)
    rate_limit_waits: list[float] = field(default_factory=list)
    rate_limit_headers: set[str] = field(default_factory=set)
    status_codes: dict[int, int] = field(default_factory=dict)

    def see(self, response: httpx.Response) -> None:
        code = response.status_code
        self.status_codes[code] = self.status_codes.get(code, 0) + 1
        self.rate_limit_headers.update(
            name.lower() for name in response.headers if name.lower().startswith("x-ratelimit-")
        )


def reset_wait(headers: httpx.Headers, now: float) -> float:
    """Seconds until the rate limit window resets: `X-Ratelimit-Reset` if usable, else 300."""
    reset = headers.get("X-Ratelimit-Reset", "")
    if reset.isdigit():
        return min(max(float(reset) - now, 1.0), WINDOW_SECONDS)
    return WINDOW_SECONDS


class CompaniesHouseClient:
    """Reads of the three spike endpoints through the shared, rate-limited `HttpClient`."""

    def __init__(
        self,
        api_key: str,
        *,
        page_size: int = PAGE_SIZE,
        transport: httpx.BaseTransport | None = None,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        hide_paths: bool = False,
    ) -> None:
        self.log = RequestLog()
        self._page_size, self._clock = page_size, clock
        self._http = HttpClient(
            BASE_URL,
            follow_redirects=True,  # httpx drops the Authorization header on another host
            limiter=limiter or RateLimiter(REQUESTS_PER_SECOND, sleep=sleep),
            retry_hint=self._retry_hint,
            max_hint=WINDOW_SECONDS,
            sleep=sleep,
            auth=httpx.BasicAuth(api_key, ""),
            transport=transport,
            hide_paths=hide_paths,  # errors and logs name no company number (M2.3c)
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._http.close()

    @property
    def requests(self) -> int:
        """Requests sent, retries included."""
        return self._http.requests

    @property
    def retried(self) -> int:
        """Requests sent again after a 429, a 5xx or a transport error."""
        return self._http.retried

    def _retry_hint(self, response: httpx.Response) -> float | None:
        """After a 429, wait for the window to reset and record it; otherwise back off."""
        self.log.see(response)
        if response.status_code != 429:
            return None
        wait = reset_wait(response.headers, self._clock())
        self.log.rate_limit_waits.append(wait)
        return wait

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """GET `path`: None on 404, HttpError on other errors or a body that is not an object."""
        response = self._http.get(path, params=params)
        self.log.see(response)
        where = self._http.describe(response.request)
        if response.status_code == 404:
            return None
        if response.is_error:
            raise HttpError(f"{where}: HTTP {response.status_code}", response.status_code)
        body = response.json()
        if not isinstance(body, dict):
            raise HttpError(f"{where}: the body is not a JSON object", response.status_code)
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
