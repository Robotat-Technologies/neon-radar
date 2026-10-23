"""The labelling guide's examples come from the synthetic benchmark (PHASE-2.md M2.14).

docs/er/labelling-guide.md shows ten worked examples drawn from data/fixtures/er-bench/, each with
two record ids, the right answer for those cards and the benchmark's answer key. These tests fail
when an id is not a benchmark record (the fixture was regenerated, or an id was mistyped), when a
card's names or linked companies are not its record's, or a name quoted in the guide or in
docs/er/README.md is no longer its record's (record ids survive a renamed record, for example a
name replaced after the OD-12 check), or when an answer key disagrees with labels/er_truth.csv.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from neonradar_resolve import bench

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "er" / "labelling-guide.md"
README = ROOT / "docs" / "er" / "README.md"
BENCH = ROOT / "data" / "fixtures" / "er-bench"
RECORD_ID = re.compile(r"syn-erb-r-[0-9a-f]+")
EXAMPLE = re.compile(r"^### Example (\d+): ", re.MULTILINE)
PAIR = re.compile(r"^\| Record \| `([^`]+)` \| `([^`]+)` \|$", re.MULTILINE)
ROW = re.compile(r"^\| ([^|]+?) \| ([^|]*?) \| ([^|]*?) \|$", re.MULTILINE)
RIGHT = re.compile(r"\*\*Right answer:\*\* `(same|different|unsure)`")
TRUTH = re.compile(r"\*\*Benchmark truth:\*\* `(same|different)`")
# How the cards word an Ownership band: the statute's bounds, as PHASE-2.md 7.2 words them.
BANDS = {
    "25-50": "more than 25 and at most 50 percent",
    "50-75": "more than 50 and less than 75 percent",
    "75-100": "at least 75 percent",
}
# Names quoted outside the cards, each with a record that carries it (the README gives no ids).
QUOTED = {
    GUIDE: {
        "MAKSIM ARSENYEVICH BRAKESBER": "syn-erb-r-5e3efc8464e109f8",
        "BRAKESBER, Maksim Arsenyevich": "syn-erb-r-daffb111ff31d33b",
        "BERBRAFEN, Piotr": "syn-erb-r-1e21284a7654b359",
    },
    README: {
        "TORYUNRIM, Kamal": "syn-erb-r-01548ac5c310a22a",
        "Kamal Toryunrim": "syn-erb-r-2b2c7c4099909742",
        "Marram Leat Catering Ltd": "syn-erb-r-3b67993a796c6d4c",
    },
}


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in BENCH.glob("*.ftm.jsonl"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    records[record["id"]] = record
    return records


def _names(record: dict[str, Any]) -> set[str]:
    properties = record["properties"]
    return {*properties.get("name", []), *properties.get("alias", [])}


def _links(records: dict[str, dict[str, Any]], record_id: str) -> set[str]:
    """The guide's words for each company that the record directs or holds shares in."""
    links: set[str] = set()
    for other in records.values():
        properties = other["properties"]
        if other["schema"] == "Directorship" and properties["director"] == [record_id]:
            how, organisations = properties["role"][0].replace("-", " "), properties["organization"]
        elif other["schema"] == "Ownership" and properties["owner"] == [record_id]:
            how = f"holds {BANDS[properties['percentage'][0]]} of the shares"
            organisations = properties["asset"]
        else:
            continue
        for organisation in organisations:
            links.update(f"{how} of {name}" for name in records[organisation]["properties"]["name"])
    return links


def _examples() -> dict[int, str]:
    """Example number to its text, from the worked examples section to the next section."""
    text = _guide()
    section = text.split("\n## Worked examples\n", 1)[1].split("\n## ", 1)[0]
    starts = list(EXAMPLE.finditer(section))
    return {
        int(match.group(1)): section[match.start() : nxt.start() if nxt else len(section)]
        for match, nxt in zip(starts, [*starts[1:], None], strict=True)
    }


def test_every_record_id_in_the_guide_is_a_benchmark_record() -> None:
    mentioned = set(RECORD_ID.findall(_guide()))
    assert mentioned, "the guide names no benchmark record"
    assert sorted(mentioned - set(_records())) == []


def test_ten_worked_examples_each_with_one_pair_and_both_answers() -> None:
    examples = _examples()
    assert sorted(examples) == list(range(1, 11))
    for number, text in examples.items():
        assert len(PAIR.findall(text)) == 1, f"example {number}: one Record row with two ids"
        assert len(RIGHT.findall(text)) == 1, f"example {number}: one right answer"
        assert len(TRUTH.findall(text)) == 1, f"example {number}: one benchmark truth"


def test_each_card_shows_the_names_and_linked_companies_of_its_record() -> None:
    records = _records()
    for number, text in _examples().items():
        rows = {label: (a, b) for label, a, b in ROW.findall(text)}
        ((a, b),) = PAIR.findall(text)
        for side, record_id in enumerate((a, b)):
            record, where = records[record_id], f"example {number}, {record_id}"
            name, _, aliases = rows["Name"][side].partition("; also ")
            assert name in record["properties"]["name"], where
            assert {name, *filter(None, aliases.split(", "))} == _names(record), where
            if "Linked companies" in rows:
                cell = rows["Linked companies"][side]
                shown = set() if cell == "none shown" else set(cell.split("; "))
                assert shown == _links(records, record_id), where


def test_names_quoted_outside_the_cards_are_their_records_names() -> None:
    records = _records()
    for doc, quoted in QUOTED.items():
        text = doc.read_text(encoding="utf-8")
        for name, record_id in quoted.items():
            assert f'"{name}"' in text, f"{doc.name} no longer quotes {name!r}"
            assert name in _names(records[record_id]), f"{doc.name}: {record_id}"


def test_answer_keys_match_the_benchmark_truth() -> None:
    truth = bench.read_truth(BENCH / "labels" / "er_truth.csv")
    for number, text in _examples().items():
        ((a, b),) = PAIR.findall(text)
        assert a != b and a in truth and b in truth, f"example {number}: two resolvable records"
        same = truth[a].entity == truth[b].entity
        key = TRUTH.search(text)
        right = RIGHT.search(text)
        assert key is not None and right is not None
        assert key.group(1) == ("same" if same else "different"), f"example {number}"
        # A right answer may be `unsure` when the cards do not decide; otherwise it is the key.
        assert right.group(1) in ("unsure", key.group(1)), f"example {number}"


def test_the_examples_cover_each_answer() -> None:
    answers = {m.group(1) for text in _examples().values() for m in RIGHT.finditer(text)}
    assert answers == {"same", "different", "unsure"}
