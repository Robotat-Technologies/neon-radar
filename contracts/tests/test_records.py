"""Contract tests for C1, the NeonRadar Record (PHASE-1.md 5.1, 5.5; PHASE-2.md 5.1, 5.4)."""

import copy
import hashlib
import json
import re
import shutil
import unicodedata
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
    make_id,
    manifest_path,
    validate_batch,
    validate_files,
    validate_record,
    write_manifest,
)

pytestmark = pytest.mark.contract

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "c1"
DEMO = EXAMPLES / "demo.ftm.jsonl"
DEMO_1_1 = EXAMPLES / "demo-1.1.ftm.jsonl"
INVALID = sorted((EXAMPLES / "invalid").glob("*.ftm.jsonl"))
NR = {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"}
COMBINING_DIAERESIS = unicodedata.lookup("COMBINING DIAERESIS")


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


def _demo(record_id: str, path: Path = DEMO) -> dict[str, Any]:
    return copy.deepcopy(next(r for r in iter_records(path) if r["id"] == record_id))


def _rules(record: dict[str, Any]) -> list[str]:
    return [issue.rule for issue in validate_record(record)]


def _batch_rules(records: list[dict[str, Any]], strict: bool = True) -> list[str]:
    return sorted(issue.rule for issue in validate_batch(records, strict))


# Golden examples


def test_demo_file_is_valid_in_strict_mode() -> None:
    counts, issues = validate_files([DEMO], strict=True)
    assert [str(issue) for issue in issues] == []
    assert counts.total() == 10
    assert counts["Payment"] == 1


def test_demo_1_1_file_is_valid_in_strict_mode() -> None:
    counts, issues = validate_files([DEMO_1_1], strict=True)
    assert [str(issue) for issue in issues] == []
    assert counts.total() == 7
    assert {r["nr"]["v"] for r in iter_records(DEMO_1_1)} == {"1.1"}
    kinds = {r["id"]: r["nr"]["synthetic_kind"] for r in iter_records(DEMO_1_1)}
    assert (kinds["syn-lst-0101"], kinds["syn-lk-0101"]) == ("list", "leak")


def test_the_1_0_and_1_1_examples_load_together() -> None:
    _, issues = validate_files([DEMO, DEMO_1_1], strict=True)
    assert [str(issue) for issue in issues] == []


def test_every_rule_has_exactly_one_invalid_example() -> None:
    assert sorted(_rule_number(path) for path in INVALID) == list(range(1, 11))


@pytest.mark.parametrize("path", INVALID, ids=lambda path: path.name)
def test_invalid_example_fails_with_exactly_its_rule(path: Path) -> None:
    _, issues = validate_files([path], strict=True)
    assert len(issues) == 1, [str(i) for i in issues]
    assert issues[0].rule == f"R{_rule_number(path)}"


def test_r10_example_really_holds_a_decomposed_string() -> None:
    [record] = iter_records(EXAMPLES / "invalid" / "r10-not-nfc.ftm.jsonl")
    assert COMBINING_DIAERESIS in record["properties"]["name"][0]
    [issue] = validate_record(record)
    assert "\\u0308" in issue.message  # printed with ascii() so the character is visible


def test_an_empty_file_is_an_empty_load(tmp_path: Path) -> None:
    path = tmp_path / "empty.ftm.jsonl"
    path.write_bytes(b"")
    counts, issues = validate_files([path], strict=True)
    assert (counts.total(), issues) == (0, [])


# R1 ids and make_id


def test_every_valid_id_can_be_referenced() -> None:
    good = ["syn-co-0001", "gbch-co-T0000001", "gleif-TEST.LEI.0002", "icij-TEST.0001"]
    for rid in good:
        assert ID_RE.match(rid), rid
        assert registry.entity.validate(rid), rid
    bad = ["gbch-officer_abc", "gbch-x:1", "syn-co-0001-", "syn-co-0001.", "SYN-co-1", "s-1"]
    for rid in [*bad, "syn-co-0001\n"]:
        assert not ID_RE.match(rid), rid
    assert _rules(_company(id="syn-co-0099\n")) == ["R1"]


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ("TEST_officer-0001", "gbch-off-TEST.officer-0001"),  # officer-id shape: `_` and `-`
        ("T0000001", "gbch-off-T0000001"),
        ("ab:cd", None),  # another character: hashed
        ("abc_", None),  # would end in a dot: hashed
        ("abc-", None),
        ("x" * 120, None),  # too long: hashed
        ("abc\n", None),
    ],
)
def test_make_id_maps_or_hashes_source_ids(native: str, expected: str | None) -> None:
    rid = make_id("gbch", "off", native)
    digest = hashlib.sha1(native.encode(), usedforsecurity=False).hexdigest()[:20]
    assert rid == (expected or f"gbch-off-{digest}")
    assert rid == make_id("gbch", "off", native)  # deterministic
    assert ID_RE.match(rid), rid
    assert registry.entity.validate(rid), rid


