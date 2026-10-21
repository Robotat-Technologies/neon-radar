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
- **Patterns:** Python `re` patterns end with `\Z`; pydantic field patterns end with `$`, which pydantic's engine matches only at the very end. Either way, a value with a trailing newline fails.
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

### C3: API 1.0.0

- The API contract: every model of `docs/build/PHASE-1.md` 5.3 in `neonradar_contracts.api` ([C3-api.md](C3-api.md)), the app `neonradar_api.main.create_app` with every v1 route declared (only `GET /api/v1/health` implemented; the others answer 501 naming M1.9c, Phase 2 or Phase 4), and `neonradar api serve` on `127.0.0.1`.
- The OpenAPI snapshot `openapi/v1.json`: `neonradar contracts export` writes it from the running app and `neonradar contracts check` fails on drift (the command line adds it to the generated files, because this package cannot import the API); `api/tests/test_openapi_contract.py` compares the app with it.
- Synthetic examples in `examples/c3/` (`subgraph.json`, `entity-detail.json`, `problem-501.json`); they reuse names already checked under OD-12 (the C4 example's holder, the C1 example's bank), so no new name was checked.

#### Changed from `docs/build/PHASE-1.md` 5.3 (tech lead sign-off at Gate 1)

- **`Citation.year`** is `int | null`: the bibliography gives living documents `year: null` (7.3).
- **`TypologyDetail.definition_markdown`** is `str | null`: null when the explainer file does not exist (M1.9c reads it "when present").
- **`GET /entities/{entity_id}`** and **`/network`** serve `:Sanction` nodes as well as `:Entity` nodes, so a sanction reached through `SUBJECT_OF` in a network can be opened; in C3 an entity is any node with a C2 record id.
- **`GET /entities/{entity_id}/ownership`:** `direction` is required (5.3 gives no default); `min_share` is optional.
- **Limits 5.3 does not give:** `cursor` 1 to 512 characters, `context_entity_ids` at most 20, `EntityDetail.alerts` at most 50 (the rest through `GET /alerts?entity_id=`).
- **Sub-model names** for the inline objects of 5.3: `SubgraphLimits` (`Subgraph.limits`), `GraphCounts` (`MetaResponse.counts`) and `Neo4jStatus` (`HealthResponse.neo4j`).
- **OpenAPI at `/api/v1/openapi.json`**, and FastAPI's `/docs` and `/redoc` pages are not served: they load Swagger UI and ReDoc from cdn.jsdelivr.net and a favicon from fastapi.tiangolo.com, which guardrail G3 forbids. M1.9c adds an offline documentation page; until then M1.9c's review step ("try a few searches at /docs") and M1.9e's printed docs URL need that page.
- **FastAPI telemetry off:** FastAPI 0.143 (not in PHASE-1.md 3.1 or 3.2) ships native OpenTelemetry that can add OTLP exporters from `FASTAPI_OTEL_AUTO_CONFIGURE` and `OTEL_EXPORTER_OTLP_*`; the app switches every part off and a test checks that the environment cannot switch it on and that no OpenTelemetry SDK or exporter is installed (G3).
- **Dependencies:** `uvicorn>=0.54,<0.55` (5.3 names it without a version); `httpx>=0.28,<0.29` in the dev group for FastAPI's TestClient. Starlette 1.9 suggests `httpx2` instead, but `httpx2` is published from github.com/pydantic/httpx2, not by encode (checked on pypi.org on 21 October 2026), so the tests keep httpx with one targeted warning filter.
- **Typology `tier` and `status`** Literals live in `neonradar_contracts.api` (the API serves them), and `neonradar_detect.catalog` imports them.

#### Clarifications of 5.3 (tech lead sign-off at Gate 1)

The spec's shapes are kept; these say how the models and routes read them.

