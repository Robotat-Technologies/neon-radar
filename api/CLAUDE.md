# api: neonradar_api

- Purpose: the FastAPI app that serves contract C3 under `/api/v1`, bound to 127.0.0.1.
- Owner: copilot squad (nr-copilot); the UI squad is its consumer.
- Depends on: C3 API models, C2 graph schema (reads Neo4j), C4 alerts (`:Alert` payload).
- Commands: `uv run pytest api/tests`; `uv run neonradar api serve` (from M1.7d).
- Traps:
  - The running app's OpenAPI must equal `contracts/openapi/v1.json` (contract test).
  - Errors are RFC 9457 problem details; snake_case JSON.
  - Alerts come only from Neo4j, not from the files in `data/runs/`.
