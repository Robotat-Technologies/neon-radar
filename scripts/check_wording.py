#!/usr/bin/env python3
"""Wording lint for entity-facing templates (docs/build/PHASE-1.md 7.1, guardrail G5).

Scans the `wording` fields of detect/typologies/*.yaml and the string literals in
detect/src/**/wording.py and graph/src/**/wording.py (the Phase 2 resolution and ownership
templates, PHASE-2.md 7.2) for the patterns in contracts/wording/forbidden-terms.txt (one
regular expression per line, case-insensitive, `#` starts a comment). Disclaimers and general
documentation are out of scope: they discuss money laundering as a subject. Until M1.7c
creates the terms file, the script exits 0 with a notice.

    python3 scripts/check_wording.py

Standard library only. Python files are read with `tokenize`, not `ast`, so that 3.14 syntax
in detect/src still reads on the runner's Python 3.12.
"""

import argparse
import io
import re
import sys
import tokenize
import unicodedata
from pathlib import Path

from hygiene_common import ROOT, annotate

TERMS_FILE = "contracts/wording/forbidden-terms.txt"
TYPOLOGY_GLOB = "detect/typologies/*.yaml"
WORDING_GLOBS = ("detect/src/**/wording.py", "graph/src/**/wording.py")
STATEMENT_START = {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING}
# Escape sequences in Python and YAML strings: in "\nLaundered" there is no word boundary before
# "L" until the escape is blanked out (with as many spaces, so line numbers stay right).
ESCAPES = re.compile(r"\\(?:[abfnrtv0]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4})")
TEXT_PARTS = {
    getattr(tokenize, name)
    for name in ("FSTRING_MIDDLE", "TSTRING_MIDDLE")
    if hasattr(tokenize, name)
}


def load_patterns(path: Path) -> list[re.Pattern[str]]:
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def wording_lines(text: str) -> list[tuple[int, str]]:
    """Lines of the top-level `wording:` field of a typology file, with line numbers."""
    lines: list[tuple[int, str]] = []
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            inside = line.startswith("wording:")
            if inside and line[len("wording:") :].strip():
                lines.append((number, line[len("wording:") :]))
            continue
        if inside:
            lines.append((number, line))
    return lines


def python_strings(text: str) -> list[tuple[int, str]]:
    """String literals used as values (docstrings and other bare string statements are not)."""
    strings: list[tuple[int, str]] = []
    previous = tokenize.ENCODING
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type in (tokenize.NL, tokenize.COMMENT):
            continue
        if (token.type == tokenize.STRING and previous not in STATEMENT_START) or (
            token.type in TEXT_PARTS
        ):
            strings.append((token.start[0], token.string))
        previous = token.type
    return strings


def find_terms(
    path: str, pieces: list[tuple[int, str]], patterns: list[re.Pattern[str]]
) -> list[str]:
    findings = []
    for number, piece in pieces:
        text = ESCAPES.sub(lambda escape: " " * len(escape.group(0)), piece)
        # As neonradar_contracts.wording.normalize: NFKC, then no format characters (Cf), so
        # neither a fullwidth "m" nor a soft hyphen or zero-width space can hide a term.
        text = unicodedata.normalize("NFKC", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Cf")
        for pattern in patterns:
            for match in pattern.finditer(text):
                line = number + text.count("\n", 0, match.start())
                findings.append(f"{path}:{line}: {match.group(0)!r} matches {pattern.pattern!r}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when an entity-facing wording template matches a forbidden term "
        f"from {TERMS_FILE} (PHASE-1.md 7.1)."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    terms = args.root / TERMS_FILE
    if not terms.exists():
        print(f"check_wording: notice: {TERMS_FILE} does not exist yet (M1.7c); nothing to check")
        return 0
    try:
        patterns = load_patterns(terms)
    except re.error as exc:
        print(f"check_wording: FAIL: {TERMS_FILE} has an invalid pattern: {exc}")
        return 1

    findings: list[str] = []
    typology_files = sorted(args.root.glob(TYPOLOGY_GLOB))
    wording_files = sorted(path for glob in WORDING_GLOBS for path in args.root.glob(glob))
    for path in typology_files:
        name = path.relative_to(args.root).as_posix()
        text = path.read_text(encoding="utf-8")
        findings.extend(find_terms(name, wording_lines(text), patterns))
    for path in wording_files:
        name = path.relative_to(args.root).as_posix()
        try:
            pieces = python_strings(path.read_text(encoding="utf-8"))
        except (tokenize.TokenError, SyntaxError) as exc:
            findings.append(f"{name}: cannot be tokenized ({exc})")
            continue
        findings.extend(find_terms(name, pieces, patterns))

    if not findings:
        print(
            f"check_wording: OK: {len(typology_files)} typology files and {len(wording_files)} "
            f"wording.py files pass {len(patterns)} patterns"
        )
        return 0
    annotate(
        "error",
        f"check_wording: FAIL: {len(findings)} entity-facing texts use forbidden wording; describe "
        "patterns, never accusations (PHASE-1.md 7.1)",
    )
    for finding in findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
