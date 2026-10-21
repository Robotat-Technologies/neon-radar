"""The OpenSanctions spike against `httpx.MockTransport` (PHASE-1.md M1.8d).

The mocked server answers like data.opensanctions.org since 17 August 2026: the
`datasets/latest/...` path redirects (307) to `artifacts/<collection>/<version>/...`. Bodies
are synthetic: `index.json` is built here and `entities.ftm.json` is the synthetic fixture.
"""

import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from neonradar_contracts.records import Manifest, manifest_path, validate_files
from neonradar_ingest.http import HttpClient, HttpError, RateLimiter
from neonradar_ingest.sources.opensanctions.access import (
    REFUSAL,
    Access,
    LicenceRequired,
    read_access,
    require_access,
)
from neonradar_ingest.sources.opensanctions.spike import (
    BASE_URL,
    IndexInfo,
    index_url,
    make_client,
    run_spike,
    summary_lines,
)

ENTITIES = Path(__file__).parent / "fixtures" / "opensanctions" / "entities.ftm.json"
ARTIFACTS = "https://data.opensanctions.org/artifacts/sanctions/20261015000000-syn"
INDEX = {
    "name": "sanctions",
    "title": "Synthetic example collection",
    "version": "20261015000000-syn",
    "last_export": "2026-10-15T00:00:00",
    "resources": [
        {
            "name": "entities.ftm.json",
            "url": f"{ARTIFACTS}/entities.ftm.json",
            "checksum": "0" * 40,
            "mime_type": "application/json+ftm",
        },
        {"name": "targets.simple.csv", "url": f"{ARTIFACTS}/targets.simple.csv"},
    ],
}


class SyntheticServer:
    """Records every request; serves the synthetic index and entities after a 307."""

    def __init__(self) -> None:
        self.requests: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if url.startswith(f"{BASE_URL}/sanctions/"):
            location = url.replace(f"{BASE_URL}/sanctions", ARTIFACTS)
            return httpx.Response(307, headers={"Location": location})
        if url == f"{ARTIFACTS}/index.json":
            return httpx.Response(200, json=INDEX)
        if url == f"{ARTIFACTS}/entities.ftm.json":
            return httpx.Response(200, content=ENTITIES.read_bytes())
        return httpx.Response(404)


@pytest.fixture
def server() -> SyntheticServer:
    return SyntheticServer()


@pytest.fixture
def client(server: SyntheticServer) -> Iterator[HttpClient]:
    with make_client(transport=httpx.MockTransport(server), sleep=lambda _: None) as client:
        client.limiter = RateLimiter(1e6)  # no waiting in tests
        yield client


def test_none_refuses_before_any_request(
    server: SyntheticServer, client: HttpClient, tmp_path: Path
) -> None:
    with pytest.raises(LicenceRequired, match=REFUSAL):
        run_spike(client, access=Access.NONE, root=tmp_path / "out")
    assert server.requests == []
    assert not (tmp_path / "out").exists()


def test_evaluation_without_the_confirmation_refuses(
    server: SyntheticServer, client: HttpClient, tmp_path: Path
) -> None:
    with pytest.raises(LicenceRequired, match="written confirmation"):
        run_spike(client, access=Access.EVALUATION, licence_file=tmp_path / "missing.md")
    assert server.requests == []


@pytest.mark.parametrize("route", [Access.EVALUATION, Access.EXEMPT])
def test_reading_routes_stream_count_and_write_nothing(
    client: HttpClient, tmp_path: Path, route: Access
) -> None:
    confirmation = tmp_path / "opensanctions.md"
    confirmation.write_text("written confirmation (test)", encoding="utf-8")
    out = tmp_path / "out"
    result = run_spike(client, access=route, root=out, licence_file=confirmation)
    assert result.index.version == "20261015000000-syn"
    assert result.index.checksum == "0" * 40
    assert result.index.redirects == (307,)
    assert result.index.url == f"{ARTIFACTS}/index.json"
    assert result.entities_url == f"{ARTIFACTS}/entities.ftm.json"
    assert result.stats.lines == 12
    assert result.stats.mapped.total() == 10
    assert result.stats.skipped == Counter(Identification=1, SynthFutureSchema=1)
    assert result.stats.flags == Counter(PEP=1, RCA=1, Sanctioned=1)
    assert result.issues == Counter()
    assert result.records_file is None
    assert not out.exists()


