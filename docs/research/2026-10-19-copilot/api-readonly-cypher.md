# NeonRadar phase 4: the API and read-only Cypher

Research date: Monday 19 October 2026.

Method. Every fact below was checked on 2026-10-19 and carries a source tag; the full list is in "Sources". I read source code and documentation from fresh shallow clones: FastAPI 0.146.0, Starlette 1.9.0, uvicorn 0.54.0, httpx 0.28.1, httpx2 2.14.0, the pydantic 2.14.1 changelog, neo4j/neo4j at tag 5.26.32 (Community modules, sparse checkout), the Operations Manual on branch `5.x`, the Cypher Manual on branch `cypher-5`, the driver manual on branch `6.x`, the Python driver at tag 6.4.1, APOC Core at tag 5.26.32 and APOC Extended on branch `5.26`. The local clones under `/home/claude/neo4j/` were used for docker-neo4j (master, fd9e4ec) and neo4j-graphrag-python (main, 029ebd9). The local docs-operations and docs-cypher clones are on `dev` (2026.10 docs) and the local driver clone is a sparse checkout without `src/`, so I did not use them for 5.26 facts. Package versions come from the PyPI JSON API. I also ran experiments in Python 3.14.6 virtual environments (FastAPI 0.146.0 and 0.143.2, Starlette 1.9.0 and 1.8.0, pydantic 2.14.1 and 2.13.5, httpx 0.28.1, httpx2 2.14.0, neo4j 6.4.1, pytest 9.1.1, pytest-asyncio 1.4.0, asgi-lifespan 2.1.0) [X1] to [X8]. Blocked: the shell could not reach rfc-editor.org (the egress proxy refused it), so RFC 9457 was read through the web fetch tool; Maven Central was refused too (not needed). There is no Docker daemon and no Neo4j server on this machine, so server behaviour comes from reading the 5.26.32 source and Neo4j's own integration tests. Anything only a running server could show is marked UNVERIFIED.

## 0. Answers for the spec writer

1. **FastAPI and friends.**
   - Latest today: FastAPI 0.146.0 (2026-10-18), Starlette 1.9.0 (2026-10-18), pydantic 2.14.1 (2026-10-11) with pydantic-core 2.50.1, uvicorn 0.54.0 (2026-09-25), httpx 0.28.1 (2024-12-06; only `1.0.dev*` pre-releases since), httpx2 2.14.0 (2026-10-18) [Y1].
   - FastAPI, Starlette, pydantic, uvicorn and the Neo4j driver declare Python 3.14 support [F1][S1][P1][U1][D6]. httpx 0.28.1 does not list 3.14 in its classifiers but ran fine on 3.14.6 in every experiment [Y1][X3].
   - Since 0.143: 0.143.1 to 0.143.5 are fixes; 0.144.0 adds WebSocket security dependencies; 0.145.0 removes `openapi_prefix` and the unused `**extra` keyword arguments of `FastAPI()`; 0.146.0 deprecates `FastAPI(root_path=...)` [F1]. None of this touches lifespan, dependency injection, response models or exception handlers. The OpenAPI output of a NeonRadar-like app is byte-identical under 0.143.2 and 0.146.0 [X1].
   - Design-relevant: FastAPI requires only `starlette>=0.46.0` with no upper bound, so pin Starlette yourself [Y1]. Starlette's `TestClient` prefers httpx2 and emits `StarletteDeprecationWarning` when only httpx is installed (since Starlette 1.2.0) [S2][X3]. `TestClient` runs lifespan only inside `with`; `httpx.ASGITransport` never runs lifespan [S2][F4][X3].
   - Testing: prefer `httpx.AsyncClient(transport=httpx.ASGITransport(app))` plus a 10-line lifespan helper for anything that touches the async Neo4j driver. It keeps the driver on the test's event loop [X3].
   - OpenAPI 3.1: `openapi` is the constant "3.1.0" and `info.version` comes from `FastAPI(version=...)`. `components.schemas` is sorted by name. Paths follow route registration. A 422 `HTTPValidationError` response is added unless the route declares `422`, `4XX` or `default`. `responses={...: {"model": Problem}}` is documented under the route's own media type (`application/json`), so problem+json needs a small post-processing step [F3][X2].
   - Snapshot pitfalls: library upgrades change the document. FastAPI 0.128.1 added `input` and `ctx` to `ValidationError`; pydantic 2.14 dropped the `pattern` from `Decimal` schemas, which I reproduced [F1][P1][X6]. Docstrings, field titles, `-Input`/`-Output` splits, `operationId` derived from function names, and `servers` added under a root path also change it [F3][X1][X6].
2. **Read-only enforcement on 5.26 Community.**
   - (a) Yes. A transaction opened in READ mode on a single Community server has every statement checked by the query router. A write is rejected with `Neo.ClientError.Statement.AccessMode` and the message "Writing in read access mode not allowed. Attempted write to neo4j" [N1][N5]. `execute_query(..., routing_=RoutingControl.READ)` sends `mode: "r"` on any driver, routing or direct [D1][D2][N4]. The check works on the parsed statement, and the kernel transaction itself is not restricted [N2][N13]. The driver manual says "There is no security guarantee that a write query submitted in read mode will be rejected." [M1].
   - (b) Bolt reports `type` "r", "rw", "w" or "s". The values are "r" for reads, "rw" or "w" for updates (w when no columns are returned), and "s" for schema commands and also for any query that calls a DBMS-mode procedure [N3][N4]. READ and DEFAULT-mode procedures, `LOAD CSV`, APOC `apoc.load.*`, `apoc.export.*` and `apoc.cypher.run`, and command clauses such as `SHOW TRANSACTIONS` and `TERMINATE TRANSACTIONS` all report "r". WRITE and SCHEMA-mode procedures report "rw"/"w" and are rejected in READ mode. This comes from source reading; the runtime values are UNVERIFIED [N2][N3][N17][A1].
   - (c) Reads that reach files or the network:
     - `LOAD CSV` with `file:///` is confined to `server.directories.import` (`import` in the shipped conf, `/import` in Docker when mounted). Setting `dbms.security.allow_csv_import_from_file_urls=false` (default true) turns file URLs off [O1][N15][K1][N8].
     - `LOAD CSV` with http, https or ftp is open by default [C1].
     - `apoc.load.json`/`jsonArray`/`xml` read files only with `apoc.import.file.enabled=true` (default false), but web URLs are always allowed [A2][A4].
     - `apoc.export.*` are READ procedures. They write files only with `apoc.export.file.enabled=true` (default false) [A1][A2].
     - `apoc.cypher.run` and the `runFirstColumnMany`/`Single` functions run dynamic Cypher that EXPLAIN cannot see [A1]. `apoc.load.csv` lives in APOC Extended, not Core [A3].
     - `dbms.security.procedures.allowlist` removes plugin procedures and functions but never built-in `db.*`/`dbms.*` ones [N12][O3].
     - Outbound web access by `LOAD CSV` and `apoc.load.json` can be blocked with the internal, undocumented setting `internal.dbms.cypher_ip_blocklist` (CIDR list). The host name is resolved before the check [N7][N8]. `dbms.cypher.ip_blocklist` does not exist in 5.26; LOAD privileges are Enterprise only [N7][O6].
   - (d) Limits:
     - `neo4j.Query(text, timeout=s)` or `begin_transaction(timeout=s)` sets a server-enforced timeout. It ends with `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration` [D3][N6][N10].
     - `db.transaction.timeout` (default 0) is only a default. Since 5.3 a client may set a longer one [O2]. The monitor checks every 2 s (`db.transaction.monitor.check.interval`) [N7].
     - `db.memory.transaction.max` (per transaction, default 0 meaning largest possible), `db.memory.transaction.total.max` (per database, default 0) and `dbms.memory.transaction.total.max` (all transactions, default 70 percent of the heap) fail with `Neo.TransientError.General.MemoryPoolOutOfMemoryError` [O1][N9][N6]. The driver retries that error in `execute_query` for up to `max_transaction_retry_time` (30 s) [D5].
   - (e) No read-only user is possible: "In Neo4j Community Edition there are no roles, but all users have implied administrator privileges." [O5]. The credential the API holds can do everything, including user management and `TERMINATE TRANSACTIONS`. All restriction must therefore come from the API code and server configuration [O5][O7].
3. **Python driver 6.4.1.**
   - Create one `AsyncGraphDatabase.driver(...)` in the lifespan, `yield {"driver": driver}`, and `await driver.close()` in `finally`. 6.0 stopped closing drivers in `__del__`, and a closed driver raises `DriverError` [D6][X5].
   - `execute_query` keywords: `routing_` (default WRITE), `database_`, `impersonated_user_`, `bookmark_manager_`, `auth_`, `result_transformer_`. Other keywords become query parameters, and a keyword ending in one underscore raises `ValueError` [D1][X5]. It accepts `Query(text, metadata=None, timeout=None)` [D1][D3].
   - Notifications: `notifications_min_severity` (OFF, WARNING, INFORMATION) and `notifications_disabled_classifications` (HINT, UNRECOGNIZED, UNSUPPORTED, PERFORMANCE, DEPRECATION, GENERIC, SECURITY, TOPOLOGY, SCHEMA). `notifications_disabled_categories` is deprecated. `warn_notification_severity` turns server notifications into `neo4j.warnings.Neo4jWarning` [D5][D7][M1].
   - Summary: `query_type`, `counters.contains_updates`, `counters.contains_system_updates`, `gql_status_objects` (stable since 6.0). `notifications` and `summary_notifications` are deprecated [D4][D6].
   - Set `telemetry_disabled=True`, and a small `max_transaction_retry_time` for the API driver. The default retry window is 30 s, so an unreachable Neo4j would surface only after about 30 s (inferred); with 3 s it took 3.6 s and with 1 s 2.7 s [D5][D7][X5].
4. **Hardening.**
   - Bind to 127.0.0.1. uvicorn defaults to it; `fastapi run` binds `0.0.0.0`, so do not use it outside the container [U1][F8].
   - Add `TrustedHostMiddleware` (`127.0.0.1`, `localhost`, `[::1]`, plus `api` if nginx forwards its default Host) against DNS rebinding [S3][W4][W5][X4].
   - Keep `strict_content_type` on (default since 0.132) and models with `extra="forbid"` [F1][F2][X4].
   - CORS only in development and only for `http://localhost:5173` and `http://127.0.0.1:5173`, with no credentials and `allow_private_network` left False. The Vite proxy already makes dev requests same-origin [S3][W4].
   - Body limit: Starlette's `RequestBodyLimitMiddleware` (Starlette 1.6+). Note that it answers oversized requests that declare `Content-Length` with a plain-text 413 [S3][X4].
   - Rate limiting: not worth it for one local user. Use a small `asyncio.Semaphore` around Neo4j calls and per-query timeouts instead [U1][X4].
   - Errors use RFC 9457 problem details with `application/problem+json`. Forward `exc.headers` (for example `Allow` on 405) [W1][X4].
   - Pagination: keyset cursor over a total `ORDER BY`, fetched with `LIMIT $limit_plus_one` [C5].
