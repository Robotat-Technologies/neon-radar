"""OpenSanctions to C1 mapping, offline, on a synthetic fixture (PHASE-1.md M1.8d step 2).

`fixtures/opensanctions/entities.ftm.json` is shaped like OpenSanctions' export: one entity per
line, `id` first, the legacy `target` key, lists of source datasets, referents, a PEP with a
Position and an Occupancy, a Family link, a Sanction, a schema outside C1 v1 and one unknown to
FollowTheMoney 4.11. Every name, id and dataset in it is a synthetic placeholder.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import SYNTHETIC_TOPICS, validate_batch, validate_record
from neonradar_ingest.sources.opensanctions.mapping import (
    DATASET,
    FLAG_LABELS,
    MALFORMED,
    NOT_JSON,
    MappingStats,
    flag_labels,
    map_entity,
    map_lines,
    record_id,
    seen_timestamp,
)

FIXTURES = Path(__file__).parent / "fixtures" / "opensanctions"
ENTITIES = FIXTURES / "entities.ftm.json"
EXPECTED = FIXTURES / "entities.expected.json"


def _map_fixture() -> tuple[list[dict[str, Any]], MappingStats]:
    stats = MappingStats()
    records = list(map_lines(ENTITIES.read_text(encoding="utf-8").splitlines(), stats))
    return records, stats


def _by_source(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["nr"]["source_ref"]: record for record in records}


def test_fixture_maps_to_the_expected_records() -> None:
    records, _ = _map_fixture()
    assert records == json.loads(EXPECTED.read_text(encoding="utf-8"))


def test_mapped_records_pass_c1_in_strict_mode() -> None:
    records, _ = _map_fixture()
    assert [issue for record in records for issue in validate_record(record)] == []
    assert validate_batch(records, strict=True) == []


def test_counts_schemata_skips_and_dropped_keys() -> None:
    _, stats = _map_fixture()
    assert stats.lines == 12
    assert stats.mapped == Counter(
        Person=3, Company=1, Address=1, Position=1, Occupancy=1, Family=1, Sanction=1, Ownership=1
    )
    assert stats.skipped == Counter(Identification=1, SynthFutureSchema=1)
    assert stats.unknown_schemata == Counter(SynthFutureSchema=1)
    assert stats.dropped_keys == Counter(target=10)
    assert stats.dropped_properties == Counter({"Person:synthFutureProperty": 1})
    assert stats.source_datasets == Counter(syn_example_peps=6, syn_example_sanctions=5)


def test_envelope_follows_c1() -> None:
    records, _ = _map_fixture()
    for record in records:
        assert "target" not in record
        assert record["datasets"] == [DATASET]
        assert record["id"].startswith("os-ent-")
        assert record["id"] == record_id(record["nr"]["source_ref"])
        assert set(record["nr"]) == {"v", "source_ref"}  # never nr.synthetic (R6)


def test_ids_references_and_referents_share_the_os_namespace() -> None:
    by_source = _by_source(_map_fixture()[0])
    occupancy = by_source["syn-os-occupancy-01"]["properties"]
    assert occupancy["holder"] == [by_source["NK-synPersonAlpha"]["id"]]
    assert occupancy["post"] == [by_source["syn-os-position_01"]["id"]]
    assert by_source["syn-os-position_01"]["id"] == "os-ent-syn-os-position.01"  # `_` -> `.`
    family = by_source["syn-os-family-01"]["properties"]
    assert family["person"] == ["os-ent-NK-synPersonAlpha"]
    assert family["relative"] == ["os-ent-NK-synPersonBeta"]
    assert by_source["syn-os-sanction-01"]["properties"]["entity"] == ["os-ent-NK-synPersonGamma"]
    assert by_source["NK-synPersonAlpha"]["referents"] == [
        "os-ent-syn-os-src-alpha-1",
        "os-ent-syn-os-src.alpha.2",
    ]
    assert "referents" not in by_source["NK-synPersonBeta"]


def test_topics_set_the_c2_flag_labels() -> None:
    records, stats = _map_fixture()
    flags = {
        record["nr"]["source_ref"]: flag_labels(record["properties"].get("topics", []))
        for record in records
    }
    assert flags["NK-synPersonAlpha"] == {"PEP"}
    assert flags["NK-synPersonBeta"] == {"RCA"}
    assert flags["NK-synPersonGamma"] == {"Sanctioned"}
    assert flags["NK-synCompanyDelta"] == set()  # sanction.linked sets no flag
    assert flags["syn-os-position_01"] == set()
    assert stats.flags == Counter(PEP=1, RCA=1, Sanctioned=1)
    assert stats.topics["gov.national"] == 1


def test_flag_topics_match_the_record_contract() -> None:
    assert set(FLAG_LABELS) == SYNTHETIC_TOPICS


def test_strings_become_nfc_and_timestamps_utc() -> None:
    by_source = _by_source(_map_fixture()[0])
    assert by_source["NK-synPersonGamma"]["properties"]["alias"] == ["Synthétic Person Gamma"]
    alpha = by_source["NK-synPersonAlpha"]
    assert alpha["first_seen"] == "2025-08-22T10:15:20"
    assert alpha["last_change"] == "2026-03-01T07:00:00"  # +02:00 converted to UTC


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025-08-22T10:15:20+00:00", "2025-08-22T10:15:20"),
        ("2025-08-22T10:15:20Z", "2025-08-22T10:15:20"),
        ("2025-08-22T10:15:20", "2025-08-22T10:15:20"),
        ("2025-08", "2025-08"),
        ("not a date", None),
        (None, None),
    ],
)
def test_seen_timestamp(value: object, expected: str | None) -> None:
    assert seen_timestamp(value) == expected


def test_odd_source_ids_are_hashed_consistently() -> None:
    stats = MappingStats()
    person = map_entity(
        {"id": "syn os/person 1", "schema": "Person", "properties": {"name": ["Synthetic Odd"]}},
        stats,
    )
    reference = {"entity": ["syn os/person 1"]}
    sanction = map_entity(
        {"id": "syn-os-sanction-9", "schema": "Sanction", "properties": reference}, stats
    )
    assert person is not None and sanction is not None
    assert person["id"].startswith("os-ent-") and len(person["id"]) == len("os-ent-") + 20
    assert sanction["properties"]["entity"] == [person["id"]]
    assert person["nr"]["source_ref"] == "syn os/person 1"
    assert validate_batch([person, sanction], strict=True) == []


def test_values_that_followthemoney_rejects_are_dropped_and_counted() -> None:
    stats = MappingStats()
    record = map_entity(
        {
            "id": "syn-os-person-9",
            "schema": "Person",
            "properties": {
                "name": ["Synthetic Person Nine"],
                "birthDate": ["1980-02", "not a date"],
                "nationality": ["gb", "Atlantis"],
                "topics": ["role.pep", "not.a.topic"],
            },
        },
        stats,
    )
    assert record is not None
    assert record["properties"]["birthDate"] == ["1980-02"]
    assert record["properties"]["nationality"] == ["gb"]
    assert record["properties"]["topics"] == ["role.pep"]
    assert stats.dropped_values == Counter(
        {"Person:birthDate": 1, "Person:nationality": 1, "Person:topics": 1}
    )
    assert validate_record(record) == []


def test_payments_are_skipped_because_c1_keeps_them_synthetic() -> None:
    stats = MappingStats()
    payment = {"id": "syn-os-pay-1", "schema": "Payment", "properties": {"amount": ["10"]}}
    assert map_entity(payment, stats) is None
    assert stats.skipped == Counter(Payment=1)


def test_bad_lines_are_counted_and_the_limit_counts_lines() -> None:
    stats = MappingStats()
    lines = [
        "",
        "not json",
        "[1, 2]",
        json.dumps({"id": "syn-os-x", "schema": "Person", "properties": {"name": "not a list"}}),
        json.dumps({"schema": "Person", "properties": {}}),
        *ENTITIES.read_text(encoding="utf-8").splitlines(),
    ]
    records = list(map_lines(lines, stats, limit=6))
    assert stats.lines == 6
    assert stats.skipped == Counter({NOT_JSON: 2, MALFORMED: 2})
    sources = [record["nr"]["source_ref"] for record in records]
    assert sources == ["NK-synPersonAlpha", "NK-synPersonBeta"]  # 4 bad lines, then 2 entities


def test_bytes_lines_are_decoded() -> None:
    stats = MappingStats()
    lines = ENTITIES.read_bytes().splitlines()
    assert len(list(map_lines(lines, stats))) == 10
