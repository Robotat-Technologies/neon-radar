# 0004. Graph schema v1

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead)

## Context

Every NeonRadar component past the loaders works on one Neo4j graph: the graph loader writes it, the detectors query it, the API and the copilot read it, and the explorer draws it. Squads build these parts in parallel from Phase 2 on, so the graph needs one agreed shape (contract C2), frozen at Gate 1 with the other contracts (`docs/build/PHASE-1.md` 4.1, 5.0 and 5.2). The shape has to:

- carry the facts of the C1 record format (FollowTheMoney 4.x plus the `nr` extension, [ADR-0003](0003-followthemoney-record-format.md)): legal entities, ownership with share bands, control, directorships, accounts, payments, addresses, positions and sanctions;
- let detectors find payment cycles and ownership chains quickly, with bounded traversals in the forward-compatible Cypher 5 subset;
- give every finding stable ids for its evidence, so an alert can be reproduced (C4);
- keep source facts apart from NeonRadar's findings, so the graph never presents a detection as a source fact (guardrails G1 and G5);
- prepare for entity resolution in Phase 2 without a rewrite;
- run on Neo4j 5.26 LTS Community ([ADR-0002](0002-neo4j-5-26-lts.md)), which offers property uniqueness constraints but no existence, type or key constraints (`docs/research/2026-10-16/neo4j.md` section 5).

## Options considered

1. **Labels that mirror the FtM hierarchy; payments as relationships between accounts; ownership and other interests as relationships; flags from source data; one node per record in Phase 1.** `MATCH (x:LegalEntity)` finds people and organisations alike; a payment cycle is a quantified relationship pattern `(a:Account)-[:PAID]->{2,6}(a)`; every relationship has the FtM record id as its `id`, which C4 evidence can cite. Drawbacks: payment details sit on relationships, so a payment cannot itself be linked to other nodes (a contract, a project) in v1; FtM schemata without a C2 mapping are not loaded.
2. **Payments and interests as nodes (reified edges), as FtM models them.** Every FtM entity becomes a node, so nothing is lost and anything can link to a payment. Cycle and chain queries need twice the hops, and quantified patterns and GDS projections become more complex and slower.
3. **A generic graph (`:Entity` nodes with a `schema` property, one `:LINK` type).** Simplest loader, but every query filters on properties instead of labels and types, indexes are less selective, and the schema stops documenting itself.
4. **Resolve entities before loading (one canonical node per real-world entity from day one).** Fewer duplicate nodes, but needs entity resolution in Phase 1 and hides which source said what, so merges cannot be explained or reversed.

## Decision

We will use option 1, as specified in `contracts/C2-graph-schema.md`:

- Nodes built from FtM things get `:Entity` plus labels that mirror the FtM hierarchy (`:Entity:LegalEntity:Organization:Company`); `BankAccount` becomes `:Account`; `Sanction` becomes a `:Sanction` node linked by `SUBJECT_OF`.
- Transactions are `PAID` relationships between accounts, with a UTC `DATETIME` `ts`, so cycle and flow queries are fast traversals and each payment has one `id` for evidence. Ownership becomes `OWNS`, `HOLDS_ACCOUNT` or `CONSOLIDATES`, and the other interests become typed relationships in FtM's edge direction.
- Flag labels (`:Synthetic`, `:Sanctioned`, `:PEP`, `:RCA`) come only from source data, never from detections; alerts are separate `:Alert` nodes linked with `FLAGS`.
- Phase 1 loads identity-first: one node per record, `referents = [id]`. Phase 2 resolves first and then merges, keeping `:SourceRecord` evidence and `RESOLVED_TO` relationships, so every merge stays explainable and reversible.
- The schema uses uniqueness constraints only (on `id` of every node key and relationship type, 22 in all) plus 7 indexes, because Community has no other constraint kinds; the mapping, the loader and the invariant tests enforce required properties.
- The mapping is data (`neonradar_contracts.graph`), so the loader, the detectors and the contract tests read one source; migrations are numbered files that are never edited once applied (`neonradar graph migrate`).

## Consequences

- Detectors and the API can rely on fixed labels, types and properties; any change after Gate 1 is a contract change with a new migration.
- Payment and ownership queries are short traversals; GDS projections over `PAID` and `OWNS` need no reification.
- Some C1 facts are not in the graph in v1 (for example payer and beneficiary on `PAID`, `Position.organization`, `BankAccount.bank`); the C2 document lists them, and Phase 2's `:SourceRecord` keeps full records.
- Records that C1 accepts but C2 cannot represent are skipped with a `MappingIssue`, and a strict load fails, so fixtures stay fully loadable.
- Required properties are not enforced by the database; the invariants I1 to I6 are tests that must keep running.
- Entity resolution in Phase 2 changes node ids from record ids to canonical ids, which `referents` and the API already allow for.

## Sources

- `docs/build/PHASE-1.md` sections 4.1, 4.4, 5.0, 5.2 and 7.6.
- `docs/research/2026-10-16/neo4j.md`, sections 4 (Cypher 5 versus 25, forward-compatible subset), 5 (constraints and indexes in Community: uniqueness only), 6 (bulk loading with `UNWIND` batches) and 9 (Testcontainers).
- `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md`, A.4 (topics vocabulary, PEP and RCA sub-topics) and part B (FtM schemata and edge schemata).
- `contracts/C1-record.md` and `contracts/C2-graph-schema.md`.
- Verified on 21 October 2026 with `neo4j:5.26.32-community`: the 29 statements of `0001_init.cypher` create 22 constraints, including the 16 relationship uniqueness constraints, and 7 indexes (`graph/tests/test_migrations.py`).
