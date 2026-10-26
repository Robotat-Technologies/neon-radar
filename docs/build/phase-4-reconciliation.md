# Phase 4 reconciliation

| | |
|---|---|
| File | `docs/build/phase-4-reconciliation.md` (PHASE-4.md M4.0 deliverable 1) |
| Reconciled against | `main` at `43a8a3e` (22 October 2026, after M3.0 merged in #48, with M2.0 #45, M2.2 #47 and M2.8 #49 before it). The open contract pull requests #59 (M2.1a), #60 (M2.1c, draft) and #61 (M2.1b, draft) were looked at but not relied on |
| Written by | The M4.0 build agent; the tech lead owns it |
| Gate 1 | **Not passed** (operator decision OD-23: Phase 4 is seeded before Gate 1). No tag `contracts-v1.0.0`, `v1.1.0` or `v1.2.0` on the remote; `neonradar_contracts.versions` gives `1.0.0` for every contract |
| Method | Reading the code on `main` and the command line's `--help`, and running read-only Python on the committed contracts (no Neo4j, no network, no real data). Phase 4 code was compared with `docs/build/PHASE-4-CODE.md` as committed; nothing from the code book beyond M4.0's two files was copied into the repository |

PHASE-4.md and its code book were written on 19 October, before Gate 1, against a prototype that stood in for the Phase 1 and Phase 2 seams (PHASE-4.md 3.4). This file records, for every seam of PHASE-4.md 2.10 and every item of 0.6, what the repository has today and what the milestone that adapts it will do. Each Phase 4 milestone that adapts a seam checks it again and appends what it finds here (PHASE-4.md 2.2 step 2).

Classes: **M** mechanical: the adapting milestone adapts and, for a verbatim file, records a deviation in `docs/build/phase-4-deviations.json` (2.2 step 6b). **Q** behavioural: a question for the person named; the milestone in the row stops and asks (2.5) unless the question has been answered. **P** pending: depends on work that has not merged, written "pending #n" or "pending M2.x/M3.x", with the Phase 4 milestone that checks it again. **D** decided in this pull request. **OK** matches the spec.

## 1. What Phase 4 needs from Phases 1 to 3 (PHASE-4.md 0.6)

### 1.1 Phase 1

| PHASE-4.md 0.6 expects | On `main` | Status |
|---|---|---|
| C3 1.0.0 models in `contracts/src/neonradar_contracts/api.py` | Present; section 2.1 lists the fields and the three differences that matter (A1 to A4) | OK, with A1 to A4 |
| `create_app()` with its problem handlers and the 501 stub of `POST /api/v1/copilot/ask` | `api/src/neonradar_api/main.py:236`, `problems.install(app)`; the stub `ask_copilot` at `main.py:204` (section 2.2) | OK, with F1 to F6 |
| `GET /api/v1/meta` with each dataset's `loaded_at` | `DatasetInfo.loaded_at: UtcTime \| None` (required, nullable); `reference.meta()` always sets it to `None` ("null in v1") | OK for the field. **P**: a date of the loaded data waits for Phase 2's loader (M2.11); Phase 5 shows it |
| The OpenAPI snapshot and its contract test, the UI types | `contracts/openapi/v1.json` (`info.version` 1.0.0, 12 operations), `api/tests/test_openapi_contract.py` (`test_the_app_matches_the_committed_snapshot` and 7 more), `npm run --prefix ui gen:api` (`openapi-typescript ../contracts/openapi/v1.json -o src/api/schema.d.ts`) | OK |
| `neonradar api serve` on 127.0.0.1 and the Vite proxy of `/api` | `cli/src/neonradar_cli/api.py:13`: `uvicorn.run("neonradar_api.main:create_app", factory=True, host="127.0.0.1", port=port)`, option `--port` only; `ui/vite.config.ts`: `/api` to `http://127.0.0.1:8000`, `changeOrigin: false` | OK; M4.1 adds `--dev`, `--host` and the log config (X1) |
| `get_driver()` and the `.env` rule | `graph/src/neonradar_graph/client.py:38`, section 2.3 | OK |
| The typer CLI | `cli/src/neonradar_cli/main.py:33-43` | OK (I1) |
| The wording lint over `contracts/wording/forbidden-terms.txt` | `neonradar_contracts.wording.find_forbidden(text, mask=()) -> list[str]` (23 patterns); `scripts/check_wording.py` in `make hygiene` | OK. Phase 4 calls Phase 3's `wording_lint.violations` (D1), pending M3.2 |
| The `entity_names` full-text index | `graph/schema/migrations/0001_init.cypher:30`: `FOR (n:LegalEntity\|Address) ON EACH [n.names_text]`, analyzer `standard-no-stop-words` | OK (G3) |
| The dataset register and `load_registry()`, `validate_batch()` | Section 2.8 and 2.13 | OK |
| ADR-0008 and the draft of ADR-0010 | Both in `docs/decisions/`, status proposed (Gate 1 sign-off pending, OD-5) | OK; M4.8 completes ADR-0010 |

### 1.2 Phase 2

| Phase 2 milestone | Needed before | On `main` | Status |
|---|---|---|---|
| M2.0: the Cypher linter and the real-data guard hook | M4.0 | Merged (#45) | Met |
| M2.1a to M2.1c: C1 1.1.0, C2 1.1.0, C3 1.1.0 and their snapshot | M4.2 (the C3 1.1.0 base) | Open: #59 (M2.1a), #61 (M2.1b, draft), #60 (M2.1c, draft); they wait for the tag `contracts-v1.0.0` | **P**: pending #59, #60, #61 and the tag; M4.2 checks again |
| M2.11: the resolution-aware loader, `:SourceRecord` ids, `neonradar_graph.instances`, the real-data instance | M4.4, M4.5 | Not started. No `instances` module; `graph load` takes paths and `--strict/--no-strict` only | **P**: pending M2.11; M4.4 and M4.5 check again |
| M2.12: `ownership()` and `paths()`, their query files, the ownership, paths and resolution routes, `api serve --real` | M4.1, M4.4 | Not started. The ownership and paths routes are Phase 1's 501 stubs ("Phase 2"); no `neonradar_graph.ownership`, no `graph/src/neonradar_graph/queries/` | **P**: pending M2.12; M4.1 (its header) and M4.4 check again |
| PHASE-2.md 7.2 wording rules | M4.3a | In PHASE-2.md; the never-write phrases reach `forbidden-terms.txt` through Phase 2's own milestones | **P** for the phrases Phase 2 adds; M4.3a checks |

### 1.3 Phase 3

| Phase 3 milestone | Needed before | On `main` | Status |
|---|---|---|---|
| M3.0: `scripts/spec_extract.py` and the code book conventions | M4.0 | Merged (#48) | Met |
| M3.1: C2 1.2.0 (`:DetectionRun` and `:Alert` properties) and the tag `contracts-v1.2.0` | M4.2 | Not started | **P**: pending M3.1 and the tag; M4.2 checks again (L2) |
| M3.2: `graphrows`, `memgraph`, the typology catalog with `shape_name`, the `wording` helpers, `wording_lint.violations`, `alerts.DATASET_NOTES`, the runner, `detect run --window` | M4.2 | Not started; every name is absent from `detect/` (section 2.6) | **P**: pending M3.2; M4.2 and M4.3a check the names |
| M3.3: the synthetic writer (`writer.write_part`, `writer.items`) | M4.4 | Not started | **P**: pending M3.3; M4.4 checks (W1) |
| M3.2 and M3.5a to M3.5f: every detector | M4.3a fixture check, M4.4 detection check | One detector on `main`: `circular_flow` 0.1.0 (Phase 1) | **P**: the two checks skip with the missing typologies named (PHASE-4.md 2.9); M4.10 runs them again |

## 2. The seams (PHASE-4.md 2.10)

### 2.1 C3 models (M4.2)

Every model on `main` subclasses `_Model` (`ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)`) or `_WithSchema` (the same, with `schema_` under the alias `schema`, `validate_by_alias=True`, `validate_by_name=False`). The code book's M4.2 listing (a reference file) declares plain `BaseModel`s.

| Model | Fields on `main` | Phase 4 expects | Class |
|---|---|---|---|
| `CopilotRequest` | `question: str` (1 to 500); `context_entity_ids: list[EntityId]` (C1 id pattern, at most `MAX_CONTEXT_ENTITIES = 20`) = `[]`; unknown fields already refused (`extra="forbid"`) | context ids `list[str (1 to 200)]`, at most 5; `template_id`, `slots`; unknown fields refused | **A1 (Q, tech lead, M4.2).** Two facts differ from 5.0's issue text: 1.0.0 already refuses unknown fields, and its context ids already follow the C1 id pattern. Keep the pattern and lower the cap to 5 (stricter), or take the listing's plain 1-to-200 strings (looser)? Recommended: keep the pattern, cap at 5, and correct the issue text |
| `CopilotAnswer` | `status: "answered" \| "refused" \| "unsupported"`; `answer_text`, `template_id`, `cypher: str \| None`; `parameters: dict \| None`; `subgraph: Subgraph \| None`; `refusal_reason: str \| None`; all required. A validator: `answered` needs `answer_text`, `cypher`, `parameters` and `subgraph`; `refused` and `unsupported` need a `refusal_reason` and **no** `answer_text` | the 1.2.0 fields with defaults, and the `needs_clarification` status; "`refusal_reason` is the same fixed text as `answer_text`" (5.3); refusals, clarifications and unsupported answers carry no queries and null `cypher` and `parameters` | **A2 (Q, tech lead, M4.2).** The 1.0.0 validator refuses every refusal the copilot writes (checked: `CopilotAnswer(status="refused", answer_text="x", ..., refusal_reason="x")` raises "a refused question needs a refusal_reason and no answer_text"). M4.2 must replace the validator with 1.2.0's rules; that changes a frozen contract's behaviour, so the contract-change issue should say so |
| `GraphNode` | `id: EntityId`, `labels: list[NodeLabel]` (at least 1), `schema`, `caption`, `flags: NodeFlags`, `properties`. A validator: `labels` must equal the C2 mapping's labels for the schema, in order (`Person`: `["Entity", "LegalEntity", "Person"]`; flag labels such as `Sanctioned` are not in it), and `properties` must not hold `id`, `schema`, `caption`, `names_text`, `synthetic`, `topics` or `referents` | `evidence.graph_node` (verbatim, M4.3a) passes `sorted(node.labels)` and every property except `id`, `caption`, `schema`, `names_text`; `evidence.PERSON_PROPERTIES` keeps `referents`, `synthetic` and `topics` | **A3 (Q, tech lead and data steward, M4.2 then M4.3a).** As written, the copilot's evidence fails C3 1.0.0's node rules (sorted labels with flag labels; three left-out properties). Recommended: keep the frozen rules, and record a mechanical deviation in `evidence.py` (labels from the C2 mapping, the left-out keys dropped), which keeps less of a person, never more. Any verbatim test that expects those keys in `properties` is a stop-and-ask (2.5 item 11) |
| `GraphEdge` | `id`, `type` (16 C2 types), `source`, `target`, `properties`; `properties` must not hold `id` or `topics` | `evidence.graph_edge` drops `id` only | **A4 (M, M4.3a)**: drop `topics` too (same deviation as A3) |
| `SubgraphLimits`, `Subgraph` | A model `SubgraphLimits(max_nodes >= 1, max_edges >= 2)`, with `max_edges == 2 * max_nodes`; `Subgraph(nodes, edges, truncated, limits)` checks distinct ids, closed edges and the limits | `SubgraphLimits(max_nodes=500, max_edges=1000)` for the copilot | OK (the ratio holds) |
| `AlertSummary` | `alert_id`, `typology`, `priority`, `pattern_strength`, `headline`, `created_at`, `subject_ids`, `involves_real_entities`, `synthetic_activity` | `+ shape_name: str \| None = None`, `display_name: str` | OK; M4.2 fills both in `api/src/neonradar_api/alerts.py:98` (`_summary`), the only builder, and the entity route reuses it. **P**: `shape_name` comes from Phase 3's catalog (pending M3.2) |
| `AlertDetail` | `alert: Alert` (C4), `evidence: Subgraph`, with its checks | unchanged | OK |
| `TypologySummary`, `TypologyDetail` | `slug`, `name`, `tier`, `status`, `summary`, `detector_available`; `TypologyDetail(TypologySummary)` adds `definition_markdown`, `graph_pattern`, `citations`, `parameters`, `false_positives` | `+ shape_name` on the summary, inherited by the detail | OK (the detail subclasses the summary); built in `api/src/neonradar_api/reference.py:96` from Phase 1's `TypologyFile`, which has no `shape_name` until M3.2 (**P**) |
| `Problem` | `type`, `title`, `status` (400 to 599), `detail`, `instance`; closed | the listing's `Problem` allows extra fields | **A5 (M, M4.1)**: `hardening.py` sends the five fields only; keep the closed model |
| `neonradar_contracts.versions` | `RECORD`, `GRAPH_SCHEMA`, `API`, `ALERT`, `CONTRACTS` all `"1.0.0"` | `API = "1.2.0"`, `CONTRACTS = "1.3.0"` after M4.2 | **P**: pending the 1.1.0 and 1.2.0 bumps (M2.1a to M2.1c, M3.1) |
| `contracts/pyproject.toml` | `pydantic>=2.14,<3` (lock 2.14.1) | `>=2.14,<2.15` (M4.2) | OK (M4.2 narrows it) |

### 2.2 App factory (M4.1, M4.2, M4.5)

| Fact on `main` | Phase 4 expects | Class |
|---|---|---|
| `create_app(graph=None, files=None, allowed_hosts=None) -> FastAPI`; no development setting. It sets `openapi_url="/api/v1/openapi.json"`, no `/docs` in the schema (an offline docs route), `generate_unique_id_function` returning `route.name`, `telemetry=TELEMETRY_OFF` (all off, `auto_configure: False`), and `app.state.graph`, `app.state.files` | `create_app(*, dev=False)` and `harden(app, dev=...)` | **F1 (M, M4.1)**: add `dev` as a keyword after the existing parameters; telemetry already matches 3.5 item 4 |
| `TrustedHostMiddleware(allowed_hosts=ApiSettings().allowed_hosts, www_redirect=False)` is already added last (runs first); `ApiSettings` (`NR_` prefix) allows `localhost`, `127.0.0.1`, `api` | `harden()` adds its own trusted-host check with `127.0.0.1`, `localhost`, `[::1]` and `api` | **F2 (M, M4.1)**: one trusted-host layer, not two; `[::1]` is new |
| `CORSMiddleware(allow_origins=["http://localhost:5173"], allow_methods=["GET","POST"], allow_headers=["content-type"])` in every mode | CORS only for `api serve --dev` (3.5 item 6) | OK: the planned change (M4.1) |
| `problems.install(app)` registers handlers for `ProblemError`, `HTTPException`, `RequestValidationError` (422), `GraphUnavailable` (503), `RepoRootNotFound` (500) and `Exception` (500, "Internal error; the API log has the details."), all as `application/problem+json`. The 422 detail lists locations and messages only, never the input (`test_an_unknown_body_key_is_reported_without_echoing_it`) | an `HTTPException` becomes a problem body; a 501-character question gets a 422 that does not repeat it | OK. **F3 (M, M4.1)**: Phase 1's generic handler and `hardening`'s "contain" layer overlap; keep one fixed 500 whose log line names only the exception class and route template |
| The OpenAPI document already documents every 4xx and 5xx as `application/problem+json` with `Problem` (`problems.responses()`); `HTTPValidationError` and `ValidationError` do not appear | `install_problem_openapi` moves them there (5.3) | OK: already true; M4.2's `install_problem_openapi` changes nothing for the existing routes, so the snapshot diff of M4.2 holds only the new routes and models |
| One router, `APIRouter(prefix="/api/v1")`, 12 operations; operation ids are the handler names | the copilot route's id `copilot_ask` | OK: 5.3 renames `ask_copilot` to `copilot_ask`; `test_every_operation_is_under_the_v1_prefix_with_a_readable_id` counts 12 and M4.2 updates it |
| The 501 stub: `@router.post("/copilot/ask", tags=["copilot"], responses=responses(422, 501, 503)) def ask_copilot(request, body: CopilotRequest) -> CopilotAnswer: not_implemented(request, PHASE_4)`; no explicit `response_model` | the service looked up after validation (3.2 trap 25) | OK: the body is already validated before the 501 |
| Alert summaries: `alerts._summary(row)` from the `:Alert` node's properties; typology summaries: `reference._summary(TypologyFile)` | M4.2 fills `shape_name` and `display_name` | **P** pending M3.2 (the catalog) |

### 2.3 Graph client (M4.5)

`get_driver(settings: Neo4jSettings | None = None, *, max_transaction_retry_time: float = 30.0) -> neo4j.Driver` (`graph/src/neonradar_graph/client.py:38`), with telemetry off and a 10-second connection timeout. `Neo4jSettings` (`NEO4J_` prefix): `uri = "bolt://localhost:7687"`, `user = "neo4j"`, `password: SecretStr` (required), `database = "neo4j"`. The driver names no database: every caller passes one (`settings.database` in the CLI; `database_=` with `routing_=READ` in `api/src/neonradar_api/graph.py:54`, with no timeout; `database="neo4j"` defaults in the loader, `migrate`, `smoke` and `onboarding`; positional in the detect runner). **G1 (OK)**: a sync 6.x driver, database `neo4j` on the default instance. **G2 (P, pending M2.11)**: `neonradar_graph.instances` and the `realdata` database. **G3 (M, M4.4)**: `entity_names` covers `LegalEntity` and `Address` over `names_text` only, so the port filters labels after the full-text call, and an account number is found by its property, never through the index.

### 2.4 Settings (M4.5)

`client.py:20-21`: `REPO_ROOT = Path(__file__).resolve().parents[3]`, `ENV_FILE = REPO_ROOT / ".env"`, with `extra="ignore"`. `api/src/neonradar_api/copilot_setup.py` will sit at the same depth (`api/src/neonradar_api/`), so its `parents[3]` is the repository root too. **S1 (OK).** `ApiSettings` already reads `NR_` variables, so `CopilotSettings`' `NR_COPILOT_` prefix does not collide.

### 2.5 Ownership and paths (M4.4)

**O1 (P, pending M2.12).** Nothing to check yet: no `neonradar_graph.ownership`, no `ownership_up.cypher`, `ownership_down.cypher`, `paths.cypher` or `resolve_id.cypher`. `OwnershipResponse(root_id, direction, paths, subgraph)` and `PathsResponse(from_id, to_id, paths, subgraph)` exist in C3 1.0.0, with `PathRef(node_ids, edge_ids, effective_share_min, effective_share_max)`. M4.4 records whether the functions take a database or an instance.

### 2.6 Detection code (M4.2, M4.3a)

**D1 (P, pending M3.2).** None of the names Phase 4 imports exists on `main`: `graphrows.from_records`, `memgraph.MemGraph`, `Node`, `Rel`, `wording.edge_sentence`, `band`, `counted`, `dates`, `day`, `money`, `model.EdgeInfo`, `alerts.DATASET_NOTES`, `wording_lint.violations`, `catalog.load`, `catalog.params_for`, `catalog.Typology`, `runner.detectors`, `runner.run_detection`, `memsource.MemSource`, `source.Window`. Each is in `PHASE-3-CODE.md` with the signature the Phase 4 book uses (for example `from_records(records: list[dict[str, Any]]) -> MemGraph`, `violations(text: str, masked: tuple[str, ...] = ()) -> list[str]`, `load(directory: Path = CATALOG_DIR) -> dict[str, Typology]`, `detectors(catalog) -> dict[str, ModuleType]`). Today `detect/` holds Phase 1's `catalog.py` (`TypologyFile`, `load_catalog()`), `runner.py` (`DETECTORS` is a constant, not a function; `run(driver, database, *, typology, run_id, ...)`), `wording.py` (`render_headline`, `format_amount`, `format_day`, ...), `alerts.py` and `circular_flow` 0.1.0; M3.2 replaces them (phase-3-reconciliation.md 2.2 to 2.4). Near-misses to avoid: `neonradar_contracts.alert.Window` is C4's evidence window, not `source.Window`.

### 2.7 Synthetic writer (M4.4)

**W1 (P, pending M3.3).** `ingest/src/neonradar_ingest/synth/` has no `writer.py`. `PHASE-3-CODE.md` gives `items(records) -> Iterator[tuple[str, str]]` and `write_part(...)`; M4.4 checks the keywords `seed=` and `git_sha=`.

### 2.8 C1 validator (M4.3a)

`validate_batch(records: Iterable[dict[str, Any]], strict: bool) -> list[RecordIssue]` (`contracts/src/neonradar_contracts/records.py:452`); valid records give `[]`; `RecordIssue(rule, record_id, message)`. `SYNTHETIC_DATASET = "nr_synthetic"`. **V1 (OK)**: `validate_batch(records, strict=True)` works as the test calls it. **V2 (P, pending M2.1a, #59)**: the fixture's records are C1 1.1.0; until C1 1.1.0 merges, a 1.1.0-only feature in them fails here. M4.3a checks.

### 2.9 Loader and detection commands (M4.4)

| Command | On `main` | Phase 4 expects (7.3.6) | Class |
|---|---|---|---|
| `neonradar graph migrate` | present | present | OK |
| `neonradar graph load` | `PATHS...` (C1 files or folders), `--strict/--no-strict` (default strict), `--timeout` | `graph load --strict` over a part folder | OK; **L1 (P, pending M2.11)**: the resolution-aware loader that writes `:SourceRecord` |
| `neonradar detect run` | `--typology`, `--run-id`, `--timeout` | `--run-id` and `--window` | **L2 (P, pending M3.2)**: no `--window` |
| `:DetectionRun` (runner.py) | `run_id` (`run-<UTC yyyymmddThhmmss>-<4 hex>`), `started_at` and `finished_at` (strings, `YYYY-MM-DDTHH:MM:SSZ`), `typologies` (list of slugs), `detectors` (a JSON string: list of `{"name", "version"}`), `alert_count` (int), `status` (`ok` or `failed`); no `summary`, `profile`, window or `params_sha256` | `RunSummary` accepts `ok` and `failed` and a list of names and versions; times as UTC strings or temporal values; `RunDetail` parses `summary` | OK for the Phase 1 properties (strings, so no temporal conversion is needed today). **P** pending M3.1 (C2 1.2.0) for `summary`, `profile`, the window and `params_sha256`; M4.5 checks again |

### 2.10 Cypher lint (M4.3a)

`Makefile:43`: `cypher-lint` runs `node scripts/cypher-lint/lint.mjs` with no argument; `lint.mjs:11` lints `['graph', 'detect', 'api']` by default, or the folders it is given. **Y1 (M, M4.3a)**: pass `graph detect api copilot` in the target, as 2.10 writes.

### 2.11 CLI (M4.5)

`cli/src/neonradar_cli/main.py:33-43`: `app.add_typer(<module>.app, name="<group>")` for api, contracts, data, detect, docs, gate, graph, ingest, onboarding, spike and synth; `doctor` is a command. No `copilot` group. **I1 (OK)**: `app.add_typer(copilot_cmd.app, name="copilot")`.

### 2.12 API test clients (M4.1)

`api/tests/conftest.py` has no client fixture; an autouse fixture sets `NR_ALLOWED_HOSTS` to `localhost`, `127.0.0.1`, `api` and `testserver`, because `TestClient` sends `Host: testserver`. Seven test files build `TestClient`s, all on the default base URL except one (`test_routes.py:228`, `http://localhost:8000`). **T1 (M, M4.1)**: move the test clients to `http://127.0.0.1` (3.2 trap 6) and drop `testserver` from the test hosts, or keep the conftest allowance; either way no Phase 1 or 2 assertion changes beyond the base URL (2.5 item 5).

### 2.13 Dataset titles (M4.5)

`load_registry(path: Path = REGISTRY_PATH) -> Registry` (cached); `Registry.datasets: list[Dataset]`, each with `slug` and `title` (and `get(slug)`). `nr_synthetic` is registered ("NeonRadar synthetic data", prefix `syn`). **N1 (M, M4.5)**: `titles = {d.slug: d.title for d in load_registry().datasets}`.

### 2.14 Guard hook (M4.0, this pull request)

**H1 (D).** `.claude/hooks/guard_real_data.py` closes `data/cache/heldout` as it closes the holdout folder (Read, Grep, Glob and every shell command, relative or absolute, in any letter case), and blocks the human-only commands of M4.0 deliverable 5. Section 4 lists what was added beyond the spec.

## 3. Other facts M4.0 was asked to record

| Item | On `main` | Who acts | Class |
|---|---|---|---|
| `uv run neonradar api serve --help` | `--port` (1 to 65535, default 8000) only; uvicorn's default logging and access log, which write full paths and query strings | M4.1 (`--dev`, `--host`, `log_config=hardening.log_config()`, `access_log=False`) | **X1 (OK)**: the planned change (3.5 item 7) |
| `api/Dockerfile` | syncs `--package neonradar-api` after copying every member's `pyproject.toml` (api, cli, contracts, copilot, detect, graph, ingest, keys, resolve); `CMD ["uv","run","--no-sync","uvicorn","neonradar_api.main:create_app","--factory","--host","0.0.0.0","--port","8000"]` | M4.1: `neonradar api serve --host 0.0.0.0 --port 8000`; the image must then hold `neonradar-cli` too | **X2 (M, M4.1)**: `--package neonradar-api` does not install the CLI; add it to the sync or the image cannot run `neonradar` |
| Vite proxy | `changeOrigin: false`: the browser's Host (`localhost:5173`) reaches the API | M4.1 | OK: `localhost` is a trusted host |
| `ui/nginx.conf` | `access_log /dev/stdout` for every location; `/api/` proxied with `proxy_set_header Host $host` | M4.1 (`access_log off;` for `/api/`, 7.6.5) | OK: the planned change |
| `compose.yaml` Neo4j services | `neo4j` and `neo4j-real`: image `neo4j:5.26.32-community`, `NEO4J_PLUGINS: '["apoc"]'`, `NEO4J_dbms_security_procedures_unrestricted: "apoc.*,gds.*"`, no allowlist, no transaction memory limit; the GDS jar comes from `./data/cache/neo4j-plugins` mounted read-only at `/nr-plugins` and copied in by the entrypoint (OD-13) | M4.1 (allowlist, `db_memory_transaction_max`, and the same two settings in the Testcontainers fixture `nr_test_neo4j`); M4.5 (the plugins folder) | **X3 (M, M4.5)**: the spec mounts `data/cache/neo4j-plugins` at `/plugins`; the repository already uses that folder (at `/nr-plugins`, OD-13), and APOC comes from the image, so offline starts do not download. Keep OD-13's mount and record the deviation; `scripts/network_off.py --plugins` (M4.6) checks the GDS jar there |
| `compose.yaml` `api` service | profile `app`, the Dockerfile's command, no `logging` block, `NEO4J_*` variables, read-only, `cap_drop: ALL` | M4.1, M4.5 (`NR_COPILOT_*`), M4.7 (`NR_COPILOT_IN_COMPOSE`) | OK |
| Pins in `api/pyproject.toml` | `fastapi>=0.143,<0.144` (lock 0.143.5), `uvicorn>=0.54,<0.55` (lock 0.54.0); no Starlette pin (lock **1.9.0**); httpx `>=0.28,<0.29` in the root dev group and ingest (lock 0.28.1); neo4j lock 6.4.1 | M4.1 | **X4 (Q, tech lead, M4.1)**: uvicorn is already pinned. The spec's `starlette>=1.8,<1.9` would move the lock down from 1.9.0, which Phase 1 adopted (the test suite filters 1.9's TestClient deprecation, decision D13). Pin `<1.9` as written (and drop the filter), or pin `>=1.9,<1.10` and record why? Recommended: `>=1.9,<1.10`, since `RequestBodyLimitMiddleware` exists in both and the repository already tests on 1.9 |
| The guard hook's protected paths and human-only commands | data/cache/real, data/cache/spikes, data/cache/holdout and, from this pull request, data/cache/heldout; human-only: `er label`, `er review`, `api serve --real`, `eval run --split test` and, from this pull request, the copilot and model commands (2.14) | M4.0 | **D** |
| `copilot/` | `copilot/pyproject.toml` (`neonradar-copilot` 0.1.0, no dependencies), a placeholder `__init__.py`, `py.typed`, `tests/test_copilot_version.py` | M4.3a adds the package's dependencies (the workspace's contracts, detect and graph packages, pyyaml, httpx) | OK |

## 4. The agent kit in this pull request (M4.0)

- `.claude/rules/copilot.md` and `docs/team/assignment-5.md`, verbatim (`make spec-check M=M4.0`: 2 of 2).
- `docs/build/phase-4-deviations.json` (`{}`); Makefile `spec-check` and `spec-extract` choose the book by milestone id; `scripts/spec_extract.py` refuses a deviation of `copilot/bench/`, `data/fixtures/copilot-bench/` and `docs/benchmark-questions.md`, and its `PHASE-3-CODE.md` block is rewritten with `spec_extract update` (`make spec-check M=M3.0`: 4 of 4). A small new test file, `scripts/tests/test_spec_extract_benchmark.py`, covers the three paths; the Makefile's choice of book is shown only by the acceptance commands (`make spec-check M=M4.0` and `M=M3.0`); the verbatim Phase 3 test file is unchanged.
- The guard hook (2.14). Beyond the fifteen cases of the spec, it also blocks: the same commands through `uv run` (the copilot commands, and `ollama` as `uv run ollama` or `uv run -- ollama`), a launcher (`env`, `nohup`, `sudo`, ...), `bash -c` or `eval`; `COMPOSE_PROFILES` with `llm` or `*`; `--profile "*"`; the `ollama` service named on `docker compose up`, `start`, `run`, `create`, `pull`, `restart` or `exec` (Compose starts a profiled service that a command names, without `--profile`); `NR_COPILOT_MODEL_ROUTER` set to anything but off on a command line (the API reads it); a `model-check` whose last `--digest` is not empty; and the same lines in a script fed to an interpreter. The command splitter took an empty argument (`""`) for an operator and split `--digest ""` into two commands; it no longer does. 39 new cases; `test_hooks.sh` prints 252. The hook stops accidents, not intent: section 6 lists what it does not catch.
- `/milestone` reads the Phase 4 book for an M4.x id; `settings.json` allows pushes to `p4/*` and the documentation hosts of 2.7 and denies reading `data/cache/heldout` (both the `./` and the project-root form, as M2.0 did for the other folders); `RUF001` joins `S101` for tests in `pyproject.toml` (the repository's ruff configuration; there is no `ruff.toml`); labels `benchmark-change`, `human-run`, `assignment-5`, synced; CODEOWNERS rows of 4.3 (the copilot mentor through a new `mentor:<squad>` role in `generate_codeowners.py`).
- `docs/build/project.yaml`: `people.heldout_owner: "@TODO"` (OD-25) and the five Phase 4 dates; the project model reads them (`People.heldout_owner`, `str | None`, and `Schedule.phase_4_start` and the rest, `date | None`), with unit tests that read the keys, read their absence as `None`, and check the committed file.
- `CLAUDE.md`: the four Phase 4 blocks, verbatim; the spec line names PHASE-2.md, PHASE-3.md and PHASE-4.md, because Phase 2 is still being built; 198 lines (rules 9 to 11 shortened, two repeated Phase 1 traps removed).

## 5. Phase 4 milestones and what they wait for

| Milestone | Waits for (beyond the Phase 4 order of 1.8) | Seams it checks again |
|---|---|---|
| M4.1 | M2.12 (its header); the answer to X4 | F1 to F3, A5, T1, X1 to X3 |
| M4.2 | `contracts-v1.2.0` (M3.1, after M2.1a to M2.1c and `contracts-v1.0.0`), M3.2, M4.1; the contract-change session; the answers to A1 to A3 | 2.1, 2.2, D1 |
| M4.3a | M4.2 | A3, A4, D1, V1, V2, Y1 |
| M4.3b | M4.3a | none new |
| M4.4 | M4.3b, M2.11, M2.12, M3.3 | G2, G3, O1, W1, L1, L2 |
| M4.5 | M4.4 | G2, S1, I1, N1, X3, 2.9 (`:DetectionRun`) |
| M4.6 to M4.10 | as PHASE-4.md 1.8 | none |

## 6. Questions, by person

- **Tech lead**: A1 (the context ids' type and cap), A2 (the 1.0.0 answer validator), A3 (the evidence nodes against C3's node rules, with the data steward), X4 (the Starlette pin). The contract-change issue of 5.0 should also say that 1.0.0 already refuses unknown fields (A1).
- **Data steward**: A3 (which properties of a person the evidence keeps; the recommendation keeps fewer). And, under OD-12, before the repository is made public: a Companies House company search and officer search for the invented names on the Assignment 5 task cards (Calvane Holdings Ltd, Orvelle Services Ltd, Zorvex Trading FZE, Kestrow Partners, and the person on card 4, written in Cyrillic), recording the query, the date and the result. Card 10 pairs Calvane Holdings Ltd with "criminal enterprise" (a question the copilot must refuse), so a match with a real company would put that phrase next to a real name (G1). `docs/team/assignment-5.md` is verbatim and is not edited here; the same text has been on `main` since the seed pull request (#40, in `PHASE-4-CODE.md`), and the repository is private. A rename is a `benchmark-change` (PHASE-4.md 1.9).
- **Operator**: `people.heldout_owner` stays `@TODO` (OD-25); only M4.9 needs it.

What the guard hook does not catch (it stops accidents, not a determined person, like the Phase 2 and 3 rules): a model or held-out command written inside `python -c` or `node -e` strings or in a script file; a command name built from a variable or `$(...)`; a renamed or linked `ollama` binary; `docker run` of the `ollama/ollama` image; HTTP calls to an Ollama server that a human already started; another Compose file or a make target that sets the `llm` profile. Two harmless lines it blocks: a launcher line that only names `ollama` as an argument (`command -v ollama`, `xargs grep ollama`), and quoted text that starts with `ollama ` inside `bash -c`, `eval` or a script fed to an interpreter (`bash -c "echo 'ollama serve'"`).

## 7. M4.1 checks its seams again (2026-10-24, on M2.12's branch)

| Seam | Found | Done in M4.1 |
|---|---|---|
| F1 `create_app` | `create_app(graph=None, files=None, allowed_hosts=None)`; telemetry all off | `create_app(graph=None, files=None, *, dev=False)`; `harden(app, dev=dev)` after every route; `create_dev_app()` is the factory `api serve --dev` names |
| F2 trusted hosts | Phase 1's `TrustedHostMiddleware` on `NR_ALLOWED_HOSTS` | one layer, `harden`'s fixed list (`[::1]` is new); `NR_ALLOWED_HOSTS`, the `allowed_hosts` parameter and the tests' `testserver` allowance are gone |
| F3 the 500 handler | Phase 1's `Exception` handler logs `request.url.path` with the traceback; it sits outside `Contain`, so it is never reached | removed; `Contain` answers; the other handlers log the route template instead of the request path, and the unavailable-graph line names the cause's class only |
| A5 `Problem` | C3 1.1.0's `Problem` is closed and requires `instance`; `Contain` sends four fields, so Phase 1's 500 test fails on it | `Contain` also sends `instance`, the route template (a recorded deviation of `hardening.py`) |
| T1 test clients | as found by M4.0, plus `test_routes.py`'s CORS test, which asserts CORS headers on the default app | every client on `http://127.0.0.1`; the CORS test runs its unchanged assertions on `create_app(dev=True)` and checks that the default app sends none |
| X1 `api serve` | `--port` only; one Phase 1 test refuses `--host` | `--dev`, `--host` (only where `NR_API_IN_IMAGE=1`, which the image sets, so that test still passes), `access_log=False`, `log_config()`; `--real` refuses `--host` and `--dev` |
| X2 the image | syncs `neonradar-api` only | syncs `neonradar-cli`; `CMD` runs `neonradar api serve --host 0.0.0.0 --port 8000` |
| X3 plugins mount | unchanged (M4.5) | none |
| X4 Starlette | no pin; lock 1.9.0; no 1.8 wheel in the offline caches | `starlette>=1.9,<1.10` (lock 1.9.0), the reconciliation's recommendation; the tech lead still answers X4 |
| Vite proxy | `changeOrigin: false` | `changeOrigin: true` (deliverable 3) |
| Validation errors | `loc` and `msg` only; an unknown key is reported at its parent | unchanged; the 501-character question case added to `test_routes.py` |

### 7.1 C3 1.1.0 text that the hardening outdates (for M4.2's contract change)

M4.1 leaves `contracts/**` alone (frozen since `contracts-v1.0.0`). The behaviour below is what the spec asks for (deliverables 2 to 4, 3.5 items 6 and 7, 7.5.3), but `contracts/C3-api.md` 1.1.0 still describes Phase 1's. The section 5.0 issue text does not name these points, so the C3 1.2.0 change (M4.2) should add them, or the tech lead decides otherwise. The Class column uses PHASE-1.md 5.0: H1 to H3 are not additive for every client, so the issue text names them the way it names its two copilot points; the tech lead approves each one or picks another option.

| # | C3 1.1.0 says | From M4.1 | Class | Decision |
|---|---|---|---|---|
| H1 | CORS allows exactly `http://localhost:5173` in every mode (line 16); another origin's preflight gets Starlette's `400 text/plain` (line 229) | CORS only under `neonradar api serve --dev`, for `http://localhost:5173` and `http://127.0.0.1:5173`, and there another origin's preflight still gets Starlette's `400 text/plain`. The default app sends no CORS header and answers every preflight (`OPTIONS`), from any origin, with `405` and an `application/problem+json` body (checked on `create_app()` and `create_app(dev=True)` at 92bf871) | Not additive (a default removed: a browser on `http://localhost:5173` loses CORS unless the server runs with `--dev`) | Spec (3.5 item 6), and the stricter option: C3 1.2.0 says CORS is for development only and states the default app's 405 |
| H2 | Host check on `NR_ALLOWED_HOSTS` (default `localhost`, `127.0.0.1`, `api`); the Code line lists `neonradar_api.settings` (`NR_REPO_ROOT`, `NR_ALLOWED_HOSTS`) | the fixed list `hardening.ALLOWED_HOSTS` (`127.0.0.1`, `localhost`, `[::1]`, `api`), still a `400 text/plain` before anything else; `NR_ALLOWED_HOSTS` is gone | Not additive (a setting removed: a deployment that set `NR_ALLOWED_HOSTS` gets 400) | Spec (7.5.3); a fixed list has no environment override; `[::1]` is new |
| H3 | `instance` is the request path (line 216) | `Contain`'s 500 sends the route template (`/api/v1/entities/{entity_id}`, `unmatched` or `redacted`); every other problem keeps the path. The template's braces are not a valid RFC 3986 URI reference, which RFC 9457 expects `instance` to be | Not additive (the meaning of `instance` changes for an unexpected 500) | OD-10 (A5): C3's `Problem` requires `instance`, and the template keeps a path value out of an unexpected error. C3 1.2.0 says that an unexpected 500's `instance` is the route template and not a URI to dereference, or the tech lead picks a fixed value |
| H4 | a 500's "`detail` is generic or names the fix, and the API log has the details" | an unexpected error's detail is "The API could not answer this request. Please report it to the maintainers."; the API log names the exception's class and the route template only (the real-data app's redacted log keeps the traceback) | Patch (wording; no shape change) | Spec (deliverable 3) |
| H5 | no 413 in the status table | a body over 64 KiB is a 413: Starlette's `text/plain` "Content Too Large" when `Content-Length` says so, a 413 problem when a streamed body passes the limit | Minor (a new status) | Spec (7.5.3). The 5.0 issue text documents every 4xx and 5xx as `application/problem+json`: C3 1.2.0 either leaves 413 out of the OpenAPI document or documents both bodies, never the problem body alone, because the declared-length path does not send one |
| H6 | `neonradar api serve [--port 8000]` is "always `127.0.0.1`" (line 8) and "has no host option" (line 15); the Code line does not name `neonradar_api.hardening` | `api serve` gains `--dev` (CORS for the Vite dev server) and `--host`, accepted only where `NR_API_IN_IMAGE=1` (the API image, which serves on `0.0.0.0` inside the container, as line 15 already says); `--real` refuses both. The bind default stays `127.0.0.1`. `neonradar_api.hardening` (trusted hosts, access log, CORS in development, body limit, `Contain`) is new | Minor (two options added; the default is unchanged) and Patch (the Code line) | Spec (deliverables 3 and 4); `--host` only in the image and `--real` refusing `--dev` are OD-10 decisions (stricter than the spec) |

Found in a verbatim file and left as it is (2.5 item 11): `harden` puts `Contain` inside the body limit, and Starlette's `RequestBodyLimitMiddleware` stops an over-long response with an internal exception (`_RequestBodyLimitResponseSent`) after it has sent its own 413. `Contain` catches that exception, so every request whose `Content-Length` is over 64 KiB also writes `unhandled _RequestBodyLimitResponseSent on POST <route template>` at ERROR (on the real-data app, `Reported` also sends its traceback to the redacted log). The answer is still the 413 and no value reaches the log; the tech lead decides whether the code book should let `Contain` pass that exception on.
