"""The shared HTTP client for spikes and loaders (PHASE-1.md M1.8, common rules).

httpx with a 10 s connect and 60 s read timeout, an explicit `follow_redirects`, the NeonRadar
User-Agent, a per-source rate limiter, and retries with exponential backoff after a 429, a
500, 502, 503 or 504 or a transport error that honour `Retry-After`. Logs never show headers,
keys or credentials.
"""

import logging
import re
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from neonradar_ingest import __version__

logger = logging.getLogger(__name__)

USER_AGENT = f"NeonRadar/{__version__} (+https://neonradar.com)"
TIMEOUT = httpx.Timeout(60.0, connect=10.0)
SECRET_NAME = re.compile(r"key|token|secret|pass|pwd|credential|auth|sig|session", re.IGNORECASE)
BACKOFF_BASE, BACKOFF_MAX = 1.0, 60.0  # seconds: 1, 2, 4, ... at most 60
RETRY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})  # idempotent: safe to send again
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})  # 501 and 505 do not change on a retry

Clock = Callable[[], float]
Sleep = Callable[[float], None]
RetryHint = Callable[[httpx.Response], float | None]


class HttpError(Exception):
    """A request failed for good; the message has the method, a redacted URL and the reason."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def redact(url: httpx.URL | str) -> str:
    """The URL without user info and with the values of secret-looking query parameters hidden."""
    url = httpx.URL(url)
    params = [(k, "REDACTED" if SECRET_NAME.search(k) else v) for k, v in url.params.multi_items()]
    return str(url.copy_with(userinfo=b"", params=params))


def _redact_urls(record: logging.LogRecord) -> bool:
    if isinstance(record.args, tuple):
        record.args = tuple(redact(a) if isinstance(a, httpx.URL) else a for a in record.args)
    return True


logging.getLogger("httpx").addFilter(_redact_urls)  # httpx logs every request URL at INFO
# httpcore logs raw response headers (cookies, tokens) at DEBUG; keep it quiet even then.
logging.getLogger("httpcore").setLevel(logging.INFO)


def retry_after_seconds(response: httpx.Response) -> float | None:
    """Seconds to wait from a `Retry-After` header (delay seconds or an HTTP date), else None."""
    value = response.headers.get("Retry-After", "").strip()
    if value.isascii() and value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    when = when if when.tzinfo else when.replace(tzinfo=UTC)
    return (when - datetime.now(UTC)).total_seconds()


class RateLimiter:
    """At most `per_second` requests per second to one source (thread-safe).

    Each source builds its own: Companies House 2 per second, GLEIF 1 per second.
    """

    def __init__(
        self, per_second: float, clock: Clock = time.monotonic, sleep: Sleep = time.sleep
    ) -> None:
        if per_second <= 0:
            raise ValueError("per_second must be greater than zero")
        self.interval = 1.0 / per_second
        self._clock, self._sleep = clock, sleep
        self._next = float("-inf")
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until the next request may go."""
        with self._lock:
            now = self._clock()
            if self._next > now:
                self._sleep(self._next - now)
            self._next = max(now, self._next) + self.interval


class HttpClient(httpx.Client):
    """An `httpx.Client` for one source; every `get`, `head` and `stream` is limited and retried.

    `options` go to httpx (`headers`, `auth`, `transport`); the User-Agent is always NeonRadar's.
    After a 429, 500, 502, 503 or 504 or a transport error, a GET, HEAD or OPTIONS request is
    retried up to `retries` times (other methods are sent once). It waits what `retry_hint`
    reads from the response (default `Retry-After`; Companies House can read
    `X-Ratelimit-Reset`), or else 1, 2, 4 ... seconds. A hint over `max_hint` seconds raises
    HttpError instead of retrying before the server allows it.
    `requests`, `retried` and `throttled` count what happened, for the spike report.
    """

    def __init__(
        self,
        base_url: str,
        *,
        follow_redirects: bool,
        limiter: RateLimiter,
        retries: int = 3,
        retry_hint: RetryHint = retry_after_seconds,
        max_hint: float = 300.0,
        sleep: Sleep = time.sleep,
        **options: Any,
    ) -> None:
        if retries < 0:
            raise ValueError("retries must be 0 or more")
        super().__init__(
            base_url=base_url, timeout=TIMEOUT, follow_redirects=follow_redirects, **options
        )
        self.headers["User-Agent"] = USER_AGENT
        self.limiter, self.retries, self.max_hint = limiter, retries, max_hint
        self._retry_hint, self._sleep = retry_hint, sleep
        self.requests = self.retried = self.throttled = 0

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        """httpx's `send` behind the rate limiter, with retries; HttpError when they run out."""
        request.headers["User-Agent"] = USER_AGENT  # also over a per-request header
        where = f"{request.method} {redact(request.url)}"
        retries = self.retries if request.method in RETRY_METHODS else 0
        for attempt in range(retries + 1):
            self.limiter.wait()
            self.requests += 1
            response: httpx.Response | None = None
            try:
                response = super().send(request, **kwargs)
            except httpx.UnsupportedProtocol as exc:  # a bad URL: sending again cannot help
                raise HttpError(f"{where}: {exc}") from None
            except httpx.TransportError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code not in RETRY_STATUSES:
                    return response
                if response.status_code == 429:
                    self.throttled += 1
                problem = f"HTTP {response.status_code}"
                response.close()
            status = response.status_code if response is not None else None
            if attempt == retries:
                raise HttpError(f"{where} failed after {attempt + 1} attempt(s): {problem}", status)
            hint = self._retry_hint(response) if response is not None else None
            if hint is not None and hint > self.max_hint:  # never retry before the server allows
                raise HttpError(f"{where}: {problem}; asked to wait {hint:.0f} s", status)
            backoff = min(BACKOFF_BASE * 2**attempt, BACKOFF_MAX)
            delay = backoff if hint is None else max(hint, 0.0)
            logger.warning("%s: %s; retry %d in %.1f s", where, problem, attempt + 1, delay)
            self.retried += 1
            self._sleep(delay)
        raise AssertionError("unreachable")

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET and parse JSON. None on 404; HttpError on any other status of 400 or more."""
        response = self.get(url, params=params)
        if response.status_code == 404:
            return None
        if response.is_error:
            where = f"GET {redact(response.request.url)}"
            raise HttpError(f"{where}: HTTP {response.status_code}", response.status_code)
        return response.json()
