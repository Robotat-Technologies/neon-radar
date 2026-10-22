"""The synthetic entity resolution benchmark (PHASE-2.md M2.9 deliverable 11)."""

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest
from faker.providers.person import ar_SA, en_GB, ru_RU
from followthemoney import model

from neonradar_contracts.records import iter_records, validate_files
from neonradar_ingest.synth import ER_BENCH_SEED, erbench, variants
from neonradar_ingest.synth.erbench import KIND, RATES, SHARES, STEM, build, write_er_bench
from neonradar_ingest.synth.names import fold, is_denied
from neonradar_keys.ids import is_valid_lei, uk_company_number
from neonradar_keys.postcodes import normalise_uk_postcode

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "er-bench"
OUTPUTS = (f"{STEM}.ftm.jsonl", "labels/er_truth.csv")
RESOLVABLE = ("Person", "LegalEntity", "Company", "Organization", "PublicBody")
NAME_PROPS = ("name", "alias", "firstName", "middleName", "lastName")
TOLERANCE = 0.03  # 3 percentage points on `large`
# On the committed fixture (at 41de481): 654 lastName values of exposed people and 518 list and
# leak name tokens other than given and middle names. A bound below each catches a check that
# silently stops looking.
LAST_NAMES_CHECKED, TOKENS_CHECKED = 600, 450


def _digests(folder: Path) -> dict[str, str]:
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in OUTPUTS}


def _manifest(folder: Path) -> dict[str, Any]:
    data = json.loads((folder / f"{STEM}.manifest.json").read_text(encoding="utf-8"))
    data.pop("created_at")
    return dict(data)


