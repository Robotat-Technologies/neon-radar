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

### C2: Graph schema 1.0.0

- The graph schema: node labels that mirror the FtM hierarchy, flag labels from source data, 19 relationship types, common properties, and the migration `graph/schema/migrations/0001_init.cypher` with 22 uniqueness constraints and 7 indexes ([C2-graph-schema.md](C2-graph-schema.md)).
- The mapping as data in `neonradar_contracts.graph`; `neonradar_graph.mapping` turns C1 records into loader rows, and `neonradar graph migrate` applies the migrations.

#### Changed from `docs/build/PHASE-1.md` 5.2 (tech lead sign-off at Gate 1)

- **Flags:** `:PEP` is set by `role.pep` and by any sub-topic `role.pep.*`, and `:RCA` by `role.rca` and `role.rca.*`; `:Sanctioned` only by the exact topic `sanction` (`sanction.linked`, `sanction.control` and `sanction.counter` do not mean the entity is sanctioned). The spec named only the three exact topics. Taken by the orchestrating session on the operator's standing instruction (OD-10).

#### Clarifications of 5.2 (tech lead sign-off at Gate 1)

The spec's tables are kept; these say how the mapping reads them.

- **Ownership:** `HOLDS_ACCOUNT` (asset is a `BankAccount` in the load) wins over `CONSOLIDATES` (`nr.consolidation` set), which wins over `OWNS`.
- **Values:** a STRING or FLOAT graph property takes the first value in FtM's stored value order; LIST properties keep every value; absent values are left out.
- **Person** gets exactly the three properties of its row; Organization and PublicBody get the Company properties.
- **`:Synthetic`** is also set on `:Sanction` nodes, so invariant I2 holds for every node that has `synthetic`.
- **`caption`** is the record's own caption, else FtM's caption, which falls back to the schema label, so it is never empty.
- **PAID** stores no payer or beneficiary; holders are found through `HOLDS_ACCOUNT`.
- **Skipped with a `MappingIssue`, failing a strict load:** an edge record with other than one source and one target value; an endpoint in the load without the required label; `addressEntity` on a record that is not a `LegalEntity`; a duplicate id.
- **Not mapped in v1:** the references `parent`, `riskSource`, `BankAccount.bank`, `Position.organization`, `Payment.payer`, `Payment.beneficiary`, `Payment.contract`, `Payment.project` and `proof`; on `HOLDS_ACCOUNT` and `CONSOLIDATES`, the Ownership's `percentage`, `ownershipType`, `nr.natures_of_control` and `nr.share_pct_*`; every other FtM property that `neonradar_contracts.graph` does not name; the record keys `last_change` and `referents`; and `nr.v`, `nr.source_ref` and `nr.synthetic_kind`.
- **Countries:** every country-typed value is stored as a lower-case code (FtM's country type normalises `GB` to `gb`), in `countries` and in `jurisdiction`, `country` and `nationalities`.
- **Relationship ids** are unique across all types and never equal a node id (derived ids contain `|`, outside the C1 id alphabet); they do not change after entity resolution.
- **Migration runner:** the checksum is taken after normalising line endings to LF; the runner also refuses a database that has a migration the folder lacks and a pending migration numbered below an applied one, and waits for new indexes (`db.awaitIndexes`) before recording a migration.

#### Open for Gate 1 sign-off (tech lead)

- **Single-valued identifiers.** `registration_number`, `lei` and `account_number` hold one value (the first, in FtM's stored order), so the range indexes can serve equality lookups; C3 `EntityDetail.identifiers` is `dict[str, list[str]]`. Either keep the graph single-valued and let the API list one value (Phase 2's `:SourceRecord` keeps all), or make them lists in C2 before the freeze.
- **`PAID.amount` is a FLOAT.** A double is exact to the cent only up to about 10^13 major units; detectors compare amounts after rounding to cents. A Phase 1 alternative would be an INTEGER in minor units.
- **`MIGRATIONS_DIR` lives in the source tree** (`graph/schema/migrations`, found relative to the package source). That works for the uv workspace's editable install; packaging the migrations as package data is open for M1.9e or later.