@pytest.mark.parametrize(
    ("prefix", "kind", "native"), [("GB", "off", "1"), ("gbch", "Off", "1"), ("gbch", "off", "")]
)
def test_make_id_refuses_bad_parts(prefix: str, kind: str, native: str) -> None:
    with pytest.raises(ValueError, match="make_id"):
        make_id(prefix, kind, native)


# R3, R9, FORMAT and NR


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


def test_synthetic_records_carry_only_flag_topics() -> None:
    record = _company()
    record["properties"]["topics"] = ["sanction", "role.pep"]
    assert _rules(record) == []
    record["properties"]["topics"] = ["crime.fin"]
    assert _rules(record) == ["R9"]
    real = _company(id="gbch-co-T0000001", datasets=["gb_companies_house"], nr={"v": "1.0"})
    real["properties"]["topics"] = ["crime.fin"]
    assert _rules(real) == []


@pytest.mark.parametrize(
    ("nr", "message"),
    [
        ({**NR, "channel": "wire"}, "nr.channel is only used on Payment"),
        ({**NR, "address_roles": {"syn-addr-0001": "registered"}}, "not in addressEntity"),
        ({**NR, "synthetic": "true"}, "nr.synthetic"),
        ({"synthetic": True}, "nr.v"),
    ],
)
def test_nr_shape_and_placement_fail_nr_only(nr: dict[str, Any], message: str) -> None:
    issues = validate_record(_company(nr=nr))
    assert [issue.rule for issue in issues] == ["NR"], [str(i) for i in issues]
    assert message in issues[0].message


def test_share_bounds_must_be_ordered() -> None:
    record = _demo("syn-ownership-0001")
    record["nr"]["share_pct_min"] = 60.0
    assert _rules(record) == ["NR"]


def test_unknown_property_and_unknown_top_level_key() -> None:
    record = _company()
    record["properties"]["birthDate"] = ["1979"]
    assert _rules(record) == ["R3"]
    assert _rules({**_company(), "target": True}) == ["FORMAT"]  # OpenSanctions' legacy flag


def test_schema_outside_the_v1_list_fails_r3() -> None:
    assert _rules(_company(schema="Vessel")) == ["R3"]


# C1 1.1.0: new and wider nr keys (PHASE-2.md 5.1, 5.4)


@pytest.mark.parametrize("v", ["1.0", "1.1"])
@pytest.mark.parametrize(
    ("record_id", "path", "keys"),
    [
        ("syn-co-0101", DEMO_1_1, {"psc_statements": ["x"], "accounts_category": "DORMANT"}),
        ("syn-off-0101", DEMO_1_1, {"ch_person_number": "SYN00101A0001"}),
        ("syn-ownership-0001", DEMO, {"share_pct_min_exclusive": True, "is_nominee": True}),
        ("syn-control-0101", DEMO_1_1, {"share_pct_max_exclusive": False}),
    ],
)
def test_1_1_keys_validate_under_both_versions(
    v: str, record_id: str, path: Path, keys: dict[str, Any]
) -> None:
    record = _demo(record_id, path)
    record["nr"].update(keys, v=v)
    assert _rules(record) == []


