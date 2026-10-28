"""The generator v1 name source (PHASE-3.md M3.3 deliverable 5, 7.2.3; OD-12)."""

import itertools
import re
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from neonradar_ingest.synth import namesource
from neonradar_ingest.synth.names import fold, is_denied
from neonradar_ingest.synth.namesource import default_names
from neonradar_ingest.synth.streams import stream

DRAWS = 10_000
OD12 = "Cedar Gate Holdings Ltd"


@pytest.fixture(scope="module")
def names() -> namesource.PhaseOneNames:
    return default_names()


@pytest.mark.parametrize("locale", namesource.LOCALES)
def test_person_names_pass_the_denylist(names: namesource.PhaseOneNames, locale: str) -> None:
    rng = stream(1, "test-person", locale)
    for _ in range(DRAWS):
        spellings, gender = names.person(rng, locale)
        assert gender in ("male", "female")
        assert spellings and not any(is_denied(name) for name in spellings)


def three_syllables(locale: str) -> re.Pattern[str]:
    """An invented surname: exactly three syllables of the table, in the locale's script."""
    script = namesource.SCRIPT[locale]
    options = "|".join(sorted({row[script] for row in namesource.SYLLABLES}, key=len, reverse=True))
    return re.compile(f"(?:{options}){{3}}", re.IGNORECASE)


@pytest.mark.parametrize("locale", namesource.LOCALES)
def test_invented_surnames_are_not_real_ones(names: namesource.PhaseOneNames, locale: str) -> None:
    rng = stream(2, "test-invented", locale)
    pattern = three_syllables(locale)
    for _ in range(DRAWS):
        spellings, _ = names.invented_person(rng, locale)
        for name in spellings:
            assert not is_denied(name)
            surname = name.split()[-1]
            assert fold(surname) not in names.real_surnames
            assert pattern.fullmatch(surname), surname


FLAG_TOPICS = {"sanction", "role.pep", "role.rca"}
LINKS = ("owner", "asset", "director", "organization", "person", "relative", "associate",
         "controller", "controlled", "agent", "client", "holder")  # fmt: skip


def test_flagged_personas_and_the_people_linked_to_them_have_invented_surnames(
    names: namesource.PhaseOneNames,
) -> None:
    """List and PEP personas, and every person one link away from a flagged entity, carry an
    invented three-syllable surname (orchestrator decision on the #71 review; 7.2.3)."""
    from neonradar_ingest.synth import overlay, world

    small = world.WorldConfig(companies=40, people=60, agent_every=20, professional_every=20)
    base = world.generate(8, small, names)
    config = overlay.OverlayConfig(
        8, illicit=4, lookalikes=4, typologies=("sanctions_exposure", "pep_exposure")
    )
    ov = overlay.generate(base, {"nr_synthetic": "synthetic"}, config, names)
    records = base + ov.records
    by_id = {r["id"]: r for r in records}
    flagged = {r["id"] for r in records if FLAG_TOPICS & set(r["properties"].get("topics", []))}
    linked: set[str] = set(flagged)
    for r in records:
        ends = {v for key in LINKS for v in r["properties"].get(key, [])}
        if ends & flagged:
            linked |= ends
    people = sorted(i for i in linked if by_id[i]["schema"] == "Person")
    assert len(people) > 10
    # S8: every person in a scenario role, flagged or not, has an invented surname too.
    roles = {row["object_id"] for row in ov.labels.participants}
    people += sorted(i for i in roles if i in by_id and by_id[i]["schema"] == "Person")
    for pid in people:
        person = by_id[pid]
        for name in person["properties"]["name"]:
            surname = name.split()[-1]
            assert fold(surname) not in names.real_surnames, pid
            assert any(three_syllables(loc).fullmatch(surname) for loc in namesource.LOCALES), pid


def test_the_same_generator_state_gives_the_same_name(names: namesource.PhaseOneNames) -> None:
    for locale in namesource.LOCALES:
        a, b = stream(3, "same", locale), stream(3, "same", locale)
        assert [names.person(a, locale) for _ in range(20)] == [
            names.person(b, locale) for _ in range(20)
        ]
        assert names.invented_person(a, locale) == names.invented_person(b, locale)
    a, b = stream(3, "same", "co"), stream(3, "same", "co")
    assert [names.company(a, "gb") for _ in range(20)] == [
        names.company(b, "gb") for _ in range(20)
    ]
    assert (names.street(a), names.town(a)) == (names.street(b), names.town(b))


def test_methods_draw_only_from_the_generator_they_are_given(
    names: namesource.PhaseOneNames,
) -> None:
    """A second name source instance gives the same names from the same generator state."""
    other = default_names()
    a, b = stream(4, "x"), stream(4, "x")
    assert names.person(a, "ru_RU") == other.person(b, "ru_RU")
    assert names.company(a, "vg") == other.company(b, "vg")


def test_company_space_is_large_enough(names: namesource.PhaseOneNames) -> None:
    space = (
        len(set(namesource.FIRST))
        * len(set(namesource.SECOND))
        * len(set(namesource.QUALIFIER))
        * len(set(namesource.ACTIVITY))
    )
    assert space >= 1_000_000
    rng = stream(5, "companies")
    drawn = [names.company(rng, "gb") for _ in range(200_000)]
    assert len(set(drawn)) >= 190_000
    assert not any(is_denied(name) for name in drawn)
    assert OD12 not in drawn


