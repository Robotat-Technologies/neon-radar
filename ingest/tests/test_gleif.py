import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from neonradar_contracts.records import validate_batch, validate_record
from neonradar_ingest.http import HttpClient, HttpError, RateLimiter
from neonradar_ingest.sources import gleif
from neonradar_ingest.sources.gleif.client import COVERAGE
from neonradar_ingest.sources.gleif.mapping import entity_id, ownership_id

FIXTURE = Path(__file__).parent / "fixtures" / "gleif" / "responses.json"
CHILD, PARENT, APEX, JOINED = (f"SYN0000000000000{n}" for n in ("0128", "0225", "0322", "0419"))


def key(request: httpx.Request) -> str:
    path = request.url.path.removeprefix("/api/v1/")
    query = "&".join(f"{k}={v}" for k, v in sorted(request.url.params.multi_items()))
    return f"{path}?{query}" if query else path


def synthetic_api(
    seen: list[str] | None = None,
    replace: dict[str, list[httpx.Response]] | None = None,
    sleeps: list[float] | None = None,
) -> HttpClient:
    """The GLEIF client over the synthetic responses; any other request is a 404.

    `replace` maps a request key to responses sent first, one per request. Every link in the
    fixture points at links.example.invalid, so a client that followed one would fail here.
    """
    responses: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))["responses"]

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.gleif.org", f"request to {request.url}"
        if seen is not None:
            seen.append(key(request))
        if replace and replace.get(key(request)):
            return replace[key(request)].pop(0)
        body = responses.get(key(request))
        return httpx.Response(200, json=body) if body else httpx.Response(404, json={})

    limiter = RateLimiter(1.0, sleep=lambda seconds: None)
    sleep = sleeps.append if sleeps is not None else (lambda seconds: None)
    return gleif.make_client(limiter=limiter, transport=httpx.MockTransport(handle), sleep=sleep)


@pytest.mark.parametrize(
    ("raw", "normalised"),
    [("1800000", "01800000"), (" sc045551 ", "SC045551"), ("NI 741128", "NI741128")],
)
def test_normalises_company_numbers_as_companies_house_writes_them(
    raw: str, normalised: str
) -> None:
    assert gleif.normalise_company_number(raw) == normalised


def test_fetches_the_record_its_parents_their_exceptions_children_and_the_join() -> None:
    seen: list[str] = []
    with synthetic_api(seen) as client:
        result = gleif.run_spike(client, CHILD)
    pairs = [(child, level) for child in (CHILD, PARENT, APEX) for level in ("direct", "ultimate")]
    assert [(link.child, link.level) for link in result.links] == pairs
    assert [link.parent["id"] for link in result.links if link.parent] == [PARENT, APEX]
    assert [link.reported for link in result.links[2:4]] == [True, True]  # not followed
    assert result.links[4].exception and result.links[4].exception["reason"] == "NATURAL_PERSONS"
    assert (result.children, result.join_number) == (3, "ZZ000001")
    assert [data["id"] for data in result.join] == [CHILD]
    assert result.publish_date == "2026-10-21T00:00:00Z"
    assert not any(f"{PARENT}/direct-parent" in path for path in seen)  # one level up: links only
    assert len(seen) == len(result.urls) == 9
    assert all(url.startswith("https://api.gleif.org/api/v1/lei-records") for url in result.urls)


