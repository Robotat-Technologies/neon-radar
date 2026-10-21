# 0005. Synthetic data policy

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead and data steward)

## Context

NeonRadar shows typology patterns on a graph, but there is no open, labelled data of real payments, so the demo, the detectors and their tests run on generated data. The project's central idea is to attach generated accounts and payments to entities that already exist in the graph, such as companies from the Companies House register, and to plant patterns that detectors should find (`docs/build/PHASE-1.md` 0.5 rows 8 and 12, M1.8e). Four forces shape how we do that:

- **Guardrail G1** (`PHASE-1.md` 2.1): no real person or company is ever labelled suspicious. A planted pattern that ran through a real company's accounts would attach a generated allegation to a real name.
- **Reproducibility**: fixtures, tests and the Gate 1 check (GC-09) need the same bytes from the same seed, on every machine.
- **Names**: generated people and companies must not carry the names of real, prominent people, families or companies. Faker's `ar_SA` surname list holds real prominent families, and mimesis company lists are real listed companies (`docs/research/2026-10-16/synthetic-docs-mcp.md` part A, "Names in several scripts"). We confirmed the Faker finding with Faker 40.43.0: at least 7 of the 44 `ar_SA` surnames are well-known Gulf families (Al Saud, Bin Laden, Olayan, Kanoo, Juffali, Al Hokair, Bugshan), and the `ru_RU` surname list includes the surnames of two former Soviet and Russian leaders. A name check on 21 October 2026 also found that the person name in the C1 example of `PHASE-1.md` 5.1 matches a real Companies House officer (OD-12).
- **Labels** (C1 rule R9): ground truth must never reach the records or the graph, or detectors could learn it instead of the pattern.

## Options considered

1. **IBM AMLSim.** It ships typology-shaped patterns and labels. Drawbacks: unmaintained since February 2022; needs Java 8, a manually downloaded MASON jar and Python 3.8 or earlier (its networkx 1.11 pin fails to import on 3.12 and 3.13); it creates its own accounts and people and cannot attach to entities that already exist; it has no structuring below a threshold and no dormancy (`synthetic-docs-mcp.md` A1, A5).
2. **External benchmark datasets** (IBM AMLworld, SAML-D). Useful for benchmarking, but they cannot attach to our entities either, and their licences (CDLA-Sharing-1.0; CC BY-NC-SA 4.0) do not fit an Apache-2.0 repository (`synthetic-docs-mcp.md` A2, A3).
3. **Our own seeded Python generator** (`neonradar_ingest.synth`). It takes any entity list as input, records the seed, and is reviewable code. The cost is that we design and maintain it ourselves, and its realism is only as good as our design (`synthetic-docs-mcp.md` A5).

## Decision

We will write our own seeded generator and follow these rules.

1. **Generator.** `neonradar_ingest.synth` writes C1 records (dataset `nr_synthetic`, id prefix `syn`, `nr.synthetic: true`) with a manifest that records the seed and the versions of FollowTheMoney, Faker and numpy. One root seed spawns an independent numpy stream per component, and each generated name has its own stream per slot, so redrawing one name changes nothing else. Draws use only numpy calls that are bit-exact on every platform. The same seed gives byte-identical records and labels; only the manifest's `created_at` changes. A test regenerates the committed fixture and compares bytes, on the developer's machine and in Linux CI.
2. **Real entities get background activity only.** In synthetic-join mode, real registry entities receive only accounts and ordinary payments. Planted scenarios run only among new synthetic entities in the `syn` namespace. The join also follows these rules:
   - no accounts for real natural persons or for bare `LegalEntity` records (ICIJ officers are often natural persons);
   - real entities transact only with new synthetic counterparties, never with each other;
   - no refunds, loans or cycles touch an account held by a real entity;
   - the scenario cluster never transacts with a real entity.
   Any exception needs the ADR that G1 requires.
3. **Labels live outside the graph.** Ground truth goes to `labels/transactions.csv` and `labels/scenarios.csv` next to the records, each starting with `# synthetic: true`, and never into a record or its `nr` object (R9). The generator keeps the records free of anything that marks a scenario:
   - planted payments use the same channels, office-hours timestamps, purposes and amount ranges as background payments;
   - payment ids follow time order;
   - background payments that would close a cycle the circular-flow detector reports are removed, so the labels list every such cycle: the planted scenario and its benign look-alikes (a loan drawdown and repayment, a full refund).
4. **Names.**
   - Faker gives first names (`ar_SA`, `ru_RU`, `en_GB`) and surnames (`ru_RU`, `en_GB`), always with an explicit gender.
   - Arabic-script surnames and every name written in several scripts come from hand-curated lists of common, neutral names. Multi-script spellings are curated, never machine transliterations (R10).
   - Every name is checked against `ingest/src/neonradar_ingest/synth/denylist.txt`. It holds the seed list from `PHASE-1.md` 7.1 verbatim, then entries added by reviewers.
   - Company names are built from neutral word lists plus a legal form for each jurisdiction, never from mimesis.
   - In synthetic-join mode, a generated name equal to a name in the input records is rejected.
   - Before a regenerated fixture is committed, every company name and every Latin-script person name is checked against the public Companies House search (OD-12). A name with an exact match is drawn again; the redraw is recorded in the code by slot, never by the real name.
5. **External benchmarks stay optional.** AMLworld and SAML-D may be supported later as user downloads. They are never committed.

## Consequences

- The demo, the detector fixtures and the Gate 1 check run without any real data or network access, and anyone can regenerate them.
- Real registry data can be loaded next to the synthetic data without any real entity taking a scenario role. A pattern that touches a real entity can only be a structural observation in generated background activity, which C4 wording reports as `structural_pattern` with `synthetic_activity: true`.
- A Faker or numpy upgrade changes the fixture. The fixture test then fails, and the fixture has to be regenerated and its new names checked again (`make fixtures`, OD-12).
- Names can still match real people with common names, and Arabic- and Cyrillic-script names cannot be checked against Companies House. The denylist and human review of samples (the M1.8e review focus) stay necessary. The standing disclaimer already says that many people share the same or similar names.
- Realism is limited: one scenario type (`round_trip`) and a small set of background behaviours. Phase 3 adds the other typologies, a held-out evaluation seed and leakage checks (`synthetic-docs-mcp.md` A5, design practices).

## Sources

- `docs/build/PHASE-1.md` 0.5 (rows 8 and 12), 2.1 (G1, G2), 5.1 (C1 rules R6 to R10), 7.1 (denylist seed), M1.8e.
- `docs/build/operator-decisions.md` OD-12 (name checks against the Companies House search).
- `docs/research/2026-10-16/synthetic-docs-mcp.md` part A: A1 (AMLSim), A2 (AMLworld), A3 (SAML-D), A5 (recommendation, generator design, names in several scripts).
- `contracts/C1-record.md` (rules R1 to R10, `make_id`).