def test_od12_company_name_is_never_produced(
    names: namesource.PhaseOneNames, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OD-12: the denylist blocks the name, and the word lists cannot spell it."""
    assert is_denied(OD12) and is_denied("CEDAR GATE HOLDINGS LIMITED")
    words = {*namesource.FIRST, *namesource.SECOND, *namesource.QUALIFIER, *namesource.ACTIVITY}
    assert not {"Cedar", "Gate"} & words
    # Even with word lists that can only spell it, `company` refuses to return it.
    monkeypatch.setattr(namesource, "FIRST", ("Cedar",))
    monkeypatch.setattr(namesource, "SECOND", ("Gate",))
    monkeypatch.setattr(namesource, "QUALIFIER", ("Holdings",))
    monkeypatch.setattr(namesource, "ACTIVITY", ("Trading",))
    with pytest.raises(RuntimeError, match="no gb company name"):
        names.company(np.random.default_rng(0), "gb")


def test_legal_forms_follow_the_jurisdiction(names: namesource.PhaseOneNames) -> None:
    rng = stream(6, "forms")
    assert names.company(rng, "gb").endswith(" Ltd")
    assert names.company(rng, "nl").endswith(" B.V.")
    assert names.company(rng, "zz").endswith(" Ltd")


def test_invented_surnames_never_spell_known_real_ones(names: namesource.PhaseOneNames) -> None:
    """S9: the filter covers every installed Faker locale and the curated denylist entries."""
    for surname in ("Takata", "Takaki", "Moroka"):
        assert not names.surname_allowed(surname)
    assert len(namesource.all_faker_surnames()) > 10_000

    for surname in ("Takita", "Kakita", "Morota"):  # the #78 review's examples
        assert not names.surname_allowed(surname)


# Every three-syllable combination with a closed syllable that the filter refuses, by script
# (Latin syllables of the table). A change to the table, Faker or the denylist shows up here.
REFUSED = {
    "en_GB": set(),
    "ru_RU": set(),
    "ar_SA": {  # Arabic ka + nor spells the denylisted family name
        "brin-ka-nor", "dra-ka-nor", "du-ka-nor", "ka-ka-nor", "ka-nor-brin", "ka-nor-dra",
        "ka-nor-du", "ka-nor-ka", "ka-nor-ki", "ka-nor-lan", "ka-nor-mesh", "ka-nor-mo",
        "ka-nor-nor", "ka-nor-ro", "ka-nor-sar", "ka-nor-ske", "ka-nor-ta", "ka-nor-ve",
        "ka-nor-vel", "ka-nor-zo", "ki-ka-nor", "lan-ka-nor", "mesh-ka-nor", "mo-ka-nor",
        "nor-ka-nor", "ro-ka-nor", "sar-ka-nor", "ske-ka-nor", "ta-ka-nor", "ve-ka-nor",
        "vel-ka-nor", "zo-ka-nor",
    },
}  # fmt: skip


@pytest.mark.parametrize("locale", namesource.LOCALES)
def test_the_refused_invented_surnames_are_pinned(
    names: namesource.PhaseOneNames, locale: str
) -> None:
    script, table = namesource.SCRIPT[locale], namesource.SYLLABLES
    refused = set()
    for picks in itertools.product(range(len(table)), repeat=3):
        if namesource.CLOSED.isdisjoint(picks):
            continue  # never drawn: open syllables alone spell real surnames (Takita)
        name = "".join(table[i][script] for i in picks)
        if not names.surname_allowed(name if script == 2 else name.capitalize()):
            refused.add("-".join(table[i][0] for i in picks))
    assert refused == REFUSED[locale]
    rng = stream(9, "closed", locale)
    for _ in range(500):
        surname = names.invented_surname(rng, locale)
        closed = {table[i][script] for i in namesource.CLOSED}
        assert any(syllable in surname.casefold() for syllable in closed), surname


def test_every_person_a_scenario_creates_has_an_invented_surname(
    names: namesource.PhaseOneNames, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#78 review: over `ScenarioCtx.created`, so unlabelled donors, buyers and payers count."""
    from neonradar_ingest.synth import ctx as ctx_module
    from neonradar_ingest.synth import overlay, world

    made: list[ctx_module.ScenarioCtx] = []

    class Recording(ctx_module.ScenarioCtx):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(overlay, "ScenarioCtx", Recording)
    small = world.WorldConfig(companies=40, people=60, agent_every=20, professional_every=20)
    base = world.generate(4, small, names)
    config = overlay.OverlayConfig(4, illicit=1, lookalikes=1)
    records = overlay.generate(base, {"nr_synthetic": "synthetic"}, config, names).other_records
    people = {i for s in made for i in s.created if records.get(i, {}).get("schema") == "Person"}
    assert len(made) == 28 and len(people) > 100
    for pid in people:
        surname = records[pid]["properties"]["name"][0].split()[-1]
        assert fold(surname) not in names.real_surnames, pid
        assert any(three_syllables(loc).fullmatch(surname) for loc in namesource.LOCALES), pid


def test_a_missing_required_faker_locale_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """#78 review: a locale dropped from the surname filter is counted, a required one fails."""
    real_import = namesource.importlib.import_module

    def without_japanese(name: str) -> Any:
        if name.endswith(".ja_JP"):
            raise ImportError(name)
        return real_import(name)

    def empty_japanese(name: str) -> Any:  # imports, but gives no surname
        if name.endswith(".ja_JP"):
            return SimpleNamespace(Provider=type("Provider", (), {"last_names": ()}))
        return real_import(name)

    namesource.all_faker_surnames.cache_clear()
    try:
        monkeypatch.setattr(namesource.importlib, "import_module", without_japanese)
        with pytest.raises(RuntimeError, match="ja_JP"):
            namesource.all_faker_surnames()
        assert "ja_JP" in namesource.DROPPED
        monkeypatch.setattr(namesource.importlib, "import_module", empty_japanese)
        with pytest.raises(RuntimeError, match="no surnames for ja_JP"):
            namesource.all_faker_surnames()
    finally:
        monkeypatch.undo()
        namesource.all_faker_surnames.cache_clear()
