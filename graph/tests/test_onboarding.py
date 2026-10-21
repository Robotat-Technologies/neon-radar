"""Unit tests for the Assignment 1 sandbox: the CSV, its design, and the first-queries format."""

import re
from collections import Counter
from pathlib import Path
from typing import cast

import pytest
from neo4j import Driver

from neonradar_graph.onboarding import (
    CSV_PATH,
    HEADER,
    QUERIES_PATH,
    Counts,
    Entry,
    OnboardingError,
    QueryResult,
    check_queries,
    expected_counts,
    parse_first_queries,
    read_rows,
)


def test_the_csv_has_twenty_synthetic_rows_with_onboarding_ids() -> None:
    rows = read_rows(CSV_PATH)
    assert len(rows) == 20
    assert all(row["synthetic"] == "true" for row in rows)
    assert [row["company_id"] for row in rows] == [f"onb-co-{n:02d}" for n in range(1, 21)]
    assert all(re.fullmatch(r"onb-p-\d\d", str(row["director_id"])) for row in rows)
    assert expected_counts(rows) == Counts(companies=20, people=15, addresses=16)


def test_the_csv_makes_two_hop_questions_interesting() -> None:
    rows = read_rows(CSV_PATH)
    directors = Counter(row["director_id"] for row in rows)
    addresses = Counter(row["registered_address"] for row in rows)
    parents = {row["company_id"]: row["parent_company_id"] for row in rows}
    assert sum(1 for count in directors.values() if count > 1) >= 3  # shared directors
    assert sorted(count for count in addresses.values() if count > 1) == [5]  # one shared address
    assert {parent for parent in parents.values() if parent} <= set(parents)
    chains = [c for c, p in parents.items() if p and parents.get(p)]  # child of a child
    assert chains == ["onb-co-03"]
    assert parents["onb-co-03"] == "onb-co-02"
    assert parents["onb-co-02"] == "onb-co-01"
    assert not parents["onb-co-01"]


def test_one_name_per_id() -> None:
    rows = read_rows(CSV_PATH)
    names: dict[str | None, set[str | None]] = {}
    for row in rows:
        names.setdefault(row["director_id"], set()).add(row["director_name"])
    assert all(len(found) == 1 for found in names.values())
    assert len({row["company_name"] for row in rows}) == 20


def write_csv(tmp_path: Path, header: list[str], *rows: list[str]) -> Path:
    path = tmp_path / "companies.csv"
    path.write_text("\n".join(",".join(line) for line in (header, *rows)) + "\n")
    return path


def test_read_rows_rejects_another_header(tmp_path: Path) -> None:
    path = write_csv(tmp_path, HEADER[1:], ["onb-co-01"] + [""] * 7)
    with pytest.raises(OnboardingError, match="header is"):
        read_rows(path)


def test_read_rows_rejects_a_row_that_is_not_synthetic(tmp_path: Path) -> None:
    row = ["false", "onb-co-01", "A Ltd", "gb", "2020-01-01", "onb-p-01", "A B", "1 Street", ""]
    with pytest.raises(OnboardingError, match=r"companies\.csv:2: synthetic is not 'true'"):
        read_rows(write_csv(tmp_path, HEADER, row))


def test_read_rows_turns_empty_fields_into_none(tmp_path: Path) -> None:
    row = ["true", "onb-co-01", "A Ltd", "gb", "2020-01-01", "onb-p-01", "A B", "1 Street", ""]
    assert read_rows(write_csv(tmp_path, HEADER, row))[0]["parent_company_id"] is None


def test_the_committed_first_queries_file_is_well_formed() -> None:
    entries = parse_first_queries(QUERIES_PATH.read_text(encoding="utf-8"))
    assert entries[0].handle == "@example"
    assert [(entry.handle, entry.problem) for entry in entries if entry.problem] == []
    assert "REGISTERED_AT" in entries[0].queries[0]


FILE = """\
# First queries

```cypher
MATCH (n) RETURN n
```

## Format

## @alice

```cypher
MATCH (a)-[:R]->(b)-[:R]->(c)
RETURN c
```

### a sub-heading keeps the section open

Two hops because...

## @bob

No query here.

## @carol

```cypher
RETURN 1
```

```text
## @not-a-heading
```

```cypher
RETURN 2
```

## @alice

```cypher
RETURN 3
```

## @-bad-

```cypher
RETURN 4
```

## Notes

```cypher
RETURN 5
```

## @dave

```cypher

```

## @frank

```cypher
LOAD CSV FROM 'https://example.org/x.csv' AS row RETURN row
```

## @grace

```cypher
MATCH (c) call { WITH c RETURN 1 AS one } RETURN c
```

## @heidi

```cypher
RETURN apoc.version()
```

## @erin

```cypher
RETURN 6
"""


REFUSED = "not allowed: first queries may not use LOAD CSV, apoc. or CALL"


def test_parse_first_queries_reports_each_section() -> None:
    entries = {(entry.handle, entry.line): entry for entry in parse_first_queries(FILE)}
    by_handle = [(handle, entry.problem) for (handle, _), entry in entries.items()]
    assert by_handle == [
        ("@alice", None),
        ("@bob", "format: expected one ```cypher block, found 0"),
        ("@carol", "format: expected one ```cypher block, found 2"),
        ("@alice", "format: a second section for @alice"),
        ("@-bad-", "format: '@-bad-' is not a GitHub handle"),
        ("@dave", "format: the ```cypher block is empty"),
        ("@frank", REFUSED),
        ("@grace", REFUSED),
        ("@heidi", REFUSED),
        ("@erin", "format: a code block is not closed"),
    ]
    alice = entries[("@alice", 9)]
    assert alice.queries == ["MATCH (a)-[:R]->(b)-[:R]->(c)\nRETURN c"]


def test_query_result_lines() -> None:
    assert QueryResult("@a", rows=4).line() == "OK    @a  ran, 4 rows returned"
    assert QueryResult("@a", error="X: y").line() == "FAIL  @a  X: y"


def test_a_refused_query_is_reported_and_never_sent() -> None:
    query = "LOAD CSV FROM 'https://example.org/x.csv' AS row RETURN row"
    entry = parse_first_queries(f"## @frank\n\n```cypher\n{query}\n```\n")[0]
    assert entry == Entry("@frank", 1, [query], REFUSED)
    no_database = cast(Driver, object())  # any use of the driver would raise AttributeError
    assert check_queries(no_database, [entry]) == [QueryResult("@frank", error=REFUSED)]
