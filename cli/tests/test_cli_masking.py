"""Masked validation messages (PHASE-2.md M2.0 deliverable 12, G9).

The non-synthetic records are look-alikes built here at run time (PHASE-2.md 2.9): invented
ids such as gbch-co-T0000001 and names such as "Test Holder Ltd", never committed as files.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli import masking
from neonradar_cli.main import app
from neonradar_contracts.datasets import load_registry

runner = CliRunner()
LOOKALIKE_ID = "gbch-co-T0000001"
LOOKALIKE_VALUE = "Test Holder Secret Date"


def _line(record: dict[str, Any]) -> str:
    return json.dumps(record) + "\n"


def _lookalike(**extra: Any) -> dict[str, Any]:
    return {
        "id": LOOKALIKE_ID,
        "schema": "Company",
        "datasets": ["gb_companies_house"],
        "properties": {"name": ["Test Holder Ltd"]},
        **extra,
    }


def _synthetic(**nr: Any) -> dict[str, Any]:
    return {
        "id": "syn-co-0099",
        "schema": "Company",
        "datasets": ["nr_synthetic"],
        "properties": {"name": ["Example Holdings Ltd"]},
        "nr": {"v": "1.0", "synthetic": True, **nr},
    }


@pytest.mark.parametrize(
    ("message", "masked"),
    [
        ("incorporationDate: Invalid value: 'x 1'", "incorporationDate: Invalid value: <value>"),
        ('got ["a", "b"]', "got [<value>, <value>]"),
        (f"name {'O' + chr(39) + 'Neill ' + chr(34) + 'x' + chr(34)!r}", "name <value>"),
        (f"R10 {'Test Café Ñandú'!a} is not NFC", "R10 <value> is not NFC"),
        ('name "O\'Neill Ltd" here', "name <value> here"),
        ("it's fine: 'v'", "it's fine: <value>"),
        (
            "nr.x: bad [type=bool_parsing, input_value=Secret Name, input_type=str]",
            "nr.x: bad [type=bool_parsing, input_value=<value>, input_type=str]",
        ),
        ("bad (input_value=Secret Name)", "bad (input_value=<value>)"),
        (
            f"BankAccount has no holder: add asset {LOOKALIKE_ID}",
            "BankAccount has no holder: add asset <record id>",
        ),
        (f"id {LOOKALIKE_ID!r} is not valid", "id <value> is not valid"),
    ],
)
def test_mask(message: str, masked: str) -> None:
    assert masking.mask(message, LOOKALIKE_ID) == masked


def test_only_synthetic_records_with_the_syn_prefix_are_unmasked() -> None:
    registry = load_registry()
    assert masking.is_synthetic(_synthetic(), registry)
    assert not masking.is_synthetic(_lookalike(), registry)
    assert not masking.is_synthetic(_lookalike(datasets=["no_such_dataset"]), registry)
    assert not masking.is_synthetic(_lookalike(datasets=None), registry)
    assert not masking.is_synthetic({**_synthetic(), "id": LOOKALIKE_ID}, registry)


def test_validate_records_masks_a_non_synthetic_record(tmp_path: Path) -> None:
    bad = _lookalike(
        properties={
            "name": ["Test Holder Ltd"],
            "incorporationDate": [LOOKALIKE_VALUE],
            "secretName": ["Test Holder Alias"],
        }
    )
    path = tmp_path / "lookalike.ftm.jsonl"
    path.write_text("\n" + _line(bad), encoding="utf-8")  # a blank first line: the record is on 2
    result = runner.invoke(app, ["contracts", "validate-records", str(path)])
    assert result.exit_code == 1
    issues = [line for line in result.output.splitlines() if line.startswith(f"{path}:")]
    assert issues == [
        f"{path}:2: R3: Company has no property <value> (FollowTheMoney would drop it)",
        f"{path}:2: R5: incorporationDate: Invalid value: <value>; dates are ISO 8601 and may be"
        " partial (1979-08)",
    ]
    for secret in (LOOKALIKE_ID, LOOKALIKE_VALUE, "Test Holder Alias", "secretName"):
        assert secret not in result.output


def test_validate_records_masks_batch_issues_on_the_right_line(tmp_path: Path) -> None:
    owner = {
        "id": "gbch-psc-T0000002",
        "schema": "Person",
        "datasets": ["gb_companies_house"],
        "properties": {"name": ["Test Person"]},
    }
    link = {
        "id": "gbch-ownership-T0000003",
        "schema": "Ownership",
        "datasets": ["gb_companies_house"],
        "properties": {"owner": ["gbch-psc-T0000002"], "asset": ["gbch-co-T0000009"]},
    }
    path = tmp_path / "batch.ftm.jsonl"
    path.write_text(_line(owner) + _line(link) + _line(owner), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path), "--strict"])
    assert result.exit_code == 1
    assert f"{path}:3: R4: duplicate id: another record in this load has it" in result.output
    assert f"{path}:2: R4: asset points to <value>, which is not in this load" in result.output
    for secret in ("T0000002", "T0000003", "T0000009", "Test Person"):
        assert secret not in result.output


def test_validate_records_keeps_values_and_ids_for_synthetic_records(tmp_path: Path) -> None:
    first, second = tmp_path / "a.ftm.jsonl", tmp_path / "b.ftm.jsonl"
    first.write_text(_line(_synthetic()), encoding="utf-8")
    second.write_text(_line(_synthetic(scenario="round_trip")), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(first), str(second)])
    assert result.exit_code == 1
    assert (
        f"{second}:1: R9 syn-co-0099: nr key 'scenario' looks like a ground-truth label"
        in result.output
    )
    assert f"{second}:1: R4 syn-co-0099: duplicate id" in result.output


@pytest.mark.parametrize(
    ("message", "masked"),
    [
        (
            "nr.address_roles.gbch-addr-T42SECRET: Input should be a valid string",
            "nr.address_roles.<value>: Input should be a valid string",
        ),
        (
            "nr.Test Holder Ltd: Extra inputs are not permitted",
            "nr.<value>: Extra inputs are not permitted",
        ),
        (
            "nr.Test: Holder: Extra inputs are not permitted",
            "nr.<value>: Extra inputs are not permitted",
        ),
        (
            "nr.channel: Input should be 'wire' or 'card'",
            "nr.channel: Input should be <value> or <value>",
        ),
        (
            "nr.share_pct_min is greater than nr.share_pct_max",
            "nr.share_pct_min is greater than nr.share_pct_max",
        ),
        (
            "first_seen 19790801 is not an ISO 8601 date",
            "first_seen <value> is not an ISO 8601 date",
        ),
    ],
)
def test_mask_nr_paths_and_numbers(message: str, masked: str) -> None:
    assert masking.mask(message) == masked


def test_hide_real_ids_keeps_synthetic_ids() -> None:
    message = "owner points to 'gbch-psc-T0000002', and asset to 'syn-co-0001'"
    assert (
        masking.hide_real_ids(message) == "owner points to <record id>, and asset to 'syn-co-0001'"
    )


def test_validate_records_masks_nr_keys_numbers_and_unknown_schemas(tmp_path: Path) -> None:
    roles = _lookalike(
        properties={"name": ["Test Holder Ltd"], "addressEntity": ["gbch-addr-T0000042"]},
        nr={"v": "1.0", "address_roles": {"gbch-addr-T0000042": 5}, "Test Holder Alias": 1},
        first_seen=19790801,
    )
    odd = {**_lookalike(), "id": "gbch-co-T0000005", "schema": "Test Holder Schema"}
    path = tmp_path / "nr.ftm.jsonl"
    path.write_text(_line(roles) + _line(odd), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path)])
    assert result.exit_code == 1
    assert "  <unknown schema>: 1" in result.output
    assert f"{path}:1: NR: nr.address_roles.<value>: " in result.output
    assert f"{path}:1: NR: nr.<value>: Extra inputs are not permitted" in result.output
    assert f"{path}:1: R5: first_seen <value> is not an ISO 8601 date" in result.output
    for secret in ("T0000042", "T0000005", "Test Holder", "19790801"):
        assert secret not in result.output


def test_validate_records_hides_real_ids_that_a_synthetic_record_names(tmp_path: Path) -> None:
    link = {
        "id": "syn-ownership-0001",
        "schema": "Ownership",
        "datasets": ["nr_synthetic"],
        "properties": {"owner": ["gbch-psc-T0000002"], "asset": ["syn-acct-0001"]},
        "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "activity"},
    }
    path = tmp_path / "join.ftm.jsonl"
    path.write_text(_line(link), encoding="utf-8")
    result = runner.invoke(app, ["contracts", "validate-records", str(path), "--strict"])
    assert result.exit_code == 1
    assert (
        f"{path}:1: R4 syn-ownership-0001: owner points to <record id>, which is not in this load"
        in result.output
    )
    assert "T0000002" not in result.output
