"""Create or update every label in .github/labels.yml with the gh command line.

Labels with the same name are updated (`--force`); labels not in the file are left alone. Every
entry is checked before the first label is created, so an invalid file changes nothing.

    uv run --no-project --with pyyaml python scripts/sync_labels.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = ROOT / ".github" / "labels.yml"
KEYS = ("name", "color", "description")
COLOR = re.compile(r"^[0-9a-fA-F]{6}$")


def load_labels(path: Path = LABELS_FILE) -> list[dict[str, str]]:
    """Read and check the label file. Exit with a clear message if any entry is invalid."""
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    try:
        labels = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise SystemExit(f"error: cannot read {shown}: {error}") from None
    if not isinstance(labels, list) or not labels:
        raise SystemExit(f"error: {shown} must be a non-empty YAML list of labels")
    seen: set[str] = set()
    for number, label in enumerate(labels, start=1):
        where = f"error: {shown}, entry {number}"
        if not isinstance(label, dict) or set(label) != set(KEYS):
            raise SystemExit(f"{where}: needs exactly the keys {', '.join(KEYS)}: {label!r}")
        if not all(isinstance(label[key], str) and label[key].strip() for key in KEYS):
            raise SystemExit(f"{where}: name, color and description must be non-empty text")
        if not COLOR.match(label["color"]):
            raise SystemExit(f"{where}: color must be six hex digits, got {label['color']!r}")
        if label["name"] in seen:
            raise SystemExit(f"{where}: duplicate label name {label['name']!r}")
        seen.add(label["name"])
    return labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or update the labels in .github/labels.yml."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the gh commands without running them"
    )
    args = parser.parse_args(argv)

    labels = load_labels()
    if not args.dry_run and shutil.which("gh") is None:
        raise SystemExit(
            "error: gh is not on PATH; install it (https://cli.github.com/) and log in"
        )
    failures = 0
    for label in labels:
        name = label["name"]
        command = ["gh", "label", "create", name, "--color", label["color"]]
        command += ["--description", label["description"], "--force"]
        if args.dry_run:
            print(shlex.join(command))
            continue
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures += 1
            print(f"FAILED  {name}: {result.stderr.strip()}", file=sys.stderr)
        else:
            print(f"synced  {name}")
    done = "listed" if args.dry_run else "synced"
    print(f"{len(labels) - failures} of {len(labels)} labels {done}.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
