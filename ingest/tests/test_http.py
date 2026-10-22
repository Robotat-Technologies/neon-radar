import base64
import logging
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

import httpx
import pytest

from neonradar_ingest.http import (
    HttpClient,
    HttpError,
    RateLimiter,
    logged_url,
    redact,
    retry_after_seconds,
)

BASE = "https://api.example.test/v1"


class Server:
    """Canned replies through httpx.MockTransport, the requests seen, and a fake clock."""

    def __init__(self, *replies: httpx.Response | Exception) -> None:
        self.replies, self.seen = list(replies), list[httpx.Request]()
        self.now, self.sleeps = 0.0, list[float]()

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self, **kwargs: Any) -> HttpClient:
        kwargs.setdefault("follow_redirects", True)
        limiter = RateLimiter(1.0, clock=lambda: self.now, sleep=self.sleep)
        transport = httpx.MockTransport(self.handle)
        return HttpClient(BASE, limiter=limiter, transport=transport, sleep=self.sleep, **kwargs)


def test_sends_the_user_agent_and_the_timeouts_and_spaces_requests() -> None:
    server = Server(httpx.Response(200, json={"ok": True}), httpx.Response(200))
    client = server.client(headers={"User-Agent": "other", "Accept": "application/json"})
    assert client.get_json("/records", {"page[size]": 1}) == {"ok": True}
    client.head("/records")
    assert (server.sleeps, client.requests) == ([1.0], 2)  # the limiter: 1 per second
    request = server.seen[0]
    assert request.url == f"{BASE}/records?page%5Bsize%5D=1"
    assert request.headers["User-Agent"] == "NeonRadar/0.1.0 (+https://neonradar.com)"
    assert request.headers["Accept"] == "application/json"
    timeout = {"connect": 10.0, "read": 60.0, "write": 60.0, "pool": 60.0}
    assert request.extensions["timeout"] == timeout


@pytest.mark.parametrize(("follow", "status"), [(True, 200), (False, 307)])
def test_follows_redirects_only_when_told(follow: bool, status: int) -> None:
    server = Server(httpx.Response(307, headers={"Location": f"{BASE}/new"}), httpx.Response(200))
    assert server.client(follow_redirects=follow).get("/old").status_code == status


def test_retries_5xx_and_transport_errors_with_exponential_backoff() -> None:
    server = Server(httpx.Response(503), httpx.ConnectError("down"), httpx.Response(502))
    server.replies.append(httpx.Response(200))
    client = server.client()
    assert client.get("/x").status_code == 200
    assert server.sleeps == [1.0, 2.0, 4.0]  # the backoff already keeps requests 1 s apart
    assert (client.requests, client.retried, client.throttled) == (4, 3, 0)


def test_honours_retry_after_refuses_long_waits_and_retries_only_safe_requests() -> None:
    server = Server(httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(429))
    server.replies.append(httpx.Response(200))
    client = server.client()
    assert client.get("/x").status_code == 200
    assert (server.sleeps, client.throttled) == ([7.0, 2.0], 2)
    server = Server(httpx.Response(503), httpx.Response(200))
    with pytest.raises(HttpError, match="asked to wait 900 s") as error:
        server.client(retry_hint=lambda response: 900.0).get("/x")
    assert (error.value.status, server.sleeps, len(server.seen)) == (503, [], 1)
    server = Server(httpx.Response(429), httpx.Response(200))
    server.client(retry_hint=lambda response: 300.0).get("/x")  # e.g. the CH 300 s fallback
    assert server.sleeps == [300.0]
    server = Server(httpx.Response(503), httpx.Response(200))
    with pytest.raises(HttpError, match=r"POST .* after 1 attempt"):
        server.client().post("/x")
    server = Server(httpx.Response(501), httpx.Response(505))
    client = server.client()
    assert [client.get("/x").status_code, client.get("/x").status_code] == [501, 505]
    assert (server.sleeps, client.retried) == ([1.0], 0)  # the limiter only; no retry
    server = Server(httpx.UnsupportedProtocol("no scheme"))
    with pytest.raises(HttpError, match="no scheme"):
        server.client().get("/x")
    assert len(server.seen) == 1


def test_a_per_request_user_agent_is_replaced_and_retries_must_not_be_negative() -> None:
    server = Server(httpx.Response(200))
    server.client().get("/x", headers={"User-Agent": "other"})
    assert server.seen[0].headers["User-Agent"].startswith("NeonRadar/")
    with pytest.raises(ValueError, match="retries"):
        Server().client(retries=-1)


def test_stream_is_limited_and_retried_too() -> None:
    server = Server(httpx.Response(503), httpx.Response(200, content=b"zip bytes"))
    with server.client().stream("GET", "/file.zip") as response:
        assert response.read() == b"zip bytes"
    assert server.sleeps == [1.0]


