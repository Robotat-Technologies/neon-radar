# contracts: neonradar_contracts

- Purpose: the four contracts as code: C1 record (`records`, `datasets`), C2 graph mapping
  (`graph`), C3 API models (`api`), C4 alert (`alert`), versions (`versions`), plus
  `datasets.yaml`, JSON Schemas, the OpenAPI snapshot and golden examples (PHASE-1.md 5).
- Owner: tech lead and nr-maintainers (every change needs the tech lead).
- Depends on: nothing in the workspace; pydantic v2, pyyaml, followthemoney 4.11+ (PyICU
  needs ICU headers). api, detect, graph and ingest use it.
- Commands: `uv run pytest contracts/tests`, `make contracts`, `make contracts-check`,
  `uv run neonradar contracts validate-records <files> --strict` (C1-record.md).
- Traps:
  - Frozen at Gate 1 (tag `contracts-v1.0.0`): after that, only an approved
    contract-change issue (`/contract-change`); the guard hook blocks edits.
  - followthemoney 4.x: build records with `ValueEntity`, not `model.make_entity`.
  - Ids use letters, digits, dots and hyphens only (FtM drops references with `_` or `:`).
  - A model change regenerates JSON Schemas and OpenAPI in the same pull request.
