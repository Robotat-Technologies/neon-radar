# C3: API v1.0.0

The HTTP interface through which the UI and, from Phase 4, the copilot read the NeonRadar graph. One FastAPI service serves it; it reads the graph (C2) and the alerts (C4) from Neo4j, and the dataset registry, disclaimers, typology catalog and bibliography from files in the repository.

- Status: version 1.0.0, **not frozen yet**. The tech lead freezes the four contracts at Gate 1 with the tag `contracts-v1.0.0` (`docs/build/PHASE-1.md` sections 5.0 and 8). After that, changes need an approved contract-change issue.
- Code: `neonradar_contracts.api` (every model), `neonradar_api.main.create_app` (the app and its routes), `neonradar_api.problems` (problem details), `neonradar_api.graph` (the read-only connection), `neonradar_api.health`.
- OpenAPI: `contracts/openapi/v1.json`, the running app's document, written by `neonradar contracts export` (`make contracts`). `neonradar contracts check` (part of `make contracts-check`) and `api/tests/test_openapi_contract.py` fail when the app and the file differ.
- Command: `uv run neonradar api serve [--port 8000]` (always `127.0.0.1`).
- Examples: `contracts/examples/c3/` (synthetic: `subgraph.json`, `entity-detail.json`, `problem-501.json`).
- Source: `docs/build/PHASE-1.md` section 5.3, with the changes and clarifications listed in [CHANGELOG.md](CHANGELOG.md) and the decision record `docs/decisions/0008-api-gateway.md`.

## Basics

- FastAPI, OpenAPI 3.1, base path `/api/v1`, JSON with snake_case fields. The OpenAPI document is served at `/api/v1/openapi.json`.
- Bound to `127.0.0.1` only (`neonradar api serve` has no host option). Inside the Compose container (M1.9e) it listens on all interfaces and Compose publishes it on `127.0.0.1`.
- CORS allows exactly `http://localhost:5173` (the Vite dev server), for `GET` and `POST` with a `content-type` header, without credentials.
- Read-only. Every query runs as a parameterised READ transaction (`routing_=RoutingControl.READ`); Neo4j refuses writes inside READ transactions.
- Nothing phones home (guardrail G3). FastAPI 0.143's native OpenTelemetry is switched off, including its auto-configuration from `FASTAPI_OTEL_AUTO_CONFIGURE` and `OTEL_EXPORTER_OTLP_*`, and no OpenTelemetry SDK or exporter is installed. FastAPI's `/docs` and `/redoc` pages are not served, because they load Swagger UI and ReDoc from a CDN and a favicon from fastapi.tiangolo.com; M1.9c adds an offline documentation page.

## Endpoints

Every route is declared with its final response model, parameter limits and error responses, so the OpenAPI snapshot does not change when a route is implemented. Until M1.9c, the routes it implements answer `501` with a problem that names it; their OpenAPI entries already describe the finished route and do not list `501`. The 501 entries of the ownership, paths and copilot routes stay declared after those routes are implemented, so implementing them never changes the snapshot.

| Method and path | Response model | Implemented in | Errors (problem details) |
|---|---|---|---|
| `GET /api/v1/health` | `HealthResponse` | M1.7d | none: always 200 |
| `GET /api/v1/meta` | `MetaResponse` | M1.9c | none: degrades instead |
| `GET /api/v1/search` | `SearchResponse` | M1.9c | 422, 503 |
| `GET /api/v1/entities/{entity_id}` | `EntityDetail` | M1.9c | 404, 422, 503 |
| `GET /api/v1/entities/{entity_id}/network` | `Subgraph` | M1.9c | 404, 422, 503 |
| `GET /api/v1/entities/{entity_id}/ownership` | `OwnershipResponse` | Phase 2 (501 until then) | 404, 422, 501, 503 |
| `GET /api/v1/paths` | `PathsResponse` | Phase 2 (501 until then) | 404, 422, 501, 503 |
| `GET /api/v1/alerts` | `AlertPage` | M1.9c | 422, 503 |
| `GET /api/v1/alerts/{alert_id}` | `AlertDetail` | M1.9c | 404, 422, 503 |
| `GET /api/v1/typologies` | `list[TypologySummary]` | M1.9c | none |
| `GET /api/v1/typologies/{slug}` | `TypologyDetail` | M1.9c | 404, 422 |
| `POST /api/v1/copilot/ask` | `CopilotAnswer` | Phase 4 (501 until then) | 422, 501, 503 |