def test_maps_to_c1_records_that_validate_in_strict_mode() -> None:
    with synthetic_api() as client:
        result = gleif.run_spike(client, CHILD)
    records, notes = gleif.build_records(result)
    by_id = {record["id"]: record for record in records}
    assert [issue for record in records for issue in validate_record(record)] == []
    assert validate_batch(records, strict=True) == []
    child = by_id[entity_id(CHILD)]
    assert child["id"] == f"gleif-lei-{CHILD}" and child["datasets"] == ["gleif_lei"]
    assert child["properties"]["leiCode"] == [CHILD]
    assert child["properties"]["registrationNumber"] == ["ZZ000001"]
    assert child["properties"]["jurisdiction"] == ["gb"]
    assert child["properties"]["alias"] == ["SYNTHETIC CHILD TRADING"]
    assert child["properties"]["previousName"] == ["SYNTHETIC CHILD EXAMPLE PUBLIC LIMITED COMPANY"]
    roles = {f"gleif-addr-{CHILD}-legal": "registered", f"gleif-addr-{CHILD}-hq": "business"}
    assert child["nr"] == {"v": "1.0", "source_ref": CHILD, "address_roles": roles}
    assert by_id[f"gleif-addr-{CHILD}-legal"]["properties"]["full"] == [
        "0 Synthetic Example Road, Exampleton, ZZ0 0ZZ, GB"
    ]
    apex = by_id[entity_id(APEX)]["properties"]
    assert apex["name"] == ["شركة المثال الاصطناعية القابضة"]  # original script kept
    assert apex["alias"] == ["SYNTHETIC APEX EXAMPLE HOLDINGS"]  # the AUTO one is not written
    assert "registrationNumber" not in apex
    direct = by_id[ownership_id(CHILD, PARENT, "direct")]
    assert re.fullmatch(r"gleif-ownership-[0-9a-f]{20}", direct["id"])
    assert direct["properties"]["owner"] == [entity_id(PARENT)]
    assert direct["properties"]["asset"] == [entity_id(CHILD)]
    assert direct["properties"]["startDate"] == ["2020-01-01"]
    assert direct["nr"]["consolidation"] == "direct"
    ultimate = by_id[ownership_id(CHILD, APEX, "ultimate")]
    assert (ultimate["nr"]["consolidation"], ultimate["properties"]["endDate"]) == (
        "ultimate",
        ["2030-12-31"],
    )
    assert sorted(record["schema"] for record in records).count("Company") == 3
    category = "DIRECT_ACCOUNTING_CONSOLIDATION_PARENT"
    assert f"{APEX} direct parent: reporting exception {category}, reason NATURAL_PERSONS" in notes
    assert f"{PARENT} direct parent: reported with an LEI, not fetched" in " ".join(notes)
    assert "names not written: 1 AUTO_ASCII_TRANSLITERATED_LEGAL_NAME" in notes
    assert not any("free text" in note for note in notes)  # exception references stay out


def test_joins_another_number_and_prints_the_result() -> None:
    with synthetic_api() as client:
        result = gleif.run_spike(client, CHILD, ch_number="zz 000004")
    assert [data["id"] for data in result.join] == [JOINED]
    records, _ = gleif.build_records(result)
    assert entity_id(JOINED) in {record["id"] for record in records}
    lines = gleif.summary_lines(result)
    assert lines[0] == f"record {CHILD}: SYNTHETIC CHILD EXAMPLE LIMITED"
    assert f"  {CHILD} direct parent: {PARENT} SYNTHETIC PARENT EXAMPLE PLC" in lines[2]
    assert lines[-1] == (
        f"join: Companies House ZZ000004 -> {JOINED} at RA000587; spike record matched: no;"
        " expected authority RA000585"
    )


def test_a_record_with_exceptions_and_no_companies_house_number_skips_the_join() -> None:
    with synthetic_api() as client:
        result = gleif.run_spike(client, APEX)
    assert [link.exception is not None for link in result.links] == [True, True]
    assert (result.join_number, result.children) == (None, 1)
    assert "join: skipped (no Companies House number)" in gleif.build_records(result)[1]


def test_unknown_or_malformed_leis_and_outages_fail_clearly() -> None:
    with synthetic_api() as client:
        with pytest.raises(LookupError, match="no LEI record"):
            gleif.run_spike(client, "SYN00000000000000516")
        with pytest.raises(ValueError, match="not an LEI"):
            gleif.run_spike(client, "../lei-records")
    sleeps: list[float] = []
    outage = httpx.MockTransport(lambda request: httpx.Response(503))
    limiter = RateLimiter(1.0, sleep=lambda seconds: None)
    client = gleif.make_client(limiter=limiter, transport=outage, sleep=sleeps.append)
    with client, pytest.raises(HttpError, match="failed after 4 attempt"):
        gleif.run_spike(client, CHILD)
    assert sleeps == [1.0, 2.0, 4.0]


