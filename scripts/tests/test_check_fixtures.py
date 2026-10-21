import json
from typing import TYPE_CHECKING

import check_fixtures
import pytest

if TYPE_CHECKING:
    from conftest import GitRepo

SYNTHETIC = {
    "id": "syn-co-0001",
    "schema": "Company",
    "datasets": ["nr_synthetic"],
    "properties": {"name": ["syn placeholder 0001"]},
    "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"},
}


def jsonl(*records: dict[str, object]) -> str:
    return "".join(json.dumps(record) + "\n" for record in records)


def run(repo: "GitRepo") -> int:
    repo.run("add", "-A")
    return check_fixtures.main(["--root", str(repo.path)])


@pytest.mark.parametrize(
    "path",
    [
        "data/fixtures/demo-mini/nr_synthetic-20261023-demo-mini.ftm.jsonl",
        "contracts/examples/c1/demo.ftm.jsonl",
        "graph/tests/fixtures/small.ftm.jsonl",
    ],
)
def test_synthetic_records_pass(git_repo: "GitRepo", path: str) -> None:
    git_repo.write(path, jsonl(SYNTHETIC, {**SYNTHETIC, "id": "syn-co-0002"}) + "\n")
    assert run(git_repo) == 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "gbch-co-T0000001"}, "does not start with 'syn-'"),
        ({"datasets": ["gb_companies_house"]}, "not ['nr_synthetic']"),
        ({"datasets": ["nr_synthetic", "gleif_lei"]}, "not ['nr_synthetic']"),
        ({"nr": {"v": "1.0"}}, "nr.synthetic is not true"),
        ({"nr": {"v": "1.0", "synthetic": "true"}}, "nr.synthetic is not true"),
    ],
)
def test_real_looking_records_fail(
    git_repo: "GitRepo", change: dict[str, object], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    git_repo.write("data/fixtures/x.ftm.jsonl", jsonl(SYNTHETIC, {**SYNTHETIC, **change}))
    assert run(git_repo) == 1
    output = capsys.readouterr().out
    assert "data/fixtures/x.ftm.jsonl:2" in output
    assert message in output


def test_record_without_nr_fails(git_repo: "GitRepo") -> None:
    record = {key: value for key, value in SYNTHETIC.items() if key != "nr"}
    git_repo.write("data/fixtures/x.ftm.jsonl", jsonl(record))
    assert run(git_repo) == 1


def test_invalid_json_fails(git_repo: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    git_repo.write("data/fixtures/x.ftm.jsonl", jsonl(SYNTHETIC) + "{not json\n")
    assert run(git_repo) == 1
    assert "x.ftm.jsonl:2: not valid JSON" in capsys.readouterr().out


def test_invalid_golden_examples_are_exempt(git_repo: "GitRepo") -> None:
    git_repo.write(
        "contracts/examples/c1/invalid/r1-bad-prefix.ftm.jsonl",
        jsonl({**SYNTHETIC, "id": "gbch-co-1"}),
    )
    assert run(git_repo) == 0


def test_untracked_files_are_ignored(git_repo: "GitRepo") -> None:
    git_repo.write("data/fixtures/x.ftm.jsonl", jsonl({**SYNTHETIC, "id": "gbch-co-1"}))
    assert check_fixtures.main(["--root", str(git_repo.path)]) == 0


@pytest.mark.parametrize(
    "content",
    [
        "# synthetic: true\ntx_id,scenario_id,is_illicit\nsyn-payment-1,s1,false\n",
        "synthetic,company_id,company_name\ntrue,onb-co-01,placeholder one\n"
        'true,onb-co-02,"placeholder, two"\n',
        "﻿synthetic,company_id\ntrue,onb-co-01\n",
    ],
)
def test_marked_csv_fixtures_pass(git_repo: "GitRepo", content: str) -> None:
    git_repo.write("data/fixtures/onboarding/companies.csv", content)
    assert run(git_repo) == 0


def test_csv_with_a_false_row_fails(
    git_repo: "GitRepo", capsys: pytest.CaptureFixture[str]
) -> None:
    git_repo.write(
        "data/fixtures/onboarding/companies.csv",
        "synthetic,company_id\ntrue,onb-co-01\nfalse,onb-co-02\n",
    )
    assert run(git_repo) == 1
    assert "companies.csv:3: synthetic is 'false'" in capsys.readouterr().out


@pytest.mark.parametrize(
    "content", ["company_id,synthetic\nonb-co-01,true\n", "", "# synthetic: false\nid\n"]
)
def test_unmarked_csv_fixtures_fail(git_repo: "GitRepo", content: str) -> None:
    git_repo.write("ingest/tests/fixtures/registry.csv", content)
    assert run(git_repo) == 1


@pytest.mark.parametrize(
    "path", ["data/README.md", "data/import/.gitkeep", "data/fixtures/notes.txt"]
)
def test_allowed_data_files_pass(git_repo: "GitRepo", path: str) -> None:
    git_repo.write(path, "ok\n")
    assert run(git_repo) == 0


@pytest.mark.parametrize(
    "path", ["data/cache/spikes/gleif.json", "data/import/companies.csv", "data/runs/a/x.jsonl"]
)
def test_other_data_files_fail(
    git_repo: "GitRepo", path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    git_repo.write(path, "{}\n")
    assert run(git_repo) == 1
    assert f"{path}: only data/fixtures/" in capsys.readouterr().out
