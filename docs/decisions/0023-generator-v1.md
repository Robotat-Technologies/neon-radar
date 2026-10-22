# 0023. Generator v1 and its look-alikes

- **Status:** proposed
- **Date:** 2026-10-22
- **Deciders:** ingest mentor, data steward, a typology researcher (all held by @robotat-com until the team joins, OD-6)

## Context

Phase 3 needs payments to detect patterns in, and labelled scenarios to measure detectors against. Generator v0 (ADR-0005, PHASE-1.md M1.8e) planted one scenario in a small fixture. Phase 3 needs fourteen typologies, worlds of three sizes (an evaluation world, a demo and a scale world of 500,000 nodes), and the same synthetic activity next to real registry data on the real profiles (PHASE-3.md 0.4, 7.2). Four forces shape the design:

- **Guardrail G1.** No scenario may touch a real entity; real organisations may receive plain background activity only, and real people none (PHASE-3.md 2.1, decision 12).
- **Determinism.** The CI baseline (`eval/baselines/ci.json`, M3.6) pins exact detection counts on one seed, so the same code, seed and base must give the same bytes on every machine and in every process (PHASE-3.md 7.2.1).
- **Honest figures.** A detector that only meets illicit shapes cannot show its false positives, and a detector fitted to the generator's internals would measure the generator, not the typology (`docs/research/2026-10-18-detection/synthetic-transactions.md` 0, answers 3 and 6).
- **Labels outside the records** (C1 R9): ground truth may never reach a record or the graph.

## Options considered

1. **An external generator or dataset.** AMLSim is unmaintained since February 2022 and cannot run on Python 3.14; AMLworld and SAML-D are data only, under licences unsuitable for bundling; AMLGentex cannot be installed on Python 3.14 as pinned; none of them attaches activity to entities that already exist, and none labels participants with roles (`synthetic-transactions.md` 0 answer 1, 1.2).
2. **Extend generator v0.** Its streams are per component and slot, so adding a scenario moves later draws, and it writes labels v1 without participants or roles.
3. **A new generator beside v0** (generator v1): a world (a synthetic register) and an overlay engine that attaches to any base.

## Decision

We will build generator v1 beside generator v0, which stays for `demo-mini`.

1. **A world and an overlay for any base.** `world.generate` makes the register of a synthetic profile. `overlay.generate` takes any base (a world, a fixture, or later a real profile's records and resolution run) and adds accounts and ordinary activity for its eligible organisations, then plants scenarios and look-alikes among synthetic entities it creates itself. Real profiles need the same overlay, so one engine serves both (M3.4 adds real profiles).
2. **Named streams.** Every draw comes from a stream keyed by what it is for (`streams.stream(seed, *keys)`), so adding a scenario or an organisation leaves every other entity's activity unchanged. Names come from streams of their own through the `NameSource` interface, so a different name source changes names and nothing else; `test_names_never_move_a_structural_draw` checks it. NumPy is pinned to a minor version, and a bump goes through `neonradar eval check`.
3. **Plain background, look-alikes beside every typology.** Base organisations get a plain UK small-business profile in which no typology is planted, and never a payment to another base organisation. Ordinary activity can still form benign shapes that a detector reads as a pattern (a refund or a loan repayment closes a cycle; a cash business may bank takings just under a threshold), so on a real profile the real-data detection rule R-REAL (G12, ADR-0021) is the only control that keeps such findings off real organisations. Only untagged company records of a registry, or synthetic organisations, receive accounts. For each typology the overlay plants illicit scenarios and benign look-alikes of the same shape (a payroll bureau beside a funnel account, a loan beside a round trip), all among new synthetic entities with invented surnames. `ScenarioCtx` refuses any id a scenario did not create, and the bridge check (I15, I16) runs on the finished overlay before anything is written.
4. **Labels v2 outside the records.** `labels/` holds the Phase 1 files with new columns, plus `participants.csv`, `scenario_params.jsonl` and `manifest.json` with the SHA-256 of the record file; no record or id names a scenario, a typology, a role or a look-alike (`synthetic-transactions.md` 0 answer 4).
5. **Names.** The background's ordinary people (employees, counterparties' directors) and the world's ordinary people have realistic names drawn from Faker and Phase 1's curated lists through the denylist. Every person a scenario creates, illicit or look-alike, and every list, PEP and RCA persona with their relatives and associates carries an invented three-syllable surname with at least one closed syllable, filtered against the surnames of every installed Faker locale and the denylist, so no realistic full name is ever flagged or put in a scenario role. Company names come from neutral word lists, never contain a denylisted name and never spell "Cedar Gate Holdings" (OD-12). Word lists cannot rule out that a combination of ordinary words is a real company's name, so the data steward checks the names of `synth-demo` against a loaded register before the demo is published (M3.8).

## Consequences

- The CI gate can pin exact counts, because the same seed gives the same bytes; a change to the generator, NumPy or the name source shows up as moved counts or moved names, never silently.
- Precision is measured against look-alikes of every typology, and the report can say which kinds of ordinary activity a detector flags.
- The generator and the detectors are written and parameterised independently and never import each other, so detectors cannot read the labels (PHASE-3.md 4.1).
- Two models of the same idea now live in `neonradar_ingest.synth`: v0 for the committed `demo-mini` fixture and v1 for everything else. Retiring v0 would change `demo-mini` and every Phase 1 test that reads it.
- Validating every generated record with C1's validator is the slowest step of `synth overlay` (it runs in worker processes); worlds and overlays are never committed and are regenerated from their seeds.
- The invented surnames use the code book's syllable table until PHASE-2.md M2.9 adds `variants.py`; the name source should then draw from it.

## Sources

- `docs/build/PHASE-3.md` 0.5 (decisions 1, 7, 8 and 12), 2.1 (G1, G10, G11), 7.2 (the generator), 7.11 (profiles).
- `docs/research/2026-10-18-detection/synthetic-transactions.md` 0 (answers 1 to 6) and 1 (generators and labelled datasets in October 2026).
- ADR-0005 (synthetic data policy) and `docs/build/operator-decisions.md` OD-12.
