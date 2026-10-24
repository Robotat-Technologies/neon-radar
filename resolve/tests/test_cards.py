"""Record cards (PHASE-2.md 7.3 rule 2, M2.10c deliverable 3). Synthetic records only."""

from __future__ import annotations

import json
import re
from pathlib import Path

from nr_resolve_support import syn

from neonradar_resolve import cards, records


def _folder(tmp_path: Path) -> Path:
    folder = tmp_path / "records"
    folder.mkdir()
    items = [
        syn(
            "syn-card-p1",
            "Person",
            nr={"ch_person_number": "SYN123450001"},
            name="Testa Example",
            alias="Теста Экзампл",
            birthDate="1970-01",
            nationality="gb",
            address="1 Example Road, Manchester, QQ1 2AB",
            addressEntity="syn-card-addr",
            passportNumber="SYNP12345",
        ),
        syn("syn-card-p2", "Person", kind="list", name="Testa Example", topics="sanction"),
        syn(
            "syn-card-addr", "Address", full="2 Example Street", postalCode="qq9 9zz", city="Leeds"
        ),
        syn("syn-card-o1", "Company", name="Example Holder Ltd", registrationNumber="SY000001"),
        syn("syn-card-d1", "Directorship", director="syn-card-p1", organization="syn-card-o1"),
        syn("syn-card-l1", "UnknownLink", subject="syn-card-p1", object="syn-card-p2"),
    ]
    lines = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items)
    (folder / "test.ftm.jsonl").write_text(lines, encoding="utf-8")
    return folder


def test_a_card_shows_what_7_3_lists(tmp_path: Path) -> None:
    found, facts = cards.load([_folder(tmp_path)], {"syn-card-p1", "syn-card-p2", "syn-gone"})
    assert sorted(found) == ["syn-card-p1", "syn-card-p2"]  # an id outside the folders: none
    card = found["syn-card-p1"]
    assert card.dataset == "NeonRadar synthetic data" and card.schema == "Person"
    assert card.names == ("Testa Example", "Теста Экзампл")  # original scripts, as recorded
    assert (card.birth_dates, card.countries) == (("1970-01",), ("gb",))
    assert card.places == ("QQ9 9ZZ, Leeds", "QQ1 2AB, Manchester")
    assert card.organisations == ("Example Holder Ltd (SY000001)",)  # people are not shown
    assert card.identifiers == (
        "passport number: SYNP12345",
        "Companies House person number: SYN123450001",
    )
    assert card.source is not None
    assert facts["syn-card-p1"] == cards.Facts(frozenset(), False)
    assert facts["syn-card-p2"] == cards.Facts(frozenset({"sanction"}), False)


def test_a_card_never_shows_a_probability_rule_method_stratum_or_label(tmp_path: Path) -> None:
    found, _ = cards.load([_folder(tmp_path)], {"syn-card-p1", "syn-card-p2"})
    text = cards.side_by_side(found["syn-card-p1"], found["syn-card-p2"], width=90)
    assert text.splitlines()[0].split() == ["Record", "1", "|", "Record", "2"]
    for word in ("probab", "rule", "method", "stratum", "label", "sanction", "topic", "anchor"):
        assert word not in text.lower(), word
    assert not re.search(r"\b(?:D[1-7]|S[1-4]|X[1-8]|P[1-6])\b", text)
    assert "0." not in text  # no score of any kind
    assert all(len(line) <= 90 for line in text.splitlines())


def test_cards_follow_only_the_record_files_the_run_read(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    inputs = [vars(found) for found in records.read([folder]).inputs]  # as run.json holds them
    assert records.unchanged([folder], inputs)
    path = folder / "test.ftm.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert not records.unchanged([folder], inputs)  # the file changed since the run
    assert not records.unchanged([folder], [])  # a file the run did not read
    assert not records.unchanged([], inputs)  # a file the run read is gone
