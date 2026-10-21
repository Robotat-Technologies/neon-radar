"""Synthetic company names from neutral word lists plus a legal form (PHASE-1.md M1.8e, 7.1).

Latin names are "<word> <word> <activity> <legal form>", for example "Ochre Tarn Freight
Ltd"; Arabic-script names (jurisdiction `ae`) are "<noun> و<noun> <activity> ذ.م.م". A name
is rejected when it contains a denylisted name or when its `name_key` is already taken: by
another synthetic company, or in synthetic-join mode by a name in the input records.
"""

import numpy as np

from neonradar_ingest.synth import words
from neonradar_ingest.synth.names import MAX_TRIES, fold, is_denied
from neonradar_ingest.synth.rng import chance, pick, slot_stream

_FORMS = tuple(sorted((f" {form}" for form in words.LEGAL_FORM_KEYS), key=len, reverse=True))


def name_key(name: str) -> str:
    """Comparison key: `fold` (NFC, case, punctuation), then legal forms at either end removed.

    "Ochre Tarn Freight Ltd", "OCHRE TARN FREIGHT LIMITED" and "Ochre-Tarn Freight, Ltd."
    share one key.
    """
    key = f" {fold(name)} "
    for _ in range(2):
        for form in _FORMS:
            if key.endswith(f"{form} "):
                key = key[: -len(form) - 1] + " "
            if key.startswith(f"{form} "):
                key = " " + key[len(form) + 1 :]
    return key.strip()


class CompanyNames:
    """Unique, denylist-checked company names. Each (slot, attempt) has its own seeded stream."""

    def __init__(self, seed: int, taken: set[str] | None = None):
        self.seed = seed
        self.taken = taken if taken is not None else set()

    @staticmethod
    def _compose(rng: np.random.Generator, jurisdiction: str, activity: str | None) -> str:
        if jurisdiction == "ae":
            first, second = (str(n) for n in rng.choice(words.ARABIC_NOUNS, 2, replace=False))
            return f"{first} و{second} {pick(rng, words.ARABIC_ACTIVITY)} ذ.م.م"
        first = pick(rng, words.COMPANY_FIRST)
        second = pick(rng, words.COMPANY_SECOND)
        activity = activity or pick(rng, words.COMPANY_ACTIVITY)
        form = pick(rng, words.LEGAL_FORMS[jurisdiction])
        if jurisdiction == "gb" and activity == "Consulting" and chance(rng, 0.5):
            form = words.GB_PARTNERSHIP
        return f"{first} {second} {activity} {form}"

    def draw(
        self, slot: int, jurisdiction: str, activity: str | None = None, first_attempt: int = 0
    ) -> tuple[str, int]:
        """The name of one slot and the attempt that gave it; `first_attempt` skips earlier
        draws (OD-12), as for people."""
        for attempt in range(first_attempt, first_attempt + MAX_TRIES):
            name = self._compose(slot_stream(self.seed, "companies", slot, attempt),
                                 jurisdiction, activity)  # fmt: skip
            key = name_key(name)
            if is_denied(name) or key in self.taken:
                continue
            self.taken.add(key)
            return name, attempt
        raise RuntimeError(f"no new {jurisdiction} company name after {MAX_TRIES} tries")


def street(rng: np.random.Generator) -> str:
    """An invented street name, for example "Ochrefold Lane"."""
    first = pick(rng, words.COMPANY_FIRST)
    second = pick(rng, words.COMPANY_SECOND).lower()
    return f"{first}{second} {pick(rng, words.STREET_TYPES)}"
