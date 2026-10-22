---
paths:
  - "ingest/src/neonradar_ingest/synth/**"
  - "ingest/profiles/synth-*.yaml"
---

# Generator rules (PHASE-3.md 2.1, 7.2)

- Scenarios and look-alikes work only through `ScenarioCtx`, which refuses any id the scenario
  did not create: no scenario ever touches a base entity (G1).
- The only record that may name a base entity is the account holding of an eligible base
  organisation, plus the payer or beneficiary field of a payment on that account (I15, I16).
  People from a base never get an account or a payment.
- Every random draw comes from a named stream (`streams.stream(seed, *keys)`); names draw from
  their own streams, so a different name source changes names only. Never iterate a set into
  an output; sort.
- Same seed, same base, same code: same bytes. `test_synth_v1.py` checks it; never relax it.
- Labels never enter records or the graph (C1 R9): no record names a scenario, a typology, a
  role or a look-alike, not even in an id.
- People on synthetic lists, PEP personas and their relatives and associates get invented
  surnames (`NameSource.invented_person`); never put a realistic full name on a synthetic list.
- A holdout seed (split `test`) is generated only by `neonradar eval run --split test`, which a
  human runs; never generate one, and never read `data/cache/holdout/` (G11).
- The generator never imports `neonradar_detect`, and the detectors never import the
  generator (PHASE-3.md 4.1).
- Payments are kept as their C1 lines (`Ctx.payments`); read one with `Ctx.record(id)`.
