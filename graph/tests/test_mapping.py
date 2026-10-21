"""C1 records to C2 rows (neonradar_graph.mapping). Records built here are C1-shaped; the
committed fixture is synthetic and valid in strict mode."""

from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.graph import FLAG_LABELS, NODE_MAPPINGS, RELATIONSHIP_ENDPOINTS
from neonradar_contracts.records import ALLOWED_SCHEMATA, iter_records, validate_files
from neonradar_graph.mapping import (
    MappingResult,
    NodeRow,
    RelationshipRow,
    to_node_rows,
    to_relationship_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"
RECORDS = list(iter_records(FIXTURE))
SUPPORT_TYPES = {"RESOLVED_TO", "FLAGS", "PRODUCED"}


def record(rid: str, schema: str, nr: dict[str, Any] | None = None, **props: Any) -> dict[str, Any]:
    """A record of nr_synthetic (prefix syn) or gb_companies_house (prefix gbch)."""
    synthetic = rid.startswith("syn-")
    data: dict[str, Any] = {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic" if synthetic else "gb_companies_house"],
        "properties": {
            key: value if isinstance(value, list) else [value] for key, value in props.items()
        },
    }
    if synthetic or nr:
        data["nr"] = {"v": "1.0", **({"synthetic": True} if synthetic else {}), **(nr or {})}
    return data


def nodes() -> dict[str, NodeRow]:
    result = to_node_rows(RECORDS)
    assert result.skipped == []
    return {row.id: row for row in result.rows}


def relationships(records: list[dict[str, Any]] | None = None) -> MappingResult[RelationshipRow]:
    return to_relationship_rows(RECORDS if records is None else records)


def by_id(result: MappingResult[RelationshipRow]) -> dict[str, RelationshipRow]:
    return {row.id: row for row in result.rows}


def test_fixture_is_valid_c1_and_covers_every_schema() -> None:
    _, issues = validate_files([FIXTURE], strict=True)
    assert issues == []
    assert {data["schema"] for data in RECORDS} == ALLOWED_SCHEMATA


def test_every_node_schema_and_relationship_type_is_produced() -> None:
    assert {row.schema for row in nodes().values()} == set(NODE_MAPPINGS)
    result = relationships()
    assert result.skipped == []
    assert {row.type for row in result.rows} == set(RELATIONSHIP_ENDPOINTS) - SUPPORT_TYPES


def test_company_node_has_common_and_specific_properties() -> None:
    company = nodes()["syn-co-0001"]
    assert company.labels == ("Entity", "LegalEntity", "Organization", "Company")
    assert company.flags == ("Synthetic", "Sanctioned")
    assert company.props == {
        "id": "syn-co-0001",
        "schema": "Company",
        "caption": "Quillon Marsh Trading Ltd",
        "names": ["Quillon Marsh Trading Ltd"],
        "names_text": "Quillon Marsh Trading Ltd",
        "countries": ["gb"],
        "topics": ["sanction"],
        "datasets": ["nr_synthetic"],
        "referents": ["syn-co-0001"],
        "synthetic": True,
        "source_url": "https://example.org/syn-co-0001",
        "registration_number": "SYN00001",
        "jurisdiction": "gb",
        "legal_form": "Private limited company",
        "incorporation_date": "2019-04-02",
    }
    assert company.as_param() == {
        "id": "syn-co-0001",
        "props": company.props,
        "flags": {"Synthetic": True, "Sanctioned": True, "PEP": False, "RCA": False},
    }


def test_person_address_account_position_and_sanction_nodes() -> None:
    rows = nodes()
    zoe, yara = rows["syn-p-0001"], rows["syn-p-0002"]
    assert zoe.labels == ("Entity", "LegalEntity", "Person")
    assert zoe.flags == ("Synthetic", "PEP")
    assert zoe.props["names"] == ["Zoe Example", "Z. Example"]
    assert zoe.props["names_text"] == "Zoe Example | Z. Example"
    assert zoe.props["nationalities"] == ["gb", "jo"]
    assert (zoe.props["birth_date"], zoe.props["gender"]) == ("1979-08", "female")
    assert "registration_number" not in zoe.props  # Person keeps only its 5.2 properties
    assert yara.flags == ("Synthetic", "RCA")
    assert yara.props["names"] == ["Yara Placeholder", "يارا"]
    address = rows["syn-addr-0001"]
    assert address.labels == ("Entity", "Address")
    assert address.props["names"] == [address.props["full"]]
    assert address.props["postal_code"] == "EX1 2MP"
    assert "address_key" not in address.props  # Phase 2
    account = rows["syn-acct-0001"]
    assert account.labels == ("Entity", "Account")
    assert account.props["caption"] == "NRSYN0000000001"
    assert account.props["account_kind"] == "customer"
    assert (account.props["names"], account.props["names_text"]) == ([], "")
    assert rows["syn-pos-0001"].labels == ("Entity", "Position")
    sanction = rows["syn-sanction-0001"]
    assert sanction.labels == ("Sanction",)
    assert sanction.flags == ("Synthetic",)  # :Synthetic on :Sanction too (I2)
    assert sanction.props["caption"] == "Synthetic programme"
    assert sanction.props["listing_date"] == "2025-02-01"


def test_the_three_ownership_cases_and_share_bands() -> None:
    rows = by_id(relationships())
    owns = rows["syn-ownership-0001"]
    assert (owns.type, owns.source, owns.target) == ("OWNS", "syn-p-0001", "syn-co-0001")
    assert owns.props == {
        "id": "syn-ownership-0001",
        "datasets": ["nr_synthetic"],
        "synthetic": True,
        "share_pct_min": 25.0,
        "share_pct_max": 50.0,
        "percentage_raw": "25-50",
        "role": "ownership-of-shares-25-to-50-percent",
        "natures_of_control": ["ownership-of-shares-25-to-50-percent"],
        "start_date": "2019-04-02",
    }
    holds = rows["syn-ownership-0002"]
    assert (holds.type, holds.source, holds.target) == (
        "HOLDS_ACCOUNT",
        "syn-co-0001",
        "syn-acct-0001",
    )
    assert holds.props["role"] == "account holder"
    consolidates = rows["syn-ownership-0004"]
    assert consolidates.type == "CONSOLIDATES"
    assert consolidates.props["level"] == "direct"
    assert "share_pct_min" not in consolidates.props


def test_holds_account_wins_over_consolidation() -> None:
    records = [
        record("syn-co-1", "Company", name="Example Holdings Ltd"),
        record("syn-acct-1", "BankAccount", accountNumber="NRSYN0000000001"),
        record(
            "syn-ownership-1",
            "Ownership",
            {"consolidation": "ultimate"},
            owner="syn-co-1",
            asset="syn-acct-1",
        ),
    ]
    (row,) = relationships(records).rows
    assert row.type == "HOLDS_ACCOUNT"
    assert "level" not in row.props


def test_paid_goes_from_account_to_account_with_a_utc_ts() -> None:
    paid = by_id(relationships())["syn-payment-000001"]
    assert (paid.type, paid.source, paid.target) == ("PAID", "syn-acct-0001", "syn-acct-0002")
    assert paid.ts == "2026-03-14T10:22:05Z"
    assert paid.props == {
        "id": "syn-payment-000001",
        "datasets": ["nr_synthetic"],
        "synthetic": True,
        "amount": 9500.0,
        "currency": "EUR",
        "channel": "wire",
        "purpose": "Invoice 17",
    }
    assert paid.as_param()["ts"] == "2026-03-14T10:22:05Z"
    assert "payer" not in str(paid.props)  # C2 v1 keeps no payer or beneficiary on PAID


def test_address_roles_default_to_unknown_and_sanction_subjects() -> None:
    rows = by_id(relationships())
    registered = rows["syn-co-0001|addr|syn-addr-0001"]
    assert (registered.type, registered.source, registered.target) == (
        "HAS_ADDRESS",
        "syn-co-0001",
        "syn-addr-0001",
    )
    assert registered.props["role"] == "registered"
    assert rows["syn-le-0001|addr|syn-addr-0001"].props["role"] == "unknown"
    subject = rows["syn-co-0001|sanction|syn-sanction-0001"]
    assert (subject.type, subject.source, subject.target) == (
        "SUBJECT_OF",
        "syn-co-0001",
        "syn-sanction-0001",
    )
    assert subject.props == {"id": subject.id, "datasets": ["nr_synthetic"], "synthetic": True}


@pytest.mark.parametrize(
    ("schema", "type_", "source", "target", "prop", "value"),
    [
        (
            "Control",
            "CONTROLS",
            "syn-le-0001",
            "syn-co-0002",
            "control_type",
            "significant influence",
        ),
        ("Directorship", "DIRECTOR_OF", "syn-p-0001", "syn-co-0001", "is_nominee", True),
        ("Representation", "REPRESENTS", "syn-le-0001", "syn-co-0001", "role", "intermediary"),
        ("Family", "FAMILY_OF", "syn-p-0001", "syn-p-0002", "relationship", "sibling"),
        (
            "Associate",
            "ASSOCIATE_OF",
            "syn-p-0001",
            "syn-p-0002",
            "relationship",
            "business associate",
        ),
        ("Membership", "MEMBER_OF", "syn-co-0002", "syn-org-0001", "role", "member"),
        ("Employment", "EMPLOYED_BY", "syn-p-0002", "syn-pb-0001", "start_date", "2020-09"),
        ("UnknownLink", "LINKED_TO", "syn-p-0002", "syn-co-0002", "role", "contact"),
        ("Succession", "SUCCEEDED_BY", "syn-le-0001", "syn-org-0001", "date", "2024-01"),
        ("Occupancy", "HOLDS_POSITION", "syn-p-0001", "syn-pos-0001", "status", "current"),
    ],
)
def test_edge_schemata(
    schema: str, type_: str, source: str, target: str, prop: str, value: Any
) -> None:
    (row,) = [r for r in relationships().rows if r.id == f"syn-{schema.lower()}-0001"]
    assert (row.type, row.source, row.target, row.props[prop]) == (type_, source, target, value)
    assert row.ts is None


def test_real_records_are_not_synthetic_and_flags_follow_topics() -> None:
    records = [
        record("gbch-co-1", "Company", name="Example Holdings Ltd", topics=["sanction.linked"]),
        record("gbch-p-1", "Person", name="Zoe Example", topics=["role.pep.natl", "role.rca"]),
        record("gbch-p-2", "Person", name="Zoe Example", topics=["sanction", "role.pepx"]),
    ]
    rows = {row.id: row for row in to_node_rows(records).rows}
    assert rows["gbch-co-1"].flags == ()  # sanction.linked does not mean sanctioned
    assert rows["gbch-co-1"].props["synthetic"] is False
    assert rows["gbch-co-1"].props["datasets"] == ["gb_companies_house"]
    assert rows["gbch-p-1"].flags == ("PEP", "RCA")  # role.pep.* is a PEP
    assert rows["gbch-p-2"].flags == ("Sanctioned",)
    assert set(rows["gbch-p-1"].as_param()["flags"]) == set(FLAG_LABELS)


def test_caption_and_first_value() -> None:
    records = [
        record(
            "gbch-co-1", "Company", name="Example Holdings Ltd", registrationNumber=["B2", "A1"]
        ),
        {**record("gbch-co-2", "Company", name="Example Holdings Ltd"), "caption": "Own caption"},
        record("syn-sanction-1", "Sanction", entity="gbch-co-1"),
    ]
    rows = {row.id: row for row in to_node_rows(records).rows}
    assert rows["gbch-co-1"].props["registration_number"] == "B2"  # FtM's stored order
    assert rows["gbch-co-2"].props["caption"] == "Own caption"
    assert rows["syn-sanction-1"].props["caption"] == "Sanction"  # FtM falls back to the label


def test_c1_records_that_c2_cannot_represent_are_skipped() -> None:
    records = [
        record("syn-p-1", "Person", name="Zoe Example"),
        record("syn-co-1", "Company", name="Example Holdings Ltd"),
        record("syn-co-2", "Company", name="Example Holdings Ltd"),
        record(
            "syn-acct-1", "BankAccount", accountNumber="NRSYN0000000001", addressEntity="syn-addr-1"
        ),
        record("syn-addr-1", "Address", full="Unit 4, 12 Example Street, London, EX1 2MP"),
        record(
            "syn-ownership-1",
            "Ownership",
            {"consolidation": "direct"},
            owner="syn-p-1",
            asset="syn-co-1",
        ),
        record("syn-ownership-2", "Ownership", owner=["syn-p-1", "syn-co-2"], asset="syn-co-1"),
        record("syn-unknownlink-1", "UnknownLink", subject="syn-p-1", object="syn-ownership-2"),
    ]
    result = relationships(records)
    assert result.rows == []
    assert [(issue.record_id, issue.message) for issue in result.skipped] == [
        (
            "syn-acct-1",
            "addressEntity on BankAccount records is not mapped"
            " (HAS_ADDRESS starts at a LegalEntity)",
        ),
        (
            "syn-ownership-1",
            "CONSOLIDATES needs a :Organization node as owner; syn-p-1 has schema Person",
        ),
        ("syn-ownership-2", "one relationship needs exactly one owner and one asset (has 2 and 1)"),
        (
            "syn-unknownlink-1",
            "LINKED_TO needs a :Entity node as object; syn-ownership-2 has schema Ownership",
        ),
    ]
    assert "syn-acct-1" in {row.id for row in to_node_rows(records).rows}  # the node stays


def test_duplicate_ids_keep_the_first_record() -> None:
    first = record("syn-co-1", "Company", name="Example Holdings Ltd")
    second = record("syn-co-1", "Person", name="Zoe Example")
    result = to_node_rows([first, second])
    assert [row.schema for row in result.rows] == ["Company"]
    assert [issue.record_id for issue in result.skipped] == ["syn-co-1"]


def test_an_endpoint_outside_the_load_is_left_to_the_loader() -> None:
    (row,) = relationships(
        [record("syn-ownership-1", "Ownership", owner="syn-p-9", asset="syn-co-9")]
    ).rows
    assert (row.type, row.endpoint_labels) == ("OWNS", ("LegalEntity", "LegalEntity"))


def test_mapping_is_deterministic() -> None:
    assert to_node_rows(RECORDS) == to_node_rows(RECORDS)
    assert relationships() == relationships()
