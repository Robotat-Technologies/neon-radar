"""Companies House REST client (M1.8a steps 2 to 4) over httpx.MockTransport; no network."""

import base64
from collections.abc import Callable

import httpx
import pytest

from neonradar_ingest.http import USER_AGENT, HttpError, RateLimiter
from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house.client import (
    REQUESTS_PER_SECOND,
    CompaniesHouseClient,
    reset_wait,
)

Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, sleeps: list[float], **kwargs: int) -> CompaniesHouseClient:
    return CompaniesHouseClient(
        "SYN-KEY",
        transport=httpx.MockTransport(handler),
        limiter=RateLimiter(REQUESTS_PER_SECOND, clock=lambda: 0.0, sleep=lambda s: None),
        sleep=sleeps.append,
        clock=lambda: 1_000.0,
        **kwargs,
    )


def test_the_limiter_allows_600_requests_per_5_minutes() -> None:
    assert REQUESTS_PER_SECOND * 300 == 600
    with CompaniesHouseClient("SYN-KEY") as client:
        assert client._http.limiter.interval == 0.5


def test_the_key_is_the_basic_auth_username_with_an_empty_password() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"company_number": "SYN00001"})

    assert make_client(handler, []).company("SYN00001") == {"company_number": "SYN00001"}
    assert seen[0].headers["Authorization"] == "Basic " + base64.b64encode(b"SYN-KEY:").decode()
    assert seen[0].headers["User-Agent"] == USER_AGENT
    assert str(seen[0].url) == "https://api.company-information.service.gov.uk/company/SYN00001"


def test_pages_advance_by_the_items_received_and_stop_at_total_results() -> None:
    starts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params["start_index"])
        starts.append(f"{start}/{request.url.params['items_per_page']}")
        items = [{"n": n} for n in range(start, min(start + 2, 5))]  # fewer than asked for
        return httpx.Response(200, json={"items": items, "total_results": 5})

    client = make_client(handler, [])
    pages = list(client.officers("SYN00001", max_pages=5))
    assert [len(page["items"]) for page in pages] == [2, 2, 1]
    assert starts == ["0/100", "2/100", "4/100"]
    assert client.log.pages == {"/company/SYN00001/officers": 3}
    assert client.requests == 3


def test_max_pages_stops_early_and_an_empty_page_ends_the_list() -> None:
    full = make_client(lambda r: httpx.Response(200, json={"items": [{}], "total_results": 50}), [])
    assert len(list(full.pscs("SYN00001", max_pages=2))) == 2
    empty = make_client(lambda request: httpx.Response(200, json={"items": []}), [])
    assert len(list(empty.pscs("SYN00001", max_pages=5))) == 1


def test_404_means_no_such_resource() -> None:
    client = make_client(lambda request: httpx.Response(404, json={"errors": []}), [])
    assert client.company("SYN00404") is None
    assert list(client.pscs("SYN00404", max_pages=5)) == []


def test_429_waits_until_the_window_resets_and_is_recorded() -> None:
    answers = iter(
        [
            httpx.Response(429, headers={"X-Ratelimit-Reset": "1120", "X-Ratelimit-Remain": "0"}),
            httpx.Response(200, json={"ok": True}, headers={"X-Ratelimit-Limit": "600"}),
        ]
    )
    sleeps: list[float] = []
    client = make_client(lambda request: next(answers), sleeps)
    assert client.get_json("/company/SYN00001") == {"ok": True}
    assert sleeps == [120.0]
    assert client.log.rate_limit_waits == [120.0]
    assert client.log.status_codes == {429: 1, 200: 1}
    assert client.log.rate_limit_headers == {
        "x-ratelimit-reset",
        "x-ratelimit-remain",
        "x-ratelimit-limit",
    }


@pytest.mark.parametrize(
    ("headers", "wait"),
    [
        ({}, 300.0),
        ({"X-Ratelimit-Reset": "soon"}, 300.0),
        ({"X-Ratelimit-Reset": "900"}, 1.0),
        ({"X-Ratelimit-Reset": "9999"}, 300.0),
    ],
)
def test_reset_wait_falls_back_to_the_full_window(headers: dict[str, str], wait: float) -> None:
    assert reset_wait(httpx.Headers(headers), now=1_000.0) == wait


def test_429_gives_up_after_three_waits() -> None:
    sleeps: list[float] = []
    client = make_client(lambda request: httpx.Response(429), sleeps)
    with pytest.raises(HttpError, match="HTTP 429"):
        client.get_json("/company/SYN00001")
    assert sleeps == [300.0, 300.0, 300.0]


def test_server_errors_back_off_instead_of_waiting_for_the_window() -> None:
    answers = iter([httpx.Response(503), httpx.Response(200, json={"ok": True})])
    sleeps: list[float] = []
    client = make_client(lambda request: next(answers), sleeps)
    assert client.get_json("/company/SYN00001") == {"ok": True}
    assert sleeps == [1.0]
    assert client.log.rate_limit_waits == []


def test_other_errors_raise_without_the_key() -> None:
    client = make_client(lambda request: httpx.Response(401), [])
    with pytest.raises(HttpError, match="HTTP 401") as error:
        client.company("SYN00001")
    assert "SYN-KEY" not in str(error.value)


def test_a_body_that_is_not_an_object_raises() -> None:
    client = make_client(lambda request: httpx.Response(200, json=[1, 2]), [])
    with pytest.raises(HttpError, match="JSON object"):
        client.company("SYN00001")


def test_a_blank_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CH_API_KEY", "  ")
    assert IngestSettings(_env_file=None).companies_house_key() is None
    monkeypatch.setenv("CH_API_KEY", "SYN-KEY")
    assert IngestSettings(_env_file=None).companies_house_key() == "SYN-KEY"
