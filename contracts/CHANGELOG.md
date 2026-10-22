# Contracts changelog

The four NeonRadar contracts and their versions (`neonradar_contracts.versions`). The tech lead tags `contracts-v<version>` when the contracts freeze (`docs/build/PHASE-1.md` 5.0); after that, every change needs an approved contract-change issue and an entry here.

## 1.1.0 (unreleased)

Phase 2 (`docs/build/PHASE-2.md` 5). Every change is additive: everything valid under 1.0.0 stays valid. The tech lead tags `contracts-v1.1.0` when M2.1a to M2.1c have merged (5.0).

### C1: NeonRadar Record 1.1.0

Contract-change issue #53 (M2.1a, PHASE-2.md 5.1). Details in [C1-record.md](C1-record.md#changes-in-110).

- **Datasets:** five entries in `datasets.yaml`, with the licence fields of 5.1 verbatim: `gb_fcdo_sanctions` (OGL v3.0), `us_ofac_sdn` (CC0 1.0), `un_sc_sanctions` (`LicenseRef-UN-Terms-of-Use`, `commercial_use: permission-required`), `eu_fsf` (`LicenseRef-EC-Reuse-Decision-2011-833`) and `gb_parliament_members` (`LicenseRef-Open-Parliament-Licence-3.0`). The data steward approves each licence field and attribution line in the M2.1a review (G2-11).
- **Dataset fields:** optional `kind` (`registry`, `list`, `leak`, `synthetic`) and `anchor_priority` (an integer, 1 first, unique; `load_registry()` refuses duplicates) on all ten entries; `commercial_use` also accepts `permission-required`. `gb_companies_house`, `gleif_lei` and `icij_offshore_leaks` move from `status: spike` to `active`; `opensanctions_default` stays `blocked`.
- **New `nr` keys:** `ch_person_number` (string, any `LegalEntity`), `psc_statements` (list of strings, `Company`), `accounts_category` (string, `Company`), `share_pct_min_exclusive` and `share_pct_max_exclusive` (booleans, `Ownership` and `Control`).
- **Wider `nr` keys:** `synthetic_kind` also accepts `list` and `leak`; `is_nominee` is also allowed on `Ownership`; `share_pct_min` and `share_pct_max` are also allowed on `Control`.
- **Versions:** `nr.v` accepts `"1.0"` and `"1.1"`, and every key under both; `versions.RECORD` and `versions.CONTRACTS` are `1.1.0`, so `write_manifest()` writes `record_contract: "1.1.0"`. The manifest's `record_contract` pattern already accepted both values and is unchanged. The JSON Schema `schemas/record-nr.v1.json` is regenerated (the file name keeps the major version).
- **Examples:** `examples/c1/demo-1.1.ftm.jsonl` (the seven lines of 5.1) and its manifest, valid in strict mode; the 1.0 example `demo.ftm.jsonl` and its manifest (`record_contract: "1.0.0"`) stay as they are and stay valid.
- **Consumers in this change:** the demo-mini fixture manifest is regenerated (`make fixtures`; only `record_contract` changes, the records are byte-identical), and the API test of `GET /meta` reads `versions.CONTRACTS`.

#### Changed from `docs/build/PHASE-2.md` 5.1 (tech lead sign-off at the M2.1a review)

- **Example names (OD-12):** the build agent cannot run the Companies House search, so the spec's names were replaced by names already checked: "Quarry Lane Instruments Ltd" by "Plover Brae Textiles Ltd" (a demo-mini company, checked in M1.8e); the officer "MARLOWE, Petra Anne" by "VELQASIMI, Yazan Zafer"; the list-style person "Ivo Kestrane" (alias "Iwo Kestran") by "Rakan Zubeirono" (alias "Raqan Zubeirono"); the leak-style entity "QUILLAN BRASKE" by "NADIM ULVARAZI". The surnames Velqasimi, Zubeirono and Ulvarazi had no result on the Companies House officer or company search on 21 October 2026, searched alone (#17), so no name with them can match a live record; the given names come from the same checked names (Zafer Qandelouni, Yazan Velqasimi, Rakan Zubeirono, Nadim Ulvarazi). None is on the synthetic-name denylist. "Synthetic Authority A" is kept: it names no person or company.
- **Id forms of the list loaders:** the sanctions and Parliament id forms of PHASE-2.md 4.4 without a kind segment (`uksl-g<group id>`, `uksl-<unique id>`, `ofac-<uid>`, `unsc-<ref>`, `eufsf-<logicalId>`, `ukparl-<member id>`) are allowed next to `make_id`, so the verbatim tests of M2.6 and M2.10a keep them. They pass R1 unchanged. Orchestrator decision under OD-10, `docs/build/phase-2-reconciliation.md` B6.

