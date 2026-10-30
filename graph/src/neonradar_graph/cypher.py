"""The Cypher files in `queries/` (PHASE-2.md M2.11 deliverable 6, reconciliation A12).

A file holds one or more statements, each ending with `;` at the end of a line; `//` lines are
comments. A template names its placeholders in a `// lint-values:` header and writes them as
`{{name}}`: `statements()` fills them with labels and relationship types of the C2 mapping
table only (never with data), and refuses anything else. Values travel as parameters.
"""

import re
from functools import cache
from pathlib import Path

from neonradar_contracts.graph import FLAG_LABELS, NODE_LABELS, RELATIONSHIP_TYPES

QUERIES_DIR = Path(__file__).resolve().parent / "queries"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
NAME = re.compile(r"^[A-Za-z][A-Za-z_]*\Z")
ALLOWED = frozenset((*NODE_LABELS, *FLAG_LABELS, *RELATIONSHIP_TYPES))
COMMENT = re.compile(r"^\s*(//.*)?$")


@cache
def _text(name: str) -> str:
    return (QUERIES_DIR / name).read_text(encoding="utf-8")


def split(text: str) -> list[tuple[list[str], str]]:
    """Each statement with the comment lines just before it, without its final `;`."""
    out: list[tuple[list[str], str]] = []
    comments: list[str] = []
    lines: list[str] = []
    for line in text.splitlines():
        if not lines and COMMENT.match(line):
            comments = [*comments, line.strip()] if line.strip() else []
            continue
        lines.append(line)
        if line.rstrip().endswith(";"):
            out.append((comments, "\n".join(lines).rstrip().removesuffix(";")))
            comments, lines = [], []
    if any(line.strip() for line in lines):
        raise ValueError("a statement does not end with ';'")
    return out


def _fill(text: str, values: dict[str, str]) -> str:
    for value in values.values():
        if not NAME.fullmatch(value) or value not in ALLOWED:
            raise ValueError(f"{value!r} is not a label or relationship type of C2")

    def replace(match: re.Match[str]) -> str:
        if match[1] not in values:
            raise ValueError(f"no value for the placeholder {{{{{match[1]}}}}}")
        return values[match[1]]

    return PLACEHOLDER.sub(replace, text)


def statements(name: str, **values: str) -> list[str]:
    """The statements of `queries/<name>`, with the placeholders filled."""
    return [_fill(text, values) for _, text in split(_text(name))]


def query(name: str, **values: str) -> str:
    """The single statement of `queries/<name>`."""
    (text,) = statements(name, **values)
    return text


def named(name: str) -> list[tuple[str, str]]:
    """`(invariant, statement)` for a verify file: the first `I<n>` of the comment above each."""
    out = []
    for comments, text in split(_text(name)):
        found = [m[1] for line in comments if (m := re.match(r"//\s*(I\d+)\b", line))]
        if not found:
            raise ValueError(f"{name}: a statement without an // I<n> comment")
        out.append((found[-1], _fill(text, {})))
    return out
