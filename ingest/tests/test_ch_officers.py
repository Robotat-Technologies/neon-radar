"""The officers step (PHASE-2.md M2.3c): gate, key, order, paging, budget, cache, retries, records.

The API is an `httpx.MockTransport` serving invented officers: `99` company numbers, `SYN`
officer ids and person numbers, `QQ` postcodes, the surnames checked under OD-12 for M2.3b and
company names from the demo-mini fixture. The clock is fake, so no test sleeps.
"""

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from followthemoney import ValueEntity, model
from typer.testing import CliRunner

from neonradar_contracts.records import Producer, iter_records, validate_files, write_manifest
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.build import build_dataset
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.sources import BuildError, BuildResult
from neonradar_ingest.sources.companies_house import build as ch_build
from neonradar_ingest.sources.companies_house import bulk, officers

DATASET, PROFILE, KEY = bulk.DATASET, "ch-test", "SYN-KEY"
NAMES = {
    "99000010": "BRACKEN DALE FREIGHT LTD",
    "99000020": "TANSY STRAND SUPPLIES LTD",
    "99000030": "LARCH MERE SERVICES LTD",
    "99000040": "HAZEL BRAE TEXTILES LTD",
}
# slice.csv order; 99000090 has no Company record, so it costs no request
SLICE = [("99000010", "seed", 0), ("99000020", "parent", 1), ("99000030", "child", 1),
         ("99000040", "district", 0), ("99000090", "district", 0)]  # fmt: skip
SERVICE = {"premises": "2", "address_line_1": "Test Lane", "locality": "Testtown",
           "postal_code": "QQ2 2BB", "country": "England"}  # fmt: skip
OTHER = {"premises": "4", "address_line_1": "Test Row", "locality": "Testtown",
         "postal_code": "QQ3 3CC", "country": "Wales"}  # fmt: skip


class Clock:
    """Wall and monotonic time in one: `sleep` moves it on and records the wait."""

    def __init__(self) -> None:
        self.now, self.waits = 1_800_000_000.0, list[float]()

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += max(seconds, 0.0)


class Api:
    """Each company's officer list; `script` answers first (429s, 5xx)."""

    def __init__(self, clock: Clock) -> None:
        self.clock, self.cap = clock, 100  # `cap`: a page size a gateway might enforce
        self.officers: dict[str, list[dict[str, Any]]] = {}
        self.totals: dict[str, int] = {}
        self.script: list[httpx.Response] = []
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.script:
            return self.script.pop(0)
        match = re.fullmatch(r"/company/(\w+)/officers", request.url.path)
        assert match, "only the company officer lists are called"
        items = self.officers.get(match[1])
        if items is None:
            return httpx.Response(404, json={"errors": [{"error": "company-profile-not-found"}]})
        start = int(request.url.params["start_index"])
        size = min(int(request.url.params["items_per_page"]), self.cap)
        total = self.totals.get(match[1], len(items))
        body = {"items": items[start : start + size], "total_results": total, "kind": "x"}
        return httpx.Response(200, json=body)

    def asked(self) -> list[tuple[str, int]]:
        return [(r.url.path.split("/")[2], int(r.url.params["start_index"])) for r in self.requests]


def officer(ident: str, name: str = "VELQASIMI, Zafer Nadim", **data: Any) -> dict[str, Any]:
    values = {
        "name": name,
        "officer_role": "director",
        "appointed_on": "2019-04-06",
        "date_of_birth": {"month": 3, "year": 1981},
        "nationality": "British,Syrian",
        "country_of_residence": "England",
        "person_number": f"SYN{ident}0001",
        "address": SERVICE,
        "links": {
            "self": f"/company/x/appointments/SYNAPPT{ident}",
            "officer": {"appointments": f"/officers/SYNOFF{ident}/appointments"},
        },
    }
    return {k: v for k, v in (values | data).items() if v is not None}


def corporate(ident: str, name: str, identification: dict[str, str], role: str) -> dict[str, Any]:
    item = officer(ident, name, officer_role=role, identification=identification)
    for key in ("date_of_birth", "nationality", "country_of_residence", "person_number"):
        item.pop(key)
    return item


def many(count: int, first: int = 100) -> list[dict[str, Any]]:
    surnames = ("ULVARAZI, Yazan", "ZUBEIRONO, Rakan", "QANDELOUNI, Nadim")
    return [officer(f"{n:05d}", surnames[n % 3]) for n in range(first, first + count)]


