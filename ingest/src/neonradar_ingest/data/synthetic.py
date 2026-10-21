"""The `nr_synthetic` builder (PHASE-2.md M2.2 deliverable 12).

It validates each fixture folder the profile lists as one load, in strict mode, and copies
nothing: `Profile.record_dirs()` hands the fixture folders themselves to the resolver and the
graph loader. Synthetic data has no download, so there is no `SourceSpec`.
"""

from collections import Counter

from neonradar_contracts.records import validate_files
from neonradar_ingest.data.profiles import SYNTHETIC, Profile, SyntheticSource
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_ingest.data.sources import (
    BuildContext,
    Builder,
    BuildError,
    BuildResult,
    register_builder,
)

SHOWN = 5  # issues named in the error; the records are synthetic, so their ids may be shown


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: SyntheticSource = profile.options(SYNTHETIC)
    schemas: Counter[str] = Counter()
    files = 0
    for folder in options.fixtures:
        paths = sorted((REPO_ROOT / folder).glob("*.ftm.jsonl"))
        if not paths:
            raise BuildError(f"{folder} holds no .ftm.jsonl file", "fixtures", counts_only=True)
        counts, issues = validate_files(paths, strict=True)
        if issues:
            shown = "; ".join(str(issue) for issue in issues[:SHOWN])
            message = f"{folder}: {len(issues)} C1 issue(s) in strict mode: {shown}"
            raise BuildError(message, "C1", counts_only=True)  # synthetic ids only
        schemas += counts
        files += len(paths)
    return BuildResult(
        counts={
            "fixture_folders": len(options.fixtures),
            "files": files,
            "records": schemas.total(),
            "schemas_by_value": {name.lower(): count for name, count in sorted(schemas.items())},
        }
    )


register_builder(Builder(SYNTHETIC, build))
