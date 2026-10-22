"""The generator's NameSource (PHASE-3.md 7.2.3, M3.3 deliverable 2).

An adapter over the Phase 1 name modules (M1.8e): Faker first names and surnames as `names.py`
draws them (honorifics stripped, Arabic-script surnames from the curated list in `words.py`,
never Faker's `ar_SA` surnames), the denylist, and the neutral word lists of `words.py`. Every
method draws only from the generator it is given (Faker is seeded per call from it), so a name
never moves a structural draw (PHASE-3.md 7.2.1).

`invented_person` gives a person an invented surname: three syllables in the person's script,
with at least one closed syllable, redrawn while the result is a surname of any installed Faker
locale or of the curated lists, or the full name is on the denylist. PHASE-2.md M2.9's
`variants.py` has not merged, so the syllable table is the code book reference's (recorded in
the Phase 3 reconciliation).

Company names are "<word> <word> <qualifier> <activity> <legal form>". The extra words below
widen Phase 1's lists to more than four million names before the legal form (the scale world
needs about 160,000, 7.2.3); they live here, never in `words.py`, so generator v0 and the
committed demo-mini fixture do not change. Rules for editing them are the rules of `words.py`:
neutral words only, no brands or famous names, nothing the wording lint forbids, and never a
word that lets a draw spell "Cedar Gate Holdings" (OD-12; the denylist blocks it as well).
"""

from __future__ import annotations

import importlib
import unicodedata
from functools import cache

import numpy as np
from faker import Faker

from neonradar_ingest.synth import words
from neonradar_ingest.synth.companies import street as phase1_street
from neonradar_ingest.synth.names import MAX_TRIES, fold, is_denied, strip_honorifics

LOCALES = ("en_GB", "ar_SA", "ru_RU")

# Company words: Phase 1's lists first, then neutral plants, minerals, birds and landforms.
FIRST = (
    *words.COMPANY_FIRST,
    "Agrimony", "Alkanet", "Avens", "Bistort", "Bugle", "Burdock", "Burnet", "Campion",
    "Chervil", "Clary", "Comfrey", "Cowslip", "Dittany", "Dunlin", "Eyebright", "Feldspar",
    "Feverfew", "Fleabane", "Gabbro", "Gneiss", "Godwit", "Gromwell", "Henbit", "Hyssop",
    "Knapweed", "Lovage", "Madder", "Mallow", "Marl", "Medlar", "Milfoil", "Mugwort", "Orpine",
    "Ouzel", "Pipit", "Purslane", "Ramson", "Redpoll", "Samphire", "Schist", "Shrike", "Siskin",
    "Sloe", "Speedwell", "Stitchwort", "Tormentil", "Toadflax", "Tufa", "Twite", "Vervain",
)  # fmt: skip
SECOND = (
    *words.COMPANY_SECOND,
    "Bourne", "Carr", "Clough", "Delph", "Dene", "Grange", "Hagg", "Hithe", "Hurst", "Ings",
    "Keld", "Knott", "Ley", "Linch", "Mire", "Nab", "Pike", "Rake", "Ridding", "Royd", "Slack",
    "Sough", "Stead", "Stell", "Swale", "Syke", "Thwaite", "Wath", "Wick", "Wray",
    "Hollin", "Intake", "Lund", "Scale", "Wyke",
)  # fmt: skip
QUALIFIER = (
    "Northern", "Southern", "Eastern", "Western", "Central", "Coastal", "Midland", "Valley",
    "Upland", "Border", "County", "Lowland", "Riverside", "Hillside", "Estuary", "Moorland",
    "Island", "Downland", "Fenland", "Lakeland", "Parkside", "Saltmarsh", "Wealden", "Dales",
)  # fmt: skip
ACTIVITY = (
    *words.COMPANY_ACTIVITY,
    "Joinery", "Glazing", "Plumbing", "Roofing", "Haulage", "Printing", "Bakery", "Stationery",
    "Hardware", "Flooring", "Landscaping", "Cleaning", "Tooling", "Fabrication", "Ceramics",
    "Upholstery", "Signage", "Lighting", "Seeds", "Timber", "Metals", "Plastics", "Electrical",
    "Surveying", "Design", "Fixings",
)  # fmt: skip
FORMS = {
    "gb": "Ltd", "vg": "Limited", "cy": "Ltd", "ae": "FZE", "je": "Limited", "gg": "Limited",
    "pa": "S.A.", "sc": "Ltd", "ie": "Limited", "nl": "B.V.", "lu": "S.a r.l.", "us": "LLC",
    "hk": "Limited", "mt": "Ltd", "bz": "Ltd", "ky": "Ltd", "de": "GmbH",
}  # fmt: skip
TOWN_ENDINGS = ("", " Green", " End", " Cross", " Hill", " Bridge", " Common", " Heath")

# Invented syllables in three scripts (Latin, Cyrillic, Arabic): sounds, not names. The code
# book reference's table, until PHASE-2.md M2.9's `variants.py` exists.
SYLLABLES = (
    ("ka", "ка", "كا"),
    ("ro", "ро", "رو"),
    ("vel", "вел", "فيل"),
    ("dra", "дра", "درا"),
    ("mo", "мо", "مو"),
    ("ske", "ске", "سكي"),
    ("ta", "та", "تا"),
    ("brin", "брин", "برين"),
    ("zo", "зо", "زو"),
    ("lan", "лан", "لان"),
    ("ve", "ве", "في"),
    ("nor", "нор", "نور"),
    ("ki", "ки", "كي"),
    ("sar", "сар", "سار"),
    ("du", "ду", "دو"),
    ("mesh", "меш", "مش"),
)
SCRIPT = {"en_GB": 0, "ru_RU": 1, "ar_SA": 2}
SURNAME_SYLLABLES = 3
CLOSED = frozenset(i for i, row in enumerate(SYLLABLES) if row[0][-1] not in "aeiou")


