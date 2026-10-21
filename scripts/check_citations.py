#!/usr/bin/env python3
"""Check that every citation key in the documentation exists in the bibliography.

Guardrail G4 and milestone M1.10a in docs/build/PHASE-1.md. In Markdown files, outside fenced
code blocks and inline code, every `[key]` that looks like a citation key must be a key of
docs/sources/bibliography.yaml; in detect/typologies/*.yaml, every `citations` entry must be one.
docs/research/ and docs/plan/ are skipped: they keep source material as delivered.

    uv run python scripts/check_citations.py docs/ detect/typologies/ README.md

Needs PyYAML, which the uv workspace provides (so not the standard-library-only hygiene job).
"""

import argparse
import re
import sys
from pathlib import Path

import yaml
from hygiene_common import ROOT, annotate

BIBLIOGRAPHY = "docs/sources/bibliography.yaml"
SKIPPED = ("docs/research/", "docs/plan/")
TYPOLOGY_DIR = "detect/typologies"
KEY = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+"
CITATION = re.compile(rf"\[({KEY})\](?![(\[])")
KEY_PATTERN = re.compile(rf"^{KEY}$")
# Any indentation, so that fences inside nested list items count too.
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`).+?(?<!`)\1(?!`)")
REQUIRED = ("key", "title", "publisher", "year", "url", "verified")


def load_keys(path: Path) -> tuple[set[str], list[str]]:
    """The bibliography's keys, and problems that would make a citation unreliable."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return set(), [f"{path}: cannot be read: {exc}"]
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return set(), [f"{path}: expected a mapping with an `entries` list"]
    keys: set[str] = set()
    problems: list[str] = []
    for number, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            problems.append(f"{path}: entry {number} is not a mapping")
            continue
        key = entry.get("key")
        missing = [field for field in REQUIRED if field not in entry]
        if missing:
            problems.append(f"{path}: entry {number} ({key!r}) lacks {', '.join(missing)}")
        if not isinstance(key, str) or not KEY_PATTERN.match(key):
            problems.append(f"{path}: entry {number}: {key!r} is not a citable key ({KEY})")
        elif key in keys:
            problems.append(f"{path}: duplicate key {key!r}")
        else:
            keys.add(key)
    return keys, problems


def markdown_citations(text: str) -> list[tuple[int, str]]:
    """(line, key) for each citation-like bracket outside fenced code and inline code."""
    found: list[tuple[int, str]] = []
    fence = ""
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence:
            closes = match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
            if closes and not match.group(2).strip():
                fence = ""
            continue
        if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            fence = match.group(1)
            continue
        for citation in CITATION.finditer(INLINE_CODE.sub(" ", line)):
            found.append((number, citation.group(1)))
    return found


def typology_citations(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(line, key) for each `citations` entry of a typology file, and (line, problem) pairs."""
    root = yaml.compose(text)
    if not isinstance(root, yaml.MappingNode):
        return [], []
    for key_node, value in root.value:
        if key_node.value != "citations":
            continue
        line = value.start_mark.line + 1
        if not isinstance(value, yaml.SequenceNode):
            return [], [(line, "`citations` must be a list of keys")]
        found, problems = [], []
        for item in value.value:
            if isinstance(item, yaml.ScalarNode) and isinstance(item.value, str):
                found.append((item.start_mark.line + 1, item.value))
            else:
                problems.append((item.start_mark.line + 1, "a citation must be a key"))
        return found, problems
    return [], []


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def files_under(paths: list[Path], root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    notices: list[str] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            notices.append(f"check_citations: notice: {relative(path, root)} does not exist")
    return files, notices


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when the docs cite a key that is not in docs/sources/bibliography.yaml."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="files or folders to check")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    keys, findings = load_keys(args.root / BIBLIOGRAPHY)
    files, notices = files_under(args.paths, args.root)
    for notice in notices:
        print(notice)
    checked = {"Markdown": 0, "typology": 0}
    cited: set[str] = set()
    for path in files:
        name = relative(path, args.root)
        if name.startswith(SKIPPED):
            continue
        if path.suffix == ".md":
            kind, problems = "Markdown", []
            citations = markdown_citations(path.read_text(encoding="utf-8"))
        elif path.suffix == ".yaml" and Path(name).parent.as_posix() == TYPOLOGY_DIR:
            kind = "typology"
            try:
                citations, problems = typology_citations(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                findings.append(f"{name}: cannot be parsed: {exc}")
                continue
        else:
            continue
        checked[kind] += 1
        findings.extend(f"{name}:{line}: {problem}" for line, problem in problems)
        for line, key in citations:
            cited.add(key)
            if keys and key not in keys:
                findings.append(f"{name}:{line}: unknown citation key {key!r}")

    if not findings:
        print(
            f"check_citations: OK: {checked['Markdown']} Markdown and {checked['typology']} "
            f"typology files cite {len(cited)} distinct keys, all in {BIBLIOGRAPHY} "
            f"({len(keys)} entries)"
        )
        return 0
    count = f"{len(findings)} problem" + ("" if len(findings) == 1 else "s")
    annotate(
        "error",
        f"check_citations: FAIL: {count}; cite only keys from {BIBLIOGRAPHY} "
        "(docs/sources/README.md)",
    )
    for finding in findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
