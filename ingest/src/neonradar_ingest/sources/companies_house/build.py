"""The `gb_companies_house` builder and its profile block (PHASE-2.md M2.3 build steps, M2.3a).

`neonradar ingest build --dataset gb_companies_house [--step <name>]...` runs the steps of the
merged sub-milestones in order: `index`, `slice` and `companies` (M2.3a); M2.3b adds
`psc-index` and `psc`, M2.3c `officers`. Each step reads the previous steps' work files in
`layout.work_dir(profile, dataset)`; a missing input stops the step with exit code 2 and names
the step to run first. After a successful build (records validated and swapped in) that ran
the `companies` step, the work indexes are deleted unless `--keep-work` is given; `slice.csv`
and `slice.json` stay until the next `slice` step. The `companies` step refuses (exit 2) a
slice built from another snapshot than the newest download.
"""

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from neonradar_ingest.data import layout
from neonradar_ingest.data.download import RECORD
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.sources import (
    BuildContext,
    Builder,
    BuildError,
    BuildResult,
    register_builder,
)
from neonradar_ingest.sources.companies_house import bulk, records
from neonradar_ingest.sources.companies_house import slice as slices

STEPS = ("index", "slice", "companies")
INDEX = "companies.sqlite"
PSC_INDEX = "corporate_pscs.sqlite"  # written by the psc-index step (M2.3b)
SLICE = "slice.csv"
SLICE_META = "slice.json"  # the snapshot version, sample seed and SHA-256 of slice.csv
NUMBER_RE = re.compile(r"[A-Z0-9]{8}\Z")


class StepInputMissing(BuildError):
    """A step whose input is missing: it names the step or command to run first."""

    exit_code = 2


class CompaniesBlock(BaseModel):
    """The `companies` block of a profile (PHASE-2.md 7.8)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seeds: list[str] = Field(default_factory=list)
    postcode_districts: list[str] = Field(default_factory=list)
    max_per_district: StrictInt = Field(ge=0)
    max_companies: StrictInt = Field(ge=0)
    sample_seed: StrictInt

    @field_validator("seeds")
    @classmethod
    def _numbers(cls, seeds: list[str]) -> list[str]:
        for seed in seeds:
            if not NUMBER_RE.fullmatch(seed):
                raise ValueError(f"seed {seed!r} is not an 8-character company number")
        return seeds

    @field_validator("postcode_districts")
    @classmethod
    def _districts(cls, districts: list[str]) -> list[str]:
        for district in districts:
            if not bulk.OUTWARD_RE.fullmatch(district):
                raise ValueError(f"{district!r} is not an upper-case outward postcode")
        return districts


class CompaniesHouseSource(BaseModel):
    """The `gb_companies_house` block; `psc` and `officers` stay mappings until M2.3b, M2.3c."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    companies: CompaniesBlock | None = None
    psc: dict[str, Any] | None = None
    officers: dict[str, Any] | None = None


register_source_model(bulk.DATASET, CompaniesHouseSource)


def companies_download() -> tuple[str, list[Path], list[str]]:
    """The newest complete download of the `companies` product: version, parts, stored URLs."""
    product = layout.sources_dir(bulk.DATASET, bulk.PRODUCT, "latest").parent
    complete: list[tuple[str, dict[str, Any]]] = []
    for folder in sorted(product.iterdir()) if product.is_dir() else []:
        if not folder.is_dir():
            continue  # a stray file such as .DS_Store
        try:
            record = json.loads((folder / RECORD).read_text(encoding="utf-8"))
        except FileNotFoundError, ValueError:
            continue
        if isinstance(record, dict) and record.get("complete"):
            complete.append((folder.name, record))
    if not complete:
        raise StepInputMissing(
            f"{bulk.DATASET}: no complete download of the {bulk.PRODUCT} product; run"
            f" neonradar data fetch --profile <profile> --dataset {bulk.DATASET} first",
            "input",
            counts_only=True,
        )
    version, record = max(complete, key=lambda item: item[0])
    files = [
        entry
        for entry in record.get("files", [])
        if entry.get("product") == bulk.PRODUCT and bulk.PART_RE.fullmatch(str(entry.get("name")))
    ]
    folder = layout.sources_dir(bulk.DATASET, bulk.PRODUCT, version)
    parts = sorted((folder / entry["name"] for entry in files), key=bulk.part_number)
    return version, parts, [str(entry.get("url", "")) for entry in files]


def _need(path: Path, step: str) -> Path:
    if not path.is_file():
        raise StepInputMissing(
            f"{bulk.DATASET}: {path.name} is missing; run --step {step} first",
            "input",
            counts_only=True,
        )
    return path


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: CompaniesHouseSource = profile.options(bulk.DATASET)
    steps = context.steps or STEPS
    if "slice" in steps and options.companies is None:  # before the long index pass
        raise BuildError(f"{profile.profile}: no companies block", "profile", counts_only=True)
    work = context.work_dir
    work.mkdir(parents=True, exist_ok=True)
    counts: dict[str, Any] = {}
    strings: dict[str, str] = {}
    if "index" in steps or "companies" in steps:
        version, parts, urls = companies_download()
        strings["version"] = version
    if "index" in steps:
        counts["index"] = bulk.build_index(parts, work / INDEX, version)
    if "slice" in steps and options.companies is not None:
        index = _need(work / INDEX, "index")
        counts["slice"], strings["slice_sha256"] = slices.build_slice(
            index, options.companies, work / SLICE
        )
        slices.write_meta(work / SLICE_META, version=bulk.index_version(index),
                          sample_seed=options.companies.sample_seed,
                          sha256=strings["slice_sha256"])  # fmt: skip
    if "companies" in steps:
        meta = slices.read_meta(_need(work / SLICE_META, "slice"))
        if meta.get("version") != version:
            raise StepInputMissing(
                f"{bulk.DATASET}: slice.csv comes from snapshot {meta.get('version')}, the newest"
                f" download is {version}; run --step index --step slice first",
                "snapshot",
                counts_only=True,
            )
        strings["slice_sha256"] = str(meta.get("slice_sha256"))
        counts["companies"], strings["statements"] = records.write_companies(
            parts,
            _need(work / SLICE, "slice"),
            work / PSC_INDEX,
            context.out_dir,
            version=version,
            urls=urls,
        )
    return BuildResult(counts=counts, strings=strings)


def cleanup(profile: Profile, context: BuildContext, result: BuildResult) -> None:
    """After a successful build that ran the `companies` step: delete the work indexes
    (unless `--keep-work`); `slice.csv` and `slice.json` stay for the later steps."""
    if "companies" in (context.steps or STEPS) and not context.keep_work:
        for name in (INDEX, PSC_INDEX):
            (context.work_dir / name).unlink(missing_ok=True)


register_builder(
    Builder(
        bulk.DATASET,
        build,
        steps=STEPS,
        string_keys=("slice_sha256", "statements"),
        cleanup=cleanup,
    )
)
