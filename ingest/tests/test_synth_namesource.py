"""The generator v1 name source (PHASE-3.md M3.3 deliverable 5, 7.2.3; OD-12)."""

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


@pytest.mark.parametrize("locale", namesource.LOCALES)
def test_invented_surnames_are_not_real_ones(names: namesource.PhaseOneNames, locale: str) -> None:
    rng = stream(2, "test-invented", locale)
    for _ in range(DRAWS):
        spellings, _ = names.invented_person(rng, locale)
        for name in spellings:
            assert not is_denied(name)
            assert fold(name.split()[-1]) not in names.real_surnames


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
