# api: neonradar_api

- Purpose: the FastAPI app that serves contract C3 under `/api/v1` (contracts/C3-api.md),
  bound to 127.0.0.1. The only way the UI and the copilot reach the graph (ADR-0008).
- Owner: copilot squad (nr-copilot); the UI squad is its consumer.
- Depends on: C3 API models (`neonradar_contracts.api`), C2 graph schema (reads Neo4j through
  `neonradar_graph.client`), C4 alerts (`:Alert` payload), the typology catalog
  (`neonradar_detect.catalog.load_catalog`).
- Commands: `uv run pytest api/tests`; `uv run pytest -m integration api/tests` (demo-mini and
  one detection run on Testcontainers); `uv run neonradar api serve [--port 8000]`, then
  `http://127.0.0.1:8000/docs` (offline page); `make contracts` after any route or model
  change (rewrites contracts/openapi/v1.json).
- Modules: `main` (`create_app` and every route), `problems` (RFC 9457 errors, `ProblemError`,
  `not_implemented`, `responses`), `graph` (`GraphConnection`: one lazy sync driver; `read()`
  runs READ transactions only; `get_graph` dependency), `health`, `files` (`RepoFiles`: the
  typology files and bibliography from `NR_REPO_ROOT`, default the nearest uv workspace above
  the working directory; `get_files` dependency), `entities` (search, entity detail, network),
  `alerts` (queue with its cursor, detail), `reference` (meta, typologies), `docs_page` (the
  `/docs` page), `settings` (`ApiSettings`: `NR_REPO_ROOT`, `NR_ALLOWED_HOSTS`; environment
  only, read when the app starts).
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
  - `TrustedHostMiddleware` answers only `NR_ALLOWED_HOSTS` (`neonradar_api.settings`; default
    `localhost`, `127.0.0.1`, `api`): a proxy must pass one of them as `Host`. Tests add
    `testserver` (`tests/conftest.py`, `TEST_HOSTS`).
  - FastAPI 0.143 mounts included routers lazily: `app.routes` does not list the API
    routes; read `main.router.routes`.
  - Every query goes through `GraphConnection.read` (parameters only, READ routing).
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
  - Unit tests never touch Neo4j: pass a `GraphConnection` subclass to `create_app`
    (`tests/conftest.py`: `OfflineGraph`, `ScriptedGraph`), and build the settings error
    yourself instead of reading the environment or `.env`. The integration tests
    (`test_api_neo4j.py`) put the API on the driver of the shared `neo4j` fixture
    (graph/tests/support/nr_test_neo4j.py; import `Neo4jTarget`, never the fixtures) and
    derive expected values from the fixture through the C2 mapping, never from hard-coded
    demo-mini names.
