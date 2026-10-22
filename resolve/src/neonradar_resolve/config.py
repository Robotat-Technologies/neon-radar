"""The resolver's settings file, `resolve/config/er.yaml` (PHASE-2.md 7.1.7)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from neonradar_resolve import cluster
from neonradar_resolve.rules import handle


class ResolverConfig(BaseModel):
    """`er.yaml`; unknown keys fail. M2.10b adds `duckdb`, `training` and `max_comparisons`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    merge_threshold: dict[Literal["person", "org"], float] = Field(min_length=2)
    candidate_threshold: float = Field(ge=0, le=1)
    cluster_cap: int = Field(ge=2)
    name_check_jaro_winkler: float = Field(gt=0, le=1)
    seed: int

    def cluster_config(self, senior_reviewers: Iterable[str] = ()) -> cluster.Config:
        """The clustering settings, with `people.er_senior_reviewers` (placeholders dropped)."""
        seniors = frozenset(h for value in senior_reviewers if (h := handle(value)))
        return cluster.Config(
            merge_threshold={str(k): v for k, v in self.merge_threshold.items()},
            candidate_threshold=self.candidate_threshold,
            cluster_cap=self.cluster_cap,
            name_check_jaro_winkler=self.name_check_jaro_winkler,
            senior_reviewers=seniors,
        )


def load_config(path: Path) -> tuple[ResolverConfig, str]:
    """The validated settings and the SHA-256 of the file (recorded in `run.json`)."""
    raw = path.read_bytes()
    config = ResolverConfig.model_validate(yaml.safe_load(raw))
    for name, value in config.merge_threshold.items():
        if not 0 <= value <= 1:
            raise ValueError(f"merge_threshold.{name} must be between 0 and 1")
    return config, hashlib.sha256(raw).hexdigest()
