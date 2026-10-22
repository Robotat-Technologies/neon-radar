# 0020. Detector design: candidate steps, hop expansion and the oracle

- **Status:** proposed
- **Date:** 2026-10-23
- **Deciders:** detect mentor, tech lead (both held by @robotat-com until the team joins, OD-6)

## Context

Phase 3 adds fourteen detectors over one graph (PHASE-3.md 0.4, 7.3). Phase 1's single detector, `circular_flow` 0.1.0, was one Cypher query that matched whole cycles with an unanchored quantified path `(a)-[:PAID]->{2,6}(a)` and then filtered them (PHASE-1.md M1.9b). Five forces shape what replaces it:

- **Cypher 5 cannot prune on the previous hop.** Inside a quantified path pattern each iteration sees only its own variables, so a condition such as "each payment later than the one before" or "each amount close to the first" is checked only after every path has been enumerated; on a payment graph that is most of the work. The pruning form (`allReduce`) is Cypher 25 only, and Neo4j 5.26 has no path modes (`docs/research/2026-10-18-detection/detection-cypher-gds.md` 0 answer 1, 1.3, 3.2).
- **Index use happens only in the database, and stateful logic is awkward there.** Window seeks, label and id anchors and simple filters belong in Cypher; sliding windows, dwell times, sums of money, partial dates, peer statistics, effective shares, deduplication and scoring are simpler, exact and testable in Python (`detection-cypher-gds.md` 2.17).
- **Tests without a database.** Fourteen typologies with five to ten cases each must run in seconds in CI and on a laptop, and the same cases must also prove that the Cypher returns what the logic expects (PHASE-3.md 7.1.5, 7.4).
- **No alert may make a statement about a real entity from synthetic activity** (G12, R-REAL). On a real profile the overlay puts synthetic payments next to real organisations, so the rule must hold on every instance and for every detector, not inside each one (PHASE-3.md 7.1.4; `typology-detection-definitions.md` 16.5).
- **Every alert must be checkable** against the graph it came from: C4 1.0.0 already gives each alert an id computed from its evidence and an evidence query (contracts/C4-alert.md).

## Options considered

1. **One Cypher query per detector, as in Phase 1.** Short to write. Path typologies enumerate every path before filtering (the Phase 1 shape), every typology's logic lives in Cypher that only a database can test, and R-REAL would have to be repeated in each query.
2. **GDS algorithms for every detector.** Fast on large graphs, but GDS projections hold no C2 time order for path checks, a concurrency above 1 makes some algorithms non-deterministic, and GDS is GPLv3 in Neo4j's repository; it fits one narrow case, the components of a ring of new accounts (`detection-cypher-gds.md` 0 answer 4; ADR-0024).
3. **Candidate steps in bounded Cypher with the typology logic in Python, behind a `Source` interface with an in-memory oracle.** More code (a query file and a reference implementation per step), in exchange for pruning paths hop by hop, testing every detector without a database, and testing the Cypher with the same cases.

## Decision

We will take option 3.

