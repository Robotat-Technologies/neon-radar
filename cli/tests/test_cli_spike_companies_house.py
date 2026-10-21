"""`neonradar spike companies-house` with a mocked API (M1.8a); no network, no key."""

from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest import spikes
from neonradar_ingest.http import RateLimiter
from neonradar_ingest.sources.companies_house import client as ch_client

runner = CliRunner()
PROFILE = {"company_number": "SYN00001", "company_name": "QUILLON MARSH TRADING LTD"}


def serve(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/company/SYN00001":
        return httpx.Response(200, json=PROFILE)
    if request.url.path.startswith("/company/SYN00001/"):
        return httpx.Response(200, json={"items": [], "total_results": 0})
    return httpx.Response(404)


HANDLER = {"server": serve}  # a test can swap the mock server


@pytest.fixture
def mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    real = ch_client.CompaniesHouseClient

    def fake(key: str, **kwargs: Any) -> ch_client.CompaniesHouseClient:
        assert key == "SYN-KEY"
        limiter = RateLimiter(1.0, clock=lambda: 0.0, sleep=lambda seconds: None)
        transport = httpx.MockTransport(lambda request: HANDLER["server"](request))
        return real(key, transport=transport, limiter=limiter)

    monkeypatch.setattr(ch_client, "CompaniesHouseClient", fake)
    monkeypatch.setattr(spikes, "SPIKE_ROOT", tmp_path)
    monkeypatch.setenv("CH_API_KEY", "SYN-KEY")
    return tmp_path


def test_the_command_prints_counts_and_validates_its_output(mocked: Path) -> None:
    result = runner.invoke(app, ["spike", "companies-house", "--company", "syn00001"])
    assert result.exit_code == 0, result.output
    assert "company SYN00001: 1 records" in result.output
    assert "requests: 3;" in result.output
    assert result.output.rstrip().endswith("OK, 0 issues (strict)")
    assert "QUILLON" not in result.output
    assert len(list((mocked / "companies_house").glob("*.ftm.jsonl"))) == 1


def test_an_unknown_company_fails(mocked: Path) -> None:
    result = runner.invoke(app, ["spike", "companies-house", "--company", "SYN00404"])
    assert (result.exit_code, result.output) == (
        1,
        "FAIL  company SYN00404 not found (unknown, or dissolved before 2010)\n",
    )


def test_without_a_key_the_command_stops_before_any_request(
    mocked: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CH_API_KEY", "")
    result = runner.invoke(app, ["spike", "companies-house", "--company", "SYN00001"])
    assert (result.exit_code, result.output) == (
        1,
        "FAIL  CH_API_KEY is not set: the operator adds it to .env (OD-14)\n",
    )
    assert not (mocked / "companies_house").exists()


def test_errors_the_shared_client_does_not_retry_fail_cleanly(
    mocked: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def loop(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": str(request.url)})

    monkeypatch.setitem(HANDLER, "server", loop)
    result = runner.invoke(app, ["spike", "companies-house", "--company", "SYN00001"])
    assert (result.exit_code, result.output) == (1, "FAIL  Exceeded maximum allowed redirects.\n")
    assert result.exception is None or isinstance(result.exception, SystemExit)