def test_nr_v_accepts_only_known_versions() -> None:
    assert _rules(_company(nr={**NR, "v": "1.1"})) == []
    for v in ("1.2", "2.0", "1", 1.1):
        assert _rules(_company(nr={**NR, "v": v})) == ["NR"], v


@pytest.mark.parametrize("kind", ["registry", "activity", "list", "leak"])
def test_synthetic_kinds(kind: str) -> None:
    assert _rules(_company(nr={**NR, "synthetic_kind": kind})) == []


@pytest.mark.parametrize("kind", ["registry ", "List", "scraped", ""])
def test_unknown_synthetic_kinds_still_fail(kind: str) -> None:
    assert _rules(_company(nr={**NR, "synthetic_kind": kind})) == ["NR"]


def test_list_and_leak_kinds_stay_synthetic_only() -> None:
    record = _company(id="gbch-co-T0000001", datasets=["gb_companies_house"])
    for kind in ("list", "leak"):
        record["nr"] = {"v": "1.1", "synthetic_kind": kind}
        assert _rules(record) == ["NR"], kind


def test_is_nominee_on_ownership_and_the_share_band_on_control() -> None:
    ownership = _demo("syn-ownership-0001")
    ownership["nr"]["is_nominee"] = True
    assert _rules(ownership) == []
    control = _demo("syn-control-0101", DEMO_1_1)
    assert {"share_pct_min", "share_pct_max", "share_pct_min_exclusive"} <= set(control["nr"])
    assert _rules(control) == []
    control["nr"]["share_pct_min"] = 80.0  # the bound order holds on Control too
    assert _rules(control) == ["NR"]


@pytest.mark.parametrize(
    ("record_id", "path", "key", "value", "used_on"),
    [
        ("syn-p-0001", DEMO, "psc_statements", ["x"], "Company"),
        ("syn-p-0001", DEMO, "accounts_category", "DORMANT", "Company"),
        ("syn-addr-0001", DEMO, "ch_person_number", "SYN00101A0001", "LegalEntity"),
        ("syn-co-0001", DEMO, "share_pct_min_exclusive", True, "Ownership or Control"),
        ("syn-co-0001", DEMO, "share_pct_max_exclusive", True, "Ownership or Control"),
        ("syn-co-0001", DEMO, "share_pct_min", 25.0, "Ownership or Control"),
        ("syn-control-0101", DEMO_1_1, "is_nominee", True, "Directorship or Ownership"),
        ("syn-control-0101", DEMO_1_1, "consolidation", "direct", "Ownership"),
    ],
)
def test_1_1_keys_keep_their_placement(
    record_id: str, path: Path, key: str, value: Any, used_on: str
) -> None:
    record = _demo(record_id, path)
    record["nr"][key] = value
    issues = validate_record(record)
    assert [issue.rule for issue in issues] == ["NR"], [str(i) for i in issues]
    assert f"nr.{key} is only used on {used_on}" in issues[0].message


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("psc_statements", "no-individual-or-entity-with-signficant-control"),
        ("psc_statements", [1]),
        ("accounts_category", ["DORMANT"]),
        ("ch_person_number", 101),
    ],
)
def test_1_1_company_and_person_keys_have_fixed_types(key: str, value: Any) -> None:
    record_id = "syn-off-0101" if key == "ch_person_number" else "syn-co-0101"
    record = _demo(record_id, DEMO_1_1)
    record["nr"][key] = value
    assert _rules(record) == ["NR"]


@pytest.mark.parametrize("value", ["true", 1, [True]])
def test_exclusive_flags_are_booleans(value: Any) -> None:
    record = _demo("syn-ownership-0101", DEMO_1_1)
    record["nr"]["share_pct_min_exclusive"] = value
    assert _rules(record) == ["NR"]