5. **SSE.** Not worth it in Phase 4. FastAPI has native SSE since 0.135.0 [F1][F6]. But a template answer takes a few seconds and a plain JSON response with a spinner is simpler to test, to type and to recover from errors. `EventSource` cannot POST [W2]. The generated OpenAPI uses the 3.2 keyword `itemSchema` inside a 3.1.0 document [X7][W3]. Revisit only if an LLM step makes answers slow.
6. **For the spec writer.**
   - The catalog stack, its pins and its tests are in section 6. The core rule: run every template through one helper. The helper opens a READ session and an explicit transaction with a server timeout, caps rows with `fetch(max_rows + 1)`, never commits (`tx.close()`), checks `query_type == "r"` and `contains_updates is False`, and maps errors to problem details [D1][D3][D4][N1].
   - Add a server-side procedures allowlist (`apoc.version,apoc.meta.stats,apoc.coll.*,gds.*`, which is everything Phases 1 to 3 call), keep the APOC file defaults, and keep the import-directory confinement [O3][A2][R1].
   - A free text-to-Cypher mode would also need per-request EXPLAIN with a plan-operator allowlist, a text lint, the outbound blocklist or network isolation, tighter limits and an audit log. EXPLAIN plus "r" alone (the approach Neo4j's own `Text2CypherRetriever` uses) lets `LOAD CSV`, READ procedures and `TERMINATE TRANSACTIONS` through [G1][N3].
   - Pins: keep `fastapi>=0.143,<0.144` (lock 0.143.5) and add `starlette>=1.8,<1.9`, `pydantic>=2.14,<2.15`, `uvicorn>=0.54,<0.55`. Keep `httpx>=0.28,<0.29`, `neo4j>=6.4,<7` and `pytest>=9.1,<10`; add `pytest-asyncio>=1.4,<2`. Add `httpx2` to dev dependencies only if `TestClient` is used [Y1].

## 1. FastAPI, Starlette, pydantic, uvicorn and httpx

### 1.1 Versions today and Python 3.14

| Package | Latest (PyPI upload) | Python | Python 3.14 note |
|---|---|---|---|
| fastapi | 0.146.0 (2026-10-18); 0.143.5 is the newest 0.143 patch (2026-10-18) | >=3.10 | "Add support for Python 3.14." in 0.118.3; "Support free-threaded Python 3.14t." in 0.136.0 [F1] |
| starlette | 1.9.0 (2026-10-18) | >=3.11 (since 1.8.0) | "Add official Python 3.14 support" in 0.48.0 [S1] |
| pydantic / pydantic-core | 2.14.1 (2026-10-11) / 2.50.1 | >=3.10 | 2.12.0 brought "initial Python 3.14 support"; 2.14.0 "drops support for Python 3.9 and adds support for Python 3.15" [P1] |
| uvicorn | 0.54.0 (2026-09-25) | >=3.10 | "Support Python 3.14" in 0.38.0 [U1] |
| httpx | 0.28.1 (2024-12-06) | >=3.8 | classifiers stop at 3.12; worked on 3.14.6 [Y1][X3] |
| httpx2 | 2.14.0 (2026-10-18) | >=3.10 | classifiers 3.10 to 3.15 [Y1] |
| neo4j | 6.4.1 (2026-10-15) | >=3.10 | "Python 3.14 support added." in 6.1 [D6] |
| pytest / pytest-asyncio | 9.1.1 (2026-06-19) / 1.4.0 (2026-05-26) | >=3.10 | classifiers include 3.14 [Y1] |
| asgi-lifespan | 2.1.0 (2023-03-28) | >=3.7 | classifiers stop at 3.11; worked on 3.14.6 [Y1][X3] |
| uvloop / httptools (uvicorn `standard` extra) | 0.23.0 / 0.9.0 | | cp314 wheels published [Y1] |

- FastAPI 0.143.2 to 0.146.0 all declare `starlette>=0.46.0`, `pydantic>=2.9.0` and `opentelemetry-api>=1.44.0` as core dependencies [Y1].
- Starlette's `full` extra lists both "httpx2>=2.0.0" and "httpx<0.29.0,>=0.27.0" [Y1].

### 1.2 Changes since FastAPI 0.143

| Version | Change (quoted from the release notes [F1]) | Effect on NeonRadar |
|---|---|---|
| 0.143.0 (2026-10-08) | "Automatic OpenTelemetry exporter setup is now opt-in." | Good for offline use. Still pass `telemetry={"auto_configure": False}`, because "An explicit `auto_configure` value in the `telemetry` dictionary overrides `FASTAPI_OTEL_AUTO_CONFIGURE`." [F5] |
| 0.143.1 | "Fix included route metadata in `iter_route_contexts()`." | none |
| 0.143.2 | "Fix blocking frontend fallback file checks." | none (`app.frontend()` unused) |
| 0.143.3 | "Fix non-finite float serialization in JSONL and SSE streams." | none |
| 0.143.4 | "Add httpx2 to optional dependencies." | `fastapi[standard]` now pulls httpx2 too |
| 0.143.5 | "Fix handling of empty value for `byte` file list parameter." | none |
| 0.144.0 | "Add WebSocket support to security dependencies." | none |
| 0.145.0 | "Remove deprecated `openapi_prefix` and unused `**extra` from `FastAPI`." | Breaks only code that passes unknown keyword arguments to `FastAPI()` |
| 0.146.0 | "The `root_path` parameter in `FastAPI()` is deprecated. Configure the server with `fastapi run --root-path /api/v1` instead." | Passing `root_path=` now emits `FastAPIDeprecationWarning` [F2] |

- FastAPI says it "provides OpenTelemetry support by default", but "By default, FastAPI uses configured providers without adding exporters." [F5]. No exporter is added unless automatic setup is enabled.
- In the experiment, the same app gave a byte-identical OpenAPI document under FastAPI 0.143.2 with Starlette 1.8.0 and under 0.146.0 with Starlette 1.9.0 (pydantic 2.14.1 in both). Both ran with `-W error` and no warning [X1].

### 1.3 Older changes still worth knowing

- 0.118.0: dependencies with `yield` run their exit code after the response is sent again. 0.121.0 added `scope="request"` to exit before the response [F1]. Do not hold a Neo4j session in a `yield` dependency; open it inside the query helper for the length of the query.
- 0.128.1: "Update `ValidationError` schema to include `input` and `ctx`." [F1]. A patch release changed every OpenAPI document that contains a 422.
- 0.131.0: JSON responses with a response model are serialized by pydantic in Rust [F1].
- 0.132.0: "Now FastAPI checks, by default, that JSON requests have a `Content-Type` header with a valid JSON value, like `application/json`, and rejects requests that don't." [F1]. The docstring explains the reason: "This prevents potential cross-site request forgery (CSRF) attacks that exploit the browser's ability to send requests without a Content-Type header, bypassing CORS preflight checks. In particular applicable for apps that need to be run locally (in localhost)." [F2].
- 0.135.0: "Add support for Server Sent Events." [F1].
- 0.137.0: "Now `router.routes` is no longer a plain list of `APIRoute` objects, it can contain these intermediate objects that can contain additional routers, forming a tree." [F1]. A test that lists routes should read the OpenAPI document or use `fastapi.routing.iter_route_contexts()` [F3].
- Starlette 1.0.0rc1: "Remove `on_startup` and `on_shutdown` parameters from `Starlette` and `Router`." [S1]. FastAPI keeps its own deprecated `on_event` ("Re-implement `on_event` in FastAPI for compatibility with the next Starlette" in 0.128.3), but "If you provide a `lifespan` parameter, `startup` and `shutdown` event handlers will no longer be called. It's all `lifespan` or all events, not both." [F1][F4].
- Starlette 1.9.0: "Stream `TestClient` response bodies, so `client.stream()` returns before the application finishes. Closing an unfinished streamed response now cancels the application" [S1].

### 1.4 Lifespan and dependency injection of the async driver

- The lifespan is an async context manager. The dict it yields becomes request state; Starlette "will not start serving any incoming requests until the lifespan has been run" [S4].
- FastAPI 0.146.0 rejects a dependency annotated `request: Request[State]` (the typed form that the Starlette docs show) with `FastAPIError: Invalid args for response field!`. Use a plain `Request` and `request.state["driver"]` or `request.state.driver` [X8][S4].
- `AsyncDriver` objects "are safe to be used in concurrent coroutines. They are not thread-safe." [D7]. Create the driver inside the lifespan so it lives on the server's event loop.
- Driver construction does no I/O; the first query connects [X5]. Do not fail startup when Neo4j is down. Report it on `/api/v1/health` (Phase 1's `status: "degraded"`) [R1]. uvicorn exits with code 3 on any lifespan startup failure [U1].

```python
"""NeonRadar API: lifespan-owned async Neo4j driver and the dependency that hands it out."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from neo4j import AsyncDriver, AsyncGraphDatabase, NotificationMinimumSeverity


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[dict[str, Any]]:
    driver = AsyncGraphDatabase.driver(
        "bolt://127.0.0.1:7687",
        auth=("neo4j", "from-settings"),
        telemetry_disabled=True,
        connection_timeout=5.0,
        connection_acquisition_timeout=5.0,
        max_transaction_retry_time=2.0,
        max_connection_pool_size=10,
        notifications_min_severity=NotificationMinimumSeverity.WARNING,
    )
    try:
        yield {"driver": driver}
    finally:
        await driver.close()


def get_driver(request: Request) -> AsyncDriver:
    return request.state["driver"]


DriverDep = Annotated[AsyncDriver, Depends(get_driver)]

app = FastAPI(
    title="NeonRadar API",
    version="1.0.0",
    lifespan=lifespan,
    telemetry={"auto_configure": False},
)
```

### 1.5 Problem details (RFC 9457) in FastAPI

- Register handlers for `starlette.exceptions.HTTPException` (it also catches FastAPI's subclass and the router's own 404 and 405), `RequestValidationError`, and the driver errors [X4][X5].
- Forward `exc.headers`. A handler that drops them loses `Allow` on 405; the experiment showed `allow` missing [X4].
- Starlette's `ServerErrorMiddleware` re-raises after sending the 500 response: "We always continue to raise the exception." [S5]. Use `TestClient(app, raise_server_exceptions=False)` or `ASGITransport(app, raise_app_exceptions=False)` to assert a 500 problem body.
- OpenAPI side:
  - `responses={404: {"model": Problem}}` puts the schema under the route's media type, `application/json` [F3][X2].
  - Adding `"content": {"application/problem+json": {}}` produces both a populated `application/json` and an empty `application/problem+json` [X2].
  - The cleanest result came from declaring `responses={404: ..., 422: ..., 503: ...}` with `model=Problem` once on the `APIRouter`, then post-processing the document so every 4xx and 5xx `application/json` key becomes `application/problem+json`. Declaring 422 also stops FastAPI from adding `HTTPValidationError` and `ValidationError`; the components were just `Item` and `Problem` [X2][F3].
  - Use the documented "extending OpenAPI" pattern: assign `app.openapi = custom_function`, cache in `app.openapi_schema` [F10].
  - A `Problem` model with `ConfigDict(extra="allow")` is emitted with `"additionalProperties": true`, which matches RFC 9457 extension members [X1][W1].

### 1.6 Testing: TestClient versus AsyncClient with ASGITransport

| | Starlette `TestClient` (FastAPI re-exports it [F3]) | `httpx.AsyncClient` + `httpx.ASGITransport` |
|---|---|---|
| Test style | synchronous | `async def` tests with pytest-asyncio |
| Event loop | the app runs in another thread on its own loop (anyio portal) | the test's own loop |
| Lifespan | only as a context manager: "If you want the `TestClient` to run the `lifespan` handler, you will need to use the `TestClient` as a context manager." [S2] | never: "If your application relies on lifespan events, the `AsyncClient` won't trigger these events." [F4]. Both httpx 0.28.1 and httpx2 2.14.0 build only `"type": "http"` scopes [H1][H2] |
| With only httpx installed | import emits "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." (a `StarletteDeprecationWarning`, a `UserWarning` subclass, present since Starlette 1.2.0) [S2][S6][X3] | no warning |
| Sharing an async driver with the test | fails: a driver made on the test loop and used by the app gave 500 (simulated with a loop-bound fake) [X3] | works |

Experiment results [X3]: `TestClient` without `with` gave 500 with no lifespan events; with `with` it gave 200 and ran startup and shutdown. `ASGITransport` alone gave 500. `ASGITransport` with `asgi_lifespan.LifespanManager` gave 200. `ASGITransport` with the helper below gave 200. `app.dependency_overrides[get_driver]` worked without any lifespan. With httpx2 2.14.0 installed, importing `TestClient` raised no warning and every test passed under `-W error::UserWarning`.

- In pytest-asyncio 1.4.0 strict mode (the default), an async fixture must use `@pytest_asyncio.fixture`; with plain `@pytest.fixture` the tests errored [X4]. Relevant ini options are `asyncio_mode` (default "strict"), `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope` (default "function") [Y1].
- The real `AsyncDriver` in a lifespan with no server mapped `ServiceUnavailable` to a 503 problem in 2.7 s and closed the driver at shutdown [X5].

```python
"""Test helper: run the app's lifespan and pass its state to every request, with no extra dependency."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


@asynccontextmanager
async def api_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app) as state:

        async def with_state(scope, receive, send):  # type: ignore[no-untyped-def]
            scope["state"] = dict(state or {})
            await app(scope, receive, send)

        transport = httpx.ASGITransport(app=with_state, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            yield client
```

### 1.7 How FastAPI generates OpenAPI 3.1, and snapshot pitfalls

How it works (FastAPI 0.146.0 source [F2][F3]):
- `app.openapi_version` is an attribute, not a constructor parameter: "FastAPI will generate OpenAPI version 3.1.0, and will output that as the OpenAPI version." `info` holds `title` and `version` from `FastAPI(...)`; both must be set when `openapi_url` is on.
- Schemas come from pydantic's `GenerateJsonSchema(ref_template="#/components/schemas/{model}")`, in validation mode for inputs and serialization mode for outputs.
- `components["schemas"] = {k: definitions[k] for k in sorted(definitions)}`, so schemas are sorted. Paths follow route order. The result goes through the `OpenAPI` pydantic model and `jsonable_encoder(..., by_alias=True, exclude_none=True)`. The observed top-level order was `openapi`, `info`, `paths`, `components` [X1].
- `operationId` is `f"{route.name}{route.path_format}"` with non-word characters replaced by `_`, plus `_` and `list(route.methods)[0].lower()`, for example `entity_api_v1_entities__entity_id__get` [F3][X1].
- `separate_input_output_schemas=True` (default) splits a model into `X-Input` and `X-Output` only when its two schemas differ. A plain `list[str] = []` default did not split, but a `Decimal` field did (`Payment-Input`) [X2][X6].
- Model docstrings become `description` (cut at `\f`), and field names become `title` [F3][X1].
- The `/openapi.json` route adds `servers: [{"url": root_path}]` when a root path is set [F2].

Snapshot pitfalls and fixes:
1. Library versions change the document. Proven here: pydantic 2.13.5 to 2.14.1 removed the `pattern` regex from every `Decimal` field schema, input and output ("Refactor `Decimal` JSON Schema `pattern` constraint" [P1]). With it went the only trace of `max_digits` and `decimal_places`. A model without `Decimal` was identical [X6][X1]. FastAPI 0.128.1 changed `ValidationError` [F1]. Lock exact versions and regenerate the snapshot in the same pull request as an upgrade.
2. Build the snapshot from `create_app().openapi()` in-process, not from `/openapi.json` behind a root path.
3. Keep `version=` a fixed contract version ("1.0.0" for C3), never a value computed from git or package metadata.
4. Serialize canonically: `json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"` (Phase 1 already asks for sorted keys and two-space indent [R1]). Store it with LF line endings (`.gitattributes`).
5. Renaming a handler function changes its `operationId` and the generated TypeScript names. A route with several methods takes the first element of a set, whose order depends on string hashing. Give such routes an explicit `operation_id` or avoid them [F3].
6. Adding a computed field or a `Decimal` to a shared model renames `X` to `X-Input`/`X-Output` [X6].
7. Docstring and `Field(description=...)` edits are contract changes [F3].
8. The default `/docs` page loads `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js` and a favicon from fastapi.tiangolo.com, so it does not work offline and floats on the `@5` major tag. Self-host the assets or accept that `/docs` needs internet [F7].

```python
"""Contract test: the app's OpenAPI document equals contracts/openapi/v1.json byte for byte."""

import json
from pathlib import Path

from neonradar_api.main import create_app

SNAPSHOT = Path("contracts/openapi/v1.json")


def canonical(doc: dict) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_openapi_matches_snapshot() -> None:
    actual = canonical(create_app().openapi())
    assert actual == SNAPSHOT.read_text(encoding="utf-8"), "run `make contracts` and review the diff"
```

## 2. Read-only enforcement on Neo4j 5.26 Community

### 2.1 READ access mode on a single Community server (question 2a)

- The driver puts the mode on the wire for any driver type: `if mode in {READ_ACCESS, "r"}:`, then the comment "It will default to mode "w" if nothing is specified", then `extra["mode"] = "r"`, in both RUN and BEGIN [D2]. `execute_query` maps `RoutingControl.READ` to `READ_ACCESS` before `_run_transaction` [D1]. A session needs `default_access_mode=neo4j.READ_ACCESS` for `begin_transaction` and `run` [D1][M1].
- The server decodes `mode`: a missing value is WRITE, "r" is READ, "a" counts as WRITE [N4].
- Community builds a `QueryRouterImpl` for Bolt [N1]. For each statement it computes a statement type from the AST and then runs this check: `if (!(executionMode.isExplain()) && accessMode == AccessMode.READ && statementType.isWrite())`, throwing `Status.Statement.AccessMode` with `WRITING_IN_READ_NOT_ALLOWED_MSG + ". Attempted write to %s"` [N1].
- The statement type is Write for any `UpdateClause` (CREATE, MERGE, SET, DELETE, REMOVE, FOREACH), for a `CALL` whose resolved procedure is not READ or DBMS mode, for schema commands, and for writing admin commands [N2][N17]. EXPLAIN skips the check, so `EXPLAIN CREATE ...` works in a READ session.
- A Community integration test asserts the exact result for the HTTP Query API: code `Neo.ClientError.Statement.AccessMode`, message "Writing in read access mode not allowed. Attempted write to neo4j" [N5]. The status text is "The request could not be completed due to access mode violation" [N6]. The Bolt path uses the same router check; I could not run it (UNVERIFIED end to end).
- In the Python driver this is a plain `neo4j.exceptions.ClientError` (no subclass); match on `exc.code` [D5].
- The guard is in the router, not the kernel. The kernel transaction is begun with the user's login context, and the READ mode only travels as routing information [N13]. In Community the login context is FULL [N11]. A write that the AST check does not see would therefore not be stopped by the transaction itself. One exception: procedures run with their declared mode, as `OverriddenAccessMode(mode, procedureMode)` for FULL users. So a write attempted inside a READ procedure or any function fails with `Neo.ClientError.Security.Forbidden` (a message like "Create node with labels '...' on database 'neo4j' is not allowed for user 'neo4j' with FULL overridden by READ."; runtime text UNVERIFIED) [N11][D5].
- A READ procedure that opens its own transaction, for example `apoc.cypher.runTimeboxed`, which uses `db.beginTx()` "in a separate thread", gets the caller's current security context through `ProcedureLoginContextTransformer`. During the call that context is the READ override, so its writes should fail too (source reading, UNVERIFIED) [A1][N11].
- The driver manual is explicit: "There is no security guarantee that a write query submitted in read mode will be rejected." [M1].
- Correction to Phase 1 research: READ routing is not "irrelevant on single-instance Community". It is enforced there, but only as a statement-type guard [N1][R2].

### 2.2 EXPLAIN and the summary `query_type` (question 2b)

- "`EXPLAIN`: plans the query but does not run it." "Unlike `EXPLAIN`, queries prepended with `PROFILE` can write data to the database." [C3].
- How the type is chosen, in `CypherCurrentCompiler.getQueryType` [N3]:
  1. Admin commands give DBMS.
  2. Schema commands give SCHEMA_WRITE.
  3. A plan containing a DBMS-mode procedure gives DBMS (or DBMS_READ).
  4. A read-only plan gives READ_ONLY.
  5. A plan with no result columns gives WRITE; otherwise READ_WRITE.
- A procedure call is read-only when its mode is READ, DEFAULT or DBMS (`ProcedureCallProjection.readOnly = call.containsNoUpdates`) [N3][N2]. Command clauses keep the default `readOnly = true` [N3].
- Bolt then maps: `case SCHEMA_WRITE, DBMS -> SCHEMA_WRITE;` with codes `'r'`, `'r','w'`, `'w'` and `'s'` [N4]. The driver documents "``'r'`` = read-only, ``'rw'`` = read/write, ``'w'`` = write-only, ``'s'`` = schema." and raises `BoltProtocolError` on any other value [D4].

| Statement (5.26, Cypher 5) | READ session | `query_type` (source reading) |
|---|---|---|
| `MATCH ... RETURN ...` | allowed | "r" |
| CREATE, MERGE, SET, DELETE, REMOVE, FOREACH with `RETURN` | rejected, `Statement.AccessMode` | "rw" |
| the same without result columns | rejected | "w" |
| `CALL` of a READ or DEFAULT-mode procedure (`db.labels`, `apoc.meta.stats`, `apoc.load.json`, `apoc.export.csv.query`, `apoc.cypher.run`, `apoc.util.sleep`, `apoc.periodic.cancel`) | allowed | "r" |
| `CALL` of a WRITE-mode procedure (`apoc.periodic.iterate`, `apoc.cypher.doIt`, `apoc.import.json`) | rejected | "rw" (or "w" without columns) |
| `CALL` of a SCHEMA-mode procedure (`apoc.schema.assert`, `apoc.import.csv`, `apoc.cypher.runSchema`) | rejected | "rw" or "w", not "s" |
| `CALL` of a DBMS-mode procedure (`dbms.components`, `dbms.listConnections`, `dbms.killConnections`, `db.clearQueryCaches`, `tx.setMetaData`) | allowed | "s" |
| `CREATE INDEX ...`, `CREATE CONSTRAINT ...` | rejected | "s" |
| `LOAD CSV ... RETURN ...` | allowed | "r" |
| `SHOW TRANSACTIONS`, `SHOW PROCEDURES`, `TERMINATE TRANSACTIONS 'id'` | allowed (command clauses are not update clauses) | "r" |
| a user-defined function that writes (for example `apoc.cypher.runFirstColumnSingle("CREATE ...", {})`) | allowed at planning, fails at run time with `Security.Forbidden` | "r" |

The runtime values in this table are UNVERIFIED: I derived them from source and could not run a server. Procedure modes come from the APOC Core 5.26.32 annotations [A1] and the built-in procedure table [O4].

Consequences:
- "r" means "no update clause and no write or schema procedure". It does not mean "no side effects". `LOAD CSV`, READ procedures with file or network access, and `TERMINATE TRANSACTIONS` all pass [N3][N17].
- A check that requires exactly "r" also rejects DBMS procedures. Keep system queries such as Phase 1's `CALL dbms.components()` health query out of the template path, or expect "s" for them [N4][R1].
- `apoc.cypher.run` hides its inner statement from EXPLAIN; the outer plan only shows a procedure call [A1][C3].
- The Bolt plan map has the keys `operatorType`, `args`, `identifiers` and `children` [N4]. The query router appends the database name to every operator: `innerPlanDescription.getName() + "@" + graphName`, for example `ProduceResults@neo4j` [N14]. A plan-operator allowlist must strip the suffix. Operator names to block include `ProcedureCall`, `LoadCSV`, `TerminateTransactions` and the `Show...` operators [C3].

### 2.3 Read clauses and procedures that reach files or the network (question 2c)

| Feature | Mode / type | File access | Network access | Controls in 5.26 Community |
|---|---|---|---|---|
| `LOAD CSV FROM 'file:///...'` | clause, "r" | yes | no | `dbms.security.allow_csv_import_from_file_urls` (default true); when false the error is "configuration property 'dbms.security.allow_csv_import_from_file_urls' is false". With `server.directories.import` set, every path is resolved inside that folder after normalisation, so `file:///etc/passwd` means `<import>/etc/passwd` [O1][N8] |
| `LOAD CSV FROM 'http(s)://...'` or `ftp://` | clause, "r" | no | yes | "`LOAD CSV` supports accessing CSV files via HTTPS, HTTP, and FTP (with or without credentials)." [C1]; only `internal.dbms.cypher_ip_blocklist` in Community [N7][N8] |
| `apoc.load.json`, `apoc.load.jsonArray`, `apoc.load.jsonParams`, `apoc.load.xml` | READ, "r" | only with `apoc.import.file.enabled=true` (default false) | yes, always | APOC checks web URLs with Neo4j's `URLAccessChecker`, so the blocklist applies [A1][A2][N7] |
| `apoc.load.csv` | APOC Extended (not installed) | | | not in Core 5.26.32 [A3] |
| `apoc.export.csv.*`, `.json.*`, `.cypher.*`, `.graphml.*` | READ, "r" | writes files only with `apoc.export.file.enabled=true` (default false); streaming still allowed | no | "Export to files not enabled, please set apoc.export.file.enabled=true in your apoc.conf." [A1][A2] |
| `apoc.import.csv` (SCHEMA), `apoc.import.json`, `.graphml`, `.xml` (WRITE) | rejected in READ | | | [A1] |
| `apoc.cypher.run` (READ), `apoc.cypher.runFirstColumnMany` and `Single` (functions) | "r" | through inner Cypher | through inner Cypher | "Runs a dynamically constructed read-only statement with the given parameters." [A1]. `apoc.cypher.runFirstColumn` no longer exists in 5.26.32 [A1] |
| `apoc.cypher.runTimeboxed` | READ, "r" | through inner Cypher | through inner Cypher | runs in its own transaction and thread [A1] |
| `apoc.periodic.commit`, `iterate`, `submit`, `repeat`, `countdown` | WRITE, rejected | | | `apoc.periodic.list` and `apoc.periodic.cancel` are READ [A1] |
| `dbms.*` (Community): `components`, `info`, `listConfig`, `listConnections`, `killConnection(s)`, `queryJmx`, `routing.getRoutingTable`, `showCurrentUser` | DBMS, "s" | no | no | admin-only procedures are allowed for every Community user [O4][N11] |
| `db.*` READ procedures with side effects (`db.resampleIndex`, `db.resampleOutdatedIndexes`, `db.stats.collect`) | READ, "r" | no | no | built in, so the allowlist cannot remove them [O4][N12] |

Settings, verified against the 5.26 settings page and source:
- `dbms.security.procedures.allowlist`: "A list of procedures (comma separated) that are to be loaded. ... The default (`*`) loads all procedures. If no value is specified, no procedures will be loaded." [O1]. "If using this setting, no extensions other than those listed will be loaded." [O3]. Built-in `db.*` and `dbms.*` procedures are registered with full access, which bypasses the check: `if (fullAccess || config.isWhitelisted(procName.toString()))` [N12].
- `dbms.security.procedures.unrestricted`: "Note that this enables these procedures to bypass security. Use with caution." [O1]. The Docker image adds `apoc.*` and `gds.*` to it for `NEO4J_PLUGINS` [K1].
- `server.directories.import`: "Removing this setting will disable the security feature, allowing all files in the local system to be imported." [O1]. The shipped conf sets `server.directories.import=import` [N15]. The Docker entrypoint uses `/import` when that folder is mounted [K1]. Confinement only applies when the setting is explicitly set (`config.isExplicitlySet(...)`). The code builds the path relative to the import root ("normalize to prevent path traversal exploits like '../'") [N8].
- `apoc.import.file.enabled`: "Enables reading local files from disk." (default false). `apoc.export.file.enabled`: "Enables writing local files to disk." (default false). `apoc.import.file.use_neo4j_config` defaults to true and applies Neo4j's file settings [A4][A2]. APOC reads these from `apoc.conf` or environment variables ("any env setting will override options set in apoc.conf.") [A4]. The Docker entrypoint writes `NEO4J_apoc_*` variables to `conf/apoc.conf` [K1].
- `internal.dbms.cypher_ip_blocklist`: defined in `GraphDatabaseInternalSettings` with the description "A list of CIDR-notation IPv4 or IPv6 addresses to block when accessing URLs.This list is checked when LOAD CSV or apoc.load.json is called." and default empty [N7]. It is not in the Operations Manual [O1]. Strict validation accepts it because `internal.` is a supported namespace and the setting is declared [N7]. In Docker it is `NEO4J_internal_dbms_cypher__ip__blocklist` (underscores become dots, double underscores become one underscore) [K1].
- How the blocklist is applied [N8]:
  - `WebURLAccessRule` resolves the host first (`InetAddress.getByName(url.getHost())`), then tests each range, and fails with `"access to " + inetAddress + " is blocked via the configuration property " + GraphDatabaseInternalSettings.cypher_ip_blocklist.name()`.
  - It re-checks every redirect hop and pins plain http and ftp to the resolved IP.
  - The code comment says "Keep doing this for community". So `0.0.0.0/0,::/0` would block all web URLs, but the DNS query still leaves the machine. What `LOAD CSV` reports at run time is UNVERIFIED.
- `dbms.cypher.ip_blocklist` does not exist in 5.26.32. The checked-out Community modules declare only the `internal.` name, migrated from `unsupported.dbms.cypher_ip_blocklist`, and the 5.x settings page has no blocklist entry [N7][O1]. The LOAD privileges (`GRANT LOAD ON CIDR ...`) are Enterprise ("page-role: enterprise-edition") [O6].
- The GenAI plugin, whose procedures call external providers, and APOC Core "have to be installed separately on on-prem servers" [O4]. NeonRadar installs only APOC and GDS through `NEO4J_PLUGINS` [R1].

### 2.4 Transaction limits (question 2d)

| Control | Default | Scope | What fires | Source |
|---|---|---|---|---|
| `neo4j.Query(text, timeout=s)` or `session.begin_transaction(timeout=s)` | none | one transaction | `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration`: "The transaction has not completed within the timeout specified at its start by the client. You may want to retry with a longer timeout." | [D3][N6][N10] |
| `db.transaction.timeout` | `0s` (off), dynamic | default for transactions without their own timeout | `Neo.ClientError.Transaction.TransactionTimedOut` exists, but over the HTTP API a Community test expects `TransactionTimedOutClientConfiguration` even for this setting | [O1][N6][N10] |
| `db.transaction.monitor.check.interval` | `2s` | how often timeouts are checked | a timeout fires up to about 2 s late | [N7] |
| `db.memory.transaction.max` | `0B` ("Zero means 'largest possible value'.") | one transaction | `Neo.TransientError.General.MemoryPoolOutOfMemoryError`, message format `"The allocation of an extra %s would use more than the limit %s. Currently using %s. %s threshold reached"` with the setting name last | [O1][N9][N6] |
| `db.memory.transaction.total.max` | `0B` (unlimited) | all transactions of one database | same status | [O1][N9] |
| `dbms.memory.transaction.total.max` | "Defaults to 70% of the heap size limit." | all transactions | same status | [O1][N9] |
| `db.transaction.concurrent.maximum` | 1000 | concurrent transactions | | [O1] |

- Timeout semantics: "Starting from Neo4j 5.3, you can set the transaction timeout to any value, even larger than configured by `db.transaction.timeout`." [O2]. The driver docstring agrees: "Values higher than ``db.transaction.timeout`` will be ignored and will fall back to the default for server versions between 4.2 and 5.2 (inclusive)." [D3]. So the server setting is a default, not a cap. The client timeout is the control.
- Do not set a server-wide `db.transaction.timeout` for the shared instance. It would also apply to loader and detector transactions that set no timeout, such as the long auto-commit statements that use `CALL { } IN TRANSACTIONS` [R1].
- Memory errors are `TransientError`s and retryable, so `execute_query` and `execute_read` retry them until `max_transaction_retry_time` (30 s by default) [D5][N6]. Timeouts are `ClientError`s and are never retried [D5].
- Phase 3 already recommends `NEO4J_db_memory_transaction_max=1G` with the 2G heap (512M in tests) [R2].
- The 5.26 settings page labels `db.transaction.timeout` as dynamic only, not Enterprise [O1]. On Community, dynamic settings still need a restart, because `dbms.setConfigValue` is Enterprise only [O4].

### 2.5 Users and roles in Community (question 2e)

- "In Neo4j Community Edition there are no roles, but all users have implied administrator privileges." [O5]. The edition table shows role-based access control and sub-graph access control only for Enterprise [O5].
- In source, the Community `SecurityContext` grants admin procedures and admin actions (`PermissionState.EXPLICIT_GRANT`), and authenticated users get `AccessMode.Static.FULL` [N11].
- "All users may terminate their own currently executing transactions." [O7]. The API and the loaders use the same `neo4j` user, so the API's credential can end the loader's transactions; and in Community `allowsAdminAction` grants every admin action anyway [N11][R1].
- Meaning for defence in depth:
  - The API's Neo4j password is equivalent to admin. Keep it out of the repository and logs, as Phase 1 does with `.env` [R1].
  - A second native user for the API would only label its transactions in `SHOW TRANSACTIONS`; it restricts nothing.
  - Read-only databases (`server.databases.read_only`, `server.databases.default_to_read_only`) exist in Community, but the API shares the database that loaders write to, so they do not fit [O1].
  - Every layer must live in the API code and the server configuration (section 6).

## 3. The Neo4j Python driver 6.x async API

### 3.1 Construction and lifespan

- `AsyncGraphDatabase.driver(uri, auth=...)` gives `AsyncBoltDriver` for `bolt://` [X5][D7].
- Unknown options raise `ConfigurationError: Unexpected config keys: ...` [X5].
- 6.0: "No longer implicitly closing drivers and sessions in `__del__()` (finalizer/destructor)." An unclosed driver produced `ResourceWarning: unclosed  AsyncBoltDriver` in the experiment. "Calling `driver.close()` again is now a no-op." Using a closed driver raised `DriverError: Driver closed` [D6][X5].
- Defaults: `max_connection_pool_size = 100`, `connection_timeout = 30.0`, `connection_write_timeout = 30.0`, `connection_acquisition_timeout = 60.0`, `max_transaction_retry_time = 30.0`, `fetch_size = 1000` [D5].
- `telemetry_disabled`: "By default, the driver will send anonymous usage statistics to the server it connects to if the server requests those." [D7].

### 3.2 `execute_query`

- Signature: `execute_query(query_, parameters_=None, routing_=RoutingControl.WRITE, database_=None, impersonated_user_=None, bookmark_manager_=..., auth_=None, result_transformer_=AsyncResult.to_eager_result, **kwargs)` [D1].
- The docstring explains the retries: "The internal usage of transaction functions provides a retry-mechanism for appropriate errors." It also notes that `CALL {} IN TRANSACTIONS` "will not work (use :meth:`AsyncSession.run` for these)" [D1].
- The default is WRITE, so a forgotten `routing_` silently allows writes [D1]. Wrap every template call in one helper.
- Keyword checks: "keyword parameters must not end with a single '_'". `timeout_=3` raised `ValueError` [D1][X5]. `RoutingControl.READ == "r"` [D5].
- `result_transformer_` "might get invoked more than once", because of retries [D1].

### 3.3 `Query` and timeouts

- `Query(text: LiteralString, metadata=None, timeout=None)`. timeout is "the transaction timeout in seconds. Transactions that execute longer than the configured timeout will be terminated by the database." "A ``0`` duration will make the transaction execute indefinitely." [D3].
- `execute_query` reads `query_.timeout` and `query_.metadata` through `unit_of_work` (since 5.15 it accepts a `Query`) [D1].
- Template text loaded from files needs `cast(LiteralString, text)` for mypy (Phase 3 does the same) [D3][R2].

### 3.4 Notification filters

- "By default, the server analyses each query for all categories and severity of notifications." [M1].
- `notifications_min_severity` takes `NotificationMinimumSeverity` OFF, WARNING or INFORMATION [D5].
- `notifications_disabled_classifications` takes `NotificationDisabledClassification` values HINT, UNRECOGNIZED, UNSUPPORTED, PERFORMANCE, DEPRECATION, GENERIC, SECURITY, TOPOLOGY ("Requires server version 5.13 or newer.") and SCHEMA ("Requires server version 5.17 or newer.") [D5].
- `notifications_disabled_categories` is deprecated in 6.0; using it emitted `DeprecationWarning: notifications_disabled_categories is deprecated, use notifications_disabled_classifications instead.` [D6][X5].
- `warn_notification_severity`: "Set the minimum severity for server notifications that should cause the driver to emit a :class:`.Neo4jWarning`." [D7].
- To surface deprecations in CI, create the test driver with `warn_notification_severity="WARNING"` and make `neo4j.warnings.Neo4jWarning` an error in pytest. Deprecations are GQL status `01N00` ("feature deprecated", condition WARNING, classification DEPRECATION) [N16]. For production, WARNING is enough; log any `01N` status [D4][N16].

### 3.5 The result summary

- `query_type: t.Literal["r", "rw", "w", "s"] | None` [D4].
- `counters.contains_updates` and `counters.contains_system_updates`: "whether the query triggered any write operation on the database on which it ran" and "on the `system` database" [M1][D4].
- `gql_status_objects` "always contains at least one entry, containing the outcome status" [M1]. It was stabilized in 6.0. `notifications` and `summary_notifications` are deprecated: "ResultSummary.notifications is deprecated, use ResultSummary.gql_status_objects instead." [D4][D6].
- `plan` holds the EXPLAIN plan as a dict [D4][N4].

### 3.6 Retries, cancellation and errors

- Managed transactions retry `TransientError`s and retryable driver errors. Against a closed port, `execute_query` logged "Transaction failed and will be retried in ..." twice and raised `ServiceUnavailable` after 3.6 s, with `max_transaction_retry_time=3.0` [X5].
- Auto-commit (`session.run`) retries once on errors the DBMS marks idempotent. "At the time of writing, this set encompasses only admission control errors." `disable_auto_commit_retries` (since 6.2) turns that off [D7].
- Cancellation: "any cancellation of I/O work will cause the driver to close the affected connection." [D7]. Whether the server then stops the query at once is UNVERIFIED, so keep the server-side timeout shorter than any client-side `asyncio.timeout`.
- `Neo.ClientError.Security.Forbidden` maps to `neo4j.exceptions.Forbidden`. `Statement.AccessMode` and the timeout codes are plain `ClientError`s [D5].
- After a partial `fetch`, `consume()` discards the rest. For a READ_ONLY query the server simply cancels it ("if the query has no side effects, and we wish to discard all remaining results, we'll simply terminate it") [N4].

## 4. Hardening the local API

### 4.1 Binding

- uvicorn's `--host` defaults to "127.0.0.1" [U1]. Phase 1 already runs `neonradar api serve` on 127.0.0.1, uses `0.0.0.0` inside the container, and publishes ports as `127.0.0.1:8000:8000` [R1].
- `fastapi run` "listens on the IP address `0.0.0.0`, which means all the available IP addresses" [F8]. Do not document it for local use.
- The Docker image defaults `server.default_listen_address` to `0.0.0.0`. Phase 1 publishes Bolt and HTTP on 127.0.0.1 only [K1][R1].
- Neo4j's HTTP connector sends `Access-Control-Allow-Origin: *` by default ("This defaults to '*', which allows broadest compatibility.") [O1]. Auth is still required.

### 4.2 Host header and DNS rebinding

- The API has no authentication, so a page that rebinds its own name to 127.0.0.1 could read API responses. That includes the real-data API on port 8001 [R1].
- Vite warns about the same risk for its dev server: it "allows any website to send requests to your dev server through DNS rebinding attacks" [W4].
- `TrustedHostMiddleware` "Enforces that all incoming requests have a correctly set `Host` header" [S3]. It ignores the port and, since 1.9.0, compares case-insensitively [S5][S1]. A request with `Host: evil.example:8000` got 400 "Invalid host header" (plain text) [X4].
- Allowed hosts: `127.0.0.1`, `localhost`, `[::1]`. Add `api` because Phase 1's nginx proxies `/api/` to `http://api:8000`, and NGINX sets "Host" to `$proxy_host` by default (or set `proxy_set_header Host $host`) [R1][W5].

### 4.3 CORS

- In development the Vite proxy (Phase 1: "Vite dev server proxy `/api` to `http://127.0.0.1:8000`") makes requests same-origin, so CORS is only needed for direct calls [R1].
- If kept: `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]`, `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type"]`, no credentials. Vite's default port is 5173 [W4]. Leave `allow_private_network` at its default False [S3].
- In the experiment the allowed preflight got 200 with `access-control-allow-origin: http://localhost:5173`. A preflight from `https://evil.example` got 400 "Disallowed CORS origin" [X4].
- Strict Content-Type: a body with no `Content-Type` or with `text/plain` got 422, so simple cross-site POSTs cannot submit JSON [X4][F4].

### 4.4 Request body size

- Starlette 1.6.0: "Add `max_body_size` to `Starlette` and route classes" [S1]. FastAPI 0.146.0 does not expose `max_body_size`, but `app.add_middleware(RequestBodyLimitMiddleware, max_body_size=...)` from `starlette.middleware.body_limit` works [F2][S3][X4].
- The docs: "Starlette counts the actual body bytes received from the ASGI server. `Content-Length` is used only to reject an oversized request early and is not trusted to enforce the limit." [S3].
- Experiment with a 1024-byte limit [X4]:
  - an oversized body with `Content-Length` got 413 `text/plain` "Content Too Large", because the middleware replaces the response;
  - a chunked oversized body got 413 `application/problem+json` from the app's handler.
- 64 KiB is ample, since a `CopilotRequest` question is at most 500 characters [R1].
- uvicorn has no body limit; its options cover connections and keep-alive [U1].

### 4.5 Rate limiting and concurrency

- Not worth it for one local user. slowapi 0.1.10 (2026-06-13) exists, but its classifiers stop at 3.13 and it adds the `limits` dependency [Y1].
- Two cheaper controls:
  - an `asyncio.Semaphore` (for example 2) around copilot queries, answering 503 "busy" when it cannot be acquired within about 1 s;
  - optionally uvicorn's `--limit-concurrency`: "Maximum number of concurrent connections or tasks to allow, before issuing HTTP 503 responses." [U1].
- Community runs each query on one thread, so a few parallel heavy queries can saturate a laptop [R2].

### 4.6 Problem details

- RFC 9457: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type." [W1].
- Members: "type" is "a JSON string containing a URI reference that identifies the problem type"; "When this member is not present, its value is assumed to be "about:blank"." [W1].
- "status" "is only advisory" [W1].
- "Clients consuming problem details MUST ignore any such extensions that they don't recognize". Extra members such as `errors` or `template_id` are therefore fine [W1].
- "This document obsoletes RFC 7807." [W1].
- With `about:blank`, "the title SHOULD be the same as the recommended HTTP status phrase for that code." [W1].
- Never put stack traces or Cypher errors verbatim in `detail` ("avoid making implementation details such as a stack dump available through the HTTP interface") [W1].
- Mapping used in the experiments [X4][X5]:
  - validation 422 (with an `errors` list of `loc`, `msg` and `type`);
  - unknown route 404 and method 405 (forward `Allow`);
  - body too large 413;
  - `ServiceUnavailable`, `SessionExpired`, timeouts and `MemoryPoolOutOfMemoryError` 503 (Phase 2 already maps query timeouts to 503 [R1]);
  - `Statement.AccessMode` or a non-"r" summary 500, logged as a template defect.

### 4.7 Cursor pagination

- "Unless `ORDER BY` is used, Neo4j does not guarantee the row order of a query result." [C5]. Order by a total key, for example `(created_at DESC, alert_id ASC)`.
- "`LIMIT` accepts any expression that evaluates to a positive `INTEGER`, does not contain any variables and does not refer to nodes or relationships." [C5]. Ask for `limit + 1` rows to learn whether a next page exists.
- Cursor: base64url of a small JSON object `{"v": 1, "k": [last_created_at, last_alert_id], "f": "<first 16 hex of sha256 of the filters>"}`. Decode it with a pydantic model, cap it at 200 characters, and answer 400 when the filters differ. Never put Cypher in a cursor. Signing is unnecessary on a local, single-user API.
- Use the OR form below. Cypher 5 has no row-value comparison.

```cypher
MATCH (a:Alert)
WHERE $after_id IS NULL
   OR a.created_at < $after_created_at
   OR (a.created_at = $after_created_at AND a.alert_id > $after_id)
RETURN a.alert_id AS alert_id, a.created_at AS created_at
ORDER BY created_at DESC, alert_id ASC
LIMIT $page_size_plus_one
```

### 4.8 Request timeouts

- uvicorn has no per-request timeout; `--timeout-keep-alive` (default 5) only closes idle connections [U1].
- Use three nested limits:
  1. the server-side transaction timeout (for example 5 s);
  2. an `asyncio.timeout` in the handler at that timeout plus the 2 s monitor interval plus a margin (for example 8 s);
  3. driver `connection_acquisition_timeout` and `max_transaction_retry_time` of a few seconds, so a saturated pool or a dead server answers 503 quickly [D5][N7][X5].
- An `asyncio.timeout` in a handler produced a clean 503 problem in the experiment [X4].

### 4.9 Offline concerns

- FastAPI telemetry: pass `telemetry={"auto_configure": False}`. FastAPI also offers `tracing`, `metrics` and `logs` switches [F5].
- The Swagger UI and ReDoc assets come from a CDN by default [F7]. Self-host them or accept that `/docs` needs internet.
- The Neo4j driver: `telemetry_disabled=True` [D7].

## 5. Streaming (server-sent events) for the copilot

- FastAPI has native SSE: "Added in FastAPI 0.135.0." Use `response_class=EventSourceResponse` from `fastapi.sse` with a generator. FastAPI sends a keep-alive comment "every 15 seconds when there hasn't been any message", sets `Cache-Control: no-cache` and `X-Accel-Buffering: no` [F6]. sse-starlette 3.5.0 is not needed [Y1].
- A POST SSE route worked with `TestClient.stream` and returned `text/event-stream; charset=utf-8` [X7].
- Its OpenAPI entry uses `itemSchema` [X7], which the OpenAPI Initiative describes as an OpenAPI 3.2 addition ("OpenAPI 3.2 introduces support for sequential and streaming media types") [W3]. The document still says 3.1.0. How `openapi-typescript` handles that is UNVERIFIED.
- Browser side: the `EventSource` constructor takes a URL and an options object whose only documented entry is `withCredentials` [W2]. A POST question would need `fetch()` with a stream reader in the Vue app.
- Errors after the first byte cannot change the HTTP status. The client then has to parse an error event instead of a problem document.
- Starlette 1.9.0 changed `TestClient` streaming the day before this research [S1].
- Verdict: no SSE in Phase 4. Templates answer in a few seconds. A single `POST /api/v1/copilot/ask` JSON response, a spinner and a client timeout are simpler and keep the C3 contract (`CopilotAnswer`) as one typed object [R1]. Reconsider only if an LLM summarisation step takes several seconds on CPU.

## 6. For the spec writer: the defence-in-depth stack, pins and tests

### 6.1 Running a catalog template safely

| Layer | What to do | What it stops | Sources |
|---|---|---|---|
| 1. Request validation | pydantic models with `extra="forbid"`, bounded strings, an enum of template ids, typed slots (id patterns, ranges); strict Content-Type stays on | smuggled fields (a `cypher` field got 422), oversized or malformed input | [F2][X4] |
| 2. Closed catalog | each template is a committed `.cypher` file with a manifest (id, parameter schema, `max_rows`, timeout, sha256); values only as parameters; labels and relationship types chosen from fixed, pre-rendered variants | Cypher injection | [C2] |
| 3. Build-time checks | a lint that rejects update clauses, `CALL` except allowlisted names, `LOAD CSV`, `USE`, `SHOW`, `TERMINATE`, `CALL { } IN TRANSACTIONS`, `apoc.cypher.*` and `apoc.load.*`; in the Testcontainers job run `EXPLAIN` on every template with sample parameters and require `query_type == "r"`, plan operators (without the `@neo4j` suffix) from an allowlist, and no `01N` status | template mistakes | [N3][N4][N14][N16] |
| 4. Start-up check | verify every template's sha256 against the manifest; optionally EXPLAIN each once and refuse to start serving templates that are not "r" | drift between files and manifest | [N4] |
| 5. READ access mode | one helper opens `driver.session(database="neo4j", default_access_mode=READ_ACCESS)` and `begin_transaction(timeout=..., metadata=...)` | update clauses, WRITE and SCHEMA procedures and schema commands, rejected with `Statement.AccessMode` | [D1][D2][N1][N5] |
| 6. Never commit | `await tx.close()` in `finally` ("Close this transaction, triggering a ROLLBACK if not closed.") | any in-transaction write that slipped through; not side effects outside the database | [D3] |
| 7. Bounded work | transaction timeout of about 5 s; `db.memory.transaction.max` on the server; `result.fetch(max_rows + 1)` then `consume()`; `LIMIT $limit` in templates; a semaphore | runaway queries, memory blow-ups, huge responses | [D3][N9][N4] |
| 8. Summary tripwire | require `summary.query_type == "r"` and `contains_updates` and `contains_system_updates` both False; otherwise log and answer 500 | defects | [D4] |
| 9. Server capability reduction | `NEO4J_dbms_security_procedures_allowlist=apoc.version,apoc.meta.stats,apoc.coll.*,gds.*`; keep `apoc.import.file.enabled` and `apoc.export.file.enabled` false (defaults); keep `server.directories.import` set | file and network side effects from APOC; Browser users also lose other APOC procedures (trade-off) | [O1][O3][A2][A4][R1] |
| 10. Network edge | API and Neo4j bound or published on 127.0.0.1; `TrustedHostMiddleware`; CORS only for the Vite origin in development | other machines and DNS rebinding | [U1][S3][W4][R1] |

The APOC names in layer 9 are everything Phases 1 to 3 call: `apoc.version()`, `apoc.meta.stats()`, `apoc.coll.toSet` and `apoc.coll.sort`. All four exist in APOC Core 5.26.32 [R1][A1]. Prove the allowlist in CI: `SHOW PROCEDURES` must not list `apoc.load.json`, and `RETURN apoc.version()`, `CALL apoc.meta.stats()` and `RETURN gds.version()` must still work.

```python
"""The one way the API runs a catalog template."""

import asyncio
from dataclasses import dataclass
from typing import Any, LiteralString, cast

import neo4j
from neo4j import AsyncDriver

TX_TIMEOUT_S = 5.0
CLIENT_TIMEOUT_S = 8.0  # server timeout + 2 s monitor interval + margin


@dataclass(frozen=True)
class Template:
    template_id: str
    text: str  # from a committed .cypher file, sha256-checked at start-up
    max_rows: int


class TemplateRefused(RuntimeError):
    """The server summary shows something other than a pure read."""


async def run_template(
    driver: AsyncDriver, tpl: Template, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool]:
    async with asyncio.timeout(CLIENT_TIMEOUT_S):
        async with driver.session(database="neo4j", default_access_mode=neo4j.READ_ACCESS) as session:
            tx = await session.begin_transaction(
                metadata={"app": "neonradar-api", "template": tpl.template_id},
                timeout=TX_TIMEOUT_S,
            )
            try:
                result = await tx.run(cast(LiteralString, tpl.text), params)
                records = await result.fetch(tpl.max_rows + 1)
                summary = await result.consume()
            finally:
                await tx.close()  # rolls back: a read never commits
    if (
        summary.query_type != "r"
        or summary.counters.contains_updates
        or summary.counters.contains_system_updates
    ):
        raise TemplateRefused(f"{tpl.template_id}: query_type={summary.query_type!r}")
    truncated = len(records) > tpl.max_rows
    return [record.data() for record in records[: tpl.max_rows]], truncated
```

An explicit transaction is not retried; the driver only retries transaction functions, and `is_retryable()` exists for custom retry policies with explicit transactions. That is intended: the API fails fast and the UI can retry [D1][D5].

In layer 2, Cypher 5.26 can take labels and relationship types from parameters with `$(...)` [C2][C4]. The planner uses token lookup indexes for such dynamic labels only from 2025.08 [C4], so in 5.26 pre-rendered variants are the faster choice.

```yaml
# compose.yaml additions for the default Neo4j instance (sizes from Phase 3 research)
services:
  neo4j:
    environment:
      NEO4J_dbms_security_procedures_allowlist: "apoc.version,apoc.meta.stats,apoc.coll.*,gds.*"
      NEO4J_db_memory_transaction_max: "1G"
      # Future free-text mode only (internal, undocumented setting; test before use):
      # NEO4J_internal_dbms_cypher__ip__blocklist: "0.0.0.0/0,::/0"
```

### 6.2 What a future free text-to-Cypher mode would add

1. Per-request `EXPLAIN` in a READ session. Require "r", then walk `plan` (`operatorType`, `children`) and accept only read operators. Reject `ProcedureCall` unless the procedure is allowlisted (where its name sits in `args` is UNVERIFIED), and reject `LoadCSV`, `TerminateTransactions`, every `Show...` operator, `TransactionApply` and `TransactionForeach`, and every create, merge, set or delete operator [C3][N4][N14].
2. A text lint before EXPLAIN: one statement; no leading `EXPLAIN`, `PROFILE` or `CYPHER` options (`PROFILE` runs the query [C3]); no `USE`; no `CALL { } IN TRANSACTIONS`; a length cap.
3. Server capability reduction:
   - an allowlist without `apoc.load.*`, `apoc.export.*`, `apoc.cypher.*`, `apoc.periodic.*` and `apoc.util.sleep`;
   - `internal.dbms.cypher_ip_blocklist=0.0.0.0/0,::/0` against HTTP exfiltration through `LOAD CSV` and `apoc.load.json`, noting that the DNS lookup still happens first [N8];
   - optionally `dbms.security.allow_csv_import_from_file_urls=false`, which would break the Phase 1 onboarding exercise that loads `file:///companies-20.csv` [R1].
   Built-in `dbms.killConnections`, `db.clearQueryCaches` and `TERMINATE TRANSACTIONS` cannot be removed by configuration [N12][O4]; only the plan check catches them.
4. Network isolation of the Neo4j container (`internal: true` "lets you create an externally isolated network" [W6]) is the only full stop for exfiltration. It conflicts with publishing Bolt to the host for the CLI loaders and with the GDS download at first start (UNVERIFIED design; needs a test).
5. Tighter limits: timeout about 3 s, a smaller `db.memory.transaction.max` if the instance is dedicated, a row cap, concurrency 1.
6. An audit log of question, generated Cypher, plan verdict and outcome. Treat graph text (company and person names from public registers) as untrusted input to the LLM, because it can carry prompt-injection text.
7. Do not rely on the pattern in Neo4j's own `Text2CypherRetriever` (neo4j-graphrag 1.22.0): it runs `EXPLAIN`, requires `query_type` "r" and executes with `RoutingControl.READ` [G1]. Per section 2.2 that admits `LOAD CSV`, READ procedures with side effects and command clauses.

### 6.3 Version pins

| Package | Phase 1 pin | Latest today | Recommendation for Phase 4 | Why |
|---|---|---|---|---|
| fastapi | `>=0.143,<0.144` | 0.146.0 | keep; lock 0.143.5; move to 0.146.x in a separate pull request gated by the snapshot test | nothing in 0.144 to 0.146 is needed; 0.146.0 is one day old [F1][Y1] |
| starlette | none (transitive) | 1.9.0 | add `starlette>=1.8,<1.9` | FastAPI declares only `>=0.46.0`; 1.9.0 changed `TestClient` streaming [Y1][S1] |
| pydantic | `>=2.14,<3` | 2.14.1 | `>=2.14,<2.15` | minor releases change JSON Schema output [P1][X6] |
| uvicorn | unpinned | 0.54.0 | `>=0.54,<0.55` | 0.x minors change behaviour (for example exit codes in 0.50.0) [U1] |
| httpx | `>=0.28,<0.29` | 0.28.1 | keep | used by the ollama client and FastAPI's `standard` extra [Y1] |
| httpx2 | none | 2.14.0 | dev-only `>=2.14,<2.15`, only if `TestClient` is used | silences the Starlette deprecation [S2][X3] |
| neo4j | `>=6.4,<7` | 6.4.1 | keep (lock 6.4.1) | [Y1] |
| pytest | `>=9.1,<10` | 9.1.1 | keep | [Y1] |
| pytest-asyncio | none | 1.4.0 | `>=1.4,<2` | strict mode by default [X4] |
| asgi-lifespan | none | 2.1.0 (2023) | not needed; use the helper in 1.6 | [Y1][X3] |
| sse-starlette, slowapi | none | 3.5.0, 0.1.10 | not needed | [Y1] |

### 6.4 Test approach

- Unit tests (no Neo4j):
  - Build the app with `create_app()` and override `get_driver` with a stub through `app.dependency_overrides`.
  - Use `httpx.AsyncClient` with `ASGITransport` and the helper in 1.6.
  - Assert problem+json bodies and headers for 404, 405 (with `Allow`), 413, 422 and 503; strict Content-Type (422 for `text/plain`); `extra="forbid"`; TrustedHost (400); the CORS preflight; and the OpenAPI snapshot (1.7).
- Warnings: in pytest `filterwarnings`, make these errors: `starlette.exceptions.StarletteDeprecationWarning`, `fastapi.exceptions.FastAPIDeprecationWarning`, `DeprecationWarning` from `neo4j`, and `neo4j.warnings.Neo4jWarning` (with `warn_notification_severity="WARNING"`). The two framework warnings are `UserWarning` subclasses [S2][F2][D7].
- Integration tests (Testcontainers `neo4j:5.26.32-community` with APOC, GDS and the layer 9 settings, as in Phase 3 [R2]):
  1. a write in a READ session raises `ClientError` with code `Neo.ClientError.Statement.AccessMode`, and the probe label count stays 0 [N5];
  2. every template passes EXPLAIN (layer 3);
  3. `Query("UNWIND range(1, 10000) AS a UNWIND range(1, 10000) AS b WITH a, b WHERE a * b < 0 RETURN count(*)", timeout=1.0)` (100 million rows, so well over 1 s; the exact duration is UNVERIFIED) raises a `TransactionTimedOut...` code; allow up to 3 s for the monitor [N7][N10];
  4. a container with `NEO4J_db_memory_transaction_max=10m` makes `UNWIND range(1, 2000000) AS x RETURN collect(x)` raise `MemoryPoolOutOfMemoryError`, and the API answers 503 within the configured retry time [N9][D5]; that 2 million integers exceed 10 MiB is an estimate, UNVERIFIED;
  5. `SHOW PROCEDURES YIELD name` under the allowlist has no `apoc.load.` names, while `apoc.meta.stats` and `gds.version()` work [O3];
  6. `LOAD CSV FROM 'file:///etc/hostname' AS r RETURN r` fails, because it resolves inside the import folder where no such file exists; assert only that it fails, since the error text is UNVERIFIED [N8];
  7. the `run_template` tripwire refuses a template whose summary is not "r" (use a test-only `CALL dbms.components()` template, which should report "s" per section 2.2; the test also confirms that value) [N4].
- Use the real async driver only inside the app's lifespan, or a sync driver for seeding, never one async driver shared across threads [D7][X3].

## Sources

All checked on Monday 19 October 2026. Repository facts come from the commits given.

- [F1] FastAPI release notes, fastapi/fastapi tag 0.146.0 (commit 3070b51), `docs/en/docs/release-notes.md` (sections 0.118.0 to 0.146.0). https://github.com/fastapi/fastapi/blob/0.146.0/docs/en/docs/release-notes.md
- [F2] FastAPI source, same tag: `fastapi/applications.py` (constructor parameters, `openapi_version`, telemetry defaults, `root_path` warning, `strict_content_type` docstring, `openapi()` and `setup()`), `fastapi/exceptions.py` (`FastAPIDeprecationWarning(UserWarning)`).
- [F3] FastAPI source, same tag: `fastapi/openapi/utils.py` (`get_openapi`, 422 handling, `ValidationError` definition, additional responses), `fastapi/utils.py` (`generate_unique_id`), `fastapi/_compat/v2.py` (`get_definitions`), `fastapi/openapi/constants.py`, `fastapi/routing.py` (`iter_route_contexts`), `fastapi/testclient.py`.
- [F4] FastAPI docs, same tag: `docs/en/docs/advanced/strict-content-type.md`, `advanced/async-tests.md`, `advanced/testing-events.md`, `advanced/events.md`.
- [F5] FastAPI docs, same tag: `docs/en/docs/advanced/opentelemetry.md`.
- [F6] FastAPI docs and source, same tag: `docs/en/docs/tutorial/server-sent-events.md`, `docs_src/server_sent_events/`, `fastapi/sse.py`.
- [F7] FastAPI docs and source, same tag: `docs/en/docs/how-to/custom-docs-ui-assets.md`, `fastapi/openapi/docs.py` (default CDN URLs).
- [F8] FastAPI docs, same tag: `docs/en/docs/fastapi-cli.md` (`fastapi dev` and `fastapi run` hosts).
- [F10] FastAPI docs, same tag: `docs/en/docs/advanced/additional-responses.md`, `docs_src/extending_openapi/tutorial001_py310.py`.
- [S1] Starlette release notes, Kludex/starlette tag 1.9.0 (commit 1840c9d), `docs/release-notes.md` (0.48.0 to 1.9.0). https://github.com/Kludex/starlette/blob/1.9.0/docs/release-notes.md
- [S2] Starlette, same tag: `starlette/testclient.py` (httpx2 import and deprecation warning), `docs/testclient.md`, `starlette/exceptions.py` (`StarletteDeprecationWarning(UserWarning)`).
- [S3] Starlette, same tag: `starlette/middleware/body_limit.py`, `docs/routing.md` ("Request body size limits"), `docs/middleware.md` (`RequestBodyLimitMiddleware`, `CORSMiddleware`, `TrustedHostMiddleware`), `docs/requests.md`.
- [S4] Starlette, same tag: `docs/lifespan.md` (lifespan state and access styles).
- [S5] Starlette, same tag: `starlette/middleware/errors.py` (re-raise), `starlette/middleware/trustedhost.py`.
- [S6] Starlette 1.2.0, 1.2.1 and 1.3.0 wheels from PyPI, `starlette/testclient.py` (the deprecation warning is present in all three).
- [U1] uvicorn, Kludex/uvicorn tag 0.54.0 (commit 3eb9a9a): `uvicorn/main.py` (CLI options and defaults), `uvicorn/config.py`, `docs/release-notes.md` (0.38.0 to 0.54.0). https://github.com/Kludex/uvicorn/tree/0.54.0
- [P1] pydantic changelog, pydantic/pydantic tag v2.14.1 (commit b2212c7), `HISTORY.md` (v2.12.0 to v2.14.1). https://github.com/pydantic/pydantic/blob/v2.14.1/HISTORY.md
- [H1] httpx, encode/httpx tag 0.28.1 (commit 26d48e0). https://github.com/encode/httpx/tree/0.28.1
- [H2] httpx2 changelog, pydantic/httpx2 tag v2.14.0 (commit 4fa853a), `src/httpx2/CHANGELOG.md` (no lifespan support in `_transports/asgi.py`). https://github.com/pydantic/httpx2/tree/v2.14.0
- [Y1] PyPI JSON API, for example https://pypi.org/pypi/fastapi/json, for fastapi (and per version 0.143.2, 0.143.5, 0.146.0), starlette (1.8.0, 1.9.0), pydantic, pydantic-core, uvicorn, httpx, httpx2, neo4j, neo4j-rust-ext, pytest, pytest-asyncio, anyio, asgi-lifespan, sse-starlette, slowapi, pydantic-settings, uvloop and httptools; plus the installed pytest-asyncio 1.4.0 `plugin.py` (ini options).
- [X1] Experiment `exp_openapi.py`: OpenAPI of a NeonRadar-like app under FastAPI 0.146.0 with Starlette 1.9.0 and FastAPI 0.143.2 with Starlette 1.8.0 (pydantic 2.14.1); sha256 of both outputs `3dff383d...` (identical). Scripts in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p4/research-api/tools/`.
- [X2] Experiments `exp_problem_media.py` and `exp_problem_openapi.py`: documenting problem+json responses.
- [X3] Experiment `exp_tests/test_lifespan_clients.py`: TestClient, ASGITransport, asgi-lifespan, the manual helper, dependency overrides, the cross-loop simulation, with and without httpx2.
- [X4] Experiment `exp_tests/test_hardening.py`: strict Content-Type, `extra="forbid"`, body limit, TrustedHost, CORS, timeout, 404 and 405 problems.
- [X5] Experiments `exp_driver.py` and `exp_tests/test_real_driver_lifespan.py`: neo4j 6.4.1 driver options, errors and retries with no server (`bolt://127.0.0.1:1`).
- [X6] Experiment `exp_schema_types.py`: `Decimal` and temporal schemas under pydantic 2.13.5 and 2.14.1 (FastAPI 0.146.0).
- [X7] Experiment `exp_sse.py`: native SSE route, its OpenAPI entry and streaming through TestClient.
- [X8] Experiment `exp_typed_state.py`: `Request[State]` in a FastAPI dependency fails; plain `Request` with `request.state["driver"]` works.
- [N1] Neo4j 5.26.32 source, neo4j/neo4j tag 5.26.32 (commit 27f2449): `community/fabric/query-router/src/main/java/org/neo4j/router/impl/QueryRouterImpl.java` (`verifyAccessModeWithStatementType`), `community/fabric/fabric/src/main/java/org/neo4j/fabric/executor/FabricExecutor.java` (`WRITING_IN_READ_NOT_ALLOWED_MSG`), `community/fabric/query-router/src/main/java/org/neo4j/router/CommunityQueryRouterBootstrap.java`. https://github.com/neo4j/neo4j/tree/5.26.32
- [N2] Same tag: `community/fabric/query-router/src/main/scala/org/neo4j/router/impl/query/StatementType.scala`, `community/cypher/front-end/frontend/src/main/scala/org/neo4j/cypher/internal/frontend/phases/ResolvedCall.scala` (`containsNoUpdates`), `.../phases/ProcedureSignature.scala`, `community/cypher/cypher-planner/src/main/scala/org/neo4j/cypher/internal/compiler/helpers/SignatureResolver.scala` (mode mapping, DEFAULT counts as READ).
- [N3] Same tag: `community/cypher/cypher/src/main/scala/org/neo4j/cypher/internal/CypherCurrentCompiler.scala` (`getQueryType`), `.../QueryTypeConversion.scala`, `.../SchemaCommandRuntime.scala`, `community/cypher/runtime-util/src/main/scala/org/neo4j/cypher/internal/runtime/InternalQueryType.scala` and `ProcedureCallMode.scala`, `community/cypher/cypher-planner/src/main/scala/org/neo4j/cypher/internal/compiler/planner/ProcedureCallProjection.scala`, `community/cypher/ir/src/main/scala/org/neo4j/cypher/internal/ir/QueryHorizon.scala` and `PlannerQuery.scala`.
- [N4] Same tag: `community/bolt/src/main/java/org/neo4j/bolt/protocol/common/fsm/response/metadata/DefaultMetadataHandler.java` (type codes and plan keys), `.../protocol/common/message/AccessMode.java`, `.../message/decoder/transaction/AbstractTransactionInitiatingMessageDecoder.java`, `community/bolt/src/main/java/org/neo4j/bolt/tx/statement/StatementImpl.java` (discard terminates read-only queries).
- [N5] Same tag: `community/community-it/query-api-it/src/test/java/org/neo4j/queryapi/QueryResourceConfigIT.java` (`shouldErrorIfWrongAccessModeUsed`).
- [N6] Same tag: `community/common/src/main/java/org/neo4j/kernel/api/exceptions/Status.java`.
- [N7] Same tag: `community/configuration/src/main/java/org/neo4j/configuration/GraphDatabaseSettings.java`, `GraphDatabaseInternalSettings.java` (`cypher_ip_blocklist`), `SettingMigrators.java`, `Config.java` (supported namespaces and strict validation).
- [N8] Same tag: `community/kernel/src/main/java/org/neo4j/kernel/impl/security/WebURLAccessRule.java`, `URIAccessRules.java`, `FileURIAccessRule.java`; `community/kernel-api/src/main/java/org/neo4j/internal/kernel/api/security/SecurityAuthorizationHandler.java` (`assertLoadAllowed`).
- [N9] Same tag: `community/common/src/main/java/org/neo4j/memory/MemoryPoolImpl.java`, `MemoryLimitExceededException.java`, `LocalMemoryTracker.java`; `community/kernel/src/main/java/org/neo4j/kernel/impl/api/TransactionMemoryPool.java`, `KernelTransactions.java`.
- [N10] Same tag: `community/kernel/src/main/java/org/neo4j/kernel/impl/api/KernelImpl.java` (timeout status per path), `community/community-it/community-it/src/test/java/org/neo4j/server/TransactionTimeoutIT.java` (`shouldTimeoutAtDBMSLevel`).
- [N11] Same tag: `community/kernel/src/main/java/org/neo4j/kernel/impl/newapi/ProcedureCaller.java`, `community/kernel/src/main/java/org/neo4j/kernel/impl/api/KernelTransactionImplementation.java` (`securityContext()`), `.../api/OverridableSecurityContext.java`, `community/procedure/src/main/java/org/neo4j/procedure/impl/ProcedureLoginContextTransformer.java` and `ProcedureGraphDatabaseAPI.java`, `community/kernel-api/src/main/java/org/neo4j/internal/kernel/api/security/SecurityContext.java` and `AccessMode.java`, `community/neo4j-exceptions/src/main/java/org/neo4j/messages/MessageUtil.java`, `community/neo4j/src/main/java/org/neo4j/graphdb/facade/DatabaseManagementServiceFactory.java`, `community/security/src/main/java/org/neo4j/server/security/auth/BasicLoginContext.java` (a successful login gets `AccessMode.Static.FULL`).
- [N12] Same tag: `community/procedure/src/main/java/org/neo4j/procedure/impl/ProcedureCompiler.java`, `GlobalProceduresRegistry.java`, `ProcedureConfig.java`.
- [N13] Same tag: `community/fabric/query-router/src/main/java/org/neo4j/router/impl/transaction/database/LocalDatabaseTransactionFactory.java`, `.../transaction/RouterTransactionImpl.java`, `community/fabric/fabric/src/main/java/org/neo4j/fabric/transaction/TransactionMode.java`, `community/kernel/src/main/java/org/neo4j/kernel/impl/factory/GraphDatabaseFacade.java`.
- [N14] Same tag: `community/fabric/fabric/src/main/java/org/neo4j/fabric/executor/TaggingPlanDescriptionWrapper.java`, used in `.../router/impl/transaction/database/LocalDatabaseTransaction.java`.
- [N15] Same tag: `packaging/standalone/standalone-community/src/main/distribution/text/community/conf/neo4j.conf`.
- [N16] Same tag: `community/neo4j-gql-status/src/main/java/org/neo4j/gqlstatus/GqlStatusInfoCodes.java` (`01N00`, `42N02`).
- [N17] Same tag: `community/cypher/front-end/ast/src/main/scala/org/neo4j/cypher/internal/ast/Clause.scala` (`LoadCSV`, `UpdateClause`, `TerminateTransactionsClause`).
- [O1] Operations Manual 5.26, neo4j/docs-operations branch `5.x` (commit 9fe3944, 9 October 2026), `modules/ROOT/pages/configuration/configuration-settings.adoc`. https://neo4j.com/docs/operations-manual/5/configuration/configuration-settings/
- [O2] Same commit, `database-internals/transaction-management.adoc`. https://neo4j.com/docs/operations-manual/5/database-internals/transaction-management/
- [O3] Same commit, `security/securing-extensions.adoc`. https://neo4j.com/docs/operations-manual/5/security/securing-extensions/
- [O4] Same commit, `procedures/built-in-procedures.adoc` (modes and edition labels). https://neo4j.com/docs/operations-manual/5/procedures/
- [O5] Same commit, `authentication-authorization/manage-users.adoc`, `authentication-authorization/index.adoc`, `introduction.adoc` (edition table). https://neo4j.com/docs/operations-manual/5/authentication-authorization/manage-users/
- [O6] Same commit, `authentication-authorization/load-privileges.adoc`. https://neo4j.com/docs/operations-manual/5/authentication-authorization/load-privileges/
- [O7] Same commit, `database-internals/show-and-terminate-transactions.adoc`. https://neo4j.com/docs/operations-manual/5/database-internals/show-and-terminate-transactions/
- [C1] Cypher Manual (Cypher 5), neo4j/docs-cypher branch `cypher-5` (commit 3b2f6c2, 16 October 2026), `modules/ROOT/pages/clauses/load-csv.adoc`. https://neo4j.com/docs/cypher-manual/5/clauses/load-csv/
- [C2] Same commit, `syntax/parameters.adoc`. https://neo4j.com/docs/cypher-manual/5/syntax/parameters/
- [C3] Same commit, `planning-and-tuning/execution-plans.adoc` and `planning-and-tuning/operators/operators-detail.adoc`. https://neo4j.com/docs/cypher-manual/5/planning-and-tuning/execution-plans/
- [C4] Same commit, `deprecations-additions-removals-compatibility.adoc` (dynamic labels and types in MATCH, CREATE and MERGE added in 5.26; token lookup index use for them added in 2025.08). https://neo4j.com/docs/cypher-manual/5/deprecations-additions-removals-compatibility/
- [C5] Same commit, `clauses/order-by.adoc`, `clauses/limit.adoc`, `clauses/skip.adoc`. https://neo4j.com/docs/cypher-manual/5/clauses/order-by/
- [A1] APOC Core, neo4j/apoc tag 5.26.32 (commit fc74597), `core/src/main/java` (annotation scan of `@Procedure`, `@UserFunction` and `mode`), in particular `apoc/cypher/Cypher.java`, `CypherFunctions.java`, `Timeboxed.java`, `apoc/load/LoadJson.java`, `Xml.java`, `apoc/export/*`, `apoc/periodic/Periodic.java`, `apoc/util/Utils.java`, `apoc/meta/Meta.java`, `apoc/coll/Coll.java`, `apoc/version/Version.java`. https://github.com/neo4j/apoc/tree/5.26.32
- [A2] Same tag, `common/src/main/java/apoc/ApocConfig.java` (defaults, `checkReadAllowed`, `checkWriteAllowed`, error texts) and `common/src/main/java/apoc/util/FileUtils.java`.
- [A3] APOC Extended, neo4j-contrib/neo4j-apoc-procedures branch `5.26` (commit 27b2418), `extended/src/main/java/apoc/load/LoadCsv.java`. https://github.com/neo4j-contrib/neo4j-apoc-procedures/tree/5.26
- [A4] APOC 5 manual, Configuration Options (page shows "Version 5"). https://neo4j.com/apoc/5/config/
- [K1] docker-neo4j, local clone `/home/claude/neo4j/docker-neo4j` on master (commit fd9e4ec, 30 September 2026): `docker-image-src/5/coredb/docker-entrypoint.sh` (import folder, listen address default, variable-to-setting conversion, apoc.conf routing) and `neo4j-plugins.json`. https://github.com/neo4j/docker-neo4j
- [D1] Neo4j Python driver, neo4j/neo4j-python-driver tag 6.4.1 (commit 9755761, fresh clone), `src/neo4j/_async/driver.py` (`execute_query`), `src/neo4j/_async/work/session.py` (`begin_transaction`, `_open_transaction`), `src/neo4j/_async/work/transaction.py`. https://github.com/neo4j/neo4j-python-driver/tree/6.4.1
- [D2] Same tag, `src/neo4j/_async/io/_bolt/_bolt5.py` (`run` and `begin` extras).
- [D3] Same tag, `src/neo4j/_work/query.py` (`Query`, `unit_of_work`) and `src/neo4j/_async/work/transaction.py` (`close`, `rollback`).
- [D4] Same tag, `src/neo4j/_work/summary.py`.
- [D5] Same tag, `src/neo4j/_conf.py`, `src/neo4j/_async/config.py`, `src/neo4j/_api.py` (enums), `src/neo4j/exceptions.py` (classes and retryable flags).
- [D6] Same tag, `CHANGELOG.md` (6.0 to 6.4).
- [D7] Same tag, `docs/source/api.rst` (configuration options) and `docs/source/async_api.rst` (lifetime, thread safety, cancellation).
- [M1] Neo4j Python driver manual, neo4j/docs-drivers branch `6.x` (commit a64c13f), `python-manual/modules/ROOT/pages/query-simple.adoc`, `transactions.adoc`, `result-summary.adoc`. https://neo4j.com/docs/python-manual/current/query-simple/
- [G1] neo4j-graphrag-python, local clone `/home/claude/neo4j/neo4j-graphrag-python` on main (commit 029ebd9, version 1.22.0), `src/neo4j_graphrag/retrievers/text2cypher.py`. https://github.com/neo4j/neo4j-graphrag-python
- [R1] NeonRadar Phase 1 specification `/home/claude/neonradar-phase1/doc/PHASE-1.md` (sections 3.2, 5.3 and milestones M1.4, M1.7d, M1.9 and the onboarding assignment), Phase 2 specification `/home/claude/neonradar-phase2/doc/PHASE-2.md` (5.2 contract L17, milestones 2.12 and 2.13), Phase 3 specification `/home/claude/neonradar-phase3/doc/build/PHASE-3.md` and `/home/claude/neonradar-phase1/plan-extract.md`.
- [R2] NeonRadar research notes `/home/claude/neonradar-phase1/research/neo4j.md` (driver section) and `/home/claude/neonradar-phase3/research/detection-cypher-gds.md` (sections 3.3, 3.4, 5.1 and 6).
- [W1] RFC 9457, Problem Details for HTTP APIs (July 2023), read through the web fetch tool because the shell was refused. https://rfc-editor.org/rfc/rfc9457.html
- [W2] MDN, EventSource() constructor. https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource
- [W3] OpenAPI Initiative, Sequential Media Types. https://learn.openapis.org/specification/media-types
- [W4] Vite, Server Options (page shows v8.3.4). https://vite.dev/config/server-options
- [W5] NGINX documentation, NGINX Reverse Proxy (default Host and Connection headers). https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
- [W6] Docker documentation, Compose file reference, networks (`internal`). https://docs.docker.com/reference/compose-file/networks/

UNVERIFIED items, collected:
- the runtime `query_type` of procedure calls by mode, `LOAD CSV`, `SHOW` and `TERMINATE`, all derived from source;
- the exact Bolt-path wording of the read-mode error (the HTTP Query API test proves it for that path);
- the runtime messages for blocked `LOAD CSV` URLs and for writes inside READ procedures;
- whether the server stops a query at once when the driver closes a cancelled connection;
- how `openapi-typescript` handles `itemSchema`;
- the position of procedure names inside plan `args`;
- whether a Docker `internal` network can be combined with host-published ports;
- the memory test estimate in 6.4.