- **Final OpenAPI now:** every route is declared with its final response model, limits and problem responses, so implementing a route (M1.9c) does not change the snapshot. Routes M1.9c implements do not list `501`, although they answer it until then. The 501 entries of the ownership, paths and copilot routes stay declared after those routes are implemented, so implementing them never changes the snapshot.
- **Strictness:** every object is closed and strict, like C4. Response fields have no defaults: nullable fields are `T | null` and always present, so generated TypeScript types are exact. Only `CopilotRequest.context_entity_ids` has a default (`[]`).
- **Errors:** RFC 9457 problems with `type: about:blank`, `title` the HTTP reason phrase, `instance` the request path; validation failures list `<location>: <message>` in `detail` without echoing input (an unknown body key is reported at its parent, as `unknown keys are not permitted`); a `405` detail points to the `Allow` header; no `errors` extension in v1. A malformed `NEO4J_URI` or an unknown `NEO4J_DATABASE` is a `503` (and `degraded` health), like an unreachable database. Rejected CORS preflights get Starlette's `400 text/plain`, which browsers do not expose. Error responses are declared as `application/problem+json` only; FastAPI's `HTTPValidationError` schema is not used.
- **Times:** model timestamps and `PAID.ts` are UTC `YYYY-MM-DDTHH:MM:SSZ`; every other date or datetime property (including `first_seen` and `last_seen`) is returned as stored.
- **Amounts** (`PAID.amount`) are JSON numbers in major units, the C2 FLOAT as stored, exact to the cent up to about 10^13; if C2 moves to integer minor units at Gate 1, C3's models do not change.
- **Identifiers** (`dict[str, list[str]]`) are keyed by C2 property name (`registration_number`, `lei`, `account_number` in v1); each list holds C2's one value, and Phase 2 adds values from `:SourceRecord` without a breaking change. This answers the C2 open item on single-valued identifiers from the API side, without changing C2.
- **Property maps:** `GraphNode.properties` holds every C2 node property except `id`, `schema`, `caption`, `names_text`, `synthetic` (in `flags`), `topics` and `referents`; `EntityDetail.properties` also leaves out `names`, `countries` and `datasets` (fields of their own); `GraphEdge.properties` holds every C2 relationship property except `id` and `topics`. The models reject the left-out keys. `topics` never appears in C3 (7.1: no source topics beyond the three flags next to entities). Absent properties are left out, never null.
- **`referents` left out of `GraphNode.properties`** (review of PR #24): it is merge history, already shown as `EntityDetail.provenance`, and grows with every merged record after Phase 2; removing it before the freeze costs nothing, after the freeze it would be a major change.
- **Graph shapes:** node `labels` (on `GraphNode` and `EntitySummary`) are exactly the C2 mapping labels of the node's `schema`, without flag labels; `schema` is one of the nine node schemata; edges are the 16 relationship types built from records (never `FLAGS`, `PRODUCED` or `RESOLVED_TO`); a `Subgraph` repeats no id, keeps both endpoints of every edge and stays within its `limits`, where `max_edges` is 2 × `max_nodes` (edges beyond it are cut and `truncated` is true).
- **Paths:** a `PathRef` has one edge fewer than nodes, and `edge_ids[i]` joins `node_ids[i]` and `node_ids[i + 1]`; ownership paths start at `root_id`, `/paths` paths run from `from_id` to `to_id`, and every path id is in the response's subgraph (the models check all of it). `min_share` keeps paths whose `effective_share_max` is at least `min_share` and drops paths with an unknown share.
- **`AlertDetail.evidence`** holds the evidence nodes and edges, the subjects, and the `HOLDS_ACCOUNT` relationships between them, and is never truncated; the model checks both. A stored payload that no longer validates as C4 is a `500` problem that says to re-run detection.
- **Alerts:** ordered by priority, then `pattern_strength` descending, then `alert_id`; the cursor is opaque, tied to its filters, and a bad one is a 422; `run_id` filters through `PRODUCED` (C4); `entity_id` filters on subjects.
- **`EntityDetail`:** one `ProvenanceRecord` per referent; `relationship_counts` counts each of the 16 record-built types in both directions and leaves out zeros; `alerts` are the alerts that flag the node. `AlertSummary.subject_ids` follow the order of the C4 `subjects`.
- **Null in v1:** `ProvenanceRecord.retrieved_at` and `DatasetInfo.loaded_at` (C2 records neither); `DatasetInfo.record_count` only when the graph cannot be read.
- **`MetaResponse`:** `app_version` is a PEP 440 version (the API package's); `schema_version` is `versions.GRAPH_SCHEMA` (the C2 version the API reads), not a `:SchemaMigration` id; `contracts_version` is `versions.CONTRACTS`. `GET /meta` answers 200 without Neo4j (null counts, empty count maps), so the disclaimers are always served.
- **`HealthResponse`:** `ok` exactly when Neo4j, APOC and GDS all answer; the route answers 200 for both statuses.
- **`CopilotAnswer`:** `answered` carries `answer_text`, `cypher`, `parameters` and `subgraph` and no `refusal_reason`; `refused` and `unsupported` carry a `refusal_reason` and no `answer_text`.
- **Read-only:** every query runs as a READ transaction through `neonradar_api.graph.GraphConnection.read`, with the sync neo4j driver from `neonradar_graph.client` (routes are plain `def` functions, run in FastAPI's thread pool).
- **CORS** allows exactly `http://localhost:5173`, for `GET` and `POST` with `content-type`, without credentials.
- **OperationIds** are the Python function names (`get_entity`, `list_alerts`, ...).
- **Clients are tolerant readers:** `additionalProperties: false` and the enums describe what this version's server emits; clients must not reject unknown fields, dictionary keys or enum values.

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
