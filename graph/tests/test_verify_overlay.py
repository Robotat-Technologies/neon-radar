"""The statements of graph/src/neonradar_graph/queries/verify_overlay.cypher (C2 1.2.0,
invariants I15 to I17), read as `graph verify` will run them (M3.4). No database: the
integration tests in test_invariants.py run them."""

from neonradar_graph.client import REPO_ROOT

VERIFY_OVERLAY = REPO_ROOT / "graph/src/neonradar_graph/queries/verify_overlay.cypher"
OVERLAY_INVARIANTS = ("I15", "I16", "I17")


def overlay_statements() -> dict[str, str]:
    """The statements by invariant: the `// I<n>:` comment that opens a block names the
    statement after it, which ends at the line ending with `;`."""
    statements: dict[str, str] = {}
    name, lines = "", list[str]()
    for line in VERIFY_OVERLAY.read_text(encoding="utf-8").splitlines():
        if line.startswith("//"):
            if not lines and line[3:].split(":")[0] in OVERLAY_INVARIANTS:
                name = line[3:].split(":")[0]
            continue
        lines.append(line)
        if line.rstrip().endswith(";"):
            statements[name] = "\n".join(lines).rstrip().removesuffix(";")
            name, lines = "", []
    return statements


OVERLAY = overlay_statements()


def test_verify_overlay_has_one_statement_per_invariant() -> None:
    assert list(OVERLAY) == list(OVERLAY_INVARIANTS)
    for statement in OVERLAY.values():
        assert ";" not in statement
        assert statement.splitlines()[-1].strip().endswith("AS violations")
