# Contracts changelog

The four NeonRadar contracts and their versions (`neonradar_contracts.versions`). The tech lead tags `contracts-v<version>` when the contracts freeze (`docs/build/PHASE-1.md` 5.0); after that, every change needs an approved contract-change issue and an entry here.

## 1.0.0 (unreleased)

### C1: NeonRadar Record 1.0.0

- The record format: FollowTheMoney 4.11+ `ValueEntity` lines in `.ftm.jsonl` files with the closed `nr` extension, rules R1 to R10, and a sibling manifest per file ([C1-record.md](C1-record.md)).
- The dataset registry `contracts/datasets.yaml` (five datasets; prefix `nr` reserved). The data steward has not yet approved its licence fields (GC-17).
- Validator `neonradar_contracts.records`, the id helper `make_id`, and the command `neonradar contracts validate-records`; golden examples in `examples/c1/`.
- Issue codes `FORMAT` (record envelope) and `NR` (the `nr` object) next to R1 to R10.
- JSON Schemas `schemas/record-manifest.v1.json` and `schemas/record-nr.v1.json`, generated from `Manifest` and `NrExtension` (added in M1.7c), so `neonradar contracts check` catches drift in C1 as well. For that, the manifest's timestamp pattern ends in `$` instead of `\z`: the same behaviour in pydantic's Rust regex engine, where `$` matches only at the very end (a trailing newline still fails), and a valid ECMA-262 pattern in the JSON Schema.

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
- **Patterns:** Python `re` patterns end with `\Z`; pydantic field patterns end with `$`, which pydantic's engine matches only at the very end. Either way, a value with a trailing newline fails. In the exported JSON Schema, the manifest's fixed-length fields (`created_at` and `source.retrieved_at`, 20 characters; `files[].sha256`, 64) also carry `minLength` and `maxLength`, because the jsonschema package matches `pattern` with Python's `re`, where `$` also matches before a final newline (added after the M1.7c review, with the C4 tightenings below).
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

### C4: Alert 1.0.0

- The alert object: `neonradar_contracts.alert.Alert` with `compute_alert_id`, `query_sha256` and `default_priority` ([C4-alert.md](C4-alert.md)); JSON Schema `schemas/alert.v1.json`; the golden example `examples/c4/circular_flow.json`.
- `neonradar contracts export` (`make contracts`) writes the JSON Schemas; `neonradar contracts check`, part of `make contracts-check`, exports to a temporary folder and fails on any difference, including a stray file in `schemas/`.
- Canonical wording in `wording/`: `standing-v1.txt`, `synthetic-demo-v1.txt` and `real-data-v1.txt` (verbatim from `docs/build/PHASE-1.md` 7.1) and `forbidden-terms.txt` (the 7.1 patterns), read by `neonradar_contracts.wording` and by `scripts/check_wording.py`.
- The typology catalog shape (not frozen, but alerts refer to it): `neonradar_detect.catalog.TypologyFile`.

#### Changed from `docs/build/PHASE-1.md` 5.4 (tech lead sign-off at Gate 1)

- The example's origin holder is "Fenwhistle Holdings Ltd": the spec's example name matches a live UK company (OD-12). The new name had no result on the Companies House company or officer search on 21 October 2026.
- The golden example carries all four explanation steps (the spec shows one), a computed `alert_id`, and a `query_sha256` computed over the example's query text, which stays abbreviated with `...` as in the spec.

#### Clarifications of 5.4 (tech lead sign-off at Gate 1)

The spec's rules are kept; these say how the model reads them.

