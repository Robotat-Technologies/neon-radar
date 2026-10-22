"""Generate .github/CODEOWNERS from docs/build/project.yaml and the ownership map.

The ownership map is docs/build/PHASE-1.md section 4.3 plus the 4.3 sections of PHASE-2.md,
PHASE-3.md and PHASE-4.md.
GitHub applies the
last matching line, so rows keep the tables' order, adjusted so that every path comes after any
broader path containing it.

    uv run --no-project --with pyyaml python scripts/generate_codeowners.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECT_FILE = ROOT / "docs" / "build" / "project.yaml"
CODEOWNERS_FILE = ROOT / ".github" / "CODEOWNERS"
COMMAND = "uv run --no-project --with pyyaml python scripts/generate_codeowners.py"

# PHASE-1.md 4.3, then PHASE-2.md, PHASE-3.md and PHASE-4.md 4.3, in table order: (paths, owner
# roles). "mentor:<squad>" is that squad's mentor in project.yaml.
# "/*" means files in
# the root directory.
OWNERSHIP_MAP: list[tuple[list[str], list[str]]] = [
    (["/contracts/", "/graph/schema/"], ["tech_lead", "maintainers"]),
    (["/ingest/", "/data/fixtures/"], ["squad:ingest"]),
    (["/graph/"], ["squad:graph"]),
    (["/detect/"], ["squad:detect"]),
    (["/copilot/", "/api/"], ["squad:copilot"]),
    (["/ui/"], ["squad:ui"]),
    (["/cli/", "/docs/", "/*", "/.github/", "/.devcontainer/", "/Makefile"], ["squad:docs"]),
    (["/.claude/", "/CLAUDE.md", "/docs/build/"], ["tech_lead"]),
    (["/docs/build/PROGRESS.md"], []),  # no code owner: every pull request updates it
    (["/DATA_SOURCES.md", "/docs/data/licences/"], ["data_steward"]),
    (["/contracts/datasets.yaml"], ["tech_lead", "data_steward"]),
    (["/docs/typologies/", "/detect/typologies/"], ["typology_researchers"]),
    # PHASE-2.md 4.3 additions
    (["/keys/", "/resolve/"], ["squad:graph"]),
    (["/resolve/config/er.yaml"], ["squad:graph", "tech_lead"]),
    (["/ingest/profiles/"], ["squad:ingest", "data_steward"]),
    (["/docs/er/", "/docs/data/er/"], ["squad:graph"]),
    (
        [
            "/docs/data/real-data-handling.md",
            "/docs/data/real-data-machines.md",
            "/docs/data/dpia/",
        ],
        ["data_steward"],
    ),
    (["/data/fixtures/er-bench/"], ["squad:graph"]),
    (
        [
            "/.claude/hooks/guard_real_data.py",
            "/.claude/agents/data-guardian.md",
            "/.claude/rules/real-data.md",
            "/.claude/rules/er.md",
        ],
        ["tech_lead"],
    ),
    (["/THIRD_PARTY_NOTICES.md"], ["tech_lead"]),
    # PHASE-3.md 4.3 additions
    (["/eval/"], ["squad:detect", "tech_lead"]),
    (["/eval/freeze.json", "/eval/seeds.yaml"], ["tech_lead", "typology_researchers"]),
    (["/detect/tests/"], ["squad:detect", "typology_researchers"]),
    (["/ingest/src/neonradar_ingest/synth/scenarios/"], ["squad:ingest", "typology_researchers"]),
    (["/docs/detection/", "/docs/data/detection/"], ["squad:detect"]),
    (["/.claude/rules/detect.md", "/.claude/rules/synth.md"], ["tech_lead"]),
    # PHASE-4.md 4.3 additions
    (
        ["/copilot/bench/", "/data/fixtures/copilot-bench/", "/docs/benchmark-questions.md"],
        ["squad:copilot", "mentor:copilot"],
    ),
    (
        [
            "/copilot/src/neonradar_copilot/policy.py",
            "/copilot/src/neonradar_copilot/evidence.py",
            "/copilot/src/neonradar_copilot/audit.py",
            "/contracts/wording/copilot-notice-v1.txt",
        ],
        ["squad:copilot", "data_steward"],
    ),
    (
        [
            "/graph/src/neonradar_graph/readonly.py",
            "/copilot/src/neonradar_copilot/queries/",
            "/api/src/neonradar_api/queries/",
        ],
        ["squad:graph", "squad:copilot"],
    ),
    (["/api/src/neonradar_api/hardening.py"], ["squad:copilot", "tech_lead"]),
    (["/docs/copilot/", "/docs/team/assignment-5.md"], ["squad:docs", "squad:copilot"]),
]


def resolve_owners(roles: list[str], project: dict) -> list[str]:
    """Turn role names into GitHub handles or teams from project.yaml."""
    people = project["people"]
    owners: list[str] = []
    for role in roles:
        if role == "maintainers":
            found = [project["maintainers_team"]]
        elif role.startswith("squad:"):
            found = [project["squads"][role.removeprefix("squad:")]["team"]]
        elif role.startswith("mentor:"):
            found = [project["squads"][role.removeprefix("mentor:")]["mentor"]]
        else:
            value = people[role]
            found = value if isinstance(value, list) else [value]
        if not found:
            raise SystemExit(f"error: role {role!r} in {PROJECT_FILE.name} has no GitHub handles")
        for owner in found:
            if not isinstance(owner, str) or not owner.startswith("@") or "TODO" in owner:
                raise SystemExit(
                    f"error: role {role!r} in {PROJECT_FILE.name} is not a GitHub handle: {owner!r}"
                )
            if owner not in owners:
                owners.append(owner)
    return owners


def contains(broad: str, specific: str) -> bool:
    """True if every file matched by `specific` is also matched by `broad`."""
    if broad == specific:
        return False
    if broad == "/*":
        return specific.count("/") == 1 and not specific.endswith("/")
    return broad.endswith("/") and specific.startswith(broad)


def ordered_rows(project: dict) -> list[tuple[str, list[str]]]:
    """Rows in table order, moving each path after every broader path that contains it."""
    pending = [
        (path, resolve_owners(roles, project)) for paths, roles in OWNERSHIP_MAP for path in paths
    ]
    placed: list[tuple[str, list[str]]] = []
    while pending:
        row = next(r for r in pending if not any(contains(other[0], r[0]) for other in pending))
        placed.append(row)
        pending.remove(row)
    return placed


def render(project: dict) -> str:
    rows = ordered_rows(project)
    width = max(len(path) for path, _ in rows)
    lines = [
        "# Generated by scripts/generate_codeowners.py from docs/build/project.yaml and the",
        "# ownership map in docs/build/PHASE-1.md section 4.3. Do not edit by hand; run:",
        f"#   {COMMAND}",
        "# GitHub applies the last matching line, so broader paths come first.",
        "",
    ]
    for path, owners in rows:
        lines.append(f"{path.ljust(width)}  {' '.join(owners)}".rstrip())
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate .github/CODEOWNERS from docs/build/project.yaml."
    )
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if .github/CODEOWNERS is out of date"
    )
    args = parser.parse_args(argv)

    content = render(yaml.safe_load(PROJECT_FILE.read_text(encoding="utf-8")))

    if args.check:
        current = CODEOWNERS_FILE.read_text(encoding="utf-8") if CODEOWNERS_FILE.exists() else ""
        if current != content:
            print(f".github/CODEOWNERS is out of date. Run: {COMMAND}", file=sys.stderr)
            return 1
        print(".github/CODEOWNERS is up to date.")
        return 0

    CODEOWNERS_FILE.write_text(content, encoding="utf-8")
    print("Wrote .github/CODEOWNERS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
