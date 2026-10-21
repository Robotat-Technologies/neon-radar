# Contracts changelog

The four NeonRadar contracts and their versions (`neonradar_contracts.versions`). The tech lead tags `contracts-v<version>` when the contracts freeze (`docs/build/PHASE-1.md` 5.0); after that, every change needs an approved contract-change issue and an entry here.

## 1.0.0 (unreleased)

### C1: NeonRadar Record 1.0.0

- The record format: FollowTheMoney 4.11+ `ValueEntity` lines in `.ftm.jsonl` files with the closed `nr` extension, rules R1 to R10, and a sibling manifest per file ([C1-record.md](C1-record.md)).
- The dataset registry `contracts/datasets.yaml` (five datasets; prefix `nr` reserved). The data steward has not yet approved its licence fields (GC-17).
- Validator `neonradar_contracts.records`, the id helper `make_id`, and the command `neonradar contracts validate-records`; golden examples in `examples/c1/`.
- Issue codes `FORMAT` (record envelope) and `NR` (the `nr` object) next to R1 to R10.

#### Changed from `docs/build/PHASE-1.md` 5.1 (tech lead sign-off at Gate 1)

- **R1:** the `rest` of an id is `[A-Za-z0-9.-]{0,99}[A-Za-z0-9]` instead of `[A-Za-z0-9._:-]{1,100}`, so every valid id matches FollowTheMoney's entity reference format and can be referenced. Taken by the orchestrating session on the operator's standing instruction (OD-10, OD-11). Loaders map source ids with `make_id`: `_` becomes `.`, and anything else outside the alphabet falls back to the first 20 hex characters of a SHA-1 of the source id, which stays in `nr.source_ref`.
- The first example company of 5.1, "Falcon Ridge Trading Ltd", is "Quillon Marsh Trading Ltd" in `examples/c1/`: a live UK company has a near-identical name (OD-12 name check, 21 October 2026).

#### Clarifications of 5.1 (tech lead sign-off at Gate 1)

The spec's rules are kept; these say how the validator reads them.

- **R3:** only the 21 v1 schemata are allowed, and a property name the schema does not define fails (FtM's validator skips it and `from_dict` drops it).
- **R4:** a value FtM cannot store as a reference fails R4 with the id-alphabet hint. Ids are unique within a load: a duplicate fails in every mode and never replaces the first record. In strict mode a reference must point to a record of its property's FtM range (`payer`, `beneficiary` and `owner` to a `LegalEntity`, `payerAccount` and `beneficiaryAccount` to a `BankAccount`, `addressEntity` to an `Address`, and so on); an `Ownership` asset may be an `Asset` or any `LegalEntity`, because C2 builds `OWNS` between legal entities.
- **R5:** also covers `first_seen`, `last_seen` and `last_change`, and every date-typed property. A Payment date with a trailing `Z`, an offset or a missing time fails.
- **R6:** only synthetic records may set `nr.synthetic`.
- **R7:** exactly one value each of `payer`, `beneficiary`, `payerAccount`, `beneficiaryAccount`, `amount`, `currency` and `date`; `currency` must be in Babel's ISO 4217 list (CLDR), not only three upper-case letters.
- **R9:** a name heuristic: a top-level key, `nr` key or property name containing `typolog`, `scenario`, `illicit`, `lookalike`, `ground truth` or `label` fails. Synthetic records may carry only the topics that set C2 flags (`sanction`, `role.pep`, `role.rca`), so no other topic can hint at a scenario.
- **NR:** the "Used on" column of the `nr` table is enforced (and `nr.synthetic_kind` only on synthetic records); `nr.address_roles` keys must be among the record's `addressEntity` values; `nr.share_pct_min` must not exceed `nr.share_pct_max`.
- **FORMAT:** the top-level keys are a closed set, so OpenSanctions' legacy `target` key is rejected; files must be UTF-8.
- **Patterns** end with `\Z`, so a value with a trailing newline fails.
- **Manifest:** `source.retrieved_at` is a UTC timestamp like `created_at`, and `dataset`, `licence.id` and `synthetic` must agree with `contracts/datasets.yaml`.
- **`nr.v`** is the contract's major and minor version: `"1.0"` for every 1.0.x release; a minor release adds its value and keeps accepting the older ones.