@cache
def all_faker_surnames() -> frozenset[str]:
    """The last names of every Faker locale installed, romanized ones included, folded."""
    from faker.config import AVAILABLE_LOCALES

    found: set[str] = set()
    for locale in AVAILABLE_LOCALES:
        try:
            provider = importlib.import_module(f"faker.providers.person.{locale}").Provider
        except ImportError, AttributeError:
            continue
        for attribute in dir(provider):
            value = getattr(provider, attribute, None)
            if attribute.startswith(("last_name", "last_romanized_name")) and isinstance(
                value, tuple | list | dict
            ):
                found.update(fold(str(name)) for name in value)
    return frozenset(found)


def _pick(rng: np.random.Generator, items: tuple[str, ...]) -> str:
    return items[int(rng.integers(len(items)))]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


class PhaseOneNames:
    """`ctx.NameSource` over the Phase 1 name modules."""

    def __init__(self) -> None:
        self._fakers = {locale: Faker(locale) for locale in LOCALES}
        surnames: set[str] = set()
        for fake in self._fakers.values():
            for provider in fake.get_providers():
                for attribute in dir(provider):
                    value = getattr(provider, attribute, None)
                    if attribute.startswith("last_names") and isinstance(value, tuple | dict):
                        surnames.update(fold(str(name)) for name in value)
        for spellings in (*words.ARABIC_SURNAMES, *words.RUSSIAN_SURNAMES):
            surnames.update(fold(name) for name in spellings)
        self.real_surnames = frozenset(surnames) | all_faker_surnames()

    def _seeded(self, rng: np.random.Generator, locale: str) -> Faker:
        fake = self._fakers[locale]
        fake.seed_instance(int(rng.integers(0, 2**31)))
        return fake

    def _first(self, rng: np.random.Generator, locale: str) -> tuple[str, str]:
        gender = "female" if rng.random() < 0.5 else "male"
        fake = self._seeded(rng, locale)
        first = fake.first_name_female() if gender == "female" else fake.first_name_male()
        return first, gender

    def _last(self, rng: np.random.Generator, locale: str, gender: str) -> str:
        if locale == "ar_SA":  # Faker's ar_SA surnames are prominent families: never use them
            return _pick(rng, tuple(spellings[1] for spellings in words.ARABIC_SURNAMES))
        fake = self._seeded(rng, locale)
        if locale == "ru_RU":
            return fake.last_name_female() if gender == "female" else fake.last_name_male()
        return fake.last_name()

    def invented_surname(self, rng: np.random.Generator, locale: str) -> str:
        """Three invented syllables in the locale's script, at least one of them closed (vel,
        brin, lan, nor, sar, mesh: open ones alone spell real surnames such as Takita), redrawn
        while the result is a surname of any installed Faker locale or of Phase 1's curated
        lists, or is on the denylist (the #71 and #72 reviews)."""
        script = SCRIPT[locale]
        for _ in range(MAX_TRIES):
            picks = [int(rng.integers(len(SYLLABLES))) for _ in range(SURNAME_SYLLABLES)]
            if CLOSED.isdisjoint(picks):
                continue
            name = "".join(SYLLABLES[i][script] for i in picks)
            name = name if script == 2 else name.capitalize()
            if self.surname_allowed(name):
                return name
        raise RuntimeError(f"no invented {locale} surname after {MAX_TRIES} tries")

    def surname_allowed(self, surname: str) -> bool:
        """Not a surname of any installed Faker locale (romanized ones included), nor of the
        curated lists, nor on the denylist (which names the real surnames syllables can spell)."""
        return fold(surname) not in self.real_surnames and not is_denied(surname)

    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """One spelling of an ordinary synthetic person's realistic name, and a gender."""
        for _ in range(MAX_TRIES):
            first, gender = self._first(rng, locale)
            name = _nfc(strip_honorifics(f"{first} {self._last(rng, locale, gender)}"))
            if not is_denied(name):
                return [name], gender
        raise RuntimeError(f"no {locale} name off the denylist after {MAX_TRIES} tries")

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """The same with an invented surname: every scenario person, and the list, PEP and RCA
        personas of the world and their relatives and associates."""
        for _ in range(MAX_TRIES):
            first, gender = self._first(rng, locale)
            name = _nfc(strip_honorifics(f"{first} {self.invented_surname(rng, locale)}"))
            if not is_denied(name):
                return [name], gender
        raise RuntimeError(f"no invented {locale} name after {MAX_TRIES} tries")

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str:
        """A neutral-word name with the jurisdiction's legal form, never a denylisted one."""
        form = FORMS.get(jurisdiction, "Ltd")
        for _ in range(MAX_TRIES):
            first, second = _pick(rng, FIRST), _pick(rng, SECOND)
            name = f"{first} {second} {_pick(rng, QUALIFIER)} {_pick(rng, ACTIVITY)} {form}"
            if not is_denied(name):
                return name
        raise RuntimeError(f"no {jurisdiction} company name after {MAX_TRIES} tries")

    def street(self, rng: np.random.Generator) -> str:
        """An invented street name, as Phase 1 makes them ("Ochrefold Lane")."""
        return phase1_street(rng)

    def town(self, rng: np.random.Generator) -> str:
        """An invented town, for example "Sedgemere Green"."""
        first = _pick(rng, words.COMPANY_FIRST)
        second = _pick(rng, words.COMPANY_SECOND).lower()
        return f"{first}{second}{_pick(rng, TOWN_ENDINGS)}"


def default_names() -> PhaseOneNames:
    return PhaseOneNames()
