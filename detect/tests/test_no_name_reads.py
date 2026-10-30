"""Detectors never read a name (ADR-0023 decision 4; phase-3 reconciliation D1).

The generator gives every scenario person an invented surname and background people realistic
ones, so a detector that read names could find scenarios by their spelling. Names reach an alert
only after the decision: the runner asks `Source.node_info` for captions, and `wording.render`
puts them into the text. These checks are static, so they cover every detector a later milestone
adds:

- no row type of `rows.py` (what candidate steps return) has a name field;
- no query file reads a name property, except `node_info.cypher`, which returns the caption the
  wording needs after the policy has decided;
- `MemSource` and `Neo4jSource` touch a name only in `node_info`;
- no detector module, `policy.py` or `expand.py` reads a name, or calls `node_info`.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import re
from importlib import resources
from pathlib import Path

import pytest

from neonradar_detect import expand, memsource, neo4jsource, policy, rows

# C2 name properties (caption, names and their search forms) and FtM's name properties
NAMES = (
    "caption",
    "names",
    "names_text",
    "names_latin",
    "names_latin_text",
    "name",
    "alias",
    "previousName",
    "abbreviation",
    "firstName",
    "lastName",
    "middleName",
    "fatherName",
    "weakAlias",
)
TOKEN = re.compile(rf"(?<![\w$])(?:{'|'.join(NAMES)})(?!\w)")
PACKAGE = Path(memsource.__file__).parent
# Wording sentences of verbatim detectors that use a name word as plain English, never as a
# property or key, by module (path within the package). Each phrase is removed exactly, and
# only from its own module, before the check; nothing else is exempt.
PROSE = {
    "detectors/sanctions_exposure.py": ("whom these records do not name",),  # UK_NOMINEE (M3.5e)
}
DETECTORS = sorted((PACKAGE / "detectors").glob("*.py"))


def _cypher(text: str) -> str:
    """The statement text without `//` comments."""
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _reads(tree: ast.AST, prose: tuple[str, ...] = ()) -> list[str]:
    """Name properties a piece of Python reads: attributes, subscripts, `get` keys, strings.

    `prose` holds the module's own exempt phrases (PROSE)."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in NAMES:
            found.append(f".{node.attr}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            for phrase in prose:
                text = text.replace(phrase, "")
            found += [m.group(0) for m in TOKEN.finditer(text)]
    return found


def test_no_row_type_has_a_name_field() -> None:
    for _, cls in inspect.getmembers(rows, dataclasses.is_dataclass):
        assert not {f.name for f in dataclasses.fields(cls)} & set(NAMES), cls.__name__


def test_no_query_file_reads_a_name_but_node_info_its_caption() -> None:
    files = [
        p
        for p in resources.files("neonradar_detect.queries").iterdir()
        if p.name.endswith(".cypher")
    ]
    assert len(files) == 33
    for path in files:
        found = set(TOKEN.findall(_cypher(path.read_text(encoding="utf-8"))))
        allowed = {"caption"} if path.name == "node_info.cypher" else set()
        assert found <= allowed, (path.name, sorted(found))


@pytest.mark.parametrize("source", [memsource.MemSource, neo4jsource.Neo4jSource])
def test_sources_touch_names_only_in_node_info(source: type) -> None:
    for name, member in inspect.getmembers(source, inspect.isfunction):
        if name == "node_info":
            continue
        found = _reads(ast.parse(inspect.getsource(member).strip().replace("\n    ", "\n")))
        assert found == [], (source.__name__, name, found)


@pytest.mark.parametrize(
    "path",
    [Path(policy.__file__), Path(expand.__file__), *DETECTORS],
    ids=lambda p: p.name,
)
def test_detectors_and_the_policy_never_read_a_name(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):  # docstrings may say "name"; code may not
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            node.value.value = ""
    assert _reads(tree, PROSE.get(path.relative_to(PACKAGE).as_posix(), ())) == [], path.name
    calls = {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "node_info" not in calls, path.name


def test_the_check_sees_a_name_read() -> None:
    """The checks above would catch a detector that compared captions or spellings."""
    bad = ast.parse('info = source.node_info(ids)\nif info[x].caption.endswith("ov"):\n    pass\n')
    assert _reads(bad) == [".caption"]
    phrases = PROSE["detectors/sanctions_exposure.py"]
    prose = ast.parse('A = "held for, whom these records do not name."\nb = row["name"]\n')
    assert _reads(prose, phrases) == ["name"]
    assert _reads(ast.parse('c = "whom these records do not name: n.name"\n'), phrases) == ["name"]
    assert _reads(ast.parse('A = "whom these records do not name."\n')) == ["name"]
    assert set(PROSE) <= {p.relative_to(PACKAGE).as_posix() for p in DETECTORS}
    assert TOKEN.findall(_cypher("MATCH (p:Person) WHERE p.names_text CONTAINS $x RETURN p.id"))
    assert not TOKEN.findall(_cypher("RETURN g.graphName AS graph_name // the caption"))
