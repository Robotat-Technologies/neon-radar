#!/usr/bin/env python3
"""Check that committed fixtures are synthetic (guardrail G2, docs/build/PHASE-1.md M1.6).

Over the files git tracks:
- every *.ftm.jsonl under data/fixtures/, contracts/examples/ or any tests/fixtures/ has ids
  starting `syn-`, datasets `["nr_synthetic"]` and `nr.synthetic: true` on every record,
  except under contracts/examples/c1/invalid/, whose files break one rule on purpose;
- every CSV file in those places starts with the line `# synthetic: true`, or, for files
  meant for Neo4j LOAD CSV, has `synthetic` as its first column with `true` on every row;
- nothing under data/ is tracked except data/fixtures/, README.md and .gitkeep files.

    python3 scripts/check_fixtures.py

Standard library only.
"""

import argparse
import csv
import io
import json
import sys
from pathlib import Path, PurePosixPath

from hygiene_common import ROOT, GitError, annotate, git

FIXTURE_PREFIXES = ("data/fixtures/", "contracts/examples/", "tests/fixtures/")
INVALID_EXAMPLES = "contracts/examples/c1/invalid/"
CSV_MARKER = "# synthetic: true"
DATA_FILES_ALLOWED = {"README.md", ".gitkeep"}
SHOWN = 30


def is_fixture_path(path: str) -> bool:
    return path.startswith(FIXTURE_PREFIXES) or "/tests/fixtures/" in path


def check_ftm(path: str, text: str) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{path}:{number}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(record, dict):
            errors.append(f"{where}: a record must be a JSON object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.startswith("syn-"):
            errors.append(f"{where}: id {record_id!r} does not start with 'syn-'")
        if record.get("datasets") != ["nr_synthetic"]:
            errors.append(f"{where}: datasets is {record.get('datasets')!r}, not ['nr_synthetic']")
        nr = record.get("nr")
        if not isinstance(nr, dict) or nr.get("synthetic") is not True:
            errors.append(f"{where}: nr.synthetic is not true")
    return errors


def check_csv(path: str, text: str) -> list[str]:
    first_line = text.splitlines()[0].strip() if text.strip() else ""
    if first_line == CSV_MARKER:
        return []
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    if not header or header[0].strip() != "synthetic":
        return [
            f"{path}: a CSV fixture starts with the line '{CSV_MARKER}' or, for LOAD CSV, has "
            "'synthetic' as its first column"
        ]
    errors: list[str] = []
    for row in reader:
        if row and row[0].strip() != "true":
            errors.append(f"{path}:{reader.line_num}: synthetic is {row[0]!r}, not 'true'")
    return errors


def check_tracked(root: Path, paths: list[str]) -> tuple[list[str], int, int]:
    """Return the errors and the numbers of .ftm.jsonl and CSV fixtures checked."""
    errors: list[str] = []
    ftm_files = csv_files = 0
    for path in paths:
        if path.startswith("data/") and not path.startswith("data/fixtures/"):
            if PurePosixPath(path).name not in DATA_FILES_ALLOWED:
                errors.append(
                    f"{path}: only data/fixtures/, README.md and .gitkeep files may be committed "
                    "under data/ (guardrail G2)"
                )
            continue
        if not is_fixture_path(path):
            continue
        is_ftm = path.endswith(".ftm.jsonl") and not path.startswith(INVALID_EXAMPLES)
        is_csv = path.lower().endswith(".csv")
        if not (is_ftm or is_csv):
            continue
        try:
            text = (root / path).read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            continue  # tracked but deleted in the working tree
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path}: cannot be read as UTF-8 ({exc})")
            continue
        if is_ftm:
            ftm_files += 1
            errors.extend(check_ftm(path, text))
        else:
            csv_files += 1
            errors.extend(check_csv(path, text))
    return errors, ftm_files, csv_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a committed fixture is not synthetic or when anything other than "
        "fixtures, README.md and .gitkeep is tracked under data/ (guardrail G2)."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    try:
        paths = [p for p in git(args.root, "ls-files", "-z").split("\0") if p]
    except GitError as exc:
        print(f"check_fixtures: FAIL: {exc}")
        return 1
    errors, ftm_files, csv_files = check_tracked(args.root, paths)
    if not errors:
        print(
            f"check_fixtures: OK: {ftm_files} .ftm.jsonl and {csv_files} CSV fixtures are "
            "synthetic; nothing else is tracked under data/"
        )
        return 0
    annotate(
        "error",
        f"check_fixtures: FAIL: {len(errors)} problems; committed fixtures must be synthetic "
        "(guardrail G2, .claude/rules/data-and-fixtures.md)",
    )
    for error in errors[:SHOWN]:
        print(f"  {error}")
    if len(errors) > SHOWN:
        print(f"  ... and {len(errors) - SHOWN} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