def test_gives_up_after_three_retries_and_get_json_raises_on_errors() -> None:
    server = Server(*[httpx.Response(500) for _ in range(4)], httpx.Response(404))
    server.replies.append(httpx.Response(400))
    client = server.client()
    with pytest.raises(HttpError, match=r"GET .*/x failed after 4 attempt\(s\): HTTP 500") as error:
        client.get("/x")
    assert (error.value.status, len(server.seen), server.sleeps) == (500, 4, [1.0, 2.0, 4.0])
    assert client.get_json("/missing") is None
    with pytest.raises(HttpError, match="HTTP 400"):
        client.get_json("/bad")


def test_rate_limiter_spaces_requests() -> None:
    server = Server()
    limiter = RateLimiter(2.0, clock=lambda: server.now, sleep=server.sleep)
    for _ in range(3):
        limiter.wait()
    server.now += 10
    limiter.wait()
    assert server.sleeps == [0.5, 0.5]
    with pytest.raises(ValueError, match="greater than zero"):
        RateLimiter(0)


def test_logs_never_show_keys_or_authorization(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    server = Server(*[httpx.Response(503) for _ in range(4)])
    with pytest.raises(HttpError) as error:
        server.client(auth=("key-1234", "")).get("/x", params={"api_token": "tok-5678", "q": "a"})
    basic = base64.b64encode(b"key-1234:").decode()
    assert server.seen[0].headers["Authorization"] == f"Basic {basic}"
    logged = caplog.text + str(error.value)
    assert "api_token=REDACTED&q=a" in logged
    assert "httpx" in {record.name for record in caplog.records}  # httpx's own request log
    for secret in ("key-1234", "tok-5678", "Authorization", basic):
        assert secret not in logged
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.INFO  # raw headers


def test_log_query_false_keeps_query_strings_out_of_logs_and_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PHASE-2.md M2.6 rule 4: a signed redirect target is followed but never logged."""
    caplog.set_level(logging.DEBUG)
    signed = "https://files.example.test/list.xml?se=2099&sig=s1"
    server = Server(
        httpx.Response(302, headers={"Location": signed}), *[httpx.Response(503) for _ in range(4)]
    )
    with pytest.raises(HttpError) as error:
        server.client(log_query=False).get("/list", params={"token": "t1", "page": "2"})
    logged = caplog.text + str(error.value)
    assert "https://files.example.test/list.xml" in logged
    for part in ("se=2099", "sig=", "s1", "token", "page=2"):
        assert part not in logged, part
    server = Server(httpx.Response(200))
    server.client().get("/list", params={"page": "2"})  # the default keeps a redacted query
    assert "page=2" in caplog.text


def test_hide_paths_and_log_query_false_together_name_only_the_hosts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Both rules on one client (M2.3c record values in paths, M2.6 rule 4 query strings): the
    request and the redirect it follows show only their hosts in logs and errors."""
    caplog.set_level(logging.DEBUG)
    signed = "https://files.example.test/company/99000010/list.xml?se=2099&sig=s1"
    server = Server(
        httpx.Response(302, headers={"Location": signed}), *[httpx.Response(503) for _ in range(4)]
    )
    client = server.client(hide_paths=True, log_query=False)
    with pytest.raises(HttpError) as error:
        client.get("/company/99000020/officers", params={"token": "t1", "page": "2"})
    assert str(error.value) == "GET https://api.example.test/… failed after 4 attempt(s): HTTP 503"
    logged = caplog.text + str(error.value)
    assert "GET https://files.example.test/…" in caplog.text  # httpx's log of the redirect hop
    for part in ("/v1", "/company/", "99000010", "99000020", "list.xml", "se=2099", "sig=",
                 "s1", "token", "page=2"):  # fmt: skip
        assert part not in logged, part
    url = "https://user:pw@x.test/company/99000030?api_key=k1&page=2#top"
    rules = [(True, True), (False, True), (True, False), (False, False)]
    assert [logged_url(url, query=query, path=path) for query, path in rules] == [
        "https://x.test/company/99000030?api_key=REDACTED&page=2#top",
        "https://x.test/company/99000030",
        "https://x.test/…",
        "https://x.test/…",
    ]


def hint(headers: dict[str, str]) -> float | None:
    return retry_after_seconds(httpx.Response(429, headers=headers))


def test_redact_and_retry_after_parsing() -> None:
    url = "https://user:pw@x.test/a?sessionId=1&lei=2&pwd=3&credential=4"
    assert (
        redact(url) == "https://x.test/a?sessionId=REDACTED&lei=2&pwd=REDACTED&credential=REDACTED"
    )
    soon = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    assert 25 < (hint({"Retry-After": soon}) or 0) <= 30
    assert [hint({"Retry-After": "120"}), hint({"Retry-After": "x"}), hint({})] == [120, None, None]
    odd = httpx.Response(429, headers=[(b"Retry-After", "\u00b2".encode())])
    assert retry_after_seconds(odd) is None
