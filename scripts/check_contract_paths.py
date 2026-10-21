#!/usr/bin/env python3
"""Check that changes to frozen contract paths carry the contract-change label (PHASE-1.md 5.0).

Fails when the diff `<base>...HEAD` touches contracts/ or graph/schema/, the tag
contracts-v1.0.0 exists, and the labels do not include `contract-change`.

    python3 scripts/check_contract_paths.py --base origin/main --labels '["agent"]'

Standard library only.
"""

import argparse
import sys
from pathlib import Path

from hygiene_common import ROOT, GitError, annotate, changed_paths, git_succeeds, parse_labels

FROZEN_PREFIXES = ("contracts/", "graph/schema/")
FREEZE_TAG = "contracts-v1.0.0"
LABEL = "contract-change"
SHOWN = 10


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a pull request touches contracts/ or graph/schema/ after the "
        f"{FREEZE_TAG} tag exists and does not carry the {LABEL} label."
    )
    parser.add_argument("--base", default="origin/main", help="base ref (default origin/main)")
    parser.add_argument(
        "--labels", default="", help="pull request labels: a JSON array or a comma-separated list"
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    try:
        labels = parse_labels(args.labels)
        touched = [p for p in changed_paths(args.root, args.base) if p.startswith(FROZEN_PREFIXES)]
    except (GitError, ValueError) as exc:
        print(f"check_contract_paths: FAIL: {exc}")
        return 1

    if not touched:
        print("check_contract_paths: OK: no change under contracts/ or graph/schema/")
        return 0
    if not git_succeeds(args.root, "rev-parse", "-q", "--verify", f"refs/tags/{FREEZE_TAG}"):
        print(
            f"check_contract_paths: OK: {len(touched)} files under contracts/ or graph/schema/ "
            f"changed; the contracts are not frozen yet (no tag {FREEZE_TAG})"
        )
        return 0
    if LABEL in labels:
        print(f"check_contract_paths: OK: frozen contract paths changed with the {LABEL} label")
        return 0
    annotate(
        "error",
        f"check_contract_paths: FAIL: this pull request changes frozen contract paths after the "
        f"{FREEZE_TAG} tag without the {LABEL} label. A change needs an approved "
        f"contract-change issue (PHASE-1.md 5.0, /contract-change).",
    )
    for path in touched[:SHOWN]:
        print(f"  {path}")
    if len(touched) > SHOWN:
        print(f"  ... and {len(touched) - SHOWN} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