def profile(env: Any, **block: Any) -> None:
    officers_block = {"enabled": True, "request_budget": 100, "cache_days": 30} | block
    env.write_profile(
        PROFILE, real_data=True, sources={DATASET: {"enabled": True, "officers": officers_block}}
    )


def write(path: Path, lines: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    write_manifest(path, dataset=DATASET, producer=Producer(name="test", version="0"))


def previous(rows: list[tuple[str, str, int]] = SLICE) -> None:
    """slice.csv and the company records an earlier build left."""
    work = layout.work_dir(PROFILE, DATASET)
    work.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{n},{reason},{level}\n" for n, reason, level in rows)
    (work / "slice.csv").write_text("company_number,reason,level\n" + text, encoding="utf-8")
    lines = []
    for number, name in NAMES.items():
        entity = ValueEntity(model["Company"], {"id": f"gbch-co-{number}", "datasets": [DATASET]})
        entity.add("name", name)
        lines.append({**entity.to_dict(), "nr": {"v": "1.1", "source_ref": number}})
    write(layout.records_dir(PROFILE, DATASET) / "companies.ftm.jsonl", lines)


@pytest.fixture
def api(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> Api:
    """A real test profile on a machine where every check passes, with the key set."""
    clock = Clock()
    mock = Api(clock)
    network = officers.Network(httpx.MockTransport(mock), clock.sleep, clock.time, clock.time)
    monkeypatch.setattr(officers, "NETWORK", network)
    monkeypatch.setenv("CH_API_KEY", KEY)
    profile(data_env)
    data_env.allow_real(PROFILE, companies_house_key="available")
    previous()
    return mock


def strict(paths: list[Path]) -> int:
    return len(validate_files(paths, strict=True)[1])


def run(steps: tuple[str, ...] = ("officers",)) -> BuildResult:
    builder = sources.builder_for(DATASET)
    assert builder is not None
    project, chosen = load_project(), load_profile(PROFILE)
    return build_dataset(builder, chosen, project, strict, run_id="build-1", steps=steps)


def cli() -> Any:
    from neonradar_cli.main import app

    command = ["ingest", "build", "--profile", PROFILE, "--dataset", DATASET, "--step", "officers"]
    return CliRunner().invoke(app, command)


def records() -> dict[str, dict[str, Any]]:
    folder = layout.records_dir(PROFILE, DATASET)
    return {r["id"]: r for p in sorted(folder.glob("*.ftm.jsonl")) for r in iter_records(p)}


def test_gate_refuses_the_officers_step_before_any_request(data_env: Any, api: Api) -> None:
    cases = [
        (
            lambda: data_env.write_project(
                real_data_profiles=[], data_protection_filed=True, companies_house_key="available"
            ),
            f"{PROFILE} is not in access.real_data_profiles",
        ),
        (
            lambda: data_env.allow_real(PROFILE),  # access.companies_house_key stays pending
            "the officers API needs access.companies_house_key: available",
        ),
    ]
    for setup, message in cases:
        setup()
        result = cli()
        assert result.exit_code == 3, result.output
        assert message in result.output
        with pytest.raises(RealDataRefused, match=re.escape(message)):
            run()  # the step's own gate, without the CLI's
    assert api.requests == []
    assert not layout.officer_cache_dir().exists()


def test_missing_key_stops_the_officers_step_with_its_own_message(
    data_env: Any, api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CH_API_KEY")  # CI, CODESPACES: data_env removes them
    result = cli()
    assert result.exit_code == 2, result.output
    assert "CH_API_KEY is not set: the operator adds it to .env (OD-14)" in result.output
    assert api.requests == []
    assert not layout.officer_cache_dir().exists()


def test_slice_order_paging_until_total_results_and_the_rate(data_env: Any, api: Api) -> None:
    api.cap = 35  # a gateway that caps the page: the next page starts after the items received
    api.officers = {"99000010": [officer("00010")], "99000020": many(40), "99000040": []}
    api.totals = {"99000040": 2}  # a list that ends before its total; 99000030 answers 404
    result = run()
    assert api.asked() == [
        ("99000010", 0),
        ("99000020", 0),
        ("99000020", 35),
        ("99000030", 0),
        ("99000040", 0),
    ]
    first = api.requests[0]
    assert dict(first.url.params) == {"items_per_page": "100", "start_index": "0"}
    assert (
        first.headers["Authorization"] == "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()
    )
    counts = result.counts["officers"]
    assert counts["companies"] == {"complete": 3, "partial": 0, "not_reached": 0, "not_found": 1}
    assert (counts["requests"], counts["pages_fetched"], counts["cache_hits"]) == (5, 5, 0)
    assert counts["slice_companies_without_record"] == 1
    assert counts["lists_shorter_than_total"] == 1
    assert counts["seconds"] == 2.0  # 5 requests at 2 per second: 4 waits of 0.5 s
    assert result.strings["stopped_by"] == "done"
    assert counts["records"]["directorship"] == 41
    limiter_clock = Clock()
    limiter = officers.BudgetLimiter(
        2.0, 600, officers.Network(sleep=limiter_clock.sleep, monotonic=limiter_clock.time)
    )
    began = limiter_clock.now
    for _ in range(600):
        limiter.wait()
    assert limiter_clock.now - began == 299.5  # 600 requests take 5 minutes, never less
    with pytest.raises(officers.BudgetExhausted):
        limiter.wait()


def test_budget_stops_mid_company_and_the_rerun_finishes_from_the_cache(
    data_env: Any, api: Api
) -> None:
    profile(data_env, request_budget=2)
    api.cap = 35
    numbers = ["99000010", "99000020", "99000030", "99000040"]
    api.officers = {"99000010": [officer("00010")], "99000020": many(40),
                    "99000030": [officer("00030")], "99000040": [officer("00040")]}  # fmt: skip
    first = run()
    assert api.asked() == [("99000010", 0), ("99000020", 0)]  # the budget ends inside 99000020
    counts = first.counts["officers"]
    assert counts["companies"] == {"complete": 1, "partial": 1, "not_reached": 2, "not_found": 0}
    assert (counts["requests"], counts["request_budget"]) == (2, 2)
    assert first.strings["stopped_by"] == "budget"
    assert counts["records"]["directorship"] == 36  # what is in hand: 1 + 35
    cache = layout.officer_cache_dir()
    assert cache.is_relative_to(layout.real_root()) and cache in layout.dataset_dirs(DATASET)
    folders = sorted(p.name for p in cache.iterdir())
    digest = {n: hashlib.sha1(n.encode(), usedforsecurity=False).hexdigest()[:20] for n in numbers}
    assert folders == sorted(digest[n] for n in numbers[:2])
    assert not any(n in str(p) for p in cache.rglob("*") for n in numbers)

    profile(data_env, request_budget=3)
    api.requests.clear()
    second = run()
    assert api.asked() == [("99000020", 35), ("99000030", 0), ("99000040", 0)]
    counts = second.counts["officers"]
    assert counts["cache_hits"] == 2 and counts["requests"] == 3
    assert counts["companies"] == {"complete": 4, "partial": 0, "not_reached": 0, "not_found": 0}
    assert second.strings["stopped_by"] == "done"
    assert counts["records"]["directorship"] == 43
    assert sorted(p.name for p in (cache / digest["99000020"]).iterdir()) == ["0.json", "35.json"]

    api.requests.clear()
    assert run().counts["officers"]["cache_hits"] == 5 and api.requests == []  # all cached
    api.clock.now += 31 * officers.DAY  # older than cache_days: fetched again
    profile(data_env)  # a budget of 100
    stale = run().counts["officers"]
    assert (stale["cache_stale"], stale["requests"]) == (5, 5)
    profile(data_env, active_only=True)  # another query: the cached answers do not count
    api.requests.clear()
    active = run().counts["officers"]
    assert (active["cache_stale"], active["requests"]) == (5, 5)
    assert all(r.url.params["filter"] == "active" for r in api.requests)


def test_429_waits_for_the_reset_or_300_seconds(
    data_env: Any, api: Api, caplog: pytest.LogCaptureFixture
) -> None:
    previous([("99000010", "seed", 0), ("99000020", "seed", 0)])
    api.officers = {"99000010": [officer("00010")], "99000020": [officer("00020")]}
    reset = str(int(api.clock.now) + 42)
    api.script = [
        httpx.Response(429, headers={"X-Ratelimit-Reset": reset}),
        httpx.Response(429),
    ]
    counts = run().counts["officers"]
    assert api.clock.waits[:2] == [42.0, 300.0]
    assert (counts["rate_limit_waits"], counts["retries"], counts["requests"]) == (2, 2, 4)
    assert counts["companies"]["complete"] == 2
    messages = [record.getMessage() for record in caplog.records]
    assert any("HTTP 429; retry 1" in m for m in messages)
    assert not any("99000010" in m or "/company/" in m for m in messages)  # no company number


def test_5xx_retries_with_backoff_then_the_fetch_stops_and_reports(data_env: Any, api: Api) -> None:
    previous([("99000010", "seed", 0), ("99000020", "seed", 0)])
    api.officers = {"99000010": [officer("00010")], "99000020": [officer("00020")]}
    api.script = [httpx.Response(503)] * 4
    result = run()
    counts = result.counts["officers"]
    assert api.clock.waits == [1.0, 2.0, 4.0]  # backoff; the limiter never had to wait
    assert result.strings["stopped_by"] == "http_error" and counts["http_error_status"] == 503
    assert counts["companies"]["not_reached"] == 2 and counts["requests"] == 4
    api.requests.clear()
    again = run()  # a re-run continues
    assert again.counts["officers"]["companies"]["complete"] == 2
    assert again.strings["stopped_by"] == "done"


def test_records_officers_directorships_corporates_nominees_and_person_numbers(
    data_env: Any, api: Api
) -> None:
    uk = {"identification_type": "uk-limited-company", "legal_authority": "Companies Act 2006",
          "legal_form": "Private Limited Company", "place_registered": "Companies House",
          "registration_number": "99000050"}  # fmt: skip
    api.officers = {
        "99000010": [
            officer("00010"),
            officer(
                "00020", "ULVARAZI, Yazan", officer_role="nominee-director", person_number=None
            ),
            corporate("00030", "KESTREL SCAR FINANCE LTD", uk, "corporate-director"),
            corporate(
                "00040",
                "Synthetic Authority A",
                {"legal_form": "Partnership", "country_registered": "Syria"},
                "corporate-secretary",
            ),
        ],
        "99000020": [
            officer(
                "00010",
                officer_role="secretary",
                appointed_on="2021-01-01",
                address=OTHER,
                person_number="SYN000109999",
            ),
            corporate(
                "00050",
                "SORREL SIKE TRADING LTD",
                {"registration_number": "SYNF-1234", "country_registered": "France"},
                "corporate-nominee-secretary",
            ),
            corporate(
                "00060",
                "UMBER GARTH FOODS LTD",
                {"registration_number": "N/A", "place_registered": "Companies House"},
                "corporate-director",
            ),
        ],
    }
    counts = run().counts["officers"]
    found = records()
    person = found["gbch-off-SYNOFF00010"]
    props = person["properties"]
    assert person["schema"] == "Person"
    assert (props["name"], props["firstName"], props["lastName"]) == (
        ["VELQASIMI, Zafer Nadim"], ["Zafer Nadim"], ["VELQASIMI"]
    )  # fmt: skip
    assert (props["birthDate"], sorted(props["nationality"]), props["country"]) == (
        ["1981-03"], ["gb", "sy"], ["gb"]
    )  # fmt: skip
    assert person["nr"]["ch_person_number"] == "SYN000100001"  # unchanged; D3 reads 8 of it
    assert sorted(person["nr"]["address_roles"].values()) == ["service", "service"]
    assert sorted(props["addressEntity"]) == sorted(person["nr"]["address_roles"])
    assert "ch_person_number" not in found["gbch-off-SYNOFF00020"]["nr"]
    links = {r["id"]: r for r in found.values() if r["schema"] == "Directorship"}
    digest = hashlib.sha1(
        b"SYNOFF00010|99000010|director|2019-04-06", usedforsecurity=False
    ).hexdigest()[:20]
    link = links[f"gbch-directorship-{digest}"]
    assert link["properties"]["director"] == ["gbch-off-SYNOFF00010"]
    assert link["properties"]["organization"] == ["gbch-co-99000010"]
    assert (link["properties"]["startDate"], link["nr"]["is_nominee"]) == (["2019-04-06"], False)
    of_person = [r for r in links.values() if r["properties"]["director"] == [person["id"]]]
    assert sorted(r["properties"]["role"][0] for r in of_person) == ["director", "secretary"]
    nominees = {r["properties"]["director"][0] for r in links.values() if r["nr"]["is_nominee"]}
    assert nominees == {"gbch-off-SYNOFF00020", "gbch-off-SYNOFF00050"}

    def shape(ident: str) -> tuple[str, list[str], list[str]]:
        record = found[f"gbch-off-SYNOFF{ident}"]
        values = record["properties"]
        return record["schema"], values.get("registrationNumber", []), values["jurisdiction"]

    assert shape("00030") == ("Company", ["99000050"], ["gb"])
    assert shape("00040") == ("LegalEntity", [], ["sy"])
    assert shape("00050") == ("Company", ["SYNF-1234"], ["fr"])
    assert shape("00060") == ("Company", [], ["gb"])  # a UK registry, a number D1 cannot read
    assert counts["records"] == {
        "address": 2, "company": 3, "directorship": 7, "legalentity": 1, "person": 2
    }  # fmt: skip
    assert (counts["person_numbers"], counts["person_numbers_not_12_digits"]) == (2, 2)
    assert (counts["person_number_conflicts"], counts["corporate_uk_numbers_invalid"]) == (1, 1)
    assert counts["roles_by_value"]["director"] == 1


def test_unmapped_personal_fields_never_reach_records_or_the_summary(
    data_env: Any, api: Api
) -> None:
    sentinel = {
        "usual_residential_address": {"premises": "SENTINELHOME", "postal_code": "QQ9 9ZZ"},
        "date_of_birth": {"day": 17, "month": 3, "year": 1981},
        "occupation": "SENTINELJOB",
        "former_names": [{"forenames": "SENTINELFORMER", "surname": "ZUBEIRONO"}],
        "identity_verification_details": {"SENTINELIDV": "x"},
        "contact_details": {"contact_name": "SENTINELCONTACT"},
        "address": SERVICE | {"care_of": "SENTINELCARE"},
    }
    api.officers = {"99000010": [officer("00010", **sentinel)]}
    result = cli()
    assert result.exit_code == 0, result.output
    summary = next(layout.reports_dir(PROFILE).glob("ingest-build-*.json")).read_text()
    folder = layout.records_dir(PROFILE, DATASET)
    texts = [summary, result.output, *(p.read_text() for p in folder.iterdir())]
    for text in texts:
        assert "SENTINEL" not in text and "QQ9" not in text and "1981-03-17" not in text
    for text in (summary, result.output):
        assert not re.search(r"Velqasimi|VELQASIMI|Zafer|SYNOFF|SYN0|99000010|BRACKEN", text)
    ch = json.loads(summary)["datasets"][DATASET]
    assert ch["stopped_by"] == "done" and ch["officers"]["companies"]["complete"] == 1
    assert records()["gbch-off-SYNOFF00010"]["properties"]["birthDate"] == ["1981-03"]


def test_profile_block_steps_and_the_records_an_officers_step_keeps(
    data_env: Any, api: Api
) -> None:
    profile(data_env, appointments=True)
    with pytest.raises(ValueError, match="appointments must be false"):
        load_profile(PROFILE)
    for name, budget in (("uk-tiny", 1500), ("uk-sample", 20_000)):
        block = load_profile(name).options(DATASET).officers
        assert block is not None and block.enabled and block.request_budget == budget
        assert (block.cache_days, block.appointments, block.active_only) == (30, False, False)
    profile(data_env, enabled=False)
    assert "officers" not in ch_build.plan(load_profile(PROFILE), ())
    with pytest.raises(BuildError, match="officers block is not enabled"):
        run()
    profile(data_env)
    assert ch_build.plan(load_profile(PROFILE), ())[-1] == "officers"
    psc = ValueEntity(model["Person"], {"id": "gbch-psc-SYNP1", "datasets": [DATASET]})
    psc.add("name", "Rakan Zubeirono")
    write(layout.records_dir(PROFILE, DATASET) / "psc.ftm.jsonl", [{**psc.to_dict()}])
    api.officers = {"99000010": [officer("00010")]}
    run()
    folder = layout.records_dir(PROFILE, DATASET)
    assert sorted(p.name for p in folder.glob("*.ftm.jsonl")) == [
        "companies.ftm.jsonl", "officers.ftm.jsonl", "psc.ftm.jsonl"
    ]  # fmt: skip
    (layout.work_dir(PROFILE, DATASET) / "slice.csv").unlink()
    with pytest.raises(BuildError, match="run --step slice first"):
        run()