def test_unknown_keys_still_fail_under_1_1() -> None:
    [issue] = validate_record(_company(nr={**NR, "v": "1.1", "person_number": "x"}))
    assert (issue.rule, "nr.person_number" in issue.message) == ("NR", True)


# R6 synthetic consistency


def test_only_synthetic_records_set_the_synthetic_keys() -> None:
    record = _company(id="gbch-co-T0000001", datasets=["gb_companies_house"])
    record["nr"] = {"v": "1.0", "synthetic": False}
    assert _rules(record) == ["R6"]
    record["nr"] = {"v": "1.0", "synthetic_kind": "registry"}
    assert _rules(record) == ["NR"]
    record["nr"] = {"v": "1.0", "source_ref": "T0000001"}
    assert _rules(record) == []


def test_synthetic_sanction_names_only_synthetic_entities(tmp_path: Path) -> None:
    """G1: C2 builds SUBJECT_OF from Sanction.entity, so a synthetic Sanction naming a real
    entity would mark it as sanctioned. Synthetic background records may name real ones."""
    sanction = _company(id="syn-sanction-0099", schema="Sanction", properties={})
    sanction["properties"] = {"entity": ["syn-co-0099"], "authority": ["Example Authority"]}
    assert _rules(sanction) == []
    sanction["properties"]["entity"] = ["syn-co-0099", "gbch-co-T0000001"]
    [issue] = validate_record(sanction)
    assert issue.rule == "R6"
    assert "'gbch-co-T0000001': SUBJECT_OF would mark a real entity as sanctioned" in issue.message
    path = tmp_path / "sanction.ftm.jsonl"
    path.write_text(json.dumps(sanction) + "\n", encoding="utf-8")
    assert "R6" in [i.rule for i in validate_files([path], strict=False)[1]]
    ownership = _demo("syn-ownership-0001")
    ownership["properties"]["owner"] = ["gbch-co-T0000001"]  # background activity (G1)
    assert _rules(ownership) == []


PER_1, PER_2 = "syn-per-0001", "syn-per-0002"


@pytest.mark.parametrize(
    ("schema", "props", "real_prop", "reason"),
    [
        ("Family", {"person": [PER_1], "relative": [PER_2]}, "relative", "FAMILY_OF"),
        ("Associate", {"person": [PER_1], "associate": [PER_2]}, "person", "ASSOCIATE_OF"),
        ("Occupancy", {"holder": [PER_1], "post": ["syn-pos-0001"]}, "holder", "HOLDS_POSITION"),
    ],
)
def test_synthetic_relative_associate_and_post_links_name_only_synthetic_people(
    schema: str, props: dict[str, list[str]], real_prop: str, reason: str
) -> None:
    """G1: these links can make a real person a relative or close associate of a politically
    exposed person, or the holder of a post, so a synthetic one references only syn- records."""
    record = _company(id="syn-link-0099", schema=schema, properties=dict(props))
    assert _rules(record) == []
    record["properties"][real_prop] = ["gbch-off-T0000001"]
    [issue] = validate_record(record)
    assert issue.rule == "R6"
    assert f"in {real_prop}, not 'gbch-off-T0000001': {reason}" in issue.message
    record["properties"][real_prop] = ["not an id"]
    assert _rules(record) == ["R4"]  # a malformed reference is reported once, by R4


@pytest.mark.parametrize(
    ("schema", "props"),
    [
        ("Ownership", {"owner": ["gbch-co-T0000001"], "asset": ["syn-acct-0001"]}),
        ("Representation", {"agent": ["syn-co-0099"], "client": ["gbch-co-T0000001"]}),
        ("Membership", {"member": ["syn-per-0001"], "organization": ["gbch-co-T0000001"]}),
    ],
)
def test_synthetic_background_links_may_name_real_records(
    schema: str, props: dict[str, list[str]]
) -> None:
    assert _rules(_company(id="syn-link-0099", schema=schema, properties=props)) == []