### C2: Graph schema 1.1.0

Additive (minor) change for entity resolution, `docs/build/PHASE-2.md` 5.2, M2.1b, contract-change issue #52. Every 1.0.0 graph stays valid; a load without a resolution run behaves as in 1.0.0 apart from the new `false` defaults and the two company properties.

- **`:SourceRecord` defined:** `id`, `dataset`, `schema`, `caption`, `names`, `topics`, `canonical_id`, `synthetic`, `retrieved_at`, `source_url`, `run_id`; one per member of an entity merged from two or more records.
- **`RESOLVED_TO` extended:** `method` is `anchor`, `deterministic`, `probabilistic` or `human` (`match_probability` 1.0 for all but `probabilistic`); new `rule`, `run_id` and `features`.
- **`POSSIBLY_SAME_AS` added** between two `:LegalEntity` nodes, stored from the smaller id to the larger and read as undirected: `id` (`<a>|psa|<b>`), `match_probability` and `match_weight` (null for `deterministic` and `source_hint` matches), `method`, `rule`, `reasons`, `features`, `run_id`, `resolver_version`, `datasets`, `synthetic`. It is a support relationship in `neonradar_contracts.graph` (written by entity resolution, not built from records), so C3's record-built relationship types are unchanged here.
- **Entity properties:** `cluster_size`, `resolution`, `names_latin`, `names_latin_text` on every `:Entity` (computed by the resolution-aware loader, M2.11; `ENTITY_RESOLUTION_PROPERTIES`).
- **Company properties:** `psc_statements` and `accounts_category` from `nr.psc_statements` and `nr.accounts_category` (C1 1.1.0).
- **`OWNS`:** `share_min_exclusive` and `share_max_exclusive` from `nr.share_pct_min_exclusive` and `nr.share_pct_max_exclusive`, and `is_nominee` from `nr.is_nominee`, each `false` when absent (`RelationshipMapping.defaults`).
- **`CONTROLS`:** the voting-rights band `share_pct_min` and `share_pct_max` (null when absent) and `share_min_exclusive` and `share_max_exclusive` (`false` when absent). A voting-rights band is control, not a share: the ownership endpoint still traverses only `OWNS`.
- **Migration `0002_resolution.cypher`** (verbatim from the spec): the constraint `possibly_same_as_id`, the indexes `source_record_canonical_id` and `source_record_dataset`, and the full-text index `entity_names` rebuilt under the same name over `names_text` and `names_latin_text`. After 0001 and 0002: 23 constraints and 9 own indexes.
- **Loader rules L8 to L17 and invariants I7 to I14** written into [C2-graph-schema.md](C2-graph-schema.md); M2.11 implements them.
- `versions.GRAPH_SCHEMA` is `1.1.0`, so `GET /api/v1/meta` reports `schema_version` 1.1.0.

#### Clarifications of PHASE-2.md 5.2 (tech lead review in M2.1b)

