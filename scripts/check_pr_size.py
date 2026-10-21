#!/usr/bin/env python3
"""Check the size of a pull request (docs/build/PHASE-1.md 2.3).

Sums added plus deleted lines from `git diff --numstat <base>...HEAD`, leaving out paths that
match a glob in .github/pr-size-exclude.txt (fnmatch: `*` also matches `/`, and a leading
`**/` also matches the top level). Above the limit it fails, or only warns when the labels
include `size-exception`.

    python3 scripts/check_pr_size.py --base origin/main --labels '["agent", "size-exception"]'

Standard library only.
"""

import argparse
import fnmatch
import sys
from pathlib import Path

from hygiene_common import ROOT, GitError, annotate, git, parse_labels

DEFAULT_LIMIT = 400
EXCLUDE_FILE = ".github/pr-size-exclude.txt"
SIZE_EXCEPTION = "size-exception"
SHOWN = 15


def read_patterns_from_text(text: str) -> list[str]:
    lines = text.splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def is_excluded(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]):
            return True
    return False


def numstat(root: Path, base: str) -> list[tuple[str, int]]:
    """(path, added plus deleted lines) per changed file; binary files count 0."""
    fields = git(root, "diff", "--numstat", "-z", "-M", f"{base}...HEAD").split("\0")
    changes: list[tuple[str, int]] = []
    i = 0
    while i < len(fields):
        entry = fields[i]
        if not entry:
            i += 1
            continue
        added, deleted, path = entry.split("\t", 2)
        if path:
            i += 1
        else:  # a rename or copy: the old and the new path follow as separate fields
            path = fields[i + 2]
            i += 3
        lines = 0 if added == "-" or deleted == "-" else int(added) + int(deleted)
        changes.append((path, lines))
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a pull request changes more than the limit of counted lines "
        "(PHASE-1.md 2.3); only warn with the size-exception label."
    )
    parser.add_argument("--base", default="origin/main", help="base ref (default origin/main)")
    parser.add_argument(
        "--labels", default="", help="pull request labels: a JSON array or a comma-separated list"
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="default 400")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    try:
        labels = parse_labels(args.labels)
        patterns = read_patterns_from_text((args.root / EXCLUDE_FILE).read_text(encoding="utf-8"))
        changes = numstat(args.root, args.base)
    except (GitError, OSError, ValueError) as exc:
        print(f"check_pr_size: FAIL: {exc}")
        return 1

    counted = sorted(
        ((path, lines) for path, lines in changes if not is_excluded(path, patterns)),
        key=lambda change: (-change[1], change[0]),
    )
    total = sum(lines for _, lines in counted)
    excluded = sum(lines for path, lines in changes if is_excluded(path, patterns))
    print(
        f"check_pr_size: {total} counted lines in {len(counted)} files (limit {args.limit}); "
        f"{excluded} lines in files excluded by {EXCLUDE_FILE}"
    )
    for path, lines in counted[:SHOWN]:
        print(f"  {lines:6d}  {path}")
    if len(counted) > SHOWN:
        print(f"  ... and {len(counted) - SHOWN} more files")

    if total <= args.limit:
        print("check_pr_size: OK")
        return 0
    if SIZE_EXCEPTION in labels:
        annotate(
            "warning",
            f"check_pr_size: WARN: {total} counted lines is above the limit of {args.limit}; "
            f"allowed because the pull request has the {SIZE_EXCEPTION} label",
        )
        return 0
    annotate(
        "error",
        f"check_pr_size: FAIL: {total} counted lines is above the limit of {args.limit}. Split "
        f"the pull request (PHASE-1.md 2.3), or add the {SIZE_EXCEPTION} label if the milestone "
        "header says 'Size: exception'.",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