ARABIC_INDIC_DIGITS = str.maketrans("0123456789", "".join(chr(0x0660 + d) for d in range(10)))


@pytest.mark.parametrize(
    ("record_id", "prop", "rule"),
    [
        ("syn-payment-000001", "amount", "R7"),
        ("syn-payment-000001", "date", "R5"),
        ("syn-acct-0001", "accountNumber", "R8"),
    ],
)
def test_non_ascii_digits_fail_c1_property_formats(record_id: str, prop: str, rule: str) -> None:
    """Python's `\\d` matches any Unicode digit; C1 formats allow only 0 to 9."""
    record = _demo(record_id)
    value = record["properties"][prop][0]
    keep = 5 if prop == "accountNumber" else 0  # the NRSYN prefix
    record["properties"][prop] = [value[:keep] + value[keep:].translate(ARABIC_INDIC_DIGITS)]
    assert _rules(record) == [rule]


@pytest.mark.parametrize("key", ["created_at", "record_contract"])
def test_non_ascii_digits_fail_the_manifest(key: str) -> None:
    data = {**MANIFEST_EXAMPLE, key: MANIFEST_EXAMPLE[key].translate(ARABIC_INDIC_DIGITS)}
    with pytest.raises(ValidationError, match=key):
        Manifest.model_validate(data)


def test_non_ascii_digits_fail_ids() -> None:
    assert _rules(_company(id="syn-co-0099".translate(ARABIC_INDIC_DIGITS))) == ["R1"]


# Each problem is reported once


def test_each_problem_is_reported_once() -> None:
    payment = _demo("syn-payment-000001")
    payment["nr"]["scenario"] = "round_trip"  # the channel is still there: no R7
    assert _rules(payment) == ["R9"]
    company = _demo("syn-co-0001")
    company["properties"]["name"] = "Quillon Marsh Trading Ltd"  # not a list
    assert _rules(company) == ["R3"]  # address_roles is not checked against broken properties
    empty_name = _company()
    empty_name["properties"]["name"] = []
    assert _rules(empty_name) == ["R3"]
    impossible = _demo("syn-payment-000001")
    impossible["properties"]["date"] = ["2026-13-45T10:22:05"]
    assert _rules(impossible) == ["R5"]
    wrong_prefix = _company(id="gbch-co-0099")
    assert _rules(wrong_prefix) == ["R1"]


# R3 to R5 property values and references


def test_references_must_be_record_ids() -> None:
    record = _company()
    record["properties"]["addressEntity"] = ["NK-abc"]
    assert _rules(record) == ["R4"]
    record["properties"]["addressEntity"] = ["gbch-x_y"]  # FollowTheMoney cannot store it
    [issue] = validate_record(record)
    assert issue.rule == "R4"
    assert "make_id" in issue.message


def test_dangling_references_fail_only_in_strict_mode() -> None:
    records = list(iter_records(EXAMPLES / "invalid" / "r4-dangling-reference.ftm.jsonl"))
    assert _batch_rules(records) == ["R4"]
    assert validate_batch(records, strict=False) == []


def test_duplicate_ids_fail_r4_in_both_modes() -> None:
    records = [*iter_records(DEMO), _demo("syn-co-0002")]
    for strict in (True, False):
        [issue] = validate_batch(records, strict)
        assert (issue.rule, issue.record_id) == ("R4", "syn-co-0002")
        assert "duplicate id" in issue.message


def test_an_account_reused_as_an_id_still_needs_a_holder() -> None:
    records = [r for r in iter_records(DEMO) if r["id"] != "syn-ownership-0003"]
    records.append(_company(id="syn-acct-0002"))
    assert _batch_rules(records, strict=False) == ["R4", "R8"]