- **`alert_id`:** the hashed text is the compact JSON array `[typology, detector.version, sorted(edge_ids), sorted(node_ids)]` (`json.dumps(..., ensure_ascii=False, separators=(",", ":"))`, UTF-8), sorted by Unicode code point, rather than text joined with `|`: composite C2 edge ids contain `|`, and a joined text leaves the boundary between the edge and node lists unmarked. The model recomputes the id and rejects a mismatch.
- **`detector.query_sha256`:** the SHA-256 (64 lower-case hex) of `evidence.query.cypher` in UTF-8; the model recomputes it and rejects a mismatch.
- **`contract_version`:** the C4 version the alert was written under, `1.<minor>.<patch>`. A later 1.x model accepts every earlier 1.x value; a model rejects a version newer than itself; a major version needs detection to be re-run (the rule of the record contract's `nr.v`).
- **Ids:** `evidence.node_ids` and `subjects[].entity_id` have the C1 id form (R1 as changed by OD-11); `evidence.edge_ids` and step `edge_ids` are C2 relationship ids (the FtM interval id, `<entity id>|addr|<address id>` or `<entity id>|sanction|<sanction id>`), so a Neo4j `elementId()` fails. `node_ids` holds at least one id, neither list repeats an id, and `subjects` holds at least one subject.
- **Evidence edges:** both endpoints of every evidence edge are in `evidence.node_ids`. The model checks composite ids (`a|addr|b`, `a|sanction|b`); for plain interval ids the detector checks it (M1.9b). C2 builds composite ids from record ids, which equal node ids in Phase 1; when Phase 2 entity resolution gives nodes canonical ids, this check needs revisiting (open question for Gate 1).
- **Explanation:** steps are numbered 1, 2, 3, ... in order; each step's `edge_ids` are evidence edges; `typology_reference.slug` equals `typology`, `doc_path` lies under `docs/typologies/`, and `citations` holds at least one bibliography key (lowercase snake case with at least one underscore, 7.3).
- **Wording lint in the model:** the headline (1 to 140 characters; templates hold only metric placeholders, so it never contains source names), every `false_positive_notes` entry, the `typology` slug and every subject `role`, the last two with `_` read as a space (so `mule_account` fails). Summary and step texts hold source names, so the detection runner lints them with captions and account numbers masked (M1.9b); masking blanks a value only as a whole token, never inside a longer word.
- **`data_flags.datasets`:** the distinct dataset slugs of the evidence nodes and relationships, the subjects and the evidence-account holders; at least one, each in `datasets.yaml`.
- **Guardrail G1 consistency:** beyond "`synthetic_scenario` exactly when `involves_real_entities` is false", the model rejects `involves_real_entities: false` when `datasets` lists a non-synthetic dataset or a subject or evidence node id has the id prefix of a non-synthetic dataset (an id with no dataset prefix, such as a Phase 2 `nr-` id, proves nothing either way), and an alert in which every entity is synthetic must have `synthetic_activity: true`. Only a `synthetic_scenario` alert may say "synthetic scenario": in a `structural_pattern` alert the model rejects the phrase (`SYNTHETIC_PHRASE`, `\bsynthetic[\s_-]+scenario`, case-insensitive) in the headline, the summary and every step text, and `render_headline` refuses it too.
- **Formats:** `created_at` and `window` times are UTC `YYYY-MM-DDTHH:MM:SSZ` (real dates), `window.start` is not after `window.end`; `run_id` is `run-<yyyymmddThhmmss>-<4 hex>`; versions are `MAJOR.MINOR.PATCH`; `detector.name` is a dotted module path; `typology` and roles are lowercase snake case.
- **Metrics** are scalar: numbers, or strings that are codes such as a currency (no booleans, lists or objects). Detectors never put names in metrics. A typology with several findings per subject emits one alert per finding, so metrics stay scalar (for example `sanctions_exposure`, Phase 3: one alert per sanctioned owner).
- **Priority:** `default_priority()` implements the default rule; the model does not enforce it, because a typology may document its own.
- **Strictness:** every object is closed (unknown keys fail) and values are not coerced (`"0.79"` is not a number). The JSON Schema checks shapes and formats only; the rules above that compare fields need the model.
- **Runs and storage:** a re-run merges onto the same `:Alert` (the id does not depend on the run), which keeps the latest run's payload and `run_id`; the API (M1.9c) lists one run's alerts through `PRODUCED` from its `:DetectionRun`.
- **Typology files:** the file name is `<slug>.yaml`; `doc` is `docs/typologies/<slug with hyphens>.md`; placeholders are `{metric}` or `{metric:<format spec>}` (no positional, attribute, index or conversion fields); `headline_synthetic` starts with "Synthetic scenario" and `headline_structural` never says it (7.1); the templates, every `false_positives` entry, the slug and, once a detector exists, the name pass the wording lint; an `explainer_only` typology has `detector: null`; `metrics` does not repeat a name; a numeric parameter's `default` lies within `min` and `max`; `owner` and `approved_by` are GitHub handles, and `approved_by` is never `@TODO`.

#### Tightened after the M1.7c review, before the freeze (tech lead sign-off at Gate 1)

A late review of M1.7c found gaps; the contracts were not frozen yet, so the model was tightened. Each rule is in [C4-alert.md](C4-alert.md) and has a test in `contracts/tests/`.

- **Finite numbers:** every Alert model sets `allow_inf_nan=False`, and `evidence.query.parameters` is checked at any depth, because pydantic's JSON parser reads `NaN` and `Infinity` into a `JsonValue` regardless. Before, NaN or infinity in `metrics` or `evidence.query.parameters` passed and was written back as `null`.
- **`synthetic_activity` and evidence edges:** `data_flags.synthetic_activity` must be false when an evidence edge id has the id prefix of a non-synthetic dataset; for a composite id (`a|addr|b`, `a|sanction|b`) either end counts, and a prefix of no dataset (`nr`) proves nothing. This enforces the 5.4 definition ("true if every evidence relationship is synthetic"), which the model did not check before.
- **Distinct subjects:** `subjects` never repeats an `entity_id`, because C2 `FLAGS` carries one `role` per alert and entity.
- **Wording lint:** `find_forbidden` NFKC-normalises the text and the masked values before matching, so fullwidth or mathematical letters (a fullwidth "m" in "mule") no longer hide a term; `scripts/check_wording.py` normalises the same way. The forbidden patterns themselves are unchanged.
- **Fixed lengths in the JSON Schema:** `alert_id` and `run_id` (24 characters), `created_at` and the `window` times (20) and `detector.query_sha256` (64) carry `minLength` and `maxLength`, so the exported `alert.v1.json` also rejects a trailing newline under Python's jsonschema package (whose `pattern` check lets `$` match before a final newline). The model already rejected it. The C1 manifest's fixed-length fields got the same lengths (see C1, Patterns).
