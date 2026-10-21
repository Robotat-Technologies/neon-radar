# Contracts changelog

The four NeonRadar contracts and their versions (`neonradar_contracts.versions`). The tech lead tags `contracts-v<version>` when the contracts freeze (`docs/build/PHASE-1.md` 5.0); after that, every change needs an approved contract-change issue and an entry here.

## 1.0.0 (unreleased)

### C1: NeonRadar Record 1.0.0

- The record format: FollowTheMoney 4.11+ `ValueEntity` lines in `.ftm.jsonl` files with the closed `nr` extension, rules R1 to R10, and a sibling manifest per file ([C1-record.md](C1-record.md)).
- The dataset registry `contracts/datasets.yaml` (five datasets; prefix `nr` reserved). The data steward has not yet approved its licence fields (GC-17).
- Validator `neonradar_contracts.records` and the command `neonradar contracts validate-records`; golden examples in `examples/c1/`.
- **Changed from `docs/build/PHASE-1.md` 5.1, R1:** the `rest` of an id is `[A-Za-z0-9.-]{0,99}[A-Za-z0-9]` instead of `[A-Za-z0-9._:-]{1,100}`, so every valid id matches FollowTheMoney's entity reference format and can be referenced. A tech lead contract decision taken by the orchestrating session on the operator's standing instruction (M1.7a); **needs explicit tech lead sign-off at Gate 1**. Loaders map source ids that contain `_` or `:` into the allowed alphabet.
- Issue codes `FORMAT` (record envelope) and `NR` (shape of the `nr` object) next to R1 to R10.
