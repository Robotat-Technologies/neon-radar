"""Contract tests for C1, the NeonRadar Record (PHASE-1.md 5.1, 5.5)."""

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from followthemoney import ValueEntity, model, registry
from pydantic import ValidationError

from neonradar_contracts import versions
from neonradar_contracts.records import (
    ALLOWED_SCHEMATA,
    ID_RE,
    LABEL_KEY_RE,
    Manifest,
    NrExtension,
    Producer,
    RecordFileError,
    iter_records,
    manifest_path,
    validate_batch,
    validate_files,
    validate_record,
    write_manifest,
)

pytestmark = pytest.mark.contract

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "c1"
DEMO = EXAMPLES / "demo.ftm.jsonl"
INVALID = sorted((EXAMPLES / "invalid").glob("*.ftm.jsonl"))
NR = {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"}


def _rule_number(path: Path) -> int:
    match = re.match(r"r(\d+)-", path.name)
    assert match, path.name
    return int(match[1])


def _company(**changes: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": "syn-co-0099",
        "schema": "Company",
        "datasets": ["nr_synthetic"],
        "properties": {"name": ["Example Holdings Ltd"], "jurisdiction": ["gb"]},
        "nr": dict(NR),
    }
    record.update(changes)
    return record


def _rules(record: dict[str, Any]) -> list[str]:
    return [issue.rule for issue in validate_record(record)]


def test_demo_file_is_valid_in_strict_mode() -> None:
    counts, issues = validate_files([DEMO], strict=True)
    assert [str(issue) for issue in issues] == []
    assert counts.total() == 10
    assert counts["Payment"] == 1


def test_every_rule_has_exactly_one_invalid_example() -> None:
    assert sorted(_rule_number(path) for path in INVALID) == list(range(1, 11))


@pytest.mark.parametrize("path", INVALID, ids=lambda path: path.name)
def test_invalid_example_fails_with_exactly_its_rule(path: Path) -> None:
    _, issues = validate_files([path], strict=True)
    assert issues, path.name
    assert {issue.rule for issue in issues} == {f"R{_rule_number(path)}"}, [str(i) for i in issues]


def test_r10_example_really_holds_a_decomposed_string() -> None:
    [record] = iter_records(EXAMPLES / "invalid" / "r10-not-nfc.ftm.jsonl")
    assert "̈" in record["properties"]["name"][0]


def test_nr_rejects_unknown_keys() -> None:
    record = _company(nr={**NR, "colour": "blue"})
    [issue] = validate_record(record)
    assert issue.rule == "NR"
    assert "nr.colour" in issue.message
    with pytest.raises(ValidationError, match="colour"):
        NrExtension.model_validate({**NR, "colour": "blue"})


@pytest.mark.parametrize(
    "key", ["typology", "scenario_id", "is_illicit", "is_lookalike", "ground_truth", "label"]
)
def test_label_like_keys_fail_r9_wherever_they_appear(key: str) -> None:
    assert _rules(_company(nr={**NR, key: "x"})) == ["R9"]
    assert _rules({**_company(), key: "x"}) == ["R9"]
    record = _company()
    record["properties"][key] = ["x"]
    assert _rules(record) == ["R9"]


def test_allowed_schema_property_names_never_look_like_labels() -> None:
    for name in ALLOWED_SCHEMATA:
        assert not [p for p in model[name].properties if LABEL_KEY_RE.search(p)], name


@pytest.mark.parametrize(
    ("nr", "message"),
    [
        ({**NR, "channel": "wire"}, "nr.channel is only used on Payment"),
        ({**NR, "address_roles": {"syn-addr-0001": "registered"}}, "not in addressEntity"),
        ({**NR, "synthetic": "true"}, "nr.synthetic"),
        ({"synthetic": True}, "nr.v"),
    ],
)
def test_nr_shape_and_placement_fail_nr(nr: dict[str, Any], message: str) -> None:
    issues = validate_record(_company(nr=nr))
    assert "NR" in {issue.rule for issue in issues}
    assert any(message in issue.message for issue in issues), [str(i) for i in issues]


def test_one_problem_is_reported_once() -> None:
    payment = copy.deepcopy(next(r for r in iter_records(DEMO) if r["schema"] == "Payment"))
    payment["nr"]["scenario"] = "round_trip"  # the channel is still there: no R7
    assert _rules(payment) == ["R9"]
    company = next(r for r in iter_records(DEMO) if r["id"] == "syn-co-0001")
    company = copy.deepcopy(company)
    company["properties"]["name"] = "Falcon Ridge Trading Ltd"  # not a list
    assert _rules(company) == ["R3"]  # address_roles is not checked against broken properties


def test_share_bounds_must_be_ordered() -> None:
    record = next(r for r in iter_records(DEMO) if r["id"] == "syn-ownership-0001")
    record = copy.deepcopy(record)
    record["nr"]["share_pct_min"] = 60.0
    assert _rules(record) == ["NR"]


def test_unknown_property_and_unknown_top_level_key() -> None:
    record = _company()
    record["properties"]["birthDate"] = ["1979"]
    assert _rules(record) == ["R3"]
    assert _rules({**_company(), "target": True}) == ["FORMAT"]


def test_schema_outside_the_v1_list_fails_r3() -> None:
    assert _rules(_company(schema="Vessel")) == ["R3"]


def test_non_synthetic_records_must_not_set_nr_synthetic() -> None:
    record = _company(id="gbch-co-01800000", datasets=["gb_companies_house"])
    record["nr"] = {"v": "1.0", "synthetic": False}
    assert _rules(record) == ["R6"]
    record["nr"] = {"v": "1.0", "source_ref": "01800000"}
    assert _rules(record) == []


def test_make_entity_output_fails_r2() -> None:
    entity = model.make_entity("Company")
    entity.id = "syn-co-0099"
    entity.add("name", "Example Holdings Ltd")
    record = {**entity.to_dict(), "nr": dict(NR)}
    assert "datasets" not in entity.to_dict()
    assert _rules(record) == ["R2"]


def test_value_entity_recipe_from_c1_record_md_is_valid() -> None:
    company = ValueEntity(model["Company"], {"id": "syn-co-0099", "datasets": ["nr_synthetic"]})
    company.add("name", "Example Holdings Ltd")
    payment = ValueEntity(
        model["Payment"], {"id": "syn-payment-000099", "datasets": ["nr_synthetic"]}
    )
    payment.add("payer", "syn-co-0099")
    payment.add("beneficiary", "syn-co-0001")
    payment.add("payerAccount", "syn-acct-0099")
    payment.add("beneficiaryAccount", "syn-acct-0001")
    payment.add("amount", "120.50")
    payment.add("currency", "EUR")
    payment.add("date", "2026-03-14T10:22:05+00:00")  # FollowTheMoney drops the offset
    assert payment.get("date") == ["2026-03-14T10:22:05"]
    lines = [
        json.dumps({**company.to_dict(), "nr": dict(NR)}, ensure_ascii=False),
        json.dumps(
            {**payment.to_dict(), "nr": {**NR, "synthetic_kind": "activity", "channel": "wire"}},
            ensure_ascii=False,
        ),
    ]
    for line in lines:
        assert validate_record(json.loads(line)) == []


def test_every_valid_id_can_be_referenced() -> None:
    good = ["syn-co-0001", "gbch-co-01800000", "gleif-549300OWFMSO9NYV4H90", "icij-10000001"]
    for rid in good:
        assert ID_RE.match(rid), rid
        assert registry.entity.validate(rid), rid
    for bad in ["gbch-officer_abc", "gbch-x:1", "syn-co-0001-", "syn-co-0001.", "SYN-co-1", "s-1"]:
        assert not ID_RE.match(bad), bad


def test_references_must_be_record_ids() -> None:
    record = _company()
    record["properties"]["addressEntity"] = ["NK-abc"]
    assert _rules(record) == ["R4"]
    record["properties"]["addressEntity"] = ["gbch-x_y"]
    assert _rules(record) == ["R3"]  # FollowTheMoney cannot store this reference


def test_dangling_references_fail_only_in_strict_mode() -> None:
    records = list(iter_records(EXAMPLES / "invalid" / "r4-dangling-reference.ftm.jsonl"))
    assert {issue.rule for issue in validate_batch(records, strict=True)} == {"R4"}
    assert validate_batch(records, strict=False) == []


@pytest.mark.parametrize(
    ("prop", "value"),
    [
        ("amount", "0.00"),
        ("amount", "-5.00"),
        ("amount", "9500.005"),
        ("amount", "abc"),
        ("currency", "EURO"),
        ("payerAccount", None),
    ],
)
def test_payment_fields_fail_r7(prop: str, value: str | None) -> None:
    payment = copy.deepcopy(next(r for r in iter_records(DEMO) if r["schema"] == "Payment"))
    if value is None:
        del payment["properties"][prop]
    else:
        payment["properties"][prop] = [value]
    assert set(_rules(payment)) == {"R7"}


def test_synthetic_accounts_cannot_look_real() -> None:
    account = copy.deepcopy(next(r for r in iter_records(DEMO) if r["id"] == "syn-acct-0001"))
    account["properties"]["accountNumber"] = ["12345678"]
    assert _rules(account) == ["R8"]
    account["properties"]["accountNumber"] = ["NRSYN0000000001"]
    account["properties"]["iban"] = ["GB00SYNT00000000000000"]
    assert "R8" in _rules(account)


def test_iter_records_names_the_bad_line(tmp_path: Path) -> None:
    path = tmp_path / "broken.ftm.jsonl"
    path.write_text(json.dumps(_company()) + "\n\n{oops\n", encoding="utf-8")
    with pytest.raises(RecordFileError, match=r"broken\.ftm\.jsonl:3: invalid JSON"):
        list(iter_records(path))


MANIFEST_EXAMPLE: dict[str, Any] = {
    "manifest_version": "1.0",
    "record_contract": "1.0.0",
    "dataset": "nr_synthetic",
    "files": [
        {"path": "nr_synthetic-20261023-demo-mini.ftm.jsonl", "sha256": "0" * 64, "records": 412}
    ],
    "created_at": "2026-10-23T09:00:00Z",
    "producer": {"name": "neonradar_ingest.synth", "version": "0.1.0", "git_sha": "a" * 40},
    "source": {"urls": [], "retrieved_at": None, "source_version": None},
    "licence": {"id": "Apache-2.0", "attribution": None},
    "counts": {"by_schema": {"Company": 24, "Person": 30, "Payment": 260}, "skipped": {}},
    "dependencies": {"followthemoney": "4.11.0"},
    "synthetic": True,
    "seed": 20261023,
    "notes": [],
}


def test_manifest_round_trips() -> None:
    text = json.dumps(MANIFEST_EXAMPLE)
    assert Manifest.model_validate_json(text).model_dump(mode="json") == MANIFEST_EXAMPLE


@pytest.mark.parametrize(
    ("key", "value"),
    [("sha256", "<hex>"), ("records", -1), ("rows", 3)],
)
def test_manifest_rejects_bad_file_entries(key: str, value: Any) -> None:
    data = copy.deepcopy(MANIFEST_EXAMPLE)
    data["files"][0][key] = value
    with pytest.raises(ValidationError):
        Manifest.model_validate(data)


def test_demo_manifest_matches_its_records() -> None:
    path = manifest_path(DEMO)
    assert path.name == "demo.manifest.json"
    manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    [entry] = manifest.files
    assert entry.path == DEMO.name
    assert entry.sha256 == hashlib.sha256(DEMO.read_bytes()).hexdigest()
    counts, _ = validate_files([DEMO], strict=True)
    assert entry.records == counts.total()
    assert manifest.counts.by_schema == dict(counts)
    assert manifest.record_contract == versions.RECORD
    assert (manifest.dataset, manifest.synthetic, manifest.licence.id) == (
        "nr_synthetic",
        True,
        "Apache-2.0",
    )


def test_write_manifest(tmp_path: Path) -> None:
    records = tmp_path / "nr_synthetic-20261021-test.ftm.jsonl"
    shutil.copyfile(DEMO, records)
    path = write_manifest(
        records,
        dataset="nr_synthetic",
        producer=Producer(name="tests", version="0.1.0"),
        skipped={"Vessel": 2},
        seed=7,
    )
    assert path == tmp_path / "nr_synthetic-20261021-test.manifest.json"
    manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    assert manifest.files[0].sha256 == hashlib.sha256(records.read_bytes()).hexdigest()
    assert manifest.files[0].records == 10
    assert manifest.counts.skipped == {"Vessel": 2}
    assert manifest.seed == 7
    assert "followthemoney" in manifest.dependencies
    with pytest.raises(ValueError, match=r"not in contracts/datasets\.yaml"):
        write_manifest(records, dataset="nope", producer=Producer(name="t", version="0"))
    with pytest.raises(ValueError, match=r"not a \.ftm\.jsonl file"):
        manifest_path(tmp_path / "records.json")
