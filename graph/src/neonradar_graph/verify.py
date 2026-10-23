"""`neonradar graph verify`: the C2 graph invariants I1 to I14 as violation counts (PHASE-2.md
M2.11 deliverable 5).

Phase 1's I1 to I6 are in `queries/verify_base.cypher`, I7 to I14 in
`queries/verify_resolution.cypher`; each statement returns `violations` and sits under an
`// I<n>` comment, and an invariant with two statements adds them up. Counts only: no value
of a node is read back, so the command is safe on the real-data instance.
"""

from neo4j import READ_ACCESS, Driver

from neonradar_graph import cypher

FILES = ("verify_base.cypher", "verify_resolution.cypher")


def invariants() -> dict[str, list[str]]:
    """Each invariant's statements, in order I1 to I14."""
    found: dict[str, list[str]] = {}
    for name in FILES:
        for invariant, statement in cypher.named(name):
            found.setdefault(invariant, []).append(statement)
    return dict(sorted(found.items(), key=lambda item: int(item[0][1:])))


def verify(driver: Driver, database: str) -> dict[str, int]:
    """The number of violations of each invariant (0 everywhere on a sound graph). Read-only;
    the server's notices (a label or type the graph does not hold yet) are switched off."""
    counts: dict[str, int] = {}
    with driver.session(
        database=database, default_access_mode=READ_ACCESS, notifications_min_severity="OFF"
    ) as session:
        for invariant, statements in invariants().items():
            counts[invariant] = sum(
                int(session.run(statement).single(strict=True)["violations"])
                for statement in statements
            )
    return counts