OperationIds are the Python function names (`get_health`, `search`, `get_entity`, `get_network`, `get_ownership`, `find_paths`, `list_alerts`, `get_alert`, `list_typologies`, `get_typology`, `ask_copilot`, `get_meta`).

### Parameters and limits

| Route | Parameter | Rule |
|---|---|---|
| search | `q` | required, 2 to 200 characters |
| search | `labels` | repeatable; `Person`, `Company`, `Organization`, `LegalEntity`, `Address`, `Account` |
| search | `limit` | 1 to 50, default 20 |
| entities | `entity_id` (path) | a C2 node id (C1 id form, rule R1 as changed by OD-11) |
| network | `depth` | 1 to 3, default 1 |
| network, paths | `rel_types` | repeatable; one of the 16 relationship types built from records (below); all of them when absent |
| network | `max_nodes` | 1 to 500, default 200 |
| ownership | `direction` | required, `up` (owners) or `down` (holdings) |
| ownership | `max_hops` | 1 to 8, default 6 |
| ownership | `min_share` | optional, 0 to 100: keeps paths whose `effective_share_max` is at least `min_share`; paths with an unknown share (null) are dropped when `min_share` is set |
| paths | `from_id`, `to_id` | required node ids |
| paths | `max_hops` | 1 to 6, default 4 |
| alerts | `typology` | optional slug |
| alerts | `priority` | optional `high`, `medium` or `low` |
| alerts | `entity_id` | optional node id: alerts that flag it (its subjects) |
| alerts | `run_id` | optional, `run-<yyyymmddThhmmss>-<4 hex>`: alerts the run produced (through `PRODUCED`, C4-alert.md "Runs and storage") |
| alerts | `limit` | 1 to 200, default 50 |
| alerts | `cursor` | optional, 1 to 512 characters, opaque |
| alert | `alert_id` (path) | `alr-` plus 20 hex characters |
| typology | `slug` (path) | lowercase snake case |
| copilot | body `CopilotRequest` | `question` 1 to 500 characters; `context_entity_ids` at most 20 node ids, default `[]`; no other key |

A request that breaks a rule gets a `422` problem.

## Values

