# contracts: neonradar_contracts

- Purpose: the four contracts as code: C1 record (`records`, `datasets`), C2 graph mapping
  (`graph`), C3 API models (`api`), C4 alert (`alert`, C4-alert.md), versions (`versions`),
  the canonical wording (`wording`: disclaimers and the lint) and generated files (`schemas`),
  plus `datasets.yaml`, JSON Schemas, the OpenAPI snapshot and golden examples (PHASE-1.md 5).
- Owner: tech lead and nr-maintainers (every change needs the tech lead).
- Depends on: nothing in the workspace; pydantic v2, pyyaml, babel, followthemoney 4.11+ (PyICU
  needs ICU headers). api, detect, graph and ingest use it.
- Commands: `uv run pytest contracts/tests`, `make contracts` (`neonradar contracts export`),
  `make contracts-check` (tests plus `neonradar contracts check`, the drift check),
  `uv run neonradar contracts validate-records <files> --strict` (C1-record.md).
- Traps:
  - Frozen at Gate 1 (tag `contracts-v1.0.0`): after that, only an approved
    contract-change issue (`/contract-change`); the guard hook blocks edits.
  - followthemoney 4.x: build records with `ValueEntity`, not `model.make_entity`.
  - Ids use letters, digits, dots and hyphens only (FtM drops `_` or `:`): use `make_id`.
  - A model change regenerates JSON Schemas and OpenAPI in the same pull request.
  - Field patterns run on pydantic's Rust regex and land in the JSON Schemas: anchor with
    `^...$` (no `\z`, `\Z` or named groups), which also rejects a trailing newline there.
  - wording/*.txt are verbatim from PHASE-1.md 7.1; changing one is a contract change
    (test_wording.py pins their hashes). `Alert` validation reads them and datasets.yaml
    from next to the package (editable install).
