"""`neonradar synth world` and `synth overlay` (PHASE-3.md M3.3 deliverable 4, 4.5, 7.2).

`make_world` generates a synthetic profile's register from its world block; `make_overlay`
streams a base (the profile's world, or `--base`) into the overlay generator and writes the
records, `labels/` and `overlay.json`. Both validate every record with C1's validator before
anything is written, and both refuse a holdout seed (G11). Real profiles get their overlay in
M3.4: `make_overlay` refuses them with exit 3 before it reads anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import batched
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from followthemoney import model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import (
    RecordIssue,
    iter_records,
    manifest_path,
    validate_batch,
    validate_record,
)
from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import REPO_ROOT, Project
from neonradar_ingest.synth import labels, overlay, world, writer
from neonradar_ingest.synth.base import REGISTRY_ID_PREFIXES
from neonradar_ingest.synth.namesource import default_names

SEEDS_FILE = REPO_ROOT / "eval" / "seeds.yaml"  # looked up per call, so tests can patch it
MISSING = re.compile(r"points to '([^']+)', which is not in this load")
SHOWN_ISSUES = 20
CHUNK = 20_000  # lines per validation task
WORKERS = 4  # validation processes at most (validate_record is pure, and the slow part)


class SynthError(Exception):
    """A refusal or a failed check; `exit_code` is the command's exit status."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class Written:
    """What a command wrote: its folder, record file, the file's SHA-256 and counts."""

    folder: Path
    records_file: Path
    sha256: str
    seed: int
    by_schema: dict[str, int]
    overlay_id: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)


def holdout_seeds() -> frozenset[int]:
    """The holdout seeds: `test.seeds` of eval/seeds.yaml, once M3.11 has written them."""
    if not SEEDS_FILE.is_file():
        return frozenset()
    data = yaml.safe_load(SEEDS_FILE.read_text(encoding="utf-8")) or {}
    test = data.get("test") if isinstance(data, dict) else None
    seeds = test.get("seeds") if isinstance(test, dict) else None
    return frozenset(int(seed) for seed in seeds or [])


def refuse_holdout(seed: int) -> None:
    if seed in holdout_seeds():
        raise SynthError(
            f"seed {seed} is a holdout seed (eval/seeds.yaml test.seeds): a holdout world is"
            " generated only inside `neonradar eval run --split test`, which a human runs (G11)",
            2,
        )


PROTECTED = ("real", "spikes", "holdout", "heldout")  # data/cache/ folders generation never touches


def refuse_protected(what: str, path: Path | None) -> None:
    """Exit 3 when `path` lies in a protected cache folder: real data, spike output, or the
    holdout and held-out runs (G9, G11), checked before anything is read or written. Paths are
    compared case-folded, because APFS and NTFS are case-insensitive (as guard_real_data.py)."""
    if path is None:
        return
    resolved = path.resolve()
    folded = [part.casefold() for part in resolved.parts]
    named = any(
        folded[i : i + 2] == ["data", "cache"] and folded[i + 2] in PROTECTED
        for i in range(len(folded) - 2)
    )
    roots = [(layout.CACHE_ROOT / name).resolve() for name in PROTECTED]
    as_text = PurePosixPath(*folded)
    inside = any(as_text.is_relative_to(PurePosixPath(str(r).casefold())) for r in roots)
    existing = [p for p in (resolved, *resolved.parents) if p.exists()]
    same = any(os.path.samefile(p, r) for p in existing for r in roots if r.exists())
    if named or inside or same:
        raise SynthError(
            f"{what} lies in a protected data/cache folder (real data, spike output or the"
            " holdout runs): synthetic generation never reads or writes there (G9, G11)",
            3,
        )


def refuse_holdout_base(files: Iterable[Path]) -> None:
    """Exit 2 when a base file's manifest names a holdout seed (G11)."""
    holdout = holdout_seeds()
    for path in files:
        meta = manifest_path(path)
        seed = json.loads(meta.read_text(encoding="utf-8")).get("seed") if meta.is_file() else None
        if isinstance(seed, int) and seed in holdout:
            refuse_holdout(seed)


def _failed(issues: list[RecordIssue]) -> SynthError:
    shown = "\n".join(f"  {issue}" for issue in issues[:SHOWN_ISSUES])
    more = f"\n  ... and {len(issues) - SHOWN_ISSUES} more" if len(issues) > SHOWN_ISSUES else ""
    return SynthError(f"{len(issues)} C1 issues in the generated records:\n{shown}{more}", 1)


def _target(folder: Path, name: str) -> Path:
    """`folder`, refusing one that already holds other record files (one base, one load)."""
    others = [p.name for p in folder.glob("*.ftm.jsonl") if p.name != f"{name}.ftm.jsonl"]
    if others:
        raise SynthError(f"{folder} already holds other record files: {', '.join(others)}", 2)
    return folder


