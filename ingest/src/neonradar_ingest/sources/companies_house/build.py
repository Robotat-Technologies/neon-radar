"""The `gb_companies_house` builder and its profile block (PHASE-2.md M2.3 build steps, M2.3a).

`neonradar ingest build --dataset gb_companies_house [--step <name>]...` runs the steps of the
merged sub-milestones in order: `index`, `slice` and `companies` (M2.3a), with `psc-index`
and `psc` (M2.3b) when the profile's `psc` block is enabled; M2.3c adds `officers`. Each step
reads the previous steps' work files in `layout.work_dir(profile, dataset)`; a missing input
stops the step with exit code 2 and names the step to run first. A build that runs the
`companies` or `psc` step deletes the work indexes at its end unless `--keep-work` is given;
`slice.csv` stays until the next `slice` step. A `psc` step run without the `companies` step
keeps the previous company records, which its links point to.
"""

import json
import re
import shutil
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
    RemoteFile,
    SourceSpec,
    register_builder,
    register_source,
)
from neonradar_ingest.http import HttpClient
from neonradar_ingest.sources.companies_house import bulk, psc, records
from neonradar_ingest.sources.companies_house import slice as slices

STEPS = ("index", "psc-index", "slice", "companies", "psc")
PSC_STEPS = ("psc-index", "psc")  # only with an enabled `psc` block
INDEX = "companies.sqlite"
PSC_INDEX = "corporate_pscs.sqlite"  # written by the psc-index step
SLICE = "slice.csv"
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


class PscBlock(BaseModel):
    """The `psc` block of a profile (PHASE-2.md 7.8, M2.3b deliverable 9)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    parent_depth: StrictInt = Field(default=0, ge=0)
    child_depth: StrictInt = Field(default=0, ge=0)
    include_ceased: StrictBool = False


class CompaniesHouseSource(BaseModel):
    """The `gb_companies_house` block; `officers` stays a mapping until M2.3c."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    companies: CompaniesBlock | None = None
    psc: PscBlock | None = None
    officers: dict[str, Any] | None = None


register_source_model(bulk.DATASET, CompaniesHouseSource)


def discover(client: HttpClient) -> list[RemoteFile]:
    """The current parts of both bulk products: `companies` (monthly) and `psc` (daily)."""
    return [*bulk.discover(client), *psc.discover(client)]


register_source(SourceSpec(bulk.DATASET, discover))
PARTS = {bulk.PRODUCT: bulk.PART_RE, psc.PRODUCT: psc.PART_RE}


def latest_download(product: str) -> tuple[str, list[Path], list[str]]:
    """The newest complete download of a product: version, parts, stored URLs."""
    product_dir = layout.sources_dir(bulk.DATASET, product, "latest").parent
    complete: list[tuple[str, dict[str, Any]]] = []
    for folder in sorted(product_dir.iterdir()) if product_dir.is_dir() else []:
        try:
            record = json.loads((folder / RECORD).read_text(encoding="utf-8"))
        except FileNotFoundError, ValueError:
            continue
        if isinstance(record, dict) and record.get("complete"):
            complete.append((folder.name, record))
    if not complete:
        raise StepInputMissing(
            f"{bulk.DATASET}: no complete download of the {product} product; run"
            f" neonradar data fetch --profile <profile> --dataset {bulk.DATASET} first",
            "input",
            counts_only=True,
        )
    version, record = max(complete, key=lambda item: item[0])
    files = [
        entry
        for entry in record.get("files", [])
        if entry.get("product") == product and PARTS[product].fullmatch(str(entry.get("name")))
    ]
    folder = layout.sources_dir(bulk.DATASET, product, version)
    parts = sorted(
        (folder / e["name"] for e in files), key=lambda p: bulk.part_number(p, PARTS[product])
    )
    return version, parts, [str(entry.get("url", "")) for entry in files]


def _need(path: Path, step: str) -> Path:
    if not path.is_file():
        raise StepInputMissing(
            f"{bulk.DATASET}: {path.name} is missing; run --step {step} first",
            "input",
            counts_only=True,
        )
    return path


def _carry(profile: Profile, out_dir: Path, name: str) -> Path:
    """`<name>.ftm.jsonl` in `out_dir`, copied with its manifest from the previous records
    when this build did not write it; StepInputMissing when there is none."""
    path = out_dir / f"{name}.ftm.jsonl"
    if not path.is_file():
        previous = layout.records_dir(profile, bulk.DATASET)
        for suffix in (".ftm.jsonl", ".manifest.json"):
            if (previous / f"{name}{suffix}").is_file():
                shutil.copy2(previous / f"{name}{suffix}", out_dir / f"{name}{suffix}")
    return _need(path, name)


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: CompaniesHouseSource = profile.options(bulk.DATASET)
    block = options.psc if options.psc is not None and options.psc.enabled else None
    steps = context.steps or tuple(s for s in STEPS if block is not None or s not in PSC_STEPS)
    if block is None and set(steps) & set(PSC_STEPS):
        raise BuildError(f"{profile.profile}: the psc block is not enabled", "profile",
                         counts_only=True)  # fmt: skip
    work = context.work_dir
    work.mkdir(parents=True, exist_ok=True)
    counts: dict[str, Any] = {}
    strings: dict[str, str] = {}
    if "index" in steps or "companies" in steps:
        version, parts, urls = latest_download(bulk.PRODUCT)
        strings["version"] = version
    if block is not None and ("psc-index" in steps or "psc" in steps):
        strings["snapshot_date"], psc_parts, psc_urls = latest_download(psc.PRODUCT)
    if "index" in steps:
        counts["index"] = bulk.build_index(parts, work / INDEX)
    if block is not None and "psc-index" in steps:
        counts["psc-index"], strings["totals_check"] = psc.build_index(
            psc_parts, work / PSC_INDEX, _need(work / INDEX, "index"), block.include_ceased
        )
    if "slice" in steps:
        if options.companies is None:
            raise BuildError(f"{profile.profile}: no companies block", "profile", counts_only=True)
        expansion = None
        if block is not None:
            expansion = psc.expansion(_need(work / PSC_INDEX, "psc-index"), work / INDEX,
                                      block.parent_depth, block.child_depth,
                                      options.companies.sample_seed)  # fmt: skip
        counts["slice"], strings["slice_sha256"] = slices.build_slice(
            _need(work / INDEX, "index"), options.companies, work / SLICE, expansion
        )
    if "companies" in steps:
        counts["companies"], strings["statements"] = records.write_companies(
            parts,
            _need(work / SLICE, "slice"),
            work / PSC_INDEX,
            context.out_dir,
            version=version,
            urls=urls,
        )
    if block is not None and "psc" in steps:
        counts["psc"], strings["totals_check"] = psc.write_pscs(
            psc_parts,
            _need(work / SLICE, "slice"),
            _carry(profile, context.out_dir, "companies"),
            context.out_dir,
            include_ceased=block.include_ceased,
            version=strings["snapshot_date"],
            urls=psc_urls,
        )
    if not context.keep_work and ("companies" in steps or "psc" in steps):
        for name in (INDEX, PSC_INDEX):  # only after every step of the build has run
            (work / name).unlink(missing_ok=True)
    return BuildResult(counts=counts, strings=strings)


register_builder(
    Builder(
        bulk.DATASET,
        build,
        steps=STEPS,
        string_keys=("slice_sha256", "statements", "snapshot_date", "totals_check"),
    )
)