def _truth(folder: Path) -> list[dict[str, str]]:
    lines = (folder / "labels" / "er_truth.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# synthetic: true"
    assert lines[1] == ",".join(erbench.TRUTH_COLUMNS)
    return list(csv.DictReader(lines[1:]))


@pytest.fixture(scope="module")
def records() -> list[dict[str, Any]]:
    return list(iter_records(FIXTURE / f"{STEM}.ftm.jsonl"))


@pytest.fixture(scope="module")
def truth() -> list[dict[str, str]]:
    return _truth(FIXTURE)


@pytest.fixture(scope="module")
def small() -> erbench.Bench:
    return build("small", ER_BENCH_SEED)


@pytest.fixture(scope="module")
def large() -> erbench.Bench:
    return build("large", ER_BENCH_SEED)


def test_same_seed_gives_the_same_bytes(tmp_path: Path) -> None:
    write_er_bench(tmp_path / "a", "small", ER_BENCH_SEED)
    write_er_bench(tmp_path / "b", "small", ER_BENCH_SEED)
    assert _digests(tmp_path / "a") == _digests(tmp_path / "b")
    assert _manifest(tmp_path / "a") == _manifest(tmp_path / "b")


def test_committed_fixture_equals_a_fresh_generation(tmp_path: Path) -> None:
    """Fails when the code, Faker or numpy changed the output: run `make fixtures`, then list
    the new names for the Companies House check (OD-12)."""
    write_er_bench(tmp_path, "small", ER_BENCH_SEED)
    assert _digests(FIXTURE) == _digests(tmp_path)
    assert _manifest(FIXTURE) == _manifest(tmp_path)


def test_the_fixture_validates_in_strict_mode() -> None:
    counts, issues = validate_files([FIXTURE / f"{STEM}.ftm.jsonl"], strict=True)
    assert issues == []
    assert counts["Person"] > 0 and counts["Sanction"] > 0


def test_every_resolvable_record_has_exactly_one_truth_row(
    records: list[dict[str, Any]], truth: list[dict[str, str]]
) -> None:
    rows = Counter(row["record_id"] for row in truth)
    assert set(rows.values()) == {1}
    resolvable = {r["id"] for r in records if r["schema"] in RESOLVABLE}
    assert set(rows) == resolvable
    people = {row["entity_id"] for row in truth if row["class"] == "person"}
    orgs = {row["entity_id"] for row in truth if row["class"] == "org"}
    assert (len(people), len(orgs)) == erbench.SIZES["small"]
    for row in truth:
        assert re.fullmatch(r"syn-erb-r-[0-9a-f]{16}", row["record_id"])  # opaque (2.7)
        assert row["style"] in KIND


def test_every_id_is_synthetic(records: list[dict[str, Any]]) -> None:
    for record in records:
        assert record["id"].startswith("syn-")
        assert record["datasets"] == ["nr_synthetic"]
        assert record["nr"]["synthetic"] is True
        assert record["nr"]["v"] == "1.1"


def test_each_record_has_the_kind_of_its_style(
    records: list[dict[str, Any]], truth: list[dict[str, str]]
) -> None:
    by_id = {r["id"]: r for r in records}
    for row in truth:
        assert by_id[row["record_id"]]["nr"]["synthetic_kind"] == KIND[row["style"]]
    styles = {row["record_id"]: row["style"] for row in truth}
    sanctions = [r for r in records if r["schema"] == "Sanction"]
    assert sanctions
    for sanction in sanctions:
        assert sanction["nr"]["synthetic_kind"] == "list"
        assert styles[sanction["properties"]["entity"][0]] == "list"
    listed = {r["id"] for r in records if r["properties"].get("topics")}
    assert listed == {row["record_id"] for row in truth if row["style"] == "list"}
    assert listed == {s["properties"]["entity"][0] for s in sanctions}


def test_no_entity_has_two_list_records_under_one_authority(
    records: list[dict[str, Any]], truth: list[dict[str, str]]
) -> None:
    entity = {row["record_id"]: row["entity_id"] for row in truth}
    seen = Counter(
        (entity[s["properties"]["entity"][0]], s["properties"]["authority"][0])
        for s in records
        if s["schema"] == "Sanction"
    )
    assert max(seen.values()) == 1
    assert {authority for _, authority in seen} == set(erbench.AUTHORITIES)


def test_every_sy_number_comes_with_jurisdiction_gb(records: list[dict[str, Any]]) -> None:
    numbered = [r for r in records if r["properties"].get("registrationNumber")]
    assert numbered
    for record in numbered:
        (number,) = record["properties"]["registrationNumber"]
        assert number.startswith("SY") and len(number) == 8
        assert uk_company_number(number, synthetic=True) == number
        assert uk_company_number(number) is None  # never a real Companies House number
        assert record["properties"]["jurisdiction"] == ["gb"]


def test_identifiers_and_postcodes_are_well_formed(records: list[dict[str, Any]]) -> None:
    leis = [lei for r in records for lei in r["properties"].get("leiCode", [])]
    assert leis and all(lei.startswith("SYN0") and is_valid_lei(lei) for lei in leis)
    assert erbench.lei_check_digits("SYN0000000000000AB") == "65"  # the M2.6a test value
    for record in records:
        for text in record["properties"].get("address", []):
            code = text.rsplit(", ", 1)[1]
            assert code.startswith("QQ") and normalise_uk_postcode(code) == code
        for unsc in record["properties"].get("unscId", []):
            assert (
                unsc[:6] in ("ZZi.99", "ZZe.99") and len(unsc) == 10
            )  # no real regime or reference
        for authority_id in record["properties"].get("authorityId", []):
            assert authority_id[:5] in ("SYA-9", "SYB-9", "SYC-9") and len(authority_id) == 10
        number = record["nr"].get("ch_person_number")
        if number is not None:
            assert number.startswith("SYN") and len(number) == 12


def test_hard_negatives_exist_and_differ_from_their_twins(
    records: list[dict[str, Any]], truth: list[dict[str, str]]
) -> None:
    entities = {row["entity_id"] for row in truth}
    twin = {row["entity_id"]: row["twin_of"] for row in truth if row["twin_of"]}
    for entity, other in twin.items():
        assert other in entities and other != entity
        assert twin[other] == entity  # set on both sides
    people = sum(e.startswith("syn-erb-p-") for e in twin) // 2
    orgs = sum(e.startswith("syn-erb-o-") for e in twin) // 2
    assert people == round(600 * SHARES["twin"]) and orgs == round(300 * SHARES["org_twin"])


def test_twins_share_their_names_but_not_their_identity(large: erbench.Bench) -> None:
    people = {p.number: p for p in large.people}
    for twin in (p for p in large.people if p.twin_of):
        original = people[twin.twin_of]
        assert (twin.given, twin.surname) == (original.given, original.surname)
        assert twin.birth.year == original.birth.year and twin.birth != original.birth
        assert twin.person_numbers != original.person_numbers
    orgs = {o.number: o for o in large.orgs}
    for twin in (o for o in large.orgs if o.twin_of):
        original = orgs[twin.twin_of]
        assert twin.core == original.core and twin.form != original.form
        assert twin.company_number != original.company_number


def test_no_generated_name_contains_a_denylisted_name(
    records: list[dict[str, Any]], large: erbench.Bench
) -> None:
    names = [v for r in records for p in NAME_PROPS for v in r["properties"].get(p, [])]
    names += [v for r in large.records for p in NAME_PROPS for v in r.props.get(p, [])]
    assert len(names) > 10_000
    assert [name for name in names if is_denied(name)] == []


def test_invented_surnames_avoid_the_known_real_ones(large: erbench.Bench) -> None:
    real = {fold(name) for name in variants.NOT_INVENTED}
    for person in large.people:
        if person.invented:
            assert not {fold(form) for form in person.surname.latin} & real


def _faker_surnames() -> set[str]:
    faker = {fold(n) for n in en_GB.Provider.last_names}
    faker |= {fold(n) for n in (*ru_RU.Provider.last_names, *ar_SA.Provider.last_names)}
    faker |= {fold(n.removeprefix("آل ")) for n in ar_SA.Provider.last_names}
    return faker | {fold(n) for n in variants.NOT_INVENTED}


def _exposed(truth: list[tuple[str, str, str, str, str]], links: list[tuple[str, str]]) -> set[str]:
    """People with a list or leak record, officers and PSCs of an organisation that has one or
    whose near twin has one, and the near twins of any of these people: worked out from the
    output (styles, links and the truth file's `twin_of`), not from the generator."""
    entity = {row[0]: row[1] for row in truth}
    styles: dict[str, set[str]] = defaultdict(set)
    for _, entity_id, _, style, _ in truth:
        styles[entity_id].add(style)
    twins = {row[1]: row[4] for row in truth if row[4]}  # set on both sides
    flagged = {e for e, s in styles.items() if s & {"list", "leak"}}
    orgs = {e for e in flagged if "-o-" in e}
    orgs |= {twins[e] for e in orgs if e in twins}
    people = {e for e in flagged if "-p-" in e}
    people |= {entity[a] for a, b in links if "-p-" in entity[a] and entity[b] in orgs}
    return people | {twins[e] for e in people if e in twins}


def _links(records: list[tuple[str, dict[str, list[str]]]]) -> list[tuple[str, str]]:
    links = []
    for schema, props in records:
        if schema in ("Directorship", "Ownership"):
            source = (props.get("director") or props["owner"])[0]
            links.append((source, (props.get("organization") or props["asset"])[0]))
    return links


@pytest.mark.parametrize("size", ["small", "large"])
def test_people_on_or_linked_to_list_and_leak_entities_have_invented_surnames(
    size: str, request: pytest.FixtureRequest
) -> None:
    """G1: Faker surnames only for registry-only people with no link to a list or leak entity
    (or to the near twin of one); checked on every person record as it shows the name."""
    bench: erbench.Bench = request.getfixturevalue(size)
    faker = _faker_surnames()
    exposed = _exposed(bench.truth, _links([(r.schema, r.props) for r in bench.records]))
    entity = {row[0]: row[1] for row in bench.truth}
    people = {p.entity_id: p for p in bench.people}
    listed = {row[1] for row in bench.truth if row[2] == "person" and row[3] in ("list", "leak")}
    assert listed < exposed  # links and twins reach beyond the list and leak records
    assert len(bench.shown) == sum(row[2] == "person" for row in bench.truth)
    for record_id, shown in bench.shown.items():
        person = people[entity[record_id]]
        # Every exposed person is invented; the generator may invent more (a person whose
        # possible organisations include an exposed one, even if no record links them).
        assert person.invented or person.entity_id not in exposed, person.entity_id
        if person.invented:
            assert fold(shown.surname) not in faker, record_id
            assert erbench.surname_ok(shown.surname), record_id
            assert not is_denied(f"{shown.given} {shown.surname}"), record_id
    for person in bench.people:
        if person.invented:
            for form in person.surname.latin:
                assert erbench.surname_ok(form), (person.entity_id, form)
            assert person.surname.native is None or erbench.surname_ok(person.surname.native)
    assert sum(p.invented for p in bench.people) > len(bench.people) // 4


def test_the_fixture_shows_no_real_surname_for_exposed_people(
    records: list[dict[str, Any]], truth: list[dict[str, str]], small: erbench.Bench
) -> None:
    """The committed records themselves: every lastName of an exposed person, and every token
    of the names and aliases of list and leak records other than given and middle names,
    passes `surname_ok`."""
    rows = [(r["record_id"], r["entity_id"], r["class"], r["style"], r["twin_of"]) for r in truth]
    exposed = _exposed(rows, _links([(r["schema"], r["properties"]) for r in records]))
    people = {p.entity_id: p for p in small.people}
    by_id = {r["id"]: r for r in records}
    last_names = tokens = 0
    for record_id, entity_id, cls, style, _ in rows:
        if cls != "person" or entity_id not in exposed:
            continue
        props = by_id[record_id]["properties"]
        for value in props.get("lastName", []):
            assert erbench.surname_ok(value), record_id
            last_names += 1
        if style not in ("list", "leak"):
            continue
        person, shown = people[entity_id], small.shown[record_id]
        forenames = [*person.given.latin, person.given.native or "", shown.given]
        if person.middle:
            forenames += [*person.middle.latin, person.middle.native or ""]
            forenames += [form[0] for form in person.middle.latin]
        skip = {token for name in forenames for token in fold(name).split()}
        for text in (*props.get("name", []), *props.get("alias", [])):
            for token in fold(text).split():
                if token not in skip:
                    assert erbench.surname_ok(token), (record_id, token)
                    tokens += 1
    assert last_names > LAST_NAMES_CHECKED and tokens > TOKENS_CHECKED


def test_entity_shares_meet_the_targets(large: erbench.Bench) -> None:
    people, orgs = large.people, large.orgs
    origins = Counter(p.origin for p in people)
    for origin, share in erbench.ORIGINS:
        assert abs(origins[origin] / len(people) - share) <= TOLERANCE
    counts = Counter(p.n_registry for p in people)
    for count, share in erbench.RECORD_COUNTS:
        assert abs(counts[count] / len(people) - share) <= TOLERANCE
    observed = {
        "listed": sum(bool(p.authorities) for p in people) / len(people),
        "leaked": sum(p.leaked for p in people) / len(people),
        "middle": sum(p.middle is not None for p in people) / len(people),
        "twin": sum(p.twin_of is not None for p in people) / len(people),
        "org_lei": sum(o.lei is not None for o in orgs) / len(orgs),
        "org_listed": sum(o.listed is not None for o in orgs) / len(orgs),
        "org_leaked": sum(o.leaked for o in orgs) / len(orgs),
        "org_twin": sum(o.twin_of is not None for o in orgs) / len(orgs),
    }
    for key, share in observed.items():
        assert abs(share - SHARES[key]) <= TOLERANCE, key
    unsc = [p for p in people if p.authorities]
    assert abs(sum(p.unsc is not None for p in unsc) / len(unsc) - RATES["unsc"]) <= TOLERANCE


def test_style_and_variation_shares_meet_the_targets(large: erbench.Bench) -> None:
    styles = Counter(style for _, entity, _, style, _ in large.truth if "-p-" in entity)
    registry = styles["officer"] + styles["psc"]
    assert abs(styles["officer"] / registry - 0.5) <= TOLERANCE
    lists = sum(len(p.authorities) for p in large.people)
    assert styles["list"] == lists and styles["leak"] == sum(p.leaked for p in large.people)
    stats = large.stats
    checked = 0
    for key, target in RATES.items():
        if f"{key}.n" not in stats:
            continue
        assert abs(stats[key] / stats[f"{key}.n"] - target) <= TOLERANCE, key
        checked += 1
    assert checked >= 18


def test_variants_draw_from_faker() -> None:
    faker = {
        "male": {erbench.strip_marks(n) for n in ar_SA.Provider.first_names_male},
        "female": {erbench.strip_marks(n) for n in ar_SA.Provider.first_names_female},
    }
    for gender, table in variants.ARABIC_GIVEN.items():
        assert set(table) <= faker[gender]
    russian = {"male": ru_RU.Provider.first_names_male, "female": ru_RU.Provider.first_names_female}
    for gender, names in variants.RUSSIAN_GIVEN.items():
        assert set(names) <= set(russian[gender])
    assert erbench.cyrillic_part("Соколов").latin[:2] == ("Sokolov", "Sokoloff")
    assert erbench.cyrillic_part("Елисеев").latin[0] == "Yeliseyev"
    assert "Vysotsky" in erbench.cyrillic_part("Высоцкий").latin


def test_the_generator_does_not_import_the_keys() -> None:
    """The benchmark tests `neonradar_keys`; it must not be built from it (deliverable 1)."""
    for module in (erbench, variants):
        tree = ast.parse(Path(str(module.__file__)).read_text(encoding="utf-8"))
        imported = [
            node.module if isinstance(node, ast.ImportFrom) else alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in node.names
        ]
        assert not [name for name in imported if name and name.startswith("neonradar_keys")]


def test_relationships_point_at_registry_records(
    records: list[dict[str, Any]], truth: list[dict[str, str]]
) -> None:
    by_id = {r["id"]: r for r in records}
    style = {row["record_id"]: row["style"] for row in truth}
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record["schema"] in ("Directorship", "Ownership"):
            target = record["properties"].get("organization") or record["properties"]["asset"]
            assert style[target[0]] == "registry" and by_id[target[0]]["schema"] == "Company"
            assert "incorporationDate" in by_id[target[0]]["properties"]  # the register record
            groups[record["schema"]].append(record["id"])
    assert all(model[s] for s in groups) and len(groups) == 2
