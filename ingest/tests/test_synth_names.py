import unicodedata

import pytest

from neonradar_ingest.synth import words
from neonradar_ingest.synth.names import (
    DENYLIST,
    Origin,
    PersonNames,
    fold,
    is_denied,
    strip_honorifics,
)

SEED_ENTRIES = ["آل سعود", "Al Saud", "بن لادن", "Bin Laden", "Binladin", "العليان", "Olayan",
                "كانو", "Kanoo"]  # fmt: skip


def test_denylist_starts_with_the_verbatim_seed() -> None:
    lines = DENYLIST.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# Real prominent family names found in Faker's ar_SA data")
    assert lines[1:10] == SEED_ENTRIES
    assert "# Added in M1.8e (review)" in lines[10]


@pytest.mark.parametrize(
    "name",
    ["Faisal Al Saud", "FAISAL AL-SAUD", "فيصل آل سعود", "Ahmed Kanoo", "Omar Haddad",
     unicodedata.normalize("NFD", "محمد بن لادن"), "Дмитрий Медведев", "Lina Juffali"],
)  # fmt: skip
def test_denylisted_names_are_found_in_any_case_script_or_form(name: str) -> None:
    assert is_denied(name)


@pytest.mark.parametrize("name", ["Salma Bitar", "Nabil Qassab", "Olga Belova", "Omar Bitar"])
def test_other_names_pass(name: str) -> None:
    assert not is_denied(name)


def test_strip_honorifics() -> None:
    assert strip_honorifics("الدكتور عمر حداد") == "عمر حداد"
    assert strip_honorifics("السيدة ليلى نجار") == "ليلى نجار"
    assert strip_honorifics("Dr. Jane Hill") == "Jane Hill"
    assert strip_honorifics("г-н Иван Волков") == "Иван Волков"
    assert strip_honorifics("Dr") == "Dr"


def _script(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if all("؀" <= c <= "ۿ" for c in letters):
        return "arabic"
    if all("Ѐ" <= c <= "ӿ" for c in letters):
        return "cyrillic"
    assert all(ord(c) < 0x250 for c in letters), text
    return "latin"


@pytest.mark.parametrize(
    ("origin", "scripts", "count", "expected"),
    [("en", 1, 300, ["latin"]), ("ar", 1, 300, ["arabic"]), ("ru", 1, 300, ["cyrillic"]),
     ("ar", 2, 60, ["latin", "arabic"]), ("ar", 3, 60, ["latin", "arabic", "cyrillic"]),
     ("ru", 2, 30, ["cyrillic", "latin"])],
)  # fmt: skip
def test_draws_are_unique_nfc_in_their_scripts_and_never_denylisted(
    origin: Origin, scripts: int, count: int, expected: list[str]
) -> None:
    names = PersonNames(seed=7)
    seen = set()
    for slot in range(count):
        person = names.draw(slot, origin, scripts)
        assert [_script(n) for n in person.names] == expected
        assert person.gender in ("male", "female")
        for name in person.names:
            assert unicodedata.is_normalized("NFC", name)
            assert not is_denied(name)
        seen.add(fold(person.names[0]))
    assert len(seen) == count


def test_arabic_surnames_come_only_from_the_curated_list() -> None:
    names = PersonNames(seed=11)
    curated = {surname for _, surname, _ in words.ARABIC_SURNAMES}
    for slot in range(200):
        assert names.draw(slot, "ar").names[0].split()[-1] in curated


def test_a_faker_only_slot_is_independent_of_other_slots_and_can_be_redrawn() -> None:
    alone = PersonNames(seed=5).draw(9, "en")
    names = PersonNames(seed=5)
    for slot in range(9):
        names.draw(slot, "ru")
    assert names.draw(9, "en") == alone
    again = PersonNames(seed=5).draw(9, "en", first_attempt=alone.attempt + 1)
    assert again.attempt > alone.attempt
    assert again.names != alone.names


def test_curated_slots_depend_on_the_parts_earlier_slots_used() -> None:
    """Curated parts are reused only when exhausted, so redrawing a curated slot can change
    later curated slots: after any redraw, check every name again (OD-12)."""
    alone = PersonNames(seed=5).draw(9, "ar", scripts=2)
    names = PersonNames(seed=5)
    for slot in range(9):
        names.draw(slot, "ar", scripts=2)
    later = names.draw(9, "ar", scripts=2)
    assert later.attempt == alone.attempt
    assert later.names != alone.names
