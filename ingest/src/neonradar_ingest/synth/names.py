"""Synthetic person names (PHASE-1.md M1.8e, 7.1; ADR-0005).

Faker 40.43 gives first names for `ar_SA`, `ru_RU` and `en_GB` and surnames for `ru_RU` and
`en_GB`, always with an explicit gender. Arabic-script surnames, and every name written in
several scripts, come from the curated lists in `words.py`. Every full name is checked
against `denylist.txt` (NFC, case-folded, punctuation as spaces; a name that contains an
entry is rejected) and must be new within the run.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

import numpy as np
from faker import Faker

from neonradar_ingest.synth import words
from neonradar_ingest.synth.rng import between, pick, slot_stream

Gender = Literal["male", "female"]
Origin = Literal["en", "ar", "ru"]
DENYLIST = Path(__file__).with_name("denylist.txt")
HONORIFICS = frozenset(
    {
        "الأستاذ", "الأستاذة", "الدكتور", "الدكتورة", "السيد", "السيدة", "المهندس", "المهندسة",
        "الآنسة", "г-н", "г-жа", "тов", "mr", "mrs", "ms", "miss", "dr", "prof", "sir",
    }
)  # fmt: skip
NATIONALITY = {"en": ("gb",), "ar": ("jo", "lb", "eg", "ae"), "ru": ("ru", "cy")}
LOCALES = {"en": "en_GB", "ar": "ar_SA", "ru": "ru_RU"}
MAX_TRIES = 200
_PUNCTUATION = re.compile(r"[\W_]+")


def fold(text: str) -> str:
    """NFC, case-folded, punctuation and spacing collapsed to single spaces."""
    folded = unicodedata.normalize("NFC", text).casefold()
    return _PUNCTUATION.sub(" ", folded).strip()


@cache
def denylist() -> tuple[str, ...]:
    lines = DENYLIST.read_text(encoding="utf-8").splitlines()
    return tuple(fold(line) for line in lines if line.strip() and not line.startswith("#"))


def is_denied(name: str) -> bool:
    """True when the name contains a denylisted name."""
    folded = f" {fold(name)} "
    return any(entry in folded for entry in denylist())


def strip_honorifics(name: str) -> str:
    """Drop leading titles such as "الدكتور" or "Dr"."""
    tokens, titles = name.split(), {fold(title) for title in HONORIFICS}
    while len(tokens) > 1 and fold(tokens[0]) in titles:
        tokens.pop(0)
    return " ".join(tokens)


@dataclass(frozen=True, slots=True)
class PersonName:
    names: tuple[str, ...]  # the primary spelling first, then other scripts
    gender: Gender
    origin: Origin
    nationality: str
    birth: str  # YYYY-MM
    attempt: int  # which draw of its slot this is (see `first_attempt`)


class PersonNames:
    """Unique, denylist-checked person names. Each (slot, attempt) has its own seeded stream;
    Faker's own `random.Random` is seeded from it for each draw."""

    def __init__(self, seed: int, taken: set[str] | None = None):
        self.seed = seed
        self.taken = taken if taken is not None else set()
        self.used: set[tuple[str, ...]] = set()  # curated parts, reused only when exhausted
        self.fakers = {origin: Faker(locale) for origin, locale in sorted(LOCALES.items())}

    def _fresh[T: tuple[str, ...]](
        self, rng: np.random.Generator, options: tuple[T, ...], parts: list[tuple[str, ...]]
    ) -> T:
        unused = [o for o in options if o not in self.used and o not in parts]
        choice = pick(rng, unused or options)
        parts.append(choice)
        return choice

    def _make(
        self, rng: np.random.Generator, origin: Origin, gender: Gender, scripts: int,
        parts: list[tuple[str, ...]],
    ) -> tuple[str, ...]:  # fmt: skip
        if scripts > 1 and origin == "ar":
            given = self._fresh(rng, words.ARABIC_GIVEN[gender], parts)
            last = self._fresh(rng, words.ARABIC_SURNAMES, parts)
            return tuple(f"{given[i]} {last[i]}" for i in range(scripts))
        if scripts > 1:
            given_ru = self._fresh(rng, words.RUSSIAN_GIVEN[gender], parts)
            latin, cyrillic = self._fresh(rng, words.RUSSIAN_SURNAMES, parts)
            if gender == "female":
                latin, cyrillic = latin + "a", cyrillic + "а"
            return (f"{given_ru[1]} {cyrillic}", f"{given_ru[0]} {latin}")
        fake = self.fakers[origin]
        fake.seed_instance(int(rng.integers(2**32)))
        male = gender == "male"
        first = fake.first_name_male() if male else fake.first_name_female()
        if origin == "ar":  # Faker ar_SA surnames are prominent families: never use them
            last_name = self._fresh(rng, words.ARABIC_SURNAMES, parts)[1]
        elif origin == "ru":
            last_name = fake.last_name_male() if male else fake.last_name_female()
        else:
            last_name = fake.last_name()
        return (strip_honorifics(f"{first} {last_name}"),)

    def draw(
        self, slot: int, origin: Origin, scripts: int = 1, first_attempt: int = 0
    ) -> PersonName:
        """The name of one slot; `scripts` above 1 uses the curated multi-script spellings.

        `first_attempt` skips earlier draws of this slot, for a name that matched a real one
        (OD-12). Faker-only slots (`en`, and `ru` in one script) are independent. Slots that use
        the curated lists (`ar`, and every multi-script name) prefer parts no earlier slot used,
        so redrawing one can change later curated slots: after any redraw, check every name
        again.
        """
        for attempt in range(first_attempt, first_attempt + MAX_TRIES):
            rng = slot_stream(self.seed, "names", slot, attempt)
            gender: Gender = "female" if rng.random() < 0.5 else "male"
            parts: list[tuple[str, ...]] = []
            names = tuple(
                unicodedata.normalize("NFC", n)
                for n in self._make(rng, origin, gender, scripts, parts)
            )
            keys = {fold(name) for name in names}
            if any(is_denied(name) for name in names) or keys & self.taken:
                continue
            self.taken.update(keys)
            self.used.update(parts)
            nationality = pick(rng, NATIONALITY[origin])
            birth = f"{between(rng, 1956, 1998)}-{between(rng, 1, 12):02d}"
            return PersonName(names, gender, origin, nationality, birth, attempt)
        raise RuntimeError(f"no new {origin} name after {MAX_TRIES} tries; extend the lists")
