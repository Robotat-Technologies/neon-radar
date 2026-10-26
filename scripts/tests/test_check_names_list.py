"""scripts/check_names_list.py: the OD-12 check of a hand-written name list.

The Companies House client runs over httpx.MockTransport (no network). Every name is synthetic
and already checked under OD-12 (contracts/CHANGELOG.md, contracts/examples/c1/).
"""

import base64
from collections.abc import Callable
from pathlib import Path

import check_names_ch
import check_names_list
import httpx
import pytest
from check_names_list import ListError, Name, check, default_kind, main, read_names

from neonradar_ingest.http import RateLimiter
from neonradar_ingest.sources.companies_house.client import (
    REQUESTS_PER_SECOND,
    CompaniesHouseClient,
)

Handler = Callable[[httpx.Request], httpx.Response]
KEY = "SYN-KEY-0001"

# Titles the fake search returns, by path and query.
COMPANIES = {
    "Plover Brae Textiles Ltd": ["PLOVER BRAE TEXTILES LIMITED"],  # same key: a match
    "Fenwhistle Holdings Ltd": ["FENWHISTLE HOLDINGS (NORTH) LTD"],  # another key
    "Plover Brae": ["PLOVER BRAE LTD"],
}
OFFICERS = {
    "Yazan Zafer Velqasimi": ["VELQASIMI, Yazan Zafer Omar"],  # every token among the title's
    "Rakan Zubeirono": ["ZUBEIRONO, Rana"],  # "rakan" is missing
}