@pytest.mark.parametrize(
    ("record_id", "prop", "target"),
    [
        ("syn-payment-000001", "payerAccount", "syn-co-0001"),  # must be a BankAccount
        ("syn-payment-000001", "payer", "syn-acct-0001"),  # must be a LegalEntity
        ("syn-ownership-0001", "owner", "syn-addr-0001"),  # must be a LegalEntity
        ("syn-ownership-0001", "asset", "syn-addr-0001"),  # must be an Asset or a LegalEntity
        ("syn-co-0001", "addressEntity", "syn-p-0001"),  # must be an Address
    ],
)
def test_strict_mode_checks_what_a_reference_points_to(
    record_id: str, prop: str, target: str
) -> None:
    records = list(iter_records(DEMO))
    record = next(r for r in records if r["id"] == record_id)
    record["properties"][prop] = [target]
    record.get("nr", {}).pop("address_roles", None)
    issues = [i for i in validate_batch(records, strict=True) if i.record_id == record_id]
    assert [issue.rule for issue in issues] == ["R4"], [str(i) for i in issues]
    assert "it must point to a" in issues[0].message
    assert all(i.rule != "R4" for i in validate_batch(records, strict=False))


def test_an_ownership_asset_may_be_a_company() -> None:
    assert validate_files([DEMO], strict=True)[1] == []  # syn-ownership-0001: asset is a Company


# R5, R7 and R8: payments and accounts


@pytest.mark.parametrize(
    ("prop", "values"),
    [
        ("amount", ["0.00"]),
        ("amount", ["-5.00"]),
        ("amount", ["9500.005"]),
        ("amount", ["abc"]),
        ("amount", ["9500.00\n"]),
        ("currency", ["EURO"]),
        ("currency", ["EUR\n"]),
        ("currency", ["XXQ"]),  # three upper-case letters, but not ISO 4217
        ("payerAccount", None),
        ("date", None),
        ("date", ["2026-03-14T10:22:05", "2026-03-15T10:22:05"]),
    ],
)
def test_payment_fields_fail_r7(prop: str, values: list[str] | None) -> None:
    payment = _demo("syn-payment-000001")
    if values is None:
        del payment["properties"][prop]
    else:
        payment["properties"][prop] = values
    assert _rules(payment) == ["R7"]


@pytest.mark.parametrize("currency", ["EUR", "GBP", "USD", "AED"])
def test_iso_currencies_pass(currency: str) -> None:
    payment = _demo("syn-payment-000001")
    payment["properties"]["currency"] = [currency]
    assert _rules(payment) == []


@pytest.mark.parametrize(
    "date", ["2026-03-14", "2026-03-14T10:22:05Z", "2026-03-14T10:22", "2026-03-14T10:22:05\n"]
)
def test_payment_dates_are_full_utc_timestamps(date: str) -> None:
    payment = _demo("syn-payment-000001")
    payment["properties"]["date"] = [date]
    assert _rules(payment) == ["R5"]


def test_followthemoney_date_cleaning_as_documented_in_c1_record_md() -> None:
    # An offset is converted to UTC; a trailing Z is cut to minutes, which then fails R5.
    assert registry.date.clean("2026-03-14T10:22:05+02:00") == "2026-03-14T08:22:05"
    assert registry.date.clean("2026-03-14T10:22:05+00:00") == "2026-03-14T10:22:05"
    assert registry.date.clean("2026-03-14T10:22:05Z") == "2026-03-14T10:22"


def test_synthetic_accounts_cannot_look_real() -> None:
    account = _demo("syn-acct-0001")
    account["properties"]["accountNumber"] = ["12345678"]
    assert _rules(account) == ["R8"]
    account["properties"]["accountNumber"] = ["NRSYN0000000001\n"]
    assert _rules(account) == ["R8"]
    account["properties"]["accountNumber"] = ["NRSYN0000000001"]
    account["properties"]["iban"] = ["GB00SYNT00000000000000"]
    assert "R8" in _rules(account)


