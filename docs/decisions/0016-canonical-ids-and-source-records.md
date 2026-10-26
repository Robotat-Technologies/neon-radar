# 0016. Canonical ids and source records

- **Status:** proposed
- **Date:** 2026-10-23
- **Deciders:** @robotat-com (tech lead)

## Context

Entity resolution (M2.10) decides which records describe the same person, organisation or address, and writes the result as a run folder: `canonical.csv` maps every resolvable record to a canonical id, and `candidates.jsonl` lists the possible matches that the merge policy kept apart (`docs/build/PHASE-2.md` 7.1.6 and 7.1.8; [ADR-0015](0015-merge-policy-for-listed-and-leaked-records.md)). The graph must then show one node per entity, keep the evidence of which records it was built from, and stay explainable: an investigator who opens a merged node must be able to see its source records and how each one joined (PHASE-2.md M2.11, "Review focus").

Three forces shape the loader:

- **Phase 1 ids are already in use.** Phase 1's loader gives every node its record id, the API accepts "a canonical id or any id in `referents`" (PHASE-1.md C3), and detections, tests and Phase 3's overlay refer to record ids (`contracts/C2-graph-schema.md`, "Common properties"; PHASE-3.md L18).
- **Resolution is redone, not patched.** A new run can merge, split or re-anchor clusters. Splink's own clustering is connected components with no cannot-link rule, which is why the resolver has its own constrained union-find ([`docs/research/2026-10-18/er-splink.md`](../research/2026-10-18/er-splink.md), finding 4); every run gives a complete, byte-stable map, not a list of changes (PHASE-2.md 7.1.6).
- **Real data must stay apart.** Real graphs live only in the separate real-data instance, whose one database is named `realdata`, so a query sent to the wrong instance fails ([ADR-0018](0018-real-data-handling.md), "A separate real-data instance"; C2 rule L17).

## Options considered

1. **Every node gets a new canonical id** (for example `nr-<hash>`), single-record entities too. Uniform, but every Phase 1 id changes, the graph doubles its node count with a `:SourceRecord` for every record, and every link that names a record id breaks.
2. **Records stay nodes; resolution only adds links between them** (a `SAME_AS` per merged pair). No id changes, but every query that counts people or companies, follows ownership or detects patterns has to collapse clusters at read time, and flags of one record would sit on a node that is "the same as" another, which G8 forbids presenting as one entity.
3. **Single-record entities keep their record id; merged entities get `nr-<anchor record id>`, with one `:SourceRecord` per member** (chosen; PHASE-2.md 4.4 and M2.11 deliverable 8).

For updating the graph after a new run, two options:

- **Incremental re-resolution in the graph** (move edges and source records node by node as clusters change): small writes, but hard to explain, to test and to keep consistent with invariants I7 to I13.
- **Resolve, then load with a replacement** (chosen): a resolved load first removes what the run replaces, then writes the run's graph.

## Decision

We will build canonical entities as follows (C2 1.1.0, loader rules L8 to L17, implemented in `graph/src/neonradar_graph/`):

- **Ids.** An entity built from one record keeps the record's id, with `cluster_size` 1, `resolution` "identity" and `referents` `[id]`, so every Phase 1 id stays valid and the graph has no extra nodes. An entity merged from two or more records gets `nr-<anchor record id>`, the anchor being the member whose dataset comes first in the anchor priority of `contracts/datasets.yaml`, then the smallest record id (7.1.6); its properties follow the merge rules of 7.1.6 and its flags come from the union of its members' own topics (G8).
- **Source records.** Only members of merged entities get a `:SourceRecord` node (the record's dataset, schema, caption, names and own topics) and one `RESOLVED_TO` to their entity, carrying `method`, `rule`, `match_probability` and `features` from `canonical.csv` and the run's id, resolver version and start time. The graph package reads the run folder only; it never reads `pairs.parquet` or imports the resolver's libraries.
- **Relationships.** Every relationship end is re-pointed to the canonical id; a relationship whose two ends land on one node is dropped and counted. Relationship ids stay the record-built ids C2 defines; HAS_ADDRESS or SUBJECT_OF rows that land on the same two nodes become one, keeping the smallest id.
- **Possible matches.** One `POSSIBLY_SAME_AS` per line of `candidates.jsonl` (a possible match, not confirmed), between two `:LegalEntity` nodes only; it moves no topic, flag, name or other property between the nodes and carries only the run's evidence and the union of their datasets.
- **Resolve, then load.** A load with a resolution run replaces what the run replaces: on the real-data instance, every entity, sanction and source record (a full replacement on each resolved load); on the default instance, the synthetic nodes whose id or referents include a record id of the load. Both remove every alert and detection run, since detections are re-run after a load. `--no-replace` keeps them for additive loads.
- **Two instances.** Real data loads only into the real-data instance and synthetic data only into the default one; a load that mixes them is refused before any connection (L17).
- **Phase 3's overlay** references record ids; the loader finds a record id that was merged through its `:SourceRecord` (L13), so an overlay loads against a resolved graph without knowing the run.

## Consequences

- Phase 1 ids, tests and API links keep working; merged nodes are the only new ids, and the API resolves any id in `referents` to its entity (M2.12).
- A resolved load rewrites every node of its records on each run (the report counts the nodes it removed), so it costs a full write; a load without a run behaves as in Phase 1.
- An `nr-` id changes when a run picks another anchor (for example a source with a higher priority joins the cluster); links to merged entities should use a member's record id, which the API accepts.
- `graph verify` checks I1 to I14 after every load; invariants I7 to I13 hold only if loads go through the loader.
- Follow-up: M2.12 serves source records and possible matches through the API; Phase 3 adds the overlay mode (L18) on top of L13.

## Sources

- `docs/build/PHASE-2.md` 4.4 (canonical ids), 5.2 (C2 1.1.0 and loader rules L8 to L17), 7.1.6 (anchor and merge rules), 7.1.8 (run outputs), M2.11.
- `contracts/C2-graph-schema.md`, "Changes in 1.1.0".
- [`docs/research/2026-10-18/er-splink.md`](../research/2026-10-18/er-splink.md), finding 4 (Splink clustering has no cannot-link rule).
- [ADR-0015](0015-merge-policy-for-listed-and-leaked-records.md) (merge policy), [ADR-0018](0018-real-data-handling.md) (real-data handling).
- `docs/build/phase-2-reconciliation.md` 2.9 (the loader's decisions in M2.11).
