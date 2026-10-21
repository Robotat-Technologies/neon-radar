"""Dataset registry: `contracts/datasets.yaml`, the licence terms every loader follows (5.1, G7)."""

from collections import Counter
from functools import cache
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# The workspace installs members editable, so the file sits next to this package's src/.
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "datasets.yaml"


class Licence(BaseModel):
    """The licence of a dataset; `contents` is set when the contents differ from the database."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    contents: str | None = None


class Dataset(BaseModel):
    """One source of C1 records and the terms a loader must respect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    id_prefix: str = Field(pattern=r"^[a-z][a-z0-9]{1,15}$")
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: str = Field(min_length=1)
    licence: Licence
    attribution: str | None  # the key is required; null means no attribution is needed
    commercial_use: Literal["allowed", "licence-required"]
    redistribution: Literal["allowed", "loaders-only", "never"]
    personal_data: bool
    synthetic: bool
    access: Literal["none", "api-key", "licence-required"]
    status: Literal["active", "spike", "blocked"]
    notes: str | None = None


class Registry(BaseModel):
    """The whole registry: unique slugs and prefixes, none of them reserved."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    reserved_prefixes: list[str]
    datasets: list[Dataset]

    @model_validator(mode="after")
    def _unique_and_unreserved(self) -> Self:
        for field in ("slug", "id_prefix"):
            counts = Counter(getattr(dataset, field) for dataset in self.datasets)
            duplicates = sorted(value for value, n in counts.items() if n > 1)
            if duplicates:
                raise ValueError(f"duplicate {field}: {', '.join(duplicates)}")
        used = {dataset.id_prefix for dataset in self.datasets} & set(self.reserved_prefixes)
        if used:
            raise ValueError(f"reserved prefixes used by a dataset: {', '.join(sorted(used))}")
        return self

    def get(self, slug: str) -> Dataset | None:
        """Return the dataset with this slug, or None."""
        return next((dataset for dataset in self.datasets if dataset.slug == slug), None)


@cache
def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    """Read and validate the registry; the result is cached per path."""
    with path.open(encoding="utf-8") as handle:
        return Registry.model_validate(yaml.safe_load(handle))