- **Ids.** Node ids are C2 `id` values (record ids in Phase 1, canonical `nr-` ids after Phase 2 entity resolution); relationship ids are C2 relationship ids (the FtM interval entity id, `<entity id>|addr|<address id>` or `<entity id>|sanction|<sanction id>`). Neo4j `elementId()` values never appear.
- **Times.** Every timestamp, in a model or in a property map, is UTC `YYYY-MM-DDTHH:MM:SSZ` with seconds precision, as in C4. `PAID.ts` is the only DATETIME in C2 (C1 R5 gives it whole seconds). Every other date or datetime property, including `first_seen` and `last_seen`, is an ISO 8601 string as the source wrote it, which may be partial (`1979`, `1979-08`) or carry another precision, and is returned as stored.
- **Amounts.** `PAID.amount` is a JSON number in major units, the C2 FLOAT as stored. C1 amounts have at most two decimals, and a double holds them exactly to the cent up to about 10^13 major units; format amounts with the currency's minor units and never do accounting arithmetic on them. If the tech lead changes C2 to integer minor units at Gate 1 (the C2 open item "`PAID.amount` is a FLOAT" in [CHANGELOG.md](CHANGELOG.md)), C3's models do not change, because amounts appear only in property maps and in C4 metrics, but this paragraph and the UI's formatting do.
- **Absent and null.** Every response field is present. A field that may be empty is `T | null`; v1 fields that are always null are listed in [Null in v1](#null-in-v1). In property maps, a property the node or relationship lacks is absent, never `null` (C2 leaves absent values out).

## Models

`neonradar_contracts.api`. Every object is closed (`additionalProperties: false`) and strict: `"1"` is not a number and `1` is not `true`.

### Graph shapes

| Model | Fields | Source and rule |
|---|---|---|
| `NodeFlags` | `synthetic`, `sanctioned`, `pep`, `rca` (booleans) | The C2 flag labels `:Synthetic`, `:Sanctioned`, `:PEP`, `:RCA`. Facts a source published, never findings of NeonRadar; on `:Sanction` nodes only `synthetic` can be true |
| `GraphNode` | `id`, `labels`, `schema`, `caption`, `flags`, `properties` | A C2 node (`:Entity` or `:Sanction`). `labels` are exactly the C2 mapping labels of its `schema`, in hierarchy order (`["Entity", "LegalEntity", "Organization", "Company"]`, `["Sanction"]`), never flag labels. `schema` is the FtM schema (`Person`, `Company`, `Organization`, `PublicBody`, `LegalEntity`, `Address`, `BankAccount`, `Position`, `Sanction`). `properties`: every other C2 property of the node except `names_text`, `synthetic` (in `flags`), `topics` and `referents` (merge history, shown as `EntityDetail.provenance`); the model rejects those keys and `id`, `schema` and `caption` |
| `GraphEdge` | `id`, `type`, `source`, `target`, `properties` | A relationship built from a record: one of `OWNS`, `CONTROLS`, `CONSOLIDATES`, `DIRECTOR_OF`, `HOLDS_ACCOUNT`, `PAID`, `HAS_ADDRESS`, `REPRESENTS`, `FAMILY_OF`, `ASSOCIATE_OF`, `MEMBER_OF`, `EMPLOYED_BY`, `LINKED_TO`, `SUCCEEDED_BY`, `HOLDS_POSITION`, `SUBJECT_OF`. `FLAGS`, `PRODUCED` and `RESOLVED_TO` never appear. `properties`: every other C2 property of the relationship (`datasets`, `synthetic`, `amount`, `currency`, `ts`, `channel`, ...); the model rejects `id` and `topics` |
| `SubgraphLimits` | `max_nodes` (at least 1), `max_edges` | The caps applied when the subgraph was built. `max_edges` is 2 × `max_nodes`; edges beyond it are cut and `truncated` is true |
| `Subgraph` | `nodes`, `edges`, `truncated`, `limits` | No id repeats; every edge's `source` and `target` are nodes of the subgraph; the sizes stay within `limits`; `truncated` is true when a cap cut the result |

`Subgraph` maps one to one onto Cytoscape elements, so the UI does no graph reshaping: a node becomes `{data: {id, ...node}}` and an edge `{data: {id, source, target, ...edge}}`. C2 relationship ids never equal node ids, so the two share Cytoscape's id space safely.

`topics` stays out of every property map (7.1: no source topics other than the three flags are shown next to entities). The flags say what may be shown, in the 7.1 vocabulary ("listed in <dataset> as sanctioned", ...).

### Entities and search

An "entity" in C3 is any node with a C2 record id: an `:Entity` node or a `:Sanction` node. `GET /entities/{entity_id}` and `/network` look up both labels through their uniqueness indexes, so a `:Sanction` node reached through `SUBJECT_OF` in a network can be opened like any other node. Search covers what the full-text index covers (`LegalEntity` and `Address`) plus exact account numbers; it never returns `:Sanction` nodes.

| Model | Fields | Source and rule |
|---|---|---|
| `EntitySummary` | `id`, `schema`, `caption`, `labels`, `flags`, `countries`, `datasets` | C2 common properties; `labels` as in `GraphNode`; `datasets` holds at least one slug |
| `SearchHit` | `entity`, `score` (at least 0), `matched_name` | `score` is the full-text relevance and orders the hits of one response only; it is not comparable across queries and is never a risk measure. `matched_name` is the value from `names` that matched, or the account number for an `Account` match |
| `SearchResponse` | `query`, `items`, `total_estimate` | `total_estimate` is at least `len(items)` |
| `ProvenanceRecord` | `dataset`, `record_id`, `retrieved_at`, `source_url` | One per entry of the node's `referents` (Phase 1: the node's own id). `dataset` is the node's dataset (C1 R2: exactly one per record), `source_url` the C2 `source_url` or null, `retrieved_at` null in v1 |
| `EntityDetail` | `entity`, `names`, `properties`, `identifiers`, `provenance`, `relationship_counts`, `alerts` | See below |
| `PathRef` | `node_ids`, `edge_ids`, `effective_share_min`, `effective_share_max` | A path as C2 ids: `node_ids` start at `root_id` (ownership) or `from_id` (paths), and `edge_ids[i]` joins `node_ids[i]` and `node_ids[i + 1]`, so there is one edge fewer than nodes. The effective share (0 to 100, min not above max) is the product of the `OWNS` share bands along an ownership path, null when a hop has no band (Phase 2) |
| `OwnershipResponse` | `root_id`, `direction`, `paths`, `subgraph` | Phase 2. Every path starts at `root_id`; every node and edge id of a path is in `subgraph`, and each edge joins its two path nodes |
| `PathsResponse` | `from_id`, `to_id`, `paths`, `subgraph` | Phase 2. Every path runs from `from_id` to `to_id`; ids and edges as for ownership |