def make_world(profile: Profile, seed: int | None, out: Path | None, *, git_sha: str) -> Written:
    """Generate, validate (R1 to R10, then R4 and R8 strictly) and write a profile's world."""
    refuse_protected("--out", out)
    block = profile.world
    if profile.real_data or block is None:
        raise SynthError(
            f"profile {profile.profile} has no world: synth world makes the register of a"
            " synthetic profile with sources.nr_synthetic.world",
            2,
        )
    seed = profile.world_seed(seed)
    refuse_holdout(seed)
    config = block.config()
    records = world.generate(seed, config, default_names())
    issues = [issue for record in records for issue in validate_record(record)]
    issues += validate_batch(records, strict=True)
    if issues:
        raise _failed(issues)
    name = f"nr_synthetic-{config.today:%Y%m%d}-world"  # the world's date, never the clock
    folder = _target(out or layout.worlds_dir(block.name, seed), name)
    refuse_protected("the output folder", folder)
    sha = writer.write_part(folder, name, writer.items(records), seed=seed, git_sha=git_sha)
    by_schema = Counter(str(record["schema"]) for record in records)
    return Written(folder, folder / f"{name}.ftm.jsonl", sha, seed, dict(sorted(by_schema.items())))


@dataclass(slots=True)
class BaseIndex:
    """What the overlay command keeps of the base: ids, never records (L18, R4 and R8)."""

    kinds: dict[str, str] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)
    legal_entities: set[str] = field(default_factory=set)
    datasets: set[str] = field(default_factory=set)
    records: int = 0

    def read(self, files: Iterable[Path]) -> Iterator[dict[str, Any]]:
        """Stream the records of `files`, line by line, indexing each one. The base of a
        synthetic profile holds synthetic records only: the first record of any other dataset
        kind stops the command (exit 3) before the generator writes anything, naming no id."""
        for path in files:
            for record in iter_records(path):
                kinds = {self.kinds.get(d) for d in record.get("datasets") or [""]}
                if kinds != {"synthetic"} or not str(record.get("id", "")).startswith("syn-"):
                    raise SynthError(
                        "the base holds a record that is not synthetic: a synthetic profile"
                        " never reads real records (G9; real profiles come with M3.4)",
                        3,
                    )
                self.records += 1
                rid = str(record.get("id"))
                self.ids.add(rid)
                self.datasets.update(record.get("datasets") or [])
                schema = model.get(str(record.get("schema")))
                if schema is not None and schema.is_a("LegalEntity"):
                    self.legal_entities.add(rid)
                yield record


def dataset_kinds() -> dict[str, str]:
    """Each registered dataset's `kind` (contracts/datasets.yaml, C1 1.1.0). A registry the
    generator has no company-record rule for is left out, so its records are never eligible
    (`unknown_dataset_kind`: fail closed, M3.3 review)."""
    return {
        d.slug: d.kind
        for d in load_registry().datasets
        if d.kind is not None and (d.kind != "registry" or d.slug in REGISTRY_ID_PREFIXES)
    }


def _resolution(profile: Profile) -> tuple[Path | None, str | None]:
    """The base's latest resolution run (`canonical.csv` and its id), when the profile resolves."""
    if not profile.resolution.enabled:
        return None, None
    run_id = layout.latest_run(profile)
    if run_id is None:
        return None, None
    path = layout.resolution_dir(profile, run_id) / "canonical.csv"
    return (path, run_id) if path.is_file() else (None, None)


def _base_files(files: list[Path]) -> list[dict[str, Any]]:
    """The base's record files with their SHA-256 (from the manifest when there is one)."""
    out = []
    for path in files:
        sha = None
        meta = manifest_path(path)
        if meta.is_file():
            entries = json.loads(meta.read_text(encoding="utf-8")).get("files", [])
            sha = next((e.get("sha256") for e in entries if e.get("path") == path.name), None)
        if sha is None:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append({"file": path.name, "sha256": sha})
    return out


def _resolved_by_base(issue: RecordIssue, index: BaseIndex, holders: dict[str, set[str]]) -> bool:
    """An R4 issue whose missing id is a base id, or an R8 issue whose account's holder is a
    base LegalEntity: the base counts as part of the same load (L18, C1 R4 and R8)."""
    if issue.rule == "R4":
        found = MISSING.search(issue.message)
        return found is not None and found[1] in index.ids
    if issue.rule == "R8" and issue.record_id is not None:
        return bool(holders.get(issue.record_id, set()) & index.legal_entities)
    return False


def _validate_lines(lines: tuple[str, ...]) -> list[RecordIssue]:
    """R1 to R10 for each record line (a worker task)."""
    return [issue for text in lines for issue in validate_record(json.loads(text))]