def fake_search(seen: list[httpx.Request]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        table = COMPANIES if request.url.path == "/search/companies" else OFFICERS
        titles = table.get(request.url.params["q"], [])
        return httpx.Response(200, json={"items": [{"title": t} for t in titles]})

    return handler


def fake_client(handler: Handler, key: str = KEY) -> CompaniesHouseClient:
    return CompaniesHouseClient(
        key,
        transport=httpx.MockTransport(handler),
        limiter=RateLimiter(REQUESTS_PER_SECOND, clock=lambda: 0.0, sleep=lambda s: None),
        sleep=lambda s: None,
    )


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "names.txt"
    path.write_text(text, encoding="utf-8")
    return path


class Terminal:
    def isatty(self) -> bool:
        return True


class Pipe:
    def isatty(self) -> bool:
        return False


def test_the_list_skips_comments_and_blank_lines_and_keeps_the_source(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "# synthetic: true\n"
        "\n"
        "Plover Brae Textiles Ltd  # p3/m3-2\n"
        "Yazan Zafer Velqasimi\tperson\t# p2/m2-6a\n"
        "  Plover Brae\tplace  \n"
        "PLOVER BRAE TEXTILES LTD  # the same fold, checked once\n",
    )
    assert read_names(path) == [
        Name("Plover Brae Textiles Ltd", "company", "p3/m3-2"),
        Name("Yazan Zafer Velqasimi", "person", "p2/m2-6a"),
        Name("Plover Brae", "place", ""),
    ]


def test_without_a_kind_a_legal_form_makes_a_company() -> None:
    assert default_kind("Fenwhistle Holdings Ltd") == "company"
    assert default_kind("QUILLON MARSH TRADING LIMITED") == "company"
    assert default_kind("Yazan Zafer Velqasimi") == "person"


@pytest.mark.parametrize("line", ["Yazan Zafer Velqasimi\tvessel", "\tperson"])
def test_a_bad_line_is_named_by_its_number_only(tmp_path: Path, line: str) -> None:
    with pytest.raises(ListError, match=r"^line 2: ") as error:
        read_names(write(tmp_path, f"# synthetic: true\n{line}\n"))
    assert "Velqasimi" not in str(error.value)


def test_flags_use_the_company_key_and_the_officer_tokens() -> None:
    seen: list[httpx.Request] = []
    names = [
        Name("Plover Brae Textiles Ltd", "company", ""),
        Name("Fenwhistle Holdings Ltd", "company", ""),
        Name("Yazan Zafer Velqasimi", "person", ""),
        Name("Rakan Zubeirono", "person", ""),
    ]
    with fake_client(fake_search(seen)) as client:
        results = [check_names_ch._flags(client, check_names_ch.Query(
            n.kind, "", "fixed", "name", "", n.text)) for n in names]  # fmt: skip
    assert results == [(True, False), (False, False), (False, True), (False, False)]
    assert {r.url.path for r in seen} == {"/search/companies", "/search/officers"}
    assert {r.url.params["items_per_page"] for r in seen} == {"20"}


def test_the_run_prints_flags_by_index_and_never_a_name(capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[httpx.Request] = []
    names = [
        Name("Plover Brae Textiles Ltd", "company", "p3/m3-2"),
        Name("Yazan Zafer Velqasimi", "person", "p2/m2-6a"),
        Name("Plover Brae", "place", "p3/m3-3"),
        Name("Зафир Канделуни", "person", "main"),
        Name("Fenwhistle Holdings Ltd", "company", "p2/m2-12"),
    ]
    with fake_client(fake_search(seen)) as client:
        assert check(names, client) == 1
    out = capsys.readouterr().out
    assert out.splitlines() == [
        "0000\tcompany=1\tofficer=0",
        "0001\tcompany=0\tofficer=1",
        "0002\tcompany=1\tofficer=0",
        "0003\tskipped=script",
        "0004\tcompany=0\tofficer=0",
        "5 names; 2 company or person names match (rename them, OD-12); 1 places match (check"
        " that the place is invented); 1 not in Latin script (not sent); 8 requests",
    ]
    for name in names:
        assert name.text.casefold() not in out.casefold()
    assert all("Зафир" not in r.url.params["q"] for r in seen)  # the Cyrillic name is never sent


def test_a_place_match_alone_does_not_break_the_rule(capsys: pytest.CaptureFixture[str]) -> None:
    with fake_client(fake_search([])) as client:
        assert check([Name("Plover Brae", "place", "")], client) == 0
    assert "0 company or person names match" in capsys.readouterr().out


def test_list_prints_the_numbered_names_and_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_client(*args: object, **kwargs: object) -> None:
        raise AssertionError("--list must not build a client")

    monkeypatch.setattr(check_names_list, "CompaniesHouseClient", no_client)
    monkeypatch.setattr("sys.stdin", Pipe())  # --list needs no terminal
    path = write(tmp_path, "Plover Brae Textiles Ltd  # p3/m3-2\nYazan Zafer Velqasimi\tperson\n")
    assert main([str(path), "--list"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "0000\tcompany\tPlover Brae Textiles Ltd\tp3/m3-2",
        "0001\tperson\tYazan Zafer Velqasimi\t",
    ]


def test_it_refuses_without_a_terminal_before_reading_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_settings() -> None:
        raise AssertionError("the key must not be read")

    monkeypatch.setattr(check_names_list, "IngestSettings", no_settings)
    monkeypatch.setattr("sys.stdin", Pipe())
    assert main([str(write(tmp_path, "Yazan Zafer Velqasimi\n"))]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "run it yourself in a terminal" in captured.err


def test_a_missing_key_stops_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class NoKey:
        def companies_house_key(self) -> None:
            return None

    monkeypatch.setattr(check_names_list, "IngestSettings", NoKey)
    monkeypatch.setattr("sys.stdin", Terminal())
    assert main([str(write(tmp_path, "Yazan Zafer Velqasimi\n"))]) == 2
    assert "CH_API_KEY is not set" in capsys.readouterr().err


def test_in_a_terminal_it_uses_the_key_from_the_environment_and_never_prints_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[httpx.Request] = []
    monkeypatch.setenv("CH_API_KEY", KEY)
    monkeypatch.setattr("sys.stdin", Terminal())
    monkeypatch.setattr(
        check_names_list, "CompaniesHouseClient", lambda key: fake_client(fake_search(seen), key)
    )
    path = write(tmp_path, "Rakan Zubeirono\tperson  # p2/m2-6c\n")
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "0000\tcompany=0\tofficer=0"
    assert KEY not in out
    expected = "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()
    assert seen and all(r.headers["Authorization"] == expected for r in seen)


def test_a_failed_search_stops_with_its_status_and_never_the_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refused(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid Authorization"})

    monkeypatch.setenv("CH_API_KEY", KEY)
    monkeypatch.setattr("sys.stdin", Terminal())
    monkeypatch.setattr(check_names_list, "CompaniesHouseClient", lambda key: fake_client(refused))
    assert main([str(write(tmp_path, "Rakan Zubeirono\tperson\n"))]) == 2
    captured = capsys.readouterr()
    assert "HTTP 401" in captured.err
    for text in (captured.out, captured.err):
        assert "Zubeirono" not in text
        assert KEY not in text


def test_an_unreadable_file_is_reported_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "missing.txt"), "--list"]) == 2
    assert capsys.readouterr().err.startswith("check_names_list: ")