# The loader recipe and the traps


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
    payment.add("date", "2026-03-14T10:22:05")  # UTC, no offset, no Z
    lines = [
        json.dumps({**company.to_dict(), "nr": dict(NR)}, ensure_ascii=False),
        json.dumps(
            {**payment.to_dict(), "nr": {**NR, "synthetic_kind": "activity", "channel": "wire"}},
            ensure_ascii=False,
        ),
    ]
    for line in lines:
        assert validate_record(json.loads(line)) == []


# Files


def test_iter_records_names_the_bad_line(tmp_path: Path) -> None:
    path = tmp_path / "broken.ftm.jsonl"
    path.write_text(json.dumps(_company()) + "\n\n{oops\n", encoding="utf-8")
    with pytest.raises(RecordFileError, match=r"broken\.ftm\.jsonl:3: invalid JSON"):
        list(iter_records(path))


def test_iter_records_refuses_other_encodings(tmp_path: Path) -> None:
    path = tmp_path / "latin1.ftm.jsonl"
    record = _company()
    record["properties"]["name"] = ["Caf\xe9 Example Ltd"]
    path.write_bytes((json.dumps(record, ensure_ascii=False) + "\n").encode("latin-1"))
    with pytest.raises(RecordFileError, match=r"latin1\.ftm\.jsonl:1: not UTF-8"):
        list(iter_records(path))


# Manifest

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


@pytest.mark.parametrize("record_contract", ["1.0.0", "1.1.0"])
def test_manifest_accepts_both_record_contract_versions(record_contract: str) -> None:
    data = {**MANIFEST_EXAMPLE, "record_contract": record_contract}
    assert Manifest.model_validate(data).record_contract == record_contract


def test_record_contract_is_1_1_0() -> None:
    assert versions.RECORD == versions.CONTRACTS == "1.1.0"


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        (("files", 0, "sha256"), "<hex>", "sha256"),
        (("files", 0, "records"), -1, "records"),
        (("files", 0, "rows"), 3, "rows"),
        (("created_at",), "2026-10-23T09:00:00Z\n", "created_at"),
        (("source", "retrieved_at"), "2026-10-23", "retrieved_at"),
        (("dataset",), "nope", "not in contracts/datasets"),
        (("licence", "id"), "CC0-1.0", "licence.id must be 'Apache-2.0'"),
        (("synthetic",), False, "synthetic must be true"),
    ],
)
def test_manifest_rejects_bad_values(path: tuple[Any, ...], value: Any, error: str) -> None:
    data = copy.deepcopy(MANIFEST_EXAMPLE)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError, match=error):
        Manifest.model_validate(data)


@pytest.mark.parametrize(
    ("records", "name", "record_contract"),
    [
        (DEMO, "demo.manifest.json", "1.0.0"),  # the 1.0 example stays as it was written
        (DEMO_1_1, "demo-1.1.manifest.json", versions.RECORD),
    ],
)
def test_demo_manifests_match_their_records(records: Path, name: str, record_contract: str) -> None:
    path = manifest_path(records)
    assert path.name == name
    manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    [entry] = manifest.files
    assert entry.path == records.name
    assert entry.sha256 == hashlib.sha256(records.read_bytes()).hexdigest()
    counts, _ = validate_files([records], strict=True)
    assert entry.records == counts.total()
    assert manifest.counts.by_schema == dict(counts)
    assert manifest.record_contract == record_contract


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
    assert (manifest.licence.id, manifest.synthetic) == ("Apache-2.0", True)
    assert "followthemoney" in manifest.dependencies
    with pytest.raises(ValueError, match=r"not in contracts/datasets\.yaml"):
        write_manifest(records, dataset="nope", producer=Producer(name="t", version="0"))
    with pytest.raises(ValueError, match=r"not a \.ftm\.jsonl file"):
        manifest_path(tmp_path / "records.json")