`EntityDetail`:

- `names`: C2 `names`, in original scripts.
- `properties`: the schema-specific C2 properties of the node table (for example `registration_number`, `incorporation_date`, `account_number`) plus `first_seen`, `last_seen` and `source_url` when present. The model rejects every other common property (`id`, `schema`, `caption`, `names`, `names_text`, `countries`, `topics`, `datasets`, `referents`, `synthetic`): each is a field of its own or left out.
- `identifiers`: `dict[str, list[str]]`, keyed by C2 property name. v1 keys: `registration_number`, `lei` (legal entities) and `account_number` (accounts). Each list holds the one value C2 stores; a key without a value is left out, and lists are never empty and never repeat a value. Phase 2 lists further values from `:SourceRecord` and may add keys (a minor change); clients ignore keys they do not know. So C2 can keep single-valued, indexed identifier properties while C3 needs no breaking change when entity resolution merges records.
- `provenance`: at least one record.
- `relationship_counts`: for each of the 16 record-built relationship types (`FLAGS`, `PRODUCED` and `RESOLVED_TO` are not counted), the number of relationships of that type touching the node in either direction; types with none are left out.
- `alerts`: the summaries of the alerts that flag the node (`FLAGS`), in queue order, at most 50; `GET /alerts?entity_id=` lists them all.

`GET /entities/{entity_id}` accepts a canonical id or any id in `referents` (Phase 2 finds record ids through `:SourceRecord` and `RESOLVED_TO`).

`GET /entities/{entity_id}/network` returns the node and its neighbours up to `depth` hops over the requested relationship types, in either direction, keeping only `:Entity` and `:Sanction` nodes and the relationships between the nodes it keeps, with at most `max_nodes` nodes and `2 × max_nodes` edges (`truncated` says when a cap cut it).

### Alerts

