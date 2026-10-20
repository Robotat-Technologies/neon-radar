"""Create or update every label in .github/labels.yml with the gh command line.

Labels with the same name are updated (`--force`); labels not in the file are left alone.

    uv run --no-project --with pyyaml python scripts/sync_labels.py [--dry-run]
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = ROOT / ".github" / "labels.yml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or update the labels in .github/labels.yml.")
    parser.add_argument("--dry-run", action="store_true", help="print the gh commands without running them")
    args = parser.parse_args(argv)

    labels = yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    failures = 0
    for label in labels:
        name, color, description = (str(label[key]) for key in ("name", "color", "description"))
        command = ["gh", "label", "create", name, "--color", color, "--description", description, "--force"]
        if args.dry_run:
            print(shlex.join(command))
            continue
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures += 1
            print(f"FAILED  {name}: {result.stderr.strip()}", file=sys.stderr)
        else:
            print(f"synced  {name}")
    print(f"{len(labels) - failures} of {len(labels)} labels {'listed' if args.dry_run else 'synced'}.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
