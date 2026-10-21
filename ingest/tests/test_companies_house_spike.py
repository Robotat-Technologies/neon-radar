"""The Companies House spike end to end over httpx.MockTransport (M1.8a); no network."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from neonradar_contracts.records import Manifest, manifest_path, validate_files
from neonradar_ingest.http import RateLimiter
from neonradar_ingest.sources.companies_house.client import BASE_URL, CompaniesHouseClient
from neonradar_ingest.sources.companies_house.spike import CompanyNotFound, SpikeResult, run_spike

FIXTURES = Path(__file__).parent / "fixtures" / "companies_house"
OFFICER_PAGES = {0: "officers-SYN00001-1.json", 3: "officers-SYN00001-2.json"}


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def serve(request: httpx.Request) -> httpx.Response:
    path, start = request.url.path, int(request.url.params.get("start_index", "0"))
    if path == "/company/SYN00001":
        return httpx.Response(200, json=load("company-SYN00001.json"))
    if path == "/company/SYN00001/officers" and start in OFFICER_PAGES:
        return httpx.Response(200, json=load(OFFICER_PAGES[start]))
    if path == "/company/SYN00001/persons-with-significant-control" and start == 0:
        return httpx.Response(200, json=load("psc-SYN00001.json"))
    return httpx.Response(404, json={"errors": [{"error": "not-found"}]})


def client() -> CompaniesHouseClient:
    limiter = RateLimiter(1.0, clock=lambda: 0.0, sleep=lambda seconds: None)
    return CompaniesHouseClient("SYN-KEY", transport=httpx.MockTransport(serve), limiter=limiter)


def spike(root: Path, company: str = "syn00001", **kwargs: int) -> SpikeResult:
    when = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)
    return run_spike(client(), company, root=root, now=lambda: when, **kwargs)


def test_the_spike_writes_valid_records_and_a_manifest(tmp_path: Path) -> None:
    result = spike(tmp_path)
    assert result.records_path.parent == tmp_path / "companies_house"
    assert re.fullmatch(r"gb_companies_house-\d{8}-SYN00001\.ftm\.jsonl", result.records_path.name)
    counts, issues = validate_files([result.records_path], strict=True)
    assert issues == []
    assert counts == {
        "Address": 1,
        "Company": 3,
        "Control": 4,
        "Directorship": 5,
        "LegalEntity": 1,
        "Ownership": 2,
        "Person": 4,
    }
    text = manifest_path(result.records_path).read_text(encoding="utf-8")
    manifest = Manifest.model_validate_json(text)
    assert (manifest.dataset, manifest.licence.id) == ("gb_companies_house", "OGL-UK-3.0")
    assert manifest.producer.name == "neonradar_ingest.sources.companies_house"
    assert manifest.files[0].records == result.records == 20
    assert manifest.counts.skipped == {"psc:super-secure-person-with-significant-control": 1}
    assert manifest.source.retrieved_at == "2026-10-21T09:30:00Z"
    assert manifest.source.urls[0] == f"{BASE_URL}/company/SYN00001"
    assert result.requests == 4  # profile, two officer pages, one PSC page
    lines = [json.loads(line) for line in result.records_path.read_text("utf-8").splitlines()]
    assert lines == load("records-SYN00001.expected.json")


def test_the_summary_has_counts_and_field_names_but_no_register_values(tmp_path: Path) -> None:
    text = "\n".join(spike(tmp_path).summary())
    assert "officer appointments: 5 (1 corporate, 20%)" in text
    assert "'SURNAME, Forenames': 4 of 4 (100%)" in text
    assert "pages: officers 2, persons-with-significant-control 1; status codes: 200 4" in text
    assert "psc.appointment_verification_start_on 2" in text
    for value in ("QANDELOUNI", "Qandelouni", "QUILLON", "Example Street", "1979", "SYNoff"):
        assert value not in text


def test_max_pages_truncates_and_says_so(tmp_path: Path) -> None:
    result = spike(tmp_path, max_pages=1)
    note = "officers: stopped after 1 page(s), 3 of 5 items"
    assert note in result.notes
    assert note in json.loads(manifest_path(result.records_path).read_text("utf-8"))["notes"]


def test_a_new_run_replaces_earlier_output_for_the_same_company(tmp_path: Path) -> None:
    folder = tmp_path / "companies_house"
    folder.mkdir()
    (folder / "gb_companies_house-20261001-SYN00001.ftm.jsonl").write_text("{}\n")
    (folder / "gb_companies_house-20261001-SYN00001.manifest.json").write_text("{}")
    (folder / "gb_companies_house-20261001-SYN00002.ftm.jsonl").write_text("")
    result = spike(tmp_path)
    names = sorted(path.name for path in folder.iterdir())
    assert names == [
        "gb_companies_house-20261001-SYN00002.ftm.jsonl",
        result.records_path.name,
        manifest_path(result.records_path).name,
    ]


def test_an_unknown_company_raises_and_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(CompanyNotFound, match="SYN00404"):
        spike(tmp_path, company="SYN00404")
    assert not (tmp_path / "companies_house").exists()


@pytest.mark.parametrize("number", ["../SYN00001", "SYN0000/1", "", "SYN00001-X"])
def test_a_company_number_that_is_not_letters_and_digits_is_refused(
    tmp_path: Path, number: str
) -> None:
    with pytest.raises(ValueError, match="letters and digits"):
        spike(tmp_path, company=number)