| Model | Fields | Source and rule |
|---|---|---|
| `AlertSummary` | `alert_id`, `typology`, `priority`, `pattern_strength`, `headline`, `created_at`, `subject_ids`, `involves_real_entities`, `synthetic_activity` | The `:Alert` scalar properties (C2), with `subject_ids` from the alert's subjects (the `FLAGS` targets), in the order of the C4 `subjects`. Types as in C4 |
| `AlertPage` | `items`, `next_cursor` | See pagination below |
| `AlertDetail` | `alert`, `evidence` | `alert` is the complete C4 `Alert`, parsed and validated from the `payload` property. `evidence` is a `Subgraph` holding every node of `alert.evidence.node_ids` and `alert.subjects`, every relationship of `alert.evidence.edge_ids`, and the `HOLDS_ACCOUNT` relationships between those nodes, so a holder that is a subject but not an evidence node is still connected. `evidence` is never truncated (`truncated` false; its `limits` are at least its sizes). The model checks both, and that every evidence id and subject is present |

A stored payload that no longer validates as C4 (for example an alert written under a newer C4 version, or edited by hand) is answered with a `500` problem whose detail says the stored alert does not validate and to re-run detection (`neonradar detect run`); the API never serves an alert it cannot validate.

The API adds no wording to an alert: the UI shows the standing disclaimer from `MetaResponse.disclaimers` (the alert names `standing-v1`), and words the alert from `involves_real_entities` and `synthetic_activity` as C4 describes.

**Order and pagination** (`GET /alerts`). Alerts are ordered by priority (`high`, `medium`, `low`), then `pattern_strength` descending, then `alert_id` ascending, which is a total, stable order. Pass `next_cursor` back unchanged, with the same filters, to get the next page; it is null on the last page. The cursor is opaque and belongs to its filters: a malformed cursor or one from other filters gets a `422` problem. Filters combine with AND; a filter that matches nothing gives an empty page, not `404`.

### Typologies

