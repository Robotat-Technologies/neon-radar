"""A second NameSource for the name-independence test: plain invented words, no Faker."""

import numpy as np


class SimpleNames:
    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        return [
            f"Testperson {int(rng.integers(10**9))}"
        ], "female" if rng.random() < 0.5 else "male"

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        return [
            f"Testlisted {int(rng.integers(10**9))}"
        ], "female" if rng.random() < 0.5 else "male"

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str:
        return f"Testcompany {int(rng.integers(10**9))} Ltd"

    def street(self, rng: np.random.Generator) -> str:
        return f"Teststreet {int(rng.integers(10**6))}"

    def town(self, rng: np.random.Generator) -> str:
        return f"Testtown {int(rng.integers(10**6))}"