def validate_lines(lines: Iterable[str]) -> list[RecordIssue]:
    """`validate_record` over every line; issues in line order. Worker processes (one per four
    20,000-line chunks, at most `WORKERS`) start from eight chunks, more than 140,000 lines, on:
    below that, starting them costs more than it saves."""
    chunks = list(batched(lines, CHUNK, strict=False))
    workers = min(WORKERS, os.cpu_count() or 1, len(chunks) // 4)
    if workers <= 1:
        return [issue for chunk in chunks for issue in _validate_lines(chunk)]
    with ProcessPoolExecutor(workers) as pool:
        return [issue for found in pool.map(_validate_lines, chunks) for issue in found]


def _parsed(ov: overlay.Overlay) -> Iterator[dict[str, Any]]:
    for _, text in ov.items():
        record: dict[str, Any] = json.loads(text)
        yield record


def make_overlay(
    profile: Profile,
    seed: int | None,
    base: Path | None,
    out: Path | None,
    *,
    project: Project,
    git_sha: str,
    clock: datetime | None = None,
) -> Written:
    """Generate, validate and write the overlay of a synthetic profile (PHASE-3.md 4.5, 7.2.7)."""
    if profile.real_data:
        raise SynthError(
            f"profile {profile.profile} is a real profile: its overlay comes with M3.4", 3
        )
    refuse_protected("--base", base)
    refuse_protected("--out", out)
    block = profile.overlay
    if block is None or not block.enabled:
        raise SynthError(f"profile {profile.profile} has no enabled overlay block", 2)
    overlay_seed = profile.overlay_seed(seed)
    refuse_holdout(overlay_seed)
    if base is not None:
        folders = [base]
    else:
        world_seed = profile.world_seed(seed) if profile.world is not None else None
        if world_seed is not None:
            refuse_holdout(world_seed)
        folders = profile.record_dirs(project, seed=world_seed)
    for folder in folders:
        refuse_protected("a base folder", folder)
    files = sorted(path for folder in folders for path in folder.glob("*.ftm.jsonl"))
    if not files:
        raise SynthError(f"no record files in the base ({', '.join(map(str, folders))})", 2)
    for path in files:  # a symlink into a protected folder is refused before it is opened
        refuse_protected("a base file", path)
        refuse_protected("a base manifest", manifest_path(path))
    refuse_holdout_base(files)
    canonical, run_id = _resolution(profile)
    refuse_protected("the resolution run", canonical)
    if profile.resolution.enabled and canonical is None:
        raise SynthError(
            "the profile resolves its base, but it has no resolution run with a canonical.csv:"
            " run `neonradar er run` first (without it a merged entity could get two accounts)",
            3,
        )
    config = block.config(overlay_seed)
    kinds = dataset_kinds()
    index = BaseIndex(kinds)
    ov = overlay.generate(index.read(files), kinds, config, default_names(), canonical)

    by_schema = Counter(schema for schema, _ in ov.items())
    issues = validate_lines(text for _, text in ov.items())
    holders: dict[str, set[str]] = {}
    for record in ov.other_records.values():
        props = record["properties"]
        if record["schema"] == "Ownership" and props.get("role") == ["account holder"]:
            for asset in props.get("asset", []):
                holders.setdefault(asset, set()).update(props.get("owner", []))
    batch = validate_batch(_parsed(ov), strict=True)
    issues += [issue for issue in batch if not _resolved_by_base(issue, index, holders)]
    if issues:
        raise _failed(issues)

    overlay_id = layout.new_run_id("ov")
    name = f"nr_synthetic-{config.end:%Y%m%d}-overlay"  # the period's end, never the clock
    folder = _target(out or layout.overlay_dir(profile, overlay_id), name)
    refuse_protected("the output folder", folder)
    sha = writer.write_part(folder, name, ov.items(), seed=overlay_seed, git_sha=git_sha)
    texts = labels.files(
        ov.labels,
        seed=overlay_seed,
        record_sha256={f"{name}.ftm.jsonl": sha},
        generator_version=writer.GENERATOR_VERSION,
    )
    labels.write(folder / "labels", texts)
    counts = {
        "records_by_schema": dict(sorted(by_schema.items())),
        "eligible_organisations": ov.stats["eligible"],
        "active_organisations": ov.stats["background"]["organisations"],
        "employees": ov.stats["background"]["employees"],
        "skipped_organisations": dict(sorted(ov.stats["skipped"].items())),
        "scenarios": ov.stats["scenarios"],
    }
    meta = {
        "overlay_id": overlay_id,
        "profile": profile.profile,
        "seed": overlay_seed,
        "split": config.split,
        "generator_version": writer.GENERATOR_VERSION,
        "label_schema": labels.LABEL_SCHEMA,
        "period": {"start": config.start.isoformat(), "end": config.end.isoformat()},
        "config": {
            **block.model_dump(mode="json"),
            "seed": overlay_seed,
            "typologies": list(config.typologies),
        },
        "base": {
            "datasets": sorted(index.datasets),
            "records": index.records,
            "files": _base_files(files),
            "resolution_run": run_id,
        },
        "records_sha256": sha,
        "counts": counts,
        "created_at": (clock or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (folder / "overlay.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if out is None:  # LATEST last, so it only ever names a complete overlay
        latest = folder.parent / layout.LATEST
        partial = latest.with_suffix(".tmp")
        partial.write_text(overlay_id + "\n", encoding="utf-8")
        partial.replace(latest)
    return Written(
        folder,
        folder / f"{name}.ftm.jsonl",
        sha,
        overlay_seed,
        counts["records_by_schema"],
        overlay_id,
        counts,
    )
