"""The query files read only C2 labels, relationship types and properties, and a templated query
takes only the values its list allows (PHASE-3.md 7.1.2; .claude/rules/cypher.md).

Phase 1 checked its one query this way (`test_circular_flow.py::test_query_reads_only_c2_labels_
types_and_properties` and `::test_query_refuses_bounds_outside_the_allowed_range`, retired in M3.2,
phase-3 reconciliation R2). The check is static, so it covers every query file a later milestone
adds. The EXPLAIN test (`test_query_plans.py`) lets a label or property pass when the small test
world lacks it (statuses 01N50 to 01N52); this test does not.
"""

import re
from importlib import resources

import pytest

from neonradar_contracts import graph as c2
from neonradar_detect.neo4jsource import TEMPLATE_VALUES, query_text

NAMES = sorted(
    p.name.removesuffix(".cypher")
    for p in resources.files("neonradar_detect.queries").iterdir()
    if p.name.endswith(".cypher")
)
LABELS = {*c2.NODE_LABELS, *c2.FLAG_LABELS}
TYPES = {*c2.RELATIONSHIP_TYPES, *c2.SUPPORT_RELATIONSHIPS}
PROPERTIES = {
    *c2.COMMON_NODE_PROPERTIES,
    *c2.COMMON_RELATIONSHIP_PROPERTIES,
    *c2.ENTITY_RESOLUTION_PROPERTIES,
    *(p for props in c2.RESERVED_PROPERTIES.values() for p in props),
    *(p for props in c2.SUPPORT_NODES.values() for p in props),
    *(p for props in c2.SUPPORT_RELATIONSHIPS.values() for p in props),
    *(p for m in c2.NODE_MAPPINGS.values() for p in m.properties.values()),
    *(
        p
        for ms in c2.RELATIONSHIP_MAPPINGS.values()
        for m in ms
        for p in (*m.properties.values(), *m.defaults)
    ),
    *(p for m in c2.REFERENCE_MAPPINGS for p in (*m.properties.values(), *m.defaults)),
}

COMMENT = re.compile(r"//[^\n]*")
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
# a variable bound by a node or relationship pattern, as in (a:Account), (s)-[r]->(t), or by a
# list predicate or comprehension, as in all(r IN relationships(p) ...), [n IN nodes(p) | n.id]
BOUND = re.compile(r"[(\[]\s*([a-z_]\w*)\s*(?=[:)\]{]|\s+IN\b)")
# labels and types: (a:Entity:Account), [:PAID], [r:OWNS|CONTROLS], (n:A&!B), WHERE n:Organization
NAMED = re.compile(r"(?:[(\[]|\b[a-z_]\w*):(!?[A-Z]\w*(?:[:|&]!?[A-Z]\w*)*)")
ACCESS = re.compile(r"\b([a-z_]\w*)\.([a-z_]\w*)\b")
PROJECTED = re.compile(r"[{,]\s*\.([a-z_]\w*)")  # map projections: h {.id, .synthetic}
INLINE = re.compile(r"[(\[]\s*(?:[a-z_]\w*)?:[A-Za-z_:|&!]+\s*\{\s*([a-z_]\w*)\s*:")


def renders(name: str) -> list[str]:
    """The query as `Neo4jSource` sends it: every allowed value of its placeholder."""
    raw = resources.files("neonradar_detect.queries").joinpath(f"{name}.cypher")
    keys = set(PLACEHOLDER.findall(raw.read_text(encoding="utf-8")))
    if not keys:
        return [query_text(name)]
    [key] = keys
    return [query_text(name, **{key: value}) for value in sorted(TEMPLATE_VALUES[key])]


def outside_c2(text: str) -> list[str]:
    text = COMMENT.sub("", text)
    found = []
    for group in NAMED.findall(text):
        for name in re.split(r"[:|&]", group.replace("!", "")):
            if name not in LABELS | TYPES:
                found.append(f":{name}")
    bound = set(BOUND.findall(text))
    for variable, prop in ACCESS.findall(text):
        if variable in bound and prop not in PROPERTIES:
            found.append(f"{variable}.{prop}")
    for prop in PROJECTED.findall(text) + INLINE.findall(text):
        if prop not in PROPERTIES:
            found.append(f".{prop}")
    return found


def test_there_are_33_query_files() -> None:
    assert len(NAMES) == 33


@pytest.mark.parametrize("name", NAMES)
def test_a_query_reads_only_c2_labels_types_and_properties(name: str) -> None:
    for text in renders(name):
        assert outside_c2(text) == [], name


def test_the_check_sees_what_is_not_c2() -> None:
    text = (
        "MATCH (a:Account:Suspect)-[r:PAID|SENT]->(b:Account&!Front {risk: 1}) WHERE b:Shell"
        " RETURN a.id, r.fee, b {.id, .score} // a comment may say c.anything"
    )
    assert outside_c2(text) == [":Suspect", ":SENT", ":Front", ":Shell", "r.fee", ".score", ".risk"]
    # parameters and function namespaces are not graph properties
    assert outside_c2("UNWIND $rows AS f RETURN f.anything, duration.inSeconds(x, y)") == []


@pytest.mark.parametrize(
    ("name", "key", "value"),
    [
        ("ownership_paths", "max_hops", "9"),
        ("ownership_cycles", "max_hops", "0"),
        ("flagged_ids", "flag", "Synthetic"),
        ("hubs", "rel_type", "PAID"),
        ("ownership_paths", "max_hops", "2}]->(x) DETACH DELETE x //"),
    ],
)
def test_a_template_takes_only_its_listed_values(name: str, key: str, value: str) -> None:
    with pytest.raises(ValueError, match="may not be"):
        query_text(name, **{key: value})


def test_a_template_left_unfilled_is_refused() -> None:
    with pytest.raises(ValueError, match="unfilled placeholder"):
        query_text("ownership_paths")
