from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest import spikes
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources import gleif

runner = CliRunner()
LEI = "SYN00000000000000128"  # synthetic: valid check digits, no GLEIF record


def synthetic_record() -> dict[str, Any]:
    """A synthetic LEI record without parents (shape of the live API, 21 Oct 2026)."""
    entity = {
        "legalName": {"name": "SYNTHETIC CHILD EXAMPLE LIMITED", "language": "en"},
        "registeredAt": {"id": "RA000585", "other": None},
        "registeredAs": "ZZ000001",
        "jurisdiction": "GB",
        "status": "ACTIVE",
    }
    return {
        "type": "lei-records",
        "id": LEI,
        "attributes": {"lei": LEI, "entity": entity, "registration": {"status": "ISSUED"}},
        "relationships": {},
    }


def use_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int = 200) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        if request.url.path.endswith("/direct-children"):
            return httpx.Response(200, json={"meta": {"pagination": {"total": 0}}, "data": []})
        if request.url.params.get("filter[entity.registeredAs]") == "ZZ000001":
            return httpx.Response(200, json={"data": [synthetic_record()]})
        if request.url.path.endswith(f"/lei-records/{LEI}"):
            meta = {"goldenCopy": {"publishDate": "2026-10-21T00:00:00Z"}}
            return httpx.Response(200, json={"meta": meta, "data": synthetic_record()})
        return httpx.Response(404, json={})

    def make_client(**options: Any) -> HttpClient:
        limiter = RateLimiter(1.0, sleep=lambda seconds: None)
        transport = httpx.MockTransport(handle)
        return gleif.client.make_client(limiter, transport=transport, sleep=lambda seconds: None)

    monkeypatch.setattr(gleif, "make_client", make_client)
    monkeypatch.setattr(spikes, "SPIKE_ROOT", tmp_path)


def test_spike_gleif_prints_the_record_parents_and_join_and_writes_valid_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_api(monkeypatch, tmp_path)
    result = runner.invoke(app, ["spike", "gleif", "--lei", LEI.lower()])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == f"record {LEI}: SYNTHETIC CHILD EXAMPLE LIMITED"
    assert lines[1].startswith("  registeredAs ZZ000001 at RA000585; jurisdiction GB")
    assert lines[2:4] == [f"  {LEI} direct parent: none", f"  {LEI} ultimate parent: none"]
    assert "join: Companies House ZZ000001 -> " in result.output
    assert "spike record matched: yes" in result.output
    assert lines[-1] == "OK, 0 issues (strict)"
    written = sorted(path.name for path in (tmp_path / "gleif").iterdir())
    assert [name.endswith(f"-{LEI}.ftm.jsonl") for name in written] == [True, False]


def test_spike_gleif_reports_an_outage_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_api(monkeypatch, tmp_path, status=503)
    result = runner.invoke(app, ["spike", "gleif", "--lei", LEI])
    assert result.exit_code == 1
    assert result.output.startswith(
        f"FAIL  GLEIF: GET https://api.gleif.org/api/v1/lei-records/{LEI}"
    )
    assert "failed after 4 attempt(s): HTTP 503" in result.output
    assert not (tmp_path / "gleif").exists()


@pytest.mark.network
def test_real_gleif_spike(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The real run (PHASE-1.md M1.8b), about 10 requests to api.gleif.org; never in CI."""
    monkeypatch.setattr(spikes, "SPIKE_ROOT", tmp_path)
    result = runner.invoke(app, ["spike", "gleif", "--lei", "549300OWFMSO9NYV4H90"])
    print(result.output)
    assert result.exit_code == 0, result.output
    assert "registeredAs 01800000 at RA000585" in result.output
    assert "spike record matched: yes" in result.output
    assert result.output.splitlines()[-1] == "OK, 0 issues (strict)"