| Model | Fields | Source and rule |
|---|---|---|
| `Citation` | `key`, `title`, `publisher`, `year`, `url` | An entry of `docs/sources/bibliography.yaml`; `year` is null for living documents (the bibliography's `year: null`). Keys the bibliography lacks are left out (`scripts/check_citations.py` prevents them) |
| `TypologySummary` | `slug`, `name`, `tier`, `status`, `summary`, `detector_available` | `detect/typologies/<slug>.yaml` (`load_catalog()`); `tier` and `status` take the catalog's values (`neonradar_detect.catalog` imports them from this contract); `detector_available` is true when the file names a detector. The list is sorted by slug |
| `TypologyDetail` | the summary fields plus `definition_markdown`, `graph_pattern`, `citations`, `parameters`, `false_positives` | `definition_markdown` is the explainer in `docs/typologies/`, null when it does not exist; `citations` follow the file's order; `parameters` are the catalog parameters as JSON |

### Meta and health

| Model | Fields | Source and rule |
|---|---|---|
| `DatasetInfo` | `slug`, `title`, `licence_id`, `licence_url`, `attribution`, `synthetic`, `personal_data`, `record_count`, `loaded_at` | One per dataset of `contracts/datasets.yaml` (`licence.id`, `licence.url`). `record_count`: the number of nodes whose `datasets` contain the slug, 0 when nothing from it is loaded, null when the graph cannot be read. `loaded_at`: null in v1 |
| `Disclaimers` | `standing`, `synthetic_demo`, `real_data` | `contracts/wording/` through `load_disclaimer()`, verbatim from PHASE-1.md 7.1 |
| `GraphCounts` | `nodes_by_label`, `relationships_by_type` | `apoc.meta.stats()`; both empty when the graph cannot be read |
| `MetaResponse` | `app_version`, `contracts_version`, `schema_version`, `datasets`, `disclaimers`, `counts` | `app_version` is the API package version (a PEP 440 version such as `0.1.0` or `1.0.0rc1`), `contracts_version` is `neonradar_contracts.versions.CONTRACTS`, and `schema_version` is `versions.GRAPH_SCHEMA` (`"1.0.0"`), the C2 version the API reads. The migrations applied to the database (`:SchemaMigration` ids such as `0001_init`) are not reported; `neonradar graph migrate` checks them |
| `Neo4jStatus` | `connected`, `version`, `edition` | From `dbms.components()` (the `Neo4j Kernel` row) |
| `HealthResponse` | `status`, `neo4j`, `apoc_version`, `gds_version` | `ok` exactly when Neo4j answers and both `apoc.version()` and `gds.version()` answer, otherwise `degraded` (the rule of `make smoke`) |

`GET /meta` answers 200 even when Neo4j cannot be read, so the disclaimers are always available: every `record_count` is then null and both count maps are empty. If any `record_count` is null, the UI shows the real data notice. Otherwise it shows the synthetic demo notice only when every dataset with `record_count` above 0 is synthetic (M1.9d's notice rule; its unit tests cover the null case).

`GET /health` answers 200 for both statuses, so a caller (the Compose health check in M1.9e) reads `status` from the body.

### Copilot (Phase 4)

| Model | Fields | Rule |
|---|---|---|
| `CopilotRequest` | `question`, `context_entity_ids` | `question` 1 to 500 characters; at most 20 node ids, default `[]` |
| `CopilotAnswer` | `status`, `answer_text`, `template_id`, `cypher`, `parameters`, `subgraph`, `refusal_reason` | `answered` needs `answer_text`, `cypher`, `parameters` and `subgraph` (the evidence) and no `refusal_reason`; `refused` and `unsupported` need a `refusal_reason` and no `answer_text`. `template_id` names the template used (null when none) |

The model checks the conditional rules; the JSON Schema shows the fields only.

## Errors

Every error is an RFC 9457 problem (`application/problem+json`), the `Problem` model:

| Field | Value |
|---|---|
| `type` | `about:blank` in v1: the HTTP status says what kind of problem it is |
| `title` | The HTTP reason phrase (`Not Found`, `Unprocessable Content`, ...) |
| `status` | The HTTP status code |
| `detail` | A sentence for people. For `422`, the failed checks as `<location>: <message>` joined with `; ` (for example `query.q: String should have at least 2 characters`), without echoing the input: an unknown body key is reported at its parent as `body: unknown keys are not permitted`, without the key itself. For `405`, a sentence pointing to the `Allow` header. For `501`, the method, the route and the milestone or phase that implements it |
| `instance` | The request path, without the query string |

| Status | When |
|---|---|
| 404 | An unknown route, or an id that matches nothing |
| 405 | A method the route does not have (with an `Allow` header) |
| 422 | A parameter, path or body that breaks a rule above, or a bad cursor |
| 500 | An unexpected error, or a stored alert that no longer validates as C4 (re-run detection); `detail` is generic or names the fix, and the API log has the details |
| 501 | A route not implemented yet |
| 503 | Neo4j is not configured (no `NEO4J_PASSWORD`, or a `NEO4J_URI` the driver cannot use), not reachable, refuses the credentials, or has no database named `NEO4J_DATABASE`; `detail` never shows the driver's message |

There is no `errors` extension member in v1; adding typed problem `type` URIs or extension members later is a minor change.

A CORS preflight (`OPTIONS`) from an origin other than `http://localhost:5173` is rejected by Starlette's CORS middleware with `400` and a `text/plain` body, not a problem; browsers do not expose that response to the page, which sees a failed request.

## Null in v1

These fields are nullable in the models. The first two are null on every response in v1; the other two are null only in the case named.

| Field | Why | When it gets a value |
|---|---|---|
| `ProvenanceRecord.retrieved_at` | C2 stores no retrieval time (manifests do, but they are not loaded) | Phase 2, from `:SourceRecord` |
| `DatasetInfo.loaded_at` | C2 records no load | When a load record joins C2 (a minor change) |
| `DatasetInfo.record_count` | Only when the graph cannot be read | - |
| `TypologyDetail.definition_markdown` | Only when the explainer file does not exist | - |

## Versioning and changes

- C3 is `neonradar_contracts.versions.API` (`"1.0.0"`), which is also the OpenAPI `info.version`. The base path `/api/v1` and the snapshot `openapi/v1.json` cover every 1.x release.
- The rules of PHASE-1.md 5.0 apply: a patch changes wording or examples; a minor change adds an optional field, a parameter with a default, an endpoint, an enum value in a response, a dictionary key or a problem response (clients ignore what they do not know); a major change renames, removes or changes the meaning of anything, and gets `/api/v2` with `openapi/v2.json`.
- `AlertDetail` embeds the C4 `Alert`, so a C4 change regenerates `openapi/v1.json` too and is a C3 change of the same kind.
- `additionalProperties: false` and the enums describe what this version's server emits; clients must not reject unknown fields, dictionary keys or enum values, so that minor releases do not break them.
- A model or route change regenerates the snapshot in the same pull request (`make contracts`).

## The OpenAPI snapshot

- `neonradar contracts export` writes `contracts/openapi/v1.json` from `create_app().openapi()` with sorted keys and two-space indentation, next to the JSON Schemas. The contracts package cannot import the API, so the command line adds the document to the generated files it exports and checks.
- `neonradar contracts check` exports to a temporary folder and fails on any difference, including a stray file in `contracts/openapi/`.
- `api/tests/test_openapi_contract.py` (marker `contract`) compares the running app, and the document it serves at `/api/v1/openapi.json`, with the file, and checks that every error response is a `Problem` as `application/problem+json` only, that no FastAPI default validation schema is left, that every object is closed and that the limits are those of 5.3.
- The snapshot is generator output: a FastAPI or pydantic upgrade can change it without a model change. `uv.lock` pins exact versions; an upgrade pull request regenerates the snapshot and is reviewed as a contract change.

## TypeScript types for the UI

The UI never writes API types by hand (`.claude/rules/frontend.md`). M1.9d adds the script `gen:api` (`openapi-typescript ../contracts/openapi/v1.json -o src/api/schema.d.ts`); run `npm run --prefix ui gen:api` after every snapshot change and commit the result; M1.9d's acceptance checks that the committed file is exactly what the script writes. Nullable fields come out as `T | null` and every response field is required, because response models have no defaults.

## Example

`contracts/examples/c3/subgraph.json`, the evidence subgraph of the C4 example alert, shortened here to one account, the holder and two relationships:

```json
{
  "nodes": [
    {"id": "syn-acct-0007", "labels": ["Entity", "Account"], "schema": "BankAccount", "caption": "NRSYN0000000007",
     "flags": {"synthetic": true, "sanctioned": false, "pep": false, "rca": false},
     "properties": {"account_number": "NRSYN0000000007", "account_kind": "customer", "bank_name": "Synthetic Bank One",
                    "countries": [], "currency": "EUR", "datasets": ["nr_synthetic"], "names": []}},
    {"id": "syn-co-0003", "labels": ["Entity", "LegalEntity", "Organization", "Company"], "schema": "Company",
     "caption": "Fenwhistle Holdings Ltd", "flags": {"synthetic": true, "sanctioned": false, "pep": false, "rca": false},
     "properties": {"countries": ["gb"], "datasets": ["nr_synthetic"], "incorporation_date": "2018-06-11", "jurisdiction": "gb",
                    "names": ["Fenwhistle Holdings Ltd"], "registration_number": "SYN00003"}}
  ],
  "edges": [
    {"id": "syn-payment-000104", "type": "PAID", "source": "syn-acct-0021", "target": "syn-acct-0007",
     "properties": {"amount": 115200.0, "channel": "wire", "currency": "EUR", "datasets": ["nr_synthetic"], "synthetic": true,
                    "ts": "2026-03-08T16:40:00Z"}},
    {"id": "syn-ownership-0007", "type": "HOLDS_ACCOUNT", "source": "syn-co-0003", "target": "syn-acct-0007",
     "properties": {"datasets": ["nr_synthetic"], "role": "account holder", "synthetic": true}}
  ],
  "truncated": false,
  "limits": {"max_nodes": 200, "max_edges": 400}
}
```

(The shortened version is not valid on its own: the `PAID` edge starts at `syn-acct-0021`, which the full file includes.)
