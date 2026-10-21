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
- **Patterns** end with `\Z`, so a value with a trailing newline fails.
- **Manifest:** `source.retrieved_at` is a UTC timestamp like `created_at`, and `dataset`, `licence.id` and `synthetic` must agree with `contracts/datasets.yaml`.
- **`nr.v`** is the contract's major and minor version: `"1.0"` for every 1.0.x release; a minor release adds its value and keeps accepting the older ones.

### C4: Alert 1.0.0

- The alert object: `neonradar_contracts.alert.Alert` with `compute_alert_id` and `default_priority` ([C4-alert.md](C4-alert.md)); JSON Schema `schemas/alert.v1.json`; the golden example `examples/c4/circular_flow.json`.
- `neonradar contracts export` (`make contracts`) writes the JSON Schemas; `neonradar contracts check`, part of `make contracts-check`, exports to a temporary folder and fails on any difference, including a stray file in `schemas/`.
- Canonical wording in `wording/`: `standing-v1.txt`, `synthetic-demo-v1.txt` and `real-data-v1.txt` (verbatim from `docs/build/PHASE-1.md` 7.1) and `forbidden-terms.txt` (the 7.1 patterns), read by `neonradar_contracts.wording` and by `scripts/check_wording.py`.
- The typology catalog shape (not frozen, but alerts refer to it): `neonradar_detect.catalog.TypologyFile`.

#### Changed from `docs/build/PHASE-1.md` 5.4 (tech lead sign-off at Gate 1)

- The example's origin holder is "Fenwhistle Holdings Ltd": the spec's example name matches a live UK company (OD-12). The new name had no result on the Companies House company or officer search on 21 October 2026.
- The golden example carries all four explanation steps (the spec shows one), a computed `alert_id`, and a `query_sha256` computed over the example's query text, which stays abbreviated with `...` as in the spec.

#### Clarifications of 5.4 (tech lead sign-off at Gate 1)

The spec's rules are kept; these say how the model reads them.

- **`alert_id`:** the hashed text is `"|".join([typology, detector.version, *sorted(edge_ids), *sorted(node_ids)])` in UTF-8, sorted by Unicode code point. The model recomputes the id and rejects a mismatch.
- **Ids:** `evidence.node_ids` and `subjects[].entity_id` have the C1 id form (R1 as changed by OD-11); `evidence.edge_ids` and step `edge_ids` are C2 relationship ids (the FtM interval id, `<entity id>|addr|<address id>` or `<entity id>|sanction|<sanction id>`), so a Neo4j `elementId()` fails. `node_ids` holds at least one id, neither list repeats an id, and `subjects` holds at least one subject.
- **Explanation:** steps are numbered 1, 2, 3, ... in order; each step's `edge_ids` are evidence edges; `typology_reference.slug` equals `typology`, `doc_path` lies under `docs/typologies/`, and `citations` holds at least one key.
- **Headline:** 1 to 140 characters, and the model runs the wording lint on it (templates hold only metric placeholders, so a headline never contains source names).
- **`data_flags.datasets`:** the distinct dataset slugs of the evidence nodes and relationships, the subjects and the evidence-account holders; at least one, each in `datasets.yaml`.
- **Guardrail G1 consistency:** beyond "`synthetic_scenario` exactly when `involves_real_entities` is false", the model rejects `involves_real_entities: false` when `datasets` lists a non-synthetic dataset or a subject or evidence node id has the id prefix of a non-synthetic dataset (an id with no dataset prefix, such as a Phase 2 `nr-` id, proves nothing either way), and an alert in which every entity is synthetic must have `synthetic_activity: true`.
- **Formats:** `created_at` and `window` times are UTC `YYYY-MM-DDTHH:MM:SSZ` (real dates), `window.start` is not after `window.end`; `run_id` is `run-<yyyymmddThhmmss>-<4 hex>`; versions are `MAJOR.MINOR.PATCH`; `detector.name` is a dotted module path; `query_sha256` is the SHA-256 (64 lower-case hex) of the detector's query text in UTF-8; `typology`, roles and citation keys are lowercase snake case.
- **Metrics** are numbers or strings (no booleans, lists or objects).
- **Priority:** `default_priority()` implements the default rule; the model does not enforce it, because a typology may document its own.
- **Strictness:** every object is closed (unknown keys fail) and values are not coerced (`"0.79"` is not a number).
- **Typology files:** the file name is `<slug>.yaml`; `doc` is `docs/typologies/<slug with hyphens>.md`; placeholders are `{metric}` or `{metric:<format spec>}` (no positional, attribute, index or conversion fields); `headline_structural` never says "synthetic scenario" (7.1); `metrics` does not repeat a name; a numeric parameter's `default` lies within `min` and `max`; `owner` and `approved_by` are GitHub handles.