def test_coverage_counts_each_query_with_one_record_per_page() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.params["page[size]"] == "1"
        total = len(str(request.url.params))  # any number that differs per query
        return httpx.Response(200, json={"meta": {"pagination": {"total": total}}, "data": []})

    limiter = RateLimiter(1.0, sleep=lambda seconds: None)
    with gleif.make_client(limiter=limiter, transport=httpx.MockTransport(handle)) as client:
        counts = gleif.coverage(client)
    assert list(counts) == list(COVERAGE) and len(set(counts.values())) > 1


def test_a_linked_record_or_exception_that_answers_404_is_reported_first() -> None:
    gone = {
        f"lei-records/{CHILD}/direct-parent": [httpx.Response(404, json={})],
        f"lei-records/{APEX}/ultimate-parent-reporting-exception": [httpx.Response(404, json={})],
    }
    with synthetic_api(replace=gone) as client:
        result = gleif.run_spike(client, CHILD)
    assert [(link.child, link.level, link.missing) for link in result.links] == [
        (CHILD, "direct", True),
        (CHILD, "ultimate", False),
        (APEX, "direct", False),
        (APEX, "ultimate", True),
    ]
    records, notes = gleif.build_records(result)
    assert f"{CHILD} direct parent: linked, but GLEIF answered 404" in notes
    assert f"{APEX} ultimate parent: linked, but GLEIF answered 404" in notes
    assert ownership_id(CHILD, PARENT, "direct") not in {record["id"] for record in records}
    assert validate_batch(records, strict=True) == []
    assert (
        gleif.summary_lines(result)[2] == f"  {CHILD} direct parent: linked, but GLEIF answered 404"
    )


@pytest.mark.parametrize(("headers", "waited"), [({"Retry-After": "2"}, [2.0]), ({}, [60.0])])
def test_a_429_waits_what_gleif_asks_or_a_minute(
    headers: dict[str, str], waited: list[float]
) -> None:
    sleeps: list[float] = []
    busy = {f"lei-records/{CHILD}": [httpx.Response(429, headers=headers)]}
    with synthetic_api(replace=busy, sleeps=sleeps) as client:
        assert gleif.run_spike(client, CHILD).record["id"] == CHILD
    assert sleeps == waited


def test_a_wait_over_max_wait_fails_instead_of_waiting() -> None:
    sleeps: list[float] = []
    busy = {f"lei-records/{CHILD}": [httpx.Response(429, headers={"Retry-After": "121"})]}
    client = synthetic_api(replace=busy, sleeps=sleeps)
    with client, pytest.raises(HttpError, match="asked to wait 121 s"):
        gleif.run_spike(client, CHILD)
    assert sleeps == []


def test_redirects_are_never_followed() -> None:
    seen: list[str] = []
    target = "https://links.example.invalid/elsewhere?token=secret"
    moved = {f"lei-records/{CHILD}": [httpx.Response(302, headers={"Location": target})]}
    client = synthetic_api(seen, replace=moved)
    with client, pytest.raises(HttpError, match=r"302 redirect to .* never followed") as error:
        gleif.run_spike(client, CHILD)
    assert seen == [f"lei-records/{CHILD}"]
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [{"meta": {}}, {"data": None}, {"data": {"id": CHILD, "attributes": {}}}, ["not", "a", "body"]],
)
def test_unexpected_shapes_fail_cleanly(body: Any) -> None:
    odd = {f"lei-records/{CHILD}": [httpx.Response(200, json=body)]}
    client = synthetic_api(replace=odd)
    with client, pytest.raises(HttpError, match=r"unexpected response shape|not a JSON:API object"):
        gleif.run_spike(client, CHILD)


def test_null_relationships_mean_no_parent_links() -> None:
    body = json.loads(FIXTURE.read_text(encoding="utf-8"))["responses"][f"lei-records/{CHILD}"]
    body["data"]["relationships"] = None
    with synthetic_api(
        replace={f"lei-records/{CHILD}": [httpx.Response(200, json=body)]}
    ) as client:
        result = gleif.run_spike(client, CHILD)
    assert [(link.reported, link.missing, link.parent) for link in result.links] == [
        (False, False, None),
        (False, False, None),
    ]