- **`DIRECTOR_OF.is_nominee`** keeps the 1.0.0 rule (no default when the record has no value); only `OWNS.is_nominee` defaults to `false`, as 5.2 says.
- **Value sets and nullable properties as data:** `ENTITY_RESOLUTIONS`, `RESOLVED_TO_METHODS`, `POSSIBLY_SAME_AS_METHODS`, `CERTAIN_METHODS` and `NULLABLE_PROPERTIES` (`POSSIBLY_SAME_AS.match_probability`, `match_weight` and `rule`; `RESOLVED_TO.rule` and `features`), so M2.11's loader and verifier read one source.

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
- **R6:** only synthetic records may set `nr.synthetic`. A synthetic `Sanction` names only synthetic entities (prefix `syn`), in strict and non-strict mode: C2 builds `SUBJECT_OF` from it, so a real entity would show as sanctioned (G1; added after the M1.7c follow-up review). The same holds for a synthetic `Family`, `Associate` or `Occupancy` on every entity reference, because `FAMILY_OF`, `ASSOCIATE_OF` and `HOLDS_POSITION` could make a real person a relative or close associate of a politically exposed person, or the holder of a post (orchestrator decision under OD-10, listed for Gate 1). `Representation` and `Membership` stay allowed, like `Ownership`. Flag topics (`sanction`, `role.pep`, `role.rca`) need no extra rule: a record's topics flag only its own node, and a synthetic record's node is always a `syn` id (R6). Other synthetic records, such as an `Ownership` naming a real owner, stay allowed as background activity.
- **R7:** exactly one value each of `payer`, `beneficiary`, `payerAccount`, `beneficiaryAccount`, `amount`, `currency` and `date`; `currency` must be in Babel's ISO 4217 list (CLDR), not only three upper-case letters.
- **R9:** a name heuristic: a top-level key, `nr` key or property name containing `typolog`, `scenario`, `illicit`, `lookalike`, `ground truth` or `label` fails. Synthetic records may carry only the topics that set C2 flags (`sanction`, `role.pep`, `role.rca`), so no other topic can hint at a scenario.
- **NR:** the "Used on" column of the `nr` table is enforced (and `nr.synthetic_kind` only on synthetic records); `nr.address_roles` keys must be among the record's `addressEntity` values; `nr.share_pct_min` must not exceed `nr.share_pct_max`.
- **FORMAT:** the top-level keys are a closed set, so OpenSanctions' legacy `target` key is rejected; files must be UTF-8.
- **Patterns:** Python `re` patterns end with `\Z`; pydantic field patterns end with `$`, which pydantic's engine matches only at the very end. Either way, a value with a trailing newline fails. In the exported JSON Schema, the manifest's fixed-length fields (`created_at` and `source.retrieved_at`, 20 characters; `files[].sha256`, 64) also carry `minLength` and `maxLength`, because the jsonschema package matches `pattern` with Python's `re`, where `$` also matches before a final newline (added after the M1.7c review, with the C4 tightenings below).
- **ASCII digits** (pre-freeze patch clarification, orchestrator decision under OD-10, listed for Gate 1): every C1 pattern uses `[0-9]` instead of `\d`, which Python reads as any Unicode digit. Before, a Payment `amount` or a synthetic `accountNumber` in Arabic-Indic digits passed R7 and R8, and so did the manifest's `created_at`, `source.retrieved_at` and `record_contract`. Ids (R1) were already ASCII, and dates (R5) go through FtM, which rejects them.
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
- **Loader reload (C2 doc, M1.9a):** reloading changed files moves a relationship whose end or type changed and removes mapped properties a record dropped; records no longer in the files stay, so the invariants hold after `neonradar graph wipe --yes` followed by a load. No schema or migration change.
- **Migration runner:** the checksum is taken after normalising line endings to LF; the runner also refuses a database that has a migration the folder lacks and a pending migration numbered below an applied one, and waits for new indexes (`db.awaitIndexes`) before recording a migration.

#### Open for Gate 1 sign-off (tech lead)

- **Single-valued identifiers.** `registration_number`, `lei` and `account_number` hold one value (the first, in FtM's stored order), so the range indexes can serve equality lookups; C3 `EntityDetail.identifiers` is `dict[str, list[str]]`. Either keep the graph single-valued and let the API list one value (Phase 2's `:SourceRecord` keeps all), or make them lists in C2 before the freeze.
- **`PAID.amount` is a FLOAT.** A double is exact to the cent only up to about 10^13 major units; detectors compare amounts after rounding to cents. A Phase 1 alternative would be an INTEGER in minor units.
- **`MIGRATIONS_DIR` lives in the source tree** (`graph/schema/migrations`, found relative to the package source). That works for the uv workspace's editable install; packaging the migrations as package data is open for M1.9e or later.

### C3: API 1.0.0

