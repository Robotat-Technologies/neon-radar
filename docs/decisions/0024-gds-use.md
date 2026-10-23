# 0024. GDS use for rings of new accounts

- **Status:** proposed
- **Date:** 2026-10-23
- **Deciders:** tech lead, project lead (both held by @robotat-com until the team joins, OD-6)

## Context

`fan_in_collection` 0.2.0 has two variants (PHASE-3.md 7.3.5). The `collector` variant looks at one account at a time and needs nothing beyond the candidate steps of ADR-0020. The `ring` variant looks for a connected group of recently opened accounts: the payments of the period between two accounts that were each opened at most `new_account_days` (90) before the payment, grouped into connected components; a component of `min_ring_accounts` (5) to `max_ring_accounts` (200) accounts that also meets the variant's other conditions is a finding. Finding the groups means computing connected components of a filtered payment graph, a step with no length limit.

The project plan said that Graph Data Science (GDS) "gives us community detection" (PHASE-3.md 0.5, decision 13). Four forces shape how far that goes:

- **Every detector query is bounded.** The project's Cypher rules allow bounded hops only (PHASE-1.md 5.2), and Cypher 5 has no connected-components operator, so a component of unknown size cannot be found by one bounded match.
- **Alerts must be the same on every run.** Component ids from GDS weakly connected components (WCC) are not stable between runs, although the partition is; Louvain varies above concurrency 1 and takes no seed (`detection-cypher-gds.md` 4.4).
- **Community Edition limits.** GDS Community runs every algorithm but caps concurrency at 4 cores; an in-memory graph lives until it is dropped or the database stops (`detection-cypher-gds.md` 4.1, 4.2).
- **The licence and the lock file.** GDS is GPLv3 in Neo4j's repository (OD-20), and the `graphdatascience` client needs `pyarrow` below 26 while Phase 2 pins `pyarrow` 26 for Splink in the same `uv.lock` (`detection-cypher-gds.md` 4.7, 4.8; PHASE-3.md 3.1).

## Options considered

1. **GDS WCC on a Cypher projection, through the driver.** An exact partition with no tuning parameters, near-linear, within the Community concurrency cap, and explained in one sentence: these accounts are linked by payments in the window (`detection-cypher-gds.md` 4.9). Drawbacks: it needs the GDS jar in the database, and the projection is state that must always be dropped.
2. **GDS Louvain or Leiden communities.** They split large groups, but Louvain's result depends on the run above concurrency 1 and Leiden needs randomness parameters, so an alert could change between two runs of the same data; their groups are also harder to explain (`detection-cypher-gds.md` 4.4, 4.9).
3. **Union-find in Python in the Neo4j source as well.** No plugin at all. The in-memory oracle (`MemSource`) already computes the components this way; the Neo4j source would then repeat the oracle's own algorithm instead of the database computing the partition that the parity tests compare with it (ADR-0020).
4. **The `graphdatascience` client.** Apache-2.0 and convenient, but it would break the lock file, and plain `CALL gds.*` covers everything the step needs (`detection-cypher-gds.md` 4.7).

## Decision

We will use GDS for the `ring` variant of `fan_in_collection` only, as option 1, through four committed query files that `Neo4jSource.recent_account_components` runs (PHASE-3.md 7.1.6):

1. `recent_account_edges.cypher` reads the window's payments between two accounts that are not cash ledgers and were each opened at most `new_account_days` before the payment: the rows the oracle also computes. With no rows, nothing is projected.
2. `recent_account_components_project.cypher` builds a Cypher aggregation projection (`gds.graph.project`, undirected, `readConcurrency: 4`, one relationship per paying and paid account pair with its payment count) named `nr-ring-` plus 32 random hex digits, unique per call. A native projection cannot filter by time, so it cannot select the window (`detection-cypher-gds.md` 4.2); the deprecated `gds.graph.project.cypher` is not used.
3. `recent_account_components_wcc.cypher` runs `gds.wcc.stream` with `concurrency: 4`, ordered by component and account id.
4. `recent_account_components_drop.cypher` drops the projection in a `finally` block, so a failed run leaves none behind.

Each component is named by its smallest account id, never by its GDS component id. GDS runs in `stream` mode only: no `write` or `mutate` procedure (they would add properties C2 does not define), no `graphdatascience` client and no `apoc.periodic.*` in detection (PHASE-3.md 2.6). `MemSource` computes the same components with union-find, and every ring test runs on both sources. Setting the typology parameter `ring` to `false` switches the variant off, and with it every GDS call.

**Licence position (PHASE-3.md 1.2).** We accept GDS Community Edition, which Neo4j's repository publishes under the GNU GPL version 3, as a plugin of the Neo4j server that users run themselves, called over Bolt and never shipped by NeonRadar. The Neo4j 5.26 Community image does not include GDS (OD-13), so `make plugins` downloads the jar pinned in `scripts/fetch_gds.sh` (2.13.4, with its SHA-256) once, on the user's own machine, into the gitignored `data/cache/neo4j-plugins/`, and Docker Compose and Testcontainers mount it into the database (`THIRD_PARTY_NOTICES.md`, OD-20). NeonRadar's Apache-2.0 code does not copy, link or ship GDS code; it sends Cypher text, its own work, to the server. GPLv3 attaches its conditions to conveying a covered work: "Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying", and a covered work in an aggregate "does not cause this License to apply to the other parts of the aggregate" (GPLv3 sections 0 and 5, `detection-cypher-gds.md` 4.8). This is the project's reading, not legal advice, and the deciders confirm it. If NeonRadar ever publishes an image, archive or appliance that contains Neo4j or GDS jars, the GPL terms apply to that distribution, and this decision is revisited first.

## Consequences

- The ring variant finds the same groups on every run and on both sources; the parity tests check the GDS step against the oracle's union-find.
- A database without GDS cannot run the ring step. Development and CI need `make plugins` once; `make up` and the test fixtures never download the jar, and stop when it is missing or its SHA-256 differs (OD-13).
- An in-memory graph stays until dropped or until the database stops (`detection-cypher-gds.md` 4.2). The drop runs in `finally`, and after the Neo4j test run `CALL gds.graph.list() YIELD graphName RETURN count(*)` returns 0 (PHASE-3.md M3.5c). A process killed between the projection and the drop can still leave one; its `nr-ring-` name makes it easy to find.
- `detect/tests/test_query_plans.py` exempts the three GDS files (project, stream, drop) from its read-only check, and only them (PHASE-3.md 7.1.6).
- The research note read the GDS 2.13 manual; the project pins the 2.13.4 jar (OD-13), on which the ring tests pass in Neo4j mode. A GDS version change goes through a reviewed pull request that changes `scripts/fetch_gds.sh` and runs those tests again.
- M3.10 completes this record; only the deciders set its status (OD-5).

## Sources

- `docs/build/PHASE-3.md` 0.5 (decision 13), 1.2 (GDS licence position), 2.6, 3.1, 7.1.6, 7.3.5, M3.5c and 9 (risk R12).
- `docs/research/2026-10-18-detection/detection-cypher-gds.md` section 4 (4.1 to 4.9: Community limits, projections, WCC, determinism, the driver, the client and the licence).
- `docs/decisions/0020-detector-design.md` (candidate steps and the oracle).
- `docs/build/operator-decisions.md` OD-13 (GDS as a pinned jar), OD-20 (licences of two dependencies), OD-25 (GDS as in ADR-0024).
- `THIRD_PARTY_NOTICES.md` (Neo4j Graph Data Science) and `docs/architecture/local-stack.md`.