1. **Candidate steps.** A detector reads the graph only through the `Source` protocol (`detect/src/neonradar_detect/source.py`). Each step is one query file in `queries/` (33 files, 40 statements): parameters only, `:Entity` named in id lookups, the `paid_ts` range seek for window steps, `ORDER BY` a C2 id before every `LIMIT`, and no write. `Neo4jSource` runs them as auto-commit queries, `session.run(neo4j.Query(text, timeout=600))`, so a memory-limit error is reported, not retried (`detection-cypher-gds.md` 0 answer 3). The typology logic (windows, sums, matching, scoring, deduplication) is plain Python over the typed rows of `rows.py`.
2. **One hop per query for payment paths.** `circular_flow` and `layering_chain` keep their partial paths in Python (`expand.py`) and ask `paid_hop` for the next hop of every path in one call, with the time, amount and currency conditions inside that query. Starts are expanded 10,000 at a time; at most `max_branching` next hops per path and `max_frontier` paths per level are kept, and whatever is cut is counted in the run summary.
3. **An oracle behind the same interface.** `MemSource` implements every step on an in-memory graph (`memgraph.py`) that `graphrows.py` builds from C1 records with its own reading of C2, independent of the loader's mapping. Every detector test runs on it, and with `NR_DETECT_SOURCE=neo4j` the same tests run again on a Neo4j test database loaded by the project's loader in strict mode (CI's `integration` job does both). A difference between the two is a defect in one of them, found by a test rather than shared by both. The memory engine is for synthetic data only: it does no entity resolution, so `neonradar detect run --engine memory` refuses a real profile and a resolving one.
4. **R-REAL in the runner.** `runner.run_detection` asks the source for the node and edge information of every finding, computes the C4 data flags (`policy.py`) and withholds, on every instance, a payment-based finding that involves a non-synthetic node and any finding that names a non-synthetic person as a subject or in its evidence; withheld findings are counted by typology and reason, never rendered or stored. Detectors never decide it.
5. **Checkable alerts.** `alerts.build` gives each alert C4's `compute_alert_id` over its evidence and the generic evidence query `queries/evidence.cypher` with the alert's ids; `detector.query_sha256` is that query's SHA-256, as C4 1.0.0 requires, and the SHA-256 of each detector's own query files goes into the run folder's `run.json` (phase-3 reconciliation A1). `neonradar detect verify-alert` runs the committed evidence query with each stored alert's ids and fails unless every evidence node and relationship exists. Detection loads replace the earlier results (C2 1.2.0 L19), and the store writes each alert's evidence ids so that invariant I17 can check them.
6. **Texts outside detectors.** A finding holds ids, metrics and the grouping of evidence into steps, never text; `wording.py` renders every headline, summary and step from the typology file and lints each one at run time, so no run emits text that names conduct (G5).

## Consequences

- Path detectors stop enumerating whole paths before filtering, and the work they do is bounded and reported (`starts`, `partial_paths`, `truncated` in the run summary).
- Detector tests run in about a second without Docker, and the same tests check the Cypher on Neo4j. The first Neo4j run of the 33 files (this milestone) passed: every detector test, the query-plan check (`EXPLAIN` on every file over a small generated world) and the Phase 1 fixture on the new detector.
- Every change to a query file needs the same change in `memsource.py` and a run of the tests in both modes (`.claude/rules/detect.md`).
- Detectors never read names (ADR-0023 decision 4): no row type carries a name, and only `node_info` returns the captions the wording needs after the policy has decided; `detect/tests/test_no_name_reads.py` checks it for every detector.
- R-REAL in one place means a detector milestone cannot weaken it, but it also means a finding is computed before it is withheld; on a real profile the run summary shows how many findings each rule withheld.
- Detection results are a function of the graph: a reload or a new run removes the earlier alerts unless `--keep-previous` keeps them for a comparison.
- Follow-up: M3.4 adds the real-profile path (the gate, `runs_dir`, counts-only output); M3.6 compares the two sources on a generated world (`test_world_parity.py`); M3.10 completes this record with what the remaining detectors built.

## Sources

- `docs/build/PHASE-3.md` 7.1 (detector design), 7.5 (alerts), M3.2; C2 1.2.0 L19 and I17 (`contracts/C2-graph-schema.md`); C4 1.0.0 (`contracts/C4-alert.md`).
- `docs/research/2026-10-18-detection/detection-cypher-gds.md` section 0 (answers 1 to 5), 1.3, 2.17 (the Cypher and Python split), 3.2 and 3.4.
- `docs/research/2026-10-18-detection/typology-detection-definitions.md` 16.5 (data protection by design).
- `docs/build/phase-3-reconciliation.md` A1, A2, R1, R2, D1 and section 9 (M3.2).
