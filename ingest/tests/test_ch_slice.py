"""The company slice (PHASE-2.md M2.3a deliverable 5), on an index built in the test.

Company numbers are invented (`T` plus digits, never a Companies House form) and districts use
the `QQ` area, which has no real postcodes.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_ingest.sources.companies_house.build import CompaniesBlock
from neonradar_ingest.sources.companies_house.slice import Member


def index(path: Path, rows: list[tuple[str, str]]) -> Path:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE company(number TEXT PRIMARY KEY, name TEXT, district TEXT,"
                       " category TEXT, status TEXT, origin TEXT)")  # fmt: skip
    connection.executemany("INSERT INTO company VALUES (?, '', ?, '', '', '')", rows)
    connection.commit()
    connection.close()
    return path


def block(**values: Any) -> CompaniesBlock:
    defaults = {"seeds": [], "postcode_districts": ["QQ1", "QQ2"], "max_per_district": 3,
                "max_companies": 100, "sample_seed": 20261026}  # fmt: skip
    return CompaniesBlock.model_validate(defaults | values)


ROWS = [(f"T{n:07d}", "QQ1" if n % 2 else "QQ2") for n in range(1, 21)]


def run(tmp_path: Path, rows: list[tuple[str, str]] = ROWS, **values: Any) -> tuple[Any, str]:
    return slices.build_slice(index(tmp_path / "companies.sqlite", rows), block(**values),
                              tmp_path / "slice.csv")  # fmt: skip


def test_the_sample_hash_is_sha256_of_seed_and_number() -> None:
    expected = hashlib.sha256(b"20261026|T0000001").hexdigest()
    assert slices.sample_hash(20261026, "T0000001") == expected


def test_the_district_sample_is_deterministic_and_independent_of_row_order(tmp_path: Path) -> None:
    for name in "abc":
        (tmp_path / name).mkdir()
    counts, first = run(tmp_path / "a")
    _, second = run(tmp_path / "b", list(reversed(ROWS)))
    assert first == second
    district = dict(ROWS)
    chosen = {n for n, _, _ in slices.read(tmp_path / "a" / "slice.csv") if district[n] == "QQ1"}
    lowest = sorted((slices.sample_hash(20261026, n), n) for n, d in ROWS if d == "QQ1")[:3]
    assert chosen == {n for _, n in lowest}
    assert counts["by_district"] == {"qq1": 3, "qq2": 3}
    _, other_seed = run(tmp_path / "c", sample_seed=1)
    assert other_seed != first


def test_seeds_are_always_kept_and_missing_ones_are_reported(tmp_path: Path) -> None:
    counts, _ = run(tmp_path, seeds=["T0000001", "T0000099"], max_companies=1)
    assert sorted(n for n, _, _ in slices.read(tmp_path / "slice.csv")) == ["T0000001", "T0000099"]
    assert counts["seeds_missing_from_index"] == 1
    assert counts["companies"] == 2 and counts["cap_removed"] >= 5
    assert counts["by_reason"] == {"seed": 2, "district": 0, "parent": 0, "child": 0}


def test_a_company_reached_twice_keeps_the_first_reason_at_its_lowest_level() -> None:
    merged = slices.merge([Member("T1", "child", 1, "a"), Member("T1", "parent", 3, "a"),
                           Member("T1", "parent", 2, "a"), Member("T2", "district", 0, "b"),
                           Member("T2", "seed", 0, "b")])  # fmt: skip
    assert merged == {"T1": Member("T1", "parent", 2, "a"), "T2": Member("T2", "seed", 0, "b")}


def test_the_cap_removes_deep_expansion_then_high_hash_districts_never_seeds() -> None:
    members = slices.merge([
        Member("S1", "seed", 0, "f"), Member("D1", "district", 0, "1"),
        Member("D2", "district", 0, "9"), Member("P1", "parent", 1, "8"),
        Member("P2", "parent", 2, "0"), Member("C1", "child", 1, "2"),
    ])  # fmt: skip
    order = []
    for size in range(5, -1, -1):
        kept, removed = slices.cap(members, size)
        order.append(sorted(m.number for m in kept))
        assert removed == 6 - max(size, 1)
    assert order == [
        ["C1", "D1", "D2", "P1", "S1"],  # P2: the deepest level
        ["C1", "D1", "D2", "S1"],  # P1: level 1, the higher hash
        ["D1", "D2", "S1"],
        ["D1", "S1"],  # then districts, the highest hash first
        ["S1"],
        ["S1"],  # never a seed
    ]


def test_slice_csv_is_ordered_by_reason_level_hash_and_number(tmp_path: Path) -> None:
    members = [Member("D1", "district", 0, "1"), Member("C1", "child", 1, "2"),
               Member("P2", "parent", 2, "0"), Member("P1", "parent", 1, "8"),
               Member("P3", "parent", 1, "8"), Member("S1", "seed", 0, "f")]  # fmt: skip
    digest = slices.write(tmp_path / "slice.csv", members)
    text = (tmp_path / "slice.csv").read_text(encoding="utf-8")
    assert text == (
        "company_number,reason,level\nS1,seed,0\nP1,parent,1\nP3,parent,1\nP2,parent,2\n"
        "C1,child,1\nD1,district,0\n"
    )
    assert digest == hashlib.sha256(text.encode()).hexdigest()
    assert slices.read(tmp_path / "slice.csv")[1] == ("P1", "parent", 1)
