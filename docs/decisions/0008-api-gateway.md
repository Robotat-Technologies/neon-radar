# 0008. API gateway and OpenAPI snapshot

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead)

## Context

The UI (Phase 5) and the copilot (Phase 4) need the graph, the alerts and the typology catalog, and they are built by other squads in parallel with the Graph and Detection squads (`docs/build/PHASE-1.md` 0.3, 4.1). The four contracts freeze at Gate 1 (5.0), so the shape of what the UI and the copilot receive has to be agreed before either is built: the API contract C3 (5.3).

Three constraints shape it:

- **Guardrails.** Nothing phones home at runtime (G3); text next to entities describes patterns and never accuses (G5); real entities are never labelled suspicious (G1). The interface should enforce these where code can, not leave them to each consumer.
- **One graph, read by many.** Neo4j holds source data, synthetic activity and alerts (C2, C4). Any component that writes to it outside the loader and the detection runner could change what an alert's reproduction query finds.
- **A local-first tool.** The demo and development run on a laptop (M1.4, M1.9e); the API serves one machine.

FastAPI generates an OpenAPI document from typed pydantic models, and the UI can generate TypeScript types from that document with `openapi-typescript` (`.claude/rules/frontend.md`). FastAPI 0.143 is the pinned version (PHASE-1.md 3.1; `docs/research/2026-10-16/stack.md` section 3.2). It ships native OpenTelemetry, which can add exporters from environment variables, and its default `/docs` and `/redoc` pages load their assets from a CDN (checked in the installed FastAPI 0.143.5 source on 21 October 2026).

## Options considered

1. **One FastAPI service as the only way to the graph, with its OpenAPI document committed as the contract (chosen).** The UI and the copilot call HTTP endpoints; only the API talks to Neo4j for them. Typed models generate the document; the committed snapshot is compared with the running app on every pull request. Drawbacks: every new question the UI or the copilot asks needs an endpoint (or a copilot template); the snapshot is generator output, so a FastAPI or pydantic upgrade can change it without a model change.
2. **The UI and the copilot query Neo4j directly** (Bolt from the browser through the Neo4j JavaScript driver, or Cypher from the copilot). No API to build. But every consumer would need database credentials, could write, and would encode C2's labels and properties itself, so a C2 change would break consumers silently. There would be no single place to keep `topics` out of the UI, to enforce limits, or to word errors.
3. **A hand-written API description (OpenAPI written by hand, or a schema-first tool) with the server generated from it.** The contract is the source, not a by-product. But it duplicates the pydantic models the rest of the project already uses for C1, C2 and C4, and two descriptions of one shape drift.
4. **GraphQL.** Flexible queries for the UI. But it makes limits and traversal depth harder to bound per request (5.2 requires every traversal and result to be bounded), adds a second schema language, and the copilot's template-first design (ADR-0010, Phase 4) does not need it.

## Decision

We will serve C3 from one FastAPI application, `neonradar_api.main.create_app`, as `contracts/C3-api.md` defines it (version 1.0.0):

- **The only way to the graph.** The UI and the copilot reach Neo4j only through the API. Every query is parameterised and runs as a READ transaction (`GraphConnection.read`, `routing_=RoutingControl.READ`); Neo4j refuses writes inside READ transactions. The API uses the sync neo4j driver from `neonradar_graph.client`, one lazily created driver per app, with plain `def` routes in FastAPI's thread pool: one client and one settings object for the whole project, and enough concurrency for a local tool.
- **The OpenAPI snapshot is the contract.** `contracts/openapi/v1.json` is the running app's document, written by `neonradar contracts export` and checked by `neonradar contracts check` and a contract test. Every route is declared with its final response model, limits and errors before it is implemented, so implementing it does not change the snapshot. The UI generates its types from the snapshot and never writes API types by hand.
- **Strict, closed models without defaults on responses**, so generated types say exactly what is always present and what may be null.
- **RFC 9457 problem details** for every error (`application/problem+json`, `type` `about:blank` in v1).
- **Bound to localhost.** `neonradar api serve` listens on `127.0.0.1` only; Compose publishes the container on `127.0.0.1` (M1.9e). CORS allows only the Vite dev server.
- **Nothing phones home.** FastAPI's OpenTelemetry is switched off, including its auto-configuration from the environment, no OpenTelemetry SDK or exporter is installed, and the CDN-backed `/docs` and `/redoc` pages are not served; an offline documentation page comes with M1.9c.
- **Versioned paths.** `/api/v1` and `openapi/v1.json` cover every 1.x release; a breaking change gets `/api/v2`.

## Consequences

- The UI and copilot squads can build against the snapshot and mocked responses before M1.9c implements the routes; M1.9c must not change the snapshot, so any missing parameter or field is found and decided before the Gate 1 freeze.
- C2 can change behind the API without breaking consumers as long as C3 holds; C3 decides what leaves the graph (for example, no `topics` in property maps, so source topics beyond the three flags never reach the UI).
- A FastAPI or pydantic upgrade can change the snapshot without a model change. `uv.lock` pins exact versions; an upgrade pull request regenerates the snapshot and is reviewed as a contract change, which after the freeze needs the contract-change label.
- The interactive API docs need an offline page (M1.9c); until then, M1.9c's review step and M1.9e's printed docs URL refer to a page that does not exist yet.
- Read-only by construction means the API can never fix data; corrections go through the loaders and the sources.
- A sync driver keeps the code simple; if the API ever serves many users at once, an async driver is a contained change inside `neonradar_api.graph`.

## Sources

- `docs/build/PHASE-1.md` sections 2.1 (G1, G3, G5), 3.1, 4.1, 5.0, 5.2 (Cypher conventions), 5.3, M1.7d, M1.9c and M1.9d.
- `contracts/C3-api.md`, `contracts/C2-graph-schema.md`, `contracts/C4-alert.md` and `contracts/CHANGELOG.md` (1.0.0, C3).
- `docs/research/2026-10-16/stack.md` section 3.2 (FastAPI 0.143.2 and its dependencies, checked on PyPI on 16 October 2026) and `docs/research/2026-10-16/neo4j.md` (driver 6 API; the async driver as an option for FastAPI, S69).
- RFC 9457, Problem Details for HTTP APIs. https://www.rfc-editor.org/rfc/rfc9457
- OpenAPI Specification 3.1.0. https://spec.openapis.org/oas/v3.1.0
- `docs/build/operator-decisions.md` OD-14 (no `.env` in agent work; acceptance against a throwaway database).