- The API contract: every model of `docs/build/PHASE-1.md` 5.3 in `neonradar_contracts.api` ([C3-api.md](C3-api.md)), the app `neonradar_api.main.create_app` with every v1 route declared (M1.7d implemented `GET /api/v1/health` only; M1.9c implements the other Phase 1 routes, and ownership, paths and the copilot answer 501 naming Phase 2 or Phase 4), and `neonradar api serve` on `127.0.0.1`.
- The OpenAPI snapshot `openapi/v1.json`: `neonradar contracts export` writes it from the running app and `neonradar contracts check` fails on drift (the command line adds it to the generated files, because this package cannot import the API); `api/tests/test_openapi_contract.py` compares the app with it.
- Synthetic examples in `examples/c3/` (`subgraph.json`, `entity-detail.json`, `problem-501.json`); they reuse names already checked under OD-12 (the C4 example's holder, the C1 example's bank), so no new name was checked.

#### Changed from `docs/build/PHASE-1.md` 5.3 (tech lead sign-off at Gate 1)

- **`Citation.year`** is `int | null`: the bibliography gives living documents `year: null` (7.3).
- **`TypologyDetail.definition_markdown`** is `str | null`: null when the explainer file does not exist (M1.9c reads it "when present").
- **`GET /entities/{entity_id}`** and **`/network`** serve `:Sanction` nodes as well as `:Entity` nodes, so a sanction reached through `SUBJECT_OF` in a network can be opened; in C3 an entity is any node with a C2 record id.
- **`GET /entities/{entity_id}/ownership`:** `direction` is required (5.3 gives no default); `min_share` is optional.
- **Limits 5.3 does not give:** `cursor` 1 to 512 characters, `context_entity_ids` at most 20, `EntityDetail.alerts` at most 50 (the rest through `GET /alerts?entity_id=`).
- **Sub-model names** for the inline objects of 5.3: `SubgraphLimits` (`Subgraph.limits`), `GraphCounts` (`MetaResponse.counts`) and `Neo4jStatus` (`HealthResponse.neo4j`).
- **OpenAPI at `/api/v1/openapi.json`**, and FastAPI's `/docs` and `/redoc` pages are not served: they load Swagger UI and ReDoc from cdn.jsdelivr.net and a favicon from fastapi.tiangolo.com, which guardrail G3 forbids. M1.9c added the offline documentation page at `GET /docs`, outside `/api/v1` and not in the snapshot.
- **FastAPI telemetry off:** FastAPI 0.143 (not in PHASE-1.md 3.1 or 3.2) ships native OpenTelemetry that can add OTLP exporters from `FASTAPI_OTEL_AUTO_CONFIGURE` and `OTEL_EXPORTER_OTLP_*`; the app switches every part off and a test checks that the environment cannot switch it on and that no OpenTelemetry SDK or exporter is installed (G3).
- **Dependencies:** `uvicorn>=0.54,<0.55` (5.3 names it without a version); `httpx>=0.28,<0.29` in the dev group for FastAPI's TestClient. Starlette 1.9 suggests `httpx2` instead, but `httpx2` is published from github.com/pydantic/httpx2, not by encode (checked on pypi.org on 21 October 2026), so the tests keep httpx with one targeted warning filter.
- **Typology `tier` and `status`** Literals live in `neonradar_contracts.api` (the API serves them), and `neonradar_detect.catalog` imports them.

#### Clarifications of 5.3 (tech lead sign-off at Gate 1)

The spec's shapes are kept; these say how the models and routes read them.

