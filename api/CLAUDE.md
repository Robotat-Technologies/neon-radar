# api: neonradar_api

- Purpose: the FastAPI app that serves contract C3 under `/api/v1` (contracts/C3-api.md),
  bound to 127.0.0.1. The only way the UI and the copilot reach the graph (ADR-0008).
- Owner: copilot squad (nr-copilot); the UI squad is its consumer.
- Depends on: C3 API models (`neonradar_contracts.api`), C2 graph schema (reads Neo4j through
  `neonradar_graph.client`), C4 alerts (`:Alert` payload), the typology catalog
  (`neonradar_detect.catalog.load_catalog`).
- Commands: `uv run pytest api/tests`; `uv run pytest -m integration api/tests` (demo-mini and
  one detection run on Testcontainers); `uv run neonradar api serve [--port 8000] [--dev]`, then
  `http://127.0.0.1:8000/docs` (offline page); `make contracts` after any route or model
  change (rewrites contracts/openapi/v1.json).
- Modules: `main` (`create_app(graph, files, *, dev, report)` and every route), `hardening` (M4.1:
  `harden`, trusted hosts, `AccessLog`, `Contain`, `route_template`, `log_config`), `problems`
  (RFC 9457 errors, `ProblemError`, `not_implemented`, `responses`, `Reported`), `graph` (`GraphConnection`: one lazy sync driver on
  `Instance.DEFAULT` unless given other settings; `read()` runs READ transactions only, with a
  transaction timeout when asked; `call(work)` hands the driver to a `neonradar_graph.ownership`
  function; a transaction timeout becomes `QueryTimeout`; `get_graph` dependency), `health`,
  `files` (`RepoFiles`: the typology files and bibliography from `NR_REPO_ROOT`, default the
  nearest uv workspace above the working directory; `get_files` dependency), `entities` (search,
  entity detail, network), `resolution` (the resolution route and entity provenance, M2.12;
  texts only from `neonradar_graph.wording`), `alerts` (queue with its cursor, detail),
  `reference` (meta, typologies), `docs_page` (the `/docs` page), `settings` (`ApiSettings`:
  `NR_REPO_ROOT`; environment only, read when the app starts).
- Traps:
  - The running app's OpenAPI must equal `contracts/openapi/v1.json` (contract test). Routes
    are declared with their final responses, so implementing one must not change the snapshot.
  - Errors are problems (`application/problem+json`); declare them with
    `problems.responses(...)`, never with `model=` (that adds `application/json`).
  - Response models have no defaults; nullable fields are `T | None` and always set.
  - FastAPI 0.143 has native OpenTelemetry: keep `telemetry=TELEMETRY_OFF` (guardrail G3);
    never install an OpenTelemetry SDK or exporter.
  - Never re-enable FastAPI's `/docs` or `/redoc`: they load assets from a CDN and
    fastapi.tiangolo.com (G3). `/docs` is `docs_page`: inline style and script only, allowed by
    their SHA-256 in the Content-Security-Policy (edit the text and the hashes follow).
  - `harden` (added after every route) answers only the fixed hosts `127.0.0.1`, `localhost`,
    `[::1]` and `api`: a proxy must pass one of them as `Host` (Vite: `changeOrigin`). Every
    test client uses `base_url="http://127.0.0.1"`, never TestClient's `http://testserver`.
  - Logs name route templates (`hardening.route_template`), never `request.url.path` or an
    exception's message. An exception no handler takes is `Contain`'s fixed 500 problem; do
    not add an `Exception` handler. CORS only with `create_app(dev=True)` (`api serve --dev`).
  - `api serve` runs uvicorn with `access_log=False` and `hardening.log_config()`; `--host`
    only where `NR_API_IN_IMAGE=1` (the API image), never with `--real`. The real-data app
    (`create_app(..., report=...)`, never with `dev`) logs warnings only, and `Reported`, inside
    `Contain`, hands an unhandled exception to `report` (the redacted traceback log).
  - FastAPI 0.143 mounts included routers lazily: `app.routes` does not list the API
    routes; read `main.router.routes`.
  - Every Phase 1 and 2 query goes through `GraphConnection.read` (parameters only, READ
    routing); Phase 4 code reads only through `neonradar_graph.readonly.run_read`.
  - `:Sanction` nodes are entities in C3: look up `:Entity` and `:Sanction` by `id` with two
    index lookups. Property maps leave out `neonradar_contracts.api.NODE_PROPERTIES_LEFT_OUT`
    (`topics`, `referents`, ...); the models reject them. `limits.max_edges` is 2 x `max_nodes`.
  - A bad `NEO4J_URI` or `NEO4J_DATABASE` must stay a 503 (health: degraded, still 200);
    `GraphConnection` maps driver configuration errors and DatabaseNotFound to `GraphUnavailable`.
  - Alerts come only from Neo4j, not from the files in `data/runs/`. `subject_ids` follow
    `payload.subjects` (FLAGS has no order). The evidence relationships are found from the
    evidence nodes (C4 puts both ends among them), so no relationship scan by id is needed.
    C3's `AlertDetail` cannot hold partial evidence: an alert whose payload no longer validates
    (or names another alert id), or whose evidence left the graph, is a 500 problem that says
    to wipe and reload, then re-run detection; the queue leaves such an alert out with a
    warning instead of failing the page.
  - Queries return nodes as `{props: properties(n), labels: labels(n)}` and relationships with
    their C2 end ids: `elementId()` values never leave the database. Search escapes Lucene
    syntax (`entities.lucene_query`) and lowercases only the operator words AND, OR and NOT;
    never lowercase the whole text in Python (it differs from Lucene for `İ` and final `Σ`).
  - `/meta` reads the registry and disclaimers from the contracts package (`load_registry()`,
    `load_disclaimer()`), never from `NR_REPO_ROOT`, so it never fails on that setting; the
    typology routes answer a 500 problem naming `NR_REPO_ROOT` when it holds no checkout.
  - The network query is chosen from `entities.NETWORK` by depth (one fixed text per depth).
  - Ownership and paths (M2.12) are `neonradar_graph.ownership.ownership|paths` through
    `GraphConnection.call`; `UnknownId` answers the 404 problem and `QueryTimeout` the 503
    with advice (`problems.install`). Upward ownership paths come back root first (C3; the
    query lists the owner first, reconciliation E13). Unit-test doubles override `read` and
    `call` (`OfflineGraph`); a fake driver needs `execute_query` and `close`.
  - Entity detail and every M2.12 route also take the id of a record merged into an entity
    (`:SourceRecord` and `RESOLVED_TO`); a merged entity's provenance is its source records.
  - Logs name the route template (`request.scope["route"].path`), never `request.url.path`:
    a path holds ids. `create_app(report=...)` builds the real-data app: no CORS, unhandled
    errors log their class only and `report` keeps the traceback; wrap it in
    `problems.Contained` so Starlette's re-raise never reaches uvicorn's traceback log.
  - `shapes` only re-exports `neonradar_graph.shapes` for C3's Code line (reconciliation K1).
  - Unit tests never touch Neo4j: pass a `GraphConnection` subclass to `create_app`
    (`tests/conftest.py`: `OfflineGraph`, `ScriptedGraph`), and build the settings error
    yourself instead of reading the environment or `.env`. The integration tests
    (`test_api_neo4j.py`) put the API on the driver of the shared `neo4j` fixture
    (graph/tests/support/nr_test_neo4j.py; import `Neo4jTarget`, never the fixtures) and
    derive expected values from the fixture through the C2 mapping, never from hard-coded
    demo-mini names.
