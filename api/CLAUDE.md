# api: neonradar_api

- Purpose: the FastAPI app that serves contract C3 under `/api/v1` (contracts/C3-api.md),
  bound to 127.0.0.1. The only way the UI and the copilot reach the graph (ADR-0008).
- Owner: copilot squad (nr-copilot); the UI squad is its consumer.
- Depends on: C3 API models (`neonradar_contracts.api`), C2 graph schema (reads Neo4j through
  `neonradar_graph.client`), C4 alerts (`:Alert` payload).
- Commands: `uv run pytest api/tests`; `uv run neonradar api serve [--port 8000]`;
  `make contracts` after any route or model change (rewrites contracts/openapi/v1.json).
- Modules: `main` (`create_app` and every route), `problems` (RFC 9457 errors, `ProblemError`,
  `not_implemented`, `responses`), `graph` (`GraphConnection`: one lazy sync driver; `read()`
  runs READ transactions only; `get_graph` dependency), `health`.
- Traps:
  - The running app's OpenAPI must equal `contracts/openapi/v1.json` (contract test). Routes
    are declared with their final responses, so implementing one must not change the snapshot.
  - Errors are problems (`application/problem+json`); declare them with
    `problems.responses(...)`, never with `model=` (that adds `application/json`).
  - Response models have no defaults; nullable fields are `T | None` and always set.
  - FastAPI 0.143 has native OpenTelemetry: keep `telemetry=TELEMETRY_OFF` (guardrail G3);
    never install an OpenTelemetry SDK or exporter.
  - Never re-enable `/docs` or `/redoc`: FastAPI's pages load assets from a CDN and
    fastapi.tiangolo.com (G3). An offline page is M1.9c's.
  - FastAPI 0.143 mounts included routers lazily: `app.routes` does not list the API
    routes; read `main.router.routes`.
  - Every query goes through `GraphConnection.read` (parameters only, READ routing).
  - `:Sanction` nodes are entities in C3: look up `:Entity` and `:Sanction` by `id` with two
    index lookups. Property maps leave out `neonradar_contracts.api.NODE_PROPERTIES_LEFT_OUT`
    (`topics`, `referents`, ...); the models reject them. `limits.max_edges` is 2 x `max_nodes`.
  - A bad `NEO4J_URI` or `NEO4J_DATABASE` must stay a 503 (health: degraded, still 200);
    `GraphConnection` maps driver configuration errors and DatabaseNotFound to `GraphUnavailable`.
  - Alerts come only from Neo4j, not from the files in `data/runs/`.
  - Tests never touch Neo4j: pass a `GraphConnection` subclass to `create_app`, and build the
    settings error yourself instead of reading the environment or `.env`.