- **Final OpenAPI now:** every route is declared with its final response model, limits and problem responses, so implementing a route (M1.9c) does not change the snapshot. Routes M1.9c implements do not list `501`, although they answer it until then. The 501 entries of the ownership, paths and copilot routes stay declared after those routes are implemented, so implementing them never changes the snapshot.
- **Finite numbers and shared C4 types:** every C3 model refuses NaN and infinity (`allow_inf_nan=False`, and C4's `FiniteJsonValue` in property and parameter maps); `AlertSummary.alert_id` is C4's `AlertId` and timestamps C4's `UtcTime`, both fixed-length; the `alert_id` path and `run_id` query parameters carry the same lengths; `AlertSummary.subject_ids` repeat no id (`uniqueItems`). `AlertDetail.alert` follows C4 as amended by the C4 follow-up (#28): `evidence.window` is required and may be null.
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
- **ASCII digits** (pre-freeze patch clarification, orchestrator decision under OD-10, listed for Gate 1): `PackageVersion` and the shared `Version` pattern use `[0-9]` instead of `\d`, so the server accepts exactly what ECMAScript clients validate; the OpenAPI snapshot and the UI's generated `ui/src/api/schema.d.ts` change only in pattern strings.

#### Clarified in M1.9c (pre-freeze patch wording; the snapshot is unchanged; Gate 1 sign-off)

- **Stale alerts:** the `500` problem also covers an alert whose evidence is no longer in the graph, and its detail says to wipe and reload the data, then re-run detection (a new run does not remove earlier runs' alerts). Whether `GET /alerts/{alert_id}` should declare `500` in the OpenAPI document is on the Gate 1 list.
- **Search:** `total_estimate` counts the label-filtered hits within the first 200 full-text hits plus exact account-number matches, a lower bound; an exact account-number hit comes first with the response's top score (1.0 when there is none).
- **Network:** the relationships returned are those of the requested types between the kept nodes.
- **Host check:** only the `Host` values in `NR_ALLOWED_HOSTS` (default `localhost`, `127.0.0.1`, `api`) are answered; any other gets Starlette's `400 text/plain` (DNS rebinding guard, review of #43).
- **Files:** `NR_REPO_ROOT` locates `detect/typologies/`, `docs/typologies/` and the bibliography for the typology routes; `GET /meta` reads the registry and disclaimers from the contracts package. `GET /docs` is the offline page, outside `/api/v1` and the snapshot.

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
- **`evidence.window`:** 5.4's "optional `window`" means nullable, not omitted: the key is always present, `null` when the finding has no time window, and the JSON Schema lists it as required. This follows the C3 rule that every response field is required and nullable ones are present as `null` (openapi-typescript then emits `window: Window | null`, not `window?:`). Changed after the M1.7c review; an alert without the key now fails.
- **Formats:** `created_at` and `window` times are UTC `YYYY-MM-DDTHH:MM:SSZ` (real dates), `window.start` is not after `window.end`; `run_id` is `run-<yyyymmddThhmmss>-<4 hex>`; versions are `MAJOR.MINOR.PATCH`; `detector.name` is a dotted module path; `typology` and roles are lowercase snake case.
- **Metrics** are scalar: numbers, strings that are codes such as a currency, or booleans (no lists, objects or null; booleans since the pre-freeze widening below). Detectors never put names in metrics. A typology with several findings per subject emits one alert per finding, so metrics stay scalar (for example `sanctions_exposure`, Phase 3: one alert per sanctioned owner).
- **Priority:** `default_priority()` implements the default rule; the model does not enforce it, because a typology may document its own.
- **Strictness:** every object is closed (unknown keys fail) and values are not coerced (`"0.79"` is not a number). The JSON Schema checks shapes and formats only; the rules above that compare fields need the model.
- **Runs and storage:** a re-run merges onto the same `:Alert` (the id does not depend on the run), which keeps the latest run's payload and `run_id`; the API (M1.9c) lists one run's alerts through `PRODUCED` from its `:DetectionRun`.
- **Typology files:** the file name is `<slug>.yaml`; `doc` is `docs/typologies/<slug with hyphens>.md`; placeholders are `{metric}` or `{metric:<format spec>}` (no positional, attribute, index or conversion fields); `headline_synthetic` starts with "Synthetic scenario" and `headline_structural` never says it (7.1); the templates, every `false_positives` entry, the slug and, once a detector exists, the name pass the wording lint; an `explainer_only` typology has `detector: null`; `metrics` does not repeat a name; a numeric parameter's `default` lies within `min` and `max`; `owner` and `approved_by` are GitHub handles, and `approved_by` is never `@TODO`.

#### Tightened after the M1.7c review, before the freeze (tech lead sign-off at Gate 1)

A late review of M1.7c found gaps; the contracts were not frozen yet, so the model was tightened. Each rule is in [C4-alert.md](C4-alert.md) and has a test in `contracts/tests/`.

- **Finite numbers:** every Alert model sets `allow_inf_nan=False`, and `evidence.query.parameters` is checked at any depth, because pydantic's JSON parser reads `NaN` and `Infinity` into a `JsonValue` regardless. Before, NaN or infinity in `metrics` or `evidence.query.parameters` passed and was written back as `null`.
- **`synthetic_activity` and evidence edges:** an evidence relationship counts as the record it was built from (C2): the interval record, the entity of `a|addr|b`, the Sanction of `a|sanction|b`. `data_flags.synthetic_activity` must be false when any of those records belongs to a non-synthetic dataset, and true when there is at least one and all are synthetic (a prefix of no dataset, `nr`, decides neither). This enforces both halves of the 5.4 definition ("true if every evidence relationship is synthetic"), which the model did not check before. With no evidence relationships, an alert with real entities has `synthetic_activity: false` (there is no generated activity to point to); an all-synthetic alert keeps `true`.
- **`data_flags.datasets` covers the ids:** it lists the dataset of every id prefix the alert names (subjects, evidence nodes, the records of evidence relationships; `nr-` ids skipped). It may list more, such as an evidence-account holder's dataset.
- **`evidence.window` required and nullable:** see the clarification above; an alert without the key fails.
- **Distinct subjects:** `subjects` never repeats an `entity_id`, because C2 `FLAGS` carries one `role` per alert and entity: one `FLAGS` per alert and subject entity (`MERGE` on the pair, `SET` the `role`), and a re-run removes `FLAGS` to entities that are no longer subjects (C2-graph-schema.md).
- **Wording lint:** `find_forbidden` normalises the text and the masked values before matching (NFKC, then format characters of category Cf removed), so fullwidth or mathematical letters (a fullwidth "m" in "mule") and soft hyphens, zero-width spaces or word joiners no longer hide a term; `scripts/check_wording.py` normalises the same way. The "synthetic scenario" check (`SYNTHETIC_PHRASE`) also reads normalised text, through `says_synthetic_scenario`, in `Alert` (headline, summary, steps), `render_headline` and `TypologyFile`. The forbidden patterns and the phrase pattern themselves are unchanged.
- **Fixed lengths in the JSON Schema:** `alert_id` and `run_id` (24 characters), `created_at` and the `window` times (20) and `detector.query_sha256` (64) carry `minLength` and `maxLength`, so the exported `alert.v1.json` also rejects a trailing newline under Python's jsonschema package (whose `pattern` check lets `$` match before a final newline). The model already rejected it. The C1 manifest's fixed-length fields got the same lengths (see C1, Patterns). Fields with a pattern but no fixed length still rely on the model: Python's jsonschema accepts a trailing newline there.
- **Shared types:** `neonradar_contracts.alert` exports `AlertId` (pattern and fixed length) and `FiniteJsonValue` (a `JsonValue` without NaN or infinity at any depth) for C3.
- **ASCII digits** (pre-freeze patch clarification, orchestrator decision under OD-10, listed for Gate 1): `run_id`, the UTC times and the versions use `[0-9]` instead of `\d`. Before, `run-٢٠٢٦١٠٢١T101500-7f3a` and versions in Arabic-Indic digits passed the model; the times were already rejected by the real-date check. A test checks that no exported JSON Schema or OpenAPI pattern contains `\d`, `\w` or `\s`.
- **`involves_real_entities` names evidence relationships** (pre-freeze patch clarification, orchestrator decision under OD-10, listed for Gate 1): the field is also true when an evidence relationship comes from a non-synthetic record. Rules 2 and 7 already required this (the record's dataset must be listed, and a listed non-synthetic dataset makes the flag true); the field description, the wording class and the helper's inputs now say so.
- **Boolean metrics** (pre-freeze widening for the Phase 3 detectors, orchestrator decision under OD-10, listed for Gate 1): `metrics` values are `bool | int | float | str`. Before, the strict model refused booleans, but the Phase 3 code book's detectors emit flags: `sanctions_exposure` 7, `pep_exposure` 2 and `mass_registration_address` 1 (`docs/build/phase-3-reconciliation.md` A3). `bool` comes first in the union, so in strict mode a JSON boolean stays a boolean and an integer stays an integer; numbers stay finite. The JSON Schema and C3's OpenAPI snapshot gain `{"type": "boolean"}` in the metric value. `render_headline` still refuses a boolean in a headline. `versions.ALERT` stays 1.0.0, because 1.0.0 is not released.
