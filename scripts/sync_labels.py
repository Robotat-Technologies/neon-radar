"""Create or update every label in .github/labels.yml with the gh command line.

Existing labels with the same name are updated (`--force`); other labels are left alone.

    uv run --no-project --with pyyaml python scripts/sync_labels.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = ROOT / ".github" / "labels.yml"


def load_labels() -> list[dict[str, str]]:
    labels = yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    for label in labels:
        if set(label) != {"name", "color", "description"}:
            raise SystemExit(f"error: label needs exactly name, color and description: {label!r}")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", str(label["color"])):
            raise SystemExit(f"error: colour must be six hex digits: {label!r}")
    return labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or update the labels in .github/labels.yml.")
    parser.add_argument("--dry-run", action="store_true", help="print the gh commands without running them")
    args = parser.parse_args(argv)

    labels = load_labels()
    failures = 0
    for label in labels:
        command = [
            "gh", "label", "create", str(label["name"]),
            "--color", str(label["color"]),
            "--description", str(label["description"]),
            "--force",
        ]
        if args.dry_run:
            print(shlex.join(command))
            continue
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"synced  {label['name']}")
        else:
            failures += 1
            print(f"FAILED  {label['name']}: {result.stderr.strip()}", file=sys.stderr)

    if not args.dry_run:
        print(f"{len(labels) - failures} of {len(labels)} labels synced.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
