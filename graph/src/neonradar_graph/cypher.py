"""The Cypher files in `queries/` (PHASE-2.md M2.11 deliverable 6, reconciliation A12).

A file holds one or more statements, each ending with `;` at the end of a line; `//` lines are
comments. A template names its placeholders in a `// lint-values:` header and writes them as
`{{name}}`: `statements()` fills them with labels and relationship types of the C2 mapping
table, or with a value the header lists for that placeholder (such as `max_hops=1,2,3`, M2.12),
never with data, and refuses anything else. Values travel as parameters.
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
LINT_VALUES = re.compile(r"^\s*//\s*lint-values:\s*(.+)$", re.MULTILINE)


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


def declared(name: str) -> dict[str, tuple[str, ...]]:
    """The values the `// lint-values:` header of `queries/<name>` lists, by placeholder."""
    found = LINT_VALUES.search(_text(name))
    pairs = (item.partition("=") for item in found[1].split()) if found else ()
    return {key: tuple(values.split(",")) for key, _, values in pairs}


def _fill(text: str, values: dict[str, str], listed: dict[str, tuple[str, ...]]) -> str:
    for key, value in values.items():
        if value in listed.get(key, ()):
            continue
        if not NAME.fullmatch(value) or value not in ALLOWED:
            raise ValueError(f"{value!r} is not a label or relationship type of C2")

    def replace(match: re.Match[str]) -> str:
        if match[1] not in values:
            raise ValueError(f"no value for the placeholder {{{{{match[1]}}}}}")
        return values[match[1]]

    return PLACEHOLDER.sub(replace, text)


def statements(name: str, **values: str) -> list[str]:
    """The statements of `queries/<name>`, with the placeholders filled."""
    listed = declared(name)
    return [_fill(text, values, listed) for _, text in split(_text(name))]


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
        out.append((found[-1], _fill(text, {}, {})))
    return out