def test_licensed_writes_valid_records_and_a_manifest_to_the_cache(
    client: HttpClient, tmp_path: Path
) -> None:
    result = run_spike(client, access=Access.LICENSED, root=tmp_path)
    assert result.records_file is not None
    assert result.records_file.parent == tmp_path / "opensanctions"
    assert result.records_file.name.startswith("opensanctions_default-")
    assert result.records_file.name.endswith("-sanctions.ftm.jsonl")
    counts, issues = validate_files([result.records_file], strict=True)
    assert counts.total() == 10 and issues == []
    raw = json.loads(manifest_path(result.records_file).read_text(encoding="utf-8"))
    manifest = Manifest.model_validate(raw)
    assert manifest.dataset == "opensanctions_default"
    assert manifest.licence.id == "CC-BY-NC-4.0"
    assert manifest.synthetic is False
    assert manifest.source.source_version == "20261015000000-syn"
    assert manifest.counts.skipped == {"Identification": 1, "SynthFutureSchema": 1}


def test_rows_limits_the_lines_read(client: HttpClient, tmp_path: Path) -> None:
    result = run_spike(client, access=Access.EXEMPT, rows=3, root=tmp_path)
    assert result.stats.lines == 3
    with pytest.raises(ValueError, match="rows"):
        run_spike(client, access=Access.EXEMPT, rows=0, root=tmp_path)


def test_unknown_collections_are_refused() -> None:
    assert index_url("peps") == f"{BASE_URL}/peps/index.json"
    for collection in ("all", "../sanctions", "Sanctions"):
        with pytest.raises(ValueError, match="unknown collection"):
            index_url(collection)


@pytest.mark.parametrize(
    ("body", "version", "entities_url"),
    [
        (
            {"version": "v1", "resources": INDEX["resources"]},
            "v1",
            f"{ARTIFACTS}/entities.ftm.json",
        ),
        ({"dataset": {"version": "v1"}, **INDEX}, "v1", f"{ARTIFACTS}/entities.ftm.json"),
        ({"version": 7}, None, f"{BASE_URL}/sanctions/entities.ftm.json"),  # latest path
    ],
)
def test_index_json_shapes(body: dict[str, Any], version: str | None, entities_url: str) -> None:
    info = IndexInfo.from_body(body, "sanctions", "u", ())
    assert (info.version, info.entities_url) == (version, entities_url)


@pytest.mark.network
def test_live_spike_streams_a_small_slice(tmp_path: Path) -> None:
    """Runs only when access.opensanctions allows it; skipped while it is none (G2, G7)."""
    route = read_access()
    try:
        require_access(route)
    except LicenceRequired as refusal:
        pytest.skip(f"access.opensanctions is {route}: {refusal}")
    with make_client() as client:
        result = run_spike(client, access=route, rows=10, root=tmp_path)
    assert result.stats.lines == 10
    assert result.index.version


def test_summary_lines_show_counts_only(client: HttpClient, tmp_path: Path) -> None:
    result = run_spike(client, access=Access.EXEMPT, root=tmp_path / "out")
    text = "\n".join(summary_lines(result))
    assert "version 20261015000000-syn" in text
    assert "(redirects: 307)" in text
    assert "read 12 lines" in text and "10 C1 records, 2 skipped" in text
    assert "C2 flags: PEP 1, RCA 1, Sanctioned 1" in text
    assert "dropped keys: target 10" in text
    assert "wrote nothing (access exempt writes nothing)" in text
    assert "Synthetic Person" not in text  # never names


def test_http_errors_name_the_url_and_status(
    server: SyntheticServer, client: HttpClient, tmp_path: Path
) -> None:
    with pytest.raises(HttpError, match=r"GET .*/peps/index.json: HTTP 404") as caught:
        run_spike(client, access=Access.EXEMPT, collection="peps", root=tmp_path)
    assert caught.value.status == 404
    assert server.requests == [f"{BASE_URL}/peps/index.json"]
