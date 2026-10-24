# 0026. Read-only defence layers on Community Edition

- **Status:** proposed
- **Date:** 2026-10-24
- **Deciders:** @robotat-com (tech lead, graph mentor)

## Context

Phase 4 adds a copilot that answers questions by running Cypher over the graph, and API routes that read detection runs (`docs/build/PHASE-4.md` 7.5). Every one of these reads must stay a read: the API has no login and serves one person on this machine (ADR-0008), and nothing it runs may change the graph, read a file or reach the network.

Neo4j 5.26 Community Edition gives less help here than its documentation suggests:

- **There is no read-only user.** Community Edition has no roles: every user it knows is an administrator, so a read-only database account is not available (`docs/research/2026-10-19-copilot/api-readonly-cypher.md` 2.5) [neo4j_ops_manual_5].
- **READ access mode is a statement check, not a property of the transaction.** On a single server the query router refuses a write statement in a READ session (`Neo.ClientError.Statement.AccessMode`), but the transaction itself is not restricted; procedures marked READ run in READ mode whatever they do (research note 2.1 and 2.3).
- **Some READ procedures reach files and the web.** APOC's `apoc.load.*` and similar procedures are declared READ, and `LOAD CSV` reads local files and URLs (research note 2.3) [neo4j_cypher_load_csv_5].

So no single setting makes the API read-only. This decision records the layers that together do, what each one stops, and what none of them stops.

## Options considered

1. **Rely on READ access mode alone.** One line of code, but it is a statement check: it does not stop a READ procedure that reads a file or a URL, a runaway query, or a write that a future driver or server version lets through.
2. **Run a second, read-only replica or an Enterprise role.** Enterprise Edition has roles and fine-grained privileges; a replica would hold the data a second time. Both change the licence or the footprint of a local-first, Community-only tool (ADR-0007).
3. **Ten layers in the code and in the server's settings, each covering a gap of the others** (chosen).

## Decision

We will treat read-only as the sum of ten layers (PHASE-4.md 7.5.2), and keep all of them:

| # | Layer | Where | What it stops |
|---|---|---|---|
| 1 | No query text from input: every query is a committed file named by a port method (G13) | the copilot's `queries.py`, review | injected Cypher of any kind |
| 2 | Values only as parameters; the one rendered value, `max_hops`, comes from a fixed range | the query files, `neonradar_graph.ownership` | injection through a value |
| 3 | Names reach the full-text index only escaped (`queries.lucene`) | the copilot's `queries.py` | Lucene syntax in a name |
| 4 | Every query file is planned with `EXPLAIN` in CI: query type "r", no write operator, no `LOAD CSV`, no procedure but the full-text search | `test_queries_explain.py` (M4.4) | a write, a file or web read, or a procedure in a committed file |
| 5 | READ access mode | `neonradar_graph.readonly.run_read` | a write statement |
| 6 | An explicit transaction that is never committed | `run_read` | a write that passed layer 5 |
| 7 | The summary check: a query type other than "r", or any update or system update in the counters, raises `ReadRefused` | `run_read` | anything but a pure read, as the server reports it |
| 8 | A 5-second transaction timeout and `db.memory.transaction.max=1G` | `run_read`, `compose.yaml` and the test containers | runaway queries |
| 9 | Row caps and the evidence limits (500 nodes, 1,000 relationships) | `run_read`, the copilot's ports, `evidence.build` | huge answers |
| 10 | The procedure allowlist `apoc.version,apoc.meta.stats,apoc.coll.*,gds.*` | `compose.yaml` and the test containers | APOC's file, web and dynamic-Cypher procedures, which run in READ mode |

`run_read` is the only way new code reads Neo4j (`graph/src/neonradar_graph/readonly.py`, M4.1). It opens a READ session, an explicit transaction with a server-side timeout and the metadata `{"app": "neonradar", "query": <file name>}` (never a parameter or a question), fetches at most `max_rows + 1` rows so the caller learns whether the result was cut, consumes the summary, closes the transaction without committing, and only then checks the summary. Phase 1's health query (`CALL dbms.components()`, query type "s") and Phase 2's `ownership()` and `paths()` keep their own read paths over committed files.

The allowlist names every procedure Phases 1 to 4 call (`apoc.version()` and `apoc.meta.stats()` from the health and meta routes, the GDS procedures of Phase 3's detectors); a test of an earlier phase that fails under it names a procedure the list misses, which is a question for the tech lead, never a reason to widen the list silently. The settings are on both Neo4j services of `compose.yaml` (the default instance and the real-data instance) and on every Testcontainers database, so the integration tests run under them.

**What no layer stops, and why that is acceptable:**

- A person with the database password can write through Neo4j Browser or `cypher-shell`. Community has no roles; the API never exposes the password, and the default instance holds synthetic data only.
- A committed query file that reads the web with `LOAD CSV`, or a file placed in the server's import folder, would pass layers 5 to 7, because both are reads. Layer 4 and review stop it.
- Side effects of READ procedures. Built-in `db.*` READ procedures such as `db.resampleIndex` and `db.stats.collect` are registered with full access, so the allowlist cannot remove them (research note 2.3), and the `gds.*` procedures it keeps build in-memory projections, which Phase 3's detectors drop. No free Cypher exists to call them (layer 1), and no copilot query file calls a procedure other than the full-text search (layer 4).
- A model's text cannot reach any layer, because no model output is ever run as a query (G13).

## Consequences

- Every Phase 4 read pays for an explicit transaction and a summary check; the reads are small, so the cost is a round trip at most.
- A query file that writes, or a server that reports an update, fails loudly as a defect of the query file (a 500 problem), never as data.
- The allowlist must grow when a later phase calls a new procedure; the integration job shows it, because every test container runs under the same settings.
- The proofs are integration tests on Neo4j 5.26 Community: `graph/tests/test_readonly_integration.py` (a write in READ mode is rejected and leaves nothing; the summary check refuses a DBMS procedure; a client timeout ends a long query; APOC's file and web procedures are absent while `apoc.version()` and `gds.version()` answer; `LOAD CSV` of a path outside the import folder fails) and, from M4.4, `copilot/tests/test_queries_explain.py`. The unit tests (`graph/tests/test_readonly.py` on the fake driver of `graph/tests/fakeneo4j.py`, which keeps the real driver's order rules) fail if the helper commits, fetches after consuming the result, or returns rows before the summary is checked.
- If Neo4j adds a read-only role to Community Edition, or the project moves to an edition that has one, a read-only database user becomes an eleventh layer; none of these ten is removed for it.

## Sources

- `docs/build/PHASE-4.md` 7.5.1 (the read helper), 7.5.2 (the layers), 3.2 traps 2, 3, 28 and 29, and M4.1.
- `docs/research/2026-10-19-copilot/api-readonly-cypher.md` 2.1 to 2.5 and 6.1 to 6.4.
- Neo4j Operations Manual 5: configuration settings (the procedure allowlist, `db.memory.transaction.max`), securing extensions, transaction management [neo4j_ops_manual_5].
- Cypher Manual 5: LOAD CSV [neo4j_cypher_load_csv_5].
