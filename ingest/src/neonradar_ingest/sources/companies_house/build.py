"""The `gb_companies_house` builder and its profile block (PHASE-2.md M2.3 build steps, M2.3a).

`neonradar ingest build --dataset gb_companies_house [--step <name>]...` runs the steps of the
merged sub-milestones in order: `index`, `slice` and `companies` (M2.3a), with `psc-index`
and `psc` (M2.3b) when the profile's `psc` block is enabled; M2.3c adds `officers`. Each step
reads the previous steps' work files in `layout.work_dir(profile, dataset)`; a missing input
stops the step with exit code 2 and names the step to run first. After a successful build
(records validated and swapped in) that ran the `companies` or `psc` step, the work indexes
are deleted unless `--keep-work` is given; `slice.csv` and `slice.json` stay until the next
`slice` step. The `companies` step refuses (exit 2) a slice built from another snapshot than
the newest download. A `psc` step run without the `companies` step keeps the previous company
records, which its links point to.
"""

import json
import re
import shutil
from collections.abc import Callable
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


def products(profile: Profile) -> dict[str, Callable[[HttpClient], list[RemoteFile]]]:
    """The products a profile needs (`data fetch`): `companies`, and `psc` only when the
    profile's `psc` block is enabled, so PSC data is never downloaded for nothing."""
    options: CompaniesHouseSource = profile.options(bulk.DATASET)
    wanted: dict[str, Callable[[HttpClient], list[RemoteFile]]] = {bulk.PRODUCT: bulk.discover}
    if options.psc is not None and options.psc.enabled:
        wanted[psc.PRODUCT] = psc.discover
    return wanted


register_source(SourceSpec(bulk.DATASET, discover, products=products))
PARTS = {bulk.PRODUCT: bulk.PART_RE, psc.PRODUCT: psc.PART_RE}


def latest_download(product: str) -> tuple[str, list[Path], list[str]]:
    """The newest complete download of a product: version, parts, stored URLs."""
    product_dir = layout.sources_dir(bulk.DATASET, product, "latest").parent
    complete: list[tuple[str, dict[str, Any]]] = []
    for folder in sorted(product_dir.iterdir()) if product_dir.is_dir() else []:
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
        (folder / entry["name"] for entry in files),
        key=lambda path: bulk.part_number(path, PARTS[product]),
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


def _steps(options: CompaniesHouseSource, context: BuildContext) -> tuple[str, ...]:
    """The steps to run: the PSC steps only with an enabled `psc` block."""
    enabled = options.psc is not None and options.psc.enabled
    return context.steps or tuple(s for s in STEPS if enabled or s not in PSC_STEPS)


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: CompaniesHouseSource = profile.options(bulk.DATASET)
    steps = _steps(options, context)
    block = options.psc if options.psc is not None and options.psc.enabled else None
    if block is None and set(steps) & set(PSC_STEPS):
        message = f"{profile.profile}: the psc block is not enabled"
        raise BuildError(message, "profile", counts_only=True)
    if "slice" in steps and options.companies is None:  # before the long index pass
        raise BuildError(f"{profile.profile}: no companies block", "profile", counts_only=True)
    work = context.work_dir
    work.mkdir(parents=True, exist_ok=True)
    counts: dict[str, Any] = {}
    strings: dict[str, str] = {}
    if "index" in steps or "companies" in steps:
        version, parts, urls = latest_download(bulk.PRODUCT)
        strings["version"] = version
    if block is not None and ("psc-index" in steps or "psc" in steps):
        psc_version, psc_parts, psc_urls = latest_download(psc.PRODUCT)
        strings["snapshot_date"] = psc_version
    if "index" in steps:
        counts["index"] = bulk.build_index(parts, work / INDEX, version)
    if block is not None and "psc-index" in steps:
        counts["psc-index"], strings["totals_check"] = psc.build_index(
            psc_parts,
            work / PSC_INDEX,
            _need(work / INDEX, "index"),
            block.include_ceased,
            psc_version,
        )
    if "slice" in steps and options.companies is not None:
        index = _need(work / INDEX, "index")
        expansion, psc_snapshot = None, None
        if block is not None:
            psc_snapshot = bulk.index_version(_need(work / PSC_INDEX, "psc-index"))
            if psc_snapshot is not None:
                strings.setdefault("snapshot_date", psc_snapshot)
            expansion = psc.expansion(
                work / PSC_INDEX,
                index,
                block.parent_depth,
                block.child_depth,
                options.companies.sample_seed,
            )
        counts["slice"], strings["slice_sha256"] = slices.build_slice(
            index, options.companies, work / SLICE, expansion
        )
        slices.write_meta(
            work / SLICE_META,
            version=bulk.index_version(index),
            sample_seed=options.companies.sample_seed,
            sha256=strings["slice_sha256"],
            psc_snapshot=psc_snapshot,
        )
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
    if block is not None and "psc" in steps:
        meta = slices.read_meta(_need(work / SLICE_META, "slice"))
        if meta.get("psc_snapshot") != psc_version:
            raise StepInputMissing(
                f"{bulk.DATASET}: slice.csv comes from PSC snapshot {meta.get('psc_snapshot')},"
                f" the newest PSC download is {psc_version}; run --step psc-index --step slice"
                " first",
                "snapshot",
                counts_only=True,
            )
        counts["psc"], strings["totals_check"] = psc.write_pscs(
            psc_parts,
            _need(work / SLICE, "slice"),
            _carry(profile, context.out_dir, "companies"),
            context.out_dir,
            include_ceased=block.include_ceased,
            version=psc_version,
            urls=psc_urls,
        )
    return BuildResult(counts=counts, strings=strings)


def cleanup(profile: Profile, context: BuildContext, result: BuildResult) -> None:
    """After a successful build that ran the `companies` or `psc` step: delete the work
    indexes (unless `--keep-work`); `slice.csv` and `slice.json` stay for the later steps."""
    steps = _steps(profile.options(bulk.DATASET), context)
    if {"companies", "psc"} & set(steps) and not context.keep_work:
        for name in (INDEX, PSC_INDEX):
            (context.work_dir / name).unlink(missing_ok=True)


register_builder(
    Builder(
        bulk.DATASET,
        build,
        steps=STEPS,
        string_keys=("slice_sha256", "statements", "snapshot_date", "totals_check"),
        cleanup=cleanup,
    )
)
