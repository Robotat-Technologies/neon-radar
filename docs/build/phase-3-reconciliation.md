# Phase 3 reconciliation

| | |
|---|---|
| File | `docs/build/phase-3-reconciliation.md` (PHASE-3.md M3.0 deliverable 1) |
| Reconciled against | `main` at `f4eec99` (22 October 2026, after M2.0 merged in #45), then brought up to `main` at `38714cd`, after #43 (M1.9e) and #46 (M1.12-2, the Phase 1 report) merged. #19 (M1.5, paused) and #47 (M2.2, open) were read but not relied on; M2.8 is in progress with no pull request yet |
| Written by | The M3.0 build agent; the tech lead owns it |
| Gate 1 | **Not passed** (operator decision OD-23: Phase 3 is seeded before Gate 1). No tag `contracts-v1.0.0` or `contracts-v1.1.0`. `docs/build/reports/phase-1.md` is on `main` (#46) |
| Method | Reading the code on `main` and the command line's `--help`. Then, in a scratch folder outside the repository, the whole code book extracted with `scripts/spec_extract.py extract --root <scratch>` and run against the repository's own packages, on synthetic data only: the code book's test kit, the committed `data/fixtures/demo-mini/` and the circular-flow fixture. Nothing from the scratch folder is committed |

PHASE-3.md and its code book were written on 18 and 19 October, before Gate 1, against a prototype that stood in for Phase 1 and Phase 2 code (code book, introduction). This file records, for every seam of PHASE-3.md 2.10 and every item of 0.6, what `main` has today and what the milestone that adapts it will do. Each Phase 3 milestone that adapts a seam checks it again and appends what it finds here (PHASE-3.md 2.2 step 2).

Classes: **M** mechanical: the adapting milestone adapts and, for a verbatim file, records a deviation (2.2 step 6b). **Q** behavioural: a question for the person named; the milestone in the row stops and asks (2.5) unless the question has been answered. **P** pending: depends on work that has not merged, written "pending #n" or "pending M2.x", with the Phase 3 milestone that checks it again. **D** decided in this pull request.

## 1. What Phase 3 needs from Phases 1 and 2 (PHASE-3.md 0.6)

### 1.1 Phase 1

| PHASE-3.md 0.6 expects | On `main` | Status |
|---|---|---|
| Tag `contracts-v1.0.0` | No tag on the remote | **Pending Gate 1** (the operator creates it, OD-5). M3.1 also needs `contracts-v1.1.0` (pending M2.1c) |
| The detection runner, `neonradar detect run` and `detect list`, the `circular_flow` detector with its fixture and integration test (M1.9b, #38) | `detect/src/neonradar_detect/runner.py`, `cli/src/neonradar_cli/detect.py`, `detectors/circular_flow.py` (version 0.1.0), `queries/circular_flow.cypher` (the unanchored template, converted to `// lint-values` by M2.0, phase-2 reconciliation A6), `detect/tests/fixtures/circular_flow/` and `detect/tests/test_circular_flow_neo4j.py` (integration) | Present; seams R1 to R6 |
| `TypologyFile` and `load_catalog()` in `catalog.py`, `render_headline` in `wording.py` (M1.7c) | Present (2.2 and 2.4 below) | Present; seams C1 to C4, R1 |
| `compute_alert_id` in `neonradar_contracts.alert` | `compute_alert_id(typology, detector_version, node_ids, edge_ids) -> str`; the code book's `alerts.build` calls it with these arguments in this order | Present and matching (A5) |
| The wording lint over `contracts/wording/forbidden-terms.txt` | `neonradar_contracts.wording.find_forbidden(text, mask=()) -> list[str]` over 23 patterns, and `scripts/check_wording.py` in CI | Present; seams W1 to W3 |
| The fifteen typology files (M1.10b) | 15 files in `detect/typologies/`, every one `version: 0.1.0`, `status: draft`, `approved_by: null`, owner `@robotat-com`; only `circular_flow` names a detector | Present. The code book replaces 14 of them; each differs from the repository's copy, so `spec_extract extract` keeps only the owner line (2.10). `trade_based_ml.yaml` stays |
| Generator v0 with its name modules and denylist (M1.8e) | `ingest/src/neonradar_ingest/synth/`: `names.py`, `companies.py`, `words.py`, `rng.py`, `namecheck.py`, `registry.py`, `activity.py`, `cycles.py`, `emit.py`, `demo.py`, `join.py`, `denylist.txt` (98 lines); the committed `data/fixtures/demo-mini/` | Present; seams N1 to N3 |
| The graph mapping and loader (M1.7b, M1.9a) | `neonradar_graph.mapping` and `neonradar_graph.loader` (2.1 and 2.7 below) | Present; seams G1 to G5 |
| `make demo-mini` and `make e2e` | Merged with #43 (M1.9e): `make demo-data` (migrate, wipe, load `demo-mini`, then `neonradar detect run` with no option), `make demo-mini` (the same in Docker, with the API and the UI), `make demo-dev`, and `make e2e` (Playwright; `ui/e2e/demo-mini.spec.ts` expects at least one alert whose headline starts "Synthetic scenario") | Present; seam L5 |

### 1.2 Phase 2

| Phase 2 milestone | Needed before | On `main` | Status |
|---|---|---|---|
| M2.0: the real-data guard hook, the Cypher linter, `neo4j-real` | M3.0 | Merged (#45) | Met |
| M2.1a: C1 1.1.0 (the exclusive share-bound flags, the `list` record kind) | M3.3 | Not started: waits for `contracts-v1.0.0`. `neonradar_contracts.versions` still gives 1.0.0 for every contract | **Pending M2.1a** |
| M2.2: profiles, the data layout, the project model, the real-data gate | M3.3 | In progress, no pull request | **Pending M2.2** |
| M2.1c and the tag `contracts-v1.1.0` | M3.1 | Not started | **Pending M2.1c and the tag** |
| M2.9: `variants.py` (invented surnames) | M3.3 (the name source) | Not started | **Pending M2.9** (N1) |
| M2.11: the resolution-aware loader (L13, L17) and `graph verify` | M3.4 | Not started | **Pending M2.11** |
| M2.13: `make load` | M3.7 | Not started | **Pending M2.13** |

## 2. The seams (PHASE-3.md 2.10)

### 2.1 Graph rows

**On `main`.** `neonradar_graph.mapping` (M1.7b) maps C1 records with `to_node_rows(records) -> MappingResult[NodeRow]` and `to_relationship_rows(records) -> MappingResult[RelationshipRow]`; a `NodeRow` keeps the flag labels (`:Synthetic`, `:Sanctioned`, `:PEP`, `:RCA`) in `flags`, apart from its schema labels. PHASE-2.md M2.11 makes it resolution-aware (pending M2.11). The code book's `graphrows.from_records` is the oracle's own reading and needs no adapter.

**Measured.** The oracle and the mapping on `demo-mini` (454 records): 110 nodes and 370 relationships on both sides, the same labels (flags included), relationship types and ends. On the circular-flow fixture (40 records): 14 nodes and 26 relationships on both sides.

| # | Difference | Class | Next step |
|---|---|---|---|
| G1 | The oracle writes `end_date: null`, and `is_nominee: false` on `OWNS` and `DIRECTOR_OF` (and `purpose: null` on `PAID`), where the record has none; the mapping leaves the property out. Neo4j stores no null, and `neo4jsource.py` reads the flags with `bool(...)`, so the detectors see the same values | M | None. M3.2's Neo4j mode confirms it |
| G2 | `OWNS.share_min_exclusive` and `share_max_exclusive` exist in the oracle only: C1 1.1.0 and C2 1.1.0 add them | P | Pending M2.1a and M2.1c; M3.2 checks again |
| G3 | The `caption` of a person whose record has names in two scripts: the oracle takes the first `name` value (`Павел Комаров`); the mapping follows C2's rule (FtM's representative value, preferring Latin script: `Pavel Komarov`). Four people of `demo-mini`. Captions reach the alert subjects and texts | M | C2 is the authority (OD-17), so the oracle departs from it. M3.2's Neo4j mode, or M3.6's world parity test, shows it wherever a record has names in two scripts; fix it as PHASE-3.md 7.1.5 says, by a recorded deviation in `graphrows.py`, never in a test |
| G4 | Flag labels: the oracle sets `:PEP` and `:RCA` for the exact topics `role.pep` and `role.rca` only; the mapping also for the sub-topics `role.pep.*` and `role.rca.*` (phase-2 reconciliation E2). The Phase 3 code writes only the exact topics | Q tech lead (with E2) | Decide with E2, before M2.11; the oracle and the loader must agree for the parity tests |
| G5 | `:Sanction.provisions` | P | Pending M3.1 (C2 1.2.0) |

### 2.2 Catalog

**On `main`.** `neonradar_detect.catalog` (M1.7c): `TypologyFile`, a strict, frozen pydantic model that forbids unknown keys, with the fields `slug`, `name`, `version`, `status`, `tier`, `owner`, `approved_by`, `summary`, `doc`, `citations`, `graph_pattern`, `parameters` (name to `Parameter`: `default` of `int | float | str | bool`, optional `min` and `max`), `metrics`, `wording` (`Wording`: `headline_structural`, `headline_synthetic`; or null), `false_positives`, `synthetic_support`, `generator_scenario` and `detector`. Functions: `load_typology(path)`, `load_catalog(directory=TYPOLOGY_DIR) -> dict[str, TypologyFile]`, `render_index(catalog)`, `placeholders(template) -> list[str]` (a plain `{name}` or `{name:<format spec>}`); `CatalogError`; constants `REPO_ROOT`, `TYPOLOGY_DIR`, `INDEX_PATH`. Callers outside `detect`: `api/src/neonradar_api/files.py` and `reference.py` (`TypologyFile`, `load_catalog`), `cli/src/neonradar_cli/detect.py`, `docs.py` (`render_index`) and `gate.py`. Tests: `detect/tests/test_detect_catalog.py` (24 tests), `api/tests/test_reference.py`.

**Measured.** Phase 1's `TypologyFile` on the 14 typology files of the code book refuses all 14: `shape_name` is an unknown key in every file, `wording.variants` in six (`dormant_reactivation`, `fan_in_collection`, `pep_exposure`, `recycled_directors`, `sanctions_exposure`, `shell_chain`) and `wording.detail` in one (`sanctions_exposure`); list defaults in three (`structuring.below_inclusive_currencies`, `mass_registration_address.exclude_postcodes`, and three `pep_exposure` parameters). 34 of the 47 templates use a filter (`{name|money}`, `{name|pct}`, `{name|n:noun}`) that Phase 1's `placeholders()` refuses. No template names a metric its file does not list, every synthetic headline starts with "Synthetic scenario", and no template uses a Python format spec. `trade_based_ml.yaml` loads.

| # | Difference | Class | Next step |
|---|---|---|---|
| C1 | `TypologyFile` needs `shape_name`, `wording.variants` and `wording.detail`; `Parameter` needs list defaults without bounds; `placeholders()` needs the filters | M | M3.2 deliverable 3 |
| C2 | Phase 1 accepts Python format specs (`test_detect_catalog.py::test_format_specs_are_allowed`: `{duration_hours:.0f}`), which the Phase 3 renderer does not substitute: its `PLACEHOLDER` leaves `{duration_hours:.0f}` in the text as written | Q tech lead (M3.2) | Either refuse format specs in typology files from M3.2 on (no Phase 3 file uses one), or keep them only on the Phase 1 headline path (R1). A template must never render with a placeholder left in it |
| C3 | The reference's `Typology.shape_name` falls back to `""`; PHASE-3.md M3.2 deliverable 3 makes it required when `detector` is set | M | M3.2 |
| C4 | The reference reads `CATALOG_DIR` (`detect/typologies` next to the package); Phase 1's `TYPOLOGY_DIR` is the same folder | M | None |

### 2.3 Wording lint

**On `main`.** `neonradar_contracts.wording.find_forbidden(text: str, mask: Iterable[str] = ()) -> list[str]` returns each match as `'<match>' (<pattern>)`. It normalises the text and the mask (NFKC, without format characters), and blanks each mask value only where it is a whole token. Also `find_forbidden_in_name`, `says_synthetic_scenario`, `normalize`, `forbidden_patterns`. The reference `violations(text, masked) -> list[str]` returns patterns and masks any substring, without normalising.

| # | Difference | Class | Next step |
|---|---|---|---|
| W1 | `violations` calls `find_forbidden(text, masked)` and returns the patterns, then applies `PHRASES` and `CONDUCT` to the normalised, masked text | M | M3.2 deliverable 4 |
| W2 | Phase 1 masks whole tokens only, the reference any substring, so Phase 1 is stricter where a caption sits inside a longer word. The verbatim tests mask whole captions (for example `test_alert_builder.py`'s "Test Mule Transport Ltd"), which both forms mask | M | M3.2 checks with the verbatim tests |
| W3 | `scripts/check_wording.py` (CI) lints the `wording:` field of every typology file and the string literals of `detect/src/**/wording.py`: it passes on the 15 typology files of Phase 3 and the verbatim `wording.py` (measured) | None | None |

### 2.4 Phase 1 detection code

**On `main`.**

- `runner.py`: `run(driver, database, *, typology=None, run_id=None, runs_dir=RUNS_DIR, catalog=None, clock=now_utc) -> RunReport`, `RunError`, `RunReport` (`as_json`, `node_properties`), `select`, `alert_row`, `store`, `new_run_id`, `now_utc`, the `DETECTORS` table, and the Cypher strings `MERGE_RUN`, `PRUNE_RUN`, `MERGE_ALERTS`.
- `alerts.py`: `Finding`, `EdgeFact`, `Step`, `entity_fact`, `build_alert`, `utc_text`, `AlertError`.
- `wording.py`: `render_headline(typology, wording_class, metrics)`, `format_metric`, `format_amount`, `format_day`, `format_duration`, `payment_step`, `cycle_summary`, `check_rendered`, `WordingError`, `MetricValue`.
- `detectors/circular_flow.py`: `NAME`, `VERSION = "0.1.0"`, `detect(driver, database, typology)`.

The code book replaces these four files whole, with other interfaces: `runner.run_detection(source, params, window, catalog, *, run_id, created_at, query_sha256=None, real_registry_alerts=True) -> RunResult`, `detectors(catalog)`, `params_sha256`, `ORDER`; `alerts.build(...) -> dict`, `EVIDENCE_QUERY`, `DATASET_NOTES`, `edge_ends`; `wording.render`, `render_template`, `templates`, `placeholders`, `Rendered`, `WordingError`; `circular_flow.SLUG`, `VERSION = "0.2.0"`, `QUERIES`, `Params`, `run(source, params, window)`.

Callers of the replaced names: `cli/src/neonradar_cli/detect.py` (`runner.run`, `runner.RunError`). Tests: `detect/tests/test_alerts.py` (11 tests), `test_runner.py` (8), `test_circular_flow.py` (11), `test_circular_flow_fixture.py` (5), `test_circular_flow_neo4j.py` (8, integration), `test_detect_wording.py` (`render_headline`, `format_metric`), `cli/tests/test_cli_detect.py` (5), and the helpers in `detect/tests/conftest.py` (`fixture_records`, `case_f_records`, `query_row`). The API imports none of the four files.

| # | Difference | Class | Next step |
|---|---|---|---|
| R1 | `render_headline` as a thin wrapper over `wording.render_template` (M3.2 deliverable 1) changes Phase 1's formatting (measured): integers lose their thousands separators (`1234567`, Phase 1 `1,234,567`); floats use `:g` (`120000.0` gives `120000`, `0.125` gives `0.125`, `1234567.0` gives `1.23457e+06`; Phase 1 `120,000`, `0.12`, `1,234,567`); booleans render as `yes` and `no` (Phase 1 refuses them); a format spec such as `{duration_hours:.0f}` stays in the text (Phase 1 renders `152`). Phase 1 tests that depend on it: `test_detect_wording.py::test_render_uses_the_placeholder_format_spec` and the rendering half of `::test_format_spec_on_a_string_metric_is_a_wording_error`. `::test_format_metric` (8 cases) and `::test_format_metric_refuses_odd_values` (3) test `format_metric`, which the verbatim `wording.py` does not have. `contracts/C4-alert.md` names `neonradar_detect.wording.render_headline` under "Code" | Q tech lead (M3.2; 2.5 item 5, as M3.2 deliverable 1 foresees) | Recommended: keep Phase 1's `render_headline` and `format_metric` with their Phase 1 behaviour, added to the verbatim `wording.py` as one recorded deviation, so the C4 document and Phase 1's tests stay true; no Phase 3 code calls them. Alternative: move them to another module and change the test imports, and the C4 document's "Code" line in M3.1's session |
| R2 | Phase 1's unit tests of the replaced internals (`test_alerts.py`, `test_circular_flow.py`, the run-logic part of `test_runner.py`, `test_cli_detect.py`) call functions the verbatim files remove (`build_alert`, `detect(driver, ...)`, `run`, `RunError`). They cannot pass, and 2.2 step 6 forbids deleting a test to make a check pass | Q tech lead (M3.2) | Recommended: M3.2 retires each of them in a commit of its own and lists, in the pull request, every retired test with the verbatim test that now covers its behaviour (`test_alert_builder.py`, `test_detector_circular_flow.py`, the new CLI tests) and any behaviour left uncovered. The tests of file writing and alert loading stay (M3.2 deliverable 1) |
| R3 | `queries/circular_flow.cypher` and its `// lint-values` header | M | Deleted in M3.2 (deliverable 1) |
| R4 | Phase 1's detector takes a driver; Phase 3's takes a `Source` | M | M3.2 |
| R5 | Case F is built by Phase 1's `detect/tests/conftest.py` (`case_f_records`) | M | M3.2 deliverable 6 moves it to the memory run |
| R6 | Phase 1's `run` checks the run id against `RUN_ID_PATTERN` with ASCII digits; the Phase 3 runner takes the id as given | M | The M3.2 CLI keeps the check |

### 2.5 Alert model

**On `main`.** `neonradar_contracts.alert.Alert` is C4 1.0.0: strict, frozen, unknown keys forbidden, no NaN or infinity. The types Phase 3 meets:

- `metrics: dict[str, int | float | str]`. Measured in Python and in JSON validation: integers, floats and strings pass; `true`, `false`, `null` and lists are refused. `contracts/schemas/alert.v1.json` gives the same three types. The C4 document: "numbers, and strings that are codes such as a currency"; "`1` is not `true`".
- `run_id`: `^run-[0-9]{8}T[0-9]{6}-[0-9a-f]{4}$`, 24 characters. `created_at` and the window times: `YYYY-MM-DDTHH:MM:SSZ`, 20 characters.
- `detector.query_sha256`: 64 lower-case hex, and the model checks that it is the SHA-256 of `evidence.query.cypher`.
- `evidence.window`: required and nullable: the key is always present, `null` when the finding has no time window.
- `data_flags.datasets`: each slug registered in `contracts/datasets.yaml` (five today: `gb_companies_house`, `gleif_lei`, `icij_offshore_leaks`, `opensanctions_default`, `nr_synthetic`).
- `pattern_strength` a float in [0, 1]; `headline` at most 140 characters; a step at most 280; `disclaimer_id` `standing-v1`; `contract_version` a 1.x not newer than the model.

**Measured.** The code book's 92 in-memory tests pass against the repository's `compute_alert_id` and wording patterns. Pushing every detector call in them through the code book's runner gave 85 distinct alerts for the 14 typologies. As the runner builds them, none of the 85 validates against `Alert`. With `detector.query_sha256` set to the SHA-256 of `evidence.query.cypher`, the 30 alerts of the eight payment typologies validate; the 55 alerts of the six registry typologies still fail (A2 to A4).

| # | Difference | Class | Next step |
|---|---|---|---|
| A1 | `detector.query_sha256`. The runner passes `(query_sha256 or {}).get(slug, "")`. M3.2 deliverable 5 makes it the SHA-256 of the module's `QUERIES` files, and the verbatim `test_detector_queries.py` says the same. C4 1.0.0 requires the SHA-256 of `evidence.query.cypher`, and every Phase 3 alert's evidence query is the generic `queries/evidence.cypher`. Either way every alert fails validation, and `detect run`, which validates every alert before writing (M3.2 deliverable 5), would always exit 1 | Q tech lead (M3.2) | Recommended: keep C4 1.0.0. `detect run` passes, for every typology, the SHA-256 of `evidence.cypher` (the alert's evidence query), and records the hash of each module's `QUERIES` files in `run.json` and in the `detectors` JSON of `:DetectionRun`. No verbatim file changes. Otherwise a C4 change |
| A2 | `evidence.window`. `alerts.build` writes the key only when the finding has a window; C4 requires the key, `null` when there is none. All 55 registry alerts fail (`mass_registration_address`, `shell_chain`, `sanctions_exposure`, `formation_agent_cluster`, `recycled_directors`, `pep_exposure`) | Q tech lead (M3.2, before M3.5b) | Recommended: one recorded mechanical deviation in `alerts.py` in M3.2 (`"window": null` when the finding has none); alert ids and texts do not change |
| A3 | Boolean metrics. C4 1.0.0 refuses them; PHASE-3.md 2.10 and 3.4 expect "numbers, strings or booleans". Booleans: `sanctions_exposure` (7: `bands_inconsistent`, `paths_capped`, `uk_control_to_assess`, `uk_measures_unknown`, `unbounded`, `us_control_caution`, `votes_follow_shares`), `pep_exposure` (2: `domestic`, `office_dates_unknown`), `mass_registration_address` (1: `po_box`). The verbatim tests check booleans on the findings (for example `metrics["unbounded"] is True`) | Q tech lead (M3.5b, M3.5e, M3.5f; 2.5 item 5) | Options: (a) C4 1.1.0, additive: a metric value may be a boolean. That needs a contract-change issue, and the JSON Schema, C3's OpenAPI snapshot and `versions.ALERT` change with it. (b) The alert builder writes booleans differently at the alert level only, which changes what the alerts and the typology files say. Recommended: (a), decided before M3.5b |
| A4 | `data_flags.datasets`: alerts about synthetic list entries name `gb_fcdo_sanctions`, `us_ofac_sdn` and `eu_fsf`, which `contracts/datasets.yaml` does not list yet | P | Pending M2.1a (the registry entries for the Phase 2 lists); M3.5e checks again |
| A5 | `compute_alert_id`: once A1 was set, the model recomputed every payment alert's id without a difference | None | None |

### 2.6 Names

**On `main`.** `names.py`: `PersonNames`, `PersonName`, `denylist()`, `is_denied(name)`, `fold(text)`, `strip_honorifics(name)`. `companies.py`: `CompanyNames`, `name_key(name)`, `street(rng)`. `rng.py`: `stream(seed, component)`, `slot_stream`, `pick`, `chance`, `between`. `namecheck.py`: `legal_entity_names`, `check_names`. Phase 2's `variants.py` does not exist yet. The Phase 3 `ctx.NameSource` protocol has five methods: `person`, `invented_person`, `company`, `street`, `town`.

| # | Difference | Class | Next step |
|---|---|---|---|
| N1 | `invented_person` needs Phase 2's invented surnames (`variants.py`) | P | Pending M2.9; M3.3 checks again |
| N2 | The reference `namesource.py`'s word lists hold "Cedar" (`WORDS_A`), "Gate" (`WORDS_B`) and "Holdings" (`WORDS_C`), and `company()` joins one of each with "Ltd": it can produce "Cedar Gate Holdings Ltd", the name OD-12 forbids | M | M3.3's adapter must not be able to produce it (its own word lists, or the denylist check); say so in its pull request |
| N3 | OD-12 asks for a Companies House search (company and officer) before a synthetic name is committed, with the query, date and result in the pull request. Since M2.0, `guard_real_data.py` blocks WebFetch and shell downloads of `find-and-update.company-information.service.gov.uk/search` (G9), so a build agent cannot run that search. Names the Phase 3 verbatim files commit: "Test Holding Ltd", "Test Holder Ltd", "Test Listed Ltd", "Test Offshore Ltd", "Test Mule Transport Ltd" (detect tests: M3.2, M3.5b, M3.5e), "Fixture Bank plc" (M3.5a), "Synthetic Card Acquiring Ltd" and "Synthetic Business Lending plc" (the generator's background, M3.3) | Q tech lead and data steward | Either the operator runs the OD-12 searches when those milestones open, or OD-12 is narrowed for names that start with "Test", "Fixture" or "Synthetic" (PHASE-2.md 2.9 already uses such test names) |

### 2.7 Test fixtures

**On `main`.** `graph/tests/support/nr_test_neo4j.py` is a pytest plugin that the root `conftest.py` registers (`pytest_plugins = ["nr_test_neo4j"]`). Fixtures: `neo4j` (one per session: a Testcontainers `neo4j:5.26.32-community` with APOC from the image and the GDS jar that `make plugins` pinned, copied in before it starts, OD-13; or the database at `NR_TEST_NEO4J_URI`), `empty_neo4j`, `graph_db` (migrated). Helpers `Neo4jTarget` and `pinned_gds()`. Its rule: never import the fixtures into a conftest, or a second database starts. The root `pyproject.toml` runs pytest with `--import-mode=importlib` and puts `scripts` and `graph/tests/support` on the path.

**The references.** `conftest.py` puts the tests folder on `sys.path`, defines `neo4j_source_factory` (one session container through `neo4j_mode.container()`) and the autouse switch for `NR_DETECT_SOURCE=neo4j`. `neo4j_mode.py` starts its own Testcontainers database with `NEO4J_PLUGINS`, writes records with M3.3's `neonradar_ingest.synth.writer` and loads them through the command line.

| # | Difference | Class | Next step |
|---|---|---|---|
| T1 | The reference starts a second container that downloads its plugins when it starts; the project shares one database per session with the pinned jar (OD-13) | M | M3.2: `neo4j_source_factory` builds on the shared `neo4j` (or `graph_db`) fixture and the project loader (`neonradar_graph.loader.load_records`), and starts no container of its own |
| T2 | Phase 1's `detect/tests/conftest.py` already holds helpers (`fixture_records`, `case_f_records`, `query_row`) | M | M3.2 merges the reference's additions into it (deliverable 7) |
| T3 | `neo4j_mode.py` needs `neonradar_ingest.synth.writer` | P | M3.3 (a dependency of M3.2) |

### 2.8 Detection store

**On `main`.** Phase 1's runner writes `data/runs/<run_id>/alerts.jsonl` (one `model_dump_json()` per line) and `run.json`; `data/` is ignored by git apart from `fixtures/`, `import/` and its README. It loads with the Python strings `MERGE_RUN`, `PRUNE_RUN` and `MERGE_ALERTS` in one managed write transaction, merging on `run_id`, `alert_id` and each alert-subject pair, and keeps other runs. `:DetectionRun` (C2 1.0.0): `run_id`, `started_at`, `finished_at`, `typologies`, `detectors` (JSON), `alert_count`, `status`. `:Alert`: `alert_id`, `typology`, `typology_version`, `priority`, `pattern_strength`, `headline`, `created_at`, `run_id`, `wording_class`, `involves_real_entities`, `synthetic_activity`, `payload`. The API's alert detail (`api/src/neonradar_api/alerts.py`) parses `payload` with C4's `Alert`, so a stored alert must validate (A1 to A3).

| # | Difference | Class | Next step |
|---|---|---|---|
| S1 | L19 replaces all earlier detection results; Phase 1 merges per run id and prunes only that run | M (C2 1.2.0) | M3.2, after M3.1 |
| S2 | The new properties: `profile`, `params_sha256`, `summary`, `window_start`, `window_end` on `:DetectionRun`; `evidence_node_ids`, `evidence_edge_ids` on `:Alert` | P | Pending M3.1 |
| S3 | The statements are Python strings; from Phase 2 on, new or changed statements live in `.cypher` files (phase-2 reconciliation A12) | M | M3.2 moves the store statements into files that pass `make cypher-lint` |
| S4 | Where a run on the real-data instance writes (phase-2 reconciliation E11, open) | D by PHASE-3.md 4.5 | `data/cache/real/runs/<profile>/<run_id>/`, with counts-only summaries in `data/cache/reports/<profile>/` (M3.4, `runs_dir`). Phase 1's `data/runs/<run_id>/` stays for runs without a profile |
| S5 | `alerts.jsonl` with sorted keys and `summary.json` | M | M3.2 deliverable 5 |

### 2.9 Project file

**On `main`.** No project model. `docs/build/project.yaml` is read ad hoc in four places: `neonradar_ingest.spikes` (`access.spike_cache_days`), `sources/opensanctions/access.py` (`access.opensanctions`), `cli/src/neonradar_cli/doctor.py` (the `access` mapping) and `cli/src/neonradar_cli/gate.py` (`people.interns`). `neonradar_ingest.data.project.Project` is M2.2's.

| # | Difference | Class | Next step |
|---|---|---|---|
| P1 | The model gains `access.real_overlay_profiles`, `access.real_registry_alerts`, `people.freeze_deciders` and the five `schedule` dates of PHASE-3.md 1.3, with unit tests | P | Pending M2.2. As M3.0 deliverable 7 says, M3.3 (the first Phase 3 milestone after M2.2) adds them as its deliverable 7. The keys are in `project.yaml` from this pull request |
| P2 | Until the model exists, nothing reads the new keys | D | Later milestones read them through the model only (2.10) |

### 2.10 Command line

**On `main`.** The `neonradar` typer app (`cli/src/neonradar_cli/main.py`) has `doctor`, `api`, `contracts`, `detect` (`run`, `list`), `docs`, `gate`, `graph` (`smoke`, `migrate`, `load`, `stats`, `wipe`), `onboarding`, `spike` and `synth` (`demo-mini`, `check-names`). `graph load PATHS... [--strict/--no-strict] [--timeout SECONDS]`; `detect run [--typology SLUG] [--run-id ID] [--timeout SECONDS]`; `detect list` takes no option. No `eval` group, no `synth world` or `synth overlay`, no `--profile` option anywhere.

| # | Difference | Class | Next step |
|---|---|---|---|
| L1 | `detect run` gains `--profile`, a repeatable `--typology`, `--engine`, `--window` and `--keep-previous`; `detect list` gains tier, version and whether the detector exists | M | M3.2 deliverable 5 |
| L2 | `graph load --profile NAME --overlay latest` | P | Pending M2.11 (profile loads); M3.4 |
| L3 | `synth world` and `synth overlay` | M | M3.3 |
| L4 | The `eval` group | M | M3.6 and M3.11. The guard blocks `eval run --split test` from this pull request on |
| L5 | `make demo-data` (and so `make demo-mini`, `demo-dev` and the e2e job) runs `neonradar detect run` with no option on the default instance, and the e2e test needs one "Synthetic scenario" alert. Measured in memory: `circular_flow` 0.2.0 on `demo-mini` over its `PAID` time range gives 1 finding and 1 `synthetic_scenario` alert ("Synthetic scenario: funds returned to the originating account through 4 transfers within 4 days") | M | M3.2 keeps `detect run` without options working on the default instance (its goal says so); the alert only validates once A1 is answered |

### 2.11 Profiles and layout

**On `main`.** No `ingest/profiles/` folder and no `neonradar_ingest.data` package.

| # | Difference | Class | Next step |
|---|---|---|---|
| Y1 | The profile YAML, `worlds_dir`, `overlay_dir`, `latest_overlay`, `eval_dir`, `holdout_dir` | P | Pending M2.2; M3.3 checks again |
| Y2 | `runs_dir`, `latest_detection_run`, the overlay and detection blocks of the Phase 2 profiles | P | Pending M2.2 and M2.11; M3.4 checks again |

## 3. The contract tests and M3.1

| # | Item | Class | Next step |
|---|---|---|---|
| K1 | `contracts/tests/test_wording.py`: `catalog_templates()` passes every value under a typology file's `wording` to `find_forbidden`. `wording.variants` is a mapping, so the test fails as soon as a file with variants is on `main` (`shell_chain` in M3.5b; `dormant_reactivation` and `fan_in_collection` in M3.5c; `sanctions_exposure` in M3.5e; `pep_exposure` and `recycled_directors` in M3.5f). `wording.detail` is text and passes. `names_with_detector()` lints each typology's name: the 14 Phase 3 names pass (measured) | Q tech lead | **M3.1 changes it**, as the issue text of PHASE-3.md 5.0 allows: lint each pair under `wording.variants` and `wording.detail`, and lint `shape_name` as well as `name` |
| K2 | `contracts/tests/test_alert.py` reads no typology file and builds no Phase 3 alert, so the Phase 3 typology files need no change to it. It asserts `versions.ALERT == "1.0.0"`, which changes only if A3 is answered with option (a) | None | None (unless A3 (a)) |
| K3 | The issue text names `contracts/C2-graph.md`; the file is `contracts/C2-graph-schema.md` | M | M3.1 |
| K4 | PHASE-3.md 5.4 names `contracts/tests/test_versions.py` "or the Phase 1 file that checks versions": the checks are `contracts/tests/test_graph_mapping.py::test_version` (`graph.SCHEMA_VERSION == versions.GRAPH_SCHEMA == "1.0.0"`) and `test_alert.py` | M | M3.1 |
| K5 | Invariants on `main`: I1 to I6, as test strings in `graph/tests/test_invariants.py`; I7 to I14 come with Phase 2 | P | Pending M2.1c and M2.11; I15 to I17 in M3.1, wired into `graph verify` in M3.4 |
| K6 | Every contract is at 1.0.0; C2 1.2.0 builds on Phase 2's 1.1.0 | P | Pending M2.1a to M2.1c |

## 4. The agent kit in this pull request (M3.0)

| # | Item | Class | Decision |
|---|---|---|---|
| D1 | `guard_real_data.py`: `data/cache/holdout` joins the protected folders, and a command line that names it may run only the read-only git subcommands. That is stricter than `data/cache/real`, where listing programs may run, because the spec's cases block `ls data/cache/holdout`. `git grep` for the folder's name stays allowed | D | As built; eight cases as the spec lists them (179 in all) |
| D2 | `.claude/settings.json`: `Read(/data/cache/holdout/**)` as well as the `./` form the spec names, as M2.0 did for the other protected folders (phase-2 reconciliation A13) | D | As built |
| D3 | `.github/pr-size-exclude.txt`: `docs/build/PHASE-3-CODE.md` added although `**/*.md` already covers it | D | As the spec says |
| D4 | The project model keys wait for M2.2 (P1) | D | M3.3, as M3.0 deliverable 7 says |
| D5 | `ingest/pyproject.toml` had `numpy>=2.5,<3`, not an unpinned `numpy`; now `numpy==2.5.*` (the lock keeps 2.5.4). `detect` keeps Phase 1's `pyyaml>=6,<7` (PHASE-3.md 3.1) | M | As built |

## 5. Phase 3 milestones and what they wait for

What each milestone waits for on 22 October, beyond its Phase 3 dependencies (PHASE-3.md 1.8):

| Milestone | Waits for |
|---|---|
| M3.1 | Tag `contracts-v1.0.0` (Gate 1); M2.1c and tag `contracts-v1.1.0`; the approved contract-change issue (5.0); an answer to K1, and to A3 if it is answered with a C4 change |
| M3.2 | M3.1 and M3.3; answers to A1, A2, R1, R2 and C2 |
| M3.3 | M2.1a and M2.2; M2.9 for invented surnames (N1); N2; an answer to N3 |
| M3.4 | M3.2; M2.11 |
| M3.5a to M3.5f | M3.2; an answer to A3 before M3.5b, M3.5e and M3.5f; M2.1a before M3.5e (A4) |
| M3.6 | M3.2 |
| M3.7 | M3.4 and M3.6; M2.13 |
| M3.8 | M3.7 and M3.5a to M3.5e |
| M3.9 | M3.7 |
| M3.10 | M3.5a to M3.5e and M3.6 |
| M3.11 | M3.5a to M3.5e, M3.6 and M3.10; `people.freeze_deciders` (still `@TODO`) |
| M3.12 | M3.11 and the human holdout run |
| M3.13 | Everything above |

## 6. Questions, by person

**Tech lead:** A1 (the query hash C4 checks), A2 (the window key of registry alerts), A3 (boolean metrics and C4), R1 (Phase 1's headline formatting), R2 (retiring Phase 1 tests of replaced modules), C2 (format specs in typology files), G4 (flag labels for sub-topics, with phase-2 E2), K1 (the change to `contracts/tests/test_wording.py` in M3.1), N3 (OD-12 searches, with the data steward).

**Data steward:** N3 (OD-12 searches for the names the Phase 3 verbatim files commit).

Each question blocks only the milestones named in its row.
