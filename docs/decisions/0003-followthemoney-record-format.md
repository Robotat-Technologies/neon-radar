# 0003. FollowTheMoney as the record format

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead)

## Context

NeonRadar loads several public sources (Companies House, GLEIF, ICIJ Offshore Leaks, a sanctions source) and its own synthetic generator into one Neo4j graph. The loaders, the graph loader and the synthetic generator are built by different squads at the same time, so they need one agreed record format between them, frozen at Gate 1 (`docs/build/PHASE-1.md` 4.1 and 5.1). The format has to:

- model the facts the project works with: companies and people, ownership with share bands, control without ownership, directorships, representation, family and associate links, positions, sanctions, bank accounts and payments;
- keep provenance (which dataset a record came from) on every record;
- keep loaders independent from Neo4j, so a squad can build and test a loader against files and a validator alone;
- be readable by existing open tools.

FollowTheMoney (FtM) is the data model of OpenSanctions and of FtM tooling. Version 4.11.0 (3 September 2026, MIT) has schemata for every fact above, including `Control` (new in 4.11.0), `Ownership` with `percentage`, `Payment` with `payerAccount` and `beneficiaryAccount`, and `BankAccount` (`docs/research/2026-10-16/sources-opensanctions-ftm-icij.md` B.1, B.4 and B.5). Its 4.x API changed in 2025: `ValueEntity` is the recommended class and carries `datasets`, while `model.make_entity()` output has none (B.1, B.3).

## Options considered

1. **FtM 4.x records plus a small closed `nr` extension.** The format already covers ownership, control, directorships, payments and accounts; OpenSanctions data and FtM tools (for example `ftm export-cypher`) work on the files; the validator can reuse FtM's schema model. Drawbacks: FtM depends on PyICU, which has no wheels and needs ICU headers on every machine and in CI (`docs/research/2026-10-16/stack.md` 3.5); the 4.x API has traps that AI-written code falls into (`PHASE-1.md` 3.2); a few facts need an extension: payment channel, account kind, address roles, parsed share bands, nominee flags, GLEIF consolidation. FtM also pulls in `python-stdnum` (LGPL-2.1+, through `rigour`) and `orjson` (MPL-2.0 AND (Apache-2.0 OR MIT)): not GPL, but the tech lead should know them.
2. **Our own pydantic record model.** Full control and no ICU, but every source mapping and every relationship type is designed from scratch, and no existing tool reads the files.
3. **Loaders write straight to Neo4j (or to `neo4j-admin` CSV).** Fastest for one source, but every loader then depends on the graph schema and on a running database, and squads cannot work in parallel against a frozen file contract.

## Decision

We will use FtM 4.11 or later as the record format (C1): one `ValueEntity.to_dict()` line per entity in `.ftm.jsonl` files, each file with a sibling manifest, plus the closed `nr` extension for the gaps above. `neonradar_contracts.records` validates records (rules R1 to R10) and `contracts/datasets.yaml` holds each dataset's id prefix and licence terms. Ids are restricted to FtM's entity reference format, so every valid id can be referenced (`contracts/CHANGELOG.md` 1.0.0).

## Consequences

- Loaders depend only on the contract and a validator; the graph loader is the only code that knows Neo4j.
- Every developer machine, the devcontainer and CI need ICU headers for PyICU (`neonradar doctor` checks it; CI installs `libicu-dev`).
- Loader code must use `ValueEntity`, not `model.make_entity`, and write payment timestamps in UTC without an offset; `CLAUDE.md` and `contracts/C1-record.md` say so.
- Loaders build ids with one helper, `neonradar_contracts.records.make_id`, which maps characters outside FtM's id alphabet (such as `_` in Companies House officer ids) or hashes the source id, and they keep the original in `nr.source_ref`.
- The `nr` extension is closed, so labels cannot hide in it (R9); new keys are a contract change.
- Upgrading FtM within 4.x is a dependency change that the contract tests check; a 5.x upgrade needs a new ADR.

## Sources

- `docs/build/PHASE-1.md` sections 3.1, 3.2, 4.1 and 5.1.
- `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md`, part B (B.1 package and 4.x API, B.3 JSON shape, B.4 schemata, B.5 AML-relevant facts).
- `docs/research/2026-10-16/stack.md` 3.5 (PyICU build requirement).
- followthemoney 4.11.0 on PyPI (https://pypi.org/project/followthemoney/), source checked on 21 October 2026: `followthemoney/types/entity.py` (reference format), `followthemoney/schema.py` (`Schema.validate`).
- `contracts/C1-record.md`.
